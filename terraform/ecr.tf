locals {
  repositories = toset([
    "llm-chatbot/gateway",
    "llm-chatbot/conversations",
    "llm-chatbot/messages",
    "llm-chatbot/settings",
    "llm-chatbot/ai-worker",
    "llm-chatbot/frontend",
  ])
}

resource "aws_ecr_repository" "repos" {
  for_each = local.repositories

  name                 = each.value
  image_tag_mutability  = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "repos" {
  for_each   = aws_ecr_repository.repos
  repository = each.value.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 30 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 30
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
