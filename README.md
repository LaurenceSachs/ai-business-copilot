# AI Business Copilot

A secure, multi-system business intelligence assistant with natural language querying and limited write capabilities.

## Features

- Natural language querying across Microsoft 365, Dropbox, Xero, Unleashed, and HubSpot
- Semantic + keyword search with source citations
- Limited write operations (email drafts, tasks, CRM notes)
- Full audit logging
- Multi-factor authentication via Microsoft Entra ID
- Weekly automated indexing with manual sync option

## Tech Stack

- **Backend**: Python 3.11+, FastAPI
- **Frontend**: React 18+, TypeScript
- **Database**: PostgreSQL 15+ with pgvector extension
- **AI**: Anthropic Claude API
- **Authentication**: Microsoft Entra ID (OAuth 2.0)

## Project Structure

```
ai-business-copilot/
├── backend/              # FastAPI backend application
│   ├── app/
│   │   ├── api/         # API endpoints
│   │   ├── core/        # Configuration, security, dependencies
│   │   ├── integrations/# External system connectors
│   │   ├── services/    # Business logic
│   │   ├── models/      # Database models
│   │   └── db/          # Database utilities
│   ├── tests/           # Backend tests
│   └── requirements.txt
├── frontend/            # React frontend application
│   ├── src/
│   │   ├── components/  # Reusable UI components
│   │   ├── pages/       # Page components
│   │   ├── services/    # API clients
│   │   ├── hooks/       # Custom React hooks
│   │   └── utils/       # Utility functions
│   └── package.json
├── infrastructure/      # Deployment configs (Docker, nginx)
└── docs/               # Documentation

```

## Setup Instructions

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+ with pgvector extension
- API credentials for:
  - Anthropic Claude
  - Microsoft Entra ID (App Registration)
  - Dropbox
  - Xero
  - Unleashed
  - HubSpot

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env
# Edit .env with API endpoint
npm start
```

## Security Features

- Tenant-isolated data storage
- Data encryption at rest and in transit
- OAuth 2.0 / SSO authentication
- Role-based access control (RBAC)
- Comprehensive audit logging
- No AI model training on user data

## User Guide

See [docs/user-guide.md](docs/user-guide.md) for detailed usage instructions.

## API Documentation

Once running, visit `http://localhost:8000/docs` for interactive API documentation.

## License

Proprietary - Internal Use Only
