output "public_url" {
  description = "Dashboard (/) and API (/api/docs) behind Caddy."
  value       = "http://${aws_eip.host.public_ip}"
}

output "backup_bucket" {
  value = aws_s3_bucket.backups.bucket
}

output "ssm_session" {
  description = "Shell without opening SSH to the world."
  value       = "aws ssm start-session --target ${aws_instance.host.id} --region ${var.region}"
}
