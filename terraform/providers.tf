terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0" # Using the latest 2026 stable range
    }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.region
}