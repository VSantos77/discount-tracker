# Create GCS Bucket to store raw data
resource "google_storage_bucket" "data_lake" {
  name          = "${var.gcp_project_id}-discount-lake"
  location      = "US-EAST1" # Explicitly us-east1 for Free Tier
  force_destroy = true       # Allows TF to delete even if it has data

  storage_class               = "STANDARD"
  uniform_bucket_level_access = true

  # Lifecycle rule to move old data to cheaper storage if it grows
  lifecycle_rule {
    condition {
      age = 30 # Days
    }
    action {
      type = "Delete"
    }
  }
}

# Create bigquery dataset for raw data = bronze
resource "google_bigquery_dataset" "dataset_raw_source" {
  dataset_id                  = "raw_source"
  friendly_name               = "Raw Source Data"
  description                 = "Warehouse for raw discount data from spiders (bronze layer)"
  location                    = "US-EAST1"
  default_table_expiration_ms = null # Keep data permanently
}

## PROD
# Create prod bigquery dataset for staging and intermediate tables = silver
resource "google_bigquery_dataset" "dataset_prod_dbt_staged" {
  dataset_id                  = "prod_dbt_staged"
  friendly_name               = "Production DBT Staged Data"
  description                 = "Warehouse for staging and intermediate tables (silver layer)"
  location                    = "US-EAST1"
  default_table_expiration_ms = null # Keep data permanently
}

# Create prod bigquery dataset for marts data = gold
resource "google_bigquery_dataset" "dataset_prod_dbt_analytics" {
  dataset_id                  = "prod_dbt_analytics"
  friendly_name               = "Production DBT Analytics Data"
  description                 = "Warehouse for marts data (gold layer)"
  location                    = "US-EAST1"
  default_table_expiration_ms = null # Keep data permanently
}

## DEV
# Create dev bigquery dataset for staging and intermediate tables = silver
resource "google_bigquery_dataset" "dataset_dev_dbt_staged" {
  dataset_id                  = "dev_dbt_staged"
  friendly_name               = "Development DBT Staged Data"
  description                 = "Warehouse for staging and intermediate tables (silver layer)"
  location                    = "US-EAST1"
  default_table_expiration_ms = null # Keep data permanently
}

# Create dev bigquery dataset for marts data = gold
resource "google_bigquery_dataset" "dataset_dev_dbt_analytics" {
  dataset_id                  = "dev_dbt_analytics"
  friendly_name               = "Development DBT Analytics Data"
  description                 = "Warehouse for marts data (gold layer)"
  location                    = "US-EAST1"
  default_table_expiration_ms = null # Keep data permanently
}

# Create external table in BigQuery pointing to GCS bucket for raw discount data
resource "google_bigquery_table" "raw_discounts" {
  dataset_id = google_bigquery_dataset.dataset_raw_source.dataset_id
  table_id   = "raw_discounts"
  deletion_protection = false

  # Schema: single JSON column wrapping the full spider item.
  # Partition virtual columns (spider, date) are injected by hive partitioning.
  schema = jsonencode([
    {
      name = "raw_payload"
      type = "JSON"
      mode = "NULLABLE"
    }
  ])

  external_data_configuration {
    autodetect    = false
    source_format = "NEWLINE_DELIMITED_JSON"
    source_uris   = ["gs://${google_storage_bucket.data_lake.name}/landing/*"]

    hive_partitioning_options {
      mode = "CUSTOM"
      # landing/{spider:STRING}/{scraped_at_dt:DATE}/{timestamp}.jsonl
      source_uri_prefix = "gs://${google_storage_bucket.data_lake.name}/landing/{spider:STRING}/{scraped_at_dt:DATE}"
      require_partition_filter = true
    }
  }
}

# 1. Create a dedicated SA for the Scraper
resource "google_service_account" "scraper_sa" {
  account_id   = "discount-tracker-scraper"
  display_name = "Scraper Service Account"
}

# 2. Assign ONLY the permissions it needs (e.g., GCS access)
resource "google_project_iam_member" "gcs_access" {
  project = "vocal-tracer-484119-t7"
  role    = "roles/storage.objectCreator"
  member  = "serviceAccount:${google_service_account.scraper_sa.email}"
}

resource "google_service_account_iam_member" "allow_me_to_act_as_scraper" {
  service_account_id = google_service_account.scraper_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "user:santiago.villaverde07@gmail.com"
}

resource "google_cloud_run_v2_job" "scrapy-job" {
  name     = "discount-tracker-scrapy-job"
  location = var.region

  template {
    template {
      service_account = google_service_account.scraper_sa.email
      containers {
        image = "docker.io/vsantos77/discount-tracker-scrapy:v1.1"
      
        command = ["scrapy"]
        args    = ["crawl", "bbva", "-s", "CLOSESPIDER_ITEMCOUNT=1"]
        
        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
          }
        }

        env {
          name  = "GCP_PROJECT_ID"
          value = var.gcp_project_id
        }
        env {
          name  = "GCS_BUCKET"
          value = google_storage_bucket.data_lake.name
        }
        env {
          name  = "STORAGE_BACKEND"
          value = "gcs"
        }
      }
      max_retries = 0
    }
  }
}

# 1. Dedicated Service Account for dbt
resource "google_service_account" "dbt_sa" {
  account_id   = "discount-tracker-dbt-runner"
  display_name = "dbt BigQuery Runner"
}

# 2. Assign BigQuery Permissions (Least Privilege)
# Role to run jobs (queries)
resource "google_project_iam_member" "bq_job_user" {
  project = "vocal-tracer-484119-t7"
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.dbt_sa.email}"
}

# Role to edit data in your specific datasets
resource "google_project_iam_member" "bq_data_editor" {
  project = "vocal-tracer-484119-t7"
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.dbt_sa.email}"
}

resource "google_service_account_iam_member" "allow_me_to_act_as_dbt" {
  service_account_id = google_service_account.dbt_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "user:santiago.villaverde07@gmail.com"
}

resource "google_cloud_run_v2_job" "dbt-job" {
  name     = "discount-tracker-dbt-job"
  location = var.region
  template {
    template {
      service_account = google_service_account.dbt_sa.email
      containers {
        image = "docker.io/vsantos77/discount-tracker-dbt:v1.2"

        command = ["dbt"]
        args    = ["build", "--select", "stg_galicia", "--target","cloud-run-prod"]
        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
          }
        }

        env {
          name  = "GCP_PROJECT_ID"
          value = var.gcp_project_id
        }
        env {
          name  = "GCP_REGION"
          value = var.region
        }
      }
      max_retries = 0
    }
  }
}