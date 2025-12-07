@echo off
REM Advanced Crypto Futures Trading Bot - Windows Setup Script
REM این اسکریپت برای ویندوز طراحی شده است

echo ==========================================
echo Advanced Crypto Futures Trading Bot
echo Setup and Installation Script (Windows)
echo ==========================================
echo.

REM بررسی Python
echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed!
    echo Please install Python 3.8 or higher from python.org
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python version: %PYTHON_VERSION%
echo.

REM بررسی pip
echo Checking pip installation...
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo Error: pip is not installed!
    echo Installing pip...
    python -m ensurepip --upgrade
)
echo pip is installed
echo.

REM به‌روزرسانی pip
echo Upgrading pip...
python -m pip install --upgrade pip --quiet

REM نصب وابستگی‌ها
echo Installing required packages...
python -m pip install -r requirements.txt

if errorlevel 1 (
    echo Error: Failed to install requirements
    pause
    exit /b 1
)

echo All packages installed successfully
echo.

REM بررسی فایل config.json
echo Checking configuration...
if not exist "config.json" (
    if exist "config.json.example" (
        echo Creating config.json from example...
        copy config.json.example config.json
        echo Config file created. Please edit config.json with your API keys
    ) else (
        echo Error: config.json.example not found!
        pause
        exit /b 1
    )
) else (
    echo Config file exists
)
echo.

REM ایجاد دیتابیس
echo Initializing database...
python -c "from crypto_futures_bot import Database; db = Database(); print('Database initialized')"

if errorlevel 1 (
    echo Error: Failed to initialize database
    pause
    exit /b 1
)

echo Database initialized successfully
echo.

REM نمایش اطلاعات
echo ==========================================
echo Setup completed successfully!
echo ==========================================
echo.
echo Configuration:
echo   - Database: trading_bot.db
echo   - Log file: trading_bot.log
echo   - Config file: config.json
echo.
echo To run the bot:
echo   setup_and_run.bat --run
echo   or
echo   python crypto_futures_bot.py
echo.
echo Important notes:
echo   1. Make sure to set your Binance API keys in config.json
echo   2. Start with testnet mode (testnet: true) for testing
echo   3. Set auto_trade to false initially to analyze only
echo   4. Monitor the logs in trading_bot.log
echo.

REM اگر آرگومان --run داده شده باشد، ربات را اجرا کن
if "%1"=="--run" (
    echo Starting trading bot...
    echo.
    python crypto_futures_bot.py
)

pause

