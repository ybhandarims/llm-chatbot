# Cleanup Runbook - Detailed Step-by-Step Procedures

**Version**: 1.0  
**Date**: May 24, 2026  
**Estimated Time**: 30-45 minutes  
**Risk Level**: Low (with proper backups)

---

## Table of Contents

1. [Pre-Cleanup Checklist](#pre-cleanup-checklist)
2. [Phase 1: Backup Data (Optional)](#phase-1-backup-data-optional)
3. [Phase 2: Delete Helm Release](#phase-2-delete-helm-release)
4. [Phase 3: Delete Kubernetes Namespace](#phase-3-delete-kubernetes-namespace)
5. [Phase 4: Delete EKS Cluster](#phase-4-delete-eks-cluster)
6. [Phase 5: Delete DynamoDB Tables](#phase-5-delete-dynamodb-tables)
7. [Phase 6: Delete SQS Queues](#phase-6-delete-sqs-queues)
8. [Phase 7: Delete ECR Repositories](#phase-7-delete-ecr-repositories)
9. [Phase 8: Delete Secrets & IAM](#phase-8-delete-secrets--iam)
10. [Phase 9: Delete CloudWatch Logs](#phase-9-delete-cloudwatch-logs)
11. [Verification & Completion](#verification--completion)

---

## Pre-Cleanup Checklist

Before proceeding with cleanup, verify the following:

### ✅ Pre-Cleanup Tasks

**PowerShell**:
```powershell
Write-Host "=== Pre-Cleanup Verification ==="

# 1. Verify you have AWS credentials
try {
    $account = aws sts get-caller-identity --query Account --output text
    Write-Host "✓ AWS Access: OK (Account: $account)"
} catch {
    Write-Host "✗ AWS Access: FAILED - Configure credentials first"
    exit
}

# 2. Verify kubectl access
try {
    kubectl cluster-info | Out-Null
    Write-Host "✓ kubectl Access: OK"
} catch {
    Write-Host "✗ kubectl Access: FAILED"
}

# 3. Verify eksctl
try {
    eksctl version | Out-Null
    Write-Host "✓ eksctl Available: OK"
} catch {
    Write-Host "✗ eksctl Not Available"
}

# 4. Verify Helm
try {
    helm version | Out-Null
    Write-Host "✓ Helm Available: OK"
} catch {
    Write-Host "✗ Helm Not Available"
}

# 5. List current resources
Write-Host "`n=== Current Resources ==="
Write-Host "Helm Releases:"
helm list -n chatbot 2>$null || Write-Host "  (none)"

Write-Host "`nKubernetes Pods:"
kubectl get pods -n chatbot 2>$null || Write-Host "  (none)"

Write-Host "`nDynamoDB Tables:"
aws dynamodb list-tables --query "TableNames[]" --output text 2>$null || Write-Host "  (none)"

Write-Host "`n⚠️  Confirm all above are correct before proceeding"
```

**Bash**:
```bash
echo "=== Pre-Cleanup Verification ==="

# 1. AWS Access
if aws sts get-caller-identity > /dev/null 2>&1; then
    echo "✓ AWS Access: OK (Account: $(aws sts get-caller-identity --query Account --output text))"
else
    echo "✗ AWS Access: FAILED"
    exit 1
fi

# 2. kubectl
if kubectl cluster-info > /dev/null 2>&1; then
    echo "✓ kubectl Access: OK"
else
    echo "✗ kubectl Access: FAILED"
fi

# 3. eksctl
if eksctl version > /dev/null 2>&1; then
    echo "✓ eksctl Available: OK"
else
    echo "✗ eksctl Not Available"
fi

# 4. Helm
if helm version > /dev/null 2>&1; then
    echo "✓ Helm Available: OK"
else
    echo "✗ Helm Not Available"
fi

echo ""
echo "=== Current Resources ==="
echo "Helm Releases:"
helm list -n chatbot 2>/dev/null || echo "  (none)"

echo ""
echo "Kubernetes Pods:"
kubectl get pods -n chatbot 2>/dev/null || echo "  (none)"

echo ""
echo "DynamoDB Tables:"
aws dynamodb list-tables --query "TableNames[]" --output text 2>/dev/null || echo "  (none)"

echo ""
echo "⚠️  Confirm all above before proceeding"
```

### ⚠️ Stop and Review Before Continuing

Make sure:
- [ ] You have proper backups (if needed)
- [ ] You've notified team members
- [ ] You understand this is mostly irreversible
- [ ] You have approval to delete resources
- [ ] AWS account is configured correctly

---

## Phase 1: Backup Data (Optional)

**Duration**: 5-10 minutes  
**Risk**: Low (read-only operations)  
**Reversibility**: N/A (creates new artifacts)

If you want to keep conversation history or other data, export from DynamoDB first:

### Step 1.1: Backup Conversations Table

**PowerShell**:
```powershell
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupFile = "./conversations-backup-$timestamp.json"

Write-Host "Exporting conversations to $backupFile..."

# Scan entire table
$result = aws dynamodb scan `
  --table-name conversations `
  --output json

# Save to file
$result | Out-File -FilePath $backupFile

Write-Host "✓ Backup created: $backupFile"
Write-Host "  Items: $($result | ConvertFrom-Json | Select-Object -ExpandProperty Count)"
```

**Bash**:
```bash
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="./conversations-backup-${TIMESTAMP}.json"

echo "Exporting conversations to $BACKUP_FILE..."

aws dynamodb scan \
  --table-name conversations \
  --output json > "$BACKUP_FILE"

echo "✓ Backup created: $BACKUP_FILE"
echo "  Size: $(wc -c < $BACKUP_FILE) bytes"
```

### Step 1.2: Backup Messages Table (Optional)

Similar to above:

```bash
aws dynamodb scan --table-name messages --output json > ./messages-backup-$(date +%Y%m%d).json
aws dynamodb scan --table-name settings --output json > ./settings-backup-$(date +%Y%m%d).json
```

---

## Phase 2: Delete Helm Release

**Duration**: 2 minutes  
**Risk**: Very Low (can reinstall immediately)  
**Reversibility**: Yes (helm install < 30 min)

### Step 2.1: Uninstall Helm Release

**PowerShell**:
```powershell
Write-Host "Uninstalling Helm release: llm-chatbot"

helm uninstall llm-chatbot -n chatbot

if ($?) {
    Write-Host "✓ Helm release deleted successfully"
} else {
    Write-Host "✗ Helm deletion failed - check error above"
    exit 1
}

# Wait for pod termination
Write-Host "Waiting for pods to terminate..."
Start-Sleep -Seconds 5

# Verify
$pods = kubectl get pods -n chatbot --output json | ConvertFrom-Json
$podCount = $pods.items.Count

if ($podCount -eq 0) {
    Write-Host "✓ All pods terminated"
} else {
    Write-Host "⚠️  $podCount pods still running - waiting longer..."
    Start-Sleep -Seconds 10
}
```

**Bash**:
```bash
echo "Uninstalling Helm release: llm-chatbot"

helm uninstall llm-chatbot -n chatbot

if [ $? -eq 0 ]; then
    echo "✓ Helm release deleted"
else
    echo "✗ Helm deletion failed"
    exit 1
fi

echo "Waiting for pods to terminate..."
sleep 5

# Check remaining pods
POD_COUNT=$(kubectl get pods -n chatbot --no-headers 2>/dev/null | wc -l)
if [ "$POD_COUNT" -eq 0 ]; then
    echo "✓ All pods terminated"
else
    echo "⚠️  $POD_COUNT pods still running"
    sleep 10
fi
```

### Step 2.2: Verify Release Deleted

**PowerShell**:
```powershell
# Check that release is gone
helm list -n chatbot

# Should show: No Helm releases with namespace "chatbot" found
Write-Host "✓ Helm verification complete"
```

**Bash**:
```bash
helm list -n chatbot || echo "✓ No Helm releases found"
```

---

## Phase 3: Delete Kubernetes Namespace

**Duration**: 3 minutes  
**Risk**: Low (contained deletion)  
**Reversibility**: Yes (namespace can be recreated)

### Step 3.1: Delete Namespace

**PowerShell**:
```powershell
Write-Host "Deleting Kubernetes namespace: chatbot"

kubectl delete namespace chatbot

if ($?) {
    Write-Host "✓ Namespace delete initiated"
} else {
    Write-Host "✗ Namespace deletion failed"
    exit 1
}

# Wait for deletion
Write-Host "Waiting for namespace deletion (may take 30-60 seconds)..."
for ($i = 0; $i -lt 60; $i++) {
    $ns = kubectl get namespace chatbot -o json 2>$null
    if (!$ns) {
        Write-Host "✓ Namespace deleted successfully"
        break
    }
    Write-Host "  [$i/60] Still deleting..."
    Start-Sleep -Seconds 1
}
```

**Bash**:
```bash
echo "Deleting Kubernetes namespace: chatbot"

kubectl delete namespace chatbot

if [ $? -eq 0 ]; then
    echo "✓ Namespace delete initiated"
else
    echo "✗ Namespace deletion failed"
    exit 1
fi

echo "Waiting for namespace deletion..."
for i in {1..60}; do
    if ! kubectl get namespace chatbot > /dev/null 2>&1; then
        echo "✓ Namespace deleted"
        break
    fi
    echo "  [$i/60] Still deleting..."
    sleep 1
done
```

### Step 3.2: Verify Namespace Deleted

**PowerShell**:
```powershell
kubectl get namespace chatbot -o json 2>&1 | Select-String "NotFound"

if ($?) {
    Write-Host "✓ Namespace completely deleted"
} else {
    Write-Host "⚠️  Namespace still exists - check cluster"
}
```

**Bash**:
```bash
if kubectl get namespace chatbot > /dev/null 2>&1; then
    echo "⚠️  Namespace still exists"
else
    echo "✓ Namespace completely deleted"
fi
```

---

## Phase 4: Delete EKS Cluster

**Duration**: 10-15 minutes ⏱️ (WAIT TIME - automated)  
**Risk**: Medium (mostly irreversible without restore)  
**Reversibility**: No (requires rebuild)  
**COST IMPACT**: **SAVES $300+/month** (main savings!)

### Step 4.1: Delete Cluster with eksctl

**PowerShell**:
```powershell
$Env:CLUSTER_NAME = "llm-chatbot"
$Env:AWS_REGION = "us-east-1"

Write-Host "=== DELETING EKS CLUSTER ==="
Write-Host "This will take 10-15 minutes..."
Write-Host "Do NOT close this terminal!"
Write-Host ""

# Delete cluster
eksctl delete cluster `
  --name $Env:CLUSTER_NAME `
  --region $Env:AWS_REGION `
  --wait

if ($?) {
    Write-Host ""
    Write-Host "✓ EKS cluster deleted successfully"
    Write-Host "  - All EC2 nodes removed"
    Write-Host "  - Control plane deleted"
    Write-Host "  - VPC/security groups cleaned up"
    Write-Host "  - IAM roles removed"
} else {
    Write-Host ""
    Write-Host "✗ EKS deletion failed - check error above"
    Write-Host "  Cluster may still exist - check AWS Console"
    exit 1
}
```

**Bash**:
```bash
export CLUSTER_NAME="llm-chatbot"
export AWS_REGION="us-east-1"

echo "=== DELETING EKS CLUSTER ==="
echo "This will take 10-15 minutes..."
echo "Do NOT close this terminal!"
echo ""

eksctl delete cluster \
  --name ${CLUSTER_NAME} \
  --region ${AWS_REGION} \
  --wait

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ EKS cluster deleted successfully"
    echo "  - All EC2 nodes removed"
    echo "  - Control plane deleted"
    echo "  - VPC/security groups cleaned up"
    echo "  - IAM roles removed"
else
    echo ""
    echo "✗ EKS deletion failed"
    exit 1
fi
```

### ⏱️ EXPECTED WAIT TIME: 10-15 MINUTES

During deletion, you'll see output like:

```
[ℹ]  deleting EKS cluster "llm-chatbot"
[ℹ]  deleting CloudFormation stack "eksctl-llm-chatbot-cluster"
[ℹ]  waiting for CloudFormation stack deletion...
[ℹ]  waiting for CloudFormation stack deletion...
...
[✔]  cluster deleted
```

**DO NOT INTERRUPT THIS PROCESS!**

### Step 4.2: Verify Cluster Deleted

**PowerShell**:
```powershell
Write-Host "Verifying cluster deletion..."

$clusters = eksctl get clusters 2>&1

if ($clusters -match "No clusters found") {
    Write-Host "✓ Cluster successfully deleted"
} else {
    Write-Host "⚠️  Cluster may still exist:"
    eksctl get clusters
}
```

**Bash**:
```bash
echo "Verifying cluster deletion..."

if eksctl get clusters 2>/dev/null | grep -q llm-chatbot; then
    echo "⚠️  Cluster still exists"
    eksctl get clusters
else
    echo "✓ Cluster successfully deleted"
fi
```

---

## Phase 5: Delete DynamoDB Tables

**Duration**: 2 minutes  
**Risk**: High (data loss)  
**Reversibility**: No (unless you have backups from Phase 1)

### Step 5.1: Delete Tables

**PowerShell**:
```powershell
$Env:AWS_REGION = "us-east-1"
$tables = @("conversations", "messages", "settings")

Write-Host "Deleting DynamoDB tables..."

foreach ($table in $tables) {
    Write-Host "  Deleting $table..."
    
    aws dynamodb delete-table `
      --table-name $table `
      --region $Env:AWS_REGION
    
    if ($?) {
        Write-Host "    ✓ $table deletion initiated"
    } else {
        Write-Host "    ✗ $table deletion failed"
    }
}

Write-Host "Waiting for table deletion..."
Start-Sleep -Seconds 5

# List remaining tables
$remaining = aws dynamodb list-tables --region $Env:AWS_REGION --query "TableNames[]" --output json | ConvertFrom-Json

if ($remaining.Count -gt 0) {
    Write-Host "⚠️  Remaining tables:"
    $remaining | ForEach-Object { Write-Host "    - $_" }
} else {
    Write-Host "✓ All DynamoDB tables deleted"
}
```

**Bash**:
```bash
export AWS_REGION="us-east-1"

echo "Deleting DynamoDB tables..."

for table in conversations messages settings; do
    echo "  Deleting $table..."
    
    aws dynamodb delete-table \
      --table-name $table \
      --region ${AWS_REGION} 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo "    ✓ $table deletion initiated"
    else
        echo "    ✗ $table deletion failed"
    fi
done

sleep 5

echo "Verifying all tables deleted..."
REMAINING=$(aws dynamodb list-tables --region ${AWS_REGION} --query "TableNames[]" --output text 2>/dev/null)

if [ -z "$REMAINING" ]; then
    echo "✓ All DynamoDB tables deleted"
else
    echo "⚠️  Remaining tables: $REMAINING"
fi
```

---

## Phase 6: Delete SQS Queues

**Duration**: 1 minute  
**Risk**: Low (no data loss risk)  
**Reversibility**: Yes (can recreate queues)

### Step 6.1: Get Queue URLs

**PowerShell**:
```powershell
$Env:AWS_REGION = "us-east-1"

Write-Host "Retrieving SQS queue URLs..."

try {
    $mainQueue = aws sqs get-queue-url `
      --queue-name ai-jobs.fifo `
      --region $Env:AWS_REGION `
      --query "QueueUrl" `
      --output text
    
    $dlq = aws sqs get-queue-url `
      --queue-name ai-jobs-dlq.fifo `
      --region $Env:AWS_REGION `
      --query "QueueUrl" `
      --output text
    
    Write-Host "  Main Queue: $mainQueue"
    Write-Host "  DLQ:        $dlq"
} catch {
    Write-Host "⚠️  Queues not found (may already be deleted)"
    return
}
```

**Bash**:
```bash
export AWS_REGION="us-east-1"

echo "Retrieving SQS queue URLs..."

MAIN_QUEUE=$(aws sqs get-queue-url \
  --queue-name ai-jobs.fifo \
  --region ${AWS_REGION} \
  --query "QueueUrl" \
  --output text 2>/dev/null)

DLQ=$(aws sqs get-queue-url \
  --queue-name ai-jobs-dlq.fifo \
  --region ${AWS_REGION} \
  --query "QueueUrl" \
  --output text 2>/dev/null)

if [ -z "$MAIN_QUEUE" ]; then
    echo "⚠️  Queues not found (may already be deleted)"
    return
fi

echo "  Main Queue: $MAIN_QUEUE"
echo "  DLQ:        $DLQ"
```

### Step 6.2: Delete Queues

**PowerShell**:
```powershell
Write-Host "Deleting SQS queues..."

aws sqs delete-queue --queue-url $mainQueue --region $Env:AWS_REGION
aws sqs delete-queue --queue-url $dlq --region $Env:AWS_REGION

Write-Host "✓ Queue deletion initiated"

# Verify
Start-Sleep -Seconds 2
$queues = aws sqs list-queues --region $Env:AWS_REGION 2>&1 | Select-String "QueueUrl"

if (!$queues) {
    Write-Host "✓ All SQS queues deleted"
} else {
    Write-Host "⚠️  Some queues still exist"
}
```

**Bash**:
```bash
echo "Deleting SQS queues..."

aws sqs delete-queue --queue-url $MAIN_QUEUE --region ${AWS_REGION}
aws sqs delete-queue --queue-url $DLQ --region ${AWS_REGION}

echo "✓ Queue deletion initiated"

sleep 2

REMAINING=$(aws sqs list-queues --region ${AWS_REGION} 2>/dev/null | grep QueueUrl)

if [ -z "$REMAINING" ]; then
    echo "✓ All SQS queues deleted"
else
    echo "⚠️  Some queues still exist"
fi
```

---

## Phase 7: Delete ECR Repositories

**Duration**: 2 minutes  
**Risk**: Medium (lose Docker images)  
**Reversibility**: Yes (can rebuild from source)

### Step 7.1: Delete Repositories

**PowerShell**:
```powershell
$Env:AWS_REGION = "us-east-1"
$services = @("frontend", "gateway", "settings", "conversations", "messages", "ai-worker")

Write-Host "Deleting ECR repositories..."

foreach ($svc in $services) {
    Write-Host "  Deleting llm-chatbot/$svc..."
    
    aws ecr delete-repository `
      --repository-name llm-chatbot/$svc `
      --force `
      --region $Env:AWS_REGION 2>$null
    
    if ($?) {
        Write-Host "    ✓ Deleted"
    } else {
        Write-Host "    ⚠️  Not found or already deleted"
    }
}

# Verify
Write-Host ""
Write-Host "Verifying all repositories deleted..."
$remaining = aws ecr describe-repositories --region $Env:AWS_REGION --query "repositories[].repositoryName" --output text 2>&1

if (!$remaining -or $remaining -match "error") {
    Write-Host "✓ All ECR repositories deleted"
} else {
    Write-Host "⚠️  Repositories found: $remaining"
}
```

**Bash**:
```bash
export AWS_REGION="us-east-1"

echo "Deleting ECR repositories..."

for service in frontend gateway settings conversations messages ai-worker; do
    echo "  Deleting llm-chatbot/$service..."
    
    aws ecr delete-repository \
      --repository-name llm-chatbot/$service \
      --force \
      --region ${AWS_REGION} 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo "    ✓ Deleted"
    else
        echo "    ⚠️  Not found"
    fi
done

sleep 2

echo ""
echo "Verifying all repositories deleted..."
REMAINING=$(aws ecr describe-repositories --region ${AWS_REGION} --query "repositories[].repositoryName" --output text 2>/dev/null)

if [ -z "$REMAINING" ]; then
    echo "✓ All ECR repositories deleted"
else
    echo "⚠️  Repositories found: $REMAINING"
fi
```

---

## Phase 8: Delete Secrets & IAM

**Duration**: 3 minutes  
**Risk**: Medium (credentials deleted)  
**Reversibility**: Partial (IAM can be recreated)

### Step 8.1: Delete Secrets Manager Secret

**PowerShell**:
```powershell
$Env:AWS_REGION = "us-east-1"

Write-Host "Deleting Secrets Manager secret..."

aws secretsmanager delete-secret `
  --secret-id llm-chatbot/openai-key `
  --force-delete-without-recovery `
  --region $Env:AWS_REGION 2>$null

if ($?) {
    Write-Host "✓ Secret deletion initiated"
} else {
    Write-Host "⚠️  Secret not found or already deleted"
}
```

**Bash**:
```bash
export AWS_REGION="us-east-1"

echo "Deleting Secrets Manager secret..."

aws secretsmanager delete-secret \
  --secret-id llm-chatbot/openai-key \
  --force-delete-without-recovery \
  --region ${AWS_REGION} 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✓ Secret deleted"
else
    echo "⚠️  Secret not found"
fi
```

### Step 8.2: Delete IAM Inline Policies

**PowerShell**:
```powershell
Write-Host "Deleting IAM inline policies..."

# Delete inline policy from workload role
aws iam delete-role-policy `
  --role-name llm-chatbot-workload `
  --policy-name llm-chatbot-inline-policy 2>$null

if ($?) {
    Write-Host "✓ Workload policy deleted"
} else {
    Write-Host "⚠️  Workload policy not found"
}
```

**Bash**:
```bash
echo "Deleting IAM inline policies..."

aws iam delete-role-policy \
  --role-name llm-chatbot-workload \
  --policy-name llm-chatbot-inline-policy 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✓ Workload policy deleted"
else
    echo "⚠️  Workload policy not found"
fi
```

### Step 8.3: Delete IAM Roles

**PowerShell**:
```powershell
Write-Host "Deleting IAM roles..."

aws iam delete-role --role-name llm-chatbot-workload 2>$null

if ($?) {
    Write-Host "✓ llm-chatbot-workload role deleted"
} else {
    Write-Host "⚠️  Role not found"
}

# Delete ALB controller policy
$accountId = aws sts get-caller-identity --query Account --output text

aws iam delete-policy `
  --policy-arn "arn:aws:iam::$accountId`:policy/AWSLoadBalancerControllerPolicy" 2>$null

if ($?) {
    Write-Host "✓ ALB controller policy deleted"
} else {
    Write-Host "⚠️  ALB policy not found"
}
```

**Bash**:
```bash
echo "Deleting IAM roles..."

aws iam delete-role --role-name llm-chatbot-workload 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✓ llm-chatbot-workload role deleted"
else
    echo "⚠️  Role not found"
fi

# Delete ALB policy
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws iam delete-policy \
  --policy-arn "arn:aws:iam::${ACCOUNT_ID}:policy/AWSLoadBalancerControllerPolicy" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✓ ALB controller policy deleted"
else
    echo "⚠️  ALB policy not found"
fi
```

---

## Phase 9: Delete CloudWatch Logs

**Duration**: 1 minute  
**Risk**: Low (logs can be archived externally)  
**Reversibility**: No (logs are permanent unless archived)

### Step 9.1: Delete Log Groups

**PowerShell**:
```powershell
$Env:AWS_REGION = "us-east-1"

Write-Host "Finding CloudWatch log groups..."

$logGroups = aws logs describe-log-groups `
  --region $Env:AWS_REGION `
  --query "logGroups[?contains(logGroupName, 'llm-chatbot')].logGroupName" `
  --output json | ConvertFrom-Json

if ($logGroups.Count -gt 0) {
    Write-Host "Deleting $($logGroups.Count) log group(s)..."
    
    foreach ($lg in $logGroups) {
        Write-Host "  Deleting $lg..."
        
        aws logs delete-log-group `
          --log-group-name $lg `
          --region $Env:AWS_REGION
        
        if ($?) {
            Write-Host "    ✓ Deleted"
        }
    }
    
    Write-Host "✓ All log groups deleted"
} else {
    Write-Host "✓ No log groups found"
}
```

**Bash**:
```bash
export AWS_REGION="us-east-1"

echo "Finding CloudWatch log groups..."

LOG_GROUPS=$(aws logs describe-log-groups \
  --region ${AWS_REGION} \
  --query "logGroups[?contains(logGroupName, 'llm-chatbot')].logGroupName" \
  --output text)

if [ -n "$LOG_GROUPS" ]; then
    echo "Deleting log group(s)..."
    
    for lg in $LOG_GROUPS; do
        echo "  Deleting $lg..."
        
        aws logs delete-log-group \
          --log-group-name "$lg" \
          --region ${AWS_REGION}
        
        if [ $? -eq 0 ]; then
            echo "    ✓ Deleted"
        fi
    done
    
    echo "✓ All log groups deleted"
else
    echo "✓ No log groups found"
fi
```

---

## Verification & Completion

**Duration**: 5 minutes

Run all verification commands to ensure complete cleanup:

**PowerShell**:
```powershell
Write-Host "========== CLEANUP VERIFICATION ==========="
Write-Host ""

$Env:AWS_REGION = "us-east-1"
$allClean = $true

# 1. EKS Clusters
Write-Host "1. EKS Clusters:"
$clusters = eksctl get clusters 2>&1
if ($clusters -match "No clusters found" -or $clusters -match "error") {
    Write-Host "   ✓ No clusters"
} else {
    Write-Host "   ✗ Clusters found:"
    Write-Host $clusters
    $allClean = $false
}

# 2. DynamoDB Tables
Write-Host ""
Write-Host "2. DynamoDB Tables:"
$tables = aws dynamodb list-tables --region $Env:AWS_REGION --query "TableNames[]" --output text 2>&1
if (!$tables -or $tables -match "error") {
    Write-Host "   ✓ No tables"
} else {
    Write-Host "   ✗ Tables found: $tables"
    $allClean = $false
}

# 3. SQS Queues
Write-Host ""
Write-Host "3. SQS Queues:"
$queues = aws sqs list-queues --region $Env:AWS_REGION --output json 2>&1 | Select-String "QueueUrl"
if (!$queues) {
    Write-Host "   ✓ No queues"
} else {
    Write-Host "   ✗ Queues found"
    $allClean = $false
}

# 4. ECR Repositories
Write-Host ""
Write-Host "4. ECR Repositories:"
$repos = aws ecr describe-repositories --region $Env:AWS_REGION --output json 2>&1 | Select-String "repositoryName"
if (!$repos -or $repos -match "error") {
    Write-Host "   ✓ No repositories"
} else {
    Write-Host "   ✗ Repositories found"
    $allClean = $false
}

# 5. IAM Roles
Write-Host ""
Write-Host "5. IAM Roles:"
$roles = aws iam list-roles --query "Roles[?contains(RoleName, 'chatbot')].RoleName" --output text 2>&1
if (!$roles -or $roles -match "error") {
    Write-Host "   ✓ No chatbot roles"
} else {
    Write-Host "   ✗ Roles found: $roles"
    $allClean = $false
}

# 6. Secrets
Write-Host ""
Write-Host "6. Secrets Manager:"
$secrets = aws secretsmanager list-secrets --region $Env:AWS_REGION --query "SecretList[?contains(Name, 'llm-chatbot')].Name" --output text 2>&1
if (!$secrets -or $secrets -match "error") {
    Write-Host "   ✓ No secrets"
} else {
    Write-Host "   ✗ Secrets found: $secrets"
    $allClean = $false
}

# 7. Log Groups
Write-Host ""
Write-Host "7. CloudWatch Logs:"
$logs = aws logs describe-log-groups --region $Env:AWS_REGION --query "logGroups[?contains(logGroupName, 'llm-chatbot')].logGroupName" --output text 2>&1
if (!$logs -or $logs -match "error") {
    Write-Host "   ✓ No log groups"
} else {
    Write-Host "   ✗ Log groups found"
    $allClean = $false
}

# Summary
Write-Host ""
Write-Host "=========================================="
if ($allClean) {
    Write-Host "✅ CLEANUP COMPLETE - All resources deleted!"
    Write-Host ""
    Write-Host "Cost Savings:"
    Write-Host "  - EKS:        $73/month"
    Write-Host "  - EC2:        $300/month"
    Write-Host "  - DynamoDB:   $30/month"
    Write-Host "  - SQS:        $5/month"
    Write-Host "  - CloudWatch: $20/month"
    Write-Host "  - Transfer:   $20/month"
    Write-Host "  ─────────────────────"
    Write-Host "  TOTAL:        $450/month saved!"
} else {
    Write-Host "⚠️  CLEANUP INCOMPLETE - Some resources remain"
    Write-Host "    Please check AWS Console for manual cleanup"
}
```

**Bash**:
```bash
echo "========== CLEANUP VERIFICATION ==========="
echo ""

export AWS_REGION="us-east-1"
ALL_CLEAN=true

# 1. EKS Clusters
echo "1. EKS Clusters:"
if ! eksctl get clusters 2>/dev/null | grep -q llm-chatbot; then
    echo "   ✓ No clusters"
else
    echo "   ✗ Clusters found"
    ALL_CLEAN=false
fi

# 2. DynamoDB
echo ""
echo "2. DynamoDB Tables:"
if [ -z "$(aws dynamodb list-tables --region ${AWS_REGION} --query "TableNames[]" --output text 2>/dev/null | grep -E '(conversations|messages|settings)')" ]; then
    echo "   ✓ No tables"
else
    echo "   ✗ Tables found"
    ALL_CLEAN=false
fi

# 3. SQS
echo ""
echo "3. SQS Queues:"
if [ -z "$(aws sqs list-queues --region ${AWS_REGION} --output json 2>/dev/null | grep QueueUrl)" ]; then
    echo "   ✓ No queues"
else
    echo "   ✗ Queues found"
    ALL_CLEAN=false
fi

# 4. ECR
echo ""
echo "4. ECR Repositories:"
if [ -z "$(aws ecr describe-repositories --region ${AWS_REGION} --query "repositories[*].repositoryName" --output text 2>/dev/null | grep llm-chatbot)" ]; then
    echo "   ✓ No repositories"
else
    echo "   ✗ Repositories found"
    ALL_CLEAN=false
fi

# 5. IAM
echo ""
echo "5. IAM Roles:"
if [ -z "$(aws iam list-roles --query "Roles[?contains(RoleName, 'chatbot')].RoleName" --output text 2>/dev/null)" ]; then
    echo "   ✓ No chatbot roles"
else
    echo "   ✗ Roles found"
    ALL_CLEAN=false
fi

# 6. Secrets
echo ""
echo "6. Secrets Manager:"
if [ -z "$(aws secretsmanager list-secrets --region ${AWS_REGION} --query "SecretList[?contains(Name, 'llm-chatbot')].Name" --output text 2>/dev/null)" ]; then
    echo "   ✓ No secrets"
else
    echo "   ✗ Secrets found"
    ALL_CLEAN=false
fi

# 7. Logs
echo ""
echo "7. CloudWatch Logs:"
if [ -z "$(aws logs describe-log-groups --region ${AWS_REGION} --query "logGroups[?contains(logGroupName, 'llm-chatbot')].logGroupName" --output text 2>/dev/null)" ]; then
    echo "   ✓ No log groups"
else
    echo "   ✗ Log groups found"
    ALL_CLEAN=false
fi

# Summary
echo ""
echo "=========================================="
if [ "$ALL_CLEAN" = true ]; then
    echo "✅ CLEANUP COMPLETE - All resources deleted!"
    echo ""
    echo "Cost Savings:"
    echo "  - EKS:        \$73/month"
    echo "  - EC2:        \$300/month"
    echo "  - DynamoDB:   \$30/month"
    echo "  - SQS:        \$5/month"
    echo "  - CloudWatch: \$20/month"
    echo "  - Transfer:   \$20/month"
    echo "  ─────────────────────"
    echo "  TOTAL:        \$450/month saved!"
else
    echo "⚠️  CLEANUP INCOMPLETE - Some resources remain"
    echo "    Check AWS Console for manual cleanup"
fi
```

---

## Post-Cleanup Steps

### Step 1: Remove Local kubeconfig Context

**PowerShell**:
```powershell
kubectl config delete-context arn:aws:eks:us-east-1:ACCOUNT_ID:cluster/llm-chatbot
```

**Bash**:
```bash
kubectl config delete-context arn:aws:eks:us-east-1:ACCOUNT_ID:cluster/llm-chatbot
```

### Step 2: Archive Backups (if created)

```bash
# Create backup archive
tar -czf llm-chatbot-backups-$(date +%Y%m%d).tar.gz *-backup*.json

# Move to safe location
mv llm-chatbot-backups-*.tar.gz ~/backups/
```

### Step 3: Verify No Charges

- Check AWS Cost Explorer
- Wait 24 hours for charges to reflect
- Confirm EKS/EC2 charges stopped
- Monitor DynamoDB, SQS, CloudWatch

---

## Cleanup Complete! ✅

**Resources Deleted**:
- ✅ EKS Cluster
- ✅ EC2 Nodes
- ✅ DynamoDB Tables
- ✅ SQS Queues
- ✅ ECR Repositories
- ✅ IAM Roles
- ✅ Secrets Manager Secrets
- ✅ CloudWatch Logs

**Monthly Savings**: ~$450/month infrastructure cost

---

**Status**: Cleanup procedures complete  
**Next Action**: Run verification commands to confirm all resources deleted  
**Support**: Check CLEANUP_QUICK_REFERENCE.md for troubleshooting
