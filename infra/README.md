 # EKS Deployment (step-by-step runbook)

 This folder contains the EKS and Helm assets for the microservices chat app.

 Quick links:
 - Chart values: [infra/helm/chatapp/values.yaml](infra/helm/chatapp/values.yaml)
 - Cluster config: [infra/eksctl/cluster.yaml](infra/eksctl/cluster.yaml)

 **Prerequisites**
 - AWS CLI configured and authenticated for your account
 - `eksctl`, `kubectl`, `helm`, `docker` installed locally
 - `jq` (optional, used for extracting JSON fields in scripts)
 - An ECR repository per image (or a single repo with multiple image names/tags)
 - Permission to create IAM roles and policies for the AWS Load Balancer Controller

 The steps below assume you will run commands from the repository root (where this file lives). Replace `<region>`, `<account>`, and repository names to match your environment.

 1) Configure environment variables

 PowerShell (Windows):

 ```powershell
 $Env:AWS_REGION = 'us-east-1'
 $Env:AWS_ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text)
 $Env:REPO_PREFIX = "$Env:AWS_ACCOUNT_ID.dkr.ecr.$Env:AWS_REGION.amazonaws.com/chatapp"
 $Env:OPENAI_API_KEY = Read-Host -AsSecureString "Enter OPENAI API key" | ConvertFrom-SecureString
 ```

 Bash (Linux / macOS):

 ```bash
 export AWS_REGION=us-east-1
 export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
 export REPO_PREFIX=${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/chatapp
 read -s -p "Enter OPENAI API key: " OPENAI_API_KEY; echo
 ```

 2) Create ECR repositories (one-time)

 Replace `service-name` with each service: `frontend`, `gateway`, `settings`, `conversations`, `messages`, `ai`.

 ```bash
 for svc in frontend gateway settings conversations messages ai; do
   aws ecr create-repository --repository-name chatapp/$svc || true
 done
 ```

 3) Build, tag and push Docker images

 Example for a single service (run from repo root). Repeat for each service or script it.

 PowerShell:

 ```powershell
 docker build -t gateway:latest .\microservices\gateway
 docker tag gateway:latest $Env:REPO_PREFIX/gateway:latest
 aws ecr get-login-password --region $Env:AWS_REGION | docker login --username AWS --password-stdin $Env:AWS_ACCOUNT_ID.dkr.ecr.$Env:AWS_REGION.amazonaws.com
 docker push $Env:REPO_PREFIX/gateway:latest
 ```

 Bash:

 ```bash
 docker build -t gateway:latest ./microservices/gateway
 docker tag gateway:latest ${REPO_PREFIX}/gateway:latest
 aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com
 docker push ${REPO_PREFIX}/gateway:latest
 ```

 Repeat for `frontend`, `settings`, `conversations`, `messages`, `ai` (change build context and final image names).

 4) (Optional) Update `infra/helm/chatapp/values.yaml`

 Edit [infra/helm/chatapp/values.yaml](infra/helm/chatapp/values.yaml) and set each service image repository and tag to the pushed ECR locations, for example:

 ```yaml
 images:
   gateway:
     repository: "<ACCOUNT>.dkr.ecr.<REGION>.amazonaws.com/chatapp/gateway"
     tag: "latest"
   frontend:
     repository: "<ACCOUNT>.dkr.ecr.<REGION>.amazonaws.com/chatapp/frontend"
     tag: "latest"
 # ... repeat for other services
 ```

 You can also override image repos/tags at deploy time with `--set` (examples below).

 5) Create the EKS cluster (eksctl)

 ```bash
 eksctl create cluster -f infra/eksctl/cluster.yaml
 aws eks update-kubeconfig --name chatapp-eks --region ${AWS_REGION}
 ```

 6) Install AWS Load Balancer Controller (ALB)

 Follow AWS docs to create the IAM policy used by the controller. Then create an IAM service account and install the chart. Skeleton commands:

 ```bash
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

