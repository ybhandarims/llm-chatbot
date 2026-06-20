# Implementation Runbook: LLM Chatbot Budget-Conscious Architecture

## Overview
This runbook provides step-by-step instructions to implement the budget-conscious production architecture from local development to AWS EKS production deployment.

**Time Estimate**: 4-6 hours (depending on your experience level)

## Prerequisites Checklist

Before starting, ensure you have:

```
☐ AWS Account with sufficient permissions
☐ Docker Desktop installed
☐ AWS CLI configured (aws configure)
☐ kubectl installed
☐ eksctl installed
☐ Helm installed (optional)
☐ OpenAI API Key
☐ Text editor/IDE (VS Code recommended)
☐ Terminal/PowerShell access
```

### Installation Links
- Docker: https://www.docker.com/products/docker-desktop
- AWS CLI: https://aws.amazon.com/cli/
- kubectl: https://kubernetes.io/docs/tasks/tools/
- eksctl: https://eksctl.io/installation/
- Helm: https://helm.sh/docs/intro/install/

---

## PHASE 1: LOCAL DEVELOPMENT SETUP
**Duration: 30 minutes**

### Step 1.1: Prepare Environment

```bash
# Navigate to microservices directory
cd "c:\Users\Yogesh Bhandari\Downloads\Kripa AI Batch\github\llm-chatbot\microservices"

# Verify structure
dir

# Expected output: Shows all services (ai-service, gateway, etc.)
```

**Success Criteria**: All service directories visible

### Step 1.2: Create Environment File

```bash
# Copy example to .env
Copy-Item -Path .env.example -Destination .env

# Open .env in editor and update
# Required changes:
# - Replace sk-your-key-here with your actual OPENAI_API_KEY
# - Update AWS credentials if needed (localstack defaults are OK for local)

# Quick edit (replace with your real key):
# OPENAI_API_KEY=sk-your-actual-openai-key-here
```

**Expected File Location**: `microservices/.env`

**Success Criteria**: .env file exists with your OpenAI API key

### Step 1.3: Verify Docker Installation

```bash
# Check Docker is running
docker --version

# Expected output: Docker version 20.10.x or higher

# Check Docker daemon
docker ps

# Expected output: Shows container list (might be empty)
```

**Success Criteria**: Docker commands execute without errors

### Step 1.4: Build All Docker Images

```bash
# Build all services
docker-compose build

# This will take 3-5 minutes
# Watch for progress bars for each service:
# - gateway
# - ai-service
# - conversations-service
# - messages-service
# - settings-service
# - frontend
# - localstack
```

**Success Criteria**: All images built successfully (no red errors)

### Step 1.5: Start All Services

```bash
# Start in background
docker-compose up -d

# Watch startup progress
docker-compose ps

# Expected output:
# NAME                    STATUS
# gateway                 Up X seconds
# ai-service              Up X seconds
# conversations-service   Up X seconds
# ... etc
```

**Success Criteria**: All containers show "Up" status

### Step 1.6: Wait for Initialization

```bash
# Wait for LocalStack to create tables
Start-Sleep -Seconds 30

# Check if tables were created
docker-compose logs localstack | Select-String "initialization complete"
```

**Success Criteria**: LocalStack initialization message appears in logs

### Step 1.7: Verify Services Are Responsive

```bash
# Check Gateway health
curl http://localhost:8080/health

# Expected output:
# {"status":"ok","service":"gateway"}

# Check Frontend
curl http://localhost:3000/

# Expected output: HTML content (React app)

# Check Settings Service
curl http://localhost:8001/health

# Expected output:
# {"status":"ok","service":"settings"}
```

**Success Criteria**: All endpoints respond with 200 status code

---

## PHASE 2: LOCAL TESTING & VALIDATION
**Duration: 45 minutes**

### Step 2.1: Test Settings API

```bash
# Get default settings
$response = curl.exe -s http://localhost:8001/settings
Write-Host $response

# Expected output includes: system_prompt, model, temperature

# Update settings
$body = @{
    system_prompt = "You are a helpful coding assistant"
    temperature = 0.5
} | ConvertTo-Json

curl.exe -X POST http://localhost:8001/settings `
  -H "Content-Type: application/json" `
  -d $body

# Expected output: {"status": "updated", "settings": {...}}
```

**Success Criteria**: Settings API responds correctly

### Step 2.2: Test Conversations API

```bash
# Create conversation
$conv = curl.exe -s -X POST http://localhost:8002/conversations `
  -H "Content-Type: application/json" `
  -d '{"title": "Test Conversation"}'

# Parse response to get conversation ID
$convId = ($conv | ConvertFrom-Json).id
Write-Host "Created conversation: $convId"

# List conversations
curl.exe http://localhost:8002/conversations

# Expected output: Array with our new conversation

# Get specific conversation
curl.exe http://localhost:8002/conversations/$convId

# Expected output: Conversation details
```

**Success Criteria**: Can create and retrieve conversations

### Step 2.3: Test Messages API

```bash
# Create a message
$msg = @{
    conversation_id = $convId
    role = "user"
    message = "Hello, what is the weather?"
} | ConvertTo-Json

curl.exe -X POST http://localhost:8003/messages `
  -H "Content-Type: application/json" `
  -d $msg

# Expected output: Message created with ID and timestamp

# Get messages for conversation
curl.exe http://localhost:8003/conversations/$convId

# Expected output: Array with messages
```

**Success Criteria**: Can create and retrieve messages

### Step 2.4: Test Async Chat Flow (Main Test)

```bash
# THIS IS THE KEY TEST - Async message processing

# Send chat message
$chat = @{
    message = "Hello! What is 2+2?"
    title = "Math Question"
} | ConvertTo-Json

$response = curl.exe -X POST http://localhost:8080/api/chat/send `
  -H "Content-Type: application/json" `
  -d $chat | ConvertFrom-Json

Write-Host "Status: $($response.status)"
Write-Host "Job ID: $($response.job_id)"
$jobId = $response.job_id
$conversationId = $response.conversation_id

# Expected output:
# Status: accepted
# Job ID: uuid-here
# Message: Your message is being processed...
```

**Success Criteria**: Chat endpoint returns job_id and conversation_id

### Step 2.5: Monitor Queue Processing

```bash
# Check SQS queue stats
curl.exe http://localhost:8080/api/debug/queue-stats

# Expected output shows messages in queue

# Wait a few seconds for AI Worker to process
Start-Sleep -Seconds 5

# Check queue stats again
curl.exe http://localhost:8080/api/debug/queue-stats

# Expected: Messages should decrease as they're processed

# Check AI worker logs
docker-compose logs ai-worker | Select-String "Processing job"

# Expected: See processing messages in logs
```

**Success Criteria**: Queue shows processing activity

### Step 2.6: Verify Response Storage

```bash
# Get conversation to see AI response
curl.exe http://localhost:8080/api/conversations/$conversationId | ConvertFrom-Json | ConvertTo-Json

# Expected output: Should show both user message and AI response
# "role": "user"/"assistant"
# "message": contains the conversation
```

**Success Criteria**: AI response is stored in database

### Step 2.7: Check Database Content

```bash
# List DynamoDB tables
aws dynamodb list-tables --endpoint-url http://localhost:4566

# Expected output: 
# - conversations
# - messages
# - settings

# Scan conversations table
aws dynamodb scan --table-name conversations `
  --endpoint-url http://localhost:4566 `
  --max-items 5

# Expected: Shows our test data
```

**Success Criteria**: Data persisted in DynamoDB

### Step 2.8: View Service Logs

```bash
# Check each service for errors
docker-compose logs --tail 20 gateway
docker-compose logs --tail 20 ai-worker
docker-compose logs --tail 20 conversations-service

# Look for any ERROR messages in red
# Success means mostly INFO messages
```

**Success Criteria**: No ERROR messages in logs

---

## PHASE 3: DOCKER PUSH TO ECR
**Duration: 30 minutes**

### Step 3.1: Setup ECR Repositories

```bash
# Set your AWS account ID and region
$AWS_ACCOUNT_ID = "123456789012"  # Replace with your account ID
$AWS_REGION = "us-east-1"
$REGISTRY = "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

# Get your account ID
aws sts get-caller-identity | ConvertFrom-Json | Select-Object Account

# Create repositories (if not exist)
$services = @("gateway", "ai-service", "conversations-service", "messages-service", "settings-service", "frontend")

foreach ($service in $services) {
    Write-Host "Creating ECR repository for $service..."
    aws ecr create-repository --repository-name llm-chatbot/$service --region $AWS_REGION 2>$null
}

# Expected: Repositories created successfully
```

**Success Criteria**: ECR repositories exist in AWS console

### Step 3.2: Login to ECR

```bash
# Get login token and login to Docker
aws ecr get-login-password --region $AWS_REGION | `
  docker login --username AWS --password-stdin $REGISTRY

# Expected output: Login Succeeded
```

**Success Criteria**: Docker login successful

### Step 3.3: Tag Docker Images

```bash
# Stop running containers first
docker-compose down

# Tag each image
$services = @("gateway", "ai-service", "conversations-service", "messages-service", "settings-service", "frontend")

foreach ($service in $services) {
    $imageName = if ($service -eq "ai-service") { "ai-service" } else { $service }
    
    Write-Host "Tagging $imageName..."
    docker tag "llm-chatbot-$imageName" "$REGISTRY/llm-chatbot/$imageName`:latest"
}

# Verify tags
docker images | Select-String "llm-chatbot"

# Expected: Shows all tagged images with ECR registry URL
```

**Success Criteria**: All images tagged with ECR registry

### Step 3.4: Push Images to ECR

```bash
# Push all images
foreach ($service in $services) {
    Write-Host "Pushing $service to ECR..."
    docker push "$REGISTRY/llm-chatbot/$service`:latest"
}

# Expected: Progress bars showing upload complete

# Verify in ECR
aws ecr describe-images --repository-name llm-chatbot/gateway --region $AWS_REGION

# Expected: Shows image details
```

**Success Criteria**: All images visible in AWS ECR console

---

## PHASE 4: EKS CLUSTER CREATION
**Duration: 20-30 minutes**

### Step 4.1: Create EKS Cluster

```bash
# Create cluster (takes 15-20 minutes)
Write-Host "Creating EKS cluster... (This will take 15-20 minutes)"

eksctl create cluster `
  --name llm-chatbot `
  --version 1.27 `
  --region us-east-1 `
  --nodegroup-name standard `
  --node-type t3.medium `
  --nodes 3 `
  --nodes-min 2 `
  --nodes-max 10 `
  --managed `
  --alb-ingress-access

# Expected: Cluster creation in progress message
# Wait for completion (get coffee ☕)
```

**Success Criteria**: Cluster shows "CREATE_COMPLETE" in AWS console

### Step 4.2: Verify Cluster Creation

```bash
# Update kubeconfig
aws eks update-kubeconfig --name llm-chatbot --region us-east-1

# Verify kubectl can connect
kubectl cluster-info

# Expected output: Shows cluster endpoint

# Check nodes
kubectl get nodes

# Expected output: 3 nodes in Ready state
```

**Success Criteria**: kubectl commands work, 3 nodes available

### Step 4.3: Install AWS Load Balancer Controller

```bash
# Add Helm repository
helm repo add eks https://aws.github.io/eks-charts
helm repo update

# Install load balancer controller
helm install aws-load-balancer-controller eks/aws-load-balancer-controller `
  -n kube-system `
  --set clusterName=llm-chatbot

# Verify installation
kubectl get deployment -n kube-system aws-load-balancer-controller

# Expected: Shows deployment with 2 replicas
```

**Success Criteria**: AWS Load Balancer Controller deployed

---

## PHASE 5: KUBERNETES DEPLOYMENT
**Duration: 15 minutes**

### Step 5.1: Prepare Kubernetes Manifests

```bash
# Update image URLs in k8s-manifests.yaml
# Replace: llm-chatbot/gateway:latest
# With: $REGISTRY/llm-chatbot/gateway:latest

$registryPath = "$REGISTRY/llm-chatbot"

# Read manifest and replace
$manifest = Get-Content k8s-manifests.yaml
$manifest = $manifest -replace 'llm-chatbot/gateway', "$registryPath/gateway"
$manifest = $manifest -replace 'llm-chatbot/ai-service', "$registryPath/ai-service"
$manifest = $manifest -replace 'llm-chatbot/conversations-service', "$registryPath/conversations-service"
$manifest = $manifest -replace 'llm-chatbot/messages-service', "$registryPath/messages-service"
$manifest = $manifest -replace 'llm-chatbot/settings-service', "$registryPath/settings-service"
$manifest = $manifest -replace 'llm-chatbot/frontend', "$registryPath/frontend"

# Save updated manifest
$manifest | Set-Content k8s-manifests-updated.yaml

Write-Host "Manifests updated successfully"
```

**Success Criteria**: k8s-manifests-updated.yaml created

### Step 5.2: Create Namespace and Secrets

```bash
# Create namespace
kubectl create namespace chatbot

# Expected: namespace/chatbot created

# Create secrets
kubectl create secret generic chatbot-secrets `
  --from-literal=OPENAI_API_KEY='your-actual-api-key' `
  --from-literal=AWS_ACCESS_KEY_ID='your-aws-key' `
  --from-literal=AWS_SECRET_ACCESS_KEY='your-aws-secret' `
  -n chatbot

# Expected: secret/chatbot-secrets created

# Verify secret
kubectl get secrets -n chatbot

# Expected: chatbot-secrets listed
```

**Success Criteria**: Namespace and secrets created

### Step 5.3: Deploy Manifests

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s-manifests-updated.yaml

# Expected: Multiple resources created

# Watch deployment progress
kubectl get deployments -n chatbot -w

# Press Ctrl+C after all show "3/3" replicas
```

**Success Criteria**: All deployments showing READY 3/3

### Step 5.4: Verify Deployments

```bash
# Check all pods running
kubectl get pods -n chatbot

# Expected output:
# NAME                                  READY   STATUS    RESTARTS
# gateway-xxx                           1/1     Running
# settings-xxx                          1/1     Running
# conversations-xxx                     1/1     Running
# messages-xxx                          1/1     Running
# frontend-xxx                          1/1     Running
# ai-worker-xxx                         1/1     Running

# Check services
kubectl get svc -n chatbot

# Expected: Shows gateway and frontend LoadBalancer services
```

**Success Criteria**: All pods in Running state, services created

### Step 5.5: Get Load Balancer URL

```bash
# Get external IP/hostname
kubectl get svc -n chatbot gateway -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'

# This might take 1-2 minutes to populate
# If empty, wait and retry

# Once available, you'll get something like:
# aaa-gateway-12345.us-east-1.elb.amazonaws.com

$GATEWAY_URL = kubectl get svc -n chatbot gateway -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
Write-Host "Gateway URL: $GATEWAY_URL"
```

**Success Criteria**: Load balancer URL displayed

### Step 5.6: Get Frontend URL

```bash
# Get frontend LoadBalancer URL
$FRONTEND_URL = kubectl get svc -n chatbot frontend -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
Write-Host "Frontend URL: $FRONTEND_URL"

# Open in browser
Start-Process "http://$FRONTEND_URL"
```

**Success Criteria**: Frontend loads in browser

---

## PHASE 6: PRODUCTION TESTING
**Duration: 30 minutes**

### Step 6.1: Test Gateway Health

```bash
# Test health endpoint
curl.exe "http://$GATEWAY_URL/health"

# Expected output:
# {"status":"ok","service":"gateway"}
```

**Success Criteria**: Gateway responds with 200 status

### Step 6.2: Test Settings API

```bash
# Get settings
curl.exe "http://$GATEWAY_URL/api/settings"

# Expected output: Settings object with defaults

# Update settings
$body = @{
    system_prompt = "You are a production AI assistant"
    temperature = 0.6
} | ConvertTo-Json

curl.exe -X POST "http://$GATEWAY_URL/api/settings" `
  -H "Content-Type: application/json" `
  -d $body

# Expected output: {"status": "updated", ...}
```

**Success Criteria**: Settings API works in production

### Step 6.3: Test Chat Flow

```bash
# Send test message
$chat = @{
    message = "What is the capital of France?"
    title = "Geography Question"
} | ConvertTo-Json

$response = curl.exe -X POST "http://$GATEWAY_URL/api/chat/send" `
  -H "Content-Type: application/json" `
  -d $chat | ConvertFrom-Json

Write-Host "Status: $($response.status)"
Write-Host "Job ID: $($response.job_id)"

# Store job ID for later
$prodJobId = $response.job_id
$prodConvId = $response.conversation_id
```

**Success Criteria**: Chat endpoint returns accepted status

### Step 6.4: Monitor AI Processing

```bash
# Check queue stats
curl.exe "http://$GATEWAY_URL/api/debug/queue-stats"

# Wait for processing
Start-Sleep -Seconds 10

# Get conversation to verify response stored
curl.exe "http://$GATEWAY_URL/api/conversations/$prodConvId"

# Expected: Shows user message and AI response
```

**Success Criteria**: AI response stored and retrieved

### Step 6.5: Check Pod Logs

```bash
# Check AI worker logs
kubectl logs -n chatbot -l app=ai-worker --tail 20

# Expected: See processing logs

# Check gateway logs
kubectl logs -n chatbot -l app=gateway --tail 20

# Expected: See request logs
```

**Success Criteria**: Logs show normal operations

### Step 6.6: View Pod Metrics

```bash
# Check resource usage
kubectl top pods -n chatbot

# Expected output: CPU and Memory usage for each pod

# Check node metrics
kubectl top nodes

# Expected: Nodes showing resource usage
```

**Success Criteria**: Metrics available and reasonable

---

## PHASE 7: MONITORING SETUP
**Duration: 20 minutes**

### Step 7.1: Enable CloudWatch Logging

```bash
# Check if logs are flowing to CloudWatch
aws logs describe-log-groups --region us-east-1 | ConvertFrom-Json

# Expected: Shows /aws/eks/chatbot log groups

# View recent logs
aws logs tail /aws/eks/chatbot/gateway --follow --region us-east-1

# Press Ctrl+C to stop
```

**Success Criteria**: Logs visible in CloudWatch

### Step 7.2: Check EKS Monitoring

```bash
# View cluster events
kubectl get events -n chatbot --sort-by='.lastTimestamp'

# Expected: Shows recent events

# Check for warnings/errors
kubectl get events -n chatbot | Select-String "Warning\|Error"

# If nothing shows, that's good!
```

**Success Criteria**: No critical errors in events

### Step 7.3: Setup HPA Monitoring

```bash
# Check HPA status
kubectl get hpa -n chatbot

# Expected output:
# NAME              REFERENCE                TARGETS   MINPODS   MAXPODS
# gateway-hpa       Deployment/gateway       5%/70%    3         10

# If TARGETS show <unknown>, wait 1-2 minutes for metrics to populate
```

**Success Criteria**: HPA shows metrics or targets

---

## PHASE 8: CLEANUP & DOCUMENTATION
**Duration: 15 minutes**

### Step 8.1: Save Deployment URLs

```bash
# Create deployment summary
$summary = @"
LLM Chatbot Production Deployment Summary
==========================================

Gateway URL: $GATEWAY_URL
Frontend URL: $FRONTEND_URL

AWS Account: $AWS_ACCOUNT_ID
Region: $AWS_REGION
Cluster: llm-chatbot

Date Deployed: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

Key Resources:
- EKS Cluster: llm-chatbot
- Namespace: chatbot
- Services: gateway, frontend (LoadBalancer)
- Deployments: gateway, ai-worker, settings, conversations, messages, frontend

Next Steps:
1. Monitor logs in CloudWatch
2. Test with load (wrk or similar)
3. Setup CI/CD pipeline
4. Configure custom domain
5. Setup SSL certificates
"@

$summary | Set-Content deployment-summary.txt
Write-Host "Deployment summary saved to deployment-summary.txt"
```

**Success Criteria**: Summary file created

### Step 8.2: Document Database Access

```bash
# Get DynamoDB table names
aws dynamodb list-tables --region us-east-1

# Create database access guide
$dbGuide = @"
DynamoDB Tables
===============

Production Tables:
- conversations (user_id + conversation_id)
- messages (conversation_id + message_id)
- settings (user_id + setting_key)

Access from CLI:
aws dynamodb scan --table-name conversations --region us-east-1 --max-items 5

Backup: Use AWS DynamoDB point-in-time recovery
"@

$dbGuide | Add-Content deployment-summary.txt
```

**Success Criteria**: Database access documented

### Step 8.3: Stop Local Development Environment

```bash
# Stop local services (to free resources)
cd microservices
docker-compose down

# Verify stopped
docker-compose ps

# Expected: All containers stopped
```

**Success Criteria**: Local containers stopped

### Step 8.4: Final Verification Checklist

```bash
# Create checklist
$checklist = @"
✓ Local testing completed successfully
✓ Docker images pushed to ECR
✓ EKS cluster created (3 nodes)
✓ Kubernetes manifests deployed
✓ All pods running
✓ Gateway health check passing
✓ Chat API responding
✓ AI worker processing messages
✓ Frontend accessible
✓ CloudWatch logs enabled
✓ HPA configured
✓ Deployment URLs documented
"@

Write-Host $checklist
```

**Success Criteria**: All checkboxes complete

---

## TROUBLESHOOTING GUIDE

### Issue: Docker container won't start

```bash
# Check logs
docker-compose logs <service-name>

# Check port conflicts
netstat -ano | findstr :8080

# Remove and rebuild
docker-compose down
docker-compose build --no-cache <service-name>
docker-compose up -d
```

### Issue: SQS jobs not processing

```bash
# Check AI worker logs
kubectl logs -n chatbot -l app=ai-worker

# Check queue
kubectl exec -it deployment/gateway -n chatbot -- bash
curl http://gateway:8080/api/debug/queue-stats

# Restart workers
kubectl rollout restart deployment/ai-worker -n chatbot
```

### Issue: Pod keeps crashing

```bash
# Check pod events
kubectl describe pod <pod-name> -n chatbot

# Check logs
kubectl logs <pod-name> -n chatbot --previous

# Check resource limits
kubectl describe deployment <deployment-name> -n chatbot

# Increase resources if needed
kubectl patch deployment <deployment-name> -n chatbot --patch '{"spec":{"template":{"spec":{"containers":[{"name":"<container>","resources":{"limits":{"memory":"2Gi"}}}]}}}}'
```

### Issue: Can't access frontend

```bash
# Check if service has external IP
kubectl get svc frontend -n chatbot

# If EXTERNAL-IP is <pending>:
kubectl describe svc frontend -n chatbot

# Check ALB controller logs
kubectl logs -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller
```

### Issue: DynamoDB connection errors

```bash
# Verify AWS credentials
aws sts get-caller-identity

# Check IAM permissions
aws iam get-user

# Verify table exists
aws dynamodb describe-table --table-name conversations --region us-east-1

# Check pod can reach DynamoDB
kubectl exec -it deployment/conversations-service -n chatbot -- bash
aws dynamodb list-tables --region us-east-1
```

---

## ROLLBACK PROCEDURE

If something goes wrong:

### Step 1: Rollback Kubernetes Deployment

```bash
# Check rollout history
kubectl rollout history deployment/gateway -n chatbot

# Rollback to previous version
kubectl rollout undo deployment/gateway -n chatbot

# Or rollback to specific revision
kubectl rollout undo deployment/gateway -n chatbot --to-revision=1
```

### Step 2: Scale Down If Needed

```bash
# Temporarily stop pods
kubectl scale deployment gateway -n chatbot --replicas=0

# Investigate issue
# Then scale back up
kubectl scale deployment gateway -n chatbot --replicas=3
```

### Step 3: Re-deploy from Scratch

```bash
# Delete namespace (removes all resources)
kubectl delete namespace chatbot

# Wait 30 seconds
Start-Sleep -Seconds 30

# Redeploy
kubectl create namespace chatbot
kubectl apply -f k8s-manifests-updated.yaml
```

---

## SUCCESS CRITERIA - FINAL CHECKLIST

Before considering deployment complete, verify:

```
Production Deployment Complete When:
====================================

✓ All 7 services running (kubectl get pods -n chatbot)
✓ All pods show "Running" status
✓ All pods show "1/1" ready
✓ Gateway LoadBalancer has external IP
✓ Frontend LoadBalancer has external IP
✓ Gateway /health endpoint responds
✓ Settings API accessible
✓ Chat API accepts messages
✓ AI worker processes messages (check logs)
✓ Messages stored in DynamoDB
✓ No error messages in pod logs
✓ HPA configured and monitoring
✓ CloudWatch logs flowing
✓ Deployment summary documented
✓ Team has access URLs
✓ DynamoDB backups enabled
```

---

## POST-DEPLOYMENT TASKS

After successful deployment:

1. **Configure Custom Domain**
   - Add CNAME record pointing to LoadBalancer URL
   - Setup SSL/TLS certificates (ACM)

2. **Setup CI/CD Pipeline**
   - Configure GitHub Actions or similar
   - Auto-build on code push
   - Auto-deploy to EKS

3. **Configure Backups**
   ```bash
   aws dynamodb update-continuous-backups \
     --table-name conversations \
     --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
   ```

4. **Setup Alarms**
   - CPU utilization > 80%
   - Memory utilization > 85%
   - SQS queue depth > 100
   - Pod restarts > 0

5. **Document Runbooks**
   - Scaling procedures
   - Incident response
   - Emergency contacts

---

## QUICK REFERENCE: KEY COMMANDS

```bash
# Kubernetes
kubectl get pods -n chatbot
kubectl logs -f deployment/gateway -n chatbot
kubectl describe pod <pod-name> -n chatbot
kubectl exec -it deployment/gateway -n chatbot -- bash

# AWS
aws dynamodb scan --table-name conversations --region us-east-1
aws sqs get-queue-attributes --queue-url <url> --attribute-names ApproximateNumberOfMessages
aws logs tail /aws/eks/chatbot/gateway --follow

# Docker Compose
docker-compose up -d
docker-compose down
docker-compose logs -f <service>
docker-compose ps

# ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <registry>
docker push <image>
```

---

## SUPPORT & NEXT STEPS

For issues:
1. Check TROUBLESHOOTING GUIDE above
2. Review CloudWatch logs
3. Check pod events: `kubectl describe pod <name> -n chatbot`
4. Review documentation files:
   - README_NEW_ARCHITECTURE.md
   - DEPLOYMENT_GUIDE.md
   - QUICK_REFERENCE.md

For questions about architecture:
- See: Updated Budget-Conscious Production Arch.txt
- See: README_NEW_ARCHITECTURE.md

---

**Congratulations! Your production deployment is complete! 🎉**

Your LLM Chatbot is now running on AWS EKS with:
- ✅ Async processing via SQS
- ✅ DynamoDB data persistence
- ✅ Kubernetes orchestration
- ✅ Auto-scaling
- ✅ CloudWatch monitoring
- ✅ Production-ready security

Next: Monitor logs, test load, and enjoy! 🚀
