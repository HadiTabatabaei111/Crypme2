#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nobitex Trading Module
Handles trading operations on Nobitex exchange (Futures)
"""

import os
import json
import hmac
import hashlib
import time
import requests
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class NobitexTrader:
    """Nobitex exchange trading interface for Futures"""
    
    # Nobitex API endpoints
    BASE_URL = "https://api.nobitex.ir"
    FUTURES_BASE_URL = "https://api.nobitex.ir/futures"
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        """
        Initialize Nobitex trader
        
        Args:
            api_key: Nobitex API key
            api_secret: Nobitex API secret
            testnet: Use testnet (default: False) - Note: Nobitex may not have testnet
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.base_url = self.FUTURES_BASE_URL
        self.session = requests.Session()
        self.token = None
        
        # Authenticate on initialization
        if api_key and api_secret:
            self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Nobitex API"""
        try:
            # Nobitex authentication - may vary based on API version
            # Try to authenticate, if fails, continue without token for public endpoints
            timestamp = str(int(time.time()))
            message = f"{self.api_key}{timestamp}"
            signature = hmac.new(
                self.api_secret.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            auth_data = {
                'apiKey': self.api_key,
                'signature': signature,
                'timestamp': timestamp
            }
            
            try:
                response = self.session.post(
                    f"{self.BASE_URL}/auth/login",
                    json=auth_data,
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'ok' or 'token' in data:
                        self.token = data.get('token') or data.get('accessToken')
                        if self.token:
                            self.session.headers.update({
                                'Authorization': f'Token {self.token}'
                            })
                            logger.info("Nobitex authentication successful")
                    else:
                        logger.warning(f"Nobitex authentication failed: {data.get('message', 'Unknown error')}")
                else:
                    logger.warning(f"Nobitex authentication failed: {response.status_code} - Continuing without authentication for public endpoints")
            except Exception as auth_error:
                logger.warning(f"Could not authenticate with Nobitex: {auth_error} - Continuing for public endpoints")
        except Exception as e:
            logger.warning(f"Error in authentication setup: {e} - Continuing for public endpoints")
    
    def _generate_signature(self, params: Dict, timestamp: str) -> str:
        """Generate signature for Nobitex API request"""
        # Sort parameters
        sorted_params = sorted(params.items())
        query_string = '&'.join([f"{k}={v}" for k, v in sorted_params])
        
        # Create signature
        sign_string = f"{timestamp}{self.api_key}{query_string}"
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            sign_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _make_request(self, method: str, endpoint: str, params: Dict = None, 
                     signed: bool = False) -> Dict:
        """
        Make API request to Nobitex
        
        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint
            params: Request parameters
            signed: Whether request requires signature
            
        Returns:
            API response
        """
        if params is None:
            params = {}
        
        url = f"{self.base_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if signed and self.token:
            headers['Authorization'] = f'Token {self.token}'
            timestamp = str(int(time.time() * 1000))
            params['timestamp'] = timestamp
            
            signature = self._generate_signature(params, timestamp)
            params['signature'] = signature
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, params=params, headers=headers, timeout=10)
            else:
                response = self.session.post(url, json=params, headers=headers, timeout=10)
            
            response.raise_for_status()
            data = response.json()
            
            # Nobitex can return data in different formats
            if isinstance(data, dict):
                if data.get('status') == 'ok':
                    return data.get('result', data)
                elif 'error' in data or 'message' in data:
                    error_msg = data.get('message') or data.get('error', 'Unknown error')
                    logger.error(f"Nobitex API error: {error_msg}")
                    raise Exception(f"Nobitex API error: {error_msg}")
                else:
                    # Return data as-is if no error structure
                    return data
            elif isinstance(data, list):
                # Direct list response
                return data
            else:
                return data
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error making request: {e}")
            raise
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """
        Get symbol information
        
        Args:
            symbol: Trading symbol (e.g., 'BTC-USDT')
            
        Returns:
            Symbol information
        """
        try:
            # Convert symbol format if needed (BTCUSDT -> BTC-USDT)
            formatted_symbol = self._format_symbol(symbol)
            
            params = {
                'symbol': formatted_symbol
            }
            response = self._make_request('GET', '/v1/instruments', params)
            
            if response and isinstance(response, list):
                for sym in response:
                    if sym.get('symbol') == formatted_symbol or sym.get('symbol') == symbol:
                        return sym
            elif response and isinstance(response, dict):
                if response.get('symbol') == formatted_symbol or response.get('symbol') == symbol:
                    return response
            return None
        except Exception as e:
            logger.error(f"Error getting symbol info: {e}")
            return None
    
    def _format_symbol(self, symbol: str) -> str:
        """Format symbol for Nobitex (BTCUSDT -> BTC-USDT)"""
        if '-' in symbol:
            return symbol
        
        # Try to split common pairs
        for base in ['BTC', 'ETH', 'USDT', 'USDC', 'IRR', 'TMN']:
            if symbol.endswith(base):
                return f"{symbol[:-len(base)]}-{base}"
            if symbol.startswith(base):
                return f"{base}-{symbol[len(base):]}"
        
        return symbol
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current price for a symbol
        
        Args:
            symbol: Trading symbol (e.g., 'BTC-USDT')
            
        Returns:
            Current price
        """
        try:
            formatted_symbol = self._format_symbol(symbol)
            
            params = {
                'symbol': formatted_symbol
            }
            response = self._make_request('GET', '/v1/ticker', params)
            
            if response:
                # Nobitex returns price in different formats
                if isinstance(response, dict):
                    price = response.get('lastPrice') or response.get('last') or response.get('price')
                    if price:
                        return float(price)
                elif isinstance(response, list):
                    for ticker in response:
                        if ticker.get('symbol') == formatted_symbol or ticker.get('symbol') == symbol:
                            price = ticker.get('lastPrice') or ticker.get('last') or ticker.get('price')
                            if price:
                                return float(price)
            
            return None
        except Exception as e:
            logger.error(f"Error getting current price: {e}")
            return None
    
    def get_klines(self, symbol: str, interval: str = '1', limit: int = 200) -> list:
        """
        Get kline/candlestick data
        
        Args:
            symbol: Trading symbol (e.g., 'BTC-USDT')
            interval: Kline interval (1m, 5m, 15m, 30m, 1h, 4h, 1d)
            limit: Number of klines (default: 200)
            
        Returns:
            List of klines
        """
        try:
            formatted_symbol = self._format_symbol(symbol)
            
            # Convert interval format (1 -> 1m, 15 -> 15m, etc.)
            interval_map = {
                '1': '1m',
                '3': '3m',
                '5': '5m',
                '15': '15m',
                '30': '30m',
                '60': '1h',
                '240': '4h',
                'D': '1d',
                '1d': '1d',
                '1m': '1m',
                '15m': '15m'
            }
            formatted_interval = interval_map.get(interval, interval)
            if not formatted_interval.endswith(('m', 'h', 'd')):
                formatted_interval = f"{formatted_interval}m"
            
            params = {
                'symbol': formatted_symbol,
                'interval': formatted_interval,
                'limit': limit
            }
            response = self._make_request('GET', '/v1/klines', params)
            
            if response and isinstance(response, list):
                return response
            elif response and isinstance(response, dict) and 'data' in response:
                return response['data']
            return []
        except Exception as e:
            logger.error(f"Error getting klines: {e}")
            return []
    
    def parse_klines(self, klines: list) -> list:
        """Parse klines to standard format"""
        parsed = []
        for kline in klines:
            if isinstance(kline, list) and len(kline) >= 6:
                # Standard format: [time, open, high, low, close, volume]
                parsed.append(kline)
            elif isinstance(kline, dict):
                # Dict format: convert to list
                parsed.append([
                    int(kline.get('time', kline.get('timestamp', 0))),
                    float(kline.get('open', 0)),
                    float(kline.get('high', 0)),
                    float(kline.get('low', 0)),
                    float(kline.get('close', 0)),
                    float(kline.get('volume', 0))
                ])
        return parsed
    
    def place_order(self, symbol: str, side: str, order_type: str, 
                   qty: float, price: Optional[float] = None,
                   stop_loss: Optional[float] = None,
                   take_profit: Optional[float] = None,
                   reduce_only: bool = False) -> Dict:
        """
        Place an order on Nobitex
        
        Args:
            symbol: Trading symbol (e.g., 'BTC-USDT')
            side: Order side ('Buy' or 'Sell')
            order_type: Order type ('Market' or 'Limit')
            qty: Order quantity
            price: Order price (required for Limit orders)
            stop_loss: Stop loss price
            take_profit: Take profit price
            reduce_only: Reduce only flag
            
        Returns:
            Order result
        """
        try:
            formatted_symbol = self._format_symbol(symbol)
            
            # Convert side to Nobitex format
            nobitex_side = 'buy' if side.lower() == 'buy' else 'sell'
            
            params = {
                'symbol': formatted_symbol,
                'side': nobitex_side,
                'type': order_type.lower(),
                'quantity': str(qty)
            }
            
            if order_type.lower() == 'limit' and price:
                params['price'] = str(price)
            
            if stop_loss:
                params['stopLoss'] = str(stop_loss)
            
            if take_profit:
                params['takeProfit'] = str(take_profit)
            
            if reduce_only:
                params['reduceOnly'] = True
            
            response = self._make_request('POST', '/v1/orders', params, signed=True)
            
            return {
                'success': True,
                'order_id': response.get('orderId') or response.get('id') or response.get('order_id'),
                'message': 'Order placed successfully'
            }
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def calculate_position_size(self, symbol: str, usd_amount: float, 
                               current_price: float) -> float:
        """
        Calculate position size based on USD amount
        
        Args:
            symbol: Trading symbol
            usd_amount: Amount in USD
            current_price: Current price
            
        Returns:
            Position size
        """
        try:
            symbol_info = self.get_symbol_info(symbol)
            if not symbol_info:
                # Default to 8 decimal places
                qty = usd_amount / current_price
                return round(qty, 8)
            
            # Get lot size filter
            min_qty = float(symbol_info.get('minQuantity', symbol_info.get('minQty', 0.001)))
            max_qty = float(symbol_info.get('maxQuantity', symbol_info.get('maxQty', 1000000)))
            step_size = float(symbol_info.get('stepSize', symbol_info.get('qtyStep', 0.001)))
            
            # Calculate quantity
            qty = usd_amount / current_price
            
            # Round to step size
            if step_size > 0:
                qty = round(qty / step_size) * step_size
            
            # Check limits
            qty = max(min_qty, min(qty, max_qty))
            
            return qty
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            # Fallback calculation
            qty = usd_amount / current_price
            return round(qty, 8)
    
    def calculate_entry_stop_take(self, current_price: float, entry_percent: float,
                                  stop_loss_percent: float, 
                                  take_profit_percent: float, side: str = 'Buy') -> Dict:
        """
        Calculate entry, stop loss, and take profit prices
        
        Args:
            current_price: Current market price
            entry_percent: Entry price adjustment percentage (positive for buy, negative for sell)
            stop_loss_percent: Stop loss percentage
            take_profit_percent: Take profit percentage
            side: Order side ('Buy' or 'Sell')
            
        Returns:
            Dictionary with entry, stop_loss, and take_profit prices
        """
        try:
            # Calculate entry price
            if side.lower() == 'buy':
                entry_price = current_price * (1 + entry_percent / 100)
                stop_loss = entry_price * (1 - stop_loss_percent / 100)
                take_profit = entry_price * (1 + take_profit_percent / 100)
            else:  # Sell
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

