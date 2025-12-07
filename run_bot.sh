#!/bin/bash

###############################################################################
# Advanced Crypto Futures Trading Bot - Complete Setup and Run Script
# ربات ترید فیوچرز کریپتو - اسکریپت کامل نصب و اجرا
###############################################################################

set -e  # Exit on error

# رنگها
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# توابع کمکی
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# شروع
clear
print_header "Advanced Crypto Futures Trading Bot"
echo "ربات حرفهای معاملهگری فیوچرز کریپتو"
echo "با قابلیت تشخیص پامپ، دامپ و معامله خودکار"
echo ""

# بررسی Python
print_info "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        print_error "Python 3 is not installed!"
        echo "Please install Python 3.8 or higher from python.org"
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
print_success "Python version: $PYTHON_VERSION"
echo ""

# بررسی pip
print_info "Checking pip installation..."
if ! $PYTHON_CMD -m pip --version &> /dev/null; then
    print_warning "pip not found, installing..."
    $PYTHON_CMD -m ensurepip --upgrade
fi
print_success "pip is installed"
echo ""

# بهروزرسانی pip
print_info "Upgrading pip..."
$PYTHON_CMD -m pip install --upgrade pip --quiet
print_success "pip upgraded"
echo ""

# بررسی و نصب وابستگیها
print_info "Installing required packages..."

# ایجاد requirements.txt اگر وجود ندارد
if [ ! -f "requirements.txt" ]; then
    cat > requirements.txt << EOF
requests>=2.31.0
python-binance>=1.0.19
python-dotenv>=1.0.0
EOF
    print_success "Created requirements.txt"
fi

# نصب پکیجها
$PYTHON_CMD -m pip install -r requirements.txt --quiet

if [ $? -ne 0 ]; then
    print_error "Failed to install requirements"
    exit 1
fi

print_success "All packages installed successfully"
echo ""

# بررسی و ایجاد فایلهای پیکربندی
print_info "Setting up configuration files..."

# ایجاد config.json اگر وجود ندارد
if [ ! -f "config.json" ]; then
    if [ -f "config.json.example" ]; then
        cp config.json.example config.json
        print_success "Created config.json from example"
    else
        # ایجاد config.json جدید
        cat > config.json << EOF
{
  "database_path": "trading_bot.db",
  "scan_interval": 300,
  "min_confidence": 0.7,
  "max_position_size": 100,
  "stop_loss_percent": 5,
  "take_profit_percent": 10,
  "auto_trade": false,
  "testnet": true,
  "binance_api_key": "",
  "binance_api_secret": ""
}
EOF
        print_success "Created config.json"
    fi
    print_warning "Please edit config.json and add your Binance API keys"
else
    print_success "Config file already exists"
fi
echo ""

# بررسی API Keys
print_info "Checking for API keys..."
if [ -z "$BINANCE_API_KEY" ] && [ -z "$BINANCE_API_SECRET" ]; then
    # بررسی در config.json
    if grep -q '"binance_api_key": ""' config.json 2>/dev/null || \
       grep -q '"binance_api_key": "YOUR_BINANCE_API_KEY"' config.json 2>/dev/null; then
        print_warning "Binance API keys not configured"
        echo ""
        echo "You can set them in two ways:"
        echo "  1. Edit config.json and add your keys"
        echo "  2. Set environment variables:"
        echo "     export BINANCE_API_KEY='your_api_key'"
        echo "     export BINANCE_API_SECRET='your_api_secret'"
        echo ""
        print_info "Bot will run in analysis mode only (no trading)"
        echo ""
    else
        print_success "API keys found in config.json"
    fi
else
    print_success "API keys found in environment variables"
fi
echo ""

# ایجاد دیتابیس
print_info "Initializing database..."
$PYTHON_CMD -c "
import sys
sys.path.insert(0, '.')
try:
    from crypto_futures_bot import Database
    db = Database()
    print('Database initialized successfully')
except Exception as e:
    print(f'Error: {e}')
    sys.exit(1)
" 2>&1

if [ $? -eq 0 ]; then
    print_success "Database initialized"
else
    print_error "Failed to initialize database"
    exit 1
fi
echo ""

# نمایش خلاصه
print_header "Setup Summary"
echo "Configuration:"
echo "  - Database: trading_bot.db"
echo "  - Log file: trading_bot.log"
echo "  - Config file: config.json"
echo "  - Python: $PYTHON_CMD ($PYTHON_VERSION)"
echo ""

# بررسی اینکه آیا باید ربات را اجرا کنیم
if [ "$1" == "--run" ] || [ "$1" == "-r" ]; then
    print_header "Starting Trading Bot"
    echo ""
    print_info "Press Ctrl+C to stop the bot"
    echo ""
    
    # اجرای ربات
    $PYTHON_CMD crypto_futures_bot.py
    
elif [ "$1" == "--test" ] || [ "$1" == "-t" ]; then
    print_header "Testing Bot Configuration"
    echo ""
    print_info "Running configuration test..."
    $PYTHON_CMD -c "
import sys
sys.path.insert(0, '.')
try:
    from crypto_futures_bot import load_config, DexScreenerAPI, RugCheckAPI
    config = load_config()
    print('✓ Config loaded successfully')
    
    dexscreener = DexScreenerAPI()
    print('✓ DexScreener API initialized')
    
    rugcheck = RugCheckAPI()
    print('✓ RugCheck API initialized')
    
    if config.get('binance_api_key') and config.get('binance_api_secret'):
        from binance.client import Client
        client = Client(
            api_key=config['binance_api_key'],
            api_secret=config['binance_api_secret'],
            testnet=config.get('testnet', True)
        )
        print('✓ Binance API connected')
    else:
        print('⚠ Binance API not configured (analysis mode only)')
    
    print('')
    print('All tests passed! Bot is ready to run.')
except Exception as e:
    print(f'✗ Error: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"
else
    print_header "Setup Completed Successfully!"
    echo ""
    echo "To run the bot, use one of the following commands:"
    echo ""
    echo "  $0 --run      # Start the trading bot"
    echo "  $0 --test     # Test bot configuration"
    echo ""
    echo "Or directly:"
    echo "  $PYTHON_CMD crypto_futures_bot.py"
    echo ""
    echo "Important notes:"
    echo "  1. Make sure to set your Binance API keys in config.json"
    echo "  2. Start with testnet mode (testnet: true) for testing"
    echo "  3. Set auto_trade to false initially to analyze only"
    echo "  4. Monitor the logs in trading_bot.log"
    echo ""
    echo "For help, see README.md"
    echo ""
fi

exit 0

