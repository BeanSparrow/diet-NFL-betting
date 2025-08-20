"""Remove unique bet constraint to allow multiple bets per user per game with different statuses

Revision ID: 004_remove_unique_bet_constraint
Revises: 003_fix_admin_field
Create Date: 2025-08-19 16:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004_remove_unique_bet_constraint'
down_revision = 'c3dc95c94fa1'
branch_labels = None
depends_on = None


def upgrade():
    """Remove the unique constraint that prevents multiple bets per user per game"""
    # SQLite requires batch mode to drop constraints
    with op.batch_alter_table('bets', schema=None) as batch_op:
        batch_op.drop_constraint('unique_user_game_bet', type_='unique')


def downgrade():
    """Restore the unique constraint"""
    # Recreate the unique constraint using batch mode
    with op.batch_alter_table('bets', schema=None) as batch_op:
        batch_op.create_unique_constraint('unique_user_game_bet', ['user_id', 'game_id'])