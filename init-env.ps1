#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

Write-Host "=== init-env: setting up Python environment ===" -ForegroundColor Cyan
Write-Host ""

# --- .env provisioning ---
if (Test-Path ".env" -PathType Leaf) {
    Write-Host "[.env] .env already exists — skipping." -ForegroundColor Yellow
} elseif (Test-Path ".git" -PathType Leaf) {
    # Worktree: .git is a file containing "gitdir: <path>"
    $gitContent = (Get-Content ".git" -Raw).Trim()
    if ($gitContent -match '^gitdir:\s*(.+)$') {
        $gitdirValue = $Matches[1].Trim()
        # Root is everything before the first /.git/ segment
        $root = $gitdirValue -replace '/\.git/.+$', ''
        $rootEnv = Join-Path $root ".env"
        if (Test-Path $rootEnv -PathType Leaf) {
            Write-Host "[.env] Copying .env from main worktree root: $root" -ForegroundColor Green
            Copy-Item $rootEnv ".env"
        } else {
            if (Test-Path ".env.example" -PathType Leaf) {
                Write-Host "[.env] No .env in root — copying .env.example" -ForegroundColor Green
                Copy-Item ".env.example" ".env"
            } else {
                Write-Host "[.env] Warning: no .env.example found. Skipping." -ForegroundColor Yellow
            }
        }
    } else {
        Write-Host "[.env] Unexpected .git file format — copying .env.example" -ForegroundColor Yellow
        Copy-Item ".env.example" ".env"
    }
} else {
    # Normal clone: .git is a directory
    if (Test-Path ".env.example" -PathType Leaf) {
        Write-Host "[.env] Copying .env.example -> .env" -ForegroundColor Green
        Copy-Item ".env.example" ".env"
    } else {
        Write-Host "[.env] Warning: no .env.example found. Skipping." -ForegroundColor Yellow
    }
}
Write-Host ""

# --- Python venv ---
$python = $null
foreach ($candidate in @("python3", "python")) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) {
        $python = $candidate
        break
    }
}
if (-not $python) {
    Write-Error "python3 or python not found. Please install Python 3."
    exit 1
}

if (-not (Test-Path ".venv" -PathType Container)) {
    Write-Host "[venv] Creating .venv with $python..." -ForegroundColor Cyan
    & $python -m venv .venv
} else {
    Write-Host "[venv] .venv already exists — skipping creation." -ForegroundColor Yellow
}
Write-Host ""

# --- Activate ---
Write-Host "[venv] Activating .venv..." -ForegroundColor Cyan
. .\.venv\Scripts\Activate.ps1
Write-Host ""

# --- Upgrade pip ---
Write-Host "[pip] Upgrading pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip
Write-Host ""

# --- Install requirements ---
Write-Host "[pip] Installing requirements..." -ForegroundColor Cyan
pip install -r requirements.txt
Write-Host ""

Write-Host "=== Done! ===" -ForegroundColor Green
Write-Host ""
Write-Host "To activate the virtual environment in a new PowerShell session:" -ForegroundColor White
Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor White
