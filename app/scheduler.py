from apscheduler.schedulers.background import BackgroundScheduler
from app.services.data_processor import run_pipeline
from app.services.market_data import update_market_data, initialize_sample_data
from app.services.email_service import send_daily_reports
import atexit
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

scheduler = None
current_interval = 15

def start_scheduler(app):
    global scheduler, current_interval
    if scheduler is None:
        scheduler = BackgroundScheduler()
        # Run every 15 minutes by default
        scheduler.add_job(func=run_pipeline, trigger="interval", minutes=current_interval, id='pipeline_job')
        
        # Update market data every 15 minutes (synced with pipeline)
        scheduler.add_job(func=update_market_data, trigger="interval", minutes=current_interval, id='market_data_job')

        # Send Daily Signal Reports at 6 AM
        scheduler.add_job(func=send_daily_reports, trigger="cron", hour=6, minute=0, id='daily_email_job', args=[app])
        
        scheduler.start()
        logger.info(f"Scheduler started. Pipeline and Market Data will run every {current_interval} minutes.")
        logger.info("Daily reports will send daily at 6:00 AM.")
        
        # Initialize sample data if needed (only runs once if no data exists)
        initialize_sample_data()
        
        # Run immediately on startup
        scheduler.add_job(func=run_pipeline, trigger="date", id='startup_job')
        scheduler.add_job(func=update_market_data, trigger="date", id='startup_market_job')

        # Shut down the scheduler when exiting the app
        atexit.register(lambda: scheduler.shutdown())

def refresh_now():
    global scheduler
    if scheduler and scheduler.running:
        scheduler.add_job(func=run_pipeline, trigger="date", id=f'manual_refresh_{datetime.now().timestamp()}')
        scheduler.add_job(func=update_market_data, trigger="date", id=f'manual_market_refresh_{datetime.now().timestamp()}')
        return True
    return False

def update_interval(minutes):
    global scheduler, current_interval
    if scheduler and scheduler.running:
        try:
            scheduler.reschedule_job('pipeline_job', trigger='interval', minutes=minutes)
            scheduler.reschedule_job('market_data_job', trigger='interval', minutes=minutes)
            current_interval = minutes
            logger.info(f"Rescheduled pipeline and market data to run every {minutes} minutes.")
            return True
        except Exception as e:
            logger.error(f"Failed to reschedule: {e}")
            return False
    return False

def get_next_run_time():
    global scheduler
    if scheduler:
        job = scheduler.get_job('pipeline_job')
        if job:
            return str(job.next_run_time)
    return "Unknown"

def get_interval():
    return current_interval
