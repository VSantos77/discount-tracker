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