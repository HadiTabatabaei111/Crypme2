#!/bin/bash

# Advanced Crypto Futures Trading Bot - Setup and Run Script
# این اسکریپت تمام نیازهای ربات را نصب و راهاندازی میکند

echo "=========================================="
echo "Advanced Crypto Futures Trading Bot"
echo "Setup and Installation Script"
echo "=========================================="
echo ""

# رنگها برای خروجی
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# بررسی Python
echo -e "${YELLOW}Checking Python installation...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed!${NC}"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}Python version: $PYTHON_VERSION${NC}"
echo ""

# بررسی pip
echo -e "${YELLOW}Checking pip installation...${NC}"
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}Error: pip3 is not installed!${NC}"
    echo "Installing pip..."
    python3 -m ensurepip --upgrade
fi
echo -e "${GREEN}pip is installed${NC}"
echo ""

# ایجاد محیط مجازی (اختیاری اما توصیه میشود)
echo -e "${YELLOW}Setting up virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}Virtual environment created${NC}"
else
    echo -e "${GREEN}Virtual environment already exists${NC}"
fi

# فعالسازی محیط مجازی
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate 2>/dev/null || . venv/bin/activate

# بهروزرسانی pip
echo -e "${YELLOW}Upgrading pip...${NC}"
pip install --upgrade pip --quiet

# نصب وابستگیها
echo -e "${YELLOW}Installing required packages...${NC}"
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to install requirements${NC}"
    exit 1
fi

echo -e "${GREEN}All packages installed successfully${NC}"
echo ""

# بررسی فایل config.json
echo -e "${YELLOW}Checking configuration...${NC}"
if [ ! -f "config.json" ]; then
    if [ -f "config.json.example" ]; then
        echo -e "${YELLOW}Creating config.json from example...${NC}"
        cp config.json.example config.json
        echo -e "${GREEN}Config file created. Please edit config.json with your API keys${NC}"
    else
        echo -e "${RED}Error: config.json.example not found!${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}Config file exists${NC}"
fi
echo ""

# بررسی متغیرهای محیطی برای API keys
echo -e "${YELLOW}Checking for API keys...${NC}"
if [ -z "$BINANCE_API_KEY" ] || [ -z "$BINANCE_API_SECRET" ]; then
    echo -e "${YELLOW}API keys not found in environment variables${NC}"
    echo -e "${YELLOW}Please set them in config.json or as environment variables:${NC}"
    echo "  export BINANCE_API_KEY='your_api_key'"
    echo "  export BINANCE_API_SECRET='your_api_secret'"
    echo ""
    echo -e "${YELLOW}Or edit config.json and add your keys${NC}"
    echo ""
    read -p "Do you want to continue without API keys? (analysis mode only) [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Exiting..."
        exit 1
    fi
else
    echo -e "${GREEN}API keys found in environment variables${NC}"
fi
echo ""

# ایجاد دیتابیس
echo -e "${YELLOW}Initializing database...${NC}"
python3 -c "from crypto_futures_bot import Database; db = Database(); print('Database initialized')"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Database initialized successfully${NC}"
else
    echo -e "${RED}Error: Failed to initialize database${NC}"
    exit 1
fi
echo ""

# نمایش اطلاعات
echo "=========================================="
echo -e "${GREEN}Setup completed successfully!${NC}"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  - Database: trading_bot.db"
echo "  - Log file: trading_bot.log"
echo "  - Config file: config.json"
echo ""
echo "To run the bot:"
echo "  ./setup_and_run.sh --run"
echo "  or"
echo "  python3 crypto_futures_bot.py"
echo ""
echo "Important notes:"
echo "  1. Make sure to set your Binance API keys in config.json"
echo "  2. Start with testnet mode (testnet: true) for testing"
echo "  3. Set auto_trade to false initially to analyze only"
echo "  4. Monitor the logs in trading_bot.log"
echo ""

# اگر آرگومان --run داده شده باشد، ربات را اجرا کن
if [ "$1" == "--run" ]; then
    echo -e "${YELLOW}Starting trading bot...${NC}"
    echo ""
    python3 crypto_futures_bot.py
fi

# غیرفعالسازی محیط مجازی (اگر از venv استفاده شده)
if [ -n "$VIRTUAL_ENV" ]; then
    echo ""
    echo -e "${YELLOW}To deactivate virtual environment, run: deactivate${NC}"
fi

