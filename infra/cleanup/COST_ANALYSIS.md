# Cost Analysis - Savings from Cleanup

**Date**: May 24, 2026  
**Analysis**: Pre-cleanup vs post-cleanup AWS costs

---

## Current Infrastructure Costs (Before Cleanup)

### Monthly Costs Breakdown

| Service | Component | On-Demand | Spot | Details |
|---------|-----------|-----------|------|---------|
| **EKS** | Control Plane | $73 | $73 | Fixed, 1 cluster |
| **EC2** | 4x t3.medium nodes | $300 | $100 | Compute instances |
| **DynamoDB** | 3 tables (PAY_PER_REQUEST) | $30 | $30 | conversations, messages, settings |
| **SQS** | 2 FIFO queues | $5 | $5 | ai-jobs.fifo, ai-jobs-dlq.fifo |
| **CloudWatch** | Logs (7-day retention) | $20 | $20 | All services + EKS logs |
| **Data Transfer** | Between AZs | $20 | $20 | Multi-AZ costs |
| **Secrets Manager** | 1 secret | $1 | $1 | llm-chatbot/openai-key |
| **ECR** | Storage (6 images) | $5 | $5 | Docker images |
| **Elastic IPs** | 2 ALB IPs (if NAT) | $10 | $10 | Optional |
| **---** | --- | --- | --- | --- |
| **TOTAL** | **Monthly Infrastructure** | **$464** | **$264** | **~$5,568-$3,168/year** |

### NOT Included (Your Costs)

| Service | Monthly | Notes |
|---------|---------|-------|
| OpenAI API | $100-$10,000 | Dominant cost - based on usage |
| Domain & SSL | $0-50 | Optional, depends on DNS provider |
| Backup/DR | $0-100 | Optional S3 storage |
| Monitoring (Grafana/Prometheus) | $0-50 | Optional commercial tools |
| **TOTAL APPLICATION** | **$100-$10,200** | **Your actual cost** |

### Total Monthly Production Cost

```
Infrastructure (On-Demand):  $464
OpenAI API:                  $100-$10,000
──────────────────────────────────────
TOTAL:                       $564-$10,464/month

With Spot Instances:
Infrastructure (Spot):       $264
OpenAI API:                  $100-$10,000
──────────────────────────────────────
TOTAL:                       $364-$10,264/month
```

---

## Post-Cleanup Costs (After Cleanup)

### Deleted Resources & Monthly Savings

| Resource | Cost | Status | Savings |
|----------|------|--------|---------|
| EKS Control Plane | $73 | ✗ DELETED | -$73 |
| EC2 Nodes (4x) | $300/$100 | ✗ DELETED | -$300/-$100 |
| DynamoDB Tables | $30 | ✗ DELETED | -$30 |
| SQS Queues | $5 | ✗ DELETED | -$5 |
| CloudWatch Logs | $20 | ✗ DELETED | -$20 |
| Data Transfer | $20 | ✗ DELETED | -$20 |
| Secrets Manager | $1 | ✗ DELETED | -$1 |
| ECR Storage | $5 | ✗ DELETED | -$5 |
| ALB/NAT Gateway | $10 | ✗ DELETED | -$10 |
| **---** | --- | --- | --- |
| **TOTAL MONTHLY SAVINGS** | **$464** | **on-demand** | **-$464** |
| **TOTAL MONTHLY SAVINGS** | **$264** | **spot** | **-$264** |

### Post-Cleanup Infrastructure Cost

```
EKS Infrastructure:          $0
OpenAI API:                  $100-$10,000 (still running)
Other Services:              $0
──────────────────────────────────────
TOTAL:                       $100-$10,000/month
```

**Cost Reduction**: 76-99% of infrastructure costs eliminated

---

## Annual Savings

### Year-Over-Year Comparison

| Period | On-Demand | Spot | OpenAI Only |
|--------|-----------|------|-------------|
| **Before Cleanup** | | | |
| Monthly | $464 | $264 | $100-$10,000 |
| Quarterly | $1,392 | $792 | $300-$30,000 |
| Annual | $5,568 | $3,168 | $1,200-$120,000 |
| | | | |
| **After Cleanup** | | | |
| Monthly | $0 | $0 | $100-$10,000 |
| Quarterly | $0 | $0 | $300-$30,000 |
| Annual | $0 | $0 | $1,200-$120,000 |
| | | | |
| **SAVINGS** | | | |
| Monthly | **-$464** | **-$264** | **$0** |
| Quarterly | **-$1,392** | **-$792** | **$0** |
| Annual | **-$5,568** | **-$3,168** | **$0** |

---

## Scenario Analysis

### Scenario 1: Development Environment (Not Cleaned Up)

```
Year 1:  $464/month × 12 = $5,568
Year 2+: $464/month × 12 = $5,568/year (recurring)

3-Year Cost: $16,704 infrastructure + OpenAI costs
```

### Scenario 2: With Cleanup After 3 Months

```
Months 1-3:  $464 × 3 = $1,392 (infrastructure)
Months 4-36: $0 (infrastructure after cleanup)

3-Year Infrastructure Cost: $1,392
Total Savings: $16,704 - $1,392 = $15,312
```

### Scenario 3: With Cleanup After 1 Year

```
Months 1-12:  $464 × 12 = $5,568 (infrastructure)
Months 13-36: $0 (infrastructure after cleanup)

3-Year Infrastructure Cost: $5,568
Total Savings: $16,704 - $5,568 = $11,136
```

---

## Cost Savings by Service

### EKS Control Plane: $73/month
- Fixed cost regardless of workload
- ONE per cluster (not per node)
- Recurring whether used or not
- **Cleanup Impact**: Remove $876/year

### EC2 Compute: $300/month (on-demand) or $100/month (spot)
- Main cost driver for infrastructure
- 4 nodes × t3.medium
- Scales up to 10 nodes under load
- **Cleanup Impact**: Remove $3,600-$1,200/year

### DynamoDB: $30/month
- Pay-per-request pricing (no provisioning)
- 3 tables × operations
- Minimal cost compared to provisioned
- **Cleanup Impact**: Remove $360/year

### SQS: $5/month
- 2 FIFO queues (main + DLQ)
- Minimal usage ($0.40 per million requests)
- **Cleanup Impact**: Remove $60/year

### CloudWatch: $20/month
- Log storage (7 days) + metrics
- Reduced if using shorter retention
- **Cleanup Impact**: Remove $240/year

### Data Transfer: $20/month
- Between availability zones
- Multi-AZ communication costs
- Reduced with fewer nodes
- **Cleanup Impact**: Remove $240/year

### Storage & Miscellaneous: $16/month
- Secrets Manager: $1
- ECR Storage: $5
- NAT Gateway: $10
- **Cleanup Impact**: Remove $192/year

---

## When to Cleanup vs Rebuild

### CLEANUP if:
- ✅ Not using cluster for >2 weeks
- ✅ Testing/development phase complete
- ✅ No active users
- ✅ Can rebuild in <4 hours if needed
- ✅ Want to save $464/month immediately

### KEEP RUNNING if:
- ❌ Active production traffic
- ❌ Need <5min deployment time
- ❌ Still in active development
- ❌ Testing or demo scenarios ongoing
- ❌ OpenAI costs dominate (cleanup saves <10%)

---

## ROI Analysis - Cleanup Effort

### Cleanup Effort: 45 minutes

```
Time to cleanup:    45 minutes
Monthly savings:    $464
Hourly savings:     $464 ÷ 730 hours = $0.63/hour
Payback period:     45 min ÷ 0.63 = 71 hours
                    ~3 days of NOT running
```

### Rebuild Effort: 4-5 hours

```
Time to rebuild:    4-5 hours
Cost of rebuild:    $3-4 in compute + your time
Break-even:         If cluster unused for 10+ days
```

### Decision Matrix

| Days Idle | Keep Running | Cleanup | Recommendation |
|-----------|--------------|---------|----------------|
| 1-5 days | $15-77 cost | Cleanup cost: $0 | **CLEANUP** |
| 5-10 days | $77-154 cost | Cleanup + rebuild | **CLEANUP** |
| 10-30 days | $154-462 cost | Much larger savings | **CLEANUP** |
| 30+ days | $462+ cost | Full monthly savings | **DEFINITELY CLEANUP** |
| <1 day | $<15 cost | Cleanup effort > savings | **KEEP RUNNING** |

---

## Cost Optimization Before Cleanup

### If You Want to Keep Running

Options to reduce costs:

1. **Use Spot Instances** (50-70% savings)
   - Estimated: $100/month (vs $300)
   - Trade-off: Can be interrupted
   - Update: `eksctl` cluster.yaml `spot: true`

2. **Reduce Node Count**
   - From 4 to 2 nodes: $150/month
   - From 4 to 1 node: $75/month
   - Trade-off: Less resilience

3. **Smaller Instance Type**
   - t3.small instead of t3.medium: $150/month
   - Trade-off: Slower performance

4. **Reduce Logging Retention**
   - From 7 days to 1 day: Save ~$15/month
   - Trade-off: Less history

5. **Combine Above**
   - Spot + smaller nodes: $50-75/month
   - Suitable for dev/test only

### Cost Comparison

```
Current:                 $464/month
With all optimizations:  $50-75/month
With cleanup:            $0/month
```

---

## Budget Allocation

### Recommended Spending Profile

| Phase | Duration | Focus | Infrastructure | OpenAI | Total |
|-------|----------|-------|------------------|--------|-------|
| **MVP/Dev** | 2-3 months | Build & test | $264 (spot) | $500-2,000 | $764-2,264 |
| **Beta** | 1-2 months | Limited users | $464 | $1,000-5,000 | $1,464-5,464 |
| **Production** | Ongoing | Scale | $464-1,000+ | $5,000-50,000+ | $5,464-51,000+ |
| **Off-Season** | Periodic | Paused | $0 (cleanup) | $0 | $0 |

---

## AWS Cost Explorer Setup

### View These Metrics Post-Cleanup

1. **By Service**:
   - EKS: Should be $0
   - EC2: Should be $0
   - DynamoDB: Should be $0
   - SQS: Should be $0
   - Total: Should be $0 ±$5

2. **By Tag**:
   - Filter by `Environment=production`
   - Should show $0 for infrastructure

3. **Trends**:
   - Create trend line
   - Should drop to baseline after cleanup date

---

## Conclusion

### Pre-Cleanup
- Monthly Cost: **$464** (infrastructure) + $100-$10,000 (OpenAI)
- Annual Cost: **$5,568** (infrastructure) + $1,200-$120,000 (OpenAI)
- Per User: Depends on OpenAI usage

### Post-Cleanup
- Monthly Cost: **$0** (infrastructure) + $100-$10,000 (OpenAI)
- Annual Cost: **$0** (infrastructure) + $1,200-$120,000 (OpenAI)
- Per User: Depends on OpenAI usage

### Recommendation
**CLEANUP now if**:
- Not in active development
- Need to save $464/month
- Can rebuild in 4-5 hours when needed
- Want to eliminate infrastructure overhead

**KEEP if**:
- Active production or development
- Need <5min redeploy time
- Infrastructure cost justified by usage

---

**Status**: Ready to execute cleanup and save infrastructure costs  
**Estimated Savings**: $464/month on-demand or $264/month with spot instances  
**Next Action**: Run cleanup procedures in [CLEANUP_RUNBOOK.md](CLEANUP_RUNBOOK.md)
