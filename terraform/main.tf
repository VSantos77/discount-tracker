terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  # Uncomment below to use remote state storage (after bucket creation)
  # backend "gcs" {
  #   bucket = "your-tf-state-bucket"
  #   prefix = "discount-tracker"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Create the VM instance
resource "google_compute_instance" "discount_tracker" {
  name         = var.vm_name
  machine_type = var.machine_type
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = var.boot_disk_size
    }
  }

  tags = ["http-server", "streamlit-port"]

  # Metadata for startup script
  metadata_startup_script = templatefile("${path.module}/cloud-init.sh", {
    github_repo_url = var.github_repo_url
    env_content     = var.env_file_content
  })

  network_interface {
    network = "default"
    access_config {
      # Ephemeral public IP assigned automatically
    }
  }

  metadata = {
    enable-oslogin = "true"
  }

  service_account {
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
  }
}
