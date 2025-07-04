#!/bin/bash

# Exit on any error
set -e

# Force Python version
pyenv install -s 3.10.13
pyenv global 3.10.13

# Verify Python version
echo "Using Python version:"
python --version

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Build the application
# Add any build steps here

echo "Build completed successfully!"
