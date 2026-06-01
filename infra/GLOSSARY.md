# Glossary — plain-language definitions

Short, non-technical explanations of tools and services used in this project. Each entry has a short definition, why we use it here, and a short example of where to look or how it's used.

## Kubernetes & Cluster

- EKS / eksctl
	- What: Amazon EKS is a managed Kubernetes service. `eksctl` is the opinionated CLI tool we use to create and manage the cluster from `eksctl/cluster.yaml`.
	- Why: EKS removes most operational work for running Kubernetes; `eksctl` automates cluster and nodegroup creation so we can deploy with a repeatable config.
	- Example: run `eksctl create cluster -f infra/eksctl/cluster.yaml` to provision the cluster used by this repo.

- Kubernetes
	- What: An orchestration system that runs, schedules, and manages containers across many machines (nodes).
	- Why: It gives us service discovery, rolling updates, scaling, and self-healing for microservices.
	- Example: our microservices are deployed as `Deployment` objects in the `chatbot` namespace.

- Namespace
	- What: A logical partition in Kubernetes to group resources (like an isolated project space).
	- Why: We keep the application in the `chatbot` namespace to avoid mixing with system components.
	- Example: `kubectl get pods -n chatbot`.

- Deployment
	- What: A Kubernetes object that maintains a desired number of pod replicas and manages updates.
	- Why: We declare a `Deployment` per microservice so Kubernetes can restart crashed pods and roll out new images safely.
	- Example: `kubectl rollout status deployment/gateway -n chatbot`.

- Service (LoadBalancer / ClusterIP)
	- What: A stable network endpoint that routes traffic to pods. `LoadBalancer` exposes services externally; `ClusterIP` is internal-only.
	- Why: The frontend and gateway use `LoadBalancer` so they can receive external traffic; backend services use `ClusterIP` to stay internal.
	- Example: `kubectl get svc frontend -n chatbot` shows an external IP when LoadBalancer is ready.

- HPA (Horizontal Pod Autoscaler)
	- What: Automatically scales the number of pod replicas based on CPU, memory, or custom metrics.
	- Why: Keeps performance stable under load and saves cost when idle.
	- Example: `kubectl get hpa -n chatbot`.

- PDB (Pod Disruption Budget)
	- What: A policy that limits how many pods can be disrupted during maintenance.
	- Why: Prevents full service outages when nodes are upgraded or drained.
	- Example: We set PDBs so at least one replica remains available during node upgrades.

- NetworkPolicy
	- What: A Kubernetes resource that restricts which pods or namespaces may communicate with each other.
	- Why: Limits blast radius and enforces a zero-trust posture inside the cluster.
	- Example: `kubectl apply -f infra/helm/chatapp/templates/networkpolicy.yaml`.

- ALB (Application Load Balancer)
	- What: An AWS-managed load balancer that routes HTTP/HTTPS traffic into the cluster (often via an ingress controller).
	- Why: Provides TLS termination, path-based routing, and health checks for external traffic.
	- Example: the gateway ALB routes `/api/*` to the `gateway` service.

## Containers & Registry

- Docker
	- What: Tool to build and run containers (images with your app and its dependencies).
	- Why: Containers give consistent runtime environments for dev, CI, and production.
	- Example: `docker build -t llm-chatbot/gateway:latest ./microservices/gateway`.

- ECR (Elastic Container Registry)
	- What: AWS-hosted Docker registry where we push built images for the cluster to pull.
	- Why: Central, private storage for production images with IAM-based access control.
	- Example: `docker push $ECR_REGISTRY/llm-chatbot/gateway:latest`.

- Image tag
	- What: A label for an image version (e.g. `:1.2.0`, `:latest`).
	- Why: Tags let you control which image version is deployed; avoid `:latest` in production for reproducibility.
	- Example: Helm values specify image tags under `infra/helm/chatapp/values.yaml`.

## AWS Services

- DynamoDB
	- What: A fully-managed NoSQL key-value database used here to store conversations, messages, and settings.
	- Why: Fast, serverless scaling and pay-for-what-you-use pricing — ideal for chat records.
	- Example: tables `conversations`, `messages`, and `settings` created by runbook commands.

- SQS
	- What: A durable queue for passing messages between services (e.g., background AI jobs).
	- Why: Decouples producers and consumers so the AI worker can process jobs at its own rate and retry failures.
	- Example: `aws sqs send-message --queue-url <url> --message-body '{"conversation_id": "abc"}'`.

- Secrets Manager
	- What: Secure storage for API keys, DB credentials, and other secrets with automatic rotation options.
	- Why: Keeps secrets out of code and reduces risk if repos or nodes are compromised.
	- Example: store `OPENAI_API_KEY` in Secrets Manager and mount it to pods via IRSA or environment variables.

- IAM Role
	- What: A permission set that can be assumed by services, nodes, or pods to access AWS APIs.
	- Why: Grants least-privilege access for the cluster and workloads (e.g., read-only DynamoDB access for API pods).
	- Example: IRSA maps Kubernetes service accounts to IAM roles for pod-level AWS permissions.

- CloudWatch
	- What: Centralized logs and metrics platform for AWS services and EKS cluster metrics.
	- Why: Use CloudWatch to build alerts, dashboards, and investigate incidents.
	- Example: `aws logs tail /aws/eks/llm-chatbot/gateway --follow` to stream gateway logs.

## CI / Testing

- GitHub Actions
	- What: The hosted CI/CD system that runs workflows defined in `.github/workflows/` on events like `push` or `pull_request`.
	- Why: Automates tests, builds, and reporting so PRs are validated before merging.
	- Example: See `.github/workflows/microservices-unit-tests.yml` for the matrix that runs Python tests per service.

- Workflow file
	- What: A YAML file that describes jobs, steps, environment, and triggers for Actions.
	- Why: It declaratively defines how CI should run and what artifacts to save.
	- Example: `on: [push, pull_request]` and a job named `python-unit-tests` with a `matrix.service`.

- actions/upload-artifact
	- What: Action that saves files produced by a workflow so they can be downloaded from the run page.
	- Why: We use it to store JUnit XML, coverage HTML, and other reports for offline inspection.
	- Example: uploaded artifacts are named like `python-unit-coverage-<service>`.

- dorny/test-reporter
	- What: Action that reads JUnit XML and posts the test summary and annotations to the workflow and PR.
	- Why: Makes failures and flaky tests more visible directly in the GitHub UI.
	- Example: It consumes `reports/*.xml` produced by `pytest --junitxml`.

- pytest
	- What: Python testing framework used to run unit and API tests across microservices.
	- Why: Simple syntax, fixtures, and plugins make test code concise and maintainable.
	- Example: `pytest microservices/conversations-service/tests -q`.

- pytest-cov
	- What: A plugin for `pytest` that measures how much code the tests exercise and creates coverage reports.
	- Why: Coverage helps identify untested code paths and improves confidence in changes.
	- Example: `pytest --cov=app --cov-report=xml:reports/service-coverage.xml --cov-report=html:reports/service-htmlcov`.

- JUnit XML
	- What: A widely-supported XML test-report format used by CI systems to aggregate test results.
	- Why: Enables test-reporting tools to show pass/fail counts and failure traces in the UI.
	- Example: `pytest --junitxml=reports/tests.xml` generates this format.

- Coverage XML / HTML
	- What: Coverage XML (`.xml`) is useful for automated tools; HTML is a human-friendly set of pages with annotated source lines.
	- Why: XML can be consumed by reporting tools; HTML is helpful for manual code-review of untested lines.
	- Example: Download `python-unit-coverage-<service>` from Actions, extract, open `reports/<service>-htmlcov/index.html`.

- Node test runner & JSDOM
	- What: `node --test` runs JavaScript tests in Node; `JSDOM` provides a DOM-like API so browser code can be tested without a real browser.
	- Why: Fast, reproducible frontend tests in CI that validate DOM updates and client-side logic.
	- Example: run `node --test --reporter=json tests/*.test.js` and convert the JSON to JUnit for CI.

## Dev Tools & Misc

- Helm
	- What: A package manager for Kubernetes that packages resources as a chart and manages installs/upgrades.
	- Why: Helm makes deployments repeatable and configurable across environments.
	- Example: `helm upgrade --install llm-chatbot ./infra/helm/chatapp -n chatbot`.

- kubectl
	- What: Kubernetes command-line tool to interact with the cluster (get resources, view logs, exec).
	- Why: Day-to-day operations and debugging use `kubectl`.
	- Example: `kubectl logs deployment/gateway -n chatbot`.

- eksctl cluster.yaml
	- What: The YAML file that specifies the cluster and nodegroups for `eksctl` to create.
	- Why: Keeps cluster config in source control for reproducible infra.
	- Example: `infra/eksctl/cluster.yaml` contains node pool sizes and AMI configuration.

- OpenAI API
	- What: External large-language-model (LLM) API used to generate responses for the AI worker.
	- Why: Provides the model inference without running heavy GPU instances in your cluster.
	- Example: Pods use the `OPENAI_API_KEY` (from Secrets Manager) to call OpenAI endpoints.

## How to use this glossary

- Short answer: start here when you see an unfamiliar name in the docs or CI output.
- Want deeper examples or step-by-step commands for any term? Tell me which entries to expand and I will add 2–4 sentence examples or links to the exact file you should inspect.

---
_Last updated: June 1, 2026_
