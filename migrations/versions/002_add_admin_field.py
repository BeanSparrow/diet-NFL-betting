"""Add is_admin field to users table

Revision ID: 002
Revises: 001
Create Date: 2025-08-19 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # Add is_admin column to users table
    # First add as nullable with default false
    op.add_column('users', sa.Column('is_admin', sa.Boolean(), nullable=True, server_default='false'))
    
    # Update all existing users to have is_admin = False (PostgreSQL compatible)
    from sqlalchemy import text
    op.execute(text('UPDATE users SET is_admin = false WHERE is_admin IS NULL'))
    
    # Note: SQLite doesn't support ALTER COLUMN to change nullable, 
    # but the column will effectively be NOT NULL since all values are set


def downgrade():
    # Remove is_admin column
    op.drop_column('users', 'is_admin')