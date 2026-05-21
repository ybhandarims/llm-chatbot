#!/usr/bin/env bash
set -euo pipefail

# Default values (override via env)
REPO_PREFIX="${REPO_PREFIX:-537053564195.dkr.ecr.ap-south-1.amazonaws.com/ott-npe}"
TAG="${TAG:-V1.0.0}"
AWS_REGION="${AWS_REGION:-ap-south-1}"

echo "Using REPO_PREFIX=${REPO_PREFIX} TAG=${TAG} AWS_REGION=${AWS_REGION}"

registry="${REPO_PREFIX%%/*}"
repo_namespace="${REPO_PREFIX#*/}"

echo "Logging in to ECR registry: ${registry}"
aws ecr get-login-password --region "${AWS_REGION}" | docker login --username AWS --password-stdin "${registry}"

SERVICES=(frontend gateway settings-service conversations-service messages-service ai-service)

for svc in "${SERVICES[@]}"; do
  echo "\n--- Building and pushing: ${svc} ---"
  case "$svc" in
    frontend) ctx="./microservices/frontend" ;;
    gateway) ctx="./microservices/gateway" ;;
    settings-service) ctx="./microservices/settings-service" ;;
    conversations-service) ctx="./microservices/conversations-service" ;;
    messages-service) ctx="./microservices/messages-service" ;;
    ai-service) ctx="./microservices/ai-service" ;;
    *) echo "Unknown service: $svc"; exit 1 ;;
  esac

  image_local="${svc}:latest"
  image_remote="${REPO_PREFIX}/${svc}:${TAG}"

  echo "Building ${image_local} from ${ctx}"
  docker build -t "${image_local}" "${ctx}"

  echo "Tagging ${image_remote}"
  docker tag "${image_local}" "${image_remote}"

  # ensure repository exists (namespace/repo)
  repo_name="${repo_namespace}/${svc}"
  aws ecr create-repository --repository-name "$repo_name" --region "${AWS_REGION}" >/dev/null 2>&1 || true

  echo "Pushing ${image_remote}"
  docker push "${image_remote}"
done

echo "\nAll images pushed successfully."
