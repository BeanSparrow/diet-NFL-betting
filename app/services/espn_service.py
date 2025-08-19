"""
ESPN API Service for NFL Game Data Collection

Handles communication with ESPN's public API endpoints to fetch NFL game
data including schedules, scores, and game results.
"""
import requests
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from flask import current_app

from app.models import Game, db
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)


class ESPNAPIError(Exception):
    """Custom exception for ESPN API errors"""
    pass


class ESPNService:
    """Service class for ESPN API integration"""
    
    BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Diet-NFL-Betting/1.0',
            'Accept': 'application/json'
        })
        
        # Rate limiting
        self._last_request_time = 0
        self._min_request_interval = 1.0  # Minimum seconds between requests
        self._max_retries = 3
        self._retry_delay = 5.0  # Seconds to wait before retrying
    
    def _rate_limit(self):
        """Enforce rate limiting between API requests"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            sleep_time = self._min_request_interval - elapsed
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        self._last_request_time = time.time()
    
    def _make_request(self, url: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make rate-limited request with retry logic
        
        Args:
            url: API endpoint URL
            params: Optional query parameters
            
        Returns:
            JSON response data
            
        Raises:
            ESPNAPIError: If request fails after retries
        """
        last_exception = None
        
        for attempt in range(self._max_retries):
            try:
                self._rate_limit()
                
                logger.debug(f"ESPN API request attempt {attempt + 1}: {url}")
                response = self.session.get(url, params=params, timeout=10)
                
                # Handle rate limiting from ESPN
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', self._retry_delay))
                    logger.warning(f"ESPN API rate limited, waiting {retry_after} seconds")
                    time.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                return response.json()
                
            except requests.RequestException as e:
                last_exception = e
                if attempt < self._max_retries - 1:
                    logger.warning(f"ESPN API request failed (attempt {attempt + 1}): {e}")
                    time.sleep(self._retry_delay)
                else:
                    logger.error(f"ESPN API request failed after {self._max_retries} attempts: {e}")
        
        raise ESPNAPIError(f"Failed to fetch data after {self._max_retries} attempts: {last_exception}")
    
    def get_current_week_games(self) -> Dict[str, Any]:
        """
        Fetch current week's NFL games from ESPN API
        
        Returns:
            Dict containing games data from ESPN API
            
        Raises:
            ESPNAPIError: If API request fails
        """
        url = f"{self.BASE_URL}/scoreboard"
        return self._make_request(url)
    
    def get_games_by_week(self, year: int, week: int) -> Dict[str, Any]:
        """
        Fetch games for a specific week and year
        
        Args:
            year: NFL season year
            week: Week number (1-18 for regular season)
            
        Returns:
            Dict containing games data from ESPN API
            
        Raises:
            ESPNAPIError: If API request fails
        """
        url = f"{self.BASE_URL}/scoreboard"
        params = {
            'seasontype': 2,  # Regular season
            'week': week,
            'year': year
        }
        return self._make_request(url, params)
    
    def parse_game_data(self, espn_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse ESPN API response into standardized game data format
        
        Args:
            espn_data: Raw response from ESPN API
            
        Returns:
            List of parsed game dictionaries
        """
        games = []
        
        try:
            events = espn_data.get('events', [])
            
            for event in events:
                game_data = self._parse_single_game(event)
                if game_data:
                    games.append(game_data)
                    
        except Exception as e:
            logger.error(f"Error parsing ESPN game data: {e}")
            
        return games
    
    def _parse_single_game(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse a single game event from ESPN API
        
        Args:
            event: Single game event from ESPN API
            
        Returns:
            Parsed game dictionary or None if parsing fails
        """
        try:
            # Basic game info
            game_id = event.get('id')
            name = event.get('name', '')
            short_name = event.get('shortName', '')
            
            # Game status
            status = event.get('status', {})
            status_type = status.get('type', {}).get('name', 'Unknown')
            game_completed = status_type in ['Final', 'Final/OT']
            
            # Date/time
            date_str = event.get('date')
            if date_str:
                # Parse ISO format and convert to naive datetime for database storage
                game_date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).replace(tzinfo=None)
            else:
                game_date = None
            
            # Teams
            competitions = event.get('competitions', [])
            if not competitions:
                logger.warning(f"No competitions found for game {game_id}")
                return None
                
            competition = competitions[0]
            competitors = competition.get('competitors', [])
            
            if len(competitors) != 2:
                logger.warning(f"Expected 2 competitors for game {game_id}, got {len(competitors)}")
                return None
            
            # Parse teams
            home_team = None
            away_team = None
            home_score = None
            away_score = None
            
            for competitor in competitors:
                team = competitor.get('team', {})
                team_name = team.get('displayName', '')
                team_abbrev = team.get('abbreviation', '')
                score = int(competitor.get('score', 0))
                is_home = competitor.get('homeAway') == 'home'
                
                if is_home:
                    home_team = team_name
                    home_team_abbrev = team_abbrev
                    home_score = score
                else:
                    away_team = team_name
                    away_team_abbrev = team_abbrev
                    away_score = score
            
            # Determine winner
            winner = None
            if game_completed and home_score is not None and away_score is not None:
                if home_score > away_score:
                    winner = home_team
                elif away_score > home_score:
                    winner = away_team
                # Tie games remain winner = None
            
            return {
                'espn_game_id': game_id,
                'home_team': home_team,
                'away_team': away_team,
                'home_team_abbrev': home_team_abbrev,
                'away_team_abbrev': away_team_abbrev,
                'home_score': home_score,
                'away_score': away_score,
                'game_date': game_date,
                'status': status_type,
                'completed': game_completed,
                'winner': winner,
                'game_name': name,
                'short_name': short_name
            }
            
        except Exception as e:
            logger.error(f"Error parsing single game event: {e}")
            return None
    
    def update_games_in_database(self, games_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Update database with parsed game data
        
        Args:
            games_data: List of parsed game dictionaries
            
        Returns:
            Dict with counts of created and updated games
        """
        created_count = 0
        updated_count = 0
        
        try:
            for game_data in games_data:
                espn_game_id = game_data['espn_game_id']
                
                # Check if game exists
                existing_game = Game.query.filter_by(espn_game_id=espn_game_id).first()
                
                if existing_game:
                    # Update existing game
                    self._update_existing_game(existing_game, game_data)
                    updated_count += 1
                else:
                    # Create new game
                    self._create_new_game(game_data)
                    created_count += 1
            
            db.session.commit()
            logger.info(f"Database update complete: {created_count} created, {updated_count} updated")
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Database update failed: {e}")
            raise ESPNAPIError(f"Failed to update database: {e}")
        
        return {'created': created_count, 'updated': updated_count}
    
    def _create_new_game(self, game_data: Dict[str, Any]) -> None:
        """Create new game record in database"""
        # Extract week and season from game date
        game_date = game_data['game_date']
        current_year = game_date.year
        # NFL season spans calendar years (Sep-Feb), use year when season starts
        season_year = current_year if game_date.month >= 9 else current_year - 1
        
        # Estimate week based on date (simplified logic)
        # NFL season typically starts first week of September
        if game_date.month >= 9:
            week = ((game_date - datetime(season_year, 9, 1)).days // 7) + 1
        else:
            # January/February games (playoffs)
            week = 18 + ((game_date - datetime(season_year + 1, 1, 1)).days // 7) + 1
        
        # Map ESPN status to our status values
        status_mapping = {
            'Final': 'final',
            'Final/OT': 'final', 
            'In Progress': 'in_progress',
            'Scheduled': 'scheduled',
            'Postponed': 'postponed',
            'Cancelled': 'cancelled'
        }
        our_status = status_mapping.get(game_data['status'], 'scheduled')
        
        game = Game(
            espn_game_id=game_data['espn_game_id'],
            home_team=game_data['home_team'],
            away_team=game_data['away_team'],
            home_team_abbr=game_data['home_team_abbrev'],
            away_team_abbr=game_data['away_team_abbrev'],
            home_score=game_data['home_score'] or 0,
            away_score=game_data['away_score'] or 0,
            game_time=game_data['game_date'],
            status=our_status,
            winner=game_data['winner'],
            is_tie=(game_data['home_score'] == game_data['away_score'] and game_data['completed']),
            week=max(1, min(week, 22)),  # Clamp week between 1-22
            season=season_year,
            season_type='regular'  # Default to regular season
        )
        db.session.add(game)
    
    def _update_existing_game(self, game: Game, game_data: Dict[str, Any]) -> None:
        """Update existing game record with new data"""
        # Map ESPN status to our status values
        status_mapping = {
            'Final': 'final',
            'Final/OT': 'final', 
            'In Progress': 'in_progress',
            'Scheduled': 'scheduled',
            'Postponed': 'postponed',
            'Cancelled': 'cancelled'
        }
        our_status = status_mapping.get(game_data['status'], 'scheduled')
        
        game.home_score = game_data['home_score'] or 0
        game.away_score = game_data['away_score'] or 0
        game.status = our_status
        game.winner = game_data['winner']
        game.is_tie = (game_data['home_score'] == game_data['away_score'] and game_data['completed'])
        game.updated_at = datetime.now(timezone.utc)
    
    def fetch_and_update_current_week(self) -> Dict[str, Any]:
        """
        Fetch current week games and update database
        
        Returns:
            Dict containing operation results
        """
        try:
            logger.info("Fetching current week games from ESPN API")
            espn_data = self.get_current_week_games()
            
            games_data = self.parse_game_data(espn_data)
            logger.info(f"Parsed {len(games_data)} games from ESPN API")
            
            update_results = self.update_games_in_database(games_data)
            
            return {
                'success': True,
                'games_processed': len(games_data),
                'created': update_results['created'],
                'updated': update_results['updated']
            }
            
        except ESPNAPIError as e:
            logger.error(f"ESPN API operation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'games_processed': 0,
                'created': 0,
                'updated': 0
            }
    
    def fetch_full_season_schedule(self, year: int = None, weeks: List[int] = None) -> Dict[str, Any]:
        """
        Fetch entire season schedule (all weeks) and update database
        This is a manual admin function, not used by automatic scheduler
        
        Args:
            year: NFL season year (defaults to current year)
            weeks: List of week numbers to fetch (defaults to 1-18 for regular season)
            
        Returns:
            Dict containing operation results
        """
        import time
        
        if year is None:
            year = datetime.now().year
            
        if weeks is None:
            # Regular season weeks 1-18
            weeks = list(range(1, 19))
            
        try:
            logger.info(f"Fetching full season schedule for {year}, weeks {weeks[0]}-{weeks[-1]}")
            
            all_games_data = []
            created_total = 0
            updated_total = 0
            errors = []
            
            for week in weeks:
                try:
                    logger.info(f"Fetching week {week} of {year} season")
                    espn_data = self.get_games_by_week(year, week)
                    
                    games_data = self.parse_game_data(espn_data)
                    logger.info(f"Parsed {len(games_data)} games for week {week}")
                    
                    # Add week and season info to each game
                    for game in games_data:
                        game['week'] = week
                        game['season'] = year
                        game['season_type'] = 'regular'
                    
                    all_games_data.extend(games_data)
                    
                    # Update database for this week
                    update_results = self.update_games_in_database(games_data)
                    created_total += update_results['created']
                    updated_total += update_results['updated']
                    
                    # Brief delay between API calls to be respectful
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error fetching week {week}: {e}")
                    errors.append(f"Week {week}: {str(e)}")
                    continue
            
            logger.info(f"Full season fetch complete: {len(all_games_data)} total games")
            
            return {
                'success': len(errors) == 0,
                'partial_success': len(errors) > 0 and len(all_games_data) > 0,
                'games_processed': len(all_games_data),
                'created': created_total,
                'updated': updated_total,
                'weeks_fetched': len(weeks) - len(errors),
                'weeks_requested': len(weeks),
                'errors': errors if errors else None
            }
            
        except Exception as e:
            logger.error(f"Full season fetch failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'games_processed': 0,
                'created': 0,
                'updated': 0
            }


# Convenience function for scheduled updates
def update_nfl_games() -> Dict[str, Any]:
    """
    Convenience function for updating NFL games
    Used by scheduler and manual triggers
    """
    service = ESPNService()
    return service.fetch_and_update_current_week()