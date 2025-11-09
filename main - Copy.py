import json
import time
from data_fetcher import get_top_coins_with_volume, get_ohlc  # ✅ این خط اصلاح شد
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
