"""
This module configures and provides logging utilities for the application.
"""
import os
import logging
from logging.handlers import RotatingFileHandler, SMTPHandler
from logging import Formatter
from flask import current_app, request, has_request_context
from flask_login import current_user
import json
from datetime import datetime

def setup_logging(app):
    """Configure application logging.
    
    Args:
        app: The Flask application instance
    """
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(app.instance_path, 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir, exist_ok=True)
    
    # Set the log level
    log_level = logging.DEBUG if app.debug else logging.INFO
    
    # Configure the root logger
    app.logger.setLevel(log_level)
    
    # Remove all existing handlers
    for handler in list(app.logger.handlers):
        app.logger.removeHandler(handler)
    
    # Create a console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # Create a file handler
    file_handler = RotatingFileHandler(
        os.path.join(logs_dir, 'app.log'),
        maxBytes=1024 * 1024 * 10,  # 10 MB
        backupCount=10,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    
    # Create a formatter and add it to the handlers
    formatter = RequestFormatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d] [%(request_id)s] [%(user_id)s] [%(ip)s] [%(user_agent)s] [%(endpoint)s] [%(method)s] [%(path)s] [%(status_code)s] [%(response_time)s] [%(request_data)s] [%(response_data)s]',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # Add the handlers to the logger
    app.logger.addHandler(console_handler)
    app.logger.addHandler(file_handler)
    
    # Configure SQLAlchemy logging if in debug mode
    if app.debug:
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
        logging.getLogger('sqlalchemy.pool').setLevel(logging.DEBUG)
    else:
        logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    
    # Configure other loggers
    logging.getLogger('werkzeug').setLevel(logging.INFO)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    # Add error email handler in production
    if not app.debug and not app.testing:
        if app.config.get('MAIL_SERVER'):
            auth = None
            if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
                auth = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            
            secure = None
            if app.config['MAIL_USE_TLS']:
                secure = ()
                
            mail_handler = SMTPHandler(
                mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
                fromaddr=app.config['MAIL_DEFAULT_SENDER'],
                toaddrs=app.config['ADMINS'],
                subject='Application Error',
                credentials=auth,
                secure=secure
            )
            mail_handler.setLevel(logging.ERROR)
            mail_handler.setFormatter(formatter)
            app.logger.addHandler(mail_handler)
    
    app.logger.info('Application logging configured')


def get_logger(name=None):
    """Get a logger instance with the given name.
    
    Args:
        name: The name of the logger (defaults to the calling module's name)
    
    Returns:
        logging.Logger: A configured logger instance
    """
    if name is None:
        import inspect
        frm = inspect.stack()[1]
        mod = inspect.getmodule(frm[0])
        name = mod.__name__ if mod else 'root'
    
    logger = logging.getLogger(name)
    return logger


class RequestFormatter(Formatter):
    """Custom log formatter that includes request information."""
    
    def format(self, record):
        """Format the specified record as text."""
        # Add request context if available
        if has_request_context():
            record.request_id = request.headers.get('X-Request-ID', '-')
            record.ip = request.remote_addr or '-'
            record.user_agent = request.headers.get('User-Agent', '-')
            record.endpoint = request.endpoint or '-'
            record.method = request.method or '-'
            record.path = request.path or '-'
            
            # Get user ID if authenticated
            if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                record.user_id = current_user.id
            else:
                record.user_id = '-'
            
            # Get status code if available
            if hasattr(record, 'status_code'):
                record.status_code = record.status_code
            else:
                record.status_code = '-'
            
            # Get response time if available
            if hasattr(record, 'response_time'):
                try:
                    # Try to format as float if it's a number
                    response_time = float(record.response_time)
                    record.response_time = f"{response_time:.2f}ms"
                except (ValueError, TypeError):
                    # If it's already a string or can't be converted, use as is
                    record.response_time = str(record.response_time)
            else:
                record.response_time = '-'
            
            # Get request data if available
            if hasattr(record, 'request_data'):
                if isinstance(record.request_data, (dict, list)):
                    record.request_data = json.dumps(record.request_data, default=str)
            else:
                record.request_data = '-'
            
            # Get response data if available
            if hasattr(record, 'response_data'):
                if isinstance(record.response_data, (dict, list)):
                    record.response_data = json.dumps(record.response_data, default=str)
            else:
                record.response_data = '-'
            
        else:
            # Default values when not in a request context
            record.request_id = '-'
            record.user_id = '-'
            record.ip = '-'
            record.user_agent = '-'
            record.endpoint = '-'
            record.method = '-'
            record.path = '-'
            record.status_code = '-'
            record.response_time = '-'
            record.request_data = '-'
            record.response_data = '-'
        
        return super().format(record)
