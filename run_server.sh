#!/bin/bash
set -e

# Change to project directory
cd /workspaces/Gambit

# Kill any existing Flask processes
pkill -f "python.*app.py" || true
sleep 1

# Activate virtual environment
source .venv/bin/activate

# Set Python path
export PYTHONPATH=/workspaces/Gambit:$PYTHONPATH

# Check if required packages are installed
echo "Checking dependencies..."
python -c "import flask; import soccerdata; import pandas; print('✓ All dependencies found')" || {
    echo "Installing missing dependencies..."
    pip install -r requirements.txt
}

# Run the Flask app
echo "Starting Flask server on port 5000..."
python app.py
