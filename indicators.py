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
