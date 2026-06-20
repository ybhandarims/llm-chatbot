# LLM Chatbot Terraform (ECR)

This folder creates the ECR repositories needed for the CI/CD pipeline.

## Files
- `providers.tf` - Terraform and AWS provider configuration
- `variables.tf` - Input variables
- `ecr.tf` - ECR repositories and lifecycle policy
- `outputs.tf` - Outputs for repository URLs
- `backend.tf` - Optional remote state backend example
- `terraform.tfvars.example` - Example values file

## Additional resources

This project now includes Terraform resources beyond ECR:

- `s3.tf` - S3 bucket for assets with encryption and public access blocked
- `secrets.tf` - Secrets Manager secrets skeleton (does not store secret values)
- `cloudwatch.tf` - CloudWatch Log Groups for application services
- `route53_acm.tf` - Optional ACM certificate and DNS validation via Route53 when `domain_name` is set

## How to enable ACM/Route53
Set `domain_name` in a `terraform.tfvars` file to request a certificate. A matching Route53 hosted zone must exist in the account.

## Example init/import/apply
Refer to the infra README and use the backend config described in `backend.tf` comments. Typical workflow:

```bash
cd terraform
terraform init -backend-config="bucket=my-terraform-state-bucket" -backend-config="key=llm-chatbot/terraform.tfstate" -backend-config="region=us-east-1" -backend-config="dynamodb_table=terraform-locks"
terraform plan -out=plan.tfplan -var-file=terraform.tfvars
# If resources already exist, import them, then:
# terraform import aws_ecr_repository.repos["llm-chatbot/gateway"] llm-chatbot/gateway
terraform apply -input=false plan.tfplan
```

Notes:
- Do not store secret values in code. Create secret versions manually or via CI using secure secrets.
- Start by planning and importing existing resources to avoid destructive changes.

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
