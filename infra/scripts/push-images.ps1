param(
  [string] $RepoPrefix = ("537053564195.dkr.ecr.ap-south-1.amazonaws.com/ott-npe"),
  [string] $Tag = ("V1.0.0"),
  [string] $AwsRegion = ("ap-south-1")
)

Write-Host "Using RepoPrefix=$RepoPrefix Tag=$Tag AwsRegion=$AwsRegion"

$registry = $RepoPrefix.Split('/')[0]
$repoNamespace = $RepoPrefix.Split('/')[1]

Write-Host "Logging in to ECR registry: $registry"
aws ecr get-login-password --region $AwsRegion | docker login --username AWS --password-stdin $registry

$services = @('frontend','gateway','settings-service','conversations-service','messages-service','ai-service')

foreach ($svc in $services) {
  Write-Host "`n--- Building and pushing: $svc ---"
  switch ($svc) {
    'frontend' { $ctx = '.\\microservices\\frontend' }
    'gateway' { $ctx = '.\\microservices\\gateway' }
    'settings-service' { $ctx = '.\\microservices\\settings-service' }
    'conversations-service' { $ctx = '.\\microservices\\conversations-service' }
    'messages-service' { $ctx = '.\\microservices\\messages-service' }
    'ai-service' { $ctx = '.\\microservices\\ai-service' }
    default { throw "Unknown service: $svc" }
  }

  $imageLocal = "$svc:latest"
  $imageRemote = "$RepoPrefix/$svc:$Tag"

  Write-Host "Building $imageLocal from $ctx"
  docker build -t $imageLocal $ctx

  Write-Host "Tagging $imageRemote"
  docker tag $imageLocal $imageRemote

  $repoName = "$repoNamespace/$svc"
  try {
    aws ecr create-repository --repository-name $repoName --region $AwsRegion | Out-Null
  } catch {
    # ignore if already exists
  }

  Write-Host "Pushing $imageRemote"
  docker push $imageRemote
}

Write-Host "`nAll images pushed successfully."
