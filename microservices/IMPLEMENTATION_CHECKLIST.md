# Implementation Checklist - Quick Reference

## PHASE 1: Local Setup (30 min)
- [ ] Navigate to microservices directory
- [ ] Copy .env.example to .env
- [ ] Add your OpenAI API key to .env
- [ ] Verify Docker is installed: `docker --version`
- [ ] Build images: `docker-compose build`
- [ ] Start services: `docker-compose up -d`
- [ ] Wait 30 seconds for LocalStack
- [ ] Check health: `curl http://localhost:8080/health`

**Expected Result**: All services show "Up" status

---

## PHASE 2: Local Testing (45 min)
- [ ] Test Settings: `curl http://localhost:8001/health`
- [ ] Create Conversation: `curl -X POST http://localhost:8002/conversations ...`
- [ ] Create Message: `curl -X POST http://localhost:8003/messages ...`
- [ ] Send Chat: `curl -X POST http://localhost:8080/api/chat/send ...`
- [ ] Check Queue: `curl http://localhost:8080/api/debug/queue-stats`
- [ ] Wait 5 seconds
- [ ] Verify Response: Check conversations endpoint for AI response
- [ ] View Logs: `docker-compose logs ai-worker`

**Expected Result**: AI processes message and stores response in 5-10 seconds

---

## PHASE 3: Docker & ECR (30 min)
- [ ] Set AWS_ACCOUNT_ID variable
- [ ] Create ECR repositories (6 total)
- [ ] Stop containers: `docker-compose down`
- [ ] Login to ECR: `aws ecr get-login-password ...`
- [ ] Tag images: `docker tag llm-chatbot-gateway ...`
- [ ] Push images: `docker push <registry>/llm-chatbot/gateway:latest`
- [ ] Verify in AWS Console

**Expected Result**: All 6 images in ECR with "latest" tag

---

## PHASE 4: EKS Cluster (20-30 min)
- [ ] Create cluster: `eksctl create cluster --name llm-chatbot ...`
- [ ] **WAIT 15-20 MINUTES** ☕
- [ ] Update kubeconfig: `aws eks update-kubeconfig ...`
- [ ] Verify connection: `kubectl cluster-info`
- [ ] Check nodes: `kubectl get nodes` (3 Ready nodes)
- [ ] Install LB Controller: `helm install aws-load-balancer-controller ...`

**Expected Result**: 3 nodes in Ready state

---

## PHASE 5: Kubernetes Deploy (15 min)
- [ ] Update image registry in k8s-manifests.yaml
- [ ] Create namespace: `kubectl create namespace chatbot`
- [ ] Create secrets: `kubectl create secret generic chatbot-secrets ...`
- [ ] Deploy: `kubectl apply -f k8s-manifests-updated.yaml`
- [ ] Watch deployment: `kubectl get deployments -n chatbot -w`
- [ ] Verify pods: `kubectl get pods -n chatbot` (all Running)

**Expected Result**: All 6 deployments showing 3/3 ready

---

## PHASE 6: Production Testing (30 min)
- [ ] Get Gateway URL: `kubectl get svc -n chatbot gateway`
- [ ] Get Frontend URL: `kubectl get svc -n chatbot frontend`
- [ ] Test Gateway: `curl http://<GATEWAY_URL>/health`
- [ ] Get Settings: `curl http://<GATEWAY_URL>/api/settings`
- [ ] Send Chat: `curl -X POST http://<GATEWAY_URL>/api/chat/send ...`
- [ ] Wait 10 seconds
- [ ] Verify Response: Check conversations endpoint
- [ ] View Pod Logs: `kubectl logs -n chatbot -l app=ai-worker`

**Expected Result**: Chat processing works in production

---

## PHASE 7: Monitoring (20 min)
- [ ] Check CloudWatch: `aws logs tail /aws/eks/chatbot/gateway`
- [ ] Check Events: `kubectl get events -n chatbot`
- [ ] Check Metrics: `kubectl top pods -n chatbot`
- [ ] Check HPA: `kubectl get hpa -n chatbot`

**Expected Result**: No critical errors, metrics flowing

---

## PHASE 8: Cleanup (15 min)
- [ ] Stop local: `docker-compose down`
- [ ] Save URLs to file
- [ ] Document database access
- [ ] Create deployment summary
- [ ] Verify all checklist items

**Expected Result**: Deployment documented and verified

---

## TROUBLESHOOTING QUICK FIXES

**Problem**: Docker container won't start
```bash
docker-compose logs <service>
docker-compose down && docker-compose build --no-cache && docker-compose up -d
```

**Problem**: SQS not processing
```bash
kubectl logs -n chatbot -l app=ai-worker
kubectl get svc -n chatbot
```

**Problem**: Pod keeps restarting
```bash
kubectl describe pod <name> -n chatbot
kubectl logs <name> -n chatbot --previous
```

**Problem**: Can't access frontend
```bash
kubectl describe svc frontend -n chatbot
kubectl logs -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller
```

---

## KEY ENVIRONMENT VARIABLES

```
OPENAI_API_KEY=sk-your-key
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012
SQS_QUEUE_URL=http://localstack:4566/000000000000/ai-jobs
DYNAMODB_TABLE=conversations
```

---

## CRITICAL SUCCESS FACTORS

✓ All services running (6 total)
✓ All pods show "1/1" ready
✓ Gateway has LoadBalancer IP
✓ Frontend has LoadBalancer IP
✓ AI processes messages (5-10 sec)
✓ Messages stored in DynamoDB
✓ No error logs
✓ Metrics flowing

---

## TIME BREAKDOWN

| Phase | Duration | Status |
|-------|----------|--------|
| 1. Local Setup | 30 min | ☐ |
| 2. Local Testing | 45 min | ☐ |
| 3. Docker & ECR | 30 min | ☐ |
| 4. EKS Cluster | 20-30 min | ☐ |
| 5. K8s Deploy | 15 min | ☐ |
| 6. Production Test | 30 min | ☐ |
| 7. Monitoring | 20 min | ☐ |
| 8. Cleanup | 15 min | ☐ |
| **TOTAL** | **3-4 hours** | ☐ |

---

## POST-DEPLOYMENT TASKS

- [ ] Configure custom domain
- [ ] Setup SSL certificates
- [ ] Configure CI/CD pipeline
- [ ] Enable DynamoDB backups
- [ ] Setup CloudWatch alarms
- [ ] Document runbooks
- [ ] Train team on operations
- [ ] Setup incident response

---

## ROLLBACK STEPS (If needed)

```bash
# Quick rollback
kubectl rollout undo deployment/gateway -n chatbot

# Full rollback
kubectl delete namespace chatbot
kubectl create namespace chatbot
kubectl apply -f k8s-manifests-updated.yaml
```

---

## SUPPORT RESOURCES

📄 Documentation:
- IMPLEMENTATION_RUNBOOK.md (detailed steps)
- README_NEW_ARCHITECTURE.md (architecture)
- DEPLOYMENT_GUIDE.md (deployment reference)
- QUICK_REFERENCE.md (commands)

🔧 Tools:
- kubectl (Kubernetes)
- aws cli (AWS)
- docker (containers)
- helm (package manager)

💡 Quick Help:
```bash
kubectl get pods -n chatbot
kubectl logs -f deployment/gateway -n chatbot
kubectl describe pod <name> -n chatbot
aws logs tail /aws/eks/chatbot/gateway --follow
```

---

## PRINT THIS PAGE FOR REFERENCE DURING DEPLOYMENT

Keep this checklist visible while implementing. Mark items as you complete them.

**Estimated Duration: 3-4 hours**

Last Updated: May 24, 2026
