"""
User model for authentication and authorization.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base


class User(Base):
    """User model with Microsoft Entra ID integration."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)

    # Microsoft Entra ID fields
    azure_id = Column(String, unique=True, index=True, nullable=False)
    azure_tenant_id = Column(String, nullable=False)

    # Authorization
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    roles = Column(JSON, default=list)  # List of role names

    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = Column(DateTime)

    # Relationships
    audit_logs = relationship("AuditLog", back_populates="user")

    def __repr__(self):
        return f"<User(email='{self.email}', full_name='{self.full_name}')>"
