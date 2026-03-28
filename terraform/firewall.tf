# Allow Streamlit traffic (port 8501)
resource "google_compute_firewall" "allow_streamlit" {
  name    = "allow-streamlit-8501"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["8501"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["streamlit-port"]
}

# Allow PGAdmin traffic (port 8080)
resource "google_compute_firewall" "allow_pgadmin" {
  name    = "allow-pgadmin-8080"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["8080"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["streamlit-port"]
}

# Allow Postgres traffic (port 5432) - Optional: only if you want direct access
resource "google_compute_firewall" "allow_postgres" {
  name    = "allow-postgres-5432"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["5432"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["streamlit-port"]
}

# Allow SSH traffic (port 22)
resource "google_compute_firewall" "allow_ssh" {
  name    = "allow-ssh-22"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["streamlit-port"]
}
