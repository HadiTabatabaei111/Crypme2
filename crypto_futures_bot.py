#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced Crypto Futures Trading Bot
Professional trading bot with DexScreener integration, pump/dump detection,
and automated trading on ByBit Futures
"""

import os
import sys
import time
import json
import sqlite3
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from dataclasses import dataclass
import threading
from collections import deque

# ByBit API (using CCXT library)
try:
    import ccxt
except ImportError:
    print("Please install ccxt: pip install ccxt")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class TokenInfo:
    """Token information structure"""
    address: str
    symbol: str
    name: str
    chain_id: str
    price_usd: float
    volume_24h: float
    price_change_24h: float
    liquidity: float
    pair_created_at: datetime
    fdv: float = 0
    market_cap: float = 0


@dataclass
class TradingSignal:
    """Trading signal structure"""
    symbol: str
    signal_type: str  # 'LONG' or 'SHORT'
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    reason: str
    timestamp: datetime


class Database:
    """Database manager for storing trading data"""
    
    def __init__(self, db_path: str = "trading_bot.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tokens table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT UNIQUE NOT NULL,
                symbol TEXT NOT NULL,
                name TEXT,
                chain_id TEXT,
                price_usd REAL,
                volume_24h REAL,
                price_change_24h REAL,
                liquidity REAL,
                fdv REAL,
                market_cap REAL,
                pair_created_at TIMESTAMP,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_blacklisted BOOLEAN DEFAULT 0,
                blacklist_reason TEXT
            )
        ''')
        
        # Price history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_address TEXT NOT NULL,
                price REAL,
                volume REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (token_address) REFERENCES tokens(address)
            )
        ''')
        
        # Trading signals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trading_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                confidence REAL,
                entry_price REAL,
                stop_loss REAL,
                take_profit REAL,
                reason TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'PENDING'
            )
        ''')
        
        # Trades table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id INTEGER,
                symbol TEXT NOT NULL,
                trade_type TEXT NOT NULL,
                entry_price REAL,
                exit_price REAL,
                quantity REAL,
                pnl REAL,
                status TEXT DEFAULT 'OPEN',
                opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at TIMESTAMP,
                FOREIGN KEY (signal_id) REFERENCES trading_signals(id)
            )
        ''')
        
        # Patterns table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                token_address TEXT,
                pattern_data TEXT,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (token_address) REFERENCES tokens(address)
            )
        ''')
        
        # Blacklist table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blacklist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_address TEXT UNIQUE NOT NULL,
                reason TEXT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def save_token(self, token: TokenInfo):
        """Save or update token information"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO tokens 
            (address, symbol, name, chain_id, price_usd, volume_24h, 
             price_change_24h, liquidity, fdv, market_cap, pair_created_at, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            token.address, token.symbol, token.name, token.chain_id,
            token.price_usd, token.volume_24h, token.price_change_24h,
            token.liquidity, token.fdv, token.market_cap,
            token.pair_created_at, datetime.now()
        ))
        
        conn.commit()
        conn.close()
    
    def save_price_history(self, token_address: str, price: float, volume: float):
        """Save price history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO price_history (token_address, price, volume)
            VALUES (?, ?, ?)
        ''', (token_address, price, volume))
        
        conn.commit()
        conn.close()
    
    def save_signal(self, signal: TradingSignal):
        """Save trading signal"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO trading_signals 
            (symbol, signal_type, confidence, entry_price, stop_loss, take_profit, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            signal.symbol, signal.signal_type, signal.confidence,
            signal.entry_price, signal.stop_loss, signal.take_profit, signal.reason
        ))
        
        signal_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return signal_id
    
    def is_blacklisted(self, token_address: str) -> bool:
        """Check if token is blacklisted"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT 1 FROM blacklist WHERE token_address = ?', (token_address,))
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
    
    def add_to_blacklist(self, token_address: str, reason: str):
        """Add token to blacklist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO blacklist (token_address, reason)
                VALUES (?, ?)
            ''', (token_address, reason))
            
            cursor.execute('''
                UPDATE tokens SET is_blacklisted = 1, blacklist_reason = ?
                WHERE address = ?
            ''', (reason, token_address))
            
            conn.commit()
            logger.info(f"Added {token_address} to blacklist: {reason}")
        except sqlite3.IntegrityError:
            pass  # Already blacklisted
        
        conn.close()
    
    def get_recent_tokens(self, hours: int = 24) -> List[Dict]:
        """Get recently added tokens"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM tokens 
            WHERE first_seen >= datetime('now', '-{} hours')
            AND is_blacklisted = 0
            ORDER BY first_seen DESC
        '''.format(hours))
        
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        
        return results


class DexScreenerAPI:
    """DexScreener API integration"""
    
    BASE_URL = "https://api.dexscreener.com/latest/dex"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'CryptoFuturesBot/1.0'
        })
    
    def get_pair(self, chain_id: str, pair_address: str) -> Optional[Dict]:
        """Get pair information from DexScreener"""
        try:
            url = f"{self.BASE_URL}/pairs/{chain_id}/{pair_address}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('pair'):
                return data['pair']
            return None
        except Exception as e:
            logger.error(f"Error fetching pair from DexScreener: {e}")
            return None
    
    def search_pairs(self, query: str) -> List[Dict]:
        """Search for pairs on DexScreener"""
        try:
            url = f"{self.BASE_URL}/search"
            params = {'q': query}
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return data.get('pairs', [])
        except Exception as e:
            logger.error(f"Error searching pairs: {e}")
            return []
    
    def get_trending_tokens(self, chain: str = "ethereum") -> List[Dict]:
        """Get trending tokens from DexScreener"""
        try:
            all_pairs = []
            
            # Method 1: Search for popular token addresses (known tokens that have pairs)
            # This helps us discover new pairs
            popular_tokens = [
                "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  # USDC
                "0xdAC17F958D2ee523a2206206994597C13D831ec7",  # USDT
                "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH
            ]
            
            for token_addr in popular_tokens:
                try:
                    url = f"{self.BASE_URL}/tokens/{token_addr}"
                    response = self.session.get(url, timeout=15)
                    response.raise_for_status()
                    data = response.json()
                    pairs = data.get('pairs', [])
                    all_pairs.extend(pairs)
                except Exception as e:
                    logger.debug(f"Error fetching pairs for token {token_addr}: {e}")
                    continue
            
            # Method 2: Search by query (DexScreener search)
            search_queries = ["USDT", "USDC", "WETH"]
            
            for query in search_queries:
                try:
                    url = f"{self.BASE_URL}/search"
                    params = {'q': query}
                    response = self.session.get(url, params=params, timeout=15)
                    response.raise_for_status()
                    data = response.json()
                    pairs = data.get('pairs', [])
                    
                    # Filter for significant pairs
                    for pair in pairs:
                        liquidity = pair.get('liquidity', {})
                        if isinstance(liquidity, dict):
                            liquidity_usd = liquidity.get('usd', 0)
                        else:
                            liquidity_usd = liquidity if liquidity else 0
                            
                        if liquidity_usd > 10000:  # Min liquidity $10k
                            all_pairs.append(pair)
                except Exception as e:
                    logger.debug(f"Error in search query '{query}': {e}")
                    continue
            
            # Remove duplicates based on pair address
            seen = set()
            unique_pairs = []
            for pair in all_pairs:
                pair_address = pair.get('pairAddress', '')
                if pair_address and pair_address not in seen:
                    seen.add(pair_address)
                    unique_pairs.append(pair)
            
            # Sort by volume and return top pairs
            def get_volume(pair):
                volume = pair.get('volume', {})
                if isinstance(volume, dict):
                    return volume.get('h24', 0)
                return volume if volume else 0
            
            unique_pairs.sort(key=get_volume, reverse=True)
            
            logger.info(f"Found {len(unique_pairs)} unique pairs from DexScreener")
            return unique_pairs[:100]  # Return top 100 pairs
        except Exception as e:
            logger.error(f"Error fetching trending tokens: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return []
    
    def parse_token_info(self, pair_data: Dict) -> Optional[TokenInfo]:
        """Parse token information from DexScreener pair data"""
        try:
            base_token = pair_data.get('baseToken', {})
            quote_token = pair_data.get('quoteToken', {})
            
            # Check if it's a USDT or USDC pair (prefer stablecoin pairs)
            quote_symbol = quote_token.get('symbol', '').upper() if isinstance(quote_token, dict) else ''
            if quote_symbol and quote_symbol not in ['USDT', 'USDC', 'BUSD', 'DAI', 'USDD']:
                # Still allow other pairs, but prioritize stablecoin pairs
                pass
            
            # Get price
            price_usd = pair_data.get('priceUsd', 0)
            if isinstance(price_usd, str):
                price_usd = float(price_usd.replace(',', ''))
            else:
                price_usd = float(price_usd) if price_usd else 0
            
            if price_usd == 0:
                return None
            
            # Get price change
            price_change = pair_data.get('priceChange', {})
            if isinstance(price_change, dict):
                price_change_24h = float(price_change.get('h24', 0))
            else:
                price_change_24h = float(price_change) if price_change else 0
            
            # Get volume
            volume = pair_data.get('volume', {})
            if isinstance(volume, dict):
                volume_24h = float(volume.get('h24', 0))
            else:
                volume_24h = float(volume) if volume else 0
            
            # Get liquidity
            liquidity_data = pair_data.get('liquidity', {})
            if isinstance(liquidity_data, dict):
                liquidity = float(liquidity_data.get('usd', 0))
            else:
                liquidity = float(liquidity_data) if liquidity_data else 0
            
            # Get FDV and market cap
            fdv = float(pair_data.get('fdv', 0)) if pair_data.get('fdv') else 0
            market_cap = float(pair_data.get('marketCap', 0)) if pair_data.get('marketCap') else 0
            
            # Get pair creation date
            pair_created_at_ts = pair_data.get('pairCreatedAt', 0)
            if pair_created_at_ts:
                try:
                    pair_created_at = datetime.fromtimestamp(pair_created_at_ts / 1000)
                except:
                    pair_created_at = datetime.now() - timedelta(days=365)  # Default to 1 year ago
            else:
                pair_created_at = datetime.now() - timedelta(days=365)
            
            # Extract token info
            if isinstance(base_token, dict):
                token_address = base_token.get('address', '')
                token_symbol = base_token.get('symbol', '')
                token_name = base_token.get('name', '')
            else:
                token_address = ''
                token_symbol = ''
                token_name = ''
            
            if not token_address or not token_symbol:
                return None
            
            return TokenInfo(
                address=token_address,
                symbol=token_symbol,
                name=token_name,
                chain_id=pair_data.get('chainId', ''),
                price_usd=price_usd,
                volume_24h=volume_24h,
                price_change_24h=price_change_24h,
                liquidity=liquidity,
                fdv=fdv,
                market_cap=market_cap,
                pair_created_at=pair_created_at
            )
        except Exception as e:
            logger.error(f"Error parsing token info: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None


class RugCheckAPI:
    """RugCheck API integration"""
    
    BASE_URL = "https://api.rugcheck.xyz/v1/tokens"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'CryptoFuturesBot/1.0'
        })
    
    def check_token(self, token_address: str, chain: str = "ethereum") -> Dict:
        """Check token safety using RugCheck"""
        try:
            url = f"{self.BASE_URL}/{chain}/{token_address}"
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            return {
                'is_rug': data.get('isRug', False),
                'risk_level': data.get('riskLevel', 'UNKNOWN'),
                'honeypot': data.get('honeypot', False),
                'mintable': data.get('mintable', False),
                'proxy': data.get('proxy', False),
                'holder_count': data.get('holderCount', 0),
                'liquidity_locked': data.get('liquidityLocked', False)
            }
        except Exception as e:
            logger.error(f"Error checking token on RugCheck: {e}")
            return {
                'is_rug': True,  # Assume unsafe if check fails
                'risk_level': 'UNKNOWN',
                'error': str(e)
            }


class PumpDumpDetector:
    """Advanced pump and dump detection algorithm"""
    
    def __init__(self, db: Database):
        self.db = db
        self.price_windows = {}  # Store price windows for each token
    
    def detect_pump(self, token: TokenInfo, price_history: List[Tuple[float, datetime]]) -> bool:
        """Detect pump pattern"""
        if len(price_history) < 10:
            return False
        
        recent_prices = [p[0] for p in price_history[-10:]]
        if len(recent_prices) < 10:
            return False
        
        # Calculate price change in last 10 minutes
        price_change = ((recent_prices[-1] - recent_prices[0]) / recent_prices[0]) * 100
        
        # Check for sudden volume spike
        volume_spike = token.volume_24h > 100000  # Minimum volume threshold
        
        # Pump criteria: >15% price increase with volume spike
        if price_change > 15 and volume_spike and token.price_change_24h > 20:
            return True
        
        return False
    
    def detect_dump(self, token: TokenInfo, price_history: List[Tuple[float, datetime]]) -> bool:
        """Detect dump pattern"""
        if len(price_history) < 10:
            return False
        
        recent_prices = [p[0] for p in price_history[-10:]]
        if len(recent_prices) < 10:
            return False
        
        # Calculate price change
        price_change = ((recent_prices[-1] - recent_prices[0]) / recent_prices[0]) * 100
        
        # Dump criteria: >15% price decrease
        if price_change < -15 and token.price_change_24h < -20:
            return True
        
        return False
    
    def detect_shadow_pump(self, token: TokenInfo, price_history: List[Tuple[float, datetime]]) -> bool:
        """Detect shadow pump (manipulated volume)"""
        if len(price_history) < 20:
            return False
        
        # Check for fake volume indicators
        # Shadow pump: high volume but low liquidity, or inconsistent price/volume ratio
        volume_to_liquidity_ratio = token.volume_24h / token.liquidity if token.liquidity > 0 else 0
        
        # If volume is much higher than liquidity, it might be fake
        if volume_to_liquidity_ratio > 10 and token.liquidity < 50000:
            return True
        
        # Check price history for suspicious patterns
        prices = [p[0] for p in price_history[-20:]]
        if len(prices) < 20:
            return False
        
        # Calculate volatility
        price_changes = [abs((prices[i] - prices[i-1]) / prices[i-1]) * 100 
                        for i in range(1, len(prices))]
        avg_volatility = sum(price_changes) / len(price_changes) if price_changes else 0
        
        # Shadow pump: high volatility but low real trading activity
        if avg_volatility > 5 and token.liquidity < 100000:
            return True
        
        return False
    
    def get_price_history(self, token_address: str, hours: int = 1) -> List[Tuple[float, datetime]]:
        """Get price history from database"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT price, timestamp FROM price_history
            WHERE token_address = ?
            AND timestamp >= datetime('now', '-{} hours')
            ORDER BY timestamp ASC
        '''.format(hours), (token_address,))
        
        results = [(row[0], datetime.fromisoformat(row[1])) 
                  for row in cursor.fetchall()]
        conn.close()
        
        return results


class TradingBot:
    """Main trading bot class"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.db = Database(config.get('database_path', 'trading_bot.db'))
        self.dexscreener = DexScreenerAPI()
        self.rugcheck = RugCheckAPI()
        self.detector = PumpDumpDetector(self.db)
        
        # ByBit client
        self.bybit_client = None
        if config.get('bybit_api_key') and config.get('bybit_api_secret'):
            try:
                exchange_params = {
                    'apiKey': config['bybit_api_key'],
                    'secret': config['bybit_api_secret'],
                    'enableRateLimit': True,
                }
                if config.get('testnet', False):
                    exchange_params['options'] = {'defaultType': 'test'}
                self.bybit_client = ccxt.bybit(exchange_params)
                logger.info("ByBit client initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing ByBit client: {e}")
        
        self.running = False
        self.trades = {}
        
        # Trading parameters
        self.min_confidence = config.get('min_confidence', 0.7)
        self.max_position_size = config.get('max_position_size', 100)  # USDT
        self.stop_loss_percent = config.get('stop_loss_percent', 5)
        self.take_profit_percent = config.get('take_profit_percent', 10)
    
    def analyze_token(self, token: TokenInfo) -> Optional[TradingSignal]:
        """Analyze token and generate trading signal"""
        try:
            # Check if blacklisted
            if self.db.is_blacklisted(token.address):
                return None
            
            # Get price history
            price_history = self.detector.get_price_history(token.address, hours=1)
            
            # Save current price
            self.db.save_price_history(token.address, token.price_usd, token.volume_24h)
            
            # Check for shadow pump (fake volume)
            if self.detector.detect_shadow_pump(token, price_history):
                logger.warning(f"Shadow pump detected for {token.symbol}")
                self.db.add_to_blacklist(token.address, "Shadow pump detected (fake volume)")
                return None
            
            # Check RugCheck
            rugcheck_result = self.rugcheck.check_token(token.address)
            if rugcheck_result.get('is_rug') or rugcheck_result.get('risk_level') != 'GOOD':
                reason = f"RugCheck failed: {rugcheck_result.get('risk_level', 'UNKNOWN')}"
                logger.warning(f"Token {token.symbol} failed RugCheck: {reason}")
                self.db.add_to_blacklist(token.address, reason)
                return None
            
            # Detect pump
            is_pump = self.detector.detect_pump(token, price_history)
            is_dump = self.detector.detect_dump(token, price_history)
            
            signal_type = None
            confidence = 0.0
            reason = ""
            
            if is_pump:
                # Potential long opportunity (but be careful with pumps)
                # Only trade if liquidity is decent
                if token.liquidity > 50000 and token.volume_24h > 50000:
                    signal_type = "LONG"
                    confidence = min(0.8, 0.5 + (token.liquidity / 1000000) * 0.3)
                    reason = f"Pump detected: {token.price_change_24h:.2f}% price increase"
            
            elif is_dump:
                # Potential short opportunity
                if token.liquidity > 50000:
                    signal_type = "SHORT"
                    confidence = min(0.75, 0.5 + (token.liquidity / 1000000) * 0.25)
                    reason = f"Dump detected: {token.price_change_24h:.2f}% price decrease"
            
            # Also check for new pairs with good fundamentals
            if not is_pump and not is_dump:
                # Check if it's a new token with good metrics
                token_age = (datetime.now() - token.pair_created_at).total_seconds() / 3600
                if token_age < 24:  # New token (less than 24 hours old)
                    if (token.liquidity > 100000 and 
                        token.volume_24h > 100000 and 
                        token.price_change_24h > 0 and
                        token.price_change_24h < 50):  # Not too volatile
                        signal_type = "LONG"
                        confidence = 0.6
                        reason = f"New token with good fundamentals: {token.liquidity:.0f} liquidity"
            
            if signal_type and confidence >= self.min_confidence:
                # Calculate entry, stop loss, and take profit
                entry_price = token.price_usd
                stop_loss = entry_price * (1 - self.stop_loss_percent / 100) if signal_type == "LONG" else entry_price * (1 + self.stop_loss_percent / 100)
                take_profit = entry_price * (1 + self.take_profit_percent / 100) if signal_type == "LONG" else entry_price * (1 - self.take_profit_percent / 100)
                
                signal = TradingSignal(
                    symbol=token.symbol,
                    signal_type=signal_type,
                    confidence=confidence,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    reason=reason,
                    timestamp=datetime.now()
                )
                
                return signal
            
            return None
            
        except Exception as e:
            logger.error(f"Error analyzing token {token.symbol}: {e}")
            return None
    
    def execute_trade(self, signal: TradingSignal):
        """Execute trade on ByBit Futures"""
        if not self.bybit_client:
            logger.warning("ByBit client not initialized. Trade not executed.")
            return None
        
        try:
            # Convert symbol to ByBit format (e.g., BTC/USDT:USDT)
            symbol = signal.symbol.upper() + "/USDT:USDT"
            
            # Check if symbol exists on ByBit
            markets = self.bybit_client.load_markets()
            if symbol not in markets:
                logger.warning(f"Symbol {symbol} not found on ByBit Futures")
                return None
            
            # Calculate quantity
            quantity = self.max_position_size / signal.entry_price
            
            # Get market info for precision
            market = markets[symbol]
            amount_precision = market.get('precision', {}).get('amount', 8)
            quantity = round(quantity, amount_precision)
            
            # Place order
            side = "buy" if signal.signal_type == "LONG" else "sell"
            order_type = "market"  # Use market order for immediate execution
            
            logger.info(f"Placing {side} order for {symbol}: {quantity} @ {signal.entry_price}")
            
            order = self.bybit_client.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=quantity,
                params={'category': 'linear'}  # USDT perpetual futures
            )
            
            # Save trade to database
            signal_id = self.db.save_signal(signal)
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO trades (signal_id, symbol, trade_type, entry_price, quantity, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (signal_id, symbol, signal.signal_type, signal.entry_price, quantity, 'OPEN'))
            trade_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"Trade executed successfully. Order ID: {order.get('id', order.get('orderId', 'N/A'))}")
            return order
            
        except ccxt.BaseError as e:
            logger.error(f"ByBit API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return None
    
    def scan_new_tokens(self):
        """Scan for new tokens on DexScreener"""
        logger.info("Scanning for new tokens and analyzing market...")
        
        # Search for tokens with high volume
        trending_pairs = self.dexscreener.get_trending_tokens()
        
        if not trending_pairs:
            logger.warning("No pairs found from DexScreener")
            return
        
        new_tokens_found = 0
        signals_generated = 0
        blacklisted_count = 0
        
        logger.info(f"Analyzing {len(trending_pairs)} pairs from DexScreener...")
        
        for pair_data in trending_pairs:
            try:
                token = self.dexscreener.parse_token_info(pair_data)
                if not token:
                    continue
                
                # Skip if already blacklisted
                if self.db.is_blacklisted(token.address):
                    blacklisted_count += 1
                    continue
                
                # Save token to database
                self.db.save_token(token)
                new_tokens_found += 1
                
                # Check RugCheck first (to avoid unnecessary analysis)
                rugcheck_result = self.rugcheck.check_token(token.address)
                if rugcheck_result.get('is_rug') or rugcheck_result.get('honeypot'):
                    reason = f"RugCheck: {rugcheck_result.get('risk_level', 'UNSAFE')}"
                    self.db.add_to_blacklist(token.address, reason)
                    blacklisted_count += 1
                    continue
                
                # Analyze token
                signal = self.analyze_token(token)
                if signal:
                    signals_generated += 1
                    logger.info(f"✓ Signal: {signal.signal_type} {signal.symbol} "
                              f"(confidence: {signal.confidence:.2f}) - {signal.reason}")
                    
                    # Save signal
                    signal_id = self.db.save_signal(signal)
                    
                    # Execute trade if enabled
                    if self.config.get('auto_trade', False):
                        trade_result = self.execute_trade(signal)
                        if trade_result:
                            logger.info(f"Trade executed for {signal.symbol}")
                    else:
                        logger.info(f"Signal saved (auto_trade disabled): {signal.symbol}")
                
            except Exception as e:
                logger.error(f"Error processing pair: {e}")
                import traceback
                logger.debug(traceback.format_exc())
                continue
        
        logger.info(f"Scan complete: {new_tokens_found} tokens analyzed, "
                   f"{signals_generated} signals generated, "
                   f"{blacklisted_count} tokens blacklisted")
    
    def monitor_positions(self):
        """Monitor open positions and manage stop loss/take profit"""
        if not self.bybit_client:
            return
        
        try:
            # Get open positions from ByBit
            positions = self.bybit_client.fetch_positions()
            
            for position in positions:
                contract_size = float(position.get('contracts', 0))
                if contract_size == 0:
                    continue
                
                symbol = position.get('symbol', '')
                entry_price = float(position.get('entryPrice', 0))
                mark_price = float(position.get('markPrice', 0))
                unrealized_pnl = float(position.get('unrealizedPnl', 0))
                
                # Update trade in database
                conn = sqlite3.connect(self.db.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE trades 
                    SET exit_price = ?, pnl = ?
                    WHERE symbol = ? AND status = 'OPEN'
                ''', (mark_price, unrealized_pnl, symbol))
                conn.commit()
                conn.close()
                
                # Check stop loss and take profit (would need order management)
                # This is a simplified version
                
        except Exception as e:
            logger.error(f"Error monitoring positions: {e}")
    
    def run(self):
        """Main bot loop"""
        self.running = True
        logger.info("Trading bot started")
        
        scan_interval = self.config.get('scan_interval', 300)  # 5 minutes default
        
        while self.running:
            try:
                # Scan for new tokens
                self.scan_new_tokens()
                
                # Monitor positions
                self.monitor_positions()
                
                # Wait before next scan
                time.sleep(scan_interval)
                
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                self.running = False
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(60)  # Wait before retrying
    
    def stop(self):
        """Stop the bot"""
        self.running = False
        logger.info("Stopping trading bot...")


def load_config() -> Dict:
    """Load configuration from file or environment variables"""
    config = {
        'database_path': 'trading_bot.db',
        'scan_interval': 300,  # 5 minutes
        'min_confidence': 0.7,
        'max_position_size': 100,  # USDT
        'stop_loss_percent': 5,
        'take_profit_percent': 10,
        'auto_trade': False,  # Set to True to enable automatic trading
        'testnet': True,  # Use testnet by default
        'bybit_api_key': os.getenv('BYBIT_API_KEY', ''),
        'bybit_api_secret': os.getenv('BYBIT_API_SECRET', '')
    }
    
    # Try to load from config file
    if os.path.exists('config.json'):
        try:
            with open('config.json', 'r') as f:
                file_config = json.load(f)
                config.update(file_config)
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
    
    return config


if __name__ == "__main__":
    print("=" * 60)
    print("Advanced Crypto Futures Trading Bot")
    print("Professional trading bot with DexScreener integration")
    print("=" * 60)
    print()
    
    config = load_config()
    
    # Check if API keys are set
    if not config.get('bybit_api_key') or not config.get('bybit_api_secret'):
        print("WARNING: ByBit API keys not set!")
        print("Set BYBIT_API_KEY and BYBIT_API_SECRET environment variables")
        print("or add them to config.json")
        print()
        print("Bot will run in analysis mode only (no trading)")
        print()
    
    bot = TradingBot(config)
    
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()

