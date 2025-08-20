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
    # Check if column exists first (SQLite compatible)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('users')]
    
    # Only add column if it doesn't exist
    if 'is_admin' not in columns:
        # Add column with default value
        with op.batch_alter_table('users', schema=None) as batch_op:
            batch_op.add_column(sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='0'))
        
        # Update all existing records to have is_admin = false (0)
        conn.execute(text('UPDATE users SET is_admin = 0 WHERE is_admin IS NULL'))


def downgrade():
    # Check if column exists before trying to drop (SQLite compatible)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('users')]
    
    if 'is_admin' in columns:
        with op.batch_alter_table('users', schema=None) as batch_op:
            batch_op.drop_column('is_admin')