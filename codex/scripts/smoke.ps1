$ErrorActionPreference = "Stop"

Invoke-WebRequest -UseBasicParsing http://localhost:8000/health | Out-Null
Write-Host "Health OK"

$metrics = Invoke-WebRequest -UseBasicParsing http://localhost:8000/metrics
if ($metrics.Content -notmatch "HELP" -or $metrics.Content -notmatch "TYPE") {
  throw "Metrics format invalid"
}
Write-Host "Metrics OK"
