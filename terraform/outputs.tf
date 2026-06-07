output "repository_urls" {
  description = "Map of ECR repository names to repository URLs."
  value = {
    for name, repo in aws_ecr_repository.repos : name => repo.repository_url
  }
}

output "repository_names" {
  description = "Names of created ECR repositories."
  value       = [for repo in aws_ecr_repository.repos : repo.name]
}
