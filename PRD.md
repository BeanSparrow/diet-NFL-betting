# Diet NFL Betting Service - Product Requirements Document

## Project Overview

A play money NFL betting system that integrates with Discord for user authentication and community engagement, while providing a web-based interface for placing bets and viewing statistics.

## Project Goals

- Create an engaging, fun betting experience for Discord community members
- Provide a simple win/loss pick system for NFL games
- Build expandable infrastructure for future betting types and seasons
- Maintain user engagement throughout the NFL season

## Target Users

- Discord server members (up to 50 users initially)
- NFL fans who enjoy friendly competition
- Users comfortable with web-based interfaces

## Core Features

### 1. User Management
- **Discord OAuth Authentication**: Users log in using their Discord accounts
- **Play Money System**: Each user starts with a set amount of play money per season
- **Balance Tracking**: Persistent balance throughout the season
- **User Profiles**: Display betting history, win/loss record, and statistics

### 2. Betting System
- **Game Selection**: Users can bet on any upcoming NFL game
- **Win/Loss Picks**: Simple team selection (no point spreads initially)
- **Wager Amounts**: Users can bet any amount > 0 up to their current balance
- **Payout Structure**: Double or nothing (2:1 payout for winning bets)
- **Bet Validation**: Prevent betting after games start

### 3. Game Data Management
- **Automated Data Collection**: ESPN API integration for game schedules and results
- **Real-time Updates**: Automatic score checking and bet settlement
- **Weekly Schedule**: Display upcoming games with betting deadlines
- **Historical Data**: Store all game results for statistics

### 4. Website Features
- **Dashboard**: User balance, active bets, recent results
- **Betting Interface**: Clean, intuitive game selection and wagering
- **Leaderboard**: Rankings by balance, win percentage, total winnings
- **Statistics**: Individual and community betting analytics
- **Betting History**: Complete record of all user bets

### 5. Discord Integration
- **Authentication**: Discord OAuth for seamless login
- **Announcements**: Automated posting of weekly games and results
- **Community Engagement**: Links back to Discord for discussion

## Technical Specifications

### Architecture
- **Frontend**: Flask web application with HTML/CSS/JavaScript
- **Backend**: Python Flask with SQLAlchemy ORM
- **Database**: SQLite for development, PostgreSQL for production
- **Authentication**: Discord OAuth 2.0
- **Data Source**: ESPN unofficial API
- **Hosting**: Local development → VPS deployment

### Database Schema

#### Users Table
- `id`: Primary key
- `discord_id`: Unique Discord user ID
- `username`: Discord username
- `discriminator`: Discord discriminator
- `avatar_url`: Discord avatar URL
- `balance`: Current play money balance
- `starting_balance`: Initial season balance
- `created_at`: Account creation timestamp
- `last_login`: Last login timestamp

#### Games Table
- `id`: Primary key
- `espn_game_id`: ESPN API game identifier
- `week`: NFL week number
- `season`: NFL season year
- `home_team`: Home team name/abbreviation
- `away_team`: Away team name/abbreviation
- `game_time`: Scheduled game start time
- `status`: Game status (scheduled, in_progress, final)
- `home_score`: Final home team score
- `away_score`: Final away team score
- `winner`: Winning team (null if tie/in progress)
- `created_at`: Record creation timestamp
- `updated_at`: Last update timestamp

#### Bets Table
- `id`: Primary key
- `user_id`: Foreign key to Users table
- `game_id`: Foreign key to Games table
- `team_picked`: Team user bet on
- `wager_amount`: Amount wagered
- `potential_payout`: Potential winnings (wager_amount * 2)
- `actual_payout`: Actual payout received (0 if loss)
- `status`: Bet status (pending, won, lost, push)
- `placed_at`: Bet placement timestamp
- `settled_at`: Bet settlement timestamp

#### Seasons Table (Future Expansion)
- `id`: Primary key
- `year`: Season year
- `status`: Season status (active, completed)
- `start_date`: Season start date
- `end_date`: Season end date

### API Endpoints

#### Authentication
- `GET /`: Home page (redirects to login if not authenticated)
- `GET /login`: Discord OAuth initiation
- `GET /callback`: Discord OAuth callback handler
- `GET /logout`: User logout

#### Betting
- `GET /dashboard`: User dashboard with balance and active bets
- `GET /games`: Current week's games available for betting
- `GET /games/week/<int:week>`: Specific week's games
- `POST /bet`: Place a new bet
- `GET /bets`: User's betting history
- `GET /bets/<int:bet_id>`: Specific bet details

#### Statistics
- `GET /leaderboard`: Community leaderboard
- `GET /stats`: Community statistics
- `GET /profile/<discord_id>`: User profile and stats

#### Admin (Future)
- `GET /admin`: Admin dashboard
- `POST /admin/settle-bets`: Manual bet settlement
- `POST /admin/update-games`: Manual game data refresh

### Data Flow

1. **Game Data Collection**: Scheduled job fetches weekly NFL schedule from ESPN API
2. **User Authentication**: Discord OAuth provides user identity and profile data
3. **Bet Placement**: Users select games and wager amounts through web interface
4. **Bet Validation**: System checks user balance and game availability
5. **Game Monitoring**: Scheduled job monitors game results via ESPN API
6. **Bet Settlement**: Automatic payout calculation and balance updates
7. **Statistics Update**: Real-time leaderboard and statistics updates

## Development Phases

### Phase 1: Core Infrastructure (Weeks 1-2)
- Set up Flask application structure
- Implement Discord OAuth authentication
- Create basic database models and migrations
- Build simple user dashboard

### Phase 2: Betting System (Weeks 3-4)
- ESPN API integration for game data
- Betting interface and logic
- Bet validation and storage
- Basic game result processing

### Phase 3: User Experience (Weeks 5-6)
- Responsive web design
- Leaderboard and statistics
- Betting history and user profiles
- Error handling and user feedback

### Phase 4: Automation & Polish (Weeks 7-8)
- Automated game data updates
- Automated bet settlement
- Discord announcements
- Testing and bug fixes

### Phase 5: Deployment (Week 9)
- Production database setup
- VPS deployment
- Domain configuration
- User acceptance testing

## Success Metrics

- **User Engagement**: > 80% of server members create accounts
- **Retention**: > 60% of users place bets in weeks 2-4
- **Technical Performance**: < 2 second page load times
- **Data Accuracy**: 100% accurate game results and bet settlements
- **System Reliability**: > 99% uptime during peak usage

## Risk Assessment

### Technical Risks
- **ESPN API Changes**: Unofficial API could change without notice
  - *Mitigation*: Monitor API regularly, have backup data sources identified
- **Discord OAuth Issues**: Authentication failures
  - *Mitigation*: Implement proper error handling and fallback options
- **Database Performance**: Potential slowdowns with concurrent users
  - *Mitigation*: Optimize queries, implement connection pooling

### Business Risks
- **Low User Adoption**: Users may not engage with the system
  - *Mitigation*: Simple onboarding, engaging features, community promotion
- **Feature Creep**: Overcomplicating initial version
  - *Mitigation*: Stick to core features, plan future enhancements separately

### Security Risks
- **User Data Protection**: Handling Discord user information
  - *Mitigation*: Minimal data storage, secure authentication flow
- **System Security**: Potential vulnerabilities in web application
  - *Mitigation*: Input validation, secure coding practices, regular updates

## Future Enhancements

### Season 2 Features
- **Point Spreads**: Betting against the spread
- **Over/Under**: Total points betting
- **Parlay Bets**: Multiple game combinations
- **Live Betting**: In-game wagering options

### Advanced Features
- **Mobile App**: Native mobile application
- **Social Features**: Friend challenges, group betting
- **Advanced Statistics**: Detailed analytics and insights
- **Playoff Tournaments**: Special playoff betting formats

### Technical Improvements
- **Real-time Updates**: WebSocket connections for live updates
- **Performance Optimization**: Caching, CDN integration
- **Multi-server Support**: Support for multiple Discord servers
- **API Documentation**: Public API for third-party integrations

## Conclusion

The Diet NFL Betting Service will provide an engaging, community-driven betting experience that enhances Discord server interaction while maintaining simplicity and reliability. The phased development approach ensures a solid foundation that can be expanded with additional features based on user feedback and engagement.
