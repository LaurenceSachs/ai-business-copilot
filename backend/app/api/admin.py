"""
Admin API endpoints for system management and monitoring.
"""
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from app.db.base import get_db
from app.core.security import get_current_admin_user
from app.models.user import User
from app.models.document import Document, DocumentSource
from app.models.audit_log import AuditLog, AuditAction
from app.services.indexing_service import IndexingService

router = APIRouter(prefix="/admin", tags=["admin"])


class IndexingStatusResponse(BaseModel):
    """Response model for indexing status."""
    total_documents: int
    documents_by_source: dict
    last_indexed: dict


class SyncRequest(BaseModel):
    """Request to trigger a sync."""
    incremental: bool = True
    sources: list[str] = []


@router.get("/status")
async def get_system_status(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get system status and statistics.

    Args:
        current_user: Admin user
        db: Database session

    Returns:
        System status information
    """
    # Count documents by source
    doc_counts = db.query(
        Document.source,
        func.count(Document.id)
    ).group_by(Document.source).all()

    # Get total users
    total_users = db.query(func.count(User.id)).scalar()

    # Get recent queries count (last 24 hours)
    from datetime import datetime, timedelta
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_queries = db.query(func.count(AuditLog.id)).filter(
        AuditLog.action == AuditAction.QUERY,
        AuditLog.timestamp >= yesterday
    ).scalar()

    return {
        "total_documents": sum(count for _, count in doc_counts),
        "documents_by_source": {source.value: count for source, count in doc_counts},
        "total_users": total_users,
        "queries_last_24h": recent_queries,
        "status": "operational"
    }


@router.get("/indexing/status")
async def get_indexing_status(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> IndexingStatusResponse:
    """
    Get indexing status for all data sources.

    Args:
        current_user: Admin user
        db: Database session

    Returns:
        Indexing status information
    """
    # Count documents by source
    doc_counts = db.query(
        Document.source,
        func.count(Document.id)
    ).group_by(Document.source).all()

    # Get last indexed timestamp for each source
    last_indexed = {}
    for source in DocumentSource:
        latest_doc = db.query(func.max(Document.last_synced_at)).filter(
            Document.source == source
        ).scalar()
        if latest_doc:
            last_indexed[source.value] = latest_doc.isoformat()

    return IndexingStatusResponse(
        total_documents=sum(count for _, count in doc_counts),
        documents_by_source={source.value: count for source, count in doc_counts},
        last_indexed=last_indexed
    )


@router.post("/indexing/sync")
async def trigger_sync(
    sync_request: SyncRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Trigger a manual sync/indexing of data sources.

    Args:
        sync_request: Sync configuration
        background_tasks: FastAPI background tasks
        current_user: Admin user
        db: Database session

    Returns:
        Sync status
    """
    def run_indexing():
        """Background task to run indexing."""
        indexing_service = IndexingService(db)
        results = indexing_service.index_all_sources(incremental=sync_request.incremental)

        # Log the sync action
        audit_log = AuditLog(
            user_id=current_user.id,
            action=AuditAction.SYNC_DATA,
            description=f"Manual sync triggered ({'incremental' if sync_request.incremental else 'full'})",
            metadata=results
        )
        db.add(audit_log)
        db.commit()

    # Add to background tasks
    background_tasks.add_task(run_indexing)

    return {
        "message": "Sync started in background",
        "incremental": sync_request.incremental
    }


@router.get("/audit-logs")
async def get_audit_logs(
    limit: int = 100,
    action: str = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get audit logs for compliance and monitoring.

    Args:
        limit: Maximum number of logs to return
        action: Filter by action type
        current_user: Admin user
        db: Database session

    Returns:
        List of audit logs
    """
    query = db.query(AuditLog)

    if action:
        try:
            action_enum = AuditAction(action)
            query = query.filter(AuditLog.action == action_enum)
        except ValueError:
            pass

    logs = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()

    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "action": log.action.value,
            "description": log.description,
            "timestamp": log.timestamp,
            "ip_address": log.ip_address,
            "target_system": log.target_system,
        }
        for log in logs
    ]


@router.get("/users")
async def get_users(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get list of all users.

    Args:
        current_user: Admin user
        db: Database session

    Returns:
        List of users
    """
    users = db.query(User).all()

    return [
        {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "last_login": user.last_login,
            "created_at": user.created_at,
        }
        for user in users
    ]
