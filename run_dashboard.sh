#!/bin/bash

echo "========================================"
echo "Crypto Trading Bot Dashboard"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install/upgrade requirements
echo "Installing requirements..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Check if database exists
if [ ! -f "trading_bot.db" ]; then
    echo ""
    echo "Warning: Database trading_bot.db not found!"
    echo "Please run the bot first to create the database."
    echo ""
fi

# Run dashboard
echo ""
echo "Starting dashboard server..."
echo "Dashboard will be available at: http://localhost:5000"
echo "Press Ctrl+C to stop"
echo ""
python3 dashboard_server.py

