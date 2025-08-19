"""Fix admin field - ensure it exists on users table

Revision ID: 003
Revises: 002
Create Date: 2025-08-19 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    # Check if column exists first (PostgreSQL compatible)
    conn = op.get_bind()
    result = conn.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='users' AND column_name='is_admin'
    """))
    
    # Only add column if it doesn't exist
    if result.rowcount == 0:
        op.add_column('users', sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'))
        # Remove the server default after adding
        op.alter_column('users', 'is_admin', server_default=None)


def downgrade():
    # Check if column exists before trying to drop
    conn = op.get_bind()
    result = conn.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='users' AND column_name='is_admin'
    """))
    
    if result.rowcount > 0:
        op.drop_column('users', 'is_admin')