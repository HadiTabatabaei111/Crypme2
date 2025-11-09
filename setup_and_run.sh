#!/bin/bash

# 🚀 Pump Hunter + Bitunix Futures — نصب و اجرا خودکار
# نویسنده: دوستت! ❤️
# اجرا: chmod +x setup_and_run.sh && ./setup_and_run.sh

echo "🧰 بررسی Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 نصب نیست. لطفاً ابتدا Python 3 را نصب کنید."
    exit 1
fi

echo "📦 ایجاد محیط مجازی (venv)..."
python3 -m venv venv
source venv/bin/activate

echo "📥 نصب کتابخانههای مورد نیاز..."
pip install requests pandas numpy

# ✅ ایجاد فایلهای پروژه
echo "📂 ایجاد فایلهای پروژه..."

# config.json
cat > config.json <<EOL
{
  "scan_interval": 60,
  "rsi_overbought": 70,
  "rsi_oversold": 30,
  "min_volume_usd": 5000000,
  "price_change_1h_min": 5.0,
  "auto_trade": false,
  "trade_symbol_suffix": "USDT",
  "position_usd": 50,
  "bitunix_api_key": "YOUR_BITUNIX_API_KEY",
  "bitunix_api_secret": "YOUR_BITUNIX_API_SECRET"
}
EOL

# indicators.py
cat > indicators.py <<EOL
import numpy as np

def rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    rs = up / down if down != 0 else 0
    rsi_value = 100 - (100 / (1 + rs))
    for d in deltas[period:]:
        up = (up * (period - 1) + (d if d >= 0 else 0)) / period
        down = (down * (period - 1) + (-d if d < 0 else 0)) / period
        rs = up / down if down != 0 else 0
        rsi_value = 100 - (100 / (1 + rs))
    return rsi_value

def macd(prices, fast=12, slow=26, signal=9):
    def _ema(data, p):
        if len(data) < p:
            return 0
        k = 2 / (p + 1)
        ema = data[0]
        for price in data[1:]:
            ema = price * k + ema * (1 - k)
        return ema
    ema_fast = _ema(prices, fast)
    ema_slow = _ema(prices, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _ema([ema_fast, ema_slow], signal) if len(prices) > signal else 0
    return macd_line, signal_line
EOL

# data_fetcher.py
cat > data_fetcher.py <<EOL
import requests

def get_ohlc(symbol_id, days=1):
    url = f"https://api.coingecko.com/api/v3/coins/{symbol_id}/ohlc"
    try:
        res = requests.get(url, params={'vs_currency': 'usd', 'days': days}, timeout=10)
        if res.status_code == 200:
            data = res.json()
            return [float(candle[4]) for candle in data[-50:]] if data else []
    except:
        pass
    return []

def get_top_coins_with_volume(min_volume=5_000_000):
    try:
        res = requests.get(
            "https://api.coingecko.com/api/v3/coins/markets",
            params={
                'vs_currency': 'usd',
                'order': 'volume_desc',
                'per_page': 200,
                'page': 1,
                'price_change_percentage': '1h'
            },
            timeout=10
        )
        coins = res.json()
        return [c for c in coins if c.get('total_volume', 0) >= min_volume]
    except:
        return []
EOL

# bitunix_futures.py
cat > bitunix_futures.py <<EOL
import hmac
import hashlib
import time
import requests
import json

class BitunixFutures:
    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        self.url = "https://openapi.bitunix.com"

    def _sign(self, payload):
        return hmac.new(self.api_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

    def place_order(self, symbol, side, qty, price=None, order_type="LIMIT"):
        timestamp = int(time.time() * 1000)
        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": str(qty),
            "timestamp": timestamp
        }
        if price:
            params["price"] = str(price)
        query = "&".join([f"{k}={v}" for k, v in params.items()])
        params["signature"] = self._sign(query)
        try:
            return requests.post(
                self.url + "/api/v1/futures/order",
                headers={"X-BAPI-API-KEY": self.api_key, "Content-Type": "application/json"},
                data=json.dumps(params),
                timeout=10
            ).json()
        except Exception as e:
            print(f"[FUTURES ERROR] {e}")
            return None
EOL

# main.py
cat > main.py <<EOL
import json, time
from data_fetcher import get_top_coins_with_volume
from indicators import rsi, macd
from bitunix_futures import BitunixFutures

with open("config.json") as f:
    cfg = json.load(f)

futures_client = BitunixFutures(cfg["bitunix_api_key"], cfg["bitunix_api_secret"])

def analyze_coin(coin):
    symbol_id = coin["id"]
    symbol = coin["symbol"].upper()
    price = coin["current_price"]
    change_1h = coin.get("price_change_percentage_1h_in_currency", 0)
    if change_1h < cfg["price_change_1h_min"]:
        return None
    closes = get_ohlc(symbol_id, days=1)
    if len(closes) < 30:
        return None
    current_rsi = rsi(closes)
    macd_val, signal_val = macd(closes)
    confidence = 0.0
    signal = None
    if current_rsi < cfg["rsi_oversold"] and macd_val > signal_val and change_1h > 0:
        signal = "PUMP"
        confidence = min(1.0, (abs(change_1h) / 20) + (1 - current_rsi / 30))
    elif current_rsi > cfg["rsi_overbought"] and macd_val < signal_val and change_1h < 0:
        signal = "DUMP"
        confidence = min(1.0, (abs(change_1h) / 20) + (current_rsi - 70) / 30)
    if signal and confidence > 0.6:
        return {
            "symbol": symbol + cfg["trade_symbol_suffix"],
            "price": price,
            "rsi": round(current_rsi, 2),
            "macd": round(macd_val - signal_val, 4),
            "change_1h": round(change_1h, 2),
            "type": signal,
            "confidence": round(confidence, 2)
        }
    return None

print("✅ سیستم پامپیاب با RSI/MACD آماده است!")
print("📝 قبل از اجرا، فایل config.json را ویرایش کنید!")
print("💡 auto_trade را false بگذارید تا فقط سیگنال ببینید.\n")

while True:
    print("="*60)
    coins = get_top_coins_with_volume(min_volume=cfg["min_volume_usd"])
    for coin in coins[:50]:
        sig = analyze_coin(coin)
        if sig:
            print(f"🚨 {sig['type']} | {sig['symbol']} | RSI: {sig['rsi']} | MACD: {sig['macd']} | Conf: {sig['confidence']}")
            if cfg["auto_trade"]:
                qty = cfg["position_usd"] / sig["price"]
                side = "BUY" if sig["type"] == "PUMP" else "SELL"
                print(f"  📥 ارسال سفارش {side}...")
                print("  نتیجه:", futures_client.place_order(sig["symbol"], side, qty))
    time.sleep(cfg["scan_interval"])
EOL

# 🔐 دستورالعمل نهایی
echo
echo "✅ پروژه با موفقیت ایجاد شد!"
echo "📝 مراحل بعدی:"
echo "  1. فایل config.json را باز کنید"
echo "  2. YOUR_BITUNIX_API_KEY و YOUR_BITUNIX_API_SECRET را جایگزین کنید"
echo "  3. auto_trade را بر اساس نیاز تنظیم کنید"
echo "  4. برای اجرا، دستور زیر را بزنید:"
echo
echo "     source venv/bin/activate"
echo "     python main.py"
echo