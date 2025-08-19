# Diet NFL Betting Service

A play-money NFL betting system integrated with Discord for community engagement.

## Features

- Discord OAuth authentication
- Play money betting system ($10,000 starting balance)
- Simple win/loss picks for NFL games
- Real-time game data from ESPN
- Community leaderboard and statistics
- Responsive web interface

## Quick Start

### Prerequisites

- Python 3.8+
- Discord Application (for OAuth)
- SQLite (development) or PostgreSQL (production)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd diet-nfl-betting
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your Discord OAuth credentials
```

4. Initialize the database:
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

5. Seed test data:
```bash
python seed_test_data.py
```

6. Add upcoming games (for testing):
```bash
python scripts/add_upcoming_games.py
```

7. Run the application:
```bash
python run.py
```

The application will be available at `http://localhost:5000`

## Discord Setup

1. Create a Discord Application at https://discord.com/developers/applications
2. Go to OAuth2 → General
3. Add redirect URL: `http://localhost:5000/callback` (development)
4. Copy Client ID and Client Secret to `.env`

## Project Structure

```
diet-nfl-betting/
├── app/
│   ├── __init__.py          # Flask app initialization
│   ├── models.py             # Database models
│   ├── auth.py               # Discord OAuth
│   ├── routes/               # Route blueprints
│   ├── services/             # Business logic
│   ├── templates/            # HTML templates
│   └── static/              # CSS, JS, images
├── migrations/              # Database migrations
├── scripts/                 # Testing & development tools
├── tests/                   # Test suite
├── config.py                # Configuration
├── requirements.txt         # Dependencies
└── run.py                   # Entry point
```

## Development Phases

- ✅ **Phase 1**: Core Infrastructure
  - Flask setup and project structure
  - Discord OAuth authentication
  - Database models (User, Game, Bet)
  - Basic dashboard and templates

- ⏳ **Phase 2**: Betting System
  - ESPN API integration
  - Betting interface and logic
  - Bet validation and storage
  - Game result processing

- ⏳ **Phase 3**: User Experience
  - Responsive web design
  - Leaderboard and statistics
  - User profiles and history
  - Error handling

- ⏳ **Phase 4**: Automation
  - Scheduled game updates
  - Automated bet settlement
  - Discord announcements
  - Testing

- ⏳ **Phase 5**: Deployment
  - Production database
  - VPS deployment
  - Domain and SSL setup
  - User acceptance testing

## Testing & Development

### Testing Scripts

The `scripts/` directory contains useful development tools:

- **`simulate_betting.py`** - Automated betting simulation
- **`manual_betting.py`** - Interactive betting control
- **`add_upcoming_games.py`** - Add test games
- **`show_betting_options.py`** - System status overview

### Run Tests

```bash
pytest tests/
```

### Simulate Betting Activity

```bash
python scripts/simulate_betting.py
```

See `scripts/README.md` for detailed documentation.

## Configuration

Key configuration options in `config.py`:

- `STARTING_BALANCE`: Initial play money amount (default: $10,000)
- `MIN_BET_AMOUNT`: Minimum bet allowed (default: $1)
- `PAYOUT_MULTIPLIER`: Payout ratio for wins (default: 2.0)
- `DISCORD_CLIENT_ID`: Your Discord app client ID
- `DISCORD_CLIENT_SECRET`: Your Discord app client secret

## API Endpoints

### Authentication
- `GET /login` - Discord OAuth login
- `GET /callback` - OAuth callback
- `GET /logout` - User logout

### Betting
- `GET /betting/games` - View available games
- `POST /betting/place/<game_id>` - Place a bet
- `GET /betting/history` - User betting history

### Statistics
- `GET /stats/leaderboard` - Community rankings
- `GET /stats/community` - Overall statistics
- `GET /stats/profile/<discord_id>` - User profile

### API
- `GET /api/user/balance` - Get user balance
- `GET /api/games/upcoming` - Upcoming games
- `GET /api/leaderboard` - Leaderboard data

## Security

- Discord OAuth for authentication
- Session-based authentication
- CSRF protection
- Input validation
- SQL injection prevention via SQLAlchemy ORM

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is for educational and entertainment purposes only. No real money gambling.

## Support

For issues or questions, please open an issue on GitHub.