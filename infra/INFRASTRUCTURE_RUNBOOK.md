# LLM Chatbot Infrastructure Implementation Runbook

**Version**: 2.0  
**Date**: May 24, 2026  
**Duration**: 4-6 hours (including EKS cluster creation wait time) + 5 minutes for Phase 0  
**Last Updated**: May 26, 2026 (Updated Step 6.5 with IRSA verification method)

## Table of Contents

0. [Phase 0: Code Repository Setup](#phase-0-code-repository-setup) ⭐ **START HERE**
1. [Prerequisites](#prerequisites)
2. [Architecture Overview](#architecture-overview)
3. [Phase 1: Environment Setup](#phase-1-environment-setup)
4. [Phase 2: AWS Configuration](#phase-2-aws-configuration)
5. [Phase 3: Container Registry Setup](#phase-3-container-registry-setup)
6. [Phase 4: EKS Cluster Creation](#phase-4-eks-cluster-creation)
7. [Phase 5: Helm Deployment](#phase-5-helm-deployment)
8. [Phase 6: AWS Service Integration](#phase-6-aws-service-integration)
9. [Phase 7: Production Testing](#phase-7-production-testing)
10. [Phase 8: Monitoring & Observability](#phase-8-monitoring--observability)
11. [Troubleshooting Guide](#troubleshooting-guide)
12. [Rollback Procedures](#rollback-procedures)
13. [Post-Deployment](#post-deployment)

---

## Prerequisites

### Required Tools & Source Code

```bash
# Verify all tools are installed
aws --version              # AWS CLI v2+
eksctl version             # eksctl 0.170+
kubectl version --client   # kubectl 1.29+
helm version               # Helm 3.12+
docker --version           # Docker 24.0+
git --version              # Git (for cloning repository)
jq --version               # jq 1.6+ (optional)

# Source code repository
# This runbook assumes the llm-chatbot repository is cloned
# All phases reference files from this repository:
# - microservices/     (Dockerfiles for 6 services)
# - infra/             (EKS cluster config, Helm charts)
# - docker-compose.yml (reference for local development)
```

### Installing Tools on Ubuntu/Linux EC2

If running on Ubuntu/Linux EC2 and any tools are missing, install them:

```bash
# Update package manager
sudo apt-get update

# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
aws --version

# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
kubectl version --client

# Install eksctl
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
eksctl version

# Install Helm (3.12+) - REQUIRED for Phase 4.4
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
helm version

# Install Docker
sudo apt-get install -y docker.io
sudo usermod -aG docker $USER
newgrp docker
docker --version

# Install jq (optional, for JSON parsing)
sudo apt-get install -y jq
jq --version

# Verify all tools
echo "✓ All tools installed. Verify:"
aws --version && eksctl version && kubectl version --client && helm version && docker --version && git --version
```

### AWS Account Requirements

```
- AWS Account ID: _________________
- Region: us-east-1 (change if needed)
- IAM Permissions: Admin or EC2, EKS, IAM, DynamoDB, SQS, CloudWatch
- Billing enabled and budget monitoring set up
- VPC with sufficient quota
```

### Service Accounts & Credentials

```
- AWS Access Key ID: _________________
- AWS Secret Access Key: _________________
- OpenAI API Key: _________________
- GitHub token (optional): _________________
```

### System Requirements

```
- Minimum compute: 8GB RAM, 2 vCPU
- Disk space: 20GB free
- Network: Stable internet connection
- Time zone considerations if using CloudWatch
```

---

## Architecture Overview

### Budget-Conscious Production Architecture

```
Users
  ↓
AWS WAF (optional) 
  ↓
AWS ALB (Application Load Balancer)
  ↓
EKS Cluster (Multi-AZ)
├─ Namespace: chatbot
├─ Node Pools:
│  ├─ system-pool (1-3 nodes, t3.medium)
│  ├─ api-pool (2-5 nodes, t3.medium)
│  └─ ai-worker-pool (1-5 nodes, t3.medium)
└─ Services (6 microservices):
   ├─ Frontend (Nginx)
   ├─ Gateway (API Orchestration)
   ├─ Settings Service
   ├─ Conversations Service
   ├─ Messages Service
   └─ AI Worker (Background Job)
  ↓
AWS Services:
├─ DynamoDB (conversations, messages, settings tables)
├─ SQS (ai-jobs.fifo queue, ai-jobs-dlq.fifo DLQ)
├─ Secrets Manager (credentials)
├─ CloudWatch (logging, metrics)
├─ IAM (IRSA/Pod Identity)
└─ ECR (container images)
```

### Cost Optimization Strategy

| Component | Budget Conscious Choice | Reason |
|-----------|------------------------|--------|
| Frontend | Nginx on EKS (not CloudFront) | Simple, regional users OK |
| Database | DynamoDB (pay-per-request) | No operational overhead |
| Compute | t3.medium, auto-scaling | Sufficient for MVP, cost-effective |
| Node Scaling | HPA for pods, EKS auto scaling for nodes | Right-size dynamically |
| Logging | CloudWatch (7-day retention) | Integrated, affordable |
| AI Cost | Optimize prompts, use cheaper models | Main cost driver, not infra |

---

## Phase 0: Code Repository Setup ⭐ **START HERE**

**Duration**: 5 minutes  
**Goal**: Clone the source code repository and verify directory structure

### ⚠️ **CRITICAL: This Phase Must Be Completed First**

All subsequent phases reference files from this repository:
- **microservices/** = Source code and Dockerfiles for all 6 services
- **infra/eksctl/** = EKS cluster configuration (cluster.yaml)
- **infra/helm/chatapp/** = Helm charts for Kubernetes deployment
- **infra/scripts/** = Utility scripts for deployment

**Without this step, you won't have access to Dockerfiles, cluster configs, or deployment charts.**

### Step 0.1: Clone Repository

**Bash (Linux/macOS)**:
```bash
# Create a working directory
mkdir -p ~/projects
cd ~/projects

# Clone the repository
git clone https://github.com/your-org/llm-chatbot.git
cd llm-chatbot

# Expected output:
# Cloning into 'llm-chatbot'...
# remote: Enumerating objects...
# Receiving objects: 100%...
```

**PowerShell (Windows)**:
```powershell
# Create working directory
New-Item -ItemType Directory -Path "$Env:USERPROFILE\projects" -Force
cd "$Env:USERPROFILE\projects"

# Clone repository
git clone https://github.com/your-org/llm-chatbot.git
cd llm-chatbot

# Alternative: using SSH
git clone git@github.com:your-org/llm-chatbot.git
cd llm-chatbot
```

### Step 0.2: Verify Directory Structure

```bash
# List the main directory structure
ls -la

# Expected output:
# ├── infra/                      (Infrastructure code)
# │   ├── README.md              (Infrastructure overview)
# │   ├── INFRASTRUCTURE_RUNBOOK.md (This file!)
# │   ├── eksctl/                (EKS cluster configuration)
# │   │   └── cluster.yaml       (Cluster definition)
# │   ├── helm/                  (Kubernetes deployment charts)
# │   │   └── chatapp/
# │   │       ├── Chart.yaml
# │   │       ├── values.yaml
# │   │       └── templates/    (K8s manifests)
# │   ├── scripts/               (Deployment utilities)
# │   │   └── push-images.sh
# │   └── cleanup/               (Cleanup documentation)
# ├── microservices/             (Application code - CRITICAL)
# │   ├── README.md
# │   ├── docker-compose.yml    (Local dev reference)
# │   ├── frontend/
# │   │   ├── Dockerfile        ← Needed for Phase 3
# │   │   ├── package.json
# │   │   └── public/
# │   ├── gateway/
# │   │   ├── Dockerfile        ← Needed for Phase 3
# │   │   ├── main.py
# │   │   └── requirements.txt
# │   ├── ai-service/
# │   │   ├── Dockerfile        ← Needed for Phase 3
# │   │   ├── main.py
# │   │   └── requirements.txt
# │   ├── conversations-service/
# │   ├── messages-service/
# │   ├── settings-service/
# │   └── scripts/
# ├── monolithic_app/            (Reference implementation)
# │   ├── backend/
# │   ├── frontend/
# │   └── README.md
# └── docker-compose.yml        (Local development - optional)
```

**Verify critical files exist**:
```bash
# Check for all Dockerfiles
find microservices -name "Dockerfile" -type f
# Expected: 6 Dockerfiles

# Check for Helm chart
ls -la infra/helm/chatapp/
# Expected: Chart.yaml, values.yaml, templates/

# Check for EKS config
ls -la infra/eksctl/
# Expected: cluster.yaml
```

### Step 0.3: Set Repository Root Path

**Bash**:
```bash
# Export repository path for use in other phases
export REPO_ROOT=$(pwd)
echo "Repository root: $REPO_ROOT"

# Verify - should output the full path
echo $REPO_ROOT
# Example output: /home/ec2-user/llm-chatbot
# or: /Users/yourname/projects/llm-chatbot
# or: C:\Users\YourName\projects\llm-chatbot (PowerShell)
```

**PowerShell**:
```powershell
# Set repository root
$Env:REPO_ROOT = (Get-Location).Path
Write-Host "Repository root: $Env:REPO_ROOT"

# Verify
Write-Host $Env:REPO_ROOT
# Example output: C:\Users\YourName\projects\llm-chatbot
```

**Important**: Keep this terminal open or set it as persistent environment variable:
```bash
# Bash - Add to ~/.bashrc or ~/.zshrc
echo 'export REPO_ROOT=/path/to/llm-chatbot' >> ~/.bashrc

# PowerShell - Add to profile
# Go to $PROFILE path and add: $Env:REPO_ROOT = "C:\Users\...\llm-chatbot"
```

### Step 0.4: Quick Verification Checklist

```bash
# ✓ Repository cloned
test -d .git && echo "✓ Git repository found" || echo "✗ Git repository NOT found"

# ✓ Source code present
test -d microservices && echo "✓ Microservices directory found" || echo "✗ Microservices NOT found"

# ✓ Infrastructure files present
test -f infra/eksctl/cluster.yaml && echo "✓ EKS cluster config found" || echo "✗ EKS config NOT found"
test -d infra/helm/chatapp && echo "✓ Helm chart found" || echo "✗ Helm chart NOT found"

# ✓ All Dockerfiles present
test $(find microservices -name "Dockerfile" | wc -l) -eq 6 && echo "✓ All 6 Dockerfiles found" || echo "✗ Missing Dockerfiles"

# ✓ Verify current directory
pwd
# Should output path to llm-chatbot
```

✅ **Success Criteria**:
- Repository cloned successfully
- All 6 microservices present in `microservices/`
- Helm charts present in `infra/helm/chatapp/`
- EKS cluster config present in `infra/eksctl/cluster.yaml`
- Repository root path exported (REPO_ROOT variable set)

⚠️ **Do NOT proceed to Phase 1 until all checks above pass**

---

## Phase 1: Environment Setup

**Duration**: 10 minutes  
**Goal**: Configure local environment and AWS credentials

### Step 1.1: Configure AWS Credentials

**PowerShell (Windows)**:
```powershell
# Set AWS credentials
$Env:AWS_ACCESS_KEY_ID = "AKIA..."
$Env:AWS_SECRET_ACCESS_KEY = "wJa..."
$Env:AWS_REGION = "us-east-1"

# Verify
aws sts get-caller-identity

# Expected output
#{
#    "UserId": "AIDAI...",
#    "Account": "123456789012",
#    "Arn": "arn:aws:iam::123456789012:user/your-user"
#}
```

**Bash (macOS/Linux)**:
```bash
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="wJa..."
export AWS_REGION="us-east-1"

# Verify
aws sts get-caller-identity
```

### Step 1.2: Set Environment Variables

**PowerShell**:
```powershell
$Env:AWS_ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text)
$Env:AWS_REGION = "us-east-1"
$Env:CLUSTER_NAME = "llm-chatbot"
$Env:ECR_REGISTRY = "$Env:AWS_ACCOUNT_ID.dkr.ecr.$Env:AWS_REGION.amazonaws.com"
$Env:OPENAI_API_KEY = Read-Host -AsSecureString "Enter OPENAI API key" | ConvertFrom-SecureString

# Display for verification
echo "Account: $Env:AWS_ACCOUNT_ID"
echo "Region: $Env:AWS_REGION"
echo "Cluster: $Env:CLUSTER_NAME"
echo "Registry: $Env:ECR_REGISTRY"
```

**Bash**:
```bash
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION="us-east-1"
export CLUSTER_NAME="llm-chatbot"
export ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
read -s -p "Enter OPENAI API key: " OPENAI_API_KEY
export OPENAI_API_KEY

# Display for verification
echo "Account: $AWS_ACCOUNT_ID"
echo "Region: $AWS_REGION"
echo "Cluster: $CLUSTER_NAME"
echo "Registry: $ECR_REGISTRY"
```

**Expected output**: 
- Account ID displayed
- Region: us-east-1
- Cluster: llm-chatbot
- Registry URL: `123456789012.dkr.ecr.us-east-1.amazonaws.com`

✅ **Success Criteria**: All environment variables set and verified

---

## Phase 2: AWS Configuration

**Duration**: 15 minutes  
**Goal**: Configure AWS services (DynamoDB, SQS, IAM)

### Step 2.1: Create DynamoDB Tables

**PowerShell**:
```powershell
# Create conversations table with TTL
aws dynamodb create-table `
  --table-name conversations `
  --attribute-definitions `
    AttributeName=user_id,AttributeType=S `
    AttributeName=conversation_id,AttributeType=S `
  --key-schema `
    AttributeName=user_id,KeyType=HASH `
    AttributeName=conversation_id,KeyType=RANGE `
  --billing-mode PAY_PER_REQUEST `
  --region $Env:AWS_REGION

# Create messages table with TTL
aws dynamodb create-table `
  --table-name messages `
  --attribute-definitions `
    AttributeName=conversation_id,AttributeType=S `
    AttributeName=message_id,AttributeType=S `
  --key-schema `
    AttributeName=conversation_id,KeyType=HASH `
    AttributeName=message_id,KeyType=RANGE `
  --billing-mode PAY_PER_REQUEST `
  --region $Env:AWS_REGION

# Create settings table
aws dynamodb create-table `
  --table-name settings `
  --attribute-definitions `
    AttributeName=user_id,AttributeType=S `
    AttributeName=setting_key,AttributeType=S `
  --key-schema `
    AttributeName=user_id,KeyType=HASH `
    AttributeName=setting_key,KeyType=RANGE `
  --billing-mode PAY_PER_REQUEST `
  --region $Env:AWS_REGION

# ⏱️ Wait 30 seconds for tables to be created
Write-Host "Waiting for tables to be active..."
Start-Sleep -Seconds 30

# Enable TTL on conversations table (auto-cleanup after 90 days)
aws dynamodb update-time-to-live `
  --table-name conversations `
  --time-to-live-specification AttributeName=ttl,Enabled=true `
  --region $Env:AWS_REGION

Write-Host "Conversations table TTL enabled (90-day auto-cleanup)"

# Enable TTL on messages table (auto-cleanup after 90 days)
aws dynamodb update-time-to-live `
  --table-name messages `
  --time-to-live-specification AttributeName=ttl,Enabled=true `
  --region $Env:AWS_REGION

Write-Host "Messages table TTL enabled (90-day auto-cleanup)"

# Verify tables created
aws dynamodb list-tables --region $Env:AWS_REGION
```

**Bash**:
```bash
# Create conversations table with TTL
aws dynamodb create-table \
  --table-name conversations \
  --attribute-definitions \
    AttributeName=user_id,AttributeType=S \
    AttributeName=conversation_id,AttributeType=S \
  --key-schema \
    AttributeName=user_id,KeyType=HASH \
    AttributeName=conversation_id,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region ${AWS_REGION}

# Create messages table with TTL
aws dynamodb create-table \
  --table-name messages \
  --attribute-definitions \
    AttributeName=conversation_id,AttributeType=S \
    AttributeName=message_id,AttributeType=S \
  --key-schema \
    AttributeName=conversation_id,KeyType=HASH \
    AttributeName=message_id,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region ${AWS_REGION}

# Create settings table
aws dynamodb create-table \
  --table-name settings \
  --attribute-definitions \
    AttributeName=user_id,AttributeType=S \
    AttributeName=setting_key,AttributeType=S \
  --key-schema \
    AttributeName=user_id,KeyType=HASH \
    AttributeName=setting_key,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region ${AWS_REGION}

# Wait for tables
echo "Waiting for tables to be active (30 seconds)..."
sleep 30

# Enable TTL on conversations (auto-delete after 90 days = 7,776,000 seconds)
aws dynamodb update-time-to-live \
  --table-name conversations \
  --time-to-live-specification AttributeName=ttl,Enabled=true \
  --region ${AWS_REGION}

echo "Conversations table TTL enabled (90-day auto-cleanup)"

# Enable TTL on messages (auto-delete after 90 days)
aws dynamodb update-time-to-live \
  --table-name messages \
  --time-to-live-specification AttributeName=ttl,Enabled=true \
  --region ${AWS_REGION}

echo "Messages table TTL enabled (90-day auto-cleanup)"

# Verify tables created
aws dynamodb list-tables --region ${AWS_REGION}
```

**Expected output**:
```
{
    "TableNames": [
        "conversations",
        "messages",
        "settings"
    ]
}
```

**⏱️ Wait 30 seconds** for tables to be fully active.

### Step 2.2: Create SQS FIFO Queues

**PowerShell**:
```powershell
# Create main FIFO queue for AI job processing
aws sqs create-queue `
  --queue-name ai-jobs.fifo `
  --attributes @(
    "FifoQueue=true",
    "VisibilityTimeout=30",
    "MessageRetentionPeriod=345600",
    "ContentBasedDeduplication=true"
  ) `
  --region $Env:AWS_REGION

Write-Host "✓ Main queue ai-jobs.fifo created"
Write-Host "  - FIFO ordering enabled (per MessageGroupId)"
Write-Host "  - Visibility timeout: 30 seconds (for worker processing)"
Write-Host "  - Message retention: 4 days (345,600 seconds)"
Write-Host "  - Content-based deduplication: Enabled"
Write-Host "  - Throughput: Standard FIFO (PER_MESSAGE_PER_SECOND)"

# Create Dead Letter Queue for failed jobs
aws sqs create-queue `
  --queue-name ai-jobs-dlq.fifo `
  --attributes @(
    "FifoQueue=true",
    "VisibilityTimeout=60",
    "MessageRetentionPeriod=1209600",
    "ContentBasedDeduplication=true"
  ) `
  --region $Env:AWS_REGION

Write-Host "✓ Dead Letter Queue ai-jobs-dlq.fifo created"
Write-Host "  - For jobs that failed max retries (3 attempts)"
Write-Host "  - Message retention: 14 days"
Write-Host "  - Used for monitoring and debugging"

# Get queue URLs for later use
$MAIN_QUEUE=$(aws sqs get-queue-url --queue-name ai-jobs.fifo --region $Env:AWS_REGION --query QueueUrl --output text)
$DLQ=$(aws sqs get-queue-url --queue-name ai-jobs-dlq.fifo --region $Env:AWS_REGION --query QueueUrl --output text)

Write-Host ""
Write-Host "Queue URLs (save for Phase 5):"
Write-Host "Main Queue: $MAIN_QUEUE"
Write-Host "DLQ: $DLQ"
```

**Bash**:
```bash
# Create main FIFO queue for AI job processing
aws sqs create-queue \
  --queue-name ai-jobs.fifo \
  --attributes FifoQueue=true,VisibilityTimeout=30,MessageRetentionPeriod=345600,ContentBasedDeduplication=true \
  --region ${AWS_REGION}

echo "✓ Main queue ai-jobs.fifo created"
echo "  - FIFO ordering enabled (per MessageGroupId = user_id)"
echo "  - Visibility timeout: 30 seconds (for AI worker processing)"
echo "  - Message retention: 4 days (345,600 seconds)"
echo "  - Content-based deduplication: Enabled"
echo "  - Throughput: Standard FIFO (PER_MESSAGE_PER_SECOND)"

# Create Dead Letter Queue for failed jobs (after 3 retries)
aws sqs create-queue \
  --queue-name ai-jobs-dlq.fifo \
  --attributes FifoQueue=true,VisibilityTimeout=60,MessageRetentionPeriod=1209600,ContentBasedDeduplication=true \
  --region ${AWS_REGION}

echo "✓ Dead Letter Queue ai-jobs-dlq.fifo created"
echo "  - For jobs that failed max retries (3 attempts per message)"
echo "  - Message retention: 14 days for investigation"
echo "  - Used for monitoring and debugging failed requests"

# Get queue URLs
MAIN_QUEUE=$(aws sqs get-queue-url --queue-name ai-jobs.fifo --region ${AWS_REGION} --query QueueUrl --output text)
DLQ=$(aws sqs get-queue-url --queue-name ai-jobs-dlq.fifo --region ${AWS_REGION} --query QueueUrl --output text)

echo ""
echo "Queue URLs (save for Phase 5):"
echo "Main Queue: $MAIN_QUEUE"
echo "DLQ: $DLQ"
```

**Expected output**:
```
Main Queue: https://sqs.us-east-1.amazonaws.com/123456789012/ai-jobs.fifo
DLQ: https://sqs.us-east-1.amazonaws.com/123456789012/ai-jobs-dlq.fifo
```

### Step 2.3: Create Secrets Manager Secret

**PowerShell**:
```powershell
# Create secret for OpenAI API key
aws secretsmanager create-secret `
  --name llm-chatbot/openai-key `
  --description "OpenAI API key for LLM chatbot" `
  --secret-string $Env:OPENAI_API_KEY `
  --region $Env:AWS_REGION

# Verify secret created
aws secretsmanager describe-secret `
  --secret-id llm-chatbot/openai-key `
  --region $Env:AWS_REGION
```

**Bash**:
```bash
# Create secret
aws secretsmanager create-secret \
  --name llm-chatbot/openai-key \
  --description "OpenAI API key for LLM chatbot" \
  --secret-string "$OPENAI_API_KEY" \
  --region ${AWS_REGION}

# Verify
aws secretsmanager describe-secret \
  --secret-id llm-chatbot/openai-key \
  --region ${AWS_REGION}
```

✅ **Success Criteria**:
- 3 DynamoDB tables created and ACTIVE
- 2 SQS queues created
- Secret stored in Secrets Manager

---

## Phase 3: Container Registry Setup

**Duration**: 20 minutes  
**Goal**: Create ECR repositories and push images

### Step 3.1: Create ECR Repositories

**PowerShell**:
```powershell
# Create repositories for all 6 services
$services = @("frontend", "gateway", "settings", "conversations", "messages", "ai-worker")

foreach ($service in $services) {
    aws ecr create-repository `
      --repository-name llm-chatbot/$service `
      --region $Env:AWS_REGION `
      --image-scanning-configuration scanOnPush=true `
      --encryption-configuration encryptionType=AES256
    
    echo "Created repository: llm-chatbot/$service"
}

# Verify repositories created
aws ecr describe-repositories --region $Env:AWS_REGION
```

**Bash**:
```bash
# Create repositories
for service in frontend gateway settings conversations messages ai-worker; do
    aws ecr create-repository \
      --repository-name llm-chatbot/$service \
      --region ${AWS_REGION} \
      --image-scanning-configuration scanOnPush=true \
      --encryption-configuration encryptionType=AES256
    
    echo "Created repository: llm-chatbot/$service"
done

# Verify
aws ecr describe-repositories --region ${AWS_REGION}
```

**Expected output**:
```
6 repositories created:
- llm-chatbot/frontend
- llm-chatbot/gateway
- llm-chatbot/settings
- llm-chatbot/conversations
- llm-chatbot/messages
- llm-chatbot/ai-worker
```

### Step 3.2: Login to ECR

**PowerShell**:
```powershell
# Get login token and login to Docker
aws ecr get-login-password --region $Env:AWS_REGION | `
  docker login --username AWS --password-stdin $Env:ECR_REGISTRY

# Expected: Login Succeeded
```

**Bash**:
```bash
# Login to ECR
aws ecr get-login-password --region ${AWS_REGION} | \
  docker login --username AWS --password-stdin ${ECR_REGISTRY}
```

**Expected output**: `Login Succeeded`

### Step 3.3: Build and Push Images

**From repository root** (where docker-compose.yml is):

⚠️ **IMPORTANT**: 
- **Windows users**: Use the **PowerShell** section below
- **Linux/macOS/Ubuntu EC2 users**: Use the **Bash** section below (do NOT use PowerShell code on Linux)

**PowerShell** (Windows only):
```powershell
cd .\microservices

$services = @(
    @{name="frontend"; context="."},
    @{name="gateway"; context="./gateway"},
    @{name="settings"; context="./settings-service"},
    @{name="conversations"; context="./conversations-service"},
    @{name="messages"; context="./messages-service"},
    @{name="ai-worker"; context="./ai-service"}
)

foreach ($svc in $services) {
    $localImage = "llm-chatbot/$($svc.name)"
    $ecrImage = "$Env:ECR_REGISTRY/$localImage"

    docker build -t "$localImage:latest" -t "$localImage:v1" $svc.context
    docker tag "$localImage:latest" "$ecrImage:latest"
    docker tag "$localImage:v1" "$ecrImage:v1"
    docker push "$ecrImage:latest"
    docker push "$ecrImage:v1"
}
```

**Bash**:
```bash
cd ./microservices

# Build and push
for service in frontend gateway settings-service conversations-service messages-service ai-service; do
    SERVICE_NAME=$(echo $service | sed 's/-service//')
    if [ "$service" = "frontend" ]; then
        SERVICE_NAME="frontend"
        CONTEXT="."
    elif [ "$service" = "gateway" ]; then
        CONTEXT="./gateway"
    else
        CONTEXT="./$service"
    fi
    
    IMAGE_NAME="llm-chatbot/$SERVICE_NAME"
    
    echo "Building $IMAGE_NAME..."
    docker build -t ${IMAGE_NAME}:latest -t ${IMAGE_NAME}:v1 $CONTEXT
    
    docker tag ${IMAGE_NAME}:latest ${ECR_REGISTRY}/${IMAGE_NAME}:latest
    docker tag ${IMAGE_NAME}:v1 ${ECR_REGISTRY}/${IMAGE_NAME}:v1
    
    echo "Pushing to ECR..."
    docker push ${ECR_REGISTRY}/${IMAGE_NAME}:latest
    docker push ${ECR_REGISTRY}/${IMAGE_NAME}:v1
done

cd ..
```

**Expected output**: Each image pushed successfully to ECR

### Step 3.4: Verify Images in ECR

**PowerShell**:
```powershell
# List images in ECR
aws ecr describe-images --repository-name llm-chatbot/gateway --region $Env:AWS_REGION

# Should show 2 image tags: latest and v1
```

**Bash**:
```bash
# Option 1: Simple verification (shows all image details)
for repo in frontend gateway settings conversations messages ai-worker; do
    echo "Images in llm-chatbot/$repo:"
    aws ecr describe-images --repository-name llm-chatbot/$repo --region ${AWS_REGION}
    echo ""
done

# Option 2: Compact verification (shows only image tags)
echo "=== Compact Image Summary ==="
for repo in frontend gateway settings conversations messages ai-worker; do
    echo -n "llm-chatbot/$repo: "
    aws ecr describe-images --repository-name llm-chatbot/$repo --region ${AWS_REGION} --query 'imageDetails[*].imageTags' --output text
done

# Option 3: Count total images
echo ""
echo "Total images pushed:"
aws ecr list-images --repository-name llm-chatbot/frontend --region ${AWS_REGION} --query 'imageIds' --output json | jq 'length'
```

**Expected output**:
```
llm-chatbot/frontend: ['latest', 'v1']
llm-chatbot/gateway: ['latest', 'v1']
llm-chatbot/settings: ['latest', 'v1']
llm-chatbot/conversations: ['latest', 'v1']
llm-chatbot/messages: ['latest', 'v1']
llm-chatbot/ai-worker: ['latest', 'v1']

Total images pushed: 2 per repository = 12 total images
```

✅ **Success Criteria**:
- 6 ECR repositories created
- All 6 services built and pushed with 2 tags each (latest, v1)
- Images scannable and encrypted

---

## Phase 4: EKS Cluster Creation

**Duration**: 20-30 minutes ⏱️ *This includes automated wait time*  
**Goal**: Create production-grade EKS cluster

### Step 4.1: Update Cluster Configuration

Edit `infra/eksctl/cluster.yaml`:

```yaml
# Update account ID and region if needed
metadata:
  name: llm-chatbot
  region: us-east-1

# Leave node groups and addons as configured
```

### Step 4.2: Create EKS Cluster

**PowerShell**:
```powershell
# Create cluster (this takes 15-20 minutes)
Write-Host "Creating EKS cluster - this will take 15-20 minutes..."
eksctl create cluster -f .\infra\eksctl\cluster.yaml

# Wait for cluster to be ready
Write-Host "Waiting for cluster to be ready..."
```

**Bash**:
```bash
echo "Creating EKS cluster - this will take 15-20 minutes..."
eksctl create cluster -f ./infra/eksctl/cluster.yaml

echo "Waiting for cluster to be ready..."
```

**⏱️ WAIT 15-20 MINUTES**. The cluster is being created in the background. You'll see output like:

```
[ℹ]  creating CloudFormation stack "eksctl-llm-chatbot-cluster"
[ℹ]  waiting for CloudFormation stack "eksctl-llm-chatbot-cluster"
[ℹ]  creating nodegroup "system-pool" in cluster "llm-chatbot"
[ℹ]  waiting for the CloudFormation stack "eksctl-llm-chatbot-nodegroup-system-pool"
...
[✔]  all EKS cluster resources for "llm-chatbot" have been created
```

### Step 4.3: Configure kubectl

**PowerShell**:
```powershell
# Update kubeconfig
aws eks update-kubeconfig `
  --region $Env:AWS_REGION `
  --name $Env:CLUSTER_NAME

# Verify cluster connection
kubectl cluster-info
kubectl get nodes

# Expected: 3 nodes (1 system, 2 api, 1 ai-worker = 4 total across zones)
```

**Bash**:
```bash
# Update kubeconfig
aws eks update-kubeconfig \
  --region ${AWS_REGION} \
  --name ${CLUSTER_NAME}

# Verify
kubectl cluster-info
kubectl get nodes
```

**Expected output**:
```
NAME                           STATUS   ROLES    AGE   VERSION
ip-10-0-x-x.ec2.internal      Ready    <none>   2m    v1.29.x
ip-10-0-x-x.ec2.internal      Ready    <none>   2m    v1.29.x
ip-10-0-x-x.ec2.internal      Ready    <none>   2m    v1.29.x
```

### Step 4.4: Install AWS Load Balancer Controller

**PowerShell**:
```powershell
# Add Helm repo
helm repo add eks https://aws.github.io/eks-charts
helm repo update

# Create IAM policy for ALB controller
$POLICY_DOC = @'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeTargetGroups",
        "elasticloadbalancing:DescribeListeners"
      ],
      "Resource": "*"
    }
  ]
}
'@

$POLICY_DOC | Out-File -FilePath ./alb-policy.json

aws iam create-policy `
  --policy-name AWSLoadBalancerControllerPolicy `
  --policy-document file://./alb-policy.json

# Create service account
kubectl create serviceaccount aws-load-balancer-controller -n kube-system

# Attach policy to service account
eksctl create iamserviceaccount `
  --cluster=$Env:CLUSTER_NAME `
  --region=$Env:AWS_REGION `
  --namespace=kube-system `
  --name=aws-load-balancer-controller `
  --override-existing-serviceaccounts `
  --attach-policy-arn=arn:aws:iam::aws:policy/AWSLoadBalancingFullAccess

# Install ALB controller using Helm
helm install aws-load-balancer-controller eks/aws-load-balancer-controller `
  -n kube-system `
  --set clusterName=$Env:CLUSTER_NAME `
  --set serviceAccount.create=false `
  --set serviceAccount.name=aws-load-balancer-controller

# Verify deployment
kubectl get deployment -n kube-system aws-load-balancer-controller

# Clean up
Remove-Item ./alb-policy.json
```

**Bash**:
```bash
# Step 1: Verify Helm is installed (install if missing)
if ! command -v helm &> /dev/null; then
    echo "Installing Helm..."
    curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
fi

helm version

# Step 2: Add Helm repo
helm repo add eks https://aws.github.io/eks-charts
helm repo update

# Step 3: Create IAM policy (skip if already exists)
if ! aws iam get-policy --policy-arn arn:aws:iam::aws:policy/AWSLoadBalancingFullAccess &> /dev/null; then
    cat > alb-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeTargetGroups",
        "elasticloadbalancing:DescribeListeners"
      ],
      "Resource": "*"
    }
  ]
}
EOF
    
    aws iam create-policy \
      --policy-name AWSLoadBalancerControllerPolicy \
      --policy-document file://./alb-policy.json
    
    rm alb-policy.json
else
    echo "✓ IAM policy already exists"
fi

# Step 4: Service account is already created by eksctl during cluster setup
# Skip manual creation to avoid conflicts
echo "✓ Service account already configured by eksctl"

# Step 5: Install ALB controller with Helm
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=${CLUSTER_NAME} \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller

# Step 6: Verify ALB controller is running
echo "Waiting for ALB controller to be ready (this may take 2-3 minutes)..."
sleep 15

kubectl rollout status deployment/aws-load-balancer-controller -n kube-system --timeout=5m

# Step 7: Check status
echo "✓ ALB Controller Status:"
kubectl get pods -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller
```

# Cleanup
rm alb-policy.json
```

**Expected output**: ALB controller deployment ready (1/1)

✅ **Success Criteria**:
- Cluster showing 4+ Ready nodes
- kubectl can connect to cluster
- ALB controller deployed and running

---

## Phase 5: Helm Deployment

**Duration**: 15 minutes  
**Goal**: Deploy microservices to EKS using Helm

### Step 5.1: Update Helm Values

Edit `infra/helm/chatapp/values.yaml`:

```yaml
# Update with your ECR registry
images:
  frontend:
    repository: "ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/llm-chatbot/frontend"
    tag: "latest"
  gateway:
    repository: "ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/llm-chatbot/gateway"
    tag: "latest"
  # ... repeat for all services

# Update with your domain
ingress:
  host: "your-domain.com"  # Change to your domain

# Update Secrets Manager ARN
irsa:
  roleArn: "arn:aws:iam::ACCOUNT_ID:role/llm-chatbot-workload"

aws:
  region: "us-east-1"
```

### Step 5.2: Create Kubernetes Namespace & Secrets

**PowerShell** (Idempotent - safe to run multiple times):
```powershell
# Create namespace only if it doesn't exist
$ns = kubectl get namespace chatbot 2>$null
if ($LASTEXITCODE -ne 0) {
  kubectl create namespace chatbot
  Write-Host "✓ Namespace 'chatbot' created"
} else {
  Write-Host "✓ Namespace 'chatbot' already exists"
}

# Add Helm management metadata (required for Helm to manage the namespace)
kubectl annotate namespace chatbot `
  meta.helm.sh/release-name=llm-chatbot `
  meta.helm.sh/release-namespace=chatbot `
  --overwrite 2>$null | Out-Null

kubectl label namespace chatbot `
  app.kubernetes.io/managed-by=Helm `
  name=chatbot `
  --overwrite | Out-Null
Write-Host "✓ Namespace labeled with Helm metadata"

# Delete and recreate secret to ensure fresh API key
kubectl delete secret llm-chatbot-secret -n chatbot 2>$null | Out-Null
kubectl create secret generic llm-chatbot-secret `
  --from-literal=OPENAI_API_KEY=$Env:OPENAI_API_KEY `
  -n chatbot
Write-Host "✓ Secret 'llm-chatbot-secret' created/updated"

# Verify
Write-Host "`n✓ Final state:"
kubectl get namespace chatbot --show-labels
kubectl get secrets -n chatbot
```

**Bash** (Idempotent - safe to run multiple times):
```bash
#!/bin/bash

# Create namespace only if it doesn't exist
if ! kubectl get namespace chatbot &>/dev/null; then
  kubectl create namespace chatbot
  echo "✓ Namespace 'chatbot' created"
else
  echo "✓ Namespace 'chatbot' already exists"
fi

# Add Helm management metadata (required for Helm to manage the namespace)
kubectl annotate namespace chatbot \
  meta.helm.sh/release-name=llm-chatbot \
  meta.helm.sh/release-namespace=chatbot \
  --overwrite 2>/dev/null

kubectl label namespace chatbot \
  app.kubernetes.io/managed-by=Helm \
  name=chatbot \
  --overwrite
echo "✓ Namespace labeled with Helm metadata"

# Delete and recreate secret to ensure fresh API key
kubectl delete secret llm-chatbot-secret -n chatbot 2>/dev/null || true
kubectl create secret generic llm-chatbot-secret \
  --from-literal=OPENAI_API_KEY="${OPENAI_API_KEY}" \
  -n chatbot
echo "✓ Secret 'llm-chatbot-secret' created/updated"

# Verify
echo ""
echo "✓ Final state:"
kubectl get namespace chatbot --show-labels
kubectl get secrets -n chatbot
```

**Expected output**: 
- Namespace exists with `name=chatbot`, `app.kubernetes.io/managed-by=Helm` labels
- Namespace has Helm metadata annotations (release-name, release-namespace)
- Secret `llm-chatbot-secret` exists and contains OPENAI_API_KEY
- Safe to re-run without errors
- Helm can now successfully import and manage the namespace

### Step 5.3: Deploy with Helm

**PowerShell**:
```powershell
# Deploy using Helm
helm upgrade --install llm-chatbot .\infra\helm\chatapp `
  -n chatbot `
  --values .\infra\helm\chatapp\values.yaml `
  --set images.frontend.repository="$Env:ECR_REGISTRY/llm-chatbot/frontend" `
  --set images.gateway.repository="$Env:ECR_REGISTRY/llm-chatbot/gateway" `
  --set images.settings.repository="$Env:ECR_REGISTRY/llm-chatbot/settings" `
  --set images.conversations.repository="$Env:ECR_REGISTRY/llm-chatbot/conversations" `
  --set images.messages.repository="$Env:ECR_REGISTRY/llm-chatbot/messages" `
  --set images.ai.repository="$Env:ECR_REGISTRY/llm-chatbot/ai-worker" `
  --set openai.apiKey=$Env:OPENAI_API_KEY

# Watch deployment progress
kubectl rollout status deployment/gateway -n chatbot --timeout=10m
kubectl rollout status deployment/frontend -n chatbot --timeout=10m
```

**Bash**:
```bash
# Deploy using Helm
helm upgrade --install llm-chatbot ./infra/helm/chatapp \
  -n chatbot \
  --values ./infra/helm/chatapp/values.yaml \
  --set images.frontend.repository="${ECR_REGISTRY}/llm-chatbot/frontend" \
  --set images.gateway.repository="${ECR_REGISTRY}/llm-chatbot/gateway" \
  --set images.settings.repository="${ECR_REGISTRY}/llm-chatbot/settings" \
  --set images.conversations.repository="${ECR_REGISTRY}/llm-chatbot/conversations" \
  --set images.messages.repository="${ECR_REGISTRY}/llm-chatbot/messages" \
  --set images.ai.repository="${ECR_REGISTRY}/llm-chatbot/ai-worker" \
  --set openai.apiKey="${OPENAI_API_KEY}"

# Watch deployments
kubectl rollout status deployment/gateway -n chatbot --timeout=10m
kubectl rollout status deployment/frontend -n chatbot --timeout=10m
```

### Step 5.4: Verify Deployments

**PowerShell**:
```powershell
# Check all pods
kubectl get pods -n chatbot

# Expected: All pods should be Running
# frontend: 2/2
# gateway: 3/3
# settings: 2/2
# conversations: 2/2
# messages: 2/2
# ai-worker: 1/1

# Check services
kubectl get svc -n chatbot

# Get LoadBalancer IPs
$GATEWAY_LB=$(kubectl get svc gateway -n chatbot -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
$FRONTEND_LB=$(kubectl get svc frontend -n chatbot -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

Write-Host "Gateway LoadBalancer: $GATEWAY_LB"
Write-Host "Frontend LoadBalancer: $FRONTEND_LB"
```

**Bash**:
```bash
# Check pods
kubectl get pods -n chatbot

# Check services  
kubectl get svc -n chatbot

# Get LoadBalancer endpoints
GATEWAY_LB=$(kubectl get svc gateway -n chatbot -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
FRONTEND_LB=$(kubectl get svc frontend -n chatbot -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

echo "Gateway LoadBalancer: $GATEWAY_LB"
echo "Frontend LoadBalancer: $FRONTEND_LB"
```

**Expected output**:
```
NAME                    READY   STATUS    RESTARTS   AGE
frontend-xxxxx-xxxxx    1/1     Running   0          2m
gateway-xxxxx-xxxxx     1/1     Running   0          2m
settings-xxxxx-xxxxx    1/1     Running   0          2m
conversations-xxxxx-xxx 1/1     Running   0          2m
messages-xxxxx-xxxxx    1/1     Running   0          2m
ai-worker-xxxxx-xxxxx   1/1     Running   0          2m

NAME            TYPE           CLUSTER-IP       EXTERNAL-IP
gateway         LoadBalancer   10.100.xx.xx     aaxxxx-111111111.us-east-1.elb.amazonaws.com
frontend        LoadBalancer   10.100.xx.xx     bbyyyy-222222222.us-east-1.elb.amazonaws.com
settings        ClusterIP      10.100.xx.xx     <none>
conversations   ClusterIP      10.100.xx.xx     <none>
messages        ClusterIP      10.100.xx.xx     <none>
```

✅ **Success Criteria**:
- All 6 services deployed with correct replicas
- All pods in Running state
- LoadBalancers have external IPs assigned
- No failed or pending pods

---

## Phase 6: AWS Service Integration

**Duration**: 10 minutes  
**Goal**: Configure IAM roles, Secrets Manager, and DynamoDB permissions

### Step 6.1: Create IAM Role for Workloads

**PowerShell**:
```powershell
# Create trust policy for IRSA
$TRUST_POLICY = @"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::$Env:AWS_ACCOUNT_ID:oidc-provider/oidc.eks.$Env:AWS_REGION.amazonaws.com/id/EXAMPLEID"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "oidc.eks.$Env:AWS_REGION.amazonaws.com/id/EXAMPLEID:sub": "system:serviceaccount:chatbot:chatbot-workload"
        }
      }
    }
  ]
}
"@

# Create IAM role
aws iam create-role `
  --role-name llm-chatbot-workload `
  --assume-role-policy-document $TRUST_POLICY

# Create inline policy for DynamoDB, SQS, and Secrets access
$POLICY = @"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem"
      ],
      "Resource": [
        "arn:aws:dynamodb:$Env:AWS_REGION:$Env:AWS_ACCOUNT_ID:table/conversations",
        "arn:aws:dynamodb:$Env:AWS_REGION:$Env:AWS_ACCOUNT_ID:table/messages",
        "arn:aws:dynamodb:$Env:AWS_REGION:$Env:AWS_ACCOUNT_ID:table/settings"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "sqs:SendMessage",
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes"
      ],
      "Resource": [
        "arn:aws:sqs:$Env:AWS_REGION:$Env:AWS_ACCOUNT_ID:ai-jobs.fifo",
        "arn:aws:sqs:$Env:AWS_REGION:$Env:AWS_ACCOUNT_ID:ai-jobs-dlq.fifo"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:$Env:AWS_REGION:$Env:AWS_ACCOUNT_ID:secret:llm-chatbot/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:$Env:AWS_REGION:$Env:AWS_ACCOUNT_ID:log-group:/aws/eks/llm-chatbot*"
    }
  ]
}
"@

aws iam put-role-policy `
  --role-name llm-chatbot-workload `
  --policy-name llm-chatbot-inline-policy `
  --policy-document $POLICY
```

**Bash**:
```bash
# Get OIDC provider ID
OIDC_ID=$(aws eks describe-cluster --name ${CLUSTER_NAME} --region ${AWS_REGION} \
  --query 'cluster.identity.oidc.issuer' --output text | cut -d '/' -f 5)

# Create trust policy
cat > trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/oidc.eks.${AWS_REGION}.amazonaws.com/id/${OIDC_ID}"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "oidc.eks.${AWS_REGION}.amazonaws.com/id/${OIDC_ID}:sub": "system:serviceaccount:chatbot:chatbot-workload"
        }
      }
    }
  ]
}
EOF

# Create role
aws iam create-role \
  --role-name llm-chatbot-workload \
  --assume-role-policy-document file://trust-policy.json

# Create policy
cat > workload-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem"
      ],
      "Resource": [
        "arn:aws:dynamodb:${AWS_REGION}:${AWS_ACCOUNT_ID}:table/conversations",
        "arn:aws:dynamodb:${AWS_REGION}:${AWS_ACCOUNT_ID}:table/messages",
        "arn:aws:dynamodb:${AWS_REGION}:${AWS_ACCOUNT_ID}:table/settings"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "sqs:SendMessage",
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes"
      ],
      "Resource": [
        "arn:aws:sqs:${AWS_REGION}:${AWS_ACCOUNT_ID}:ai-jobs.fifo",
        "arn:aws:sqs:${AWS_REGION}:${AWS_ACCOUNT_ID}:ai-jobs-dlq.fifo"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:${AWS_REGION}:${AWS_ACCOUNT_ID}:secret:llm-chatbot/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:${AWS_REGION}:${AWS_ACCOUNT_ID}:log-group:/aws/eks/llm-chatbot*"
    }
  ]
}
EOF

# Attach policy
aws iam put-role-policy \
  --role-name llm-chatbot-workload \
  --policy-name llm-chatbot-inline-policy \
  --policy-document file://workload-policy.json

# Cleanup
rm trust-policy.json workload-policy.json
```

### Step 6.2: Create Kubernetes Service Account

**PowerShell**:
```powershell
# Create service account
kubectl create serviceaccount chatbot-workload -n chatbot

# Annotate with IAM role
kubectl annotate serviceaccount chatbot-workload `
  -n chatbot `
  eks.amazonaws.com/role-arn=arn:aws:iam::$Env:AWS_ACCOUNT_ID`:role/llm-chatbot-workload

# Verify
kubectl describe sa chatbot-workload -n chatbot
```

**Bash**:
```bash
# Create service account
kubectl create serviceaccount chatbot-workload -n chatbot

# Annotate
kubectl annotate serviceaccount chatbot-workload \
  -n chatbot \
  eks.amazonaws.com/role-arn=arn:aws:iam::${AWS_ACCOUNT_ID}:role/llm-chatbot-workload

# Verify
kubectl describe sa chatbot-workload -n chatbot
```

✅ **Success Criteria**:
- IAM role created for workloads
- Service account created and annotated
- DynamoDB, SQS, and Secrets permissions granted
- Annotation shows correct IAM role ARN

⚠️ **Important**: After creating/modifying the service account, pods must be restarted to inject IRSA tokens. This will be done in Step 6.5.

---

### Step 6.3: Verify DynamoDB Table Access

**Goal**: Test that Kubernetes pods can access DynamoDB tables with the new IAM role

**PowerShell**:
```powershell
# Create a test pod with the chatbot-workload service account
kubectl run dynamodb-test --rm -it --image=amazon/aws-cli:latest --serviceaccount=chatbot-workload -n chatbot --command -- /bin/sh

# Inside the pod, run these commands:
# 1. Verify AWS credentials are available
aws sts get-caller-identity

# Expected output: Shows the role ARN (arn:aws:iam::ACCOUNT:role/llm-chatbot-workload)

# 2. Test DynamoDB access - scan conversations table
aws dynamodb scan --table-name conversations --region us-east-1 --max-items 5

# Expected output: Returns table items (even if empty initially)

# 3. Test write permission - put a test item
aws dynamodb put-item --table-name conversations \
  --item '{"user_id": {"S": "test-user"}, "conversation_id": {"S": "test-conv-123"}, "title": {"S": "Test Conversation"}}' \
  --region us-east-1

# 4. Verify the item was written
aws dynamodb get-item --table-name conversations \
  --key '{"user_id": {"S": "test-user"}, "conversation_id": {"S": "test-conv-123"}}' \
  --region us-east-1

# 5. Clean up test data
aws dynamodb delete-item --table-name conversations \
  --key '{"user_id": {"S": "test-user"}, "conversation_id": {"S": "test-conv-123"}}' \
  --region us-east-1

# Exit the pod
exit
```

**Bash** (same commands, but in pod):
```bash
# Create test pod
kubectl run dynamodb-test --rm -it \
  --image=amazon/aws-cli:latest \
  --serviceaccount=chatbot-workload \
  -n chatbot \
  --command -- /bin/sh

# Inside pod:
aws sts get-caller-identity
aws dynamodb scan --table-name conversations --region us-east-1 --max-items 5
aws dynamodb put-item --table-name conversations \
  --item '{"user_id": {"S": "test-user"}, "conversation_id": {"S": "test-conv-123"}, "title": {"S": "Test Conversation"}}' \
  --region us-east-1
aws dynamodb get-item --table-name conversations \
  --key '{"user_id": {"S": "test-user"}, "conversation_id": {"S": "test-conv-123"}}' \
  --region us-east-1
aws dynamodb delete-item --table-name conversations \
  --key '{"user_id": {"S": "test-user"}, "conversation_id": {"S": "test-conv-123"}}' \
  --region us-east-1
exit
```

**Expected Output**:
```
{
    "UserId": "AIDAI...",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:role/llm-chatbot-workload"
}

Items: [] or existing items (depends on database state)

{
    "ConsumedCapacity": {...}
}
```

✅ **Success Criteria**:
- Pod assumes the llm-chatbot-workload IAM role
- Can read from DynamoDB tables (Scan, GetItem)
- Can write to DynamoDB tables (PutItem)
- Can delete from DynamoDB tables (DeleteItem)

---

### Step 6.4: Verify SQS Queue Access

**Goal**: Test that Kubernetes pods can access SQS queues with the new IAM role

**PowerShell**:
```powershell
# Get queue URLs (set as variables from earlier phases)
$MAIN_QUEUE = "https://sqs.us-east-1.amazonaws.com/123456789012/ai-jobs.fifo"
$DLQ = "https://sqs.us-east-1.amazonaws.com/123456789012/ai-jobs-dlq.fifo"

# Create a test pod with chatbot-workload service account
kubectl run sqs-test --rm -it --image=amazon/aws-cli:latest --serviceaccount=chatbot-workload -n chatbot --command -- /bin/sh

# Inside the pod, run these commands:
# 1. Verify role assumption
aws sts get-caller-identity

# 2. List SQS queues
aws sqs list-queues --region us-east-1

# Expected: Shows ai-jobs.fifo and ai-jobs-dlq.fifo

# 3. Get queue attributes (check queue exists and is accessible)
aws sqs get-queue-attributes --queue-url $MAIN_QUEUE --attribute-names All --region us-east-1

# 4. Send test message to queue
aws sqs send-message \
  --queue-url $MAIN_QUEUE \
  --message-body '{"test": "connectivity-check", "timestamp": "2024-05-26T10:00:00Z"}' \
  --message-group-id "test-group" \
  --region us-east-1

# Expected: Returns MessageId

# 5. Receive message from queue
aws sqs receive-message --queue-url $MAIN_QUEUE --region us-east-1

# Expected: Returns the message we just sent

# 6. Delete message from queue
aws sqs delete-message \
  --queue-url $MAIN_QUEUE \
  --receipt-handle <RECEIPT_HANDLE_FROM_RECEIVE> \
  --region us-east-1

# 7. Check DLQ is accessible
aws sqs get-queue-attributes --queue-url $DLQ --attribute-names All --region us-east-1

# Exit pod
exit
```

**Bash** (same commands):
```bash
# Get queue URLs
MAIN_QUEUE="https://sqs.us-east-1.amazonaws.com/123456789012/ai-jobs.fifo"
DLQ="https://sqs.us-east-1.amazonaws.com/123456789012/ai-jobs-dlq.fifo"

# Create test pod
kubectl run sqs-test --rm -it \
  --image=amazon/aws-cli:latest \
  --serviceaccount=chatbot-workload \
  -n chatbot \
  --command -- /bin/sh

# Inside pod:
aws sts get-caller-identity
aws sqs list-queues --region us-east-1
aws sqs get-queue-attributes --queue-url ${MAIN_QUEUE} --attribute-names All --region us-east-1
aws sqs send-message \
  --queue-url ${MAIN_QUEUE} \
  --message-body '{"test": "connectivity-check"}' \
  --message-group-id "test-group" \
  --region us-east-1
aws sqs receive-message --queue-url ${MAIN_QUEUE} --region us-east-1
exit
```

**Expected Output**:
```
{
    "QueueUrls": [
        "https://sqs.us-east-1.amazonaws.com/123456789012/ai-jobs.fifo",
        "https://sqs.us-east-1.amazonaws.com/123456789012/ai-jobs-dlq.fifo"
    ]
}

{
    "MessageId": "12345678-1234-1234-1234-123456789012",
    "MD5OfMessageBody": "abc123...",
    "SequenceNumber": "18..."
}
```

✅ **Success Criteria**:
- Pod assumes llm-chatbot-workload role
- Can list SQS queues
- Can read queue attributes
- Can send messages to queue
- Can receive messages from queue
- DLQ is accessible

---

### Step 6.5: Test Service Connectivity

**Goal**: Verify that IRSA (IAM Roles for Service Accounts) is properly configured and pods have AWS credentials

⚠️ **Important Note**: Production containers don't have `aws` CLI or `curl` tools installed (by design for security). We verify IRSA by checking service account annotations and environment variables instead.

### Step 6.5a: Restart Pods to Inject IRSA Tokens

After creating the service account, pods must be restarted to inject IRSA tokens:

**PowerShell**:
```powershell
# Restart all service deployments
Write-Host "Restarting Gateway pods..."
kubectl rollout restart deployment/gateway -n chatbot

Write-Host "Restarting AI Worker pods..."
kubectl rollout restart deployment/ai-worker -n chatbot

Write-Host "Waiting for pods to be ready..."
kubectl rollout status deployment/gateway -n chatbot --timeout=5m
kubectl rollout status deployment/ai-worker -n chatbot --timeout=5m

Write-Host "✓ All pods restarted successfully"
```

**Bash**:
```bash
# Restart deployments
echo "Restarting Gateway pods..."
kubectl rollout restart deployment/gateway -n chatbot

echo "Restarting AI Worker pods..."
kubectl rollout restart deployment/ai-worker -n chatbot

echo "Waiting for pods to be ready..."
kubectl rollout status deployment/gateway -n chatbot --timeout=5m
kubectl rollout status deployment/ai-worker -n chatbot --timeout=5m

echo "✓ All pods restarted successfully"
```

### Step 6.5b: Verify IRSA Configuration

**PowerShell**:
```powershell
# 1. Verify service account annotation
Write-Host "=== Verifying Service Account ==="
kubectl describe sa chatbot-workload -n chatbot

# Expected: Should show annotation "eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT_ID:role/llm-chatbot-workload"

# 2. Verify pods use correct service account
Write-Host ""
Write-Host "=== Verifying Pod Service Accounts ==="
kubectl get pods -n chatbot -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.serviceAccountName}{"\n"}{end}'

# Expected: All pods should use "chatbot-workload" service account

# 3. Verify IRSA environment variables in pods
Write-Host ""
Write-Host "=== Verifying IRSA Environment Variables ==="

$GATEWAY_POD = kubectl get pods -n chatbot | Select-String "gateway" | Select-Object -First 1 | ForEach-Object { $_.ToString().Split()[0] }
Write-Host "Gateway Pod: $GATEWAY_POD"

kubectl exec -it $GATEWAY_POD -n chatbot -- env | Select-String "AWS_ROLE_ARN", "AWS_WEB_IDENTITY_TOKEN_FILE", "AWS_REGION"

# Expected output:
# AWS_ROLE_ARN=arn:aws:iam::396608772637:role/llm-chatbot-workload
# AWS_WEB_IDENTITY_TOKEN_FILE=/var/run/secrets/eks.amazonaws.com/serviceaccount/token
# AWS_REGION=us-east-1
```

**Bash**:
```bash
# 1. Verify service account annotation
echo "=== Verifying Service Account ==="
kubectl describe sa chatbot-workload -n chatbot

# Expected: Should show annotation "eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT_ID:role/llm-chatbot-workload"

# 2. Verify pods use correct service account
echo ""
echo "=== Verifying Pod Service Accounts ==="
kubectl get pods -n chatbot -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.serviceAccountName}{"\n"}{end}'

# Expected: All pods should use "chatbot-workload" service account

# 3. Verify IRSA environment variables in pods
echo ""
echo "=== Verifying IRSA Environment Variables ==="

GATEWAY_POD=$(kubectl get pods -n chatbot | grep gateway | head -1 | awk '{print $1}')
echo "Gateway Pod: $GATEWAY_POD"

kubectl exec -it $GATEWAY_POD -n chatbot -- env | grep -E "AWS_ROLE_ARN|AWS_WEB_IDENTITY_TOKEN_FILE|AWS_REGION"

# Expected output:
# AWS_ROLE_ARN=arn:aws:iam::396608772637:role/llm-chatbot-workload
# AWS_WEB_IDENTITY_TOKEN_FILE=/var/run/secrets/eks.amazonaws.com/serviceaccount/token
# AWS_REGION=us-east-1

AI_POD=$(kubectl get pods -n chatbot | grep ai-worker | head -1 | awk '{print $1}')
echo ""
echo "AI Worker Pod: $AI_POD"

kubectl exec -it $AI_POD -n chatbot -- env | grep -E "AWS_ROLE_ARN|AWS_WEB_IDENTITY_TOKEN_FILE|AWS_REGION"

# Expected: Same environment variables as gateway pod
```

**Expected Output**:
```
✓ Service account annotated with IAM role ARN
✓ All pods using "chatbot-workload" service account
✓ AWS_ROLE_ARN set correctly in all pods
✓ AWS_WEB_IDENTITY_TOKEN_FILE present for token mounting
✓ AWS_REGION set correctly
```

✅ **Success Criteria**:
- Service account has correct IAM role annotation
- All pods configured with chatbot-workload service account
- IRSA environment variables injected in all pods
- AWS credentials available via IAM role (IRSA)
- No manual AWS credentials needed in containers

---

## Phase 6.6: AI Worker Background Processing Configuration

**Duration**: 5 minutes  
**Goal**: Configure auto-scaling for AI worker pods based on SQS queue depth

### Step 6.6.1: Configure AI Worker Auto-Scaling

The AI Worker service is the only background processing service that scales based on SQS queue depth, not CPU metrics.

**PowerShell**:
```powershell
# Create HPA for AI Worker based on SQS queue depth
kubectl apply -f - <<'EOF'
apiVersion: autoscaling.keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: ai-worker-scaler
  namespace: chatbot
spec:
  scaleTargetRef:
    name: ai-worker
    kind: Deployment
  minReplicaCount: 0  # Scale to zero when no jobs
  maxReplicaCount: 10  # Max 10 concurrent AI workers
  triggers:
  - type: aws-sqs-queue
    metadata:
      queueURL: $MAIN_QUEUE
      queueLength: "5"  # Scale up when 5+ messages waiting
      awsRegion: "$Env:AWS_REGION"
      identityOwner: "operator"  # Use IAM role of worker pod
EOF

Write-Host \"\u2713 AI Worker auto-scaling configured\"\nWrite-Host \"  - Scales from 0 to 10 pods based on SQS queue depth\"\nWrite-Host \"  - Scales up when queue length > 5\"\nWrite-Host \"  - Scales down to 0 when queue is empty for 5 minutes\"\n```\n\n**⏰ Important**: This requires KEDA (Kubernetes Event Driven Autoscaling) to be installed. If not already installed:\n\n```powershell\nhelm repo add kedacore https://kedacore.github.io/charts\nhelm repo update\nhelm install keda kedacore/keda --namespace keda --create-namespace\n```\n\n### Step 6.6.2: Monitor AI Worker Processing\n\n**PowerShell**:\n```powershell\n# Watch AI worker pods scaling\nkubectl get pods -n chatbot -l app=ai-worker -w\n\n# Check queue depth\n$QUEUE_ATTRS=$(aws sqs get-queue-attributes `\n  --queue-url $MAIN_QUEUE `\n  --attribute-names ApproximateNumberOfMessages,ApproximateNumberOfMessagesNotVisible `\n  --region $Env:AWS_REGION)\n\n$QUEUE_ATTRS | ConvertFrom-Json | Select-Object -ExpandProperty Attributes\n\n# Expected output:\n# ApproximateNumberOfMessages: 0-100 (waiting to process)\n# ApproximateNumberOfMessagesNotVisible: 0-50 (currently processing)\n```\n\n**Key Metrics to Monitor**:\n- **Queue Depth**: `ApproximateNumberOfMessages` (target: 0-5)\n- **In-Flight**: `ApproximateNumberOfMessagesNotVisible` (target: same as worker pods)\n- **DLQ Messages**: Should stay near 0 (indicates failures)\n- **AI Worker Pod Restarts**: Should be 0 (indicates crashes)\n\n---\n\n## Phase 7: Production Testing\n\n**Duration**: 15 minutes  \n**Goal**: Test all services and verify integration"

### Step 7.1: Test Gateway Health

**PowerShell**:
```powershell
$GATEWAY_URL = kubectl get svc gateway -n chatbot -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'

# Wait for LoadBalancer to be ready
for ($i = 0; $i -lt 30; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://$GATEWAY_URL/health" -ErrorAction Stop
        Write-Host "✓ Gateway healthy"
        break
    } catch {
        Write-Host "Waiting for gateway... ($i/30)"
        Start-Sleep -Seconds 2
    }
}

# Test settings endpoint
Invoke-RestMethod -Uri "http://$GATEWAY_URL/api/settings" -Headers @{"Content-Type"="application/json"}
```

**Bash**:
```bash
GATEWAY_URL=$(kubectl get svc gateway -n chatbot -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# Wait for health check
for i in {1..30}; do
    if curl -f "http://${GATEWAY_URL}/health" > /dev/null 2>&1; then
        echo "✓ Gateway healthy"
        break
    else
        echo "Waiting for gateway... ($i/30)"
        sleep 2
    fi
done

# Test settings API
curl -X GET "http://${GATEWAY_URL}/api/settings" \
  -H "Content-Type: application/json"
```

**Expected output**: HTTP 200 with settings JSON

### Step 7.2: Test Chat Flow

**PowerShell**:
```powershell
$GATEWAY_URL = kubectl get svc gateway -n chatbot -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'

# Create conversation
$conv_response = Invoke-RestMethod -Uri "http://$GATEWAY_URL/api/conversations" `
  -Method POST `
  -Headers @{"Content-Type"="application/json"} `
  -Body '{"title": "Test Conversation"}'

$CONV_ID = $conv_response.id

Write-Host "Created conversation: $CONV_ID"

# Send message
$msg_response = Invoke-RestMethod -Uri "http://$GATEWAY_URL/api/chat/send" `
  -Method POST `
  -Headers @{"Content-Type"="application/json"} `
  -Body "{`"message`": `"Hello, how are you?`", `"conversation_id`": `"$CONV_ID`"}"

$JOB_ID = $msg_response.job_id

Write-Host "Job submitted: $JOB_ID"
Write-Host "Response: $msg_response"

# Wait for AI processing (10-15 seconds)
Start-Sleep -Seconds 10

# Check conversation for response
$conv_check = Invoke-RestMethod -Uri "http://$GATEWAY_URL/api/conversations/$CONV_ID" `
  -Method GET `
  -Headers @{"Content-Type"="application/json"}

Write-Host "Conversation messages:"
$conv_check.messages | ForEach-Object { Write-Host "- $_.role: $_.content" }
```

**Bash**:
```bash
GATEWAY_URL=$(kubectl get svc gateway -n chatbot -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# Create conversation
CONV_RESPONSE=$(curl -s -X POST "http://${GATEWAY_URL}/api/conversations" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Conversation"}')

CONV_ID=$(echo $CONV_RESPONSE | jq -r '.id')
echo "Created conversation: $CONV_ID"

# Send message
MSG_RESPONSE=$(curl -s -X POST "http://${GATEWAY_URL}/api/chat/send" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Hello, how are you?\", \"conversation_id\": \"$CONV_ID\"}")

JOB_ID=$(echo $MSG_RESPONSE | jq -r '.job_id')
echo "Job submitted: $JOB_ID"

# Wait for AI processing
sleep 10

# Check conversation
curl -s -X GET "http://${GATEWAY_URL}/api/conversations/${CONV_ID}" \
  -H "Content-Type: application/json" | jq '.messages'
```

**Expected output**: Chat message processed and AI response stored

### Step 7.3: Check Pod Logs

**PowerShell**:
```powershell
# Gateway logs
kubectl logs -n chatbot deployment/gateway --tail=50

# AI Worker logs
kubectl logs -n chatbot deployment/ai-worker --tail=50

# Check for errors
kubectl logs -n chatbot deployment/ai-worker --tail=100 | Select-String "ERROR"
```

**Bash**:
```bash
# Gateway logs
kubectl logs -n chatbot deployment/gateway --tail=50

# AI Worker logs
kubectl logs -n chatbot deployment/ai-worker --tail=50

# Check for errors
kubectl logs -n chatbot deployment/ai-worker --tail=100 | grep ERROR
```

✅ **Success Criteria**:
- All API endpoints responding (200 OK)
- Chat message submitted successfully
- AI worker processing messages
- No error logs

---

## Phase 8: Monitoring & Observability

**Duration**: 10 minutes  
**Goal**: Enable logging, metrics, and monitoring

### Step 8.1: View CloudWatch Logs

**PowerShell**:
```powershell
# Check log group
aws logs describe-log-groups --region $Env:AWS_REGION | Select-String "llm-chatbot"

# Tail logs
aws logs tail /aws/eks/llm-chatbot/gateway --follow --region $Env:AWS_REGION
```

**Bash**:
```bash
# List log groups
aws logs describe-log-groups --region ${AWS_REGION}

# Tail logs
aws logs tail /aws/eks/llm-chatbot/gateway --follow --region ${AWS_REGION}
```

### Step 8.2: Monitor HPA

**PowerShell**:
```powershell
# Check HPA status
kubectl get hpa -n chatbot

# Watch HPA scaling
kubectl get hpa -n chatbot -w

# Expected: HPA for gateway, frontend, settings, conversations, messages, ai-worker
```

**Bash**:
```bash
# Check HPA
kubectl get hpa -n chatbot

# Watch scaling
kubectl get hpa -n chatbot -w

# Check metrics
kubectl top pods -n chatbot
kubectl top nodes
```

### Step 8.3: Setup CloudWatch Alarms

**PowerShell**:
```powershell
# Create alarm for failed API requests
aws cloudwatch put-metric-alarm `
  --alarm-name llm-chatbot-api-errors `
  --alarm-description "Alert on high error rate" `
  --metric-name ErrorCount `
  --namespace AWS/ApplicationELB `
  --statistic Sum `
  --period 300 `
  --threshold 10 `
  --comparison-operator GreaterThanThreshold `
  --alarm-actions arn:aws:sns:$Env:AWS_REGION:$Env:AWS_ACCOUNT_ID:YourSNSTopic `
  --region $Env:AWS_REGION
```

**Bash**:
```bash
# Create alarm for errors
aws cloudwatch put-metric-alarm \
  --alarm-name llm-chatbot-api-errors \
  --alarm-description "Alert on high error rate" \
  --metric-name ErrorCount \
  --namespace AWS/ApplicationELB \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --region ${AWS_REGION}
```

✅ **Success Criteria**:
- CloudWatch logs visible for all services
- HPA configured and monitoring
- Metrics flowing to CloudWatch

---

## Phase 9: Post-Deployment Operations

**Duration**: Ongoing  
**Goal**: Maintain, monitor, and optimize the production system

### Step 9.1: Production Cost Optimization

**DynamoDB Cost Optimization**:
```powershell
# Verify TTL is enabled and working
aws dynamodb describe-table --table-name conversations --region $Env:AWS_REGION | Select-Object -ExpandProperty Table | Select-Object TimeToLiveDescription

# Monitor consumed capacity
aws cloudwatch get-metric-statistics `
  --namespace AWS/DynamoDB `
  --metric-name ConsumedWriteCapacityUnits `
  --dimensions Name=TableName,Value=conversations `
  --start-time (Get-Date).AddHours(-1) `
  --end-time (Get-Date) `
  --period 3600 `
  --statistics Sum,Average `
  --region $Env:AWS_REGION

# Estimated monthly cost:
# - Conversations: 1M reads + 1M writes = ~$0.25/month
# - Messages: 3M reads + 3M writes = ~$0.75/month
# - Settings: 500K reads + 500K writes = ~$0.10/month
# - TOTAL DynamoDB: ~$1.10/month (pay-per-request)
```

**SQS Cost Optimization**:
```powershell
# Monitor queue activity (messages processed)
aws cloudwatch get-metric-statistics `
  --namespace AWS/SQS `
  --metric-name NumberOfMessagesSent `
  --dimensions Name=QueueName,Value=ai-jobs.fifo `
  --start-time (Get-Date).AddDays(-7) `
  --end-time (Get-Date) `
  --period 86400 `
  --statistics Sum `
  --region $Env:AWS_REGION

# SQS pricing: First 1M requests/month free, then $0.40 per million
# Typical usage: 10,000 messages/day = 300K/month (within free tier)
# Cost: $0 - $2/month depending on traffic
```

**EC2/EKS Cost Optimization**:
```powershell
# Check node utilization
kubectl top nodes

# Scale down non-production hours (if applicable)
# Minimum: 2 nodes (system + api)
# For cost: Use Spot instances (70% discount) instead of on-demand
# Edit eksctl cluster.yaml to enable Spot instances:
# - instanceTypes: [\"t3.medium\"]
# - spot: true
# Cost Reduction: ~$300/month → $100/month with Spot instances

# Check current costs
aws ce get-cost-and-usage `
  --time-period Start=2024-05-01,End=2024-05-31 `
  --granularity MONTHLY `
  --metrics BlendedCost `
  --group-by Type=DIMENSION,Key=SERVICE `
  --region $Env:AWS_REGION
```

**Summary - Monthly Infrastructure Cost**:
```
| Component | On-Demand | Spot | Monthly |
|-----------|-----------|------|---------|
| EKS Control | $73 | $73 | Fixed |
| EC2 (t3.medium x4) | $300 | $90 | Variable |
| DynamoDB | $20 | $20 | Variable |
| SQS | $2 | $2 | Variable |
| CloudWatch Logs | $20 | $20 | Fixed |
| Data Transfer | $20 | $20 | Variable |
| ECR | $5 | $5 | Fixed |
| Misc (ALB, NAT) | $24 | $24 | Fixed |
|------------|------------|------|---------|
| TOTAL | $464 | $254 | Per month |

OpenAI API costs not included (typically $100-$10,000/month depending on usage)
Total annual infrastructure savings with Spot: $2,520
```

### Step 9.2: Daily Operations Checklist

**Daily (Morning)**:
```bash
# 1. Check system health
kubectl get nodes -n chatbot
kubectl get pods -n chatbot | grep -v Running  # Should be empty

# 2. Monitor queue depth
aws sqs get-queue-attributes --queue-url $MAIN_QUEUE --attribute-names All

# 3. Check error logs
kubectl logs -n chatbot deployment/ai-worker --tail=100 | grep ERROR || echo "✓ No errors"

# 4. Verify DynamoDB
aws dynamodb scan --table-name conversations --select COUNT --region $Env:AWS_REGION
```

**Weekly**:
```bash
# 1. Check DynamoDB consumed capacity
# 2. Review CloudWatch cost estimates
# 3. Verify backup/snapshots are running
# 4. Test disaster recovery procedures (at least monthly)
# 5. Review and update documentation
```

**Monthly**:
```bash
# 1. Full cost analysis and optimization review
# 2. Security audit (IAM permissions, secrets rotation)
# 3. Capacity planning (need to scale up/down?)
# 4. Performance tuning (query patterns, indexes)
# 5. Disaster recovery drill
```

### Step 9.3: Scaling Operations

**When to Scale Up**:
- Queue depth consistently > 50 (add more AI workers)
- CPU utilization > 70% on any service
- Memory usage > 80%
- Response time degradation

**Scaling Steps**:
```powershell
# 1. Increase HPA max replicas
kubectl patch hpa gateway -n chatbot -p '{\"spec\":{\"maxReplicas\":10}}'

# 2. Add more nodes to cluster
eksctl scale nodegroup --cluster=llm-chatbot --name=api-pool --nodes=8 --nodes-max=10

# 3. Monitor scaling progress
kubectl get hpa -n chatbot -w
kubectl get nodes -w

# 4. Verify performance improved
# Re-test chat flow and measure response times
```

**When to Scale Down** (for cost reduction):
- Queue depth consistently < 2
- CPU utilization < 20%
- During non-business hours (if applicable)

### Step 9.4: Security Hardening

**Ongoing**:
```bash
# 1. Rotate credentials monthly
aws secretsmanager rotate-secret --secret-id llm-chatbot/openai-key

# 2. Review IAM permissions quarterly
aws iam get-role --role-name llm-chatbot-workload

# 3. Enable MFA on AWS account
# 4. Use AWS Secrets Manager (not env vars) for all credentials
# 5. Enable CloudTrail for audit logging
# 6. Use VPC endpoints for AWS service access (private)
```

---

## Phase 10: Cleanup & Teardown (When Needed)

**⚠️ WARNING**: This will DELETE all resources. Ensure backups are in place first.

See [infra/cleanup/README.md](./cleanup/README.md) for complete 9-phase teardown procedures:

1. **Phase 1**: Helm Release Deletion (2-3 min)
2. **Phase 2**: Kubernetes Namespace Cleanup (2-3 min)
3. **Phase 3**: EKS Cluster Deletion (10-15 min)
4. **Phase 4**: DynamoDB Table Deletion (2-5 min)
5. **Phase 5**: SQS Queue Deletion (immediate)
6. **Phase 6**: ECR Repository Cleanup (2 min)
7. **Phase 7**: Secrets Manager Cleanup (2 min)
8. **Phase 8**: IAM Role Cleanup (5 min)
9. **Phase 9**: CloudWatch Logs Cleanup (2 min)

**Quick Cleanup Command**:
```bash
# Helm uninstall
helm uninstall llm-chatbot -n chatbot

# Delete namespace
kubectl delete namespace chatbot

# Delete EKS cluster (15+ minutes)
eksctl delete cluster --name=llm-chatbot

# Delete databases
aws dynamodb delete-table --table-name conversations
aws dynamodb delete-table --table-name messages
aws dynamodb delete-table --table-name settings

# Delete queues
aws sqs delete-queue --queue-url $MAIN_QUEUE
aws sqs delete-queue --queue-url $DLQ

# Total estimated cleanup time: 45 minutes
# Total cost saved: $464/month (on-demand) or $254/month (Spot)
# Annual savings: $5,568 (on-demand) or $3,048 (Spot)
```

---

## Troubleshooting Guide

### Problem: Pods stuck in ImagePullBackOff

**Symptoms**: Pods show `ImagePullBackOff` status

**Solution**:
```bash
# Check pod events
kubectl describe pod <pod-name> -n chatbot

# Verify ECR login
aws ecr get-login-password | docker login --username AWS --password-stdin ${ECR_REGISTRY}

# Check image exists
aws ecr describe-images --repository-name llm-chatbot/gateway --region ${AWS_REGION}

# Re-push image if needed
docker push ${ECR_REGISTRY}/llm-chatbot/gateway:latest
```

### Problem: CrashLoopBackOff

**Symptoms**: Pods restart repeatedly

**Solution**:
```bash
# Check logs
kubectl logs <pod-name> -n chatbot --previous

# Common causes:
# - Missing environment variables
# - Database connection errors
# - OpenAI API key invalid

# Verify secrets
kubectl get secrets -n chatbot
kubectl describe secret llm-chatbot-secret -n chatbot
```

### Problem: LoadBalancer stuck in pending

**Symptoms**: `External-IP` shows `<pending>`

**Solution**:
```bash
# Check ALB controller
kubectl get deployment -n kube-system aws-load-balancer-controller

# Verify ALB controller logs
kubectl logs -n kube-system deployment/aws-load-balancer-controller --tail=50

# Restart ALB controller
kubectl rollout restart deployment/aws-load-balancer-controller -n kube-system
```

### Problem: DynamoDB permission denied

**Symptoms**: "User: arn:aws:sts::... is not authorized to perform: dynamodb:..."

**Solution**:
```bash
# Verify IRSA is configured
kubectl describe sa chatbot-workload -n chatbot

# Check IAM role permissions
aws iam get-role-policy \
  --role-name llm-chatbot-workload \
  --policy-name llm-chatbot-inline-policy

# Verify service account using role
kubectl set serviceaccount deployment/gateway chatbot-workload -n chatbot
kubectl rollout restart deployment/gateway -n chatbot
```

### Problem: SQS queue errors

**Symptoms**: AI worker not processing messages

**Solution**:
```bash
# Check queue exists
aws sqs list-queues --region ${AWS_REGION}

# Check queue attributes
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/123456789012/ai-jobs.fifo \
  --attribute-names ApproximateNumberOfMessages

# Check DLQ
aws sqs receive-message \
  --queue-url https://sqs.us-east-1.amazonaws.com/123456789012/ai-jobs-dlq.fifo \
  --region ${AWS_REGION}
```

---

## Rollback Procedures

### Complete Rollback

**Step 1: Delete Helm Release**

```bash
helm uninstall llm-chatbot -n chatbot
```

**Step 2: Delete Namespace**

```bash
kubectl delete namespace chatbot
```

**Step 3: Delete EKS Cluster**

```bash
eksctl delete cluster --name llm-chatbot --region ${AWS_REGION}
```

**Step 4: Delete AWS Resources**

```bash
# Delete DynamoDB tables
aws dynamodb delete-table --table-name conversations
aws dynamodb delete-table --table-name messages
aws dynamodb delete-table --table-name settings

# Delete SQS queues
aws sqs delete-queue --queue-url <queue-url>
aws sqs delete-queue --queue-url <dlq-url>

# Delete IAM role
aws iam delete-role-policy --role-name llm-chatbot-workload \
  --policy-name llm-chatbot-inline-policy
aws iam delete-role --role-name llm-chatbot-workload

# Delete ECR repositories
for repo in frontend gateway settings conversations messages ai-worker; do
  aws ecr delete-repository --repository-name llm-chatbot/$repo --force
done
```

### Partial Rollback (Helm Release Only)

```bash
# Rollback to previous Helm release
helm rollback llm-chatbot -n chatbot

# Or delete and reinstall
helm uninstall llm-chatbot -n chatbot
helm install llm-chatbot ./infra/helm/chatapp -n chatbot
```

### Pod Recovery

```bash
# Restart a specific pod
kubectl delete pod <pod-name> -n chatbot

# Restart entire deployment
kubectl rollout restart deployment/<service-name> -n chatbot

# Scale deployment up/down
kubectl scale deployment/<service-name> --replicas=3 -n chatbot
```

---

## Post-Deployment

### Documentation

- [ ] Save LoadBalancer URLs for future reference
- [ ] Document DNS mapping (domain → ALB)
- [ ] Create runbooks for common operations
- [ ] Document backup and restore procedures

### Operational Setup

- [ ] Configure monitoring dashboards (CloudWatch/Grafana)
- [ ] Setup alerts for critical metrics
- [ ] Configure backup strategy for DynamoDB
- [ ] Setup log retention and archival

### Security Hardening

- [ ] Enable encryption at rest for EBS volumes
- [ ] Configure WAF rules on ALB
- [ ] Setup GuardDuty for threat detection
- [ ] Enable audit logging
- [ ] Regular security updates

### Cost Optimization

- [ ] Enable AWS Cost Explorer
- [ ] Set up budget alerts
- [ ] Review unused resources quarterly
- [ ] Consider Spot Instances for non-critical workloads

### Team Training

- [ ] Onboard team on kubectl commands
- [ ] Create deployment procedures
- [ ] Setup incident response procedures
- [ ] Document escalation paths

---

## Quick Reference Commands

### Kubernetes

```bash
# Get all resources
kubectl get all -n chatbot

# Describe resource
kubectl describe pod <name> -n chatbot

# View logs
kubectl logs deployment/<name> -n chatbot
kubectl logs deployment/<name> -n chatbot --previous
kubectl logs deployment/<name> -n chatbot -f  # Follow

# Execute command in pod
kubectl exec -it <pod-name> -n chatbot -- /bin/bash

# Port forward
kubectl port-forward svc/gateway 8080:8080 -n chatbot

# Port forward local
kubectl port-forward svc/gateway 8080:8080 -n chatbot &
```

### Helm

```bash
# List releases
helm list -n chatbot

# Show values
helm get values llm-chatbot -n chatbot

# Upgrade
helm upgrade llm-chatbot ./infra/helm/chatapp -n chatbot

# Rollback
helm rollout history llm-chatbot -n chatbot
helm rollback llm-chatbot <revision> -n chatbot
```

### AWS

```bash
# EKS
eksctl get clusters
eksctl get nodegroup --cluster llm-chatbot

# DynamoDB
aws dynamodb list-tables
aws dynamodb scan --table-name conversations

# SQS
aws sqs list-queues
aws sqs get-queue-attributes --queue-url <url> --attribute-names All

# ECR
aws ecr describe-repositories
aws ecr describe-images --repository-name llm-chatbot/gateway

# CloudWatch
aws logs tail /aws/eks/llm-chatbot/gateway --follow
aws logs describe-log-groups
```

---

## Support & Escalation

**For Infrastructure Issues**:
1. Check troubleshooting guide
2. Review pod logs: `kubectl logs <pod> -n chatbot`
3. Check AWS console for resource status
4. Review CloudWatch metrics

**For Application Issues**:
1. Check microservice logs
2. Verify API connectivity: `curl http://<service>:8080/health`
3. Check DynamoDB tables
4. Verify SQS queues

**Emergency Contacts**:
- Platform Team: [contact info]
- On-Call: [contact info]
- Escalation: [contact info]

---

## Checklist - Final Verification

Before considering deployment complete:

```
✅ Prerequisites
  [ ] All tools installed and verified
  [ ] AWS account configured
  [ ] Credentials available

✅ AWS Configuration
  [ ] DynamoDB tables created and active
  [ ] SQS queues created
  [ ] Secrets Manager configured
  [ ] IAM roles created

✅ Container Registry
  [ ] ECR repositories created
  [ ] 6 services built and pushed
  [ ] Images can be pulled

✅ EKS Cluster
  [ ] Cluster created and ready
  [ ] 4+ nodes in Ready state
  [ ] kubectl can connect
  [ ] ALB controller running

✅ Helm Deployment
  [ ] All 6 services deployed
  [ ] All pods in Running state
  [ ] LoadBalancers have external IPs

✅ Integration
  [ ] IRSA configured
  [ ] Service accounts created
  [ ] IAM permissions verified

✅ Testing
  [ ] Gateway /health endpoint responds
  [ ] Chat API works end-to-end
  [ ] Messages processed by AI worker
  [ ] Logs visible in CloudWatch

✅ Documentation
  [ ] LoadBalancer URLs documented
  [ ] Team trained
  [ ] Runbooks created
  [ ] Monitoring configured

[ ] ✅ DEPLOYMENT COMPLETE!
```

---

**Next Steps**: 
1. Access Frontend: `http://<FRONTEND_LB>`
2. Test Chat: Send message via frontend or API
3. Monitor: Check CloudWatch logs and metrics
4. Scale: Adjust HPA thresholds based on traffic

**Good luck! 🚀**

---

## Advanced Troubleshooting: AI Worker & SQS Deep Dive

### AI Worker Background Processing Issues

**Problem: AI Worker not polling SQS queue**

**Symptoms**:
- Queue has messages but nothing processing
- AI Worker pod running but idle
- No new messages in Messages table

**Diagnostic Steps**:
\\\ash
# 1. Verify worker is actually polling
kubectl logs -n chatbot deployment/ai-worker -f --tail=20 | grep -i poll

# Expected: "[DEBUG] Polling queue for jobs..."

# 2. Check queue has messages
aws sqs get-queue-attributes \\
  --queue-url \ \\
  --attribute-names ApproximateNumberOfMessages

# 3. Check if worker has SQS permissions
kubectl exec -it <ai-worker-pod> -n chatbot -- \\
  aws sqs list-queues --region us-east-1

# 4. Check worker environment variables
kubectl exec -it <ai-worker-pod> -n chatbot -- env | grep -i sqs

# Expected: SQS_QUEUE_URL, AWS_REGION, etc.
\\\

**Solutions**:
\\\ash
# Restart worker
kubectl rollout restart deployment/ai-worker -n chatbot

# Check and update environment variables
kubectl set env deployment/ai-worker \\
  SQS_QUEUE_URL=\ \\
  POLL_INTERVAL=5 \\
  -n chatbot

# Verify SQS role permissions
aws iam get-role-policy \\
  --role-name llm-chatbot-workload \\
  --policy-name llm-chatbot-inline-policy | jq '.PolicyDocument.Statement[] | select(.Action[] | contains(\"sqs\"))'
\\\

### SQS Queue Health Monitoring

**Critical Health Metrics**:
\\\ash
# Check main queue depth
aws sqs get-queue-attributes --queue-url \ --attribute-names ApproximateNumberOfMessages

# Check messages in flight
aws sqs get-queue-attributes --queue-url \ --attribute-names ApproximateNumberOfMessagesNotVisible

# Check DLQ (dead letter queue)
aws sqs get-queue-attributes --queue-url \ --attribute-names ApproximateNumberOfMessages

# Combined health check
echo "=== Queue Health ==="
echo "Main Queue - Waiting: \"
echo "Main Queue - Processing: \"
echo "DLQ - Failed: \"
echo "AI Workers: \"
\\\

**Normal State**:
- Main queue waiting: 0-5
- Main queue processing: 1-10 (number of active workers)
- DLQ failed: 0
- Worker pods: 1-10 (auto-scaling based on load)

**Alert Thresholds**:
- Queue waiting > 100 (backlog building)
- DLQ failed > 10 (failures occurring)
- Worker pod restarts > 5 in 5 minutes (stability issue)
- Response time > 40 seconds (degradation)

### Dead Letter Queue (DLQ) Recovery

**Problem: Messages failing and moving to DLQ**

**Investigation Steps**:
\\\ash
# 1. Count DLQ messages
aws sqs get-queue-attributes --queue-url \ --attribute-names ApproximateNumberOfMessages

# 2. Read a sample failed message
aws sqs receive-message --queue-url \ --max-number-of-messages 1 | jq '.Messages[0].Body'

# 3. Find worker logs for that job
job_id="<id-from-failed-message>"
kubectl logs -n chatbot deployment/ai-worker --all-containers=true | grep \

# 4. Check for OpenAI API issues
kubectl logs -n chatbot deployment/ai-worker | grep -i "429\\|timeout\\|rate"

# 5. Check DynamoDB throttling
aws cloudwatch get-metric-statistics \\
  --namespace AWS/DynamoDB \\
  --metric-name UserErrors \\
  --dimensions Name=TableName,Value=messages \\
  --start-time \ \\
  --end-time \ \\
  --period 300 --statistics Sum
\\\

**Recovery Process**:
\\\ash
# 1. Fix root cause (check logs above)
# 2. Wait for worker to stabilize
# 3. Requeue messages from DLQ back to main queue
aws sqs receive-message --queue-url \ --max-number-of-messages 10 | \\
jq -r '.Messages[] | .Body' | \\
while read msg; do
  user_id=\
  aws sqs send-message --queue-url \ \\
    --message-body \"\\" \\
    --message-group-id \"\\"
done

# 4. Monitor reprocessing progress
watch -n 3 'aws sqs get-queue-attributes --queue-url \ --attribute-names ApproximateNumberOfMessages'

# 5. Verify messages are being processed
kubectl logs -n chatbot deployment/ai-worker -f --tail=20
\\\

### DynamoDB Troubleshooting

**Problem: DynamoDB writes timing out**

**Check consumed capacity**:
\\\ash
aws cloudwatch get-metric-statistics \\
  --namespace AWS/DynamoDB \\
  --metric-name ConsumedWriteCapacityUnits \\
  --dimensions Name=TableName,Value=messages \\
  --start-time \ \\
  --end-time \ \\
  --period 300 --statistics Sum,Average
\\\

**Verify TTL is working**:
\\\ash
# Check TTL status on conversations table
aws dynamodb describe-table --table-name conversations | jq '.Table.TimeToLiveDescription'

# Check TTL status on messages table
aws dynamodb describe-table --table-name messages | jq '.Table.TimeToLiveDescription'

# Expected output: \"TimeToLiveStatus\": \"ENABLED\"
\\\

**Monitor Auto-Cleanup Progress**:
\\\ash
# Count items in table
aws dynamodb scan --table-name messages --select COUNT --query 'Count'

# Monitor over time (should decrease as TTL deletes old items)
while true; do
  count=\
  echo "\05/24/2026 22:31:19: Messages count = \"
  sleep 60
done
\\\

---

## Summary: Key Operational Responsibilities

**Daily**:
- Monitor queue depth (should be 0-5)
- Check no DLQ messages
- Verify all pods are running
- Review error logs

**Weekly**:
- Cost analysis review
- Backup verification
- Capacity planning check
- Documentation update

**Monthly**:
- Full disaster recovery drill
- Security audit
- Performance optimization
- Credential rotation

**Quarterly**:
- IAM permission review
- Compliance audit
- Capacity rebalancing
- Architecture review

---

**Documentation Version**: 2.0  
**Last Updated**: May 24, 2026  
**Status**: Production Ready  
**Runbook Owner**: Infrastructure Team  

For questions or issues, refer to: [infra/cleanup/README.md](./cleanup/README.md)
