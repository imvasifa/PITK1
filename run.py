#!/usr/bin/env python3
"""
Main entry point for the Flask application.
"""
import os
import logging
from app import create_app
from app.db_utils import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)

def check_license_statuses():
    """Background thread to check license statuses."""
    # This function will be implemented in a separate module
    pass

def main():
    """Initialize and run the Flask application."""
    # Create application instance
    app = create_app()
    
    # Initialize database
    with app.app_context():
        init_db(app)
    
    # Start license check thread
    import threading
    license_thread = threading.Thread(target=check_license_statuses, daemon=True)
    license_thread.start()
    app.logger.info("License check thread started")
    
    # Run the application
    try:
        app.run(
            debug=app.config.get('DEBUG', True),
            use_reloader=False,
            host=app.config.get('HOST', '0.0.0.0'),
            port=int(app.config.get('PORT', 5000))
        )
    except Exception as e:
        app.logger.error(f"Error starting application: {e}")
    finally:
        # Cleanup code if needed
        pass

if __name__ == '__main__':
    main()
