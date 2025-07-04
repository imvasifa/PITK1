#!/bin/bash
set -e

# Set environment variables
export FLASK_APP=app3.py
export FLASK_ENV=production

# Activate the virtual environment
source /tmp/venv/bin/activate

# Ensure we're using the correct Python version
PYTHON_VERSION=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Using Python $PYTHON_VERSION"

# Check if required environment variables are set
if [ -z "$PORT" ]; then
    echo "ERROR: PORT environment variable is not set"
    exit 1
fi

# Run database migrations if needed
# python -m flask db upgrade

# Start the application
echo "Starting Gunicorn on port $PORT..."
exec gunicorn --bind :$PORT \
    --workers 1 \
    --threads 8 \
    --timeout 120 \
    --worker-class uvicorn.workers.UvicornWorker \
    --log-level=info \
    --access-logfile - \
    --error-logfile - \
    app3:app
