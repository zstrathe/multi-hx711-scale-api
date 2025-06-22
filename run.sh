#!/bin/bash

# Exit on error
set -e

# Go to the script's directory (project root)
cd "$(dirname "$0")"

# Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
  VENV_CREATED=true
fi

# Activate venv
source .venv/bin/activate

# Install dependencies if venv was just created or requirements.txt is newer
if [ "$VENV_CREATED" = true ] || [ requirements.txt -nt .venv/.last_requirements_install ]; then
  echo "Installing/updating Python dependencies..."
  pip install --upgrade pip
  pip install -r requirements.txt
  touch .venv/.last_requirements_install
else
  echo "Dependencies already installed and up-to-date."
fi

# Start FastAPI app
echo "Starting FastAPI app with uvicorn..."
uvicorn api.main:app --host 0.0.0.0 --port 8000