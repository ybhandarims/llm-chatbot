# Terraform Onboarding & Import Guide

This document explains how to initialize Terraform for this project, import existing resources, and push secret values securely from GitHub Actions.

Prerequisites
- AWS CLI configured locally or GitHub repo secrets configured.
- `terraform` CLI installed (1.6+ recommended).
- Repository secrets set in GitHub: `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `OPENAI_API_KEY`.

1) Backends and initialization

- Create an S3 bucket and DynamoDB table for remote state locking (optional but recommended):

```bash
aws s3 mb s3://my-terraform-state-bucket --region us-east-1
aws dynamodb create-table --table-name terraform-locks --attribute-definitions AttributeName=LockID,AttributeType=S --key-schema AttributeName=LockID,KeyType=HASH --billing-mode PAY_PER_REQUEST
```

- Initialize Terraform with backend config:

```bash
cd terraform
terraform init -backend-config="bucket=my-terraform-state-bucket" -backend-config="key=llm-chatbot/terraform.tfstate" -backend-config="region=us-east-1" -backend-config="dynamodb_table=terraform-locks"
```

2) Plan and review

```bash
terraform plan -out=plan.tfplan -var-file=terraform.tfvars.example
```

3) Import existing resources (examples)

- ECR repository:
```bash
terraform import 'aws_ecr_repository.repos["llm-chatbot/gateway"]' llm-chatbot/gateway
```

- DynamoDB tables:
```bash
terraform import aws_dynamodb_table.conversations conversations
terraform import aws_dynamodb_table.messages messages
terraform import aws_dynamodb_table.settings settings
```

- SQS queues (provide queue URL):
```bash
terraform import aws_sqs_queue.ai_jobs <queue-url>
terraform import aws_sqs_queue.ai_jobs_dlq <dlq-queue-url>
```

- IAM roles/resources: locate ARN or ID and import with the appropriate address shown in the Terraform config.

- EKS (if you have an existing cluster created by `eksctl`):
```bash
terraform import aws_eks_cluster.main <cluster-name>
terraform import aws_eks_node_group.main <node-group-id>
```

4) Apply

After reviewing the plan, apply:

```bash
terraform apply -input=false plan.tfplan
```

5) Sync secrets from GitHub to AWS Secrets Manager (recommended)

- Set the repo secret `OPENAI_API_KEY` to the value you want stored.
- Trigger the workflow `Sync Secrets to AWS Secrets Manager` in the Actions tab, or run it locally using the AWS CLI:

```bash
# Create/update secret locally (manual alternative)
aws secretsmanager create-secret --name "llm-chatbot/openai_api_key" --secret-string "<your-secret>" || \
aws secretsmanager put-secret-value --secret-id "llm-chatbot/openai_api_key" --secret-string "<your-secret>"
```

6) Notes and best practices
- Do not put secret values in Terraform files or git.
- Start by managing non-destructive resources (ECR, DynamoDB, SQS, S3, CloudWatch) first.
- Import and reconcile existing infra before applying changes.
- Keep `apply` manual or protect the GitHub environment for production applies.

Questions? I can help import specific resources or enable protected environment approvals for the CI apply step.
