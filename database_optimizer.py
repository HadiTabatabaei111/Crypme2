#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Optimizer
Adds indexes and optimizations to database
"""

import sqlite3
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class DatabaseOptimizer:
    """Database optimization utilities"""
    
    def __init__(self, db_path: str):
        """
        Initialize database optimizer
        
        Args:
            db_path: Path to database file
        """
        self.db_path = db_path
    
    def create_indexes(self):
        """Create indexes for better query performance"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            indexes = [
                # Tokens table indexes
                "CREATE INDEX IF NOT EXISTS idx_tokens_symbol ON tokens(symbol)",
                "CREATE INDEX IF NOT EXISTS idx_tokens_is_blacklisted ON tokens(is_blacklisted)",
                "CREATE INDEX IF NOT EXISTS idx_tokens_price_change ON tokens(price_change_24h)",
                "CREATE INDEX IF NOT EXISTS idx_tokens_last_updated ON tokens(last_updated)",
                "CREATE INDEX IF NOT EXISTS idx_tokens_volume ON tokens(volume_24h)",
                
                # Price history indexes
                "CREATE INDEX IF NOT EXISTS idx_price_history_address ON price_history(token_address)",
                "CREATE INDEX IF NOT EXISTS idx_price_history_timestamp ON price_history(timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_price_history_address_timestamp ON price_history(token_address, timestamp)",
                
                # Trading signals indexes
                "CREATE INDEX IF NOT EXISTS idx_signals_symbol ON trading_signals(symbol)",
                "CREATE INDEX IF NOT EXISTS idx_signals_type ON trading_signals(signal_type)",
                "CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON trading_signals(timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_signals_status ON trading_signals(status)",
                
                # Trades indexes
                "CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)",
                "CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)",
                "CREATE INDEX IF NOT EXISTS idx_trades_opened_at ON trades(opened_at)",
                
                # Blacklist indexes
                "CREATE INDEX IF NOT EXISTS idx_blacklist_address ON blacklist(token_address)",
            ]
            
            for index_sql in indexes:
                try:
                    cursor.execute(index_sql)
                    logger.debug(f"Created index: {index_sql.split()[5]}")
                except sqlite3.OperationalError as e:
                    logger.warning(f"Index creation skipped (may already exist): {e}")
            
            conn.commit()
            conn.close()
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
    
    def optimize_database(self):
        """Run database optimization commands"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Analyze tables for query optimization
            cursor.execute("ANALYZE")
            
            # Vacuum to reclaim space
            cursor.execute("VACUUM")
            
            conn.commit()
            conn.close()
            logger.info("Database optimized successfully")
            
        except Exception as e:
            logger.error(f"Error optimizing database: {e}")
    
    def get_table_stats(self) -> dict:
        """Get database table statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            stats = {}
            tables = ['tokens', 'price_history', 'trading_signals', 'trades', 'blacklist']
            
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    
                    # Get table size info
                    cursor.execute(f"SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='{table}'")
                    exists = cursor.fetchone()[0] > 0
                    
                    if exists:
                        stats[table] = {
                            'count': count,
                            'exists': True
                        }
                except sqlite3.OperationalError:
                    stats[table] = {
                        'count': 0,
                        'exists': False
                    }
            
            conn.close()
            return stats
            
        except Exception as e:
            logger.error(f"Error getting table stats: {e}")
            return {}

