#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Technical Indicators Calculator
Calculates RSI, MACD, MA, and Volume indicators for trading analysis
"""

import numpy as np
from typing import List, Tuple, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class TechnicalIndicators:
    """Calculate technical indicators for trading analysis"""
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> float:
        """
        Calculate Relative Strength Index (RSI)
        
        Args:
            prices: List of closing prices
            period: RSI period (default: 14)
            
        Returns:
            RSI value (0-100)
        """
        if len(prices) < period + 1:
            return 50.0  # Neutral RSI if not enough data
        
        try:
            deltas = np.diff(prices)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            avg_gain = np.mean(gains[-period:])
            avg_loss = np.mean(losses[-period:])
            
            if avg_loss == 0:
                return 100.0
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return float(rsi)
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            return 50.0
    
    @staticmethod
    def calculate_macd(prices: List[float], fast_period: int = 12, 
                       slow_period: int = 26, signal_period: int = 9) -> Dict[str, float]:
        """
        Calculate MACD (Moving Average Convergence Divergence)
        
        Args:
            prices: List of closing prices
            fast_period: Fast EMA period (default: 12)
            slow_period: Slow EMA period (default: 26)
            signal_period: Signal line period (default: 9)
            
        Returns:
            Dictionary with 'macd', 'signal', and 'histogram' values
        """
        if len(prices) < slow_period + signal_period:
            return {'macd': 0.0, 'signal': 0.0, 'histogram': 0.0}
        
        try:
            prices_array = np.array(prices, dtype=float)
            
            # Calculate EMAs
            ema_fast = TechnicalIndicators._calculate_ema(prices_array, fast_period)
            ema_slow = TechnicalIndicators._calculate_ema(prices_array, slow_period)

            # Validate and align lengths (ema_slow is shorter or equal)
            if ema_fast.size == 0 or ema_slow.size == 0:
                return {'macd': 0.0, 'signal': 0.0, 'histogram': 0.0}

            # Align by trimming the fast EMA to the length of the slow EMA
            if ema_fast.size > ema_slow.size:
                ema_fast_aligned = ema_fast[-ema_slow.size:]
                ema_slow_aligned = ema_slow
            else:
                # If for any reason fast is shorter (shouldn't happen), align to fast
                ema_fast_aligned = ema_fast
                ema_slow_aligned = ema_slow[-ema_fast.size:]

            # MACD line
            macd_line = ema_fast_aligned - ema_slow_aligned  # numpy array

            # Signal line (EMA of full MACD series, not just the last window)
            signal_line = TechnicalIndicators._calculate_ema(macd_line, signal_period)
            if signal_line.size == 0:
                return {'macd': float(macd_line[-1]), 'signal': 0.0, 'histogram': float(macd_line[-1])}

            # Histogram
            histogram = macd_line[-1] - signal_line[-1]
            
            return {
                'macd': float(macd_line[-1]),
                'signal': float(signal_line[-1]),
                'histogram': float(histogram)
            }
        except Exception as e:
            logger.error(f"Error calculating MACD: {e}")
            return {'macd': 0.0, 'signal': 0.0, 'histogram': 0.0}
    
    @staticmethod
    def _calculate_ema(prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return np.array([])
        
        multiplier = 2 / (period + 1)
        ema = np.zeros(len(prices))
        ema[period - 1] = np.mean(prices[:period])
        
        for i in range(period, len(prices)):
            ema[i] = (prices[i] * multiplier) + (ema[i - 1] * (1 - multiplier))
        
        return ema[period - 1:]
    
    @staticmethod
    def calculate_ma(prices: List[float], period: int = 20) -> float:
        """
        Calculate Simple Moving Average (MA)
        
        Args:
            prices: List of closing prices
            period: MA period (default: 20)
            
        Returns:
            MA value
        """
        if len(prices) < period:
            return float(np.mean(prices)) if prices else 0.0
        
        try:
            return float(np.mean(prices[-period:]))
        except Exception as e:
            logger.error(f"Error calculating MA: {e}")
            return float(np.mean(prices)) if prices else 0.0
    
    @staticmethod
    def calculate_volume_ma(volumes: List[float], period: int = 20) -> float:
        """
        Calculate Volume Moving Average
        
        Args:
            volumes: List of volumes
            period: MA period (default: 20)
            
        Returns:
            Volume MA value
        """
        if len(volumes) < period:
            return float(np.mean(volumes)) if volumes else 0.0
        
        try:
            return float(np.mean(volumes[-period:]))
        except Exception as e:
            logger.error(f"Error calculating Volume MA: {e}")
            return float(np.mean(volumes)) if volumes else 0.0
    
    @staticmethod
    def calculate_volume_ratio(current_volume: float, avg_volume: float) -> float:
        """
        Calculate volume ratio (current volume / average volume)
        
        Args:
            current_volume: Current volume
            avg_volume: Average volume
            
        Returns:
            Volume ratio
        """
        if avg_volume == 0:
            return 1.0
        
        return current_volume / avg_volume
    
    @staticmethod
    def calculate_price_change(prices: List[float], periods: int = 1) -> float:
        """
        Calculate price change percentage
        
        Args:
            prices: List of closing prices
            periods: Number of periods to look back
            
        Returns:
            Price change percentage
        """
        if len(prices) < periods + 1:
            return 0.0
        
        try:
            old_price = prices[-(periods + 1)]
            new_price = prices[-1]
            
            if old_price == 0:
                return 0.0
            
            return ((new_price - old_price) / old_price) * 100
        except Exception as e:
            logger.error(f"Error calculating price change: {e}")
            return 0.0
    
    @staticmethod
    def calculate_score(rsi: float, macd_histogram: float, price_change: float,
                       volume_ratio: float, ma_signal: float,
                       rsi_weight: float = 0.25, macd_weight: float = 0.25,
                       price_weight: float = 0.25, volume_weight: float = 0.15,
                       ma_weight: float = 0.10) -> Dict[str, float]:
        """
        Calculate overall score for a token based on indicators
        
        Args:
            rsi: RSI value (0-100)
            macd_histogram: MACD histogram value
            price_change: Price change percentage
            volume_ratio: Volume ratio (current/avg)
            ma_signal: MA signal (-1 for below MA, 0 for neutral, 1 for above MA)
            rsi_weight: Weight for RSI (default: 0.25)
            macd_weight: Weight for MACD (default: 0.25)
            price_weight: Weight for price change (default: 0.25)
            volume_weight: Weight for volume (default: 0.15)
            ma_weight: Weight for MA (default: 0.10)
            
        Returns:
            Dictionary with individual scores and total score
        """
        try:
            # Normalize RSI score (30-70 is neutral, <30 oversold, >70 overbought)
            if rsi < 30:
                rsi_score = ((30 - rsi) / 30) * 50  # Oversold, good for LONG
            elif rsi > 70:
                rsi_score = -((rsi - 70) / 30) * 50  # Overbought, good for SHORT
            else:
                rsi_score = 0  # Neutral
            
            # MACD score (positive histogram is bullish, negative is bearish)
            macd_score = macd_histogram * 10  # Scale MACD histogram
            
            # Price change score (positive is good for LONG, negative for SHORT)
            price_score = price_change * 2  # Scale price change
            
            # Volume score (higher volume is better)
            if volume_ratio > 1.5:
                volume_score = 30  # High volume
            elif volume_ratio > 1.0:
                volume_score = 15  # Above average volume
            elif volume_ratio > 0.5:
                volume_score = 0  # Average volume
            else:
                volume_score = -15  # Low volume
            
            # MA score
            ma_score = ma_signal * 20  # -20, 0, or 20
            
            # Calculate weighted total score
            total_score = (
                rsi_score * rsi_weight +
                macd_score * macd_weight +
                price_score * price_weight +
                volume_score * volume_weight +
                ma_score * ma_weight
            )
            
            return {
                'rsi_score': rsi_score,
                'macd_score': macd_score,
                'price_score': price_score,
                'volume_score': volume_score,
                'ma_score': ma_score,
                'total_score': total_score
            }
        except Exception as e:
            logger.error(f"Error calculating score: {e}")
            return {
                'rsi_score': 0.0,
                'macd_score': 0.0,
                'price_score': 0.0,
                'volume_score': 0.0,
                'ma_score': 0.0,
                'total_score': 0.0
            }

