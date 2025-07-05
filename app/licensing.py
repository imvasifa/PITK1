"""
This module handles license management and validation.
"""
import threading
import time
import logging
from datetime import datetime, timedelta
from flask import current_app

logger = logging.getLogger(__name__)

class LicenseManager:
    """Manages license validation and status checks."""
    
    def __init__(self, app=None):
        """Initialize the license manager."""
        self.app = app
        self._check_interval = 3600  # Check every hour by default
        self._stop_event = threading.Event()
        self._thread = None
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app."""
        self.app = app
        self._check_interval = app.config.get('LICENSE_CHECK_INTERVAL', 3600)
        
        # Start license check when app starts
        with app.app_context():
            self.start_license_check()
    
    def start_license_check(self):
        """Start the license check thread."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("License check thread is already running")
            return
            
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_license_check,
            daemon=True,
            name="LicenseCheckThread"
        )
        self._thread.start()
        logger.info("License check thread started")
    
    def stop_license_check(self):
        """Stop the license check thread."""
        if self._thread is None:
            return
            
        self._stop_event.set()
        self._thread.join(timeout=5)
        self._thread = None
        logger.info("License check thread stopped")
    
    def _run_license_check(self):
        """Main loop for license checking."""
        logger.info("License check thread started")
        
        while not self._stop_event.is_set():
            try:
                self.check_all_licenses()
            except Exception as e:
                logger.error(f"Error in license check: {str(e)}")
            
            # Wait for the next check or until stopped
            self._stop_event.wait(self._check_interval)
    
    def check_all_licenses(self):
        """Check all licenses in the database."""
        if not self.app:
            logger.error("Application context not available")
            return
            
        with self.app.app_context():
            from . import db
            
            conn = None  # Initialize conn as None
            try:
                conn = db.get_connection()
                with conn.cursor() as cur:
                    # Get all users with licenses
                    cur.execute("""
                        SELECT id, user_data 
                        FROM users 
                        WHERE user_data->'account'->>'license_key' IS NOT NULL
                    """)
                    
                    for user_id, user_data in cur.fetchall():
                        try:
                            self._check_user_license(cur, user_id, user_data)
                        except Exception as e:
                            logger.error(f"Error checking license for user {user_id}: {str(e)}")
                            
                    conn.commit()
                    
            except Exception as e:
                logger.error(f"Database error during license check: {str(e)}")
                if conn:  # Now conn is always defined
                    try:
                        conn.rollback()
                    except Exception as rollback_error:
                        logger.error(f"Error during rollback: {str(rollback_error)}")
            finally:
                if conn:  # Ensure connection is properly closed
                    try:
                        conn.close()
                    except Exception as close_error:
                        logger.error(f"Error closing connection: {str(close_error)}")
    
    def _check_user_license(self, cursor, user_id, user_data):
        """Check and update a single user's license status."""
        try:
            account = user_data.get('account', {})
            license_key = account.get('license_key')
            
            if not license_key:
                return
                
            # Check license validity (implement your own validation logic)
            is_valid = self._validate_license(license_key)
            
            # Update user's license status
            cursor.execute("""
                UPDATE users 
                SET user_data = jsonb_set(
                    user_data,
                    '{account,license_status}',
                    %s
                )
                WHERE id = %s
            """, (json.dumps('active' if is_valid else 'expired'), user_id))
            
            logger.info(f"Updated license status for user {user_id}: {'valid' if is_valid else 'expired'}")
            
        except Exception as e:
            logger.error(f"Error processing license for user {user_id}: {str(e)}")
            raise
    
    def _validate_license(self, license_key):
        """Validate a license key."""
        # Implement your license validation logic here
        # This is a placeholder - replace with actual validation
        try:
            # Example: Check if license key format is valid
            if not license_key or not isinstance(license_key, str):
                return False
                
            # Add your validation logic here
            # For now, just check if it looks like a UUID
            import re
            uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)
            return bool(uuid_pattern.match(license_key))
            
        except Exception as e:
            logger.error(f"License validation error: {str(e)}")
            return False

# Global instance
license_manager = LicenseManager()

def check_license_statuses():
    """Background thread function to check license statuses."""
    license_manager.check_all_licenses()

# Create a global instance of LicenseManager
license_manager = LicenseManager()

def check_license_statuses():
    """Background thread function to check license statuses."""
    with current_app.app_context():
        license_manager.check_all_licenses()
