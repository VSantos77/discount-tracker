resource "google_project_service" "workflows_api" {
  service            = "workflows.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "scheduler_api" {
  service            = "cloudscheduler.googleapis.com"
  disable_on_destroy = false
}

resource "google_service_account" "workflows_sa" {
  account_id   = "discount-tracker-workflows-sa"
  display_name = "Discount Tracker Workflows Service Account"
}

resource "google_project_iam_member" "workflows_run_developer" {
  project = var.gcp_project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.workflows_sa.email}"
}

resource "google_project_iam_member" "workflows_logging_viewer" {
  project = var.gcp_project_id
  role    = "roles/logging.viewer"
  member  = "serviceAccount:${google_service_account.workflows_sa.email}"
}

resource "google_project_iam_member" "workflows_logging_writer" {
  project = var.gcp_project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.workflows_sa.email}"
}

resource "google_project_iam_member" "workflows_storage_viewer" {
  project = var.gcp_project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.workflows_sa.email}"
}

resource "google_project_iam_member" "workflows_invoker" {
  project = var.gcp_project_id
  role    = "roles/workflows.invoker"
  member  = "serviceAccount:${google_service_account.workflows_sa.email}"
}

resource "google_workflows_workflow" "prod_workflow" {
  name            = "discount-tracker-prod-workflow"
  region          = var.gcp_region
  description     = "Prod discount tracker workflow"
  service_account = google_service_account.workflows_sa.id
  source_contents = file("${path.module}/workflow.yaml")
  depends_on      = [google_project_service.workflows_api]
}

resource "google_cloud_scheduler_job" "weekly_workflow" {
  name             = "discount-tracker-weekly"
  description      = "Triggers the discount tracker workflow weekly on mondays at 9 PM GMT-3"
  schedule         = "0 0 * * 1"
  time_zone        = "UTC"
  region           = var.gcp_region
  attempt_deadline = "1800s"

  http_target {
    http_method = "POST"
    uri         = "https://workflowexecutions.googleapis.com/v1/projects/${var.gcp_project_id}/locations/${var.gcp_region}/workflows/${google_workflows_workflow.prod_workflow.name}/executions"
    body = base64encode(jsonencode({
      argument = jsonencode({
        spiders    = ["galicia", "bbva", "naranjax"]
        dbt_cmd    = "build"
        dbt_target = "cloud-run-prod"
      })
    }))
    headers = {
      "Content-Type" = "application/json"
    }
    oauth_token {
      service_account_email = google_service_account.workflows_sa.email
    }
  }

  depends_on = [google_project_service.scheduler_api]
}
