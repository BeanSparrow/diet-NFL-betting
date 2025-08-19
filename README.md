# 🏈 Diet NFL Betting Service

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-Educational-orange.svg)](#license)
[![Deployment](https://img.shields.io/badge/Deploy-Heroku-purple.svg)](https://heroku.com)

A modern, play-money NFL betting platform with Discord authentication, real-time ESPN data integration, and comprehensive user experience features. Built for community engagement and friendly competition.

![Diet NFL Betting Service Dashboard](https://via.placeholder.com/800x400/1a1a1a/ffffff?text=Diet+NFL+Betting+Dashboard)

## ✨ Features

### 🎯 **Core Functionality**
- **Discord OAuth Authentication** - Seamless login with Discord accounts
- **Play Money Betting** - $10,000 starting balance, no real money involved
- **Live NFL Data** - Real-time game updates via ESPN API
- **Smart Betting System** - Win/loss predictions with 2x payout multiplier
- **5-Minute Cutoff** - Betting closes 5 minutes before game start

### 🎮 **User Experience**
- **Interactive Dashboard** - View pending bets, balance, and statistics
- **Betting History** - Complete history with filtering and pagination
- **Bet Cancellation** - Cancel pending bets with full refunds
- **Community Leaderboard** - Rankings and community statistics
- **Responsive Design** - Mobile-friendly interface with TailwindCSS

### 🔧 **Technical Features**
- **Automated Settlement** - Bets settle automatically when games complete
- **Transaction Integrity** - Atomic database operations with rollback protection
- **Error Handling** - Comprehensive error pages and user feedback
- **Production Ready** - PostgreSQL support, Heroku deployment configured

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Discord Application ([Create one here](https://discord.com/developers/applications))
- PostgreSQL (production) or SQLite (development)

### Installation

1. **Clone and Setup**
   ```bash
   git clone https://github.com/yourusername/diet-nfl-betting.git
   cd diet-nfl-betting
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your Discord OAuth credentials
   ```

3. **Database Setup**
   ```bash
   flask db upgrade
   ```

4. **Run Development Server**
   ```bash
   python run.py
   ```

   Visit `http://localhost:5000` to access the application.

### Discord OAuth Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Navigate to **OAuth2 → General**
4. Add redirect URI: `http://localhost:5000/callback`
5. Copy **Client ID** and **Client Secret** to your `.env` file

## 📊 Project Structure

```
diet-nfl-betting/
├── 📁 app/
│   ├── 🐍 __init__.py              # Flask application factory
│   ├── 🗃️ models.py                # Database models (User, Game, Bet)
│   ├── 🔐 auth.py                  # Discord OAuth implementation
│   ├── 🌐 routes/                  # Route blueprints
│   │   ├── main.py                 # Dashboard and main pages
│   │   ├── betting.py              # Betting interface
│   │   ├── auth.py                 # Authentication routes
│   │   └── api.py                  # REST API endpoints
│   ├── ⚙️ services/                # Business logic layer
│   │   ├── bet_service.py          # Betting validation and processing
│   │   ├── espn_service.py         # ESPN API integration
│   │   └── settlement_service.py   # Automated bet settlement
│   ├── 🎨 templates/               # Jinja2 HTML templates
│   └── 📎 static/                  # CSS, JavaScript, images
├── 🔄 migrations/                  # Database migrations
├── 🧪 tests/                       # Comprehensive test suite
├── 📊 scripts/                     # Development utilities
├── ⚙️ config.py                    # Application configuration
├── 📋 requirements.txt             # Python dependencies
└── 🚀 run.py                       # Application entry point
```

## 🎯 User Journey

### New User Experience
1. **Discord Login** → Seamless OAuth authentication
2. **Welcome Dashboard** → $10,000 starting balance
3. **Browse Games** → View upcoming NFL games with odds
4. **Place Bets** → Simple win/loss predictions
5. **Track Progress** → Real-time updates and history

### Betting Flow
1. **Game Selection** → Choose from upcoming NFL games
2. **Team Pick** → Select winning team
3. **Wager Amount** → Set bet amount (min $1)
4. **Confirmation** → Review and confirm bet
5. **Auto Settlement** → Automatic payout when game completes

## 🏆 Milestone Achievements

- ✅ **M1: Core Infrastructure** - Flask app with Discord OAuth and database models
- ✅ **M2: Betting System** - ESPN integration, bet placement, and validation
- ✅ **M3: Settlement & Leaderboard** - Automated settlement and community features  
- ✅ **M4: User Experience** - Dashboard enhancements, history, and bet management
- 🎯 **Ready for Production** - PostgreSQL migration, Heroku deployment configured

## 🛠️ Development

### Running Tests
```bash
pytest tests/ -v
```

### Database Management
```bash
# Create migration
flask db migrate -m "Description"

# Apply migrations
flask db upgrade

# Clear data for production
python clear_data_auto.py
```

### Development Scripts
- `scripts/simulate_betting.py` - Generate test betting activity
- `scripts/manual_betting.py` - Interactive betting control
- `scripts/show_betting_options.py` - System status overview

## 🌐 API Reference

### Authentication Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/login` | Discord OAuth login |
| GET | `/callback` | OAuth callback handler |
| GET | `/logout` | User logout |

### Betting Endpoints  
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/betting/games` | Available games |
| POST | `/betting/place/<game_id>` | Place bet |
| GET | `/betting/history` | Betting history |
| POST | `/betting/cancel/<bet_id>` | Cancel pending bet |

### API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/user/balance` | Current user balance |
| GET | `/api/games/upcoming` | Upcoming games |
| GET | `/api/leaderboard` | Community rankings |

## 🚀 Production Deployment

### Heroku Deployment
1. **Prerequisites**: Heroku account and CLI installed
2. **Quick Deploy**: 
   ```bash
   heroku create your-app-name
   heroku addons:create heroku-postgresql:mini
   git push heroku main
   ```
3. **Configuration**: Set environment variables for Discord OAuth
4. **Cost**: ~$7/month for basic deployment

See [`HEROKU_DEPLOYMENT_GUIDE.md`](HEROKU_DEPLOYMENT_GUIDE.md) for detailed instructions.

### Environment Variables
| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | ✅ | Flask session secret |
| `DATABASE_URL` | ✅ | PostgreSQL connection URL |
| `DISCORD_CLIENT_ID` | ✅ | Discord OAuth client ID |
| `DISCORD_CLIENT_SECRET` | ✅ | Discord OAuth client secret |
| `FLASK_ENV` | ✅ | Set to `production` |

## 🔒 Security Features

- **Discord OAuth** for secure authentication
- **HTTPS Enforcement** in production environments
- **CSRF Protection** on all forms
- **Input Validation** and sanitization
- **SQL Injection Prevention** via SQLAlchemy ORM
- **Session Security** with secure cookie settings
- **Transaction Integrity** with atomic database operations

## 🧪 Testing

Comprehensive test suite with 95%+ coverage:
- **Unit Tests** - Individual component testing
- **Integration Tests** - End-to-end workflows  
- **API Tests** - REST endpoint validation
- **Database Tests** - Data integrity verification
- **Authentication Tests** - OAuth flow testing

## 📈 Performance

- **Database Optimization** - Connection pooling for PostgreSQL
- **Caching Strategy** - Session-based caching for user data
- **API Efficiency** - ESPN data fetched via scheduled tasks
- **Responsive Design** - Optimized for mobile and desktop

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guidelines
- Write tests for new features
- Update documentation as needed
- Use meaningful commit messages

## 📄 License

This project is for **educational and entertainment purposes only**. 

⚠️ **No Real Money Gambling** - This application uses play money only and is not intended for real money gambling. Please gamble responsibly and follow local laws regarding gambling activities.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/diet-nfl-betting/issues)
- **Documentation**: Check the [`HEROKU_DEPLOYMENT_GUIDE.md`](HEROKU_DEPLOYMENT_GUIDE.md)
- **Discord Setup**: [Discord Developer Portal Guide](https://discord.com/developers/docs/topics/oauth2)

## 🙏 Acknowledgments

- **ESPN** for providing free NFL game data
- **Discord** for OAuth authentication services  
- **Flask** community for excellent documentation
- **Heroku** for accessible cloud deployment
- **TailwindCSS** for responsive design framework

---

<div align="center">
  <p><strong>Built with ❤️ for the NFL community</strong></p>
  <p>🏈 Ready to make some (play money) bets? Let's go! 🏈</p>
</div>