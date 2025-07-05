#!/usr/bin/env python3
"""
This is a transitional wrapper for the refactored application.
Most functionality has been moved to the 'app' package.

This file is kept for backward compatibility during the transition.
"""
import os
import sys
from app import create_app
from app.config import DevelopmentConfig

# Create application instance with development configuration
app = create_app(config_class=DevelopmentConfig)

# Import the application instance for WSGI servers
application = app

if __name__ == '__main__':
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=5000)
