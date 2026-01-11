"""
Document model for indexed content across all integrated systems.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Enum, Index
from pgvector.sqlalchemy import Vector
import enum
from app.db.base import Base


class DocumentSource(str, enum.Enum):
    """Enumeration of document sources."""
    OUTLOOK_EMAIL = "outlook_email"
    OUTLOOK_CALENDAR = "outlook_calendar"
    DROPBOX = "dropbox"
    XERO = "xero"
    UNLEASHED = "unleashed"
    HUBSPOT_CONTACT = "hubspot_contact"
    HUBSPOT_DEAL = "hubspot_deal"
    HUBSPOT_NOTE = "hubspot_note"
    MS_TODO = "ms_todo"
    TEAMS_MESSAGE = "teams_message"
    EXCEL = "excel"
    WORD = "word"


class Document(Base):
    """
    Indexed document with vector embeddings for semantic search.
    Stores content from all integrated business systems.
    """

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)

    # Source information
    source = Column(Enum(DocumentSource), nullable=False, index=True)
    source_id = Column(String, nullable=False)  # Original ID in source system
    source_url = Column(String)  # Deep link to original item

    # Content
    title = Column(String, nullable=False)
    content = Column(Text)
    summary = Column(Text)

    # Metadata
    metadata = Column(JSON, default=dict)  # Source-specific metadata
    author = Column(String)
    created_date = Column(DateTime)
    modified_date = Column(DateTime)

    # Search fields
    embedding = Column(Vector(384))  # Vector embedding for semantic search (all-MiniLM-L6-v2 dimension)
    keywords = Column(JSON, default=list)  # Extracted keywords

    # Indexing metadata
    indexed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_synced_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Composite indexes for efficient querying
    __table_args__ = (
        Index("idx_source_source_id", "source", "source_id", unique=True),
        Index("idx_source_created_date", "source", "created_date"),
        Index("idx_author", "author"),
    )

    def __repr__(self):
        return f"<Document(source='{self.source}', title='{self.title[:50]}')>"
