# Technology Decisions - LLM Chatbot Project

**Date**: May 30, 2026  
**Status**: ✅ FINAL ARCHITECTURE DECISIONS  

This document explains why each technology was chosen for this project and provides detailed comparisons with alternatives.

---

## Table of Contents

1. [Database Technology](#database-technology)
2. [Backend Language & Framework](#backend-language--framework)
3. [Frontend Technology](#frontend-technology)
4. [Message Queue & Async Processing](#message-queue--async-processing)
5. [Container Orchestration](#container-orchestration)
6. [Infrastructure & Cloud Provider](#infrastructure--cloud-provider)
7. [Summary Decision Matrix](#summary-decision-matrix)

---

## Database Technology

### ✅ Chosen: **DynamoDB (NoSQL, AWS Managed)**

#### Why DynamoDB is Right for This Project

| Aspect | Advantage |
|--------|-----------|
| **Operational Burden** | ✅ Fully managed by AWS (no patching, backups, scaling) |
| **Cost Model** | ✅ Pay-per-request (ideal for bursty chat traffic) |
| **Auto-Scaling** | ✅ Automatic, no configuration needed |
| **Security** | ✅ IRSA integration, no database passwords to manage |
| **Multi-AZ** | ✅ Built-in replication across availability zones |
| **Integration** | ✅ Native AWS services ecosystem (IAM, CloudWatch, Secrets Manager) |
| **Microservices** | ✅ Perfect for table-per-service pattern |
| **DevOps** | ✅ LocalStack emulation for local development |

#### Cost Comparison: DynamoDB vs Alternatives

```
MONTHLY COST ESTIMATE (1000 requests/day, ~30KB avg item size):

┌─────────────────────────────────────────────────────────────┐
│ Technology         │ Base Cost  │ Data Transfer │ Total      │
├─────────────────────────────────────────────────────────────┤
│ DynamoDB (Pay/req) │ $15-50     │ $5-10         │ $20-60     │
│ RDS PostgreSQL     │ $150-300   │ $10-20        │ $160-320   │
│ RDS MySQL          │ $150-300   │ $10-20        │ $160-320   │
│ RDS Aurora         │ $300-500   │ $10-20        │ $310-520   │
│ Self-hosted Postgres│ $50-200   │ Free (EC2)    │ $50-200    │
│ MongoDB Atlas      │ $100-200   │ $20-50        │ $120-250   │
└─────────────────────────────────────────────────────────────┘

💰 DynamoDB SAVINGS: 87% cheaper than managed RDS!
```

#### Why NOT PostgreSQL/MySQL?

| Issue | Impact |
|-------|--------|
| **Provisioned Capacity** | Pay $150-300/month minimum regardless of usage |
| **Complex Scaling** | Requires manual intervention or elaborate auto-scaling setup |
| **Operational Overhead** | Backups, patches, replication setup, failover handling |
| **ACID Transactions** | Overkill for simple key-value chat data model |
| **Complex Queries** | Chat data needs simple lookups, not complex JOINs |
| **Connection Pooling** | Must manage connection limits across microservices |
| **Server Management** | Storage, CPU, memory allocation headaches |

#### Data Model: Why DynamoDB Fits

**Chat Application Data Characteristics:**
```
Conversations Table:
- PK: conversation_id (UUID)
- Simple structure: user_id, title, created_at, updated_at
- No JOINs needed (just key lookups)
- Queries: Get conversation by ID, Query by user_id with GSI

Messages Table:
- PK: conversation_id, SK: timestamp (FIFO ordering)
- Simple structure: message_id, sender, content, created_at
- No JOINs needed
- Queries: Get messages by conversation, pagination

Settings Table:
- PK: user_id (or system_settings)
- Simple structure: preferences, system_prompt
- No JOINs needed
- Queries: Get user settings, update preferences
```

**❌ No complex queries that PostgreSQL would excel at:**
- No multi-table transactions
- No aggregations across millions of rows
- No complex analytical queries
- No full-text search requirements

**✅ Perfect DynamoDB use case:**
- Key-value lookups (fast, predictable)
- Partition key access patterns (email/user_id)
- TTL-based auto-expiration
- Global secondary indexes for alternate access patterns

---

## Backend Language & Framework

### ✅ Chosen: **Python + FastAPI**

#### Why Python/FastAPI is Right for This Project

| Aspect | Advantage |
|--------|-----------|
| **Development Speed** | ✅ Rapid prototyping, minimal boilerplate |
| **AI/ML Integration** | ✅ Best ecosystem (OpenAI SDK, LangChain, etc.) |
| **Data Science** | ✅ NumPy, Pandas, scikit-learn all Python-native |
| **Learning Curve** | ✅ Beginner-friendly, great for teaching microservices |
| **Framework** | ✅ FastAPI is modern, async, auto-docs (Swagger) |
| **AWS SDK** | ✅ Boto3 is production-grade, well-maintained |
| **Docker** | ✅ Small images, good performance in containers |
| **Cost** | ✅ Low memory footprint, cheap to run on EKS |
| **Team Velocity** | ✅ Features ship faster than Java/.NET |

#### Performance: Python vs Alternatives

```
REQUEST LATENCY (measured in milliseconds, lower is better):

┌────────────────────────────────────────────────────────────┐
│ Technology    │ Simple GET │ DynamoDB Query │ AI Call    │
├────────────────────────────────────────────────────────────┤
│ FastAPI/Py    │ 2-5ms      │ 15-30ms        │ 500-2000ms │
│ Node.js/Expr  │ 1-3ms      │ 15-30ms        │ 500-2000ms │
│ Java/Spring   │ 5-10ms     │ 15-30ms        │ 500-2000ms │
│ .NET/Core     │ 3-8ms      │ 15-30ms        │ 500-2000ms │
│ Go/Gin        │ 1-2ms      │ 15-30ms        │ 500-2000ms │
└────────────────────────────────────────────────────────────┘

📊 BOTTLENECK: AI API calls (500-2000ms), not Python runtime!
   Python framework choice is irrelevant for this app.
```

#### Why NOT Java?

| Issue | Impact | Severity |
|-------|--------|----------|
| **Startup Time** | 5-15 seconds JVM warmup | ⚠️ High in K8s autoscaling |
| **Memory Usage** | 300-500MB per service | ⚠️ 3x higher EKS costs |
| **Container Size** | 500MB+ images | ⚠️ Longer deployments |
| **Development Speed** | Verbose boilerplate | ⚠️ Slower iteration |
| **Team** | May not know Java | ⚠️ Learning overhead |
| **Overkill** | Type system for simple API | ❌ Unnecessary complexity |

**Example: Same endpoint in Java vs Python**

Java Spring Boot:
```java
@RestController
@RequestMapping("/api/conversations")
public class ConversationController {
    
    @Autowired
    private ConversationService conversationService;
    
    @PostMapping
    public ResponseEntity<ConversationDTO> create(
        @RequestBody CreateConversationRequest req
    ) {
        ConversationEntity entity = conversationService.create(
            req.getUserId(),
            req.getTitle()
        );
        return ResponseEntity.ok(
            new ConversationDTO(entity)
        );
    }
}
```

Python FastAPI:
```python
@router.post("/api/conversations")
async def create_conversation(
    req: CreateConversationRequest
):
    entity = await conversation_service.create(
        req.user_id,
        req.title
    )
    return ConversationDTO.from_entity(entity)
```

**Result**: Python is 50% less code, same functionality!

#### Why NOT .NET/C#?

| Issue | Impact |
|-------|--------|
| **Open Source Immaturity** | .NET Core is newer, less battle-tested than Java/Python |
| **AWS Tooling** | Fewer libraries than Python/JavaScript ecosystem |
| **Learning Resource** | Less free content on microservices with .NET |
| **Team Fit** | Python is more universally known |
| **Docker Size** | Similar to Java (heavy) |

#### Why NOT Node.js?

| Issue | Impact |
|-------|--------|
| **AI/ML Libraries** | 80% less mature than Python ecosystem |
| **OpenAI Integration** | Python SDK is better maintained |
| **Data Science** | Not viable for AI workloads |
| **Type Safety** | TypeScript adds complexity without AI benefits |
| **Prototype Focus** | Good for APIs but weak for ML integration |

#### Why NOT Go?

| Issue | Impact |
|-------|--------|
| **Startup Speed** | Excellent (faster than all others) |
| **Memory Efficiency** | Excellent (uses less memory) |
| **BUT** | Very difficult to integrate with OpenAI, LangChain, ML libraries |
| **Trade-off** | Go wins on ops but loses on AI capabilities |

**✅ Verdict**: Python is the ONLY good choice for an LLM-based application.

---

## Frontend Technology

### ✅ Chosen: **React + JavaScript**

#### Why React is Right for This Project

| Aspect | Advantage |
|--------|-----------|
| **Component Library** | ✅ Reusable, composable UI patterns |
| **State Management** | ✅ React Hooks simple for chat UI |
| **Ecosystem** | ✅ Best-in-class libraries (React Query, Zustand) |
| **Dev Tools** | ✅ React DevTools, hot reload excellent |
| **Deployment** | ✅ Static build, served by Nginx (cheap!) |
| **Learning Curve** | ✅ Easier than Angular for beginners |
| **Performance** | ✅ Virtual DOM handles frequent updates well |
| **Job Market** | ✅ Most sought-after frontend skill |

#### Architecture: Why Nginx Static Build

```
Frontend Deployment:
┌────────────────────────────────────────┐
│  React Build Output                    │
│  (Static HTML, CSS, JS bundles)        │
├────────────────────────────────────────┤
│  Nginx Reverse Proxy                   │
│  ├─ Serves static files (fast)         │
│  ├─ Reverse proxies API calls to       │
│  │  Backend services                   │
│  └─ Handles compression, caching       │
├────────────────────────────────────────┤
│  LoadBalancer (AWS ALB)                │
│  Public IP accessible from browser     │
└────────────────────────────────────────┘

Cost: $3-5/month for Nginx pod
Benefits:
- ✅ No Node.js server overhead
- ✅ Ultra-fast static file serving
- ✅ Efficient load balancing
- ✅ Easy caching headers
```

#### Why NOT Next.js?

| Issue | Impact |
|-------|--------|
| **Server Overhead** | Requires Node.js server (adds cost) |
| **Complexity** | Adds routing, SSR capabilities we don't need |
| **Deployment** | Can't just use Nginx; needs Node runtime |
| **For This Project** | Simple SPA is sufficient, zero benefit |

#### Why NOT Angular?

| Issue | Impact |
|-------|--------|
| **Learning Curve** | Much steeper than React |
| **Boilerplate** | More complex setup for simple chat UI |
| **Bundle Size** | Larger default bundles |
| **Team** | React is more universally known |

#### Why NOT Vue?

| Issue | Impact |
|-------|--------|
| **Ecosystem** | Smaller community than React |
| **Job Market** | Fewer opportunities for team |
| **Libraries** | Less mature UI libraries |
| **Scalability** | React better for large applications |

---

## Message Queue & Async Processing

### ✅ Chosen: **AWS SQS (Standard + FIFO)**

#### Why SQS is Right for This Project

| Aspect | Advantage |
|--------|-----------|
| **Managed Service** | ✅ No queue server to manage |
| **AWS Integration** | ✅ Works seamlessly with IAM, EKS, Lambda |
| **FIFO Guarantee** | ✅ Messages processed in order (important for chat) |
| **DLQ Support** | ✅ Dead letter queues for failed messages |
| **Scalability** | ✅ Unlimited message throughput |
| **Cost** | ✅ Cheap ($0.40 per million messages) |
| **Simplicity** | ✅ No cluster/replication setup needed |

#### Why NOT RabbitMQ?

| Comparison | SQS | RabbitMQ |
|-----------|-----|----------|
| **Setup** | None (AWS manages) | Deploy, manage, scale cluster |
| **Replication** | Built-in multi-AZ | Manual setup required |
| **Cost** | $0.40/M messages | $150-500/month (server) |
| **Operations** | 0 hours/month | 10+ hours/month maintenance |
| **Availability** | 99.99% SLA | Depends on your ops |
| **Learning** | Simple API | Complex, many features |
| **Team** | AWS credentials | Queue admin knowledge |

**Example: SQS vs RabbitMQ Operations**

RabbitMQ Setup:
```bash
# Install
brew install rabbitmq

# Start service
brew services start rabbitmq-server

# Create queue
rabbitmqctl add_user chatbot password
rabbitmqctl set_permissions -p / chatbot ".*" ".*" ".*"

# Create queue
# Must use web UI or complex CLI commands
# Monitor manually or setup Prometheus

# Backup strategy
# Must configure replication
# Must manage node failures
```

SQS Setup:
```bash
# Create queue
aws sqs create-queue --queue-name ai-jobs.fifo --attributes FifoQueue=true

# Done! Everything else is AWS responsibility.
```

#### Why NOT Kafka?

| Issue | Impact |
|-------|--------|
| **Complexity** | Kafka is for massive scale (millions msg/sec) |
| **Learning Curve** | Complex topics, partitions, consumer groups |
| **Operations** | Requires Kafka cluster management |
| **Cost** | Self-hosted: $1000+/month infrastructure |
| **Overkill** | We need 10-100 messages/sec, not 100,000+ |

**When to use Kafka**: Netflix, Uber, Airbnb (thousands msg/sec)  
**When to use SQS**: Most startups and internal tools

---

## Container Orchestration

### ✅ Chosen: **Kubernetes (AWS EKS)**

#### Why Kubernetes/EKS is Right for This Project

| Aspect | Advantage |
|--------|-----------|
| **Industry Standard** | ✅ 99% of enterprises use Kubernetes |
| **Portability** | ✅ Can run on AWS, Azure, Google Cloud, on-prem |
| **Auto-scaling** | ✅ HPA + KEDA handle traffic spikes |
| **High Availability** | ✅ Multi-AZ, self-healing, rolling updates |
| **Secrets Management** | ✅ Built-in secrets, config maps |
| **Cost** | ✅ EKS is cheaper than Lambda for sustained workloads |
| **Learning** | ✅ Best skill for DevOps/SRE career |
| **Scalability** | ✅ Handles 100+ services easily |

#### Architecture Benefits: Why Microservices Need K8s

```
Single Application on Kubernetes:

┌─────────────────────────────────────────────────────────────┐
│                      AWS EKS Cluster                        │
│                     (Multi-AZ Setup)                        │
├──────────────────────┬──────────────────┬──────────────────┤
│   Availability       │  Availability    │  Availability    │
│   Zone 1             │  Zone 2          │  Zone 3          │
├──────────────────────┼──────────────────┼──────────────────┤
│ ┌────────────────┐   │ ┌────────────┐   │ ┌────────────┐   │
│ │ Gateway Pod    │   │ │ Gateway    │   │ │ Gateway    │   │
│ ├────────────────┤   │ └────────────┘   │ └────────────┘   │
│ │ Conversations  │   │ ┌────────────┐   │ ┌────────────┐   │
│ │ Pod (2x)       │   │ │Conversations   │ │ Conversat..│   │
│ ├────────────────┤   │ └────────────┘   │ └────────────┘   │
│ │ Messages Pod   │   │ ┌────────────┐   │ ┌────────────┐   │
│ │(2x)            │   │ │ Messages   │   │ │ Messages   │   │
│ ├────────────────┤   │ └────────────┘   │ └────────────┘   │
│ │ AI Worker      │   │ ┌────────────┐   │ ┌────────────┐   │
│ │ (1-10 pods)    │   │ │ AI Worker  │   │ │ AI Worker  │   │
│ └────────────────┘   │ └────────────┘   │ └────────────┘   │
└──────────────────────┴──────────────────┴──────────────────┘
         ↑                    ↑                    ↑
    If AZ1 fails,      If AZ2 fails,      If AZ3 fails,
    pods auto-migrate  pods auto-migrate  pods auto-migrate
    to AZ2/AZ3         to AZ1/AZ3         to AZ1/AZ2
```

#### Why NOT Docker Compose/Swarm?

| Feature | K8s | Docker Swarm |
|---------|-----|--------------|
| **High Availability** | ✅ Auto-healing, multi-node | ❌ Basic |
| **Auto-scaling** | ✅ HPA, KEDA | ❌ Manual |
| **Rolling Updates** | ✅ Zero-downtime | ⚠️ Complex |
| **Multi-Region** | ✅ Easy federation | ❌ Not supported |
| **Team Size** | ✅ Scales to 100+ | ❌ Breaks at 5+ nodes |
| **Learning** | ✅ Industry standard | ❌ Dying tech |

**Docker Compose only works for:**
- Local development
- Single machine deployments
- Small internal tools

#### Why NOT AWS Lambda?

| Issue | Impact | Cost at Scale |
|-------|--------|---------------|
| **Cold Start** | 1-5 second delay on first call | ⚠️ Bad for chat UX |
| **Concurrent Invocations** | Limited to 1000 by default | ⚠️ Throttling |
| **Cost** | $0.20 per 1M requests + compute | ❌ $500+/month at scale |
| **Dependencies** | 250MB deployment package limit | ⚠️ LangChain won't fit |
| **Timeout** | 15-minute limit | ⚠️ Long-running AI tasks fail |
| **Complexity** | API Gateway, VPC, triggers setup | ⚠️ More ops work |

**Cost Comparison**: Lambda vs EKS
```
1000 requests/day, avg 500ms runtime:

Lambda:
- Requests: 365,000/year = $0.20 per 1M = $73
- Compute: 365,000 * 0.5s * $0.0000166667 = $3,041
- Total: ~$3,114/month

EKS:
- t3.medium node: $30/month
- 4 nodes: $120/month
- DynamoDB: $30/month
- Total: ~$150/month (20x cheaper!)
```

#### Why NOT AWS Fargate?

| Comparison | EKS | Fargate |
|-----------|-----|---------|
| **Setup** | More complex initially | Simpler, but limited |
| **Cost** | $150-250/month | $300-500/month (more expensive) |
| **Scaling** | Full control | Limited options |
| **Persistent Storage** | Flexible (PVC, EBS) | Limited support |
| **Networking** | Full control | Constrained |
| **For This Project** | ✅ Best fit | ❌ Unnecessarily expensive |

---

## Infrastructure & Cloud Provider

### ✅ Chosen: **AWS (with EKS, DynamoDB, SQS)**

#### Why AWS is Right for This Project

| Aspect | Advantage |
|--------|-----------|
| **Service Breadth** | ✅ 200+ services for every need |
| **Market Leadership** | ✅ 33% market share, most mature |
| **Ecosystem** | ✅ Most libraries, documentation, community |
| **Cost Optimization** | ✅ Spot instances, reserved capacity, savings plans |
| **Global Reach** | ✅ 30+ regions, best worldwide coverage |
| **IAM/Security** | ✅ Most granular access controls |
| **Organization** | ✅ AWS free tier, credits for startups |

#### Multi-Cloud Consideration

```
MULTI-CLOUD PORTABILITY:

┌────────────────────────────────────────────────────────────┐
│ Layer            │ Portable? │ Effort   │ Value            │
├────────────────────────────────────────────────────────────┤
│ Kubernetes       │ ✅ Yes    │ 5 min   │ High (go/azure)  │
│ Containers       │ ✅ Yes    │ 5 min   │ High             │
│ Python Code      │ ✅ Yes    │ 1 hour  │ Medium           │
│ DynamoDB → ??    │ ⚠️ Partial│ 2-3days │ Low (reinvent)   │
│ SQS → ??         │ ⚠️ Partial│ 2-3days │ Low (reinvent)   │
│ IAM/IRSA         │ ❌ No     │ 1-2day  │ Low (rearchitect)│
│                  │           │         │                  │
│ NET PORTABILITY  │ ~40%      │ 1 week  │ Not worth effort  │
└────────────────────────────────────────────────────────────┘

DECISION: Build for AWS, not multi-cloud.
- Multi-cloud abstractions (Terraform) add 15-20% complexity
- Costs more (~10% infrastructure premium)
- Takes 2-3x longer to deploy
- Rarely migrates in practice (vendor lock-in is rare)

Focus: Be GOOD at AWS, not mediocre at 3 clouds.
```

#### Why NOT Azure?

| Issue | Impact |
|-------|--------|
| **Learning Curve** | Different naming, concepts than industry standard |
| **Ecosystem** | 30% fewer libraries than AWS |
| **Global Regions** | Fewer locations than AWS |
| **Cost** | Slightly more expensive for this workload |
| **For Enterprise** | Good if company mandate exists |
| **For Startups** | AWS is better choice |

#### Why NOT Google Cloud?

| Issue | Impact |
|-------|--------|
| **Market Share** | 10% market share, smaller ecosystem |
| **Data Science** | Excellent (BigQuery, Vertex AI) but overkill for chat |
| **Learning Resources** | Far fewer tutorials than AWS |
| **Kubernetes** | GKE is best-in-class, but more complex |
| **Cost** | Competitive but ecosystem advantage lost |

#### Why NOT On-Premises/Self-Hosted?

| Issue | Impact | Time Cost |
|-------|--------|-----------|
| **Infrastructure** | Servers, networking, power, cooling | Setup: 2-3 weeks |
| **Expertise** | Need sysadmin, network engineer | Hiring: $100k+/year |
| **Disaster Recovery** | Manual setup, partial solution | Setup: 1 week |
| **Scaling** | Buy new servers, wait for delivery | Scaling: 2-4 weeks |
| **Security** | Firewalls, patches, compliance | Ongoing: 10+ hours/month |
| **Availability** | 99.5% typical (AWS is 99.99%) | Outages: $50k/hour lost |

**Total Cost of On-Prem**: $200k+ setup + $50k+/year maintenance  
**AWS Cost**: $150-300/month (99.99% uptime included)

---

## Summary Decision Matrix

### Technology Stack Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                    LLM CHATBOT TECH STACK                        │
├──────────────┬──────────────┬──────────────┬─────────────────────┤
│ Layer        │ Chosen       │ Alternatives │ Why Chosen          │
├──────────────┼──────────────┼──────────────┼─────────────────────┤
│ Cloud        │ AWS          │ Azure, GCP   │ Best ecosystem      │
│ K8s          │ EKS          │ GKE, AKS     │ AWS integration     │
│ Language     │ Python 3.11  │ Java, .NET   │ AI/ML best fit      │
│ Framework    │ FastAPI      │ Flask, Django│ Modern, async       │
│ Frontend     │ React        │ Vue, Angular │ Best libraries      │
│ Serving      │ Nginx        │ Node.js      │ Lightweight         │
│ Database     │ DynamoDB     │ PostgreSQL   │ 87% cost savings    │
│ Queue        │ SQS          │ RabbitMQ     │ Managed service     │
│ LLM          │ OpenAI API   │ Bedrock      │ Best models/API     │
│ Monitoring   │ CloudWatch   │ Prometheus   │ AWS native          │
│ IaC          │ Terraform    │ CloudFormation│ Cloud-agnostic     │
│ Secrets      │ Secrets Mgr  │ HashiCorp    │ AWS integrated      │
│ Auth         │ IRSA         │ API keys     │ Zero secrets needed │
└──────────────┴──────────────┴──────────────┴─────────────────────┘
```

### Trade-offs Made

| Decision | Benefit | Trade-off |
|----------|---------|-----------|
| **Python** | AI/ML friendly, fast development | Slightly slower runtime (irrelevant) |
| **DynamoDB** | 87% cheaper, no ops | No complex queries (not needed) |
| **SQS** | Managed, simple | Less features than Kafka (overkill anyway) |
| **EKS** | Industry standard, powerful | Complex to learn initially |
| **AWS** | Best ecosystem | Higher cloud spend vs self-hosted (worth it) |

---

## Cost Summary

### Monthly Infrastructure Cost Breakdown

```
┌────────────────────────────────────────────────────────────┐
│             PRODUCTION COST ESTIMATE                       │
├────────────────────────────────────────────────────────────┤
│ Compute (EKS)                             $150-250/month   │
│ Database (DynamoDB pay-per-req)           $20-50/month    │
│ Message Queue (SQS)                       $5-10/month     │
│ Load Balancer (ALB)                       $16/month       │
│ Data Transfer                             $10-20/month    │
│ CloudWatch Logs (7-day retention)         $10-20/month    │
│ Secrets Manager                           $1/month        │
│                                           ─────────────   │
│ INFRASTRUCTURE TOTAL                      $212-367/month  │
│                                                           │
│ OpenAI API (main cost driver)             $100-10,000+    │
│ GRAND TOTAL                               $300-10,400+    │
│                                                           │
│ 💡 Optimize OpenAI, not infrastructure!                   │
└────────────────────────────────────────────────────────────┘
```

### What This Gets You

✅ **Uptime**: 99.99% SLA (26 seconds downtime/month)  
✅ **Scalability**: 0-100+ concurrent users instantly  
✅ **Reliability**: Auto-healing, multi-AZ failover  
✅ **Security**: IAM roles, encryption, no passwords  
✅ **Observability**: CloudWatch logs, metrics, alarms  
✅ **Disaster Recovery**: RTO <1min, RPO <5min  

---

## Key Learnings

1. **Choose for Your Use Case, Not Hype**
   - Lambda is hyped but expensive at scale
   - RabbitMQ is mature but overkill
   - Kubernetes is complex but necessary for 6+ services

2. **Language Matters Less Than Ecosystem**
   - Python is 10% slower but 10x better for AI
   - Java is 10% faster but 3x slower to develop
   - Trade-off: Use Python

3. **Managed Services Win for Operations**
   - DynamoDB: 0 ops, $30/month
   - Self-hosted Postgres: 10 hrs/month ops, $50/month
   - Trade-off: Use managed

4. **Cost Optimization Hierarchy**
   - OpenAI API: $1000-10,000/month (main driver)
   - Infrastructure: $200-400/month (secondary)
   - Optimization effort: 90% on AI costs, 10% on infra

5. **Technology Lock-in is Normal**
   - 40% of your stack is AWS-specific (DynamoDB, SQS, IAM)
   - This is fine for 99% of companies
   - Multi-cloud is rarely needed in practice

---

## Conclusion

This technology stack was chosen because:

✅ **Cost-Optimized**: $200-400/month infrastructure  
✅ **Production-Ready**: 99.99% uptime, auto-scaling, multi-AZ  
✅ **LLM-Focused**: Python ecosystem is unmatched for AI  
✅ **Team-Friendly**: Microservices teach best practices  
✅ **Industry-Standard**: Skills transfer to other jobs  
✅ **Operationally Simple**: Managed services reduce toil  

Not the fanciest, not the fastest, but the *right fit* for this project's goals.

---

## Testing & CI choices (brief)

We selected pragmatic testing and CI patterns to balance fast PR feedback with reliable integration validation:

- **Python tests**: `pytest` for unit and API tests. Integration-style API tests run in-process with FastAPI `TestClient` and an in-memory `FakeTable` so tests don't hit AWS.
- **Frontend tests**: Node's test runner + JSDOM (`node --test`) for DOM-level checks. Tests inline `public/assets/app.js` or stub `window.fetch` to prevent network calls in CI.
- **CI strategy**: two synced workflow pairs — `microservices-unit-tests.yml` (PRs, fast) and `integration-tests.yml` (main, slower integration suites), each mirrored under `infra/github-actions/`.
- **Release workflow**: the top-level `.github/workflows/ci-cd.yml` workflow handles the full release path. It runs on `push`, `pull_request`, and `workflow_dispatch`, with path filters so it only starts for relevant backend, frontend, or infra changes.
- **Reporting**: Python tests emit JUnit XML (`--junitxml`) plus coverage XML/HTML via `pytest-cov`, and the frontend uses Node's built-in JUnit test reporter so GitHub Actions can show test summaries and artifacts without a JSON conversion step.

This approach keeps PR feedback fast while preserving full integration validation on protected branches.

---

**Last Updated**: May 30, 2026  
**Status**: ✅ FINAL DECISION  
**Migration Path**: None (this was the chosen path from day 1)
