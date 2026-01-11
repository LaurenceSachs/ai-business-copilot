"""
Authentication service for Microsoft Entra ID integration.
"""
from datetime import datetime
from typing import Optional
import msal
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import create_access_token
from app.models.user import User


class AuthService:
    """Service for handling Microsoft Entra ID authentication."""

    def __init__(self):
        """Initialize MSAL confidential client application."""
        self.msal_app = msal.ConfidentialClientApplication(
            settings.AZURE_CLIENT_ID,
            authority=f"https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}",
            client_credential=settings.AZURE_CLIENT_SECRET,
        )

    def get_authorization_url(self, state: str) -> str:
        """
        Generate authorization URL for OAuth flow.

        Args:
            state: State parameter for CSRF protection

        Returns:
            Authorization URL to redirect user to
        """
        auth_url = self.msal_app.get_authorization_request_url(
            scopes=["User.Read", "Mail.Read", "Calendars.Read", "Tasks.ReadWrite", "Files.Read.All"],
            state=state,
            redirect_uri=settings.AZURE_REDIRECT_URI,
        )
        return auth_url

    def acquire_token_by_auth_code(self, code: str) -> dict:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            Token response from MSAL

        Raises:
            Exception: If token acquisition fails
        """
        result = self.msal_app.acquire_token_by_authorization_code(
            code,
            scopes=["User.Read", "Mail.Read", "Calendars.Read", "Tasks.ReadWrite", "Files.Read.All"],
            redirect_uri=settings.AZURE_REDIRECT_URI,
        )

        if "error" in result:
            raise Exception(f"Failed to acquire token: {result.get('error_description')}")

        return result

    def get_or_create_user(self, db: Session, azure_token: dict) -> User:
        """
        Get or create user from Azure token.

        Args:
            db: Database session
            azure_token: Token response from Azure containing user info

        Returns:
            User object
        """
        # Extract user info from token
        id_token_claims = azure_token.get("id_token_claims", {})
        azure_id = id_token_claims.get("oid")
        email = id_token_claims.get("preferred_username") or id_token_claims.get("email")
        full_name = id_token_claims.get("name", "")

        # Check if user exists
        user = db.query(User).filter(User.azure_id == azure_id).first()

        if user:
            # Update last login
            user.last_login = datetime.utcnow()
        else:
            # Create new user
            user = User(
                email=email,
                full_name=full_name,
                azure_id=azure_id,
                azure_tenant_id=settings.AZURE_TENANT_ID,
                is_active=True,
                is_admin=False,  # First user should be manually set as admin in DB
                roles=[],
                last_login=datetime.utcnow(),
            )
            db.add(user)

        db.commit()
        db.refresh(user)
        return user

    def create_user_session_token(self, user: User) -> str:
        """
        Create JWT session token for user.

        Args:
            user: User object

        Returns:
            JWT token
        """
        token_data = {
            "sub": user.id,
            "email": user.email,
            "is_admin": user.is_admin,
        }
        return create_access_token(token_data)

    def refresh_token(self, refresh_token: str) -> dict:
        """
        Refresh an expired access token.

        Args:
            refresh_token: Refresh token from previous authentication

        Returns:
            New token response

        Raises:
            Exception: If token refresh fails
        """
        result = self.msal_app.acquire_token_by_refresh_token(
            refresh_token,
            scopes=["User.Read", "Mail.Read", "Calendars.Read", "Tasks.ReadWrite", "Files.Read.All"],
        )

        if "error" in result:
            raise Exception(f"Failed to refresh token: {result.get('error_description')}")

        return result


# Singleton instance
auth_service = AuthService()
