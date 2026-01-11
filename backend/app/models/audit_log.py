"""
Audit log model for tracking all queries and write operations.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum
from app.db.base import Base


class AuditAction(str, enum.Enum):
    """Enumeration of audit actions."""
    QUERY = "query"
    CREATE_EMAIL_DRAFT = "create_email_draft"
    CREATE_TODO = "create_todo"
    CREATE_HUBSPOT_NOTE = "create_hubspot_note"
    CREATE_HUBSPOT_TASK = "create_hubspot_task"
    LOGIN = "login"
    LOGOUT = "logout"
    SYNC_DATA = "sync_data"


class AuditLog(Base):
    """
    Comprehensive audit log for compliance and security.
    Records all user queries and write operations with before/after state.
    """

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Action details
    action = Column(Enum(AuditAction), nullable=False, index=True)
    description = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Request/Response data
    query_text = Column(Text)  # For search queries
    response_summary = Column(Text)  # Summary of response
    sources_used = Column(JSON, default=list)  # List of document IDs used

    # Write operation tracking
    target_system = Column(String)  # System being written to
    target_id = Column(String)  # ID of created/modified item
    before_state = Column(JSON)  # State before modification (if applicable)
    after_state = Column(JSON)  # State after modification
    user_confirmed = Column(DateTime)  # When user confirmed the action

    # Session and security
    ip_address = Column(String)
    user_agent = Column(String)
    session_id = Column(String, index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog(action='{self.action}', user_id={self.user_id}, timestamp='{self.timestamp}')>"
