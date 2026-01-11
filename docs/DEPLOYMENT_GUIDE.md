# AI Business Copilot - Deployment Guide

This guide walks you through deploying the AI Business Copilot on self-hosted infrastructure.

## Prerequisites

### System Requirements

- **Operating System**: Linux (Ubuntu 22.04 LTS recommended) or Windows Server
- **CPU**: 4+ cores
- **RAM**: 16GB minimum, 32GB recommended
- **Storage**: 100GB+ SSD
- **Network**: Static IP address, firewall configured for HTTPS (port 443)

### Software Requirements

- Python 3.11+
- PostgreSQL 15+ with pgvector extension
- Redis 6+
- Node.js 18+ and npm
- Nginx (for reverse proxy)
- SSL certificate (Let's Encrypt or commercial)

## Step 1: API Credentials Setup

Before deployment, obtain API credentials for all integrated services:

### 1.1 Microsoft Entra ID (Azure AD)

1. Go to [Azure Portal](https://portal.azure.com) > Azure Active Directory
2. Navigate to **App registrations** > **New registration**
3. Name: "AI Business Copilot"
4. Supported account types: Single tenant
5. Redirect URI: `https://yourdomain.com/api/v1/auth/callback`
6. After creation, note the **Application (client) ID** and **Directory (tenant) ID**
7. Go to **Certificates & secrets** > **New client secret**
8. Note the **Client secret value** (save immediately, won't be shown again)
9. Go to **API permissions** > **Add a permission** > **Microsoft Graph**
10. Add these **Delegated permissions**:
    - User.Read
    - Mail.Read
    - Calendars.Read
    - Tasks.ReadWrite
    - Files.Read.All
11. Grant admin consent for your organization

### 1.2 Anthropic Claude API

1. Sign up at [Anthropic Console](https://console.anthropic.com)
2. Go to API Keys section
3. Create a new API key
4. Note the key (starts with `sk-ant-`)

### 1.3 Dropbox

1. Go to [Dropbox App Console](https://www.dropbox.com/developers/apps)
2. Create new app > Scoped access > Full Dropbox access
3. Note the **App key** and **App secret**
4. Generate an access token or set up OAuth flow
5. Get refresh token using OAuth 2.0 flow

### 1.4 Xero

1. Go to [Xero Developer Portal](https://developer.xero.com/myapps)
2. Create new app > Web app
3. Redirect URI: `https://yourdomain.com/api/v1/integrations/xero/callback`
4. Note **Client ID** and **Client secret**
5. Complete OAuth 2.0 flow to get **Refresh token**
6. Note your **Tenant ID** (organization ID)

### 1.5 Unleashed

1. Login to Unleashed > Settings > Integration
2. Generate API credentials
3. Note **API ID** and **API Key**

### 1.6 HubSpot

1. Go to [HubSpot App Developer Account](https://developers.hubspot.com/)
2. Create private app or use OAuth
3. Grant these scopes: crm.objects.contacts, crm.objects.deals, crm.objects.notes
4. Note the **Access Token**
5. Note your **Portal ID** (HubSpot account ID)

## Step 2: Database Setup

### 2.1 Install PostgreSQL with pgvector

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql-15 postgresql-contrib-15

# Install pgvector extension
sudo apt install postgresql-15-pgvector

# Or build from source:
cd /tmp
git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

### 2.2 Create Database

```bash
sudo -u postgres psql

# In PostgreSQL shell:
CREATE DATABASE ai_copilot;
CREATE USER ai_copilot_user WITH PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE ai_copilot TO ai_copilot_user;

# Connect to database and enable extensions
\c ai_copilot
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- For text search

# Grant permissions
GRANT ALL ON SCHEMA public TO ai_copilot_user;

\q
```

### 2.3 Configure PostgreSQL

Edit `/etc/postgresql/15/main/postgresql.conf`:

```conf
# Increase shared_buffers for better performance
shared_buffers = 4GB
effective_cache_size = 12GB
maintenance_work_mem = 1GB
work_mem = 64MB

# Connection settings
max_connections = 100
```

Restart PostgreSQL:

```bash
sudo systemctl restart postgresql
```

## Step 3: Install Redis

```bash
sudo apt install redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

## Step 4: Backend Setup

### 4.1 Clone and Setup Backend

```bash
cd /opt
sudo mkdir ai-business-copilot
sudo chown $USER:$USER ai-business-copilot
cd ai-business-copilot

# Copy your backend files here
# Or clone from your git repository

cd backend
```

### 4.2 Create Python Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4.3 Configure Environment Variables

```bash
cp .env.example .env
nano .env
```

Fill in all the API credentials you obtained in Step 1:

```env
# Application
APP_NAME=AI Business Copilot
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=<generate-with: openssl rand -hex 32>
API_V1_PREFIX=/api/v1

# Database
DATABASE_URL=postgresql://ai_copilot_user:your-secure-password@localhost:5432/ai_copilot
DB_ECHO=False

# Anthropic Claude API
ANTHROPIC_API_KEY=sk-ant-your-key-here
CLAUDE_MODEL=claude-sonnet-4-5-20250929
MAX_TOKENS=4096

# Microsoft Entra ID
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=your-tenant-id
AZURE_REDIRECT_URI=https://yourdomain.com/api/v1/auth/callback

# ... (fill in all other credentials)

# Security
CORS_ORIGINS=https://yourdomain.com
JWT_SECRET_KEY=<generate-with: openssl rand -hex 32>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Redis
REDIS_URL=redis://localhost:6379/0
```

### 4.4 Run Database Migrations

```bash
alembic upgrade head
```

### 4.5 Create First Admin User

```bash
# Create a Python script to add first admin user
python3 <<EOF
from app.db.base import SessionLocal
from app.models.user import User
from datetime import datetime

db = SessionLocal()

# Replace with your Azure AD details
admin_user = User(
    email="admin@yourdomain.com",
    full_name="Admin User",
    azure_id="your-azure-object-id",
    azure_tenant_id="your-tenant-id",
    is_active=True,
    is_admin=True,
    roles=["admin"],
    created_at=datetime.utcnow(),
    updated_at=datetime.utcnow()
)

db.add(admin_user)
db.commit()
print(f"Admin user created: {admin_user.email}")
EOF
```

### 4.6 Setup Celery Worker for Background Tasks

Create systemd service file `/etc/systemd/system/ai-copilot-celery.service`:

```ini
[Unit]
Description=AI Business Copilot Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/opt/ai-business-copilot/backend
Environment="PATH=/opt/ai-business-copilot/backend/venv/bin"
ExecStart=/opt/ai-business-copilot/backend/venv/bin/celery -A app.tasks worker --loglevel=info

[Install]
WantedBy=multi-user.target
```

### 4.7 Setup Celery Beat for Scheduled Indexing

Create `/etc/systemd/system/ai-copilot-celerybeat.service`:

```ini
[Unit]
Description=AI Business Copilot Celery Beat Scheduler
After=network.target redis.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/ai-business-copilot/backend
Environment="PATH=/opt/ai-business-copilot/backend/venv/bin"
ExecStart=/opt/ai-business-copilot/backend/venv/bin/celery -A app.tasks beat --loglevel=info

[Install]
WantedBy=multi-user.target
```

### 4.8 Setup Uvicorn Service

Create `/etc/systemd/system/ai-copilot-api.service`:

```ini
[Unit]
Description=AI Business Copilot API
After=network.target postgresql.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/ai-business-copilot/backend
Environment="PATH=/opt/ai-business-copilot/backend/venv/bin"
ExecStart=/opt/ai-business-copilot/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4

[Install]
WantedBy=multi-user.target
```

Enable and start services:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-copilot-api
sudo systemctl enable ai-copilot-celery
sudo systemctl enable ai-copilot-celerybeat
sudo systemctl start ai-copilot-api
sudo systemctl start ai-copilot-celery
sudo systemctl start ai-copilot-celerybeat

# Check status
sudo systemctl status ai-copilot-api
```

## Step 5: Frontend Setup

```bash
cd /opt/ai-business-copilot/frontend
npm install
npm run build
```

## Step 6: Nginx Configuration

### 6.1 Install Nginx

```bash
sudo apt install nginx
```

### 6.2 Configure Nginx

Create `/etc/nginx/sites-available/ai-copilot`:

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    # SSL certificates (update paths)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Frontend
    location / {
        root /opt/ai-business-copilot/frontend/build;
        try_files $uri /index.html;
    }

    # API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts for long-running queries
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Max upload size
    client_max_body_size 50M;
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/ai-copilot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Step 7: SSL Certificate with Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

## Step 8: Initial Data Indexing

```bash
cd /opt/ai-business-copilot/backend
source venv/bin/activate

# Run initial indexing (can take several hours for 100GB Dropbox)
python3 <<EOF
from app.db.base import SessionLocal
from app.services.indexing_service import IndexingService

db = SessionLocal()
indexing_service = IndexingService(db)

print("Starting initial indexing...")
results = indexing_service.index_all_sources(incremental=False)

print("Indexing complete:")
for source, count in results.items():
    print(f"  {source}: {count} documents")
EOF
```

## Step 9: Security Hardening

### 9.1 Firewall Configuration

```bash
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 80/tcp  # HTTP
sudo ufw allow 443/tcp # HTTPS
sudo ufw enable
```

### 9.2 Fail2Ban

```bash
sudo apt install fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 9.3 Automatic Security Updates

```bash
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

## Step 10: Monitoring and Logging

### 10.1 Setup Log Rotation

Create `/etc/logrotate.d/ai-copilot`:

```
/var/log/ai-copilot/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
}
```

### 10.2 Monitoring Script

Create a monitoring cron job to check system health:

```bash
sudo crontab -e

# Add this line to check every 5 minutes
*/5 * * * * systemctl is-active ai-copilot-api || systemctl restart ai-copilot-api
```

## Step 11: Backup Strategy

### 11.1 Database Backups

Create `/opt/ai-business-copilot/scripts/backup-db.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/backup/ai-copilot"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
pg_dump -U ai_copilot_user ai_copilot | gzip > $BACKUP_DIR/db_backup_$DATE.sql.gz

# Keep only last 30 days
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +30 -delete
```

Add to crontab for daily backups:

```bash
0 2 * * * /opt/ai-business-copilot/scripts/backup-db.sh
```

## Step 12: Testing

### 12.1 Test API

```bash
curl https://yourdomain.com/health
# Should return: {"status":"healthy"}
```

### 12.2 Test Authentication

1. Navigate to `https://yourdomain.com`
2. Click login
3. Authenticate with Microsoft Entra ID
4. Verify you can access the dashboard

### 12.3 Test Query

1. Enter a test query: "Show me recent emails"
2. Verify results are returned with citations
3. Check audit logs in admin panel

## Maintenance

### Weekly Tasks

- Review audit logs
- Check disk space usage
- Verify backups are running

### Monthly Tasks

- Update dependencies: `pip install -U -r requirements.txt`
- Review and archive old audit logs
- Performance optimization review

### As Needed

- Manual sync: Use admin panel "Sync Now" button
- Add/remove users: Use admin panel
- Update API credentials: Edit `.env` and restart services

## Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u ai-copilot-api -n 100
sudo journalctl -u ai-copilot-celery -n 100

# Check permissions
ls -la /opt/ai-business-copilot/backend
```

### Database Connection Issues

```bash
# Test connection
psql -U ai_copilot_user -d ai_copilot -h localhost

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-15-main.log
```

### Slow Queries

```sql
-- Check slow queries in PostgreSQL
SELECT * FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 10;
```

## Support

For issues or questions:
- Check logs in `/var/log/ai-copilot/`
- Review API documentation at `https://yourdomain.com/docs`
- Contact your system administrator

## Security Considerations

- Regularly update all dependencies
- Monitor audit logs for suspicious activity
- Rotate API keys periodically
- Review user access quarterly
- Keep backups in separate location
- Use MFA for all administrative accounts
