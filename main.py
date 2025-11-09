# main.py — فقط اسکن و ذخیره در signals.json
import json
import time
from data_fetcher import get_top_coins_with_volume, get_ohlc
from indicators import rsi, macd

with open("config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

SCAN_INTERVAL = cfg.get("scan_interval", 60)
MIN_VOLUME = cfg.get("min_volume_usd", 5_000_000)
PRICE_CHANGE_MIN = cfg.get("price_change_1h_min", 5.0)
RSI_OVERSOLD = cfg.get("rsi_oversold", 30)
RSI_OVERBOUGHT = cfg.get("rsi_overbought", 70)

print("📊 پامپ‌یاب فعال شد — خروجی در signals.json ذخیره می‌شود...")

while True:
    all_data = []
    coins = get_top_coins_with_volume(min_volume=MIN_VOLUME)

    for coin in coins[:100]:
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
                "signal": (
                    "PUMP" if (current_rsi < RSI_OVERSOLD and change_1h > 0) else
                    "DUMP" if (current_rsi > RSI_OVERBOUGHT and change_1h < 0) else
                    "NEUTRAL"
                )
            })
        except:
            continue

    # ذخیره در فایل
    with open("signals.json", "w", encoding="utf-8") as f:
        json.dump({
            "last_update": time.strftime("%Y-%m-%d %H:%M:%S"),
            "coins": all_data
        }, f, ensure_ascii=False, indent=2)

    print(f"✅ {len(all_data)} ارز در signals.json ذخیره شد. ({time.strftime('%H:%M:%S')})")
    time.sleep(SCAN_INTERVAL)