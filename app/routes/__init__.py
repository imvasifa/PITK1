"""
This package contains all the route blueprints for the application.
"""

# Import blueprints to make them available when importing from routes
from .main import main_bp
from .auth import auth_bp
from .admin import admin_bp

# List of all blueprints to be registered in the application
__all__ = ['main_bp', 'auth_bp', 'admin_bp']
