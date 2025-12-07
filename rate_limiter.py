#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rate Limiter
Simple rate limiting for API endpoints
"""

import time
from collections import defaultdict
from typing import Dict, Tuple
import threading

logger = None
try:
    import logging
    logger = logging.getLogger(__name__)
except:
    pass


class RateLimiter:
    """Simple rate limiter"""
    
    def __init__(self, max_requests: int = 100, window: int = 60):
        """
        Initialize rate limiter
        
        Args:
            max_requests: Maximum requests per window
            window: Time window in seconds (default: 60)
        """
        self.max_requests = max_requests
        self.window = window
        self.requests: Dict[str, list] = defaultdict(list)
        self.lock = threading.Lock()
    
    def is_allowed(self, identifier: str) -> Tuple[bool, int]:
        """
        Check if request is allowed
        
        Args:
            identifier: Request identifier (IP, user ID, etc.)
            
        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        with self.lock:
            current_time = time.time()
            request_times = self.requests[identifier]
            
            # Remove old requests outside the window
            request_times[:] = [t for t in request_times if current_time - t < self.window]
            
            # Check if limit exceeded
            if len(request_times) >= self.max_requests:
                return False, 0
            
            # Add current request
            request_times.append(current_time)
            remaining = self.max_requests - len(request_times)
            
            return True, remaining
    
    def get_remaining(self, identifier: str) -> int:
        """Get remaining requests for identifier"""
        with self.lock:
            current_time = time.time()
            request_times = self.requests[identifier]
            request_times[:] = [t for t in request_times if current_time - t < self.window]
            return max(0, self.max_requests - len(request_times))
    
    def reset(self, identifier: str = None):
        """Reset rate limit for identifier or all"""
        with self.lock:
            if identifier:
                self.requests[identifier] = []
            else:
                self.requests.clear()


# Global rate limiter
rate_limiter = RateLimiter(max_requests=100, window=60)

