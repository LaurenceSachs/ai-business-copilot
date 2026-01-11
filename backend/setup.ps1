# AI Business Copilot - Windows Setup Script
# Run this script from PowerShell in the backend directory

param(
    [switch]$SkipVenv,
    [switch]$SkipDeps,
    [switch]$SkipMigrations
)

$ErrorActionPreference = "Stop"

function Write-Success {
    param($Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Write-Info {
    param($Message)
    Write-Host "→ $Message" -ForegroundColor Cyan
}

function Write-Warning {
    param($Message)
    Write-Host "! $Message" -ForegroundColor Yellow
}

function Write-Error {
    param($Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

Write-Host @"
╔════════════════════════════════════════════════════════════╗
║        AI Business Copilot - Windows Setup                 ║
║        Backend Development Environment                      ║
╚════════════════════════════════════════════════════════════╝
"@ -ForegroundColor Cyan

Write-Host ""

# Check if running in backend directory
if (-not (Test-Path "requirements.txt")) {
    Write-Error "requirements.txt not found. Please run this script from the backend directory."
    exit 1
}

# Check Python
Write-Info "Checking Python installation..."
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python (\d+\.\d+)") {
        $version = [version]$matches[1]
        if ($version -ge [version]"3.11") {
            Write-Success "Python $($matches[1]) found"
        } else {
            Write-Error "Python 3.11+ required, found $($matches[1])"
            Write-Warning "Download from: https://www.python.org/downloads/"
            exit 1
        }
    }
} catch {
    Write-Error "Python not found"
    Write-Warning "Please install Python 3.11+ from python.org"
    Write-Warning "Make sure to check 'Add Python to PATH' during installation"
    exit 1
}

# Check pip
Write-Info "Checking pip..."
try {
    $pipVersion = pip --version 2>&1
    Write-Success "pip found"
} catch {
    Write-Error "pip not found"
    exit 1
}

Write-Host ""

# Create virtual environment
if (-not $SkipVenv) {
    Write-Info "Setting up virtual environment..."
    if (Test-Path "venv") {
        Write-Warning "Virtual environment already exists. Skipping creation."
    } else {
        python -m venv venv
        Write-Success "Virtual environment created"
    }
} else {
    Write-Warning "Skipping virtual environment creation (--SkipVenv)"
}

Write-Host ""

# Activate virtual environment
Write-Info "Activating virtual environment..."
$activateScript = ".\venv\Scripts\Activate.ps1"

if (-not (Test-Path $activateScript)) {
    Write-Error "Virtual environment activation script not found"
    Write-Warning "Try running without --SkipVenv"
    exit 1
}

try {
    & $activateScript
    Write-Success "Virtual environment activated"
} catch {
    Write-Error "Failed to activate virtual environment"
    Write-Warning "You may need to run: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser"
    exit 1
}

Write-Host ""

# Upgrade pip
Write-Info "Upgrading pip..."
python -m pip install --upgrade pip --quiet
Write-Success "pip upgraded"

Write-Host ""

# Install dependencies
if (-not $SkipDeps) {
    Write-Info "Installing dependencies (this may take a few minutes)..."
    try {
        pip install -r requirements.txt --quiet
        Write-Success "All dependencies installed"
    } catch {
        Write-Error "Failed to install dependencies"
        Write-Warning "Try running manually: pip install -r requirements.txt"
        exit 1
    }
} else {
    Write-Warning "Skipping dependency installation (--SkipDeps)"
}

Write-Host ""

# Check for .env file
Write-Info "Checking environment configuration..."
if (Test-Path ".env") {
    Write-Success ".env file exists"
} else {
    if (Test-Path ".env.example") {
        Copy-Item .env.example .env
        Write-Success ".env created from example"
        Write-Warning "IMPORTANT: Edit .env with your API credentials before running the app"
    } else {
        Write-Error ".env.example not found"
        exit 1
    }
}

Write-Host ""

# Check PostgreSQL
Write-Info "Checking PostgreSQL..."
$postgresPath = "C:\Program Files\PostgreSQL\15\bin\psql.exe"
if (Test-Path $postgresPath) {
    Write-Success "PostgreSQL found"

    # Check if service is running
    $pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
    if ($pgService -and $pgService.Status -eq "Running") {
        Write-Success "PostgreSQL service is running"
    } else {
        Write-Warning "PostgreSQL service may not be running"
        Write-Info "Start it with: Start-Service postgresql-x64-15"
    }
} else {
    Write-Warning "PostgreSQL not found at default location"
    Write-Info "If installed elsewhere, make sure it's accessible"
}

Write-Host ""

# Check Redis (optional)
Write-Info "Checking Redis (optional for background tasks)..."
try {
    $redisTest = Test-NetConnection -ComputerName localhost -Port 6379 -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
    if ($redisTest.TcpTestSucceeded) {
        Write-Success "Redis is accessible on localhost:6379"
    } else {
        Write-Warning "Redis not found (optional for development)"
        Write-Info "Background tasks will not work without Redis"
    }
} catch {
    Write-Warning "Redis check skipped"
}

Write-Host ""

# Run migrations
if (-not $SkipMigrations) {
    Write-Info "Running database migrations..."
    try {
        alembic upgrade head
        Write-Success "Database migrations completed"
    } catch {
        Write-Error "Database migration failed"
        Write-Warning "Make sure:"
        Write-Warning "  1. PostgreSQL is running"
        Write-Warning "  2. Database credentials in .env are correct"
        Write-Warning "  3. Database 'ai_copilot_dev' exists"
        Write-Warning "  4. pgvector extension is installed"
        Write-Info ""
        Write-Info "To create the database manually, run:"
        Write-Info '  & "C:\Program Files\PostgreSQL\15\bin\psql.exe" -U postgres'
        Write-Info "  Then in psql:"
        Write-Info "    CREATE DATABASE ai_copilot_dev;"
        Write-Info "    CREATE USER dev_user WITH PASSWORD 'dev_password';"
        Write-Info "    GRANT ALL PRIVILEGES ON DATABASE ai_copilot_dev TO dev_user;"
        Write-Info "    \c ai_copilot_dev"
        Write-Info "    CREATE EXTENSION vector;"
        Write-Info "    GRANT ALL ON SCHEMA public TO dev_user;"
        exit 1
    }
} else {
    Write-Warning "Skipping database migrations (--SkipMigrations)"
}

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                    Setup Complete!                         ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

Write-Info "Next steps:"
Write-Host "  1. Edit .env file with your API credentials:" -ForegroundColor White
Write-Host "     notepad .env" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Start the development server:" -ForegroundColor White
Write-Host "     uvicorn app.main:app --reload" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. Open API documentation:" -ForegroundColor White
Write-Host "     http://localhost:8000/docs" -ForegroundColor Gray
Write-Host ""

Write-Info "Documentation:"
Write-Host "  Windows Setup Guide: ..\docs\WINDOWS_SETUP.md" -ForegroundColor Gray
Write-Host "  Quick Start:         ..\docs\QUICKSTART.md" -ForegroundColor Gray
Write-Host "  Implementation:      ..\docs\IMPLEMENTATION_SUMMARY.md" -ForegroundColor Gray
Write-Host ""

Write-Info "Useful commands:"
Write-Host "  Activate venv:  .\venv\Scripts\Activate.ps1" -ForegroundColor Gray
Write-Host "  Run tests:      pytest" -ForegroundColor Gray
Write-Host "  Check style:    black app/" -ForegroundColor Gray
Write-Host ""
