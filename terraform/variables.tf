variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "region" {
  type        = string
  description = "GCP region for all resources"
  default     = "us-east1"
}

variable "image" {
  type        = string
  description = "Full Docker image URI to deploy (injected by CI)"
}

variable "service_name" {
  type        = string
  description = "Cloud Run service name (varies per branch)"
}

