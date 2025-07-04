#!/bin/bash
set -e

# Create a virtual environment
python3 -m venv /tmp/venv
source /tmp/venv/bin/activate

# Install Python dependencies with binary wheels
pip install --upgrade pip
pip install --no-cache-dir --only-binary=:all: -r requirements.txt

# Make sure the script is executable
chmod +x /tmp/venv/bin/activate
