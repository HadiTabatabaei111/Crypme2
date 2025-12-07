#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bitunix Trading Module
Handles trading operations on Bitunix exchange (Futures)
"""

import os
import json
import hmac
import hashlib
import time
import requests
import logging
from typing import Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class BitunixTrader:
    """Bitunix exchange trading interface for USDT Perpetual Futures"""

    BASE_URL = "https://api.bitunix.com"
    FUTURES_BASE_URL = "https://api.bitunix.com/fapi/v1"

    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        """
        Initialize Bitunix trader

        Args:
            api_key: Bitunix API key
            api_secret: Bitunix API secret
            testnet: Use testnet (default: False) — Bitunix testnet status unclear
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.base_url = self.FUTURES_BASE_URL  # Bitunix likely uses single endpoint
        self.session = requests.Session()

    # ---------- Public market data helpers ----------
    def get_all_symbols(self) -> List[Dict]:
        """Return all futures symbols metadata"""
        try:
            data = self._make_request('GET', '/exchangeInfo', params={})
            # Normalize to list of symbols
            if isinstance(data, dict) and 'symbols' in data:
                return data['symbols']
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Error fetching exchange info: {e}")
            return []

    def get_all_24h_tickers(self) -> List[Dict]:
        """Return 24h ticker stats for all symbols"""
        try:
            data = self._make_request('GET', '/ticker/24hr', params={})
            return data if isinstance(data, list) else [data]
        except Exception as e:
            logger.error(f"Error fetching 24h tickers: {e}")
            return []

    def get_24h_ticker(self, symbol: str) -> Optional[Dict]:
        """Return 24h ticker for a symbol"""
        try:
            data = self._make_request('GET', '/ticker/24hr', params={'symbol': symbol})
            return data if isinstance(data, dict) else None
        except Exception as e:
            logger.error(f"Error fetching 24h ticker {symbol}: {e}")
            return None

    def _generate_signature(self, params: Dict) -> str:
        """Generate HMAC SHA256 signature for Bitunix"""
        # Sort by key and create query string
        query_string = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _make_request(self, method: str, endpoint: str, params: Dict = None, signed: bool = False) -> Dict:
        """
        Make API request to Bitunix

        Args:
            method: 'GET' or 'POST'
            endpoint: API endpoint (e.g., '/order')
            params: Request parameters
            signed: Add signature & auth headers

        Returns:
            JSON response data
        """
        if params is None:
            params = {}

        url = self.base_url + endpoint
        headers = {"Content-Type": "application/json"}

        if signed:
            # Add timestamp and API key
            timestamp = str(int(time.time() * 1000))
            params['timestamp'] = timestamp
            params['recvWindow'] = 5000  # optional but recommended

            signature = self._generate_signature(params)
            params['signature'] = signature

            headers['X-BAPI-API-KEY'] = self.api_key
            headers['X-BAPI-SIGN'] = signature
            headers['X-BAPI-TIMESTAMP'] = timestamp

        try:
            if method.upper() == "GET":
                response = self.session.get(url, params=params, headers=headers, timeout=10)
            else:
                response = self.session.post(url, json=params, headers=headers, timeout=10)

            response.raise_for_status()
            data = response.json()

            # Bitunix likely uses {"code": 0, "msg": "...", "data": ...}
            if data.get("code") != 0:
                error_msg = data.get("msg", "Unknown error")
                logger.error(f"Bitunix API error: {error_msg}")
                raise Exception(f"Bitunix API error: {error_msg}")

            return data.get("data", data)

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error making request: {e}")
            raise

    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """Get symbol info (leverage, limits, etc.)"""
        try:
            response = self._make_request('GET', '/exchangeInfo', params={'symbol': symbol})
            if isinstance(response, dict) and 'symbols' in response:
                for sym in response['symbols']:
                    if sym['symbol'] == symbol:
                        return sym
            return None
        except Exception as e:
            logger.error(f"Error getting symbol info: {e}")
            return None

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current mark price or last price"""
        try:
            response = self._make_request('GET', '/ticker/price', params={'symbol': symbol})
            return float(response.get('price'))
        except Exception as e:
            logger.error(f"Error getting current price: {e}")
            return None

    def get_klines(self, symbol: str, interval: str = '1m', limit: int = 200) -> List[List]:
        """Get candlestick data"""
        interval_map = {
            '1': '1m', '5': '5m', '15': '15m', '30': '30m',
            '60': '1h', '240': '4h', 'D': '1d', '1d': '1d'
        }
        by_interval = interval_map.get(str(interval), str(interval))

        try:
            response = self._make_request('GET', '/klines', {
                'symbol': symbol,
                'interval': by_interval,
                'limit': limit
            })
            # Expected format: [[open_time, open, high, low, close, volume, ...], ...]
            klines = []
            for item in response:
                klines.append([
                    int(item[0]),      # timestamp
                    float(item[1]),    # open
                    float(item[2]),    # high
                    float(item[3]),    # low
                    float(item[4]),    # close
                    float(item[5])     # volume
                ])
            return klines
        except Exception as e:
            logger.error(f"Error getting klines: {e}")
            return []

    def parse_klines(self, klines: list) -> list:
        """Already in standard format"""
        return klines

    def place_order(self, symbol: str, side: str, order_type: str,
                    qty: float, price: Optional[float] = None,
                    stop_loss: Optional[float] = None,
                    take_profit: Optional[float] = None,
                    reduce_only: bool = False) -> Dict:
        """
        Place order on Bitunix Futures

        Note: Bitunix may use 'positionIdx' for hedge mode (0=one-way, 1=long, 2=short)
        """
        params = {
            'symbol': symbol,
            'side': side.upper(),           # BUY / SELL
            'orderType': order_type.capitalize(),  # Market / Limit
            'qty': str(qty),
            'reduceOnly': reduce_only,
            'positionIdx': 0  # assume one-way mode
        }

        if order_type.lower() == 'limit':
            if price is None:
                raise ValueError("Price required for Limit order")
            params['price'] = str(price)

        if stop_loss:
            params['stopLoss'] = str(stop_loss)
        if take_profit:
            params['takeProfit'] = str(take_profit)

        try:
            response = self._make_request('POST', '/order', params, signed=True)
            return {
                'success': True,
                'order_id': response.get('orderId') or response.get('orderId'),
                'message': 'Order placed successfully'
            }
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def calculate_position_size(self, symbol: str, usd_amount: float, current_price: float) -> float:
        qty = usd_amount / current_price
        return round(qty, 3)  # adjust based on symbol precision if needed

    def calculate_entry_stop_take(self, current_price: float, entry_percent: float,
                                  stop_loss_percent: float,
                                  take_profit_percent: float, side: str = 'Buy') -> Dict:
        try:
            if side.lower() == 'buy':
                entry_price = current_price * (1 + entry_percent / 100)
                stop_loss = entry_price * (1 - stop_loss_percent / 100)
                take_profit = entry_price * (1 + take_profit_percent / 100)
            else:
                entry_price = current_price * (1 - entry_percent / 100)
                stop_loss = entry_price * (1 + stop_loss_percent / 100)
                take_profit = entry_price * (1 - take_profit_percent / 100)

            return {
                'entry_price': round(entry_price, 8),
                'stop_loss': round(stop_loss, 8),
                'take_profit': round(take_profit, 8),
                'entry_percent': entry_percent,
                'stop_loss_percent': stop_loss_percent,
                'take_profit_percent': take_profit_percent
            }
        except Exception as e:
            logger.error(f"Error calculating prices: {e}")
            return {
                'entry_price': current_price,
                'stop_loss': current_price,
                'take_profit': current_price,
                'entry_percent': 0,
                'stop_loss_percent': 0,
                'take_profit_percent': 0
            }