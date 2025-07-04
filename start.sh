#!/bin/bash
set -e

# Activate the virtual environment
source /tmp/venv/bin/activate

# Set environment variables
export FLASK_APP=app3.py
export FLASK_ENV=production

# Run the application
exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app3:app
