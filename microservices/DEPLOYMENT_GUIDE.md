# Deployment Guide - Budget-Conscious Architecture

## Table of Contents
1. [Local Development Setup](#local-development-setup)
2. [Docker Build & Push](#docker-build--push)
3. [EKS Deployment](#eks-deployment)
4. [AWS Configuration](#aws-configuration)
5. [Monitoring & Troubleshooting](#monitoring--troubleshooting)
6. [Cost Management](#cost-management)

## Local Development Setup

### Prerequisites
- Docker & Docker Compose
- Python 3.9+
- Node.js 18+ (for frontend development)
- AWS CLI (for production deployments)

### Quick Start

1. **Clone and setup environment:**
```bash
cd microservices
cp .env.example .env
# Edit .env with your values
```

2. **Start all services:**
```bash
docker-compose up --build
```

3. **Verify services are running:**
```bash
# Wait for LocalStack to initialize (30 seconds)
sleep 30

# Check service health
curl http://localhost:8080/health
curl http://localhost:3000/health

# Access frontend
open http://localhost:3000
```

4. **Test the async flow:**
```bash
# Send a chat message
curl -X POST http://localhost:8080/api/chat/send \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, what is 2+2?",
    "title": "Math Question"
  }'

# Check queue stats
curl http://localhost:8080/api/debug/queue-stats

# Wait 2-3 seconds for AI Worker to process
sleep 3

# Get conversation (note the conversation_id from previous response)
curl http://localhost:8080/api/conversations
```

### LocalStack Verification

```bash
# Check DynamoDB tables
aws dynamodb list-tables --endpoint-url http://localhost:4566

# List SQS queues
aws sqs list-queues --endpoint-url http://localhost:4566

# Send test message to SQS
aws sqs send-message \
  --queue-url http://localhost:4566/000000000000/ai-jobs \
  --message-body '{"test": "message"}' \
  --endpoint-url http://localhost:4566
```

## Docker Build & Push

### Building Images

```bash
# Build all services
docker-compose build

# Build specific service
docker-compose build gateway

# Build with custom registry
DOCKER_REGISTRY=your-registry.dkr.ecr.us-east-1.amazonaws.com
docker build -t $DOCKER_REGISTRY/gateway:latest ./gateway
```

### Push to ECR

```bash
# Create ECR repository
aws ecr create-repository --repository-name llm-chatbot/gateway --region us-east-1

# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $DOCKER_REGISTRY

# Push images
docker push $DOCKER_REGISTRY/gateway:latest
docker push $DOCKER_REGISTRY/ai-service:latest
docker push $DOCKER_REGISTRY/conversations-service:latest
docker push $DOCKER_REGISTRY/messages-service:latest
docker push $DOCKER_REGISTRY/settings-service:latest
docker push $DOCKER_REGISTRY/frontend:latest
```

### Build Script

Create `scripts/build-and-push.sh`:
```bash
#!/bin/bash
set -e

REGISTRY=${1:-"your-registry.dkr.ecr.us-east-1.amazonaws.com"}
TAG=${2:-"latest"}

SERVICES=(
  "gateway"
  "ai-service"
  "conversations-service"
  "messages-service"
  "settings-service"
  "frontend"
)

for service in "${SERVICES[@]}"; do
  echo "Building $service..."
  docker build -t $REGISTRY/$service:$TAG ./$service
  echo "Pushing $service..."
  docker push $REGISTRY/$service:$TAG
done

echo "All services built and pushed!"
```

## EKS Deployment

### Prerequisites
```bash
# Install tools
brew install awscli kubectl eksctl helm

# Configure AWS credentials
aws configure

# Create EKS cluster (if not exists)
eksctl create cluster \
  --name llm-chatbot \
  --version 1.27 \
  --region us-east-1 \
  --nodegroup-name standard \
  --node-type t3.medium \
  --nodes 3 \
  --nodes-min 2 \
  --nodes-max 10
```

### Deploy to EKS

1. **Update image registry in k8s-manifests.yaml:**
```bash
sed -i 's|llm-chatbot/|your-registry.dkr.ecr.us-east-1.amazonaws.com/|g' k8s-manifests.yaml
```

2. **Create namespace and secrets:**
```bash
kubectl apply -f k8s-manifests.yaml

# Create secrets
kubectl create secret generic chatbot-secrets \
  --from-literal=OPENAI_API_KEY='your-key' \
  --from-literal=AWS_ACCESS_KEY_ID='your-key' \
  --from-literal=AWS_SECRET_ACCESS_KEY='your-secret' \
  -n chatbot
```

3. **Deploy services:**
```bash
kubectl apply -f k8s-manifests.yaml
```

4. **Verify deployment:**
```bash
# Watch deployments
kubectl get deployments -n chatbot -w

# Check pod status
kubectl get pods -n chatbot

# View logs
kubectl logs -f deployment/gateway -n chatbot

# Get service endpoints
kubectl get svc -n chatbot
```

### Helm Deployment (Alternative)

```bash
# Install Helm (if needed)
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Create Helm chart
helm create chatapp

# Deploy
helm install chatapp ./chatapp -n chatbot --create-namespace

# Upgrade
helm upgrade chatapp ./chatapp -n chatbot
```

## AWS Configuration

### DynamoDB Setup

```bash
# Create tables
aws dynamodb create-table \
  --table-name conversations \
  --attribute-definitions \
    AttributeName=user_id,AttributeType=S \
    AttributeName=conversation_id,AttributeType=S \
  --key-schema \
    AttributeName=user_id,KeyType=HASH \
    AttributeName=conversation_id,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1

# Add TTL for auto-cleanup (30 days)
aws dynamodb update-time-to-live \
  --table-name conversations \
  --time-to-live-specification AttributeName=ttl,Enabled=true \
  --region us-east-1
```

### SQS Setup

```bash
# Create main queue (FIFO for message ordering)
aws sqs create-queue \
  --queue-name ai-jobs.fifo \
  --attributes '{"FifoQueue":"true","ContentBasedDeduplication":"true"}' \
  --region us-east-1

# Create DLQ
aws sqs create-queue \
  --queue-name ai-jobs-dlq.fifo \
  --attributes '{"FifoQueue":"true"}' \
  --region us-east-1

# Set redrive policy
aws sqs set-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/ACCOUNT_ID/ai-jobs.fifo \
  --attributes '{
    "RedrivePolicy": "{
      \"deadLetterTargetArn\": \"arn:aws:sqs:us-east-1:ACCOUNT_ID:ai-jobs-dlq.fifo\",
      \"maxReceiveCount\": 3
    }"
  }' \
  --region us-east-1
```

### Secrets Manager

```bash
# Store OpenAI API key
aws secretsmanager create-secret \
  --name llm-chatbot/openai-api-key \
  --secret-string 'sk-your-key-here' \
  --region us-east-1

# Retrieve secret
aws secretsmanager get-secret-value \
  --secret-id llm-chatbot/openai-api-key \
  --region us-east-1
```

### IAM Roles for IRSA (Pod Identity)

```bash
# Create service account with role
eksctl create iamserviceaccount \
  --name chatbot-sa \
  --namespace chatbot \
  --cluster llm-chatbot \
  --role-name chatbot-pod-role \
  --attach-policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess \
  --attach-policy-arn arn:aws:iam::aws:policy/AmazonSQSFullAccess \
  --attach-policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite

# Update deployment to use service account
# serviceAccountName: chatbot-sa
```

## Monitoring & Troubleshooting

### CloudWatch Logs

```bash
# View logs for a service
aws logs tail /aws/eks/chatbot/gateway --follow

# Export logs
aws logs create-export-task \
  --log-group-name /aws/eks/chatbot/gateway \
  --from 1620000000000 \
  --to 1620086400000 \
  --destination s3-bucket \
  --destination-prefix logs/
```

### Prometheus & Grafana

```bash
# Install Prometheus
helm install prometheus prometheus-community/kube-prometheus-stack \
  -n monitoring \
  --create-namespace

# Access Grafana
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# Create dashboard for SQS metrics
# Source: https://grafana.com/dashboards
```

### Debug Commands

```bash
# Check service connectivity
kubectl run debug --image=curlimages/curl -it --rm -- \
  curl http://gateway:8080/health

# Execute in pod
kubectl exec -it deployment/gateway -n chatbot -- bash

# Check resource usage
kubectl top pods -n chatbot
kubectl top nodes

# View events
kubectl get events -n chatbot --sort-by='.lastTimestamp'
```

### Common Issues

**Issue: SQS jobs not processing**
```bash
# Check AI worker logs
kubectl logs -f deployment/ai-worker -n chatbot

# Check queue visibility
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/ACCOUNT_ID/ai-jobs.fifo \
  --attribute-names ApproximateNumberOfMessages \
  --region us-east-1

# Purge queue (careful - deletes messages)
aws sqs purge-queue \
  --queue-url https://sqs.us-east-1.amazonaws.com/ACCOUNT_ID/ai-jobs.fifo
```

**Issue: DynamoDB throttling**
```bash
# Check consumed capacity
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConsumedWriteCapacityUnits \
  --dimensions Name=TableName,Value=conversations \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-01T01:00:00Z \
  --period 300 \
  --statistics Sum \
  --region us-east-1

# Enable autoscaling (if on provisioned mode)
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/conversations \
  --scalable-dimension dynamodb:table:WriteCapacityUnits \
  --min-capacity 100 \
  --max-capacity 40000
```

## Cost Management

### Cost Estimation

Based on the budget-conscious architecture:

```
Monthly Costs (Estimate):
- EKS Cluster:        $80-150
- DynamoDB:           $0-100 (pay-per-request)
- SQS:                $0-20
- S3 (logs):          $0-10
- Data Transfer:      $0-50
- OpenAI:             $100-10000+ (main driver!)
- CloudWatch:         $10-50
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total (excl. AI):     $90-380
Total (with AI):      $190-10380
```

### Cost Optimization Tips

1. **DynamoDB Optimization**
   - Use PAY_PER_REQUEST for variable workloads
   - Enable TTL for old conversations
   - Monitor consumed capacity

2. **EKS Optimization**
   - Use Spot instances for AI workers
   - Schedule batch processing off-peak
   - Use Karpenter for autoscaling

3. **OpenAI Cost Reduction**
   - Token truncation: 50% savings
   - Context summarization: 30% savings
   - Caching: 20% savings
   - Batch processing: 40% savings

4. **Network Cost Reduction**
   - Use VPC endpoints for AWS services
   - Deploy in single region
   - Minimize cross-AZ traffic

### Monitoring Costs

```bash
# Get cost breakdown
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-02-01 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE \
  --region us-east-1

# Set up budget alerts
aws budgets create-budget \
  --account-id ACCOUNT_ID \
  --budget file://budget.json \
  --notifications-with-subscribers file://notifications.json
```

## Rollback Procedure

```bash
# Rollback to previous version
kubectl rollout undo deployment/gateway -n chatbot

# Check rollout history
kubectl rollout history deployment/gateway -n chatbot

# Rollback to specific revision
kubectl rollout undo deployment/gateway -n chatbot --to-revision=2
```

## Disaster Recovery

```bash
# Backup DynamoDB
aws dynamodb create-backup \
  --table-name conversations \
  --backup-name conversations-backup-$(date +%s)

# Restore from backup
aws dynamodb restore-table-from-backup \
  --target-table-name conversations-restore \
  --backup-arn arn:aws:dynamodb:us-east-1:ACCOUNT_ID:table/conversations/backup/BACKUP_ARN

# Enable point-in-time recovery
aws dynamodb update-continuous-backups \
  --table-name conversations \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
```

## Conclusion

This deployment guide provides comprehensive instructions for deploying the budget-conscious LLM chatbot architecture to production. Always test in staging before production deployment.

For more information, see:
- [README_NEW_ARCHITECTURE.md](./README_NEW_ARCHITECTURE.md)
- [Updated Budget-Conscious Production Arch.txt](./Updated%20Budget-Conscious%20Production%20Arch.txt)
