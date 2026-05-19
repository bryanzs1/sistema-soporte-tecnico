#!/usr/bin/env bash
# Build script for Render deployment

set -o errexit

echo "Installing Python dependencies..."

# Upgrade pip
pip install --upgrade pip

# Install all requirements
pip install -r requirements.txt

# Explicitly install ML dependencies to ensure they're present
pip install scikit-learn numpy

# Run migrations if needed
python -m flask db upgrade

echo "Build completed successfully!"
