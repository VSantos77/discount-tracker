variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  default     = "us-east1"
}

variable "zone" {
  description = "GCP Zone"
  default     = "us-east1-c"
}

variable "vm_name" {
  description = "VM Instance name"
  default     = "discount-tracker-vm"
}

variable "machine_type" {
  description = "Machine type for VM"
  default     = "e2-micro"
}

variable "boot_disk_size" {
  description = "Boot disk size in GB"
  default     = 30
}

variable "github_repo_url" {
  description = "GitHub repository URL with authentication (SSH or HTTPS with PAT)"
  type        = string
}

variable "env_file_content" {
  description = "Content of .env file (sensitive)"
  type        = string
  sensitive   = true
}
