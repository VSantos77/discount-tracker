### Common

# Create Service Account for cloud run job updates
resource "google_service_account" "github-actions-deployer-sa" {
    account_id = "github-actions-deploy"
    display_name = "Github Actions Deploy Service Account"
}

# Grant Cloud Run developer role to SA to edit Cloud Run Jobs
resource "google_project_iam_member" "github-actions-deploy-update-cloud-run-job" {
  project = var.gcp_project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.github-actions-deployer-sa.email}"
}

### Scrapy

# Allow CI SA to act as Scrapy Cloud Run Job (needed for edits)
resource "google_service_account_iam_member" "github-actions-deployer-run-as-scrapy-job" {
  service_account_id = google_service_account.scraper_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.github-actions-deployer-sa.email}"
}

### DBT

# Allow CI SA to act as DBT Cloud Run Job (needed for edits)
resource "google_service_account_iam_member" "github-actions-deployer-run-as-dbt-job" {
  service_account_id = google_service_account.dbt_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.github-actions-deployer-sa.email}"
}

# Create SA for DBT CI Target
resource "google_service_account" "dbt_ci_sa" {
    account_id = "dbt-ci-sa"
    display_name = "Github Actions CI DBT Service Account"
}

## ROLE GRANTS

# Run queries
resource "google_project_iam_member" "dbt_ci_sa_bq_job_user" {
  project = var.gcp_project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.dbt_ci_sa.email}"
}

# Read and write tables/views (viewer only to raw + editor to dev datasets)

resource "google_project_iam_member" "dbt_ci_bq_editor" {
  project    = var.gcp_project_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.dbt_ci_sa.email}"
}

# View storage objects and metadata (access external table)
resource "google_project_iam_member" "dbt_ci_sa_storage_object_viewer" {
  project = var.gcp_project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.dbt_ci_sa.email}"
}