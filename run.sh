#!/bin/bash

# Exit on any error
set -e

# Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

# Activate venv
source .venv/bin/activate

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Starting sensors/serial_handler.py in background..."
python sensors/serial_handler.py &

echo "Starting FastAPI app with uvicorn..."
uvicorn api.main:app --host 0.0.0.0 --port 8000