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

output "eks_cluster_name" {
  description = "EKS cluster name."
  value       = aws_eks_cluster.main.name
}

output "eks_cluster_arn" {
  description = "EKS cluster ARN."
  value       = aws_eks_cluster.main.arn
}

output "eks_cluster_endpoint" {
  description = "EKS API server endpoint."
  value       = aws_eks_cluster.main.endpoint
}

output "eks_node_group_name" {
  description = "Managed node group name."
  value       = aws_eks_node_group.main.node_group_name
}

output "vpc_id" {
  description = "VPC ID created for EKS."
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "Public subnet IDs created for EKS."
  value       = [for subnet in aws_subnet.public : subnet.id]
}

output "workload_role_arn" {
  description = "IAM role ARN used by the workload service account."
  value       = aws_iam_role.workload.arn
}

output "workload_namespace" {
  description = "Namespace used by the workload service account."
  value       = var.workload_namespace
}

output "workload_service_account_name" {
  description = "Service account used by the workload pods."
  value       = var.workload_service_account_name
}

output "dynamodb_tables" {
  description = "DynamoDB table names created for the application."
  value = {
    conversations = aws_dynamodb_table.conversations.name
    messages      = aws_dynamodb_table.messages.name
    settings      = aws_dynamodb_table.settings.name
  }
}

output "sqs_queue_urls" {
  description = "SQS queue URLs for AI jobs and DLQ."
  value = {
    ai_jobs     = aws_sqs_queue.ai_jobs.id
    ai_jobs_dlq = aws_sqs_queue.ai_jobs_dlq.id
  }
}

output "s3_bucket" {
  description = "S3 bucket for assets"
  value       = aws_s3_bucket.assets.id
}

output "secrets_arns" {
  description = "ARNs of created Secrets Manager secrets"
  value       = { for k, s in aws_secretsmanager_secret.app_secrets : k => s.arn }
}

output "log_groups" {
  description = "CloudWatch Log Group names"
  value       = { for k, lg in aws_cloudwatch_log_group.services : k => lg.name }
}

output "acm_certificate_arn" {
  description = "ACM certificate ARN (if created)"
  value       = length(aws_acm_certificate.cert) > 0 ? aws_acm_certificate.cert[0].arn : ""
}
