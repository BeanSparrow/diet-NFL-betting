from datetime import datetime, timedelta, timezone
from typing import Optional, List
from app import db
from sqlalchemy import func, String, Integer, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from flask import current_app

class User(db.Model):
    """User model for Discord authenticated users"""
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    discord_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(32), nullable=False)
    discriminator: Mapped[Optional[str]] = mapped_column(String(4))  # Legacy Discord discriminator
    display_name: Mapped[Optional[str]] = mapped_column(String(32))  # New Discord display name
    avatar_url: Mapped[Optional[str]] = mapped_column(String(255))
    email: Mapped[Optional[str]] = mapped_column(String(100))  # Optional, if user shares email
    
    # Betting balance
    balance: Mapped[float] = mapped_column(Float, nullable=False, default=10000.0)
    starting_balance: Mapped[float] = mapped_column(Float, nullable=False, default=10000.0)
    total_winnings: Mapped[float] = mapped_column(Float, default=0.0)
    total_losses: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Statistics
    total_bets: Mapped[int] = mapped_column(Integer, default=0)
    winning_bets: Mapped[int] = mapped_column(Integer, default=0)
    losing_bets: Mapped[int] = mapped_column(Integer, default=0)
    biggest_win: Mapped[float] = mapped_column(Float, default=0.0)
    biggest_loss: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Admin status
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_active: Mapped[Optional[datetime]] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    bets: Mapped[List['Bet']] = relationship('Bet', back_populates='user', lazy='dynamic', 
                                            cascade='all, delete-orphan')
    
    @classmethod
    def create_from_discord(cls, discord_user):
        """Create user from Discord OAuth data"""
        starting_balance = current_app.config.get('STARTING_BALANCE', 10000.0)
        
        user = cls(
            discord_id=str(discord_user.id),
            username=discord_user.username,
            discriminator=getattr(discord_user, 'discriminator', None),
            display_name=getattr(discord_user, 'display_name', None),
            avatar_url=getattr(discord_user, 'avatar_url', None),
            balance=starting_balance,
            starting_balance=starting_balance,
            last_login=datetime.now(timezone.utc)
        )
        return user
    
    def update_from_discord(self, discord_user):
        """Update user from Discord OAuth data"""
        self.username = discord_user.username
        self.discriminator = getattr(discord_user, 'discriminator', None)
        self.display_name = getattr(discord_user, 'display_name', None)
        self.avatar_url = getattr(discord_user, 'avatar_url', None)
        self.last_login = datetime.now(timezone.utc)
    
    @property
    def win_percentage(self):
        """Calculate win percentage with data validation"""
        if self.total_bets == 0:
            return 0.0
        
        # Ensure data integrity
        actual_total = self.winning_bets + self.losing_bets
        if actual_total != self.total_bets and actual_total > 0:
            # Use the sum of winning + losing bets if they don't match total_bets
            # This handles data inconsistency gracefully
            effective_total = actual_total
        else:
            effective_total = self.total_bets
        
        if effective_total == 0:
            return 0.0
            
        percentage = (self.winning_bets / effective_total) * 100
        # Cap at 100% to prevent impossible percentages
        return min(percentage, 100.0)
    
    @property
    def profit_loss(self):
        """Calculate total profit/loss"""
        return self.balance - self.starting_balance
    
    def validate_bet_counts(self):
        """Validate that bet counts are consistent"""
        return self.winning_bets + self.losing_bets == self.total_bets
    
    def fix_bet_counts(self):
        """Fix inconsistent bet counts by recalculating total_bets"""
        if not self.validate_bet_counts():
            self.total_bets = self.winning_bets + self.losing_bets
    
    def __repr__(self):
        return f'<User {self.username}#{self.discriminator}>'


class Game(db.Model):
    """NFL game model"""
    __tablename__ = 'games'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    espn_game_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    
    # Schedule information
    week: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    season: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    season_type: Mapped[str] = mapped_column(String(20), default='regular')  # regular, preseason, postseason
    
    # Teams
    home_team: Mapped[str] = mapped_column(String(50), nullable=False)
    home_team_abbr: Mapped[Optional[str]] = mapped_column(String(5))
    away_team: Mapped[str] = mapped_column(String(50), nullable=False)
    away_team_abbr: Mapped[Optional[str]] = mapped_column(String(5))
    
    # Game timing
    game_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    quarter: Mapped[Optional[str]] = mapped_column(String(10))  # Current quarter if in progress
    time_remaining: Mapped[Optional[str]] = mapped_column(String(10))  # Time remaining in quarter
    
    # Status
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='scheduled', index=True)
    # Status values: scheduled, in_progress, final, postponed, cancelled
    
    # Scores
    home_score: Mapped[int] = mapped_column(Integer, default=0)
    away_score: Mapped[int] = mapped_column(Integer, default=0)
    
    # Results
    winner: Mapped[Optional[str]] = mapped_column(String(50))  # Team name of winner, NULL if tie or not finished
    is_tie: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Betting information
    total_bets: Mapped[int] = mapped_column(Integer, default=0)
    total_wagered: Mapped[float] = mapped_column(Float, default=0.0)
    home_bets: Mapped[int] = mapped_column(Integer, default=0)
    away_bets: Mapped[int] = mapped_column(Integer, default=0)
    home_wagered: Mapped[float] = mapped_column(Float, default=0.0)
    away_wagered: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    bets: Mapped[List['Bet']] = relationship('Bet', back_populates='game', lazy='dynamic',
                                           cascade='all, delete-orphan')
    
    @property
    def is_bettable(self):
        """Check if game is still open for betting (closes 5 minutes before game start)"""
        # Handle both naive and aware datetimes
        if self.game_time.tzinfo is None:
            # If game_time is naive, assume it's UTC
            cutoff_time = self.game_time.replace(tzinfo=timezone.utc) - timedelta(minutes=5)
        else:
            cutoff_time = self.game_time - timedelta(minutes=5)
        return self.status == 'scheduled' and datetime.now(timezone.utc) < cutoff_time
    
    @property
    def home_bet_percentage(self):
        """Calculate percentage of bets on home team"""
        if self.total_bets == 0:
            return 0.0
        return (self.home_bets / self.total_bets) * 100
    
    @property
    def away_bet_percentage(self):
        """Calculate percentage of bets on away team"""
        if self.total_bets == 0:
            return 0.0
        return (self.away_bets / self.total_bets) * 100
    
    def calculate_team_wagered_amounts(self):
        """Calculate home_wagered and away_wagered from actual bets"""
        from sqlalchemy import func
        
        # Calculate home wagered amount
        home_wagered = db.session.query(func.sum(Bet.wager_amount)).filter(
            Bet.game_id == self.id,
            Bet.team_picked == self.home_team,
            Bet.status.in_(['pending', 'won', 'lost', 'push'])
        ).scalar() or 0.0
        
        # Calculate away wagered amount  
        away_wagered = db.session.query(func.sum(Bet.wager_amount)).filter(
            Bet.game_id == self.id,
            Bet.team_picked == self.away_team,
            Bet.status.in_(['pending', 'won', 'lost', 'push'])
        ).scalar() or 0.0
        
        return home_wagered, away_wagered
    
    def __repr__(self):
        return f'<Game {self.away_team} @ {self.home_team} - Week {self.week}>'


class Bet(db.Model):
    """User bet model"""
    __tablename__ = 'bets'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Foreign keys
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    game_id: Mapped[int] = mapped_column(ForeignKey('games.id'), nullable=False, index=True)
    
    # Bet details
    team_picked: Mapped[str] = mapped_column(String(50), nullable=False)
    wager_amount: Mapped[float] = mapped_column(Float, nullable=False)
    potential_payout: Mapped[float] = mapped_column(Float, nullable=False)
    actual_payout: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='pending', index=True)
    # Status values: pending, won, lost, push (tie), cancelled
    
    # Timestamps
    placed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    settled_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    user: Mapped['User'] = relationship('User', back_populates='bets')
    game: Mapped['Game'] = relationship('Game', back_populates='bets')
    
    # Note: Removed unique constraint to allow users to place new bets 
    # on games where they previously cancelled bets. Duplicate validation 
    # is now handled at the application level to only prevent pending duplicates.
    
    def calculate_payout(self, multiplier=2.0):
        """Calculate potential payout based on wager"""
        self.potential_payout = self.wager_amount * multiplier
    
    def settle(self, winner):
        """Settle the bet based on game outcome"""
        if winner is None:  # Game ended in tie
            self.status = 'push'
            self.actual_payout = self.wager_amount  # Return original wager
        elif self.team_picked == winner:
            self.status = 'won'
            self.actual_payout = self.potential_payout
        else:
            self.status = 'lost'
            self.actual_payout = 0.0
        
        self.settled_at = datetime.now(timezone.utc)
    
    def __repr__(self):
        return f'<Bet User:{self.user_id} Game:{self.game_id} ${self.wager_amount}>'


class Season(db.Model):
    """Season tracking model for future expansion"""
    __tablename__ = 'seasons'
    
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, unique=True, nullable=False)
    
    # Status
    status = db.Column(db.String(20), nullable=False, default='upcoming')
    # Status values: upcoming, active, completed
    
    # Season dates
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    playoff_start_date = db.Column(db.Date)
    
    # Settings
    starting_balance = db.Column(db.Float, default=10000.0)
    min_bet = db.Column(db.Float, default=1.0)
    max_bet = db.Column(db.Float)  # Optional max bet limit
    
    # Statistics
    total_users = db.Column(db.Integer, default=0)
    total_bets = db.Column(db.Integer, default=0)
    total_wagered = db.Column(db.Float, default=0.0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    @property
    def is_active(self):
        """Check if season is currently active"""
        return self.status == 'active'
    
    def __repr__(self):
        return f'<Season {self.year} - {self.status}>'


class Transaction(db.Model):
    """Transaction log for audit trail"""
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Transaction details
    type = db.Column(db.String(20), nullable=False)
    # Types: deposit, withdrawal, bet_placed, bet_won, bet_lost, bet_push, adjustment
    
    amount = db.Column(db.Float, nullable=False)
    balance_before = db.Column(db.Float, nullable=False)
    balance_after = db.Column(db.Float, nullable=False)
    
    # Reference to related bet if applicable
    bet_id = db.Column(db.Integer, db.ForeignKey('bets.id'))
    
    # Description for audit purposes
    description = db.Column(db.String(255))
    
    # Timestamp
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    
    def __repr__(self):
        return f'<Transaction {self.type} ${self.amount} User:{self.user_id}>'


# Flask-Discord user session helpers
def get_current_user():
    """Get current user from session"""
    from flask import session
    if 'discord_user_id' not in session:
        return None
    return User.query.filter_by(discord_id=session['discord_user_id']).first()