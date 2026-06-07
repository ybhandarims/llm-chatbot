# Optional remote state backend.
# Create the S3 bucket and DynamoDB table first, then uncomment and adjust.
#
# terraform {
#   backend "s3" {
#     bucket        = "llm-chatbot-terraform-state"
#     key           = "prod/terraform.tfstate"
#     region        = "us-east-1"
#     dynamodb_table = "terraform-locks"
#     encrypt       = true
#   }
# }
