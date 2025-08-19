"""
APScheduler Service for Diet NFL Betting Service

Handles automated scheduling of tasks including:
- Periodic ESPN data fetching
- Game status updates
- Basic scheduling operations

Follows scope requirements:
- Must implement: APScheduler setup, periodic ESPN data fetch, game status updates, basic scheduling
- Must NOT implement: complex scheduling, distributed tasks, real-time websockets
"""

import logging
from typing import Optional, List, Dict, Any
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from flask import Flask, current_app
import pytz

logger = logging.getLogger(__name__)


class SchedulerService:
    """
    Service class for managing APScheduler integration with Flask app.
    
    Provides automated task scheduling capabilities for ESPN data updates
    and other periodic operations required by the betting system.
    """
    
    def __init__(self, app: Optional[Flask] = None):
        """
        Initialize scheduler service.
        
        Args:
            app: Optional Flask application instance
        """
        self.app = app
        self.scheduler = None
        self._running = False
        
        if app is not None:
            self.init_app(app)
        else:
            # Set up scheduler even without app for testing
            self._setup_scheduler()
    
    def init_app(self, app: Flask) -> None:
        """
        Initialize scheduler with Flask app (factory pattern support).
        
        Args:
            app: Flask application instance
        """
        self.app = app
        self._setup_scheduler()
    
    def _setup_scheduler(self) -> None:
        """Set up APScheduler with appropriate configuration"""
        # Get timezone from app config or default to UTC
        timezone = 'UTC'
        if self.app:
            timezone = self.app.config.get('SCHEDULER_TIMEZONE', 'UTC')
        
        # Configure job stores
        jobstores = {
            'default': MemoryJobStore()
        }
        
        # Configure executors
        executors = {
            'default': ThreadPoolExecutor(20)
        }
        
        # Scheduler configuration
        job_defaults = {
            'coalesce': True,  # Combine multiple pending executions
            'max_instances': 1,  # Only one instance of each job at a time
            'misfire_grace_time': 300  # 5 minutes grace period for missed jobs
        }
        
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=pytz.timezone(timezone)
        )
        
        # Add event listeners for logging
        self.scheduler.add_listener(self._job_executed_listener, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error_listener, EVENT_JOB_ERROR)
    
    def _job_executed_listener(self, event) -> None:
        """Log successful job executions"""
        logger.info(f"Job '{event.job_id}' executed successfully")
    
    def _job_error_listener(self, event) -> None:
        """Log job execution errors"""
        logger.error(f"Job '{event.job_id}' failed: {event.exception}")
    
    def start(self) -> None:
        """Start the scheduler"""
        if not self.scheduler:
            self._setup_scheduler()
        
        if not self._running:
            try:
                self.scheduler.start()
                self._running = True
                logger.info("Scheduler started successfully")
            except Exception as e:
                logger.error(f"Failed to start scheduler: {e}")
                raise
    
    def shutdown(self, wait: bool = True) -> None:
        """
        Shutdown the scheduler
        
        Args:
            wait: Whether to wait for running jobs to complete
        """
        if self._running and self.scheduler:
            try:
                self.scheduler.shutdown(wait=wait)
                self._running = False
                logger.info("Scheduler shut down successfully")
            except Exception as e:
                logger.error(f"Error shutting down scheduler: {e}")
    
    def is_running(self) -> bool:
        """Check if scheduler is currently running"""
        return self._running and self.scheduler is not None and self.scheduler.running
    
    def add_espn_update_job(self, job_id: str, interval_minutes: int) -> Any:
        """
        Add ESPN data update job to scheduler
        
        Args:
            job_id: Unique identifier for the job
            interval_minutes: How often to run the job (in minutes)
            
        Returns:
            Scheduled job instance
            
        Raises:
            ValueError: If parameters are invalid
        """
        if not job_id or job_id.strip() == '':
            raise ValueError("Job ID cannot be empty")
        
        if interval_minutes <= 0:
            raise ValueError("Interval must be positive")
        
        if not self.scheduler:
            self._setup_scheduler()
        
        # Import here to avoid circular imports
        from app.services.espn_service import update_nfl_games
        
        # Wrap the ESPN update function to handle exceptions
        def safe_espn_update():
            """Wrapper for ESPN update with exception handling"""
            try:
                logger.info(f"Starting ESPN update job '{job_id}'")
                result = update_nfl_games()
                
                if result.get('success'):
                    logger.info(f"ESPN update completed: {result.get('games_processed', 0)} games processed")
                else:
                    logger.warning(f"ESPN update failed: {result.get('error', 'Unknown error')}")
                
                return result
                
            except Exception as e:
                logger.error(f"Exception in ESPN update job '{job_id}': {e}")
                return {'success': False, 'error': str(e)}
        
        # Add the job (replace if exists)
        job = self.scheduler.add_job(
            func=safe_espn_update,
            trigger='interval',
            minutes=interval_minutes,
            id=job_id,
            name=f"ESPN Game Updates ({interval_minutes}min)",
            replace_existing=True
        )
        
        logger.info(f"Added ESPN update job '{job_id}' with {interval_minutes}-minute interval")
        return job
    
    def add_settlement_job(self, job_id: str, interval_minutes: int) -> Any:
        """
        Add bet settlement job to scheduler
        
        Args:
            job_id: Unique identifier for the job
            interval_minutes: How often to run settlement (in minutes)
            
        Returns:
            Scheduled job instance
            
        Raises:
            ValueError: If parameters are invalid
        """
        if not job_id or job_id.strip() == '':
            raise ValueError("Job ID cannot be empty")
        
        if interval_minutes <= 0:
            raise ValueError("Interval must be positive")
        
        if not self.scheduler:
            self._setup_scheduler()
        
        # Import here to avoid circular imports
        from app.services.settlement_service import settle_completed_games
        
        # Wrap the settlement function to handle exceptions
        def safe_settlement():
            """Wrapper for settlement with exception handling"""
            try:
                logger.info(f"Starting settlement job '{job_id}'")
                result = settle_completed_games()
                
                if result.get('success'):
                    logger.info(f"Settlement completed: {result.get('bets_settled', 0)} bets settled")
                else:
                    logger.warning(f"Settlement failed: {result.get('error', 'Unknown error')}")
                
                return result
                
            except Exception as e:
                logger.error(f"Exception in settlement job '{job_id}': {e}")
                return {'success': False, 'error': str(e)}
        
        # Add the job (replace if exists)
        job = self.scheduler.add_job(
            func=safe_settlement,
            trigger='interval',
            minutes=interval_minutes,
            id=job_id,
            name=f"Bet Settlement ({interval_minutes}min)",
            replace_existing=True
        )
        
        logger.info(f"Added settlement job '{job_id}' with {interval_minutes}-minute interval")
        return job
    
    def remove_job(self, job_id: str) -> bool:
        """
        Remove job from scheduler
        
        Args:
            job_id: ID of job to remove
            
        Returns:
            True if job was removed, False if job didn't exist
        """
        if not self.scheduler:
            return False
        
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed job '{job_id}'")
            return True
        except Exception:
            logger.warning(f"Job '{job_id}' not found for removal")
            return False
    
    def get_jobs(self) -> List[Any]:
        """
        Get list of all scheduled jobs
        
        Returns:
            List of scheduled job instances
        """
        if not self.scheduler:
            return []
        
        return self.scheduler.get_jobs()
    
    def get_job_info(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific job
        
        Args:
            job_id: ID of job to query
            
        Returns:
            Job information dictionary or None if not found
        """
        if not self.scheduler:
            return None
        
        job = self.scheduler.get_job(job_id)
        if not job:
            return None
        
        return {
            'id': job.id,
            'name': job.name,
            'next_run_time': job.next_run_time,
            'trigger': str(job.trigger),
            'executor': job.executor,
            'max_instances': job.max_instances
        }
    
    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.shutdown()


# Global scheduler instance for app factory pattern
_scheduler_instance = None


def init_scheduler(app: Flask) -> SchedulerService:
    """
    Initialize scheduler service for the Flask app
    
    Args:
        app: Flask application instance
        
    Returns:
        SchedulerService instance
    """
    global _scheduler_instance
    
    if _scheduler_instance is None:
        _scheduler_instance = SchedulerService(app)
    else:
        _scheduler_instance.init_app(app)
    
    return _scheduler_instance


def get_scheduler() -> Optional[SchedulerService]:
    """
    Get the current scheduler instance
    
    Returns:
        SchedulerService instance or None if not initialized
    """
    return _scheduler_instance


def setup_default_jobs(scheduler: SchedulerService) -> None:
    """
    Set up default scheduled jobs for the application
    
    Args:
        scheduler: SchedulerService instance to configure
    """
    try:
        # Add default ESPN game update job (every 15 minutes)
        scheduler.add_espn_update_job(
            job_id='espn_game_updates',
            interval_minutes=15
        )
        
        # Add default bet settlement job (every 30 minutes)
        scheduler.add_settlement_job(
            job_id='automated_settlement',
            interval_minutes=30
        )
        
        logger.info("Default scheduled jobs configured successfully")
        
    except Exception as e:
        logger.error(f"Failed to setup default jobs: {e}")


def start_scheduler_if_needed() -> None:
    """
    Start the scheduler if it exists and is not running
    Used for application startup
    """
    scheduler = get_scheduler()
    if scheduler and not scheduler.is_running():
        try:
            scheduler.start()
            logger.info("Scheduler started during application startup")
        except Exception as e:
            logger.error(f"Failed to start scheduler during startup: {e}")


def shutdown_scheduler() -> None:
    """
    Shutdown the scheduler gracefully
    Used for application shutdown
    """
    scheduler = get_scheduler()
    if scheduler and scheduler.is_running():
        try:
            scheduler.shutdown(wait=True)
            logger.info("Scheduler shut down during application shutdown")
        except Exception as e:
            logger.error(f"Error shutting down scheduler: {e}")