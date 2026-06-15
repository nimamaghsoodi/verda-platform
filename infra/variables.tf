variable "client_id" {
  description = "Verda Cloud OAuth2 client ID (from console → Keys → Cloud API Credentials)"
  type        = string
  sensitive   = true
}

variable "client_secret" {
  description = "Verda Cloud OAuth2 client secret"
  type        = string
  sensitive   = true
}

variable "location" {
  description = "Verda Cloud datacenter location code (GET /v1/locations)"
  type        = string
  default     = "FIN-01"
}

variable "image" {
  description = "OS image name (GET /v1/images)"
  type        = string
  default     = "ubuntu-22.04"
}

variable "instance_type_control_plane" {
  description = "Instance type for control-plane node (GET /v1/instance-types, filter cpu-only)"
  type        = string
  default     = "CPU.4V.16G"
}

variable "instance_type_worker" {
  description = "Instance type for worker nodes"
  type        = string
  default     = "CPU.4V.16G"
}

variable "worker_count" {
  description = "Number of worker nodes"
  type        = number
  default     = 2
}

variable "cluster_name" {
  description = "Name prefix for all resources"
  type        = string
  default     = "verda-k8s"
}

variable "ssh_public_key_path" {
  description = "Path to local SSH public key file"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "os_volume_size_gb" {
  description = "OS disk size in GB"
  type        = number
  default     = 100
}
