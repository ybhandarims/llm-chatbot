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
