# Cleanup Quick Reference - Essential Commands

**Quick Access**: Copy-paste commands for fast cleanup

---

## One-Line Full Cleanup (PowerShell)

```powershell
# Set variables
$ENV_CLUSTER="llm-chatbot"; $ENV_REGION="us-east-1"; $ENV_ACCOUNT=$(aws sts get-caller-identity --query Account --output text);

# 1. Delete Helm
helm uninstall llm-chatbot -n chatbot; Start-Sleep 5

# 2. Delete namespace
kubectl delete namespace chatbot; Start-Sleep 30

# 3. Delete EKS (wait 10-15 min)
eksctl delete cluster --name $ENV_CLUSTER --region $ENV_REGION --wait

# 4. Delete DynamoDB
foreach ($t in "conversations","messages","settings") { aws dynamodb delete-table --table-name $t --region $ENV_REGION }

# 5. Delete SQS
$q1=$(aws sqs get-queue-url --queue-name ai-jobs.fifo --region $ENV_REGION --query QueueUrl --output text);
$q2=$(aws sqs get-queue-url --queue-name ai-jobs-dlq.fifo --region $ENV_REGION --query QueueUrl --output text);
aws sqs delete-queue --queue-url $q1 --region $ENV_REGION; aws sqs delete-queue --queue-url $q2 --region $ENV_REGION

# 6. Delete ECR
foreach ($s in "frontend","gateway","settings","conversations","messages","ai-worker","auth-service") { aws ecr delete-repository --repository-name llm-chatbot/$s --force --region $ENV_REGION }

# 7. Delete IAM
aws iam delete-role-policy --role-name llm-chatbot-workload --policy-name llm-chatbot-inline-policy; aws iam delete-role --role-name llm-chatbot-workload

# 8. Verify
write-host "✅ Cleanup complete!"
```

---

## Helm Commands

```bash
# List releases
helm list -n chatbot
helm list -n chatbot --all

# Uninstall
helm uninstall llm-chatbot -n chatbot

# Verify deletion
helm list -n chatbot
kubectl get pods -n chatbot
```

---

## Kubernetes Commands

```bash
# Delete namespace
kubectl delete namespace chatbot
kubectl delete namespace chatbot --grace-period=0 --force  # Force delete if stuck

# Verify deletion
kubectl get namespace chatbot
kubectl get namespace  # List all namespaces

# Check pods before deletion
kubectl get pods -n chatbot
kubectl get all -n chatbot
```

---

## EKS Commands

```bash
# List clusters
eksctl get clusters

# Get cluster info
eksctl get cluster --name llm-chatbot
eksctl get nodegroup --cluster llm-chatbot

# Delete cluster (WAIT 10-15 MINUTES)
eksctl delete cluster --name llm-chatbot --region us-east-1 --wait

# Force delete (if delete stuck)
aws cloudformation delete-stack --stack-name eksctl-llm-chatbot-cluster

# Check CloudFormation status
aws cloudformation describe-stacks --stack-name eksctl-llm-chatbot-cluster
```

---

## DynamoDB Commands

```bash
# List tables
aws dynamodb list-tables
aws dynamodb list-tables --query "TableNames[]"

# Describe table
aws dynamodb describe-table --table-name conversations

# Delete table
aws dynamodb delete-table --table-name conversations
aws dynamodb delete-table --table-name messages
aws dynamodb delete-table --table-name settings

# Backup before delete
aws dynamodb scan --table-name conversations > conversations-backup.json
```

---

## SQS Commands

```bash
# List queues
aws sqs list-queues

# Get queue URLs first (IMPORTANT: Variables must be set)
MAIN_QUEUE=$(aws sqs get-queue-url --queue-name ai-jobs.fifo --region us-east-1 --query QueueUrl --output text)
DLQ=$(aws sqs get-queue-url --queue-name ai-jobs-dlq.fifo --region us-east-1 --query QueueUrl --output text)

# Verify variables
echo "Main: $MAIN_QUEUE"
echo "DLQ: $DLQ"

# Get queue attributes
aws sqs get-queue-attributes --queue-url "$MAIN_QUEUE" --attribute-names ApproximateNumberOfMessages

# Delete queues (with proper quoting)
aws sqs delete-queue --queue-url "$MAIN_QUEUE"
aws sqs delete-queue --queue-url "$DLQ"

# Verify deletion
aws sqs list-queues --region us-east-1
```

---

## ECR Commands

```bash
# List repositories
aws ecr describe-repositories
aws ecr describe-repositories --query "repositories[].repositoryName"

# List images
aws ecr describe-images --repository-name llm-chatbot/gateway

# Delete repository
aws ecr delete-repository --repository-name llm-chatbot/gateway --force

# Delete all llm-chatbot repos
for repo in frontend gateway settings conversations messages ai-worker auth-service; do
  aws ecr delete-repository --repository-name llm-chatbot/$repo --force
done
```

---

## IAM Commands

```bash
# List roles
aws iam list-roles
aws iam list-roles --query "Roles[?contains(RoleName, 'chatbot')].RoleName"

# List inline policies
aws iam list-role-policies --role-name llm-chatbot-workload

# Delete inline policy
aws iam delete-role-policy --role-name llm-chatbot-workload --policy-name llm-chatbot-inline-policy

# Delete role
aws iam delete-role --role-name llm-chatbot-workload

# List managed policies
aws iam list-policies --scope Local --query "Policies[?contains(PolicyName, 'Chatbot')]"

# Delete managed policy
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
aws iam delete-policy --policy-arn arn:aws:iam::$ACCOUNT:policy/AWSLoadBalancerControllerPolicy
```

---

## Secrets Manager Commands

```bash
# List secrets
aws secretsmanager list-secrets
aws secretsmanager list-secrets --query "SecretList[?contains(Name, 'llm-chatbot')]"

# Get secret value
aws secretsmanager get-secret-value --secret-id llm-chatbot/openai-key

# Delete secret (permanent after 7 days)
aws secretsmanager delete-secret --secret-id llm-chatbot/openai-key --force-delete-without-recovery

# Delete without recovery
aws secretsmanager delete-secret --secret-id llm-chatbot/openai-key --force-delete-without-recovery
```

---

## CloudWatch Logs Commands

```bash
# List log groups
aws logs describe-log-groups
aws logs describe-log-groups --query "logGroups[].logGroupName"

# Find llm-chatbot logs
aws logs describe-log-groups --query "logGroups[?contains(logGroupName, 'llm-chatbot')].logGroupName"

# Delete log group
aws logs delete-log-group --log-group-name /aws/eks/llm-chatbot/gateway

# Export logs before delete (optional)
aws logs create-export-task --log-group-name /aws/eks/llm-chatbot/gateway --from 0 --to $(date +%s)000 --destination my-s3-bucket
```

---

## Verification Commands

```bash
# Quick verification
echo "=== Cleanup Status ==="
echo "Clusters: $(eksctl get clusters 2>&1 | grep -c llm-chatbot || echo 0)"
echo "DynamoDB Tables: $(aws dynamodb list-tables --query 'TableNames[]' --output text | wc -w)"
echo "ECR Repos: $(aws ecr describe-repositories --query 'repositories[].repositoryName' --output text | grep -c llm-chatbot || echo 0)"
echo "IAM Roles: $(aws iam list-roles --query 'Roles[?contains(RoleName, \"chatbot\")].RoleName' --output text | wc -w)"

# Full verification
bash ./cleanup/verify-cleanup.sh
```

---

## Troubleshooting Quick Fixes

### Stuck on EKS deletion
```bash
# Check CloudFormation stack
aws cloudformation describe-stacks --stack-name eksctl-llm-chatbot-cluster

# Force delete if stuck >30 min
aws cloudformation delete-stack --stack-name eksctl-llm-chatbot-cluster
```

### DynamoDB table deletion fails
```bash
# Check if table locked
aws dynamodb describe-table --table-name conversations

# Try again
aws dynamodb delete-table --table-name conversations
```

### IAM role deletion fails
```bash
# Remove attached policies first
aws iam list-role-policies --role-name llm-chatbot-workload
aws iam delete-role-policy --role-name llm-chatbot-workload --policy-name [POLICY_NAME]

# Then delete role
aws iam delete-role --role-name llm-chatbot-workload
```

### ECR repository deletion fails
```bash
# Force delete
aws ecr delete-repository --repository-name llm-chatbot/gateway --force
```

---

## Environment Variables (Setup Once)

```bash
# Export for use in commands
export AWS_REGION="us-east-1"
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export CLUSTER_NAME="llm-chatbot"
export ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Verify
echo "Region: $AWS_REGION"
echo "Account: $AWS_ACCOUNT_ID"
echo "Cluster: $CLUSTER_NAME"
echo "Registry: $ECR_REGISTRY"
```

---

## Save These Commands

```bash
# Create an alias for quick cleanup verification
alias check-cleanup='echo "Clusters: $(eksctl get clusters 2>&1 | grep llm-chatbot | wc -l)" && echo "DynamoDB: $(aws dynamodb list-tables --query "TableNames[]" 2>/dev/null | wc -w)" && echo "ECR: $(aws ecr describe-repositories --query "repositories[?contains(repositoryName, '\''chatbot'\'')].repositoryName" 2>/dev/null | wc -w)"'

# Add to ~/.bashrc or ~/.bash_profile for persistence
echo "alias check-cleanup='...'" >> ~/.bashrc
```

---

## Cost Verification

After cleanup, verify cost savings in AWS Console:

1. **CloudWatch**: Go to Cost Explorer
2. **Filter**: By service
3. **Look for**: EKS, EC2, DynamoDB, SQS, CloudWatch costs going to $0
4. **Timeline**: Changes may take 24 hours to show

---

**Status**: Ready for cleanup  
**Reference**: Use these commands as shortcuts during cleanup process
