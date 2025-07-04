#!/bin/bash
set -e

# Ensure we're using Python 3.10
export PYTHONUNBUFFERED=1
export PYTHONIOENCODING=UTF-8

# Create a virtual environment
python3.10 -m venv /tmp/venv
source /tmp/venv/bin/activate

# Upgrade pip and setuptools
python -m pip install --upgrade pip setuptools wheel

# Install Python dependencies with binary wheels
pip install --no-cache-dir --only-binary=:all: -r requirements.txt

# Make sure the script is executable
chmod +x /tmp/venv/bin/activate

# Verify installation
python -c "import pandas; print(f'Pandas version: {pandas.__version__}')"
