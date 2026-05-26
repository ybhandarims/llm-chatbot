# Infrastructure Quick Reference

## File Structure

```
infra/
├─ eksctl/
│  └─ cluster.yaml          # EKS cluster configuration
├─ helm/
│  └─ chatapp/
│     ├─ Chart.yaml         # Helm chart metadata
│     ├─ values.yaml        # Default values (update with your ECR URLs)
│     └─ templates/
│        ├─ hpa.yaml        # Horizontal Pod Autoscaler (new)
│        ├─ pdb.yaml        # Pod Disruption Budget (new)
│        ├─ networkpolicy.yaml  # Network policies (new)
│        ├─ deployment-*.yaml   # Service deployments
│        ├─ service-*.yaml      # Kubernetes services
│        └─ ...other configs
├─ scripts/
│  └─ push-images.sh/.ps1   # Script to push Docker images
├─ README.md                # Original README
├─ INFRASTRUCTURE_RUNBOOK.md ← START HERE! Complete 8-phase implementation guide
└─ INFRASTRUCTURE_QUICK_REFERENCE.md (this file)
```

## Environment Variables Setup

### PowerShell (Windows)

```powershell
# Step 1: Set AWS credentials
$Env:AWS_ACCESS_KEY_ID = "AKIA..."
$Env:AWS_SECRET_ACCESS_KEY = "wJa..."

# Step 2: Get account info
$Env:AWS_ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text)
$Env:AWS_REGION = "us-east-1"
$Env:CLUSTER_NAME = "llm-chatbot"

# Step 3: Build registry URL
$Env:ECR_REGISTRY = "$Env:AWS_ACCOUNT_ID.dkr.ecr.$Env:AWS_REGION.amazonaws.com"

# Step 4: Get OpenAI key
$Env:OPENAI_API_KEY = Read-Host -AsSecureString "Enter OPENAI API key" | ConvertFrom-SecureString

# Verify
echo "Account: $Env:AWS_ACCOUNT_ID"
echo "Registry: $Env:ECR_REGISTRY"
```

### Bash (Linux/macOS)

```bash
# Step 1: Set AWS credentials
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="wJa..."

# Step 2: Get account info
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION="us-east-1"
export CLUSTER_NAME="llm-chatbot"

# Step 3: Build registry URL
export ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Step 4: Get OpenAI key
read -s -p "Enter OPENAI API key: " OPENAI_API_KEY
export OPENAI_API_KEY

# Verify
echo "Account: $AWS_ACCOUNT_ID"
echo "Registry: $ECR_REGISTRY"
```

## Key AWS Resources

| Resource | Name | Purpose |
|----------|------|---------|
| EKS Cluster | `llm-chatbot` | Kubernetes cluster |
| DynamoDB | `conversations` | Store conversations |
| DynamoDB | `messages` | Store individual messages |
| DynamoDB | `settings` | Store user settings |
| SQS Queue | `ai-jobs.fifo` | Queue AI processing jobs |
| SQS Queue | `ai-jobs-dlq.fifo` | Dead Letter Queue for failed jobs |
| ECR Repo | `llm-chatbot/frontend` | Frontend Docker image |
| ECR Repo | `llm-chatbot/gateway` | Gateway Docker image |
| ECR Repo | `llm-chatbot/settings` | Settings service Docker image |
| ECR Repo | `llm-chatbot/conversations` | Conversations service Docker image |
| ECR Repo | `llm-chatbot/messages` | Messages service Docker image |
| ECR Repo | `llm-chatbot/ai-worker` | AI Worker Docker image |

## Kubernetes Resources

### Namespaces
- `chatbot` - Application namespace
- `kube-system` - System components

### Deployments (in `chatbot` namespace)
- `frontend` - 2-5 replicas (HPA enabled)
- `gateway` - 3-10 replicas (HPA enabled)
- `settings` - 2-5 replicas (HPA enabled)
- `conversations` - 2-5 replicas (HPA enabled)
- `messages` - 2-5 replicas (HPA enabled)
- `ai-worker` - 1-10 replicas (HPA enabled)

### Services (in `chatbot` namespace)
- `frontend` - LoadBalancer (public)
- `gateway` - LoadBalancer (public API)
- `settings`, `conversations`, `messages` - ClusterIP (internal)

## Common Commands

### Cluster Management

```bash
# Create cluster
eksctl create cluster -f ./infra/eksctl/cluster.yaml

# Delete cluster
eksctl delete cluster --name llm-chatbot

# Get cluster info
eksctl get clusters
eksctl get nodegroup --cluster llm-chatbot

# Update kubeconfig
aws eks update-kubeconfig --name llm-chatbot --region us-east-1
```

### Container Management

```bash
# Build image
docker build -t llm-chatbot/gateway:latest ./microservices/gateway

# Tag for ECR
docker tag llm-chatbot/gateway:latest $ECR_REGISTRY/llm-chatbot/gateway:latest

# Push to ECR
docker push $ECR_REGISTRY/llm-chatbot/gateway:latest

# Login to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_REGISTRY
```

### Helm Deployment

```bash
# Deploy/update
helm upgrade --install llm-chatbot ./infra/helm/chatapp -n chatbot

# Check status
helm status llm-chatbot -n chatbot

# Get values
helm get values llm-chatbot -n chatbot

# Rollback
helm rollback llm-chatbot -n chatbot

# Uninstall
helm uninstall llm-chatbot -n chatbot
```

### Kubernetes Operations

```bash
# Get resources
kubectl get all -n chatbot
kubectl get pods -n chatbot
kubectl get svc -n chatbot

# Describe resource
kubectl describe pod <pod-name> -n chatbot

# View logs
kubectl logs deployment/gateway -n chatbot
kubectl logs deployment/gateway -n chatbot -f  # Follow

# Execute command
kubectl exec -it <pod-name> -n chatbot -- /bin/bash

# Port forward
kubectl port-forward svc/gateway 8080:8080 -n chatbot

# Restart deployment
kubectl rollout restart deployment/gateway -n chatbot

# Scale deployment
kubectl scale deployment/gateway --replicas=5 -n chatbot
```

### AWS Resource Management

```bash
# List DynamoDB tables
aws dynamodb list-tables

# List SQS queues
aws sqs list-queues

# List ECR repositories
aws ecr describe-repositories

# Get cluster logs
aws logs tail /aws/eks/llm-chatbot/gateway --follow

# Describe DynamoDB table
aws dynamodb describe-table --table-name conversations

# Get SQS queue attributes
aws sqs get-queue-attributes --queue-url <url> --attribute-names All
```

## Networking

### Node Groups and Availability

- **system-pool**: 1-3 t3.medium nodes (system components, tainted)
- **api-pool**: 2-5 t3.medium nodes (CRUD services)
- **ai-worker-pool**: 1-5 t3.medium nodes (AI background jobs)

### Load Balancers

- **Frontend ALB**: Exposes frontend service to internet
- **Gateway ALB**: Exposes API gateway to internet
- **Internal Services**: Using ClusterIP (no external access)

### Network Policies

Enabled in `networkpolicy.yaml`:
- Default deny all
- Allow DNS to kube-system
- Frontend ↔ Gateway communication
- Gateway ↔ Backend services
- Backend ↔ AWS services (HTTPS/443)

## Cost Optimization

### Current Configuration

| Component | Type | Cost Driver |
|-----------|------|-------------|
| **Compute** | t3.medium (4 nodes) | ~$300-500/month |
| **Data Transfer** | Between AZs | ~$10-30/month |
| **DynamoDB** | Pay-per-request | ~$20-50/month |
| **SQS** | Standard pricing | ~$5-10/month |
| **CloudWatch** | 7-day logs | ~$10-20/month |
| **Secrets Manager** | Basic | ~$1/month |
| **OpenAI API** | Per tokens | $100-10,000/month (main cost) |

### Optimization Tips

1. **Use Spot Instances**: Reduce compute by 50-70%
   - Change `spot: false` to `spot: true` in cluster.yaml

2. **Right-size Nodes**: Use smaller instances if load is low
   - Change t3.medium to t3.small

3. **Optimize AI Costs** (biggest driver):
   - Use gpt-3.5-turbo instead of gpt-4
   - Add prompt caching
   - Use context summarization
   - Batch requests

4. **Reduce Logging**:
   - CloudWatch 7-day retention (not 30)
   - Only log at INFO level in production

5. **Use DynamoDB TTL**:
   - Automatically delete old conversations after 90 days

## Monitoring & Alerts

### Key Metrics to Monitor

```bash
# CPU Usage
kubectl top pods -n chatbot
kubectl top nodes

# Pod Status
kubectl get pods -n chatbot -w

# HPA Status
kubectl get hpa -n chatbot -w

# Service LoadBalancers
kubectl get svc -n chatbot

# Node Status
kubectl get nodes

# Events
kubectl get events -n chatbot
```

### CloudWatch Metrics

- API Gateway: Request count, errors, latency
- DynamoDB: Consumed read/write units, throttling
- SQS: Messages in queue, age of oldest message
- ECS: CPU utilization, memory utilization
- Load Balancer: Target health, response time

## Troubleshooting Checklist

| Issue | Check | Solution |
|-------|-------|----------|
| Pods won't start | `kubectl describe pod <name>` | Check image, resources, permissions |
| Can't reach API | `kubectl get svc` | Check LoadBalancer IP, wait for provisioning |
| DynamoDB errors | `kubectl logs deployment/gateway` | Verify IAM role, table exists |
| SQS not working | Check AI worker logs | Verify queue URL, permissions |
| High latency | `kubectl top pods` | Check CPU/memory, scale pods |
| Image pull fails | `kubectl describe pod` | Verify ECR login, image exists |

## Security Checklist

- [ ] IAM roles use least privilege
- [ ] Service accounts annotated with IAM role
- [ ] Network policies restrict traffic
- [ ] Pods run as non-root user
- [ ] Secrets not in logs or env vars
- [ ] Images scanned for vulnerabilities
- [ ] API uses HTTPS/TLS
- [ ] WAF rules configured (optional)

## Useful Links

- [eksctl Documentation](https://eksctl.io/)
- [Helm Documentation](https://helm.sh/)
- [AWS EKS Best Practices](https://aws.github.io/aws-eks-best-practices/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [AWS DynamoDB Guide](https://docs.aws.amazon.com/dynamodb/)

## Next Steps

1. **Start with**: Read [INFRASTRUCTURE_RUNBOOK.md](INFRASTRUCTURE_RUNBOOK.md)
2. **Setup environment**: Run environment variable commands above
3. **Create resources**: Follow phases 1-8 in runbook
4. **Test deployment**: Run verification commands
5. **Monitor**: Use CloudWatch and kubectl commands
6. **Cleanup**: Follow Phase 10 cleanup commands when ready to teardown

---

## Phase 10: Complete Infrastructure Cleanup

**⚠️ WARNING**: These commands DELETE all resources permanently

```bash
# 1. Delete Helm release
helm uninstall llm-chatbot -n chatbot

# 2. Delete Kubernetes namespace
kubectl delete namespace chatbot

# 3. Delete EKS cluster (WAIT 10-15 MINUTES)
eksctl delete cluster --name llm-chatbot --region us-east-1 --wait

# 4. Delete DynamoDB tables
aws dynamodb delete-table --table-name conversations --region us-east-1
aws dynamodb delete-table --table-name messages --region us-east-1
aws dynamodb delete-table --table-name settings --region us-east-1

# 5. Delete SQS queues (Get URLs first)
MAIN_QUEUE=$(aws sqs get-queue-url --queue-name ai-jobs.fifo --region us-east-1 --query 'QueueUrl' --output text)
DLQ=$(aws sqs get-queue-url --queue-name ai-jobs-dlq.fifo --region us-east-1 --query 'QueueUrl' --output text)
aws sqs delete-queue --queue-url "$MAIN_QUEUE"
aws sqs delete-queue --queue-url "$DLQ"

# 6. Delete ECR repositories
for repo in frontend gateway settings conversations messages ai-worker; do
  aws ecr delete-repository --repository-name llm-chatbot/$repo --force --region us-east-1
done

# 7. Verify cleanup
echo "DynamoDB tables:" && aws dynamodb list-tables --region us-east-1 | grep TableNames
echo "SQS queues:" && aws sqs list-queues --region us-east-1 2>/dev/null || echo "✅ No queues found"
echo "ECR repos:" && aws ecr describe-repositories --region us-east-1 | grep -i llm-chatbot || echo "✅ No llm-chatbot repos found"
echo "EKS clusters:" && eksctl get clusters || echo "✅ No clusters found"

# Cost savings achieved
echo ""
echo "✅ Cleanup Complete"
echo "📊 Monthly Savings: \$464 (on-demand) or \$254 (Spot)"
echo "📊 Annual Savings: \$5,568 (on-demand) or \$3,048 (Spot)"
```

**Cleanup Time**: ~45 minutes  
**Billing**: Stops within 5-10 minutes  
**For detailed instructions**: See [Phase 10 in INFRASTRUCTURE_RUNBOOK.md](INFRASTRUCTURE_RUNBOOK.md#phase-10-cleanup--teardown-complete)

---

**Last Updated**: May 27, 2026 (Phase 10 Complete)

For detailed step-by-step instructions, see: [INFRASTRUCTURE_RUNBOOK.md](INFRASTRUCTURE_RUNBOOK.md)
