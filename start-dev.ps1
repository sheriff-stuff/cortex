# start-dev.ps1 — Install dependencies and start Ollama for development
# Run the backend and frontend separately in their own terminals:
#   Backend:  $env:PYTHONUTF8="1"; meeting-notes serve --reload
#   Frontend: cd frontend; npm run dev
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# --- Install dependencies ---
Write-Host "[setup] " -NoNewline -ForegroundColor Green
Write-Host "Installing backend dependencies..."
python -m pip install -e ".[api]" --quiet
if ($LASTEXITCODE -ne 0) { throw "Failed to install backend dependencies" }

Write-Host "[setup] " -NoNewline -ForegroundColor Green
Write-Host "Installing frontend dependencies..."
Push-Location frontend
npm install --silent
Pop-Location

# --- Run database migration ---
Write-Host "[setup] " -NoNewline -ForegroundColor Green
Write-Host "Running database migration..."
$env:PYTHONUTF8 = "1"
python -X utf8 migration/migrate.py

# --- Start Ollama ---
if (Get-Command ollama -ErrorAction SilentlyContinue) {
    try {
        Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 2 | Out-Null
        Write-Host "[ollama] " -NoNewline -ForegroundColor Blue
        Write-Host "Already running"
    } catch {
        Write-Host "[ollama] " -NoNewline -ForegroundColor Blue
        Write-Host "Starting Ollama..."
        Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
        for ($i = 0; $i -lt 15; $i++) {
            try {
                Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 2 | Out-Null
                Write-Host "[ollama] " -NoNewline -ForegroundColor Blue
                Write-Host "Ready!"
                break
            } catch { Start-Sleep 1 }
        }
    }
} else {
    Write-Host "[ollama] " -NoNewline -ForegroundColor Red
    Write-Host "WARNING: Ollama not found. LLM extraction will not work."
    Write-Host "[ollama] " -NoNewline -ForegroundColor Red
    Write-Host "Install from https://ollama.ai"
}

Write-Host ""
Write-Host "========================================"
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "  Start the backend and frontend in separate terminals:"
Write-Host ""
Write-Host '  Backend:  $env:PYTHONUTF8="1"; meeting-notes serve --reload' -ForegroundColor Cyan
Write-Host "  Frontend: cd frontend; npm run dev" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Backend:  http://127.0.0.1:9000"
Write-Host "  Frontend: http://localhost:5173"
Write-Host "========================================"
