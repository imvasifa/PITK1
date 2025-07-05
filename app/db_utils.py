"""
Database utilities for the application.
Handles database connections and operations using SQLAlchemy.
"""
import os
import logging
from flask import current_app
from redis import Redis, ConnectionPool
from contextlib import contextmanager
from . import db

logger = logging.getLogger(__name__)

class Database:
    """Database connection manager."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._redis_pool = None
        return cls._instance
        
    @classmethod
    def init_app(cls, app):
        """Initialize the database with the Flask app."""
        try:
            # Initialize Redis if configured and URL is valid
            redis_url = app.config.get('REDIS_URL')
            if redis_url and any(redis_url.startswith(scheme) for scheme in ['redis://', 'rediss://', 'unix://']):
                try:
                    cls._instance._redis_pool = ConnectionPool.from_url(
                        redis_url,
                        max_connections=10,
                        decode_responses=True
                    )
                    logger.info("Redis connection pool initialized successfully.")
                except Exception as e:
                    logger.warning(f"Redis connection failed: {str(e)}. Continuing without Redis.")
                    cls._instance._redis_pool = None
            else:
                logger.info("Redis URL not configured or invalid. Continuing without Redis.")
                cls._instance._redis_pool = None
            
            logger.info("Database initialization complete.")
            
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            if 'sqlite' not in app.config.get('SQLALCHEMY_DATABASE_URI', ''):
                logger.error("Consider using SQLite for development by setting DATABASE_URL=sqlite:///app.db")
            # Don't raise the exception to allow the app to start without Redis
            cls._instance._redis_pool = None
    
    def test_connections(self):
        """Test database and Redis connections."""
        # Test database connection
        try:
            # Test SQLAlchemy connection
            db.session.execute('SELECT 1')
            logger.info("Database connection test successful.")
            
            # Test Redis connection if configured
            if hasattr(self, '_redis_pool') and self._redis_pool:
                redis_conn = self.get_redis_connection()
                redis_conn.ping()
                redis_conn.close()
                logger.info("Redis connection test successful.")
                
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Get a database connection from SQLAlchemy."""
        connection = None
        try:
            connection = db.engine.connect()
            yield connection
        except Exception as e:
            logger.error(f"Error getting database connection: {str(e)}")
            raise
        finally:
            if connection:
                connection.close()
    
    def get_redis_connection(self):
        """Get a Redis connection from the pool."""
        if not hasattr(self, '_redis_pool') or not self._redis_pool:
            raise RuntimeError("Redis connection pool not initialized")
        return Redis(connection_pool=self._redis_pool)
    
    def close_all_connections(self):
        """Close all database and Redis connections."""
        # SQLAlchemy handles its own connection pooling
        logger.info("SQLAlchemy connection pool will be managed automatically")
        
        # Close Redis connections if they exist
        if hasattr(self, '_redis_pool') and self._redis_pool:
            self._redis_pool.disconnect()
            logger.info("Closed all Redis connections")

# Create a global instance
db_manager = Database()

def init_db(app):
    """
    Initialize the database with the Flask app.
    
    Args:
        app: Flask application instance
        
    Returns:
        Database: The database manager instance
    """
    db_manager.init_app(app)
    
    # Ensure the upload directory exists
    upload_dir = app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir, exist_ok=True)
    
    return db_manager
