Set-Location (Split-Path $PSScriptRoot)
docker compose up -d --build
Write-Host "Kanban Studio running at http://localhost:8000"
