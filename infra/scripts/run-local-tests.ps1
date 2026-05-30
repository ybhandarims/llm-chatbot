<#
.SYNOPSIS
  Run all local tests and save reports to infra/artifacts.

.DESCRIPTION
  Runs pytest for each Python microservice and Node JSDOM tests for the frontend.
  Outputs JUnit XML for Python and a JSON+converted JUnit XML for frontend tests.

.EXAMPLE
  .\run-local-tests.ps1

#>

param(
    [switch]$FailOnError = $true
)

Set-Location -Path $PSScriptRoot\..\..

$artifacts = Join-Path -Path (Get-Location) -ChildPath "infra\artifacts"
if (-not (Test-Path $artifacts)) { New-Item -ItemType Directory -Path $artifacts -Force | Out-Null }

function Run-Pytest($path, $outFile) {
    Write-Host "Running pytest: $path -> $outFile"
    & python -m pytest $path -q --junitxml=$outFile
    return $LASTEXITCODE
}

$errors = @()

$errors += (Run-Pytest "microservices/ai-service/tests" "$artifacts/ai-service-unit.xml")
$errors += (Run-Pytest "microservices/gateway/tests" "$artifacts/gateway-unit.xml")
$errors += (Run-Pytest "microservices/conversations-service/tests" "$artifacts/conversations-unit.xml")
$errors += (Run-Pytest "microservices/messages-service/tests" "$artifacts/messages-unit.xml")
$errors += (Run-Pytest "microservices/settings-service/tests" "$artifacts/settings-unit.xml")

Write-Host "Running frontend tests (Node/JSDOM)"
Push-Location microservices\frontend
try {
    if (-not (Test-Path node_modules)) { npm ci --no-audit --no-fund }
    $jsonOut = Join-Path $artifacts "frontend-tests.json"
    $xmlOut = Join-Path $artifacts "frontend-tests.xml"
    if (Test-Path $jsonOut) { Remove-Item $jsonOut -Force }
    Write-Host "Running: node --test --test-reporter=json tests/*.test.js -> $jsonOut"
    & node --test --test-reporter=json --test-reporter-destination=$jsonOut tests/*.test.js
    $nodeExit = $LASTEXITCODE
    if ($nodeExit -ne 0) { $errors += $nodeExit }
    if (-not (Test-Path $jsonOut) -or (Get-Item $jsonOut).Length -eq 0) {
      throw 'frontend JSON report was not generated'
    }
    # Convert JSON -> JUnit XML
    & node tools/json-to-junit.js $jsonOut $xmlOut
    if ($LASTEXITCODE -ne 0) { $errors += $LASTEXITCODE }
} finally {
    Pop-Location
}

if ($errors -contains 1 -or ($errors | Where-Object { $_ -ne 0 -and $_ -ne $null }).Count -gt 0) {
    Write-Host "Some tests failed. Check files in infra\artifacts for details." -ForegroundColor Yellow
    if ($FailOnError) { exit 1 } else { exit 0 }
}

Write-Host "All tests completed. Reports are in infra\artifacts" -ForegroundColor Green
exit 0
