# Infrastructure Roadmap

This document turns the current infrastructure priorities into a phased plan.

## Goal

Deliver a production-ready, budget-conscious AWS deployment for the chatbot with safe releases, test coverage, observability, and clear operational ownership.

In plain terms: first make it build and deploy reliably, then make it observable and secure, then make it cheaper and easier to recover when something breaks.

## Guiding Principles

- **Work from the foundation up**: automate deployment before adding advanced platform features.
- **Keep each phase shippable**: every phase should leave the system in a usable state.
- **Prefer low-ops AWS services**: use managed services where possible to reduce maintenance.
- **Make failures visible**: logs, metrics, and tests should tell us what broke and why.

## Phased Plan

### Phase 1: CI/CD and Release Automation

**What we do**
- Build GitHub Actions for tests, image builds, ECR pushes, and Helm deployments.
- Add caching and JUnit test reports so runs are faster and easier to inspect.

**Why it comes first**
- Without repeatable releases, every later change is slower and riskier.
- This gives us a predictable path from code change to deployed app.

**Layman explanation**
Think of this as installing the conveyor belt before opening the factory floor.

**Output**
- Test job
- Build/push job
- Helm deploy job
- Basic rollback path

### Phase 2: Infrastructure Provisioning Automation

**What we do**
- Make cluster and AWS resource setup repeatable.
- Standardize EKS, ECR, DynamoDB, SQS, and IAM bootstrap steps.

**Why it comes next**
- Deployment automation is only fully useful when the environment can be created the same way every time.

**Layman explanation**
This removes the need to click around manually every time we need a new environment.

**Output**
- Idempotent bootstrap scripts
- Documented AWS setup steps
- Environment variables and naming conventions

### Phase 3: Security and Identity Hardening

**What we do**
- Tighten IAM roles and IRSA permissions.
- Review pod security settings and network policies.
- Keep secrets out of code and plain environment files.

**Why it comes here**
- Once deployment is predictable, we can safely lock down access without breaking the workflow.

**Layman explanation**
This is the part where we decide who can open which doors.

**Output**
- Least-privilege IAM
- Stronger pod security context
- Secrets management pattern

### Phase 4: Observability and Operations

**What we do**
- Add metrics, dashboards, alerts, and log retention rules.
- Make it easy to answer: what is broken, how bad is it, and where is it happening?

**Why it comes here**
- After the app can deploy safely, we need visibility into real runtime behavior.

**Layman explanation**
This is the dashboard and alarm system for the whole platform.

**Output**
- Prometheus/Grafana or AWS-native metrics path
- CloudWatch dashboards
- Alert thresholds

### Phase 5: Reliability and Recovery

**What we do**
- Add backup and restore guidance for data services.
- Define retry, DLQ, and rollback behavior.
- Document failure recovery steps.

**Why it comes here**
- Once the system is observable, we can recover from real incidents faster and with less guesswork.

**Layman explanation**
This is the fire drill plan: what happens when something stops working.

**Output**
- DynamoDB export/backup approach
- SQS retry and DLQ handling
- Rollback runbook

### Phase 6: Cost and Capacity Optimization

**What we do**
- Review instance sizing and autoscaling thresholds.
- Add usage monitoring and cost alerts.
- Tune services for the budget-conscious target architecture.

**Why it comes last**
- Cost tuning is most effective after the system is stable and measurable.

**Layman explanation**
This is the bill review phase: we keep the lights on without wasting money.

**Output**
- Cost dashboard
- Scale-down strategy
- Resource tuning recommendations

## Suggested Delivery Order

| Phase | Focus | Result |
|------|-------|--------|
| 1 | CI/CD | Safe, repeatable releases |
| 2 | Provisioning | Repeatable environments |
| 3 | Security | Reduced risk and cleaner access |
| 4 | Observability | Better visibility into runtime behavior |
| 5 | Reliability | Faster recovery from incidents |
| 6 | Cost control | Lower monthly spend |

## How to Use This Roadmap

- Treat each phase as a small project.
- Do not start the next phase until the current one is documented and usable.
- Update the roadmap when priorities change or a phase is completed.

## Current Status

- Phase 1: In progress / mostly done
- Phase 2: Not started
- Phase 3: Not started
- Phase 4: Not started
- Phase 5: Not started
- Phase 6: Not started
