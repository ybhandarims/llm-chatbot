# Quick Reference Guide

## File Structure Changes

```
microservices/
├── docker-compose.yml              ✅ Updated - Async architecture
├── .env.example                    ✅ New - Environment template
├── aws_config.py                   ✅ New - Shared AWS utilities
├── localstack-init.sh              ✅ New - LocalStack setup
├── k8s-manifests.yaml              ✅ New - Kubernetes deployment
├── nginx.conf                      ✅ (In frontend/)
├── 
├── DEPLOYMENT_GUIDE.md             ✅ New - Step-by-step deployment
├── README_NEW_ARCHITECTURE.md      ✅ New - Architecture docs
├── MIGRATION_SUMMARY.md            ✅ New - Change summary
│
├── gateway/
│   ├── main.py                     ✅ Updated - SQS integration
│   └── requirements.txt            ✅ Updated - New dependencies
│
├── ai-service/
│   ├── main.py                     ✅ Updated - SQS consumer pattern
│   └── requirements.txt            ✅ Updated - New dependencies
│
├── conversations-service/
│   ├── main.py                     ✅ Updated - DynamoDB backend
│   └── requirements.txt            ✅ Updated - New dependencies
│
├── messages-service/
│   ├── main.py                     ✅ Updated - DynamoDB backend
│   └── requirements.txt            ✅ Updated - New dependencies
│
├── settings-service/
│   ├── main.py                     ✅ Updated - DynamoDB backend
│   └── requirements.txt            ✅ Updated - New dependencies
│
└── frontend/
    ├── Dockerfile                  ✅ Updated - Nginx multi-stage build
    └── nginx.conf                  ✅ New - Nginx configuration
```

## Core Architecture Changes

### Service Communication Flow
```
OLD:  Frontend → Gateway → Services (sync)
      ↓
      AI Service (blocking)

NEW:  Frontend → Gateway → Services (sync)
      ↓
      SQS Queue → AI Worker (async)
      ↓
      Services (async response)
```

### Data Storage
```
OLD:  SQLite (local files)
NEW:  DynamoDB (managed service)
```

### Frontend Serving
```
OLD:  Node.js http-server
NEW:  Nginx (static + proxy)
```

## Quick Start Commands

```bash
# 1. Setup
cd microservices
cp .env.example .env
# Edit .env with your OpenAI key

# 2. Start services
docker-compose up --build

# 3. Wait for initialization
sleep 30

# 4. Test endpoints
curl http://localhost:8080/health
curl http://localhost:3000

# 5. Send a message
curl -X POST http://localhost:8080/api/chat/send \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}'

# 6. Check queue
curl http://localhost:8080/api/debug/queue-stats
```

## Key Environment Variables

```
OPENAI_API_KEY=sk-your-key
SQS_QUEUE_URL=http://localstack:4566/000000000000/ai-jobs
DYNAMODB_TABLE=conversations
AWS_REGION=us-east-1
```

## Service Ports

| Service | Port | Type | Notes |
|---------|------|------|-------|
| Frontend | 3000 | Nginx | Static + API proxy |
| Gateway | 8080 | FastAPI | Orchestration + SQS |
| Settings | 8001 | FastAPI | User settings |
| Conversations | 8002 | FastAPI | Chat history |
| Messages | 8003 | FastAPI | Individual messages |
| AI Worker | - | Background | Processes SQS jobs |
| LocalStack | 4566 | Local AWS | DynamoDB/SQS |

## API Endpoints

### Chat (Async)
```
POST /api/chat/send
{
  "message": "Hello!",
  "conversation_id": "optional-uuid",
  "title": "optional-title"
}
```

### Conversations
```
GET /api/conversations
POST /api/conversations
GET /api/conversations/{id}
DELETE /api/conversations/{id}
```

### Messages
```
POST /api/messages
GET /api/conversations/{id}/messages
```

### Settings
```
GET /api/settings
POST /api/settings
POST /api/settings/reset
```

### Health & Debug
```
GET /health (all services)
GET /api/debug/queue-stats (gateway)
```

## DynamoDB Tables

### conversations
```
PK: user_id (String)
SK: conversation_id (String)
- title, messages[], created_at, updated_at
```

### messages
```
PK: conversation_id (String)
SK: message_id (String)
- role, message, timestamp
```

### settings
```
PK: user_id (String)
SK: setting_key (String)
- system_prompt, model, temperature, max_tokens
```

## Common Tasks

### View logs
```bash
# Service logs
docker-compose logs -f gateway
docker-compose logs -f ai-worker

# Kubernetes logs
kubectl logs -f deployment/gateway -n chatbot
```

### Check database
```bash
# LocalStack
aws dynamodb list-tables --endpoint-url http://localhost:4566
aws dynamodb scan --table-name conversations --endpoint-url http://localhost:4566

# Production
aws dynamodb scan --table-name conversations --region us-east-1
```

### Check SQS queue
```bash
# LocalStack
aws sqs get-queue-attributes \
  --queue-url http://localhost:4566/000000000000/ai-jobs \
  --attribute-names ApproximateNumberOfMessages \
  --endpoint-url http://localhost:4566

# Production
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/ACCOUNT_ID/ai-jobs \
  --attribute-names ApproximateNumberOfMessages
```

### Deploy to Kubernetes
```bash
# 1. Create EKS cluster
eksctl create cluster --name llm-chatbot --region us-east-1

# 2. Apply manifests
kubectl apply -f k8s-manifests.yaml

# 3. Check status
kubectl get pods -n chatbot
kubectl get svc -n chatbot

# 4. Get load balancer URL
kubectl get svc -n chatbot gateway -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

## Troubleshooting

### Service won't start
```bash
# Check logs
docker-compose logs <service>

# Check dependencies
docker-compose ps

# Verify network
docker network ls
```

### AI worker not processing
```bash
# Check worker logs
docker-compose logs ai-worker

# Check queue
curl http://localhost:8080/api/debug/queue-stats

# Check if messages service is up
curl http://messages:8003/health
```

### DynamoDB connection error
```bash
# Check LocalStack
docker-compose ps localstack

# Check tables
aws dynamodb list-tables --endpoint-url http://localhost:4566

# Check table data
aws dynamodb scan --table-name conversations \
  --endpoint-url http://localhost:4566 \
  --max-items 5
```

### Frontend not loading
```bash
# Check Nginx
docker-compose logs frontend

# Check if static files exist
docker-compose exec frontend ls -la /usr/share/nginx/html

# Test API proxy
curl -v http://localhost:3000/api/settings
```

## Performance Tips

### DynamoDB
- Use PAY_PER_REQUEST for variable workloads
- Enable TTL for old conversations
- Monitor consumed capacity
- Use batch operations when possible

### SQS
- Monitor queue depth
- Check visibility timeout
- Review DLQ for failures
- Implement exponential backoff

### Kubernetes
- Set resource limits
- Use horizontal pod autoscaling
- Monitor pod metrics
- Use spot instances for workers

## Security Checklist

- [ ] Secrets stored in AWS Secrets Manager
- [ ] IAM roles with least privilege
- [ ] Pod security context (non-root)
- [ ] Network policies enabled
- [ ] HTTPS/TLS for APIs
- [ ] API rate limiting
- [ ] Input validation
- [ ] CORS properly configured
- [ ] CloudWatch logging enabled
- [ ] Audit logs enabled

## Cost Monitoring

```bash
# Get current month costs
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-02-01 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE

# Set budget alert
aws budgets create-budget --account-id ACCOUNT_ID --budget file://budget.json
```

## References

- [README_NEW_ARCHITECTURE.md](./README_NEW_ARCHITECTURE.md) - Full architecture
- [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) - Deployment instructions
- [MIGRATION_SUMMARY.md](./MIGRATION_SUMMARY.md) - What changed
- [Updated Budget-Conscious Production Arch.txt](./Updated%20Budget-Conscious%20Production%20Arch.txt) - Business architecture
- [k8s-manifests.yaml](./k8s-manifests.yaml) - Kubernetes configuration

## Support

For issues or questions:
1. Check CloudWatch Logs
2. Review service logs
3. Check SQS queue stats
4. Verify DynamoDB connectivity
5. Review architecture documents
6. Check AWS service health dashboard
