# ---------------------------------------------------------------------------
# Scrapy job
# ---------------------------------------------------------------------------

resource "google_service_account" "scraper_sa" {
  account_id   = "discount-tracker-scraper"
  display_name = "Scraper Service Account"
}

resource "google_project_iam_member" "gcs_access" {
  project = var.gcp_project_id
  role    = "roles/storage.objectCreator"
  member  = "serviceAccount:${google_service_account.scraper_sa.email}"
}

resource "google_storage_bucket_iam_member" "gcs_bucket_reader" {
  bucket = google_storage_bucket.data_lake.name
  role   = "roles/storage.legacyBucketReader"
  member = "serviceAccount:${google_service_account.scraper_sa.email}"
}

resource "google_service_account_iam_member" "allow_me_to_act_as_scraper" {
  service_account_id = google_service_account.scraper_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "user:santiago.villaverde07@gmail.com"
}

resource "google_cloud_run_v2_job" "scrapy-job" {
  name     = "discount-tracker-scrapy-job"
  location = var.gcp_region

  template {
    template {
      service_account = google_service_account.scraper_sa.email
      timeout         = "3600s"
      max_retries     = 0

      containers {
        image   = "docker.io/vsantos77/discount-tracker-scrapy:v1.2"
        command = ["scrapy"]
        args    = ["crawl", "galicia"]

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
    }
  }
}


# ---------------------------------------------------------------------------
# dbt job
# ---------------------------------------------------------------------------

resource "google_service_account" "dbt_sa" {
  account_id   = "discount-tracker-dbt-runner"
  display_name = "dbt BigQuery Runner"
}

resource "google_project_iam_member" "bq_job_user" {
  project = var.gcp_project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.dbt_sa.email}"
}

resource "google_project_iam_member" "bq_data_editor" {
  project = var.gcp_project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.dbt_sa.email}"
}

resource "google_service_account_iam_member" "allow_me_to_act_as_dbt" {
  service_account_id = google_service_account.dbt_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "user:santiago.villaverde07@gmail.com"
}

resource "google_storage_bucket_iam_member" "dbt_gcs_object_viewer" {
  bucket = google_storage_bucket.data_lake.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.dbt_sa.email}"
}

resource "google_cloud_run_v2_job" "dbt-job" {
  name     = "discount-tracker-dbt-job"
  location = var.gcp_region

  template {
    template {
      service_account = google_service_account.dbt_sa.email
      max_retries     = 0

      containers {
        image   = "docker.io/vsantos77/discount-tracker-dbt:v1.2"
        command = ["dbt"]
        args    = ["build", "--target", "cloud-run-prod"]

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
          value = var.gcp_region
        }
      }
    }
  }
}
