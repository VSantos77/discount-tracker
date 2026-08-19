resource "google_service_account" "github-actions-deployer-sa" {
    account_id = "github-actions-deploy"
    display_name = "Github Actions Deploy Service Account"
}

resource "google_project_iam_member" "github-actions-deploy-update-cloud-run-job" {
  project = var.gcp_project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.github-actions-deployer-sa.email}"
}

resource "google_service_account_iam_member" "github-actions-deployer-run-as-scrapy-job" {
  service_account_id = google_service_account.scraper_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.github-actions-deployer-sa.email}"
}