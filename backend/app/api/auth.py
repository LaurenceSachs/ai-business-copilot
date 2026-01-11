"""
Authentication API endpoints.
"""
import secrets
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.base import get_db
from app.services.auth_service import auth_service
from app.models.audit_log import AuditLog, AuditAction

router = APIRouter(prefix="/auth", tags=["authentication"])


class TokenResponse(BaseModel):
    """Response model for token endpoint."""
    access_token: str
    token_type: str = "bearer"
    user: dict


@router.get("/login")
async def login(request: Request):
    """
    Initiate OAuth login flow with Microsoft Entra ID.

    Returns:
        Redirect to Microsoft login page
    """
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)

    # Store state in session (you'd typically use Redis or encrypted cookie)
    # For now, we'll pass it through the OAuth flow
    auth_url = auth_service.get_authorization_url(state)

    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def auth_callback(
    code: str,
    state: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    OAuth callback endpoint.

    Args:
        code: Authorization code from Microsoft
        state: State parameter for CSRF validation
        request: FastAPI request object
        db: Database session

    Returns:
        JWT access token and user info
    """
    # TODO: Validate state parameter against stored value

    try:
        # Exchange code for token
        azure_token = auth_service.acquire_token_by_auth_code(code)

        # Get or create user
        user = auth_service.get_or_create_user(db, azure_token)

        # Create session token
        access_token = auth_service.create_user_session_token(user)

        # Log login
        audit_log = AuditLog(
            user_id=user.id,
            action=AuditAction.LOGIN,
            description=f"User logged in via Microsoft Entra ID",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
        )
        db.add(audit_log)
        db.commit()

        return TokenResponse(
            access_token=access_token,
            user={
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "is_admin": user.is_admin,
            }
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/logout")
async def logout(request: Request, db: Session = Depends(get_db)):
    """
    Logout endpoint.

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        Success message
    """
    # In a real implementation, you'd invalidate the token
    # For JWT, you'd typically add it to a blacklist in Redis

    return {"message": "Logged out successfully"}


@router.post("/refresh")
async def refresh_token(refresh_token: str):
    """
    Refresh an expired access token.

    Args:
        refresh_token: Refresh token from previous authentication

    Returns:
        New access token
    """
    try:
        new_token = auth_service.refresh_token(refresh_token)
        return {"access_token": new_token["access_token"], "token_type": "bearer"}
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
