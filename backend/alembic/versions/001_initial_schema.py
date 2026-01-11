"""Initial database schema with pgvector support

Revision ID: 001
Revises:
Create Date: 2026-01-11

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=False),
        sa.Column('azure_id', sa.String(), nullable=False),
        sa.Column('azure_tenant_id', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('is_admin', sa.Boolean(), nullable=True, default=False),
        sa.Column('roles', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_azure_id'), 'users', ['azure_id'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source', sa.Enum('outlook_email', 'outlook_calendar', 'dropbox', 'xero',
                  'unleashed', 'hubspot_contact', 'hubspot_deal', 'hubspot_note',
                  'ms_todo', 'teams_message', 'excel', 'word',
                  name='documentsource'), nullable=False),
        sa.Column('source_id', sa.String(), nullable=False),
        sa.Column('source_url', sa.String(), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('author', sa.String(), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('modified_date', sa.DateTime(), nullable=True),
        sa.Column('embedding', Vector(384), nullable=True),
        sa.Column('keywords', sa.JSON(), nullable=True),
        sa.Column('indexed_at', sa.DateTime(), nullable=False),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_documents_id'), 'documents', ['id'], unique=False)
    op.create_index(op.f('ix_documents_source'), 'documents', ['source'], unique=False)
    op.create_index('idx_source_source_id', 'documents', ['source', 'source_id'], unique=True)
    op.create_index('idx_source_created_date', 'documents', ['source', 'created_date'], unique=False)
    op.create_index('idx_author', 'documents', ['author'], unique=False)

    # Create vector index for similarity search
    op.execute('CREATE INDEX idx_documents_embedding ON documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)')

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.Enum('query', 'create_email_draft', 'create_todo',
                  'create_hubspot_note', 'create_hubspot_task', 'login', 'logout', 'sync_data',
                  name='auditaction'), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('query_text', sa.Text(), nullable=True),
        sa.Column('response_summary', sa.Text(), nullable=True),
        sa.Column('sources_used', sa.JSON(), nullable=True),
        sa.Column('target_system', sa.String(), nullable=True),
        sa.Column('target_id', sa.String(), nullable=True),
        sa.Column('before_state', sa.JSON(), nullable=True),
        sa.Column('after_state', sa.JSON(), nullable=True),
        sa.Column('user_confirmed', sa.DateTime(), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.Column('session_id', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_audit_logs_timestamp'), 'audit_logs', ['timestamp'], unique=False)
    op.create_index(op.f('ix_audit_logs_session_id'), 'audit_logs', ['session_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_audit_logs_session_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_timestamp'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_action'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_user_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_id'), table_name='audit_logs')
    op.drop_table('audit_logs')

    op.execute('DROP INDEX IF EXISTS idx_documents_embedding')
    op.drop_index('idx_author', table_name='documents')
    op.drop_index('idx_source_created_date', table_name='documents')
    op.drop_index('idx_source_source_id', table_name='documents')
    op.drop_index(op.f('ix_documents_source'), table_name='documents')
    op.drop_index(op.f('ix_documents_id'), table_name='documents')
    op.drop_table('documents')

    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_azure_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')

    op.execute('DROP EXTENSION IF EXISTS vector')
