# Windows Setup Guide - AI Business Copilot

This guide is specifically for setting up the development environment on Windows.

## Step 1: Install Python 3.11+

### Option A: Download from Python.org (Recommended)
1. Go to https://www.python.org/downloads/
2. Download Python 3.11 or later (3.11.x or 3.12.x)
3. **IMPORTANT**: During installation, check "Add Python to PATH"
4. Click "Install Now"

### Option B: Using Windows Package Manager (winget)
```powershell
winget install Python.Python.3.11
```

### Verify Installation
Open a NEW PowerShell window and run:
```powershell
python --version
# Should show: Python 3.11.x or 3.12.x

pip --version
# Should show: pip 23.x or later
```

If these commands don't work, restart your computer and try again.

## Step 2: Install PostgreSQL with pgvector

### Install PostgreSQL
1. Download PostgreSQL 15 from: https://www.postgresql.org/download/windows/
2. Run the installer
3. Remember the password you set for the `postgres` user
4. Default port: 5432 (keep this unless you have conflicts)

### Install pgvector Extension
1. Download pgvector for Windows from: https://github.com/pgvector/pgvector/releases
2. Look for `pgvector-v0.5.1-windows-x64.zip` or similar
3. Extract the files
4. Copy the files to your PostgreSQL installation:
   - Copy `vector.dll` to `C:\Program Files\PostgreSQL\15\lib\`
   - Copy `vector.control` and `vector--*.sql` to `C:\Program Files\PostgreSQL\15\share\extension\`

### Create Database
Open PowerShell and run:
```powershell
# Connect to PostgreSQL (will prompt for password)
& "C:\Program Files\PostgreSQL\15\bin\psql.exe" -U postgres

# In the psql prompt, run:
# CREATE DATABASE ai_copilot_dev;
# CREATE USER dev_user WITH PASSWORD 'dev_password';
# GRANT ALL PRIVILEGES ON DATABASE ai_copilot_dev TO dev_user;
# \c ai_copilot_dev
# CREATE EXTENSION vector;
# GRANT ALL ON SCHEMA public TO dev_user;
# \q
```

Or save this to a file `setup_db.sql` and run:
```powershell
@"
CREATE DATABASE ai_copilot_dev;
CREATE USER dev_user WITH PASSWORD 'dev_password';
GRANT ALL PRIVILEGES ON DATABASE ai_copilot_dev TO dev_user;
\c ai_copilot_dev
CREATE EXTENSION vector;
GRANT ALL ON SCHEMA public TO dev_user;
"@ | Out-File -FilePath setup_db.sql -Encoding utf8

& "C:\Program Files\PostgreSQL\15\bin\psql.exe" -U postgres -f setup_db.sql
```

## Step 3: Install Redis (Optional for Development)

### Option A: Using WSL2 (Recommended)
1. Enable WSL2: https://learn.microsoft.com/en-us/windows/wsl/install
2. Install Ubuntu from Microsoft Store
3. In WSL2 Ubuntu terminal:
   ```bash
   sudo apt update
   sudo apt install redis-server
   redis-server --daemonize yes
   ```

### Option B: Memurai (Redis Alternative for Windows)
1. Download from: https://www.memurai.com/
2. Install and start the service
3. Use connection string: `redis://localhost:6379/0`

### Option C: Skip Redis for Now
Redis is only needed for background tasks (Celery). You can skip it initially and run without background indexing.

## Step 4: Setup Backend

Open PowerShell in the project directory:

```powershell
cd C:\Users\LaurenceSachs\dev\ai-business-copilot\backend

# Create virtual environment
python -m venv venv

# Activate virtual environment (WINDOWS COMMAND)
.\venv\Scripts\Activate.ps1

# If you get execution policy error, run this first:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

## Step 5: Configure Environment

```powershell
# Copy example environment file
Copy-Item .env.example .env

# Edit with Notepad or your preferred editor
notepad .env
```

Update these critical settings in `.env`:

```env
# Database - use localhost on Windows
DATABASE_URL=postgresql://dev_user:dev_password@localhost:5432/ai_copilot_dev

# Redis - if using WSL2, use localhost; if not using Redis, comment out
REDIS_URL=redis://localhost:6379/0

# Windows-specific: Use absolute paths if needed
# LOG_PATH=C:\Users\LaurenceSachs\dev\ai-business-copilot\logs
```

## Step 6: Run Database Migrations

With virtual environment still activated:

```powershell
# Make sure you're in the backend directory
cd C:\Users\LaurenceSachs\dev\ai-business-copilot\backend

# Activate venv if not already active
.\venv\Scripts\Activate.ps1

# Run migrations
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 001, Initial database schema with pgvector support
```

## Step 7: Start Development Server

```powershell
# With virtual environment activated
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Application startup complete.
```

## Step 8: Test the Installation

Open a web browser and go to:
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

Or use PowerShell:
```powershell
Invoke-WebRequest -Uri http://localhost:8000/health | Select-Object -Expand Content
```

Should return: `{"status":"healthy"}`

## Common Windows Issues

### Issue 1: "Python was not found"
**Solution:**
1. Install Python from python.org
2. Make sure "Add to PATH" was checked during installation
3. Restart PowerShell/computer
4. If still not working, manually add Python to PATH:
   - Search "Environment Variables" in Windows
   - Edit System PATH
   - Add: `C:\Users\YourUsername\AppData\Local\Programs\Python\Python311`
   - Add: `C:\Users\YourUsername\AppData\Local\Programs\Python\Python311\Scripts`

### Issue 2: "Activate.ps1 cannot be loaded" / Execution Policy Error
**Solution:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then try activating venv again:
```powershell
.\venv\Scripts\Activate.ps1
```

### Issue 3: PostgreSQL Connection Failed
**Solution:**
1. Check if PostgreSQL is running:
   ```powershell
   Get-Service -Name postgresql*
   ```
2. If not running:
   ```powershell
   Start-Service postgresql-x64-15
   ```
3. Verify connection:
   ```powershell
   & "C:\Program Files\PostgreSQL\15\bin\psql.exe" -U dev_user -d ai_copilot_dev -h localhost
   ```

### Issue 4: pgvector Extension Error
**Solution:**
1. Download correct pgvector version for PostgreSQL 15
2. Make sure files are in correct directories
3. Restart PostgreSQL service:
   ```powershell
   Restart-Service postgresql-x64-15
   ```

### Issue 5: Module Import Errors
**Solution:**
Make sure you're:
1. In the `backend` directory
2. Virtual environment is activated (you should see `(venv)` in your prompt)
3. All dependencies are installed: `pip install -r requirements.txt`

## Complete Setup Script

Save this as `setup.ps1` in the `backend` directory:

```powershell
# AI Business Copilot - Windows Setup Script

Write-Host "Starting setup..." -ForegroundColor Green

# Check Python
Write-Host "Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version
    Write-Host "✓ Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python not found. Please install Python 3.11+ from python.org" -ForegroundColor Red
    exit 1
}

# Create virtual environment
Write-Host "`nCreating virtual environment..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "✓ Virtual environment already exists" -ForegroundColor Green
} else {
    python -m venv venv
    Write-Host "✓ Virtual environment created" -ForegroundColor Green
}

# Activate virtual environment
Write-Host "`nActivating virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

# Upgrade pip
Write-Host "`nUpgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Install dependencies
Write-Host "`nInstalling dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

# Copy .env if not exists
Write-Host "`nSetting up environment file..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host "✓ .env already exists" -ForegroundColor Green
} else {
    Copy-Item .env.example .env
    Write-Host "✓ .env created from example" -ForegroundColor Green
    Write-Host "  → Please edit .env with your API credentials" -ForegroundColor Yellow
}

# Run migrations
Write-Host "`nRunning database migrations..." -ForegroundColor Yellow
try {
    alembic upgrade head
    Write-Host "✓ Database migrations complete" -ForegroundColor Green
} catch {
    Write-Host "✗ Migration failed. Make sure PostgreSQL is running and .env is configured" -ForegroundColor Red
}

Write-Host "`nSetup complete!" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "1. Edit .env file with your API credentials"
Write-Host "2. Make sure PostgreSQL is running"
Write-Host "3. Run: uvicorn app.main:app --reload"
Write-Host "`nDocumentation: ../docs/WINDOWS_SETUP.md" -ForegroundColor Cyan
```

Run it with:
```powershell
cd C:\Users\LaurenceSachs\dev\ai-business-copilot\backend
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\setup.ps1
```

## Development Workflow (Windows)

### Starting Development

1. Open PowerShell in `backend` directory
2. Activate virtual environment:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
3. Start server:
   ```powershell
   uvicorn app.main:app --reload
   ```

### Stopping

Press `Ctrl+C` in the PowerShell window

### Running Tests

```powershell
.\venv\Scripts\Activate.ps1
pytest
```

### Checking Code Quality

```powershell
.\venv\Scripts\Activate.ps1
black app/
flake8 app/
```

## Alternative: Using Docker on Windows

If you prefer not to install PostgreSQL and Redis directly, you can use Docker Desktop:

1. Install Docker Desktop for Windows
2. Create `docker-compose.yml` in the backend directory:

```yaml
version: '3.8'
services:
  postgres:
    image: ankane/pgvector:latest
    environment:
      POSTGRES_DB: ai_copilot_dev
      POSTGRES_USER: dev_user
      POSTGRES_PASSWORD: dev_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

3. Start services:
   ```powershell
   docker-compose up -d
   ```

4. Your backend can now connect to `localhost:5432` and `localhost:6379`

## Next Steps

Once the backend is running:

1. Test the API at http://localhost:8000/docs
2. Get API credentials for all integrated services
3. Update `.env` with real credentials
4. Test indexing with: `python -c "from app.services.indexing_service import IndexingService; print('OK')"`
5. Build the React frontend (separate guide)

## Getting Help

- Check PowerShell command history: `Get-History`
- View Python package versions: `pip list`
- Check if services are running: `Get-Service | Where-Object {$_.Name -like "*postgres*"}`
- Test database connection: `& "C:\Program Files\PostgreSQL\15\bin\psql.exe" -U dev_user -d ai_copilot_dev`

For more detailed information, see:
- [QUICKSTART.md](QUICKSTART.md) - General development guide
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Production deployment
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - Architecture details
