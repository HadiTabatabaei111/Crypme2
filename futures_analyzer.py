#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Futures Analyzer
Analyzes cryptocurrency futures using technical indicators
"""

import os
import sqlite3
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from technical_indicators import TechnicalIndicators
from bybit_client import BybitClient

logger = logging.getLogger(__name__)


class FuturesAnalyzer:
    """Analyze cryptocurrency futures using technical indicators"""
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None,
                 testnet: bool = False):
        """
        Initialize Futures Analyzer
        
        Args:
            api_key: Bitunix API key (optional; public endpoints don't need it)
            api_secret: Bitunix API secret (optional)
            testnet: Use testnet (default: False)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.bybit = BybitClient()
        
        self.indicators = TechnicalIndicators()
        self.db_path = os.getenv('DB_PATH', 'trading_bot.db')
        
        # Default parameters
        self.params = {
            'rsi_period': 14,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'ma_period': 20,
            'volume_ma_period': 20,
            'rsi_weight': 0.25,
            'macd_weight': 0.25,
            'price_weight': 0.25,
            'volume_weight': 0.15,
            'ma_weight': 0.10,
            'min_volume_ratio': 1.0,
            'min_score': 0.0
        }
    
    def load_params(self, params_file: str = 'futures_params.json'):
        """Load parameters from file"""
        if os.path.exists(params_file):
            try:
                with open(params_file, 'r') as f:
                    file_params = json.load(f)
                    self.params.update(file_params)
                logger.info(f"Loaded parameters from {params_file}")
            except Exception as e:
                logger.error(f"Error loading parameters: {e}")
    
    def save_params(self, params_file: str = 'futures_params.json'):
        """Save parameters to file"""
        try:
            with open(params_file, 'w') as f:
                json.dump(self.params, f, indent=2)
            logger.info(f"Saved parameters to {params_file}")
        except Exception as e:
            logger.error(f"Error saving parameters: {e}")
    
    def get_klines(self, symbol: str, interval: str, limit: int = 500) -> List[List]:
        """
        Get kline/candlestick data from Bybit
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            interval: Kline interval (1m, 5m, 15m, 1h, 4h, 1d, etc.)
            limit: Number of klines to retrieve (default: 500)
            
        Returns:
            List of klines
        """
        return self.bybit.get_klines(symbol, interval, limit, category="linear") or []
    
    def parse_klines(self, klines: List[List]) -> Dict[str, List[float]]:
        """
        Parse klines into price and volume data
        
        Args:
            klines: List of klines from Bybit
            
        Returns:
            Dictionary with 'prices', 'volumes', 'highs', 'lows', 'opens', 'closes'
        """
        if not klines:
            return {
                'prices': [],
                'volumes': [],
                'highs': [],
                'lows': [],
                'opens': [],
                'closes': []
            }
        
        prices = []
        volumes = []
        highs = []
        lows = []
        opens = []
        closes = []
        
        for kline in klines:
            opens.append(float(kline[1]))
            highs.append(float(kline[2]))
            lows.append(float(kline[3]))
            closes.append(float(kline[4]))
            volumes.append(float(kline[5]))
            prices.append(float(kline[4]))  # Use close price
        
        return {
            'prices': prices,
            'volumes': volumes,
            'highs': highs,
            'lows': lows,
            'opens': opens,
                'closes': closes
        }
    
    def analyze_symbol(self, symbol: str, timeframe: str = '15m') -> Optional[Dict]:
        """
        Analyze a symbol using technical indicators
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            timeframe: Timeframe (1m, 15m, 1d, etc.)
            
        Returns:
            Dictionary with analysis results
        """
        # Get klines
        klines = self.get_klines(symbol, timeframe, limit=500)
        if not klines:
            return None
        
        # Parse klines
        data = self.parse_klines(klines)
        if not data['prices']:
            return None
        
        prices = data['prices']
        volumes = data['volumes']
        
        # Calculate indicators
        rsi = self.indicators.calculate_rsi(prices, self.params['rsi_period'])
        macd = self.indicators.calculate_macd(
            prices,
            self.params['macd_fast'],
            self.params['macd_slow'],
            self.params['macd_signal']
        )
        ma = self.indicators.calculate_ma(prices, self.params['ma_period'])
        volume_ma = self.indicators.calculate_volume_ma(volumes, self.params['volume_ma_period'])
        
        # Calculate volume ratio
        current_volume = volumes[-1] if volumes else 0
        volume_ratio = self.indicators.calculate_volume_ratio(current_volume, volume_ma)
        
        # Calculate price change
        price_change = self.indicators.calculate_price_change(prices, 1)
        
        # Determine MA signal
        current_price = prices[-1]
        if current_price > ma * 1.02:  # 2% above MA
            ma_signal = 1  # Bullish
        elif current_price < ma * 0.98:  # 2% below MA
            ma_signal = -1  # Bearish
        else:
            ma_signal = 0  # Neutral
        
        # Calculate score
        score_data = self.indicators.calculate_score(
            rsi=rsi,
            macd_histogram=macd['histogram'],
            price_change=price_change,
            volume_ratio=volume_ratio,
            ma_signal=ma_signal,
            rsi_weight=self.params['rsi_weight'],
            macd_weight=self.params['macd_weight'],
            price_weight=self.params['price_weight'],
            volume_weight=self.params['volume_weight'],
            ma_weight=self.params['ma_weight']
        )
        
        # Determine signal
        if score_data['total_score'] > 20:
            signal = 'STRONG_BUY'
        elif score_data['total_score'] > 10:
            signal = 'BUY'
        elif score_data['total_score'] > -10:
            signal = 'NEUTRAL'
        elif score_data['total_score'] > -20:
            signal = 'SELL'
        else:
            signal = 'STRONG_SELL'
        
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'current_price': current_price,
            'price_change': price_change,
            'rsi': rsi,
            'macd': macd,
            'ma': ma,
            'ma_signal': ma_signal,
            'volume': current_volume,
            'volume_ma': volume_ma,
            'volume_ratio': volume_ratio,
            'score': score_data,
            'signal': signal,
            'timestamp': datetime.now().isoformat()
        }

        # Note: Unreachable, kept structure clarity
    
    def get_top_symbols(self, timeframes: List[str] = ['15m', '1m', '1d'],
                       min_volume: float = 1000000) -> List[Dict]:
        """
        Get top symbols for futures trading
        
        Args:
            timeframes: List of timeframes to analyze
            min_volume: Minimum 24h volume (default: 1M USDT)
            
        Returns:
            List of analyzed symbols sorted by score
        """
        try:
            symbols_meta = self.bybit.get_all_symbols(category="linear")
            tickers = self.bybit.get_all_24h_tickers(category="linear")
            ticker_dict = {t.get('symbol'): t for t in tickers} if isinstance(tickers, list) else {}

            symbols: List[Dict] = []
            for symbol_info in symbols_meta:
                symbol = symbol_info.get('symbol')
                status = symbol_info.get('status', 'Trading')
                if not symbol:
                    continue
                # USDT perpetuals and active
                if symbol and symbol.endswith('USDT') and status in ['Trading', 'TRADING']:
                    t = ticker_dict.get(symbol) or {}
                    try:
                        quote_volume = float(t.get('turnover24h') or t.get('volume24h') or 0.0)
                    except Exception:
                        quote_volume = 0.0
                    if quote_volume >= min_volume:
                        symbols.append({'symbol': symbol, 'volume_24h': quote_volume})
            
            # Sort by volume
            symbols.sort(key=lambda x: x['volume_24h'], reverse=True)
            
            # Analyze top symbols
            analyzed_symbols = []
            for symbol_data in symbols[:100]:  # Analyze top 100 by volume
                symbol = symbol_data['symbol']
                
                # Analyze for each timeframe
                timeframe_analyses = {}
                for timeframe in timeframes:
                    analysis = self.analyze_symbol(symbol, timeframe)
                    if analysis:
                        # Persist analysis
                        self.store_analysis(analysis)
                        timeframe_analyses[timeframe] = analysis
                
                if timeframe_analyses:
                    # Calculate average score
                    scores = [a['score']['total_score'] for a in timeframe_analyses.values()]
                    avg_score = sum(scores) / len(scores) if scores else 0
                    
                    analyzed_symbols.append({
                        'symbol': symbol,
                        'volume_24h': symbol_data['volume_24h'],
                        'timeframes': timeframe_analyses,
                        'avg_score': avg_score
                    })
            
            # Sort by average score
            analyzed_symbols.sort(key=lambda x: x['avg_score'], reverse=True)
            
            return analyzed_symbols
            
        except Exception as e:
            logger.error(f"Error getting top symbols: {e}")
            return []

    # ---------- Persistence ----------
    def store_analysis(self, analysis: Dict) -> None:
        """Persist OHLCV-derived indicators for a symbol/timeframe"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS futures_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    current_price REAL,
                    price_change REAL,
                    rsi REAL,
                    macd REAL,
                    macd_signal REAL,
                    macd_hist REAL,
                    ma REAL,
                    ma_signal INTEGER,
                    volume REAL,
                    volume_ma REAL,
                    volume_ratio REAL,
                    total_score REAL,
                    signal TEXT
                )
            """)
            cur.execute("""
                INSERT INTO futures_analysis
                (symbol, timeframe, timestamp, current_price, price_change, rsi, macd, macd_signal, macd_hist, ma, ma_signal, volume, volume_ma, volume_ratio, total_score, signal)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                analysis['symbol'],
                analysis['timeframe'],
                analysis['timestamp'],
                analysis.get('current_price'),
                analysis.get('price_change'),
                analysis.get('rsi'),
                analysis.get('macd', {}).get('macd'),
                analysis.get('macd', {}).get('signal'),
                analysis.get('macd', {}).get('histogram'),
                analysis.get('ma'),
                analysis.get('ma_signal'),
                analysis.get('volume'),
                analysis.get('volume_ma'),
                analysis.get('volume_ratio'),
                analysis.get('score', {}).get('total_score'),
                analysis.get('signal')
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug(f"Could not store analysis: {e}")

