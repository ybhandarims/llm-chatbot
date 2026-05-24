# Infrastructure Cleanup - Complete Resource Teardown

**Version**: 1.0  
**Purpose**: Safely remove all deployed resources to avoid AWS charges  
**Duration**: 30-45 minutes  
**Cost Saved**: ~$450/month infrastructure costs  

---

## Overview

This folder contains comprehensive cleanup procedures to safely tear down all AWS and Kubernetes resources created during deployment.

### What Gets Deleted

```
✅ Kubernetes Resources (EKS)
   ├─ Helm releases
   ├─ Namespaces
   ├─ Services
   ├─ Deployments
   └─ Persistent volumes

✅ AWS Resources
   ├─ EKS Cluster
   ├─ Node Groups
   ├─ DynamoDB Tables
   ├─ SQS Queues
   ├─ ECR Repositories
   ├─ IAM Roles & Policies
   ├─ Secrets Manager Secrets
   ├─ CloudWatch Log Groups
   └─ VPC & Networking

✅ Cost Savings
   └─ ~$450/month (on-demand) or ~$250/month (spot)
```

---

## Quick Start - Full Cleanup (5 Steps)

### Option 1: Automated Full Cleanup (Recommended)

**PowerShell**:
```powershell
# Run comprehensive cleanup script
.\cleanup\cleanup-all.ps1 -Confirm
```

**Bash**:
```bash
# Run comprehensive cleanup script
chmod +x ./cleanup/cleanup-all.sh
./cleanup/cleanup-all.sh --confirm
```

### Option 2: Manual Phase-by-Phase Cleanup

Follow the phases in order:

1. **Phase 1**: [Delete Helm Release](#phase-1-delete-helm-release) (2 min)
2. **Phase 2**: [Delete Kubernetes Namespace](#phase-2-delete-kubernetes-namespace) (3 min)
3. **Phase 3**: [Delete EKS Cluster](#phase-3-delete-eks-cluster) (10-15 min)
4. **Phase 4**: [Delete AWS Resources](#phase-4-delete-aws-resources) (5 min)
5. **Phase 5**: [Verify Cleanup](#phase-5-verify-cleanup) (5 min)

---

## Files in This Folder

```
cleanup/
├─ README.md (this file)
├─ CLEANUP_RUNBOOK.md                    # Detailed phase-by-phase cleanup
├─ CLEANUP_QUICK_REFERENCE.md            # Common cleanup commands
├─ cleanup-all.ps1                       # PowerShell automated cleanup
├─ cleanup-all.sh                        # Bash automated cleanup
├─ cleanup-phases/
│  ├─ 01-helm-cleanup.ps1
│  ├─ 01-helm-cleanup.sh
│  ├─ 02-k8s-cleanup.ps1
│  ├─ 02-k8s-cleanup.sh
│  ├─ 03-eks-cluster-cleanup.ps1
│  ├─ 03-eks-cluster-cleanup.sh
│  ├─ 04-aws-resources-cleanup.ps1
│  ├─ 04-aws-resources-cleanup.sh
│  └─ verify-cleanup.sh
├─ CLEANUP_CHECKLIST.md                  # Pre/during/post cleanup checklist
├─ COST_ANALYSIS.md                      # What cleanup saves
└─ ROLLBACK_ALTERNATIVES.md              # If you need to rollback instead
```

---

## Detailed Cleanup Process

### Phase 1: Delete Helm Release

**Duration**: 2 minutes  
**Reversible**: Yes (can reinstall if needed immediately)

Remove all Kubernetes resources deployed by Helm in one command:

**PowerShell**:
```powershell
$Env:CLUSTER_NAME = "llm-chatbot"

# Uninstall Helm release
helm uninstall llm-chatbot -n chatbot

# Verify removed
helm list -n chatbot
kubectl get pods -n chatbot
```

**Bash**:
```bash
export CLUSTER_NAME="llm-chatbot"

# Uninstall Helm release
helm uninstall llm-chatbot -n chatbot

# Verify
helm list -n chatbot
kubectl get pods -n chatbot
```

**Expected Output**: No resources shown after this phase

---

### Phase 2: Delete Kubernetes Namespace

**Duration**: 3 minutes  
**Reversible**: Yes (namespace can be recreated)

Remove the entire `chatbot` namespace and all resources within it:

**PowerShell**:
```powershell
# Delete namespace (cascading delete of all resources)
kubectl delete namespace chatbot

# Wait for deletion to complete
kubectl get namespace chatbot -w

# Verify deletion
kubectl get namespace
```

**Bash**:
```bash
# Delete namespace
kubectl delete namespace chatbot

# Wait for deletion
kubectl get namespace chatbot -w

# Verify
kubectl get namespace
```

**Expected Output**: `Error from server (NotFound)` - namespace is gone

---

### Phase 3: Delete EKS Cluster

**Duration**: 10-15 minutes ⏱️ (automated process)  
**Reversible**: No - requires full rebuild  
**WARNING**: This is the main cost saver

Delete the entire EKS cluster (all nodes, control plane):

**PowerShell**:
```powershell
$Env:CLUSTER_NAME = "llm-chatbot"
$Env:AWS_REGION = "us-east-1"

# Delete cluster (eksctl handles all cleanup)
eksctl delete cluster `
  --name $Env:CLUSTER_NAME `
  --region $Env:AWS_REGION `
  --wait

# This removes:
# - EC2 nodes
# - EKS control plane
# - IAM roles
# - Security groups
# - VPC configuration
# - Auto Scaling Groups
```

**Bash**:
```bash
export CLUSTER_NAME="llm-chatbot"
export AWS_REGION="us-east-1"

# Delete cluster
eksctl delete cluster \
  --name ${CLUSTER_NAME} \
  --region ${AWS_REGION} \
  --wait

# Removes all associated resources
```

**⏱️ WAIT 10-15 MINUTES** - CloudFormation stack deletion in progress

**Expected Output**:
```
[ℹ]  deleting EKS cluster "llm-chatbot"
[ℹ]  deleting CloudFormation stack "eksctl-llm-chatbot-cluster"
[✔]  cluster deleted
```

---

### Phase 4: Delete AWS Resources

**Duration**: 5-10 minutes  
**Reversible**: Partial (can recreate tables if you have backups)

Remove remaining AWS resources not handled by eksctl:

#### Step 4.1: Delete DynamoDB Tables

**PowerShell**:
```powershell
$Env:AWS_REGION = "us-east-1"
$tables = @("conversations", "messages", "settings")

foreach ($table in $tables) {
    Write-Host "Deleting DynamoDB table: $table"
    
    aws dynamodb delete-table `
      --table-name $table `
      --region $Env:AWS_REGION
}

# Wait for deletion
Start-Sleep -Seconds 5

# Verify
aws dynamodb list-tables --region $Env:AWS_REGION
```

**Bash**:
```bash
export AWS_REGION="us-east-1"

for table in conversations messages settings; do
    echo "Deleting DynamoDB table: $table"
    
    aws dynamodb delete-table \
      --table-name $table \
      --region ${AWS_REGION}
done

# Wait for deletion
sleep 5

# Verify
aws dynamodb list-tables --region ${AWS_REGION}
```

#### Step 4.2: Delete SQS Queues

**PowerShell**:
```powershell
# Get queue URLs
$mainQueue = (aws sqs get-queue-url --queue-name ai-jobs.fifo --region $Env:AWS_REGION --query QueueUrl --output text)
$dlq = (aws sqs get-queue-url --queue-name ai-jobs-dlq.fifo --region $Env:AWS_REGION --query QueueUrl --output text)

# Delete queues
aws sqs delete-queue --queue-url $mainQueue --region $Env:AWS_REGION
aws sqs delete-queue --queue-url $dlq --region $Env:AWS_REGION

# Verify
aws sqs list-queues --region $Env:AWS_REGION
```

**Bash**:
```bash
# Get queue URLs
MAIN_QUEUE=$(aws sqs get-queue-url --queue-name ai-jobs.fifo --region ${AWS_REGION} --query QueueUrl --output text)
DLQ=$(aws sqs get-queue-url --queue-name ai-jobs-dlq.fifo --region ${AWS_REGION} --query QueueUrl --output text)

# Delete queues
aws sqs delete-queue --queue-url $MAIN_QUEUE --region ${AWS_REGION}
aws sqs delete-queue --queue-url $DLQ --region ${AWS_REGION}

# Verify
aws sqs list-queues --region ${AWS_REGION}
```

#### Step 4.3: Delete Secrets Manager Secrets

**PowerShell**:
```powershell
# Delete secret
aws secretsmanager delete-secret `
  --secret-id llm-chatbot/openai-key `
  --force-delete-without-recovery `
  --region $Env:AWS_REGION

# Verify
aws secretsmanager describe-secret `
  --secret-id llm-chatbot/openai-key `
  --region $Env:AWS_REGION 2>&1 | Select-String "ResourceNotFoundException"
```

**Bash**:
```bash
# Delete secret (permanent, no recovery)
aws secretsmanager delete-secret \
  --secret-id llm-chatbot/openai-key \
  --force-delete-without-recovery \
  --region ${AWS_REGION}

# Verify
aws secretsmanager describe-secret \
  --secret-id llm-chatbot/openai-key \
  --region ${AWS_REGION} 2>&1 | grep "ResourceNotFoundException"
```

#### Step 4.4: Delete ECR Repositories

**PowerShell**:
```powershell
$services = @("frontend", "gateway", "settings", "conversations", "messages", "ai-worker")

foreach ($svc in $services) {
    Write-Host "Deleting ECR repository: llm-chatbot/$svc"
    
    aws ecr delete-repository `
      --repository-name llm-chatbot/$svc `
      --force `
      --region $Env:AWS_REGION
}

# Verify
aws ecr describe-repositories --region $Env:AWS_REGION
```

**Bash**:
```bash
for service in frontend gateway settings conversations messages ai-worker; do
    echo "Deleting ECR repository: llm-chatbot/$service"
    
    aws ecr delete-repository \
      --repository-name llm-chatbot/$service \
      --force \
      --region ${AWS_REGION}
done

# Verify
aws ecr describe-repositories --region ${AWS_REGION}
```

#### Step 4.5: Delete IAM Roles and Policies

**PowerShell**:
```powershell
# Delete inline policy
aws iam delete-role-policy `
  --role-name llm-chatbot-workload `
  --policy-name llm-chatbot-inline-policy

# Delete role
aws iam delete-role `
  --role-name llm-chatbot-workload

# Delete ALB policy (if created)
aws iam delete-policy `
  --policy-arn arn:aws:iam::$Env:AWS_ACCOUNT_ID`:policy/AWSLoadBalancerControllerPolicy

# Verify
aws iam list-roles --query "Roles[?contains(RoleName, 'chatbot')]"
```

**Bash**:
```bash
# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Delete inline policy
aws iam delete-role-policy \
  --role-name llm-chatbot-workload \
  --policy-name llm-chatbot-inline-policy

# Delete role
aws iam delete-role \
  --role-name llm-chatbot-workload

# Delete ALB policy
aws iam delete-policy \
  --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/AWSLoadBalancerControllerPolicy

# Verify
aws iam list-roles --query "Roles[?contains(RoleName, 'chatbot')]"
```

#### Step 4.6: Delete CloudWatch Log Groups

**PowerShell**:
```powershell
# List log groups
$logGroups = aws logs describe-log-groups `
  --query "logGroups[?contains(logGroupName, 'llm-chatbot')].logGroupName" `
  --output text

# Delete each
foreach ($lg in $logGroups.Split()) {
    Write-Host "Deleting log group: $lg"
    aws logs delete-log-group --log-group-name $lg
}

# Verify
aws logs describe-log-groups --query "logGroups[?contains(logGroupName, 'llm-chatbot')]"
```

**Bash**:
```bash
# Find and delete log groups
aws logs describe-log-groups \
  --query "logGroups[?contains(logGroupName, 'llm-chatbot')].logGroupName" \
  --output text | tr '\t' '\n' | while read lg; do
    echo "Deleting log group: $lg"
    aws logs delete-log-group --log-group-name "$lg"
done

# Verify
aws logs describe-log-groups --query "logGroups[?contains(logGroupName, 'llm-chatbot')]"
```

---

### Phase 5: Verify Cleanup

**Duration**: 5 minutes  
**Goal**: Confirm all resources are deleted

Run verification commands to ensure nothing remains:

**PowerShell**:
```powershell
$Env:AWS_REGION = "us-east-1"

Write-Host "=== Verification Checklist ==="

# 1. Check EKS clusters
Write-Host "`n1. EKS Clusters:"
eksctl get clusters

# 2. Check DynamoDB tables
Write-Host "`n2. DynamoDB Tables:"
aws dynamodb list-tables --region $Env:AWS_REGION

# 3. Check SQS queues
Write-Host "`n3. SQS Queues:"
aws sqs list-queues --region $Env:AWS_REGION 2>&1 | Select-String "QueueUrl"

# 4. Check ECR repositories
Write-Host "`n4. ECR Repositories:"
aws ecr describe-repositories --query "repositories[?contains(repositoryName, 'chatbot')]" --region $Env:AWS_REGION

# 5. Check IAM roles
Write-Host "`n5. IAM Roles:"
aws iam list-roles --query "Roles[?contains(RoleName, 'chatbot')]"

# 6. Check Secrets Manager
Write-Host "`n6. Secrets:"
aws secretsmanager list-secrets --region $Env:AWS_REGION | Select-String "llm-chatbot"

# 7. Check kubeconfig
Write-Host "`n7. Kubeconfig Context:"
kubectl config get-contexts | Select-String "llm-chatbot"

Write-Host "`n✅ If all above show 'No resources' or 'None', cleanup is complete!"
```

**Bash**:
```bash
export AWS_REGION="us-east-1"

echo "=== Verification Checklist ==="

# 1. EKS Clusters
echo -e "\n1. EKS Clusters:"
eksctl get clusters || echo "No clusters"

# 2. DynamoDB
echo -e "\n2. DynamoDB Tables:"
aws dynamodb list-tables --region ${AWS_REGION} --query "TableNames[]" || echo "No tables"

# 3. SQS Queues
echo -e "\n3. SQS Queues:"
aws sqs list-queues --region ${AWS_REGION} 2>/dev/null | grep QueueUrl || echo "No queues"

# 4. ECR Repositories
echo -e "\n4. ECR Repositories:"
aws ecr describe-repositories --region ${AWS_REGION} --query "repositories[?contains(repositoryName, 'chatbot')].repositoryName" 2>/dev/null || echo "No repos"

# 5. IAM Roles
echo -e "\n5. IAM Roles:"
aws iam list-roles --query "Roles[?contains(RoleName, 'chatbot')].RoleName" 2>/dev/null || echo "No roles"

# 6. Secrets Manager
echo -e "\n6. Secrets:"
aws secretsmanager list-secrets --region ${AWS_REGION} --query "SecretList[?contains(Name, 'llm-chatbot')].Name" 2>/dev/null || echo "No secrets"

# 7. Log Groups
echo -e "\n7. Log Groups:"
aws logs describe-log-groups --region ${AWS_REGION} --query "logGroups[?contains(logGroupName, 'llm-chatbot')].logGroupName" 2>/dev/null || echo "No log groups"

echo -e "\n✅ If all show empty, cleanup is complete!"
```

**Expected Output**: All queries return empty or "No resources"

---

## Important Notes

### ⚠️ Before Cleanup

- [ ] Backup any important data from DynamoDB (if needed)
- [ ] Export conversations if you want to keep them
- [ ] Verify you won't need the cluster in the immediate future
- [ ] Confirm with team leads that cleanup is approved
- [ ] Save any important logs or metrics

### ⚠️ During Cleanup

- **Do NOT interrupt** eksctl deletion (Phase 3)
  - If interrupted, manually check AWS Console for orphaned resources
- **Keep terminal open** during the 10-15 minute wait
- **Watch for errors** - retry failed commands if needed

### ⚠️ After Cleanup

- [ ] Verify all resources deleted (Phase 5)
- [ ] Check AWS Console for any remaining resources
- [ ] Remove local kubeconfig context: `kubectl config delete-context <context>`
- [ ] Confirm CloudWatch shows no new charges
- [ ] Update team on cleanup completion

---

## Quick Cleanup (PowerShell - 5 Steps)

```powershell
# 1. Setup
$Env:AWS_REGION = "us-east-1"
$Env:CLUSTER_NAME = "llm-chatbot"
$Env:AWS_ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text)

# 2. Delete Helm
helm uninstall llm-chatbot -n chatbot

# 3. Delete namespace
kubectl delete namespace chatbot

# 4. Delete cluster (wait 10-15 min)
eksctl delete cluster --name $Env:CLUSTER_NAME --region $Env:AWS_REGION --wait

# 5. Delete AWS resources
# DynamoDB
foreach ($t in "conversations", "messages", "settings") {
    aws dynamodb delete-table --table-name $t --region $Env:AWS_REGION
}

# SQS
$q = aws sqs get-queue-url --queue-name ai-jobs.fifo --region $Env:AWS_REGION --query QueueUrl --output text
aws sqs delete-queue --queue-url $q --region $Env:AWS_REGION

# ECR
foreach ($s in "frontend", "gateway", "settings", "conversations", "messages", "ai-worker") {
    aws ecr delete-repository --repository-name llm-chatbot/$s --force --region $Env:AWS_REGION
}

# IAM
aws iam delete-role-policy --role-name llm-chatbot-workload --policy-name llm-chatbot-inline-policy
aws iam delete-role --role-name llm-chatbot-workload

Write-Host "✅ Cleanup Complete!"
```

---

## Cost Impact

### Monthly Savings (By Deleting)

| Resource | Monthly Cost | Deleted |
|----------|--------------|---------|
| EKS Control Plane | $73 | ✅ |
| EC2 Nodes (4x) | $300 | ✅ |
| DynamoDB | $30 | ✅ |
| SQS | $5 | ✅ |
| CloudWatch | $20 | ✅ |
| Data Transfer | $20 | ✅ |
| **TOTAL MONTHLY** | **$450** | **✅** |

**With Spot Instances**: Save additional $100-200/month

**Saved After Cleanup**: ~$450-650/month infrastructure costs

---

## Troubleshooting Cleanup Issues

### Issue: eksctl deletion stuck or failed

**Solution**:
```bash
# Check CloudFormation stack
aws cloudformation describe-stacks --stack-name eksctl-llm-chatbot-cluster

# Manually delete if needed (careful!)
aws cloudformation delete-stack --stack-name eksctl-llm-chatbot-cluster

# Check for orphaned resources in AWS Console
```

### Issue: DynamoDB table deletion fails (table locked)

**Solution**:
```bash
# Check if table exists
aws dynamodb describe-table --table-name conversations

# Force deletion
aws dynamodb delete-table --table-name conversations --region us-east-1
```

### Issue: IAM role deletion fails (still attached to resources)

**Solution**:
```bash
# Check attached policies
aws iam list-role-policies --role-name llm-chatbot-workload

# Delete inline policies
aws iam list-role-policies --role-name llm-chatbot-workload --query "PolicyNames[]" \
  | jq -r '.[]' | while read policy; do
    aws iam delete-role-policy --role-name llm-chatbot-workload --policy-name $policy
  done

# Then delete role
aws iam delete-role --role-name llm-chatbot-workload
```

---

## Next Steps After Cleanup

### Option 1: Complete Infrastructure Removal
- All resources deleted
- AWS account clean
- No ongoing charges
- Ready to start fresh anytime

### Option 2: Keep ECR Images (Optional)
- Delete everything EXCEPT ECR repositories
- Saves rebuild time if you redeploy soon
- Still incurs ~$0.50/GB/month storage

### Option 3: Keep Backups
- Export DynamoDB data before deletion
- Keep backups in S3
- Can restore later if needed

---

## Support & Reference

- **Quick Commands**: See [CLEANUP_QUICK_REFERENCE.md](CLEANUP_QUICK_REFERENCE.md)
- **Detailed Steps**: See [CLEANUP_RUNBOOK.md](CLEANUP_RUNBOOK.md)
- **Pre/During/Post Checklist**: See [CLEANUP_CHECKLIST.md](CLEANUP_CHECKLIST.md)
- **Cost Details**: See [COST_ANALYSIS.md](COST_ANALYSIS.md)

---

## Summary

✅ **Comprehensive cleanup procedure** covering all AWS and Kubernetes resources  
✅ **Both PowerShell and Bash variants** for cross-platform support  
✅ **Phase-by-phase or automated** options  
✅ **Complete verification** to ensure nothing remains  
✅ **Cost savings** of ~$450/month infrastructure  

**Status**: Ready to cleanup infrastructure safely and completely  
**Estimated Duration**: 30-45 minutes (including 10-15 min EKS deletion wait)

---

**⚠️ WARNING**: Cleanup is largely irreversible. Ensure you have proper backups before proceeding.

**Start Cleanup**: Run `./cleanup-all.ps1` or `./cleanup-all.sh`
