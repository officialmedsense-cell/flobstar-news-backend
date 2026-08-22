# Flobstar News Intelligence Backend — Startup Script
# Run this from the backend/ directory

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Flobstar News Intelligence Backend" -ForegroundColor Cyan
Write-Host "  http://localhost:8000" -ForegroundColor Yellow
Write-Host "  Swagger UI: http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Activate virtual environment
$venvActivate = Join-Path $PSScriptRoot "venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    . $venvActivate
    Write-Host "[OK] Virtual environment activated" -ForegroundColor Green
} else {
    Write-Host "[ERROR] venv not found. Run: python -m venv venv && venv\Scripts\pip install -r requirements.txt" -ForegroundColor Red
    exit 1
}

# Check .env exists
$envFile = Join-Path $PSScriptRoot ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "[ERROR] .env file not found. Copy .env.example to .env and fill in credentials." -ForegroundColor Red
    exit 1
}

Write-Host "[OK] .env found" -ForegroundColor Green
Write-Host ""
Write-Host "Starting server..." -ForegroundColor Cyan
Write-Host ""

# Start uvicorn
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
