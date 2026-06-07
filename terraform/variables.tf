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
