variable "aws_region" {
  description = "AWS region where resources will be created."
  type        = string
  default     = "us-east-1"
}

variable "repository_names" {
  description = "List of ECR repository names to create."
  type        = list(string)
  default = [
    "llm-chatbot/gateway",
    "llm-chatbot/conversations",
    "llm-chatbot/messages",
    "llm-chatbot/settings",
    "llm-chatbot/ai-worker",
    "llm-chatbot/frontend",
  ]
}

variable "image_tag_mutability" {
  description = "ECR tag mutability."
  type        = string
  default     = "MUTABLE"
}

variable "scan_on_push" {
  description = "Enable vulnerability scanning on push."
  type        = bool
  default     = true
}

variable "availability_zone_count" {
  description = "Number of availability zones to use"
  type        = number
  default     = 2
}

variable "project_name" {
  description = "Project name used in naming and tagging"
  type        = string
  default     = "llm-chatbot"
}

variable "tags" {
  description = "Common tags to apply to resources"
  type        = map(string)
  default     = {}
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
  default     = "chatapp-eks"
}

variable "kubernetes_version" {
  description = "EKS Kubernetes version"
  type        = string
  default     = "1.33"
}

variable "node_instance_type" {
  description = "EKS worker node instance type"
  type        = string
  default     = "t3.micro"
}

variable "node_desired_size" {
  description = "Desired number of worker nodes"
  type        = number
  default     = 1
}

variable "node_max_size" {
  description = "Maximum number of worker nodes"
  type        = number
  default     = 2
}

variable "node_min_size" {
  description = "Minimum number of worker nodes"
  type        = number
  default     = 1
}

variable "workload_namespace" {
  description = "Kubernetes namespace used by the application workloads"
  type        = string
  default     = "chatbot"
}

variable "workload_service_account_name" {
  description = "Kubernetes service account used by the application workloads"
  type        = string
  default     = "chatbot-workload"
}
