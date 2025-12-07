#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Performance Monitor
Monitors system performance and API response times
"""

import time
import functools
import logging
from typing import Dict, List, Callable
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Performance monitoring utility"""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = defaultdict(list)
        self.request_counts: Dict[str, int] = defaultdict(int)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.max_history = 1000  # Keep last 1000 measurements
    
    def record_time(self, operation: str, duration: float):
        """
        Record operation duration
        
        Args:
            operation: Operation name
            duration: Duration in seconds
        """
        self.metrics[operation].append(duration)
        if len(self.metrics[operation]) > self.max_history:
            self.metrics[operation].pop(0)
    
    def record_request(self, endpoint: str, success: bool = True):
        """
        Record API request
        
        Args:
            endpoint: API endpoint
            success: Whether request was successful
        """
        self.request_counts[endpoint] += 1
        if not success:
            self.error_counts[endpoint] += 1
    
    def get_stats(self, operation: str) -> Dict[str, float]:
        """
        Get statistics for an operation
        
        Args:
            operation: Operation name
            
        Returns:
            Statistics dictionary
        """
        if operation not in self.metrics or not self.metrics[operation]:
            return {
                'count': 0,
                'avg': 0,
                'min': 0,
                'max': 0,
                'total': 0
            }
        
        times = self.metrics[operation]
        return {
            'count': len(times),
            'avg': sum(times) / len(times),
            'min': min(times),
            'max': max(times),
            'total': sum(times)
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all operations"""
        return {op: self.get_stats(op) for op in self.metrics.keys()}
    
    def get_request_stats(self) -> Dict[str, Dict[str, int]]:
        """Get request statistics"""
        return {
            endpoint: {
                'total': self.request_counts[endpoint],
                'errors': self.error_counts.get(endpoint, 0),
                'success_rate': (self.request_counts[endpoint] - self.error_counts.get(endpoint, 0)) / self.request_counts[endpoint] * 100 if self.request_counts[endpoint] > 0 else 0
            }
            for endpoint in self.request_counts.keys()
        }
    
    def reset(self):
        """Reset all metrics"""
        self.metrics.clear()
        self.request_counts.clear()
        self.error_counts.clear()


# Global performance monitor
performance_monitor = PerformanceMonitor()


def monitor_performance(operation_name: str = None):
    """
    Decorator to monitor function performance
    
    Args:
        operation_name: Name for the operation (uses function name if None)
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            success = True
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                performance_monitor.record_request(op_name, success=False)
                raise
            finally:
                duration = time.time() - start_time
                performance_monitor.record_time(op_name, duration)
                performance_monitor.record_request(op_name, success=success)
        return wrapper
    return decorator

