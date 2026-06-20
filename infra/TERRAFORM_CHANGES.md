# Terraform Changes Summary

This file lists the Terraform additions and CI integrations added to the repository.

Managed resources (added):
- ECR repositories (`terraform/ecr.tf`) — frontend, gateway, conversations, messages, settings, ai-worker
- DynamoDB tables (`terraform/dynamodb.tf`) — `conversations`, `messages`, `settings`
- SQS queues (`terraform/sqs.tf`) — `ai-jobs.fifo`, `ai-jobs-dlq.fifo`
- IAM roles & IRSA bindings (`terraform/iam.tf`) — workload role and policies
- S3 bucket (`terraform/s3.tf`) — assets/static files
- Secrets Manager skeleton (`terraform/secrets.tf`) — secret resources (values provided via CI/GitHub secrets)
- CloudWatch Log Groups (`terraform/cloudwatch.tf`) — per-service log groups
- Route53 / ACM (`terraform/route53_acm.tf`) — optional ACM certificate + validation via Route53
- EKS scaffolding (`terraform/eks.tf`) — optional cluster management (disabled by default in CI apply)

CI / Automation:
- `.github/workflows/terraform.yml` — runs `terraform plan` on PRs/pushes and stores plan; `apply` is manual (workflow_dispatch) for safety.
- `.github/workflows/secrets-sync.yml` — manual workflow to securely create/update Secrets Manager secret values from GitHub Secrets.

Docs & Onboarding:
- `terraform/README.md` — usage, init, import, example `terraform.tfvars`.
- `infra/terraform.md` — step-by-step onboarding and import commands.

Safety notes:
- Remote backend example included in `terraform/backend.tf` (S3 + DynamoDB locking). Backends must be initialized with `-backend-config`.
- Import existing resources before running `apply` to prevent destructive changes.
- Secrets values should not be stored in Git. Use the `secrets-sync` workflow or manual `aws secretsmanager` commands.
