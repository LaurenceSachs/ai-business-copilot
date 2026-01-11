"""
Query API endpoints for searching and querying business data.
"""
from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.base import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.document import DocumentSource
from app.services.query_service import QueryService

router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    """Request model for queries."""
    query: str
    filters: Optional[Dict[str, Any]] = None


class QueryResponse(BaseModel):
    """Response model for queries."""
    answer: str
    summary: str
    citations: list
    metadata: dict


class SearchFiltersRequest(BaseModel):
    """Request model for advanced search filters."""
    source: Optional[DocumentSource] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    author: Optional[str] = None
    keyword: Optional[str] = None


@router.post("/", response_model=QueryResponse)
async def query_business_data(
    query_request: QueryRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Query business data using natural language.

    Args:
        query_request: Query text and optional filters
        request: FastAPI request object
        current_user: Authenticated user
        db: Database session

    Returns:
        Query results with answer and citations
    """
    query_service = QueryService(db)

    result = query_service.process_query(
        user=current_user,
        query_text=query_request.query,
        filters=query_request.filters,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )

    return QueryResponse(**result)


@router.get("/history")
async def get_query_history(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get query history for the current user.

    Args:
        limit: Maximum number of queries to return
        current_user: Authenticated user
        db: Database session

    Returns:
        List of previous queries
    """
    from app.models.audit_log import AuditLog, AuditAction

    logs = db.query(AuditLog).filter(
        AuditLog.user_id == current_user.id,
        AuditLog.action == AuditAction.QUERY
    ).order_by(AuditLog.timestamp.desc()).limit(limit).all()

    return [
        {
            "query": log.query_text,
            "summary": log.response_summary,
            "timestamp": log.timestamp,
        }
        for log in logs
    ]


@router.get("/sources")
async def get_available_sources(
    current_user: User = Depends(get_current_user)
):
    """
    Get list of available data sources for filtering.

    Returns:
        List of data sources
    """
    return {
        "sources": [
            {"value": "outlook_email", "label": "Outlook Emails"},
            {"value": "outlook_calendar", "label": "Outlook Calendar"},
            {"value": "dropbox", "label": "Dropbox Files"},
            {"value": "xero", "label": "Xero Accounting"},
            {"value": "unleashed", "label": "Unleashed Inventory"},
            {"value": "hubspot_contact", "label": "HubSpot Contacts"},
            {"value": "hubspot_deal", "label": "HubSpot Deals"},
            {"value": "hubspot_note", "label": "HubSpot Notes"},
            {"value": "ms_todo", "label": "Microsoft To Do"},
        ]
    }
