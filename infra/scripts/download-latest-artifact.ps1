<#
.SYNOPSIS
  Download the latest GitHub Actions artifact from a workflow run using the GitHub CLI (`gh`).

.DESCRIPTION
  This script finds the most recent run for the specified workflow and downloads the requested artifact.
  It requires the `gh` CLI to be installed and authenticated (run `gh auth login` first).

.PARAMETER Workflow
  The workflow filename or workflow name to search for (default: microservices-unit-tests.yml).

.PARAMETER ArtifactName
  The name of the artifact to download. If omitted, all artifacts for the run will be downloaded.

.PARAMETER OutputDir
  Directory to save downloaded artifacts (default: ./infra/artifacts).

.PARAMETER All
  If set, download all artifacts for the latest run.

.EXAMPLE
  .\download-latest-artifact.ps1 -Workflow microservices-unit-tests.yml -ArtifactName "frontend-test-report" -OutputDir .\infra\artifacts

  Downloads the `frontend-test-report` artifact from the latest run of `microservices-unit-tests.yml`.
#>

param(
    [string]$Workflow = "microservices-unit-tests.yml",
    [string]$ArtifactName = "",
    [string]$OutputDir = ".\infra\artifacts",
    [switch]$All
)

function Write-ErrorAndExit($msg) {
    Write-Host "ERROR: $msg" -ForegroundColor Red
    exit 1
}

# Ensure gh is available
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-ErrorAndExit "GitHub CLI 'gh' not found. Install from https://cli.github.com/ and run 'gh auth login' to authenticate."
}

# Ensure output directory exists
if (-not (Test-Path -Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

Write-Host "Searching for latest workflow run for: $Workflow"

# Try to get the latest run for the workflow; fall back to any recent run if workflow filter fails
$runList = & gh run list --workflow $Workflow --limit 1 2>&1
if (-not $runList -or $runList -match "No workflow runs found") {
    Write-Host "No runs found for workflow '$Workflow'. Falling back to most recent run overall."
    $runList = & gh run list --limit 1 2>&1
}

$firstLine = $runList | Where-Object { $_ -and ($_ -match '\S') } | Select-Object -First 1
if (-not $firstLine) {
    Write-ErrorAndExit "Couldn't find any workflow runs. Ensure you're in the correct repo and `gh` is authenticated."
}

# The run list output is like: "123456789 workflow-name branch 2 days ago"
$runId = ($firstLine -split '\s+')[0]
if (-not $runId -or -not ($runId -match '^[0-9]+$')) {
    Write-ErrorAndExit "Unable to parse run id from: $firstLine"
}

Write-Host "Found run id: $runId"

if ($ArtifactName -and -not $All.IsPresent) {
    Write-Host "Downloading artifact '$ArtifactName' into $OutputDir"
    & gh run download $runId --name "$ArtifactName" --dir $OutputDir
    if ($LASTEXITCODE -ne 0) { Write-ErrorAndExit "Failed to download artifact '$ArtifactName' from run $runId" }
    Write-Host "Downloaded artifact '$ArtifactName' to: $OutputDir"
} else {
    Write-Host "Downloading all artifacts for run $runId into $OutputDir"
    & gh run download $runId --dir $OutputDir
    if ($LASTEXITCODE -ne 0) { Write-ErrorAndExit "Failed to download artifacts for run $runId" }
    Write-Host "Downloaded artifacts to: $OutputDir"
}

Write-Host "Done. Open the output directory to inspect artifacts."
