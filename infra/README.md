 # Infrastructure Deployment (Complete Budget-Conscious Architecture)

**📚 START HERE**: [INFRASTRUCTURE_RUNBOOK.md](INFRASTRUCTURE_RUNBOOK.md) - Complete 8-phase implementation guide

**⚡ Quick Reference**: [INFRASTRUCTURE_QUICK_REFERENCE.md](INFRASTRUCTURE_QUICK_REFERENCE.md) - Common commands and quick lookups

---

## Overview

This folder contains complete infrastructure-as-code for deploying the LLM Chatbot on production-grade AWS EKS with a **budget-conscious** architecture optimized for startups and MVPs.

### What's Included

✅ **eksctl cluster configuration** - Multi-AZ EKS cluster with 3 node pools  
✅ **Helm charts** - Complete deployment for 6 microservices  
✅ **Production-grade configs** - HPA, PDB, Network Policies, IRSA  
✅ **Comprehensive runbook** - 8-phase step-by-step implementation guide  
✅ **AWS integration** - DynamoDB, SQS, Secrets Manager, CloudWatch  

### Architecture Highlights

```
Users → AWS ALB → EKS Cluster (3-4 nodes) → 6 Microservices
                                             ↓
                        AWS Services: DynamoDB + SQS + Secrets Manager
```

**Budget Optimized**:
- Estimated cost: **$400-600/month** (excluding OpenAI API costs)
- Suitable for: Startups, MVPs, early-stage products
- Scales to: 10,000+ daily active users

---

## Quick Start (3 Steps)

### Step 1: Update Configuration

Edit `helm/chatapp/values.yaml`:
```yaml
images:
  gateway:
    repository: "YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/llm-chatbot/gateway"
    tag: "latest"
  # ... update all 6 services
```

### Step 2: Create AWS Resources

```bash
# Create DynamoDB tables, SQS queues, and IAM roles
# (See INFRASTRUCTURE_RUNBOOK.md Phase 2 for details)

aws dynamodb create-table --table-name conversations ...
aws sqs create-queue --queue-name ai-jobs.fifo ...
```

### Step 3: Deploy Cluster

```bash
# Create EKS cluster (15-20 minutes)
eksctl create cluster -f eksctl/cluster.yaml

# Deploy services
helm upgrade --install llm-chatbot ./helm/chatapp -n chatbot
```

✅ **Done!** Access your services via LoadBalancer IPs

---

## Complete Implementation

For detailed, step-by-step instructions covering all 8 phases:

### **→ [Read INFRASTRUCTURE_RUNBOOK.md](INFRASTRUCTURE_RUNBOOK.md)**

This includes:
- ✅ Phase 1: Environment Setup
- ✅ Phase 2: AWS Configuration (DynamoDB, SQS, Secrets)
- ✅ Phase 3: ECR Container Registry
- ✅ Phase 4: EKS Cluster Creation
- ✅ Phase 5: Helm Deployment
- ✅ Phase 6: AWS Service Integration
- ✅ Phase 7: Production Testing
- ✅ Phase 8: Monitoring & Observability
- ✅ Troubleshooting Guide
- ✅ Rollback Procedures

---

## File Structure

```
infra/
├─ eksctl/
│  └─ cluster.yaml                 # EKS cluster definition (updated!)
│     ├─ Multi-AZ setup
│     ├─ 3 node pools (system, api, ai-worker)
│     ├─ IRSA configuration
│     └─ CloudWatch logging
│
├─ helm/chatapp/
│  ├─ Chart.yaml                   # Helm chart metadata
│  ├─ values.yaml                  # Configuration (UPDATED!)
│  │  ├─ HPA settings
│  │  ├─ PDB configuration
│  │  ├─ Resource limits
│  │  └─ Observability settings
│  │
│  └─ templates/
│     ├─ hpa.yaml                  # NEW! Horizontal Pod Autoscaler
│     ├─ pdb.yaml                  # NEW! Pod Disruption Budget
│     ├─ networkpolicy.yaml        # NEW! Network policies
│     ├─ deployment-*.yaml         # Deployments (UPDATED!)
│     ├─ service-*.yaml            # Kubernetes services
│     ├─ configmap.yaml            # Configuration
│     ├─ secret.yaml               # Secrets
│     ├─ ingress.yaml              # ALB ingress
│     └─ _helpers.tpl              # Template helpers
│
├─ scripts/
│  └─ push-images.ps1              # PowerShell script to push images to ECR
│  └─ push-images.sh               # Bash script to push images to ECR
│
├─ README.md                        # This file
├─ INFRASTRUCTURE_RUNBOOK.md       # ← START HERE! Complete implementation guide
└─ INFRASTRUCTURE_QUICK_REFERENCE.md  # Common commands and troubleshooting

```

---

## What's New in This Update

### eksctl/cluster.yaml
- ✅ Multi-AZ deployment across 3 availability zones
- ✅ 3 separate node pools: system, api, ai-worker
- ✅ IRSA (IAM Roles for Service Accounts) support
- ✅ CloudWatch logging configuration
- ✅ Proper addon configurations

### helm/chatapp/values.yaml
- ✅ HPA configuration for all services
- ✅ PDB (Pod Disruption Budget) settings
- ✅ IRSA role annotations
- ✅ Structured JSON logging
- ✅ Probe configuration (startup, readiness, liveness)
- ✅ Network policy settings
- ✅ Security context configurations

### helm/chatapp/templates/
- ✅ NEW: `hpa.yaml` - 6 Horizontal Pod Autoscalers
- ✅ NEW: `pdb.yaml` - Pod Disruption Budgets for reliability
- ✅ NEW: `networkpolicy.yaml` - Secure network policies
- ✅ UPDATED: All deployments with production-grade configurations
- ✅ UPDATED: Probes, security context, affinity rules

---

## Prerequisites

```bash
# Required Tools
aws --version              # AWS CLI v2+
eksctl version            # eksctl 0.170+
kubectl version           # kubectl 1.29+
helm version              # Helm 3.12+
docker --version          # Docker 24.0+

# Required Credentials
AWS_ACCESS_KEY_ID         # AWS account access
AWS_SECRET_ACCESS_KEY     # AWS account secret
OPENAI_API_KEY           # OpenAI API key
```

---

## Key Features

### Production-Grade Kubernetes

- **Multi-AZ Deployment**: Spans 3 availability zones for high availability
- **Auto-Scaling**: HPA scales pods based on CPU/memory; nodes auto-scale
- **Pod Disruption Budgets**: Ensures service availability during node maintenance
- **Network Policies**: Secure pod-to-pod and pod-to-AWS communication
- **Graceful Shutdown**: 30-second termination grace period
- **Health Checks**: Startup, readiness, and liveness probes

### AWS Integration

- **DynamoDB**: Pay-per-request pricing, no operational overhead
- **SQS FIFO**: Guaranteed message ordering for AI jobs
- **Secrets Manager**: Secure credential storage
- **IAM IRSA**: Pod-level IAM roles without exposed credentials
- **CloudWatch**: Centralized logging and metrics
- **ALB Ingress**: Automatic load balancer management

### Budget Optimization

- **t3.medium instances**: Good CPU/memory for reasonable cost
- **Pay-per-request DynamoDB**: No provisioned capacity waste
- **Auto-scaling**: Scale down during off-hours
- **Spot instances ready**: Can enable for 50-70% cost savings
- **Structured logging**: 7-day retention instead of 30

---

## Deployment Process

### Phase Overview

| Phase | Duration | What | Commands |
|-------|----------|------|----------|
| 1 | 10 min | Environment Setup | AWS credentials, vars |
| 2 | 15 min | AWS Configuration | DynamoDB, SQS, IAM |
| 3 | 20 min | ECR Setup | Build and push images |
| 4 | 25 min | EKS Cluster | Create cluster ⏱️ 15-20 min wait |
| 5 | 15 min | Helm Deployment | Deploy services |
| 6 | 10 min | Integration | IRSA, permissions |
| 7 | 15 min | Testing | Verify services |
| 8 | 10 min | Monitoring | Enable logging |
| **TOTAL** | **4-5 hours** | | |

---

## Cost Analysis

### Monthly Infrastructure Cost (Estimate)

```
EKS Control Plane:    $73    (fixed)
EC2 Nodes (4):        $300   (t3.medium, on-demand)
 └─ With Spot:        $100   (50-70% savings)
DynamoDB:             $30    (pay-per-request)
SQS:                  $5     (minimal traffic)
CloudWatch:           $20    (logging)
Data Transfer:        $20    (between AZs)
─────────────────────────────
Total Infrastructure: $450   (with spot: $250)
```

**OpenAI API Costs** (Much larger): $100-$10,000/month depending on usage

**Total Production Cost**: **$550-$10,450/month** (dominated by LLM tokens)

---

## Security Considerations

✅ **IRSA**: Pods assume IAM roles (no keys in env vars)  
✅ **Network Policies**: Restrict inter-pod communication  
✅ **Non-root Pods**: All containers run as non-root user  
✅ **Secrets Manager**: Credentials stored securely  
✅ **Private Cluster Option**: Can configure private subnets  
✅ **Audit Logging**: CloudWatch logging for all API calls  

---

## Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| Pods stuck in `ImagePullBackOff` | Verify ECR images exist, check IAM permissions |
| Pods can't access DynamoDB | Verify IRSA role attached, check table permissions |
| LoadBalancer pending | Check ALB controller: `kubectl get deployment -n kube-system` |
| AI worker not processing | Verify SQS queue exists, check IAM SQS permissions |

### Quick Diagnostic Commands

```bash
# Pod status
kubectl get pods -n chatbot

# Pod logs
kubectl logs deployment/gateway -n chatbot

# Describe pod (for detailed errors)
kubectl describe pod <name> -n chatbot

# Check services and IPs
kubectl get svc -n chatbot

# HPA status
kubectl get hpa -n chatbot

# Check events
kubectl get events -n chatbot
```

For more troubleshooting, see [INFRASTRUCTURE_RUNBOOK.md#Troubleshooting](INFRASTRUCTURE_RUNBOOK.md#troubleshooting-guide)

---

## Monitoring

### CloudWatch

```bash
# View logs
aws logs tail /aws/eks/llm-chatbot/gateway --follow

# List log groups
aws logs describe-log-groups
```

### Kubernetes Metrics

```bash
# CPU and memory usage
kubectl top pods -n chatbot
kubectl top nodes

# Watch HPA scaling
kubectl get hpa -n chatbot -w
```

---

## Rollback

### Quick Rollback (Helm Release)

```bash
# Undo last deployment
helm rollback llm-chatbot -n chatbot

# Full deletion
helm uninstall llm-chatbot -n chatbot
```

### Full Rollback (Delete Everything)

```bash
# Delete cluster and all AWS resources
eksctl delete cluster --name llm-chatbot --region us-east-1
```

For detailed rollback procedures, see [INFRASTRUCTURE_RUNBOOK.md#Rollback](INFRASTRUCTURE_RUNBOOK.md#rollback-procedures)

---

## Next Steps

1. **Read**: [INFRASTRUCTURE_RUNBOOK.md](INFRASTRUCTURE_RUNBOOK.md) - Complete implementation guide
2. **Reference**: [INFRASTRUCTURE_QUICK_REFERENCE.md](INFRASTRUCTURE_QUICK_REFERENCE.md) - Commands and tips
3. **Follow**: 8 phases in the runbook (4-5 hours total)
4. **Deploy**: Your production chatbot on AWS EKS!

---

## Support

- **Runbook**: Full step-by-step guide with examples
- **Quick Reference**: Common commands and troubleshooting
- **AWS Docs**: Links to official AWS documentation

---

**Ready to deploy? Start with [INFRASTRUCTURE_RUNBOOK.md](INFRASTRUCTURE_RUNBOOK.md)** 🚀
 # associate OIDC provider (eksctl helper)
 eksctl utils associate-iam-oidc-provider --cluster chatapp-eks --approve

 # create IAM service account (adjust policy arn / file as per AWS docs)
 eksctl create iamserviceaccount \
   --cluster=chatapp-eks \
   --namespace=kube-system \
   --name=aws-load-balancer-controller \
   --attach-policy-arn=arn:aws:iam::${AWS_ACCOUNT_ID}:policy/AWSLoadBalancerControllerIAMPolicy \
   --approve

 helm repo add eks https://aws.github.io/eks-charts
 helm repo update
 kubectl apply -k "github.com/aws/eks-charts/stable/aws-load-balancer-controller//crds?ref=master"
 helm upgrade -i aws-load-balancer-controller eks/aws-load-balancer-controller \
   -n kube-system \
   --set clusterName=chatapp-eks \
   --set serviceAccount.create=false \
   --set serviceAccount.name=aws-load-balancer-controller
 ```

 Note: the exact IAM policy creation steps are long and depend on your AWS account. If you prefer, use the AWS console or follow the official AWS guide for the ALB controller.

 7) Create the OpenAI secret in Kubernetes

 ```bash
 kubectl -n chatapp create secret generic openai-secret --from-literal=OPENAI_API_KEY=${OPENAI_API_KEY}
 ```

 8) Install the Helm chart for the application

 Example using `--set` to override image repositories and to point to the OpenAI secret:

 ```bash
 helm upgrade --install chatapp infra/helm/chatapp \
   --namespace chatapp --create-namespace \
   --set images.gateway.repository=${REPO_PREFIX}/gateway \
   --set images.gateway.tag=latest \
   --set images.frontend.repository=${REPO_PREFIX}/frontend \
   --set images.frontend.tag=latest \
   --set images.ai.repository=${REPO_PREFIX}/ai \
   --set images.ai.tag=latest \
   --set openai.secretName=openai-secret
 ```

 Alternatively, set values directly in [infra/helm/chatapp/values.yaml](infra/helm/chatapp/values.yaml) and run the `helm upgrade --install` without `--set` overrides.

 9) Verify rollout & get ingress

 ```bash
 kubectl -n chatapp get pods
 kubectl -n chatapp get svc
 kubectl -n chatapp get ingress
 kubectl -n chatapp describe ingress
 ```

 10) Tail logs for quick debugging

 ```bash
 # gateway logs
 kubectl -n chatapp logs -l app=gateway -f

 # ai service logs
 kubectl -n chatapp logs -l app=ai -f
 ```

 11) Upgrade / redeploy images

 - Build and push a new image with a new tag (e.g. `v1.0.1`), then run:

 ```bash
 helm upgrade --install chatapp infra/helm/chatapp -n chatapp \
   --set images.gateway.tag=v1.0.1 --set images.frontend.tag=v1.0.1
 ```

 Troubleshooting tips
 - If the ALB does not become healthy, check the AWS Load Balancer Controller logs and confirm the service account IAM policy is correct.
 - If pods crash with sqlite errors, verify that PVCs bound correctly: `kubectl -n chatapp get pvc`.
 - Use `helm template infra/helm/chatapp --values infra/helm/chatapp/values.yaml` to render templates locally for inspection.

 Notes
 - Keep your OpenAI API key out of version control. Use Kubernetes Secrets, AWS Secrets Manager, or External Secrets Operator in production.
 - Replace `chatapp` in repo names and resource names with your preferred naming convention.

