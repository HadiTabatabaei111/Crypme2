# indicators.py
def rsi(prices, period=14):
    """
    محاسبه RSI به صورت سبک‌وزن
    """
    if len(prices) < period + 1:
        return 50.0
    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    up = sum(d for d in deltas[:period] if d >= 0) / period
    down = -sum(d for d in deltas[:period] if d < 0) / period
    if down == 0:
        rsi_val = 100.0
    else:
        rs = up / down
        rsi_val = 100.0 - (100.0 / (1.0 + rs))
    for delta in deltas[period:]:
        up = (up * (period - 1) + max(delta, 0)) / period
        down = (down * (period - 1) + max(-delta, 0)) / period
        if down == 0:
            rsi_val = 100.0
        else:
            rs = up / down
            rsi_val = 100.0 - (100.0 / (1.0 + rs))
    return rsi_val

def macd(prices, fast=12, slow=26, signal=9):
    """
    محاسبه MACD و خط سیگنال
    """
    def _ema(data, period):
        if len(data) < period:
            return 0
        k = 2.0 / (period + 1)
        ema = data[0]
        for price in data[1:]:
            ema = price * k + ema * (1 - k)
        return ema

    ema_fast = _ema(prices, fast)
    ema_slow = _ema(prices, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _ema([ema_fast, ema_slow], signal) if len(prices) >= signal else 0
    return macd_line, signal_line
