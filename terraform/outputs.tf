output "vm_instance_name" {
  description = "The name of the VM instance"
  value       = google_compute_instance.discount_tracker.name
}

output "vm_external_ip" {
  description = "The external IP of the VM"
  value       = google_compute_instance.discount_tracker.network_interface[0].access_config[0].nat_ip
}

output "vm_internal_ip" {
  description = "The internal IP of the VM"
  value       = google_compute_instance.discount_tracker.network_interface[0].network_ip
}

output "streamlit_url" {
  description = "URL to access Streamlit app"
  value       = "http://${google_compute_instance.discount_tracker.network_interface[0].access_config[0].nat_ip}:8501"
}

output "vm_zone" {
  description = "The zone where the VM is deployed"
  value       = google_compute_instance.discount_tracker.zone
}

output "ssh_command" {
  description = "SSH command to connect to the VM"
  value       = "gcloud compute ssh ${google_compute_instance.discount_tracker.name} --zone=${google_compute_instance.discount_tracker.zone}"
}
