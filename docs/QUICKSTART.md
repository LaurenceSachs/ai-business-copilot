# Quick Start Guide - Development Environment

This guide gets you up and running with the AI Business Copilot in a local development environment.

## Prerequisites

- Python 3.11+
- PostgreSQL 15+ with pgvector
- Redis
- Node.js 18+ (for frontend, when built)
- Git

## 1. Install PostgreSQL with pgvector

### macOS (using Homebrew)
```bash
brew install postgresql@15
brew install pgvector

# Start PostgreSQL
brew services start postgresql@15
```

### Ubuntu/Debian
```bash
sudo apt update
sudo apt install postgresql-15 postgresql-15-pgvector
sudo systemctl start postgresql
```

### Windows
1. Download PostgreSQL 15 from [postgresql.org](https://www.postgresql.org/download/windows/)
2. Install pgvector from [pgvector releases](https://github.com/pgvector/pgvector/releases)

## 2. Create Database

```bash
# Connect to PostgreSQL
psql -U postgres

# In psql shell:
CREATE DATABASE ai_copilot_dev;
CREATE USER dev_user WITH PASSWORD 'dev_password';
GRANT ALL PRIVILEGES ON DATABASE ai_copilot_dev TO dev_user;

\c ai_copilot_dev
CREATE EXTENSION vector;
GRANT ALL ON SCHEMA public TO dev_user;

\q
```

## 3. Install Redis

### macOS
```bash
brew install redis
brew services start redis
```

### Ubuntu/Debian
```bash
sudo apt install redis-server
sudo systemctl start redis
```

### Windows
Download from [Redis releases](https://github.com/microsoftarchive/redis/releases) or use WSL2.

## 4. Setup Backend

```bash
cd backend

# Create virtual environment
python3.11 -m venv venv

# Activate (macOS/Linux)
source venv/bin/activate

# Activate (Windows)
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## 5. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

**Minimum required for development:**

```env
# Application
APP_NAME=AI Business Copilot
ENVIRONMENT=development
DEBUG=True
SECRET_KEY=dev-secret-key-change-in-production
API_V1_PREFIX=/api/v1

# Database
DATABASE_URL=postgresql://dev_user:dev_password@localhost:5432/ai_copilot_dev
DB_ECHO=True

# Anthropic Claude API (REQUIRED - get from https://console.anthropic.com)
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
CLAUDE_MODEL=claude-sonnet-4-5-20250929
MAX_TOKENS=4096

# Microsoft Entra ID (REQUIRED for auth)
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=your-tenant-id
AZURE_REDIRECT_URI=http://localhost:8000/api/v1/auth/callback

# Other integrations (optional for initial testing)
DROPBOX_APP_KEY=optional-for-dev
DROPBOX_APP_SECRET=optional-for-dev
DROPBOX_REFRESH_TOKEN=optional-for-dev

# ... (other services optional for basic testing)

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
JWT_SECRET_KEY=dev-jwt-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Indexing
INDEX_BATCH_SIZE=100
INDEX_SCHEDULE_CRON=0 2 * * 0
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Logging
LOG_LEVEL=DEBUG
LOG_FORMAT=json
```

## 6. Run Database Migrations

```bash
# Make sure you're in the backend directory with venv activated
alembic upgrade head
```

You should see output like:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 001, Initial database schema with pgvector support
```

## 7. Create Test Admin User (Optional)

```bash
python3 <<'EOF'
from app.db.base import SessionLocal
from app.models.user import User
from datetime import datetime

db = SessionLocal()

# Create a test admin user
# Note: In production, this would be created via Azure AD login
test_user = User(
    email="admin@test.com",
    full_name="Test Admin",
    azure_id="test-azure-id-123",
    azure_tenant_id="test-tenant-id",
    is_active=True,
    is_admin=True,
    roles=["admin"],
    created_at=datetime.utcnow(),
    updated_at=datetime.utcnow()
)

db.add(test_user)
db.commit()
print(f"✓ Test admin user created: {test_user.email}")
db.close()
EOF
```

## 8. Start Development Server

```bash
# Make sure you're in backend directory
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

## 9. Test the API

### Check Health
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status":"healthy"}
```

### View API Documentation
Open your browser and navigate to:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 10. Test Basic Functionality

### Test Embedding Service
```bash
python3 <<'EOF'
from app.services.embedding_service import embedding_service

# Generate a test embedding
text = "This is a test document about business operations"
embedding = embedding_service.generate_embedding(text)

print(f"✓ Generated embedding with {len(embedding)} dimensions")
print(f"  First 5 values: {embedding[:5]}")
EOF
```

### Test Database Connection
```bash
python3 <<'EOF'
from app.db.base import SessionLocal
from app.models.document import Document, DocumentSource
from datetime import datetime

db = SessionLocal()

# Create a test document
test_doc = Document(
    source=DocumentSource.DROPBOX,
    source_id="test-123",
    title="Test Document",
    content="This is a test document for development",
    embedding=[0.1] * 384,  # Dummy embedding
    indexed_at=datetime.utcnow()
)

db.add(test_doc)
db.commit()
print(f"✓ Test document created with ID: {test_doc.id}")

# Query it back
found = db.query(Document).filter(Document.source_id == "test-123").first()
print(f"✓ Document retrieved: {found.title}")

db.close()
EOF
```

## 11. Start Celery Worker (Optional for Background Tasks)

In a new terminal:

```bash
cd backend
source venv/bin/activate  # or .\venv\Scripts\activate on Windows

# Start Celery worker
celery -A app.tasks worker --loglevel=info
```

## 12. Start Celery Beat (Optional for Scheduled Tasks)

In another new terminal:

```bash
cd backend
source venv/bin/activate

# Start Celery beat scheduler
celery -A app.tasks beat --loglevel=info
```

## Common Development Tasks

### Run Tests
```bash
cd backend
pytest
```

### Check Code Style
```bash
black app/
flake8 app/
mypy app/
```

### Generate New Migration
```bash
alembic revision --autogenerate -m "description of changes"
```

### Reset Database
```bash
# WARNING: This deletes all data
alembic downgrade base
alembic upgrade head
```

### View Logs
```bash
# All logs go to stdout in development mode
# Check the terminal where uvicorn is running
```

### Test Authentication Flow
Since you need Azure AD setup, you can temporarily bypass auth for testing:

1. Comment out the `Depends(get_current_user)` in API endpoints
2. Or create a mock user in the request
3. Or complete Azure AD app registration (see DEPLOYMENT_GUIDE.md)

### Manual Indexing Test

```bash
python3 <<'EOF'
from app.db.base import SessionLocal
from app.services.indexing_service import IndexingService

db = SessionLocal()
indexing_service = IndexingService(db)

# This will attempt to index from configured sources
# Make sure you have valid API credentials in .env
try:
    results = indexing_service.index_hubspot_contacts()
    print(f"✓ Indexed {results} HubSpot contacts")
except Exception as e:
    print(f"⚠ Error (expected if credentials not configured): {e}")

db.close()
EOF
```

## Troubleshooting

### Database Connection Error
```
sqlalchemy.exc.OperationalError: could not connect to server
```
**Solution:** Make sure PostgreSQL is running and credentials in `.env` are correct.

### pgvector Extension Not Found
```
ERROR: extension "vector" does not exist
```
**Solution:** Install pgvector extension (see step 1) and run `CREATE EXTENSION vector;`

### Import Errors
```
ModuleNotFoundError: No module named 'app'
```
**Solution:** Make sure you're in the `backend` directory and virtual environment is activated.

### Redis Connection Error
```
redis.exceptions.ConnectionError
```
**Solution:** Make sure Redis is running: `redis-cli ping` should return `PONG`

### Anthropic API Error
```
anthropic.AuthenticationError
```
**Solution:** Verify your `ANTHROPIC_API_KEY` in `.env` is correct.

## Development Workflow

1. **Start services:**
   ```bash
   # Terminal 1: PostgreSQL (if not running as service)
   # Terminal 2: Redis (if not running as service)
   # Terminal 3: Backend
   cd backend && source venv/bin/activate && uvicorn app.main:app --reload
   ```

2. **Make changes:**
   - Edit code in `backend/app/`
   - Server auto-reloads thanks to `--reload` flag

3. **Test changes:**
   - Use http://localhost:8000/docs to test API
   - Write unit tests in `backend/tests/`
   - Run `pytest`

4. **Commit:**
   ```bash
   git add .
   git commit -m "Description of changes"
   ```

## Next Steps

1. **Complete API Credentials Setup**
   - Get all API keys from integrated services
   - Test each integration individually

2. **Build Frontend**
   - Set up React project in `frontend/`
   - Connect to backend API
   - Implement UI components

3. **Write Tests**
   - Unit tests for services
   - Integration tests for API endpoints
   - End-to-end tests

4. **Deploy to Staging**
   - Follow DEPLOYMENT_GUIDE.md
   - Test in production-like environment

## Useful Resources

- **FastAPI Docs:** https://fastapi.tiangolo.com/
- **SQLAlchemy Docs:** https://docs.sqlalchemy.org/
- **pgvector Docs:** https://github.com/pgvector/pgvector
- **Anthropic API Docs:** https://docs.anthropic.com/
- **Microsoft Graph Docs:** https://learn.microsoft.com/en-us/graph/

## Getting Help

- Check `backend/app/main.py` for app initialization
- Review models in `backend/app/models/` to understand data structure
- Look at API endpoints in `backend/app/api/` for request/response patterns
- Read IMPLEMENTATION_SUMMARY.md for architecture overview
