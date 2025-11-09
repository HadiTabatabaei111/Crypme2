# data_fetcher.py
import requests

def get_ohlc(symbol_id, days=1):
    """
    دریافت داده OHLC (باز، بالا، پایین، بسته) از CoinGecko
    """
    url = f"https://api.coingecko.com/api/v3/coins/{symbol_id}/ohlc"
    try:
        res = requests.get(
            url,
            params={'vs_currency': 'usd', 'days': days},
            timeout=10
        )
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list) and len(data) > 0:
                # هر سطر: [timestamp, open, high, low, close]
                return [float(candle[4]) for candle in data[-50:]]
    except Exception as e:
        print(f"[OHLC Error] {symbol_id}: {e}")
    return []

def get_top_coins_with_volume(min_volume=5_000_000):
    """
    دریافت لیست ارزهای برتر بر اساس حجم 24h
    """
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
        if res.status_code == 200:
            coins = res.json()
            return [c for c in coins if c.get('total_volume', 0) >= min_volume]
    except Exception as e:
        print(f"[Market List Error]: {e}")
    return []
