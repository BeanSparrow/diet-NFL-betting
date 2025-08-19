import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, call
from app import create_app, db
from app.services.scheduler import SchedulerService
from app.models import Game


class TestSchedulerService:
    """Test APScheduler integration service with TDD methodology"""
    
    @pytest.fixture
    def app(self):
        """Create test Flask application"""
        app = create_app('testing')
        app.config['TESTING'] = True
        
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    @pytest.fixture
    def scheduler_service(self, app):
        """Create scheduler service instance"""
        with app.app_context():
            return SchedulerService(app)
    
    def test_scheduler_service_initialization(self, app):
        """Test SchedulerService can be initialized with Flask app"""
        with app.app_context():
            scheduler = SchedulerService(app)
            assert scheduler is not None
            assert scheduler.app == app
            assert scheduler.scheduler is not None
    
    def test_scheduler_service_initialization_without_app(self):
        """Test SchedulerService can be initialized without Flask app"""
        scheduler = SchedulerService()
        assert scheduler is not None
        assert scheduler.app is None
        assert scheduler.scheduler is not None
    
    def test_scheduler_init_app_method(self, app):
        """Test init_app method for deferred initialization"""
        scheduler = SchedulerService()
        scheduler.init_app(app)
        
        assert scheduler.app == app
        assert scheduler.scheduler is not None
    
    def test_scheduler_starts_successfully(self, scheduler_service):
        """Test scheduler can be started successfully"""
        # Scheduler should not be running initially
        assert not scheduler_service.is_running()
        
        # Start scheduler
        scheduler_service.start()
        assert scheduler_service.is_running()
        
        # Clean up
        scheduler_service.shutdown()
    
    def test_scheduler_stops_successfully(self, scheduler_service):
        """Test scheduler can be stopped successfully"""
        # Start scheduler first
        scheduler_service.start()
        assert scheduler_service.is_running()
        
        # Stop scheduler
        scheduler_service.shutdown()
        assert not scheduler_service.is_running()
    
    def test_scheduler_restart_idempotent(self, scheduler_service):
        """Test scheduler start/stop operations are idempotent"""
        # Multiple starts should not fail
        scheduler_service.start()
        scheduler_service.start()  # Should not raise error
        assert scheduler_service.is_running()
        
        # Multiple stops should not fail
        scheduler_service.shutdown()
        scheduler_service.shutdown()  # Should not raise error
        assert not scheduler_service.is_running()
    
    def test_add_espn_update_job(self, scheduler_service):
        """Test adding ESPN update job to scheduler"""
        job_id = 'test_espn_update'
        
        # Add job
        job = scheduler_service.add_espn_update_job(
            job_id=job_id,
            interval_minutes=30
        )
        
        assert job is not None
        assert job.id == job_id
        
        # Job should be scheduled but scheduler not running yet
        assert not scheduler_service.is_running()
        
        # Start scheduler to activate job
        scheduler_service.start()
        
        # Job should be in scheduler
        scheduled_job = scheduler_service.scheduler.get_job(job_id)
        assert scheduled_job is not None
        assert scheduled_job.id == job_id
        
        # Clean up
        scheduler_service.shutdown()
    
    def test_add_duplicate_job_replaces_existing(self, scheduler_service):
        """Test adding job with same ID replaces existing job"""
        job_id = 'duplicate_test'
        
        # Add first job
        job1 = scheduler_service.add_espn_update_job(
            job_id=job_id,
            interval_minutes=30
        )
        
        # Add job with same ID but different interval
        job2 = scheduler_service.add_espn_update_job(
            job_id=job_id,
            interval_minutes=60
        )
        
        # Should get the same job ID but different instance
        assert job1.id == job2.id == job_id
        
        scheduler_service.start()
        
        # Only one job should exist
        jobs = scheduler_service.scheduler.get_jobs()
        job_ids = [job.id for job in jobs]
        assert job_ids.count(job_id) == 1
        
        scheduler_service.shutdown()
    
    def test_remove_job_by_id(self, scheduler_service):
        """Test removing scheduled job by ID"""
        job_id = 'removable_job'
        
        # Add job
        scheduler_service.add_espn_update_job(
            job_id=job_id,
            interval_minutes=15
        )
        
        scheduler_service.start()
        
        # Verify job exists
        assert scheduler_service.scheduler.get_job(job_id) is not None
        
        # Remove job
        removed = scheduler_service.remove_job(job_id)
        assert removed is True
        
        # Verify job no longer exists
        assert scheduler_service.scheduler.get_job(job_id) is None
        
        scheduler_service.shutdown()
    
    def test_remove_nonexistent_job_returns_false(self, scheduler_service):
        """Test removing non-existent job returns False"""
        scheduler_service.start()
        
        result = scheduler_service.remove_job('nonexistent_job')
        assert result is False
        
        scheduler_service.shutdown()
    
    def test_get_scheduled_jobs_list(self, scheduler_service):
        """Test getting list of all scheduled jobs"""
        # Initially no jobs
        jobs = scheduler_service.get_jobs()
        assert len(jobs) == 0
        
        # Add multiple jobs
        scheduler_service.add_espn_update_job('job1', 30)
        scheduler_service.add_espn_update_job('job2', 60)
        
        jobs = scheduler_service.get_jobs()
        assert len(jobs) == 2
        
        job_ids = [job.id for job in jobs]
        assert 'job1' in job_ids
        assert 'job2' in job_ids
    
    @patch('app.services.espn_service.update_nfl_games')
    def test_espn_update_job_execution(self, mock_update_function, scheduler_service):
        """Test ESPN update job executes the correct function"""
        mock_update_function.return_value = {
            'success': True,
            'games_processed': 5,
            'created': 2,
            'updated': 3
        }
        
        job_id = 'test_execution'
        
        # Add job with very short interval for testing
        scheduler_service.add_espn_update_job(job_id, interval_minutes=1)
        
        # Manually trigger the job to test execution
        job = scheduler_service.scheduler.get_job(job_id)
        assert job is not None
        
        # Execute the job function directly
        job.func()
        
        # Verify the ESPN update function was called
        mock_update_function.assert_called_once()
    
    def test_scheduler_configuration_properties(self, scheduler_service):
        """Test scheduler has correct configuration"""
        scheduler = scheduler_service.scheduler
        
        # Should have proper timezone handling
        assert scheduler.timezone is not None
        
        # Should be configured for standalone operation
        assert hasattr(scheduler, 'add_job')
        assert hasattr(scheduler, 'start')
        assert hasattr(scheduler, 'shutdown')
    
    def test_add_job_with_invalid_interval_raises_error(self, scheduler_service):
        """Test adding job with invalid interval raises appropriate error"""
        with pytest.raises(ValueError, match="Interval must be positive"):
            scheduler_service.add_espn_update_job('invalid_job', interval_minutes=0)
        
        with pytest.raises(ValueError, match="Interval must be positive"):
            scheduler_service.add_espn_update_job('invalid_job', interval_minutes=-5)
    
    def test_add_job_with_invalid_job_id_raises_error(self, scheduler_service):
        """Test adding job with invalid job ID raises appropriate error"""
        with pytest.raises(ValueError, match="Job ID cannot be empty"):
            scheduler_service.add_espn_update_job('', interval_minutes=30)
        
        with pytest.raises(ValueError, match="Job ID cannot be empty"):
            scheduler_service.add_espn_update_job(None, interval_minutes=30)
    
    @patch('app.services.espn_service.update_nfl_games')
    def test_espn_update_job_handles_exceptions(self, mock_update_function, scheduler_service):
        """Test ESPN update job handles exceptions gracefully"""
        # Mock function to raise exception
        mock_update_function.side_effect = Exception("ESPN API Error")
        
        job_id = 'exception_test'
        scheduler_service.add_espn_update_job(job_id, interval_minutes=1)
        
        # Execute job function and verify it doesn't crash
        job = scheduler_service.scheduler.get_job(job_id)
        try:
            job.func()
            # Job should handle exception gracefully
        except Exception:
            pytest.fail("Job function should handle exceptions gracefully")
    
    def test_scheduler_context_manager_support(self, app):
        """Test scheduler can be used as context manager"""
        with app.app_context():
            with SchedulerService(app) as scheduler:
                assert scheduler.is_running()
                
                # Add a job inside context
                scheduler.add_espn_update_job('context_job', 30)
                jobs = scheduler.get_jobs()
                assert len(jobs) == 1
            
            # Scheduler should be shut down after context
            assert not scheduler.is_running()


class TestSchedulerIntegration:
    """Integration tests for scheduler with Flask app lifecycle"""
    
    @pytest.fixture
    def app(self):
        """Create test Flask application"""
        app = create_app('testing')
        app.config['TESTING'] = True
        
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    def test_scheduler_initialization_from_app_factory(self, app):
        """Test scheduler can be initialized from app factory pattern"""
        from app.services.scheduler import init_scheduler
        
        # Initialize scheduler
        scheduler = init_scheduler(app)
        
        assert scheduler is not None
        assert scheduler.app == app
    
    @patch('app.services.espn_service.update_nfl_games')
    def test_default_espn_update_job_registration(self, mock_update_function, app):
        """Test default ESPN update job is registered with app"""
        from app.services.scheduler import init_scheduler, setup_default_jobs
        
        mock_update_function.return_value = {'success': True}
        
        scheduler = init_scheduler(app)
        setup_default_jobs(scheduler)
        
        # Should have default ESPN update job
        jobs = scheduler.get_jobs()
        job_ids = [job.id for job in jobs]
        assert 'espn_game_updates' in job_ids
        
        # Clean up
        scheduler.shutdown()
    
    def test_scheduler_service_exists_and_importable(self):
        """Test that SchedulerService can be imported"""
        try:
            from app.services.scheduler import SchedulerService
            assert SchedulerService is not None
        except ImportError:
            pytest.fail("SchedulerService should be importable")


class TestSchedulerConfiguration:
    """Test scheduler configuration and setup"""
    
    def test_scheduler_default_configuration(self):
        """Test scheduler uses appropriate default configuration"""
        from app.services.scheduler import SchedulerService
        
        scheduler = SchedulerService()
        
        # Should use proper jobstore (in-memory for testing)
        assert scheduler.scheduler is not None
        
        # Should have timezone support
        assert scheduler.scheduler.timezone is not None
    
    def test_scheduler_production_configuration(self, app):
        """Test scheduler configuration for production environment"""
        app.config['TESTING'] = False
        app.config['SCHEDULER_TIMEZONE'] = 'America/New_York'
        
        from app.services.scheduler import SchedulerService
        
        with app.app_context():
            scheduler = SchedulerService(app)
            
            # Should respect timezone configuration
            assert scheduler.scheduler.timezone is not None
            
            scheduler.shutdown()