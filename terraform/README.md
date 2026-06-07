# LLM Chatbot Terraform (ECR)

This folder creates the ECR repositories needed for the CI/CD pipeline.

## Files
- `providers.tf` - Terraform and AWS provider configuration
- `variables.tf` - Input variables
- `ecr.tf` - ECR repositories and lifecycle policy
- `outputs.tf` - Outputs for repository URLs
- `backend.tf` - Optional remote state backend example
- `terraform.tfvars.example` - Example values file

## Create resources
```bash
terraform init
terraform plan
terraform apply
```

## Optional remote state
1. Create an S3 bucket for Terraform state.
2. Create a DynamoDB table for state locking.
3. Uncomment the backend block in `providers.tf` or move it into `backend.tf`.
4. Run `terraform init -reconfigure`.

## Import existing repositories
If repositories already exist, import them before `apply`.
Example:
```bash
terraform import 'aws_ecr_repository.repos["llm-chatbot/gateway"]' llm-chatbot/gateway
```
Repeat for each repository.
