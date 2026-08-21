variable "gcp_project_id" {
  type        = string
  description = "The ID of the project in GCP"
}

variable "gcp_region" {
  type        = string
  default     = "us-east1" # Required for Always Free tier
  description = "Region for all resources"
}

variable "owner_email" {
  type        = string
  description = "Email for the project owner account"
}