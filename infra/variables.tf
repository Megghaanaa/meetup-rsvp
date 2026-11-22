variable "aws_region" {
  description = "AWS Region of your project"
  type        = string
  default     = "ap-southeast-2"
}

variable "instance_type" {
  description = "Server size (Free Tier eligible for new accounts)"
  type        = string
  default     = "t4g.small"
}

variable "repo_url" {
  description = "Public GitHub repo to deploy"
  type        = string
}

variable "my_ip" {
  description = "Your public IP address, allowed to SSH in"
  type        = string
}

variable "ssh_public_key_path" {
  description = "Path to your SSH public key"
  type        = string
  default     = "~/.ssh/id_ed25519.pub"
}

variable "google_client_id" {
  type      = string
  sensitive = true
}

variable "google_client_secret" {
  type      = string
  sensitive = true
}

variable "session_secret" {
  type      = string
  sensitive = true
}