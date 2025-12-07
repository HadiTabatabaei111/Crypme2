#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cache Manager
Simple in-memory cache for API responses and database queries
"""

import time
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import threading

logger = None
try:
    import logging
    logger = logging.getLogger(__name__)
except:
    pass


class CacheManager:
    """Simple in-memory cache manager"""
    
    def __init__(self, default_ttl: int = 60):
        """
        Initialize cache manager
        
        Args:
            default_ttl: Default time-to-live in seconds (default: 60)
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
        self.lock = threading.Lock()
        self._cleanup_interval = 300  # Cleanup every 5 minutes
        self._last_cleanup = time.time()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                if time.time() < entry['expires_at']:
                    return entry['value']
                else:
                    # Expired, remove it
                    del self.cache[key]
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        with self.lock:
            ttl = ttl or self.default_ttl
            self.cache[key] = {
                'value': value,
                'expires_at': time.time() + ttl,
                'created_at': time.time()
            }
            
            # Periodic cleanup
            if time.time() - self._last_cleanup > self._cleanup_interval:
                self._cleanup()
    
    def delete(self, key: str):
        """Delete key from cache"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
    
    def clear(self):
        """Clear all cache"""
        with self.lock:
            self.cache.clear()
    
    def _cleanup(self):
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.cache.items()
            if current_time >= entry['expires_at']
        ]
        for key in expired_keys:
            del self.cache[key]
        
        self._last_cleanup = current_time
        if logger and expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            current_time = time.time()
            active_entries = sum(
                1 for entry in self.cache.values()
                if current_time < entry['expires_at']
            )
            expired_entries = len(self.cache) - active_entries
            
            return {
                'total_entries': len(self.cache),
                'active_entries': active_entries,
                'expired_entries': expired_entries,
                'memory_usage': len(str(self.cache))
            }


# Global cache instance
cache = CacheManager(default_ttl=60)

