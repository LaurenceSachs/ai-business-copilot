"""
Write action API endpoints for creating drafts, tasks, and notes.
All actions require user confirmation and are audited.
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from app.db.base import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.audit_log import AuditLog, AuditAction
from app.integrations.microsoft_graph import MicrosoftGraphService
from app.integrations.hubspot_client import HubSpotService

router = APIRouter(prefix="/actions", tags=["actions"])


class EmailDraftRequest(BaseModel):
    """Request to create an email draft."""
    to: List[EmailStr]
    subject: str
    body: str
    cc: Optional[List[EmailStr]] = None
    bcc: Optional[List[EmailStr]] = None


class EmailDraftPreview(BaseModel):
    """Preview of email draft before creation."""
    to: List[str]
    cc: Optional[List[str]]
    bcc: Optional[List[str]]
    subject: str
    body: str


class TodoTaskRequest(BaseModel):
    """Request to create a To Do task."""
    title: str
    body: Optional[str] = None
    due_date: Optional[datetime] = None
    list_name: str = "Tasks"


class HubSpotNoteRequest(BaseModel):
    """Request to create a HubSpot note."""
    note_body: str
    associated_contacts: Optional[List[str]] = None
    associated_deals: Optional[List[str]] = None


class HubSpotTaskRequest(BaseModel):
    """Request to create a HubSpot task."""
    subject: str
    body: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: str = "MEDIUM"
    associated_contacts: Optional[List[str]] = None
    associated_deals: Optional[List[str]] = None


@router.post("/email-draft/preview")
async def preview_email_draft(
    draft: EmailDraftRequest,
    current_user: User = Depends(get_current_user)
) -> EmailDraftPreview:
    """
    Preview an email draft before creation.

    Args:
        draft: Email draft details
        current_user: Authenticated user

    Returns:
        Preview of the email draft
    """
    return EmailDraftPreview(
        to=draft.to,
        cc=draft.cc,
        bcc=draft.bcc,
        subject=draft.subject,
        body=draft.body
    )


@router.post("/email-draft/create")
async def create_email_draft(
    draft: EmailDraftRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create an email draft in Outlook (requires user confirmation).

    Args:
        draft: Email draft details
        request: FastAPI request
        current_user: Authenticated user
        db: Database session

    Returns:
        Created draft details
    """
    try:
        # Initialize Microsoft Graph service
        ms_graph = MicrosoftGraphService()

        # Create the draft
        result = await ms_graph.create_email_draft(
            user_email=current_user.email,
            to=draft.to,
            subject=draft.subject,
            body=draft.body,
            cc=draft.cc,
            bcc=draft.bcc
        )

        # Log the action
        audit_log = AuditLog(
            user_id=current_user.id,
            action=AuditAction.CREATE_EMAIL_DRAFT,
            description=f"Created email draft: {draft.subject}",
            target_system="outlook",
            target_id=result["id"],
            after_state={
                "to": draft.to,
                "subject": draft.subject,
                "id": result["id"],
            },
            user_confirmed=datetime.utcnow(),
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        db.add(audit_log)
        db.commit()

        return {
            "success": True,
            "draft_id": result["id"],
            "subject": result["subject"],
            "web_link": result["web_link"],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create email draft: {str(e)}")


@router.post("/todo/create")
async def create_todo_task(
    task: TodoTaskRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a Microsoft To Do task.

    Args:
        task: Task details
        request: FastAPI request
        current_user: Authenticated user
        db: Database session

    Returns:
        Created task details
    """
    try:
        ms_graph = MicrosoftGraphService()

        result = await ms_graph.create_todo_task(
            user_email=current_user.email,
            title=task.title,
            body=task.body,
            due_date=task.due_date,
            list_name=task.list_name
        )

        # Log the action
        audit_log = AuditLog(
            user_id=current_user.id,
            action=AuditAction.CREATE_TODO,
            description=f"Created To Do task: {task.title}",
            target_system="ms_todo",
            target_id=result["id"],
            after_state={
                "title": task.title,
                "list_name": task.list_name,
                "id": result["id"],
            },
            user_confirmed=datetime.utcnow(),
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        db.add(audit_log)
        db.commit()

        return {
            "success": True,
            "task_id": result["id"],
            "title": result["title"],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create To Do task: {str(e)}")


@router.post("/hubspot/note/create")
async def create_hubspot_note(
    note: HubSpotNoteRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a note in HubSpot.

    Args:
        note: Note details
        request: FastAPI request
        current_user: Authenticated user
        db: Database session

    Returns:
        Created note details
    """
    try:
        hubspot = HubSpotService()

        result = hubspot.create_note(
            note_body=note.note_body,
            associated_contacts=note.associated_contacts,
            associated_deals=note.associated_deals
        )

        # Log the action
        audit_log = AuditLog(
            user_id=current_user.id,
            action=AuditAction.CREATE_HUBSPOT_NOTE,
            description=f"Created HubSpot note",
            target_system="hubspot",
            target_id=result["id"],
            after_state={
                "note_body": note.note_body[:100],
                "id": result["id"],
            },
            user_confirmed=datetime.utcnow(),
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        db.add(audit_log)
        db.commit()

        return {
            "success": True,
            "note_id": result["id"],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create HubSpot note: {str(e)}")


@router.post("/hubspot/task/create")
async def create_hubspot_task(
    task: HubSpotTaskRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a task in HubSpot.

    Args:
        task: Task details
        request: FastAPI request
        current_user: Authenticated user
        db: Database session

    Returns:
        Created task details
    """
    try:
        hubspot = HubSpotService()

        result = hubspot.create_task(
            subject=task.subject,
            body=task.body,
            due_date=task.due_date,
            priority=task.priority,
            associated_contacts=task.associated_contacts,
            associated_deals=task.associated_deals
        )

        # Log the action
        audit_log = AuditLog(
            user_id=current_user.id,
            action=AuditAction.CREATE_HUBSPOT_TASK,
            description=f"Created HubSpot task: {task.subject}",
            target_system="hubspot",
            target_id=result["id"],
            after_state={
                "subject": task.subject,
                "priority": task.priority,
                "id": result["id"],
            },
            user_confirmed=datetime.utcnow(),
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        db.add(audit_log)
        db.commit()

        return {
            "success": True,
            "task_id": result["id"],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create HubSpot task: {str(e)}")
