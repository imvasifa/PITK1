"""
This package contains utility modules for the application.
"""

# Import utility functions to make them available when importing from utils
from .email import send_email, send_verification_email, send_password_reset_email
from .logging import setup_logging, get_logger
from .cache import cache, get_cached_data, set_cached_data, delete_cached_data

# Make these available when importing from app.utils
__all__ = [
    'send_email',
    'send_verification_email',
    'send_password_reset_email',
    'setup_logging',
    'get_logger',
    'cache',
    'get_cached_data',
    'set_cached_data',
    'delete_cached_data'
]
