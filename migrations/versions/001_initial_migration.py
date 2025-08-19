"""Initial migration - Create Users, Games, and Bets tables

Revision ID: 001
Revises: 
Create Date: 2025-08-18 17:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import func

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### Create Users table ###
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('discord_id', sa.String(length=20), nullable=False),
        sa.Column('username', sa.String(length=32), nullable=False),
        sa.Column('discriminator', sa.String(length=4), nullable=True),
        sa.Column('display_name', sa.String(length=32), nullable=True),
        sa.Column('avatar_url', sa.String(length=255), nullable=True),
        sa.Column('email', sa.String(length=100), nullable=True),
        
        # Betting balance
        sa.Column('balance', sa.Float(), nullable=False, default=10000.0),
        sa.Column('starting_balance', sa.Float(), nullable=False, default=10000.0),
        sa.Column('total_winnings', sa.Float(), default=0.0),
        sa.Column('total_losses', sa.Float(), default=0.0),
        
        # Statistics
        sa.Column('total_bets', sa.Integer(), default=0),
        sa.Column('winning_bets', sa.Integer(), default=0),
        sa.Column('losing_bets', sa.Integer(), default=0),
        sa.Column('biggest_win', sa.Float(), default=0.0),
        sa.Column('biggest_loss', sa.Float(), default=0.0),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, default=func.now()),
        sa.Column('last_login', sa.DateTime(), default=func.now()),
        sa.Column('last_active', sa.DateTime(), default=func.now()),
        
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('discord_id')
    )
    op.create_index(op.f('ix_users_discord_id'), 'users', ['discord_id'], unique=True)
    
    # ### Create Games table ###
    op.create_table('games',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('espn_game_id', sa.String(length=20), nullable=False),
        
        # Schedule information
        sa.Column('week', sa.Integer(), nullable=False),
        sa.Column('season', sa.Integer(), nullable=False),
        sa.Column('season_type', sa.String(length=20), default='regular'),
        
        # Teams
        sa.Column('home_team', sa.String(length=50), nullable=False),
        sa.Column('home_team_abbr', sa.String(length=5), nullable=True),
        sa.Column('away_team', sa.String(length=50), nullable=False),
        sa.Column('away_team_abbr', sa.String(length=5), nullable=True),
        
        # Game timing
        sa.Column('game_time', sa.DateTime(), nullable=False),
        sa.Column('quarter', sa.String(length=10), nullable=True),
        sa.Column('time_remaining', sa.String(length=10), nullable=True),
        
        # Status
        sa.Column('status', sa.String(length=20), nullable=False, default='scheduled'),
        
        # Scores
        sa.Column('home_score', sa.Integer(), default=0),
        sa.Column('away_score', sa.Integer(), default=0),
        
        # Results
        sa.Column('winner', sa.String(length=50), nullable=True),
        sa.Column('is_tie', sa.Boolean(), default=False),
        
        # Betting information
        sa.Column('total_bets', sa.Integer(), default=0),
        sa.Column('total_wagered', sa.Float(), default=0.0),
        sa.Column('home_bets', sa.Integer(), default=0),
        sa.Column('away_bets', sa.Integer(), default=0),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, default=func.now()),
        sa.Column('updated_at', sa.DateTime(), default=func.now()),
        
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('espn_game_id')
    )
    op.create_index(op.f('ix_games_espn_game_id'), 'games', ['espn_game_id'], unique=True)
    op.create_index(op.f('ix_games_week'), 'games', ['week'], unique=False)
    op.create_index(op.f('ix_games_season'), 'games', ['season'], unique=False)
    op.create_index(op.f('ix_games_game_time'), 'games', ['game_time'], unique=False)
    op.create_index(op.f('ix_games_status'), 'games', ['status'], unique=False)
    
    # ### Create Bets table ###
    op.create_table('bets',
        sa.Column('id', sa.Integer(), nullable=False),
        
        # Foreign keys
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('game_id', sa.Integer(), nullable=False),
        
        # Bet details
        sa.Column('team_picked', sa.String(length=50), nullable=False),
        sa.Column('wager_amount', sa.Float(), nullable=False),
        sa.Column('potential_payout', sa.Float(), nullable=False),
        sa.Column('actual_payout', sa.Float(), default=0.0),
        
        # Status
        sa.Column('status', sa.String(length=20), nullable=False, default='pending'),
        
        # Timestamps
        sa.Column('placed_at', sa.DateTime(), nullable=False, default=func.now()),
        sa.Column('settled_at', sa.DateTime(), nullable=True),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.UniqueConstraint('user_id', 'game_id', name='unique_user_game_bet')
    )
    op.create_index(op.f('ix_bets_user_id'), 'bets', ['user_id'], unique=False)
    op.create_index(op.f('ix_bets_game_id'), 'bets', ['game_id'], unique=False)
    op.create_index(op.f('ix_bets_status'), 'bets', ['status'], unique=False)
    op.create_index(op.f('ix_bets_placed_at'), 'bets', ['placed_at'], unique=False)
    
    # ### Create Seasons table (for future expansion) ###
    op.create_table('seasons',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        
        # Status
        sa.Column('status', sa.String(length=20), nullable=False, default='upcoming'),
        
        # Season dates
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('playoff_start_date', sa.Date(), nullable=True),
        
        # Settings
        sa.Column('starting_balance', sa.Float(), default=10000.0),
        sa.Column('min_bet', sa.Float(), default=1.0),
        sa.Column('max_bet', sa.Float(), nullable=True),
        
        # Statistics
        sa.Column('total_users', sa.Integer(), default=0),
        sa.Column('total_bets', sa.Integer(), default=0),
        sa.Column('total_wagered', sa.Float(), default=0.0),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, default=func.now()),
        sa.Column('updated_at', sa.DateTime(), default=func.now()),
        
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('year')
    )
    
    # ### Create Transactions table (audit trail) ###
    op.create_table('transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        
        # Transaction details
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('balance_before', sa.Float(), nullable=False),
        sa.Column('balance_after', sa.Float(), nullable=False),
        
        # Reference to related bet if applicable
        sa.Column('bet_id', sa.Integer(), nullable=True),
        
        # Description for audit purposes
        sa.Column('description', sa.String(length=255), nullable=True),
        
        # Timestamp
        sa.Column('created_at', sa.DateTime(), nullable=False, default=func.now()),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['bet_id'], ['bets.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], )
    )
    op.create_index(op.f('ix_transactions_user_id'), 'transactions', ['user_id'], unique=False)
    op.create_index(op.f('ix_transactions_created_at'), 'transactions', ['created_at'], unique=False)


def downgrade():
    # ### Drop tables in reverse order ###
    op.drop_index(op.f('ix_transactions_created_at'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_user_id'), table_name='transactions')
    op.drop_table('transactions')
    
    op.drop_table('seasons')
    
    op.drop_index(op.f('ix_bets_placed_at'), table_name='bets')
    op.drop_index(op.f('ix_bets_status'), table_name='bets')
    op.drop_index(op.f('ix_bets_game_id'), table_name='bets')
    op.drop_index(op.f('ix_bets_user_id'), table_name='bets')
    op.drop_table('bets')
    
    op.drop_index(op.f('ix_games_status'), table_name='games')
    op.drop_index(op.f('ix_games_game_time'), table_name='games')
    op.drop_index(op.f('ix_games_season'), table_name='games')
    op.drop_index(op.f('ix_games_week'), table_name='games')
    op.drop_index(op.f('ix_games_espn_game_id'), table_name='games')
    op.drop_table('games')
    
    op.drop_index(op.f('ix_users_discord_id'), table_name='users')
    op.drop_table('users')