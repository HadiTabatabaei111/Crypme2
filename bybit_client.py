#!/usr/bin/env python3
import requests
from typing import Dict, List, Optional


class BybitClient:
    BASE_URL = "https://api.bybit.com"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def _get(self, path: str, params: Dict) -> Dict:
        url = f"{self.BASE_URL}{path}"
        r = self.session.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict):
            result = data.get("result", data)
            return result
        return data

    def get_klines(self, symbol: str, interval: str = "1", limit: int = 200, category: str = "linear") -> List[List]:
        interval_map = {
            "1": "1",
            "3": "3",
            "5": "5",
            "15": "15",
            "30": "30",
            "60": "60",
            "240": "240",
            "D": "D",
            "1m": "1",
            "15m": "15",
            "1h": "60",
            "4h": "240",
            "1d": "D",
        }
        by_interval = interval_map.get(str(interval), str(interval))
        params = {
            "category": category,
            "symbol": symbol,
            "interval": by_interval,
            "limit": limit,
        }
        res = self._get("/v5/market/kline", params)
        items = res.get("list", []) if isinstance(res, dict) else []
        out: List[List] = []
        for it in items:
            ts = int(it[0])
            op = float(it[1])
            hi = float(it[2])
            lo = float(it[3])
            cl = float(it[4])
            vol = float(it[5])
            out.append([ts, op, hi, lo, cl, vol])
        return out

    def get_all_symbols(self, category: str = "linear") -> List[Dict]:
        res = self._get("/v5/market/instruments-info", {"category": category})
        items = res.get("list", []) if isinstance(res, dict) else []
        return items

    def get_all_24h_tickers(self, category: str = "linear") -> List[Dict]:
        res = self._get("/v5/market/tickers", {"category": category})
        items = res.get("list", []) if isinstance(res, dict) else []
        return items