output "app_url" {
  description = "Open this in your browser"
  value       = "https://${local.domain}"
}

output "google_redirect_uri" {
  description = "Add this to your Google OAuth client's redirect URIs"
  value       = "https://${local.domain}/auth/callback"
}

output "ssh_command" {
  description = "Log in to the server"
  value       = "ssh ubuntu@${aws_eip.app.public_ip}"
}