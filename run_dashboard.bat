@echo off
chcp 65001 >nul
echo ========================================
echo Crypto Trading Bot Dashboard
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install/upgrade requirements
echo Installing requirements...
pip install -q --upgrade pip
pip install -q -r requirements.txt

REM Check if database exists
if not exist "trading_bot.db" (
    echo.
    echo Warning: Database trading_bot.db not found!
    echo Please run the bot first to create the database.
    echo.
    pause
)

REM Run dashboard
echo.
echo Starting dashboard server...
echo Dashboard will be available at: http://localhost:5000
echo Press Ctrl+C to stop
echo.
python dashboard_server.py

pause

