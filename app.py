# app.py
from flask import Flask, send_from_directory, jsonify
import json
import threading
import time
from data_fetcher import get_top_coins_with_volume, get_ohlc
from indicators import rsi, macd

app = Flask(__name__, static_folder='.')

# تنظیمات پیش‌فرض (اگر config.json وجود نداشته باشه)
DEFAULT_CONFIG = {
    "scan_interval": 120,
    "min_volume_usd": 5000000,
    "price_change_1h_min": 5.0,
    "rsi_oversold": 30,
    "rsi_overbought": 70
}

signals_data = {"last_update": "—", "coins": []}

def scanner_loop():
    global signals_data
    while True:
        try:
            coins = get_top_coins_with_volume(DEFAULT_CONFIG["min_volume_usd"])
            all_data = []
            for coin in coins[:80]:
                try:
                    symbol_id = coin.get("id")
                    symbol = coin.get("symbol", "").upper()
                    price = coin.get("current_price", 0)
                    change_1h = coin.get("price_change_percentage_1h_in_currency", 0)
                    volume = coin.get("total_volume", 0)

                    if not symbol_id or price <= 0:
                        continue

                    closes = get_ohlc(symbol_id, days=1)
                    current_rsi = rsi(closes) if len(closes) >= 30 else 50
                    macd_val, signal_val = macd(closes) if len(closes) >= 30 else (0, 0)

                    all_data.append({
                        "symbol": f"{symbol}/USDT",
                        "price": round(price, 6),
                        "change_1h": round(change_1h, 2),
                        "volume": round(volume, 0),
                        "rsi": round(current_rsi, 2),
                        "macd_hist": round(macd_val - signal_val, 6),
                        "signal": "PUMP" if (current_rsi < DEFAULT_CONFIG["rsi_oversold"] and change_1h > 0) else
                                  "DUMP" if (current_rsi > DEFAULT_CONFIG["rsi_overbought"] and change_1h < 0) else "NEUTRAL"
                    })
                except:
                    continue

            signals_data = {
                "last_update": time.strftime("%Y-%m-%d %H:%M:%S"),
                "coins": all_data
            }
            print(f"✅ آپدیت شد: {len(all_data)} ارز")
        except Exception as e:
            print(f"❌ خطا: {e}")
        time.sleep(DEFAULT_CONFIG["scan_interval"])

# راه‌اندازی اسکنر در ترد پس‌زمینه
threading.Thread(target=scanner_loop, daemon=True).start()

@app.route('/')
def dashboard():
    return send_from_directory('.', 'dashboard.html')

@app.route('/signals.json')
def signals():
    return jsonify(signals_data)

# برای Render.com
if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
