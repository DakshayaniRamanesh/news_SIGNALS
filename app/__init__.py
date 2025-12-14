from flask import Flask
from app.scheduler import start_scheduler

def create_app():
    app = Flask(__name__)
    app.secret_key = 'dev-secret-key-change-in-production'
    
    # Register Blueprints
    from app.routes import main
    app.register_blueprint(main)
    
    # Start Scheduler
    # We only want to start the scheduler if we are not in debug mode reloader
    # or we handle it to not run twice. 
    # For simplicity in this setup, we'll just start it.
    # In production with gunicorn, this might need a different approach (e.g. separate worker).
    # But for "industrial format" single app usage, this is fine.
    import os
    # Start Scheduler
    # We start the scheduler here. The `start_scheduler` function internally checks
    # if it's already running in this process.
    # Note: If running with a reloader (debug=True), this might run in both parent and child
    # processes if not handled carefully. However, for standard deployment (wsgi.py),
    # this ensures the scheduler actually runs.
    start_scheduler(app)

    return app
