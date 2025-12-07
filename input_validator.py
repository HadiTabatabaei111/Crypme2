#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Input Validator
Validates and sanitizes user inputs
"""

import re
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class InputValidator:
    """Input validation utilities"""
    
    @staticmethod
    def validate_symbol(symbol: str) -> bool:
        """
        Validate trading symbol format
        
        Args:
            symbol: Trading symbol
            
        Returns:
            True if valid, False otherwise
        """
        if not symbol or not isinstance(symbol, str):
            return False
        
        # Remove whitespace
        symbol = symbol.strip().upper()
        
        # Check length (typically 2-20 characters)
        if len(symbol) < 2 or len(symbol) > 20:
            return False
        
        # Check for valid characters (alphanumeric and dash)
        if not re.match(r'^[A-Z0-9\-]+$', symbol):
            return False
        
        return True
    
    @staticmethod
    def validate_price(price: Any) -> Optional[float]:
        """
        Validate and convert price
        
        Args:
            price: Price value
            
        Returns:
            Validated price as float or None
        """
        try:
            price_float = float(price)
            if price_float <= 0:
                return None
            if price_float > 1e10:  # Sanity check
                return None
            return price_float
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def validate_percent(percent: Any, min_val: float = -100, max_val: float = 100) -> Optional[float]:
        """
        Validate percentage value
        
        Args:
            percent: Percentage value
            min_val: Minimum value (default: -100)
            max_val: Maximum value (default: 100)
            
        Returns:
            Validated percentage or None
        """
        try:
            percent_float = float(percent)
            if percent_float < min_val or percent_float > max_val:
                return None
            return percent_float
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def validate_amount(amount: Any, min_val: float = 0.01, max_val: float = 1e6) -> Optional[float]:
        """
        Validate amount value
        
        Args:
            amount: Amount value
            min_val: Minimum value (default: 0.01)
            max_val: Maximum value (default: 1,000,000)
            
        Returns:
            Validated amount or None
        """
        try:
            amount_float = float(amount)
            if amount_float < min_val or amount_float > max_val:
                return None
            return amount_float
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def sanitize_string(text: str, max_length: int = 100) -> str:
        """
        Sanitize string input
        
        Args:
            text: Input text
            max_length: Maximum length
            
        Returns:
            Sanitized string
        """
        if not isinstance(text, str):
            return ""
        
        # Remove potentially harmful characters
        sanitized = re.sub(r'[<>"\']', '', text)
        
        # Limit length
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized.strip()
    
    @staticmethod
    def validate_limit_offset(limit: Any, offset: Any) -> tuple:
        """
        Validate limit and offset parameters
        
        Args:
            limit: Limit value
            offset: Offset value
            
        Returns:
            Tuple of (validated_limit, validated_offset)
        """
        try:
            limit_int = int(limit) if limit else 100
            offset_int = int(offset) if offset else 0
            
            # Clamp values
            limit_int = max(1, min(limit_int, 1000))  # Between 1 and 1000
            offset_int = max(0, offset_int)  # Non-negative
            
            return limit_int, offset_int
        except (ValueError, TypeError):
            return 100, 0
    
    @staticmethod
    def validate_timeframe(timeframe: str) -> bool:
        """
        Validate timeframe string
        
        Args:
            timeframe: Timeframe string (e.g., '1m', '15m', '1d')
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(timeframe, str):
            return False
        
        valid_timeframes = ['1m', '3m', '5m', '15m', '30m', '1h', '4h', '1d', '1w', '1M']
        return timeframe in valid_timeframes

