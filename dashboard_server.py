#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crypto Trading Bot Dashboard Server
Beautiful and modern dashboard for displaying cryptocurrency data
"""

import os
import sqlite3
import json
import functools
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from typing import List, Dict, Optional
import logging

# Import futures analyzer
try:
    from futures_analyzer import FuturesAnalyzer
    FUTURES_ANALYZER_AVAILABLE = True
except ImportError:
    FUTURES_ANALYZER_AVAILABLE = False
    logging.warning("Futures analyzer not available")

# Import Nobitex trader
try:
    from nobitex_trader import NobitexTrader
    NOBITEX_TRADER_AVAILABLE = True
except ImportError:
    NOBITEX_TRADER_AVAILABLE = False
    logging.warning("Nobitex trader not available")

# Import Bitunix trader
try:
    from bitunix_trader import BitunixTrader
    BITUNIX_TRADER_AVAILABLE = True
except ImportError:
    BITUNIX_TRADER_AVAILABLE = False
    logging.warning("Bitunix trader not available")
# Import optimization modules
try:
    from cache_manager import cache
    from database_optimizer import DatabaseOptimizer
    from performance_monitor import performance_monitor, monitor_performance
    from input_validator import InputValidator
    from rate_limiter import rate_limiter
    OPTIMIZATION_AVAILABLE = True
except ImportError:
    OPTIMIZATION_AVAILABLE = False
    logging.warning("Optimization modules not available")
    cache = None
    performance_monitor = None
    monitor_performance = lambda x: lambda f: f  # No-op decorator
    InputValidator = None
    rate_limiter = None

# CoinGecko client
try:
    from coingecko_client import CoinGeckoClient
    COINGECKO_AVAILABLE = True
except ImportError:
    COINGECKO_AVAILABLE = False
    logging.warning("CoinGecko client not available")

# Initialize validator
validator = InputValidator() if OPTIMIZATION_AVAILABLE else None

# Rate limiting decorator
def rate_limit(max_requests: int = 100, window: int = 60):
    """Rate limiting decorator"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if rate_limiter:
                # Get client IP
                client_ip = request.remote_addr or 'unknown'
                allowed, remaining = rate_limiter.is_allowed(client_ip)
                
                if not allowed:
                    return jsonify({
                        'error': 'Rate limit exceeded',
                        'message': f'Too many requests. Please try again later.',
                        'remaining': 0
                    }), 429
                
                # Add remaining to response headers
                response = func(*args, **kwargs)
                if hasattr(response, 'headers'):
                    response.headers['X-RateLimit-Remaining'] = str(remaining)
                    response.headers['X-RateLimit-Limit'] = str(max_requests)
                return response
            else:
                return func(*args, **kwargs)
        return wrapper
    return decorator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Database path
DB_PATH = os.getenv('DB_PATH', 'trading_bot.db')


class DashboardDatabase:
    """Database manager for dashboard"""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
    
    def get_all_tokens(self, limit: int = 1000, offset: int = 0, 
                      filter_type: Optional[str] = None,
                      search: Optional[str] = None,
                      min_price_change: Optional[float] = None,
                      max_price_change: Optional[float] = None,
                      min_price: Optional[float] = None,
                      max_price: Optional[float] = None,
                      min_volume: Optional[float] = None,
                      max_volume: Optional[float] = None,
                      sort_by: Optional[str] = None,
                      sort_dir: str = 'DESC') -> List[Dict]:
        """Get all tokens with optional filters"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            # Optimized query using LEFT JOIN instead of subqueries
            query = '''
                SELECT t.*,
                       COUNT(DISTINCT CASE WHEN ts.signal_type = 'LONG' THEN ts.id END) as pump_signals,
                       COUNT(DISTINCT CASE WHEN ts.signal_type = 'SHORT' THEN ts.id END) as dump_signals
                FROM tokens t
                LEFT JOIN trading_signals ts ON ts.symbol = t.symbol
                WHERE t.is_blacklisted = 0
            '''
            
            params = []
            
            # Apply filters
            if filter_type == 'pump':
                query += ' AND t.price_change_24h > 15'
            elif filter_type == 'dump':
                query += ' AND t.price_change_24h < -15'
            elif filter_type == 'pumped':
                query += ' AND t.price_change_24h > 20'
            elif filter_type == 'dumped':
                query += ' AND t.price_change_24h < -20'
            
            if search:
                query += ' AND (t.symbol LIKE ? OR t.name LIKE ?)'
                params.extend([f'%{search}%', f'%{search}%'])
            
            if min_price_change is not None:
                query += ' AND t.price_change_24h >= ?'
                params.append(min_price_change)
            
            if max_price_change is not None:
                query += ' AND t.price_change_24h <= ?'
                params.append(max_price_change)

            if min_price is not None:
                query += ' AND t.price >= ?'
                params.append(min_price)

            if max_price is not None:
                query += ' AND t.price <= ?'
                params.append(max_price)

            if min_volume is not None:
                query += ' AND t.volume_24h >= ?'
                params.append(min_volume)

            if max_volume is not None:
                query += ' AND t.volume_24h <= ?'
                params.append(max_volume)
            
            # Sorting whitelist
            sort_map = {
                'symbol': 't.symbol',
                'name': 't.name',
                'price': 't.price',
                'price_change_24h': 't.price_change_24h',
                'volume_24h': 't.volume_24h',
                'last_updated': 't.last_updated'
            }
            order_col = sort_map.get(sort_by or '', 't.last_updated')
            order_dir = 'ASC' if str(sort_dir).upper() == 'ASC' else 'DESC'

            query += f' GROUP BY t.id ORDER BY {order_col} {order_dir} LIMIT ? OFFSET ?'
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            tokens = []
            for row in rows:
                token = dict(row)
                # Convert datetime strings to timestamps
                if token.get('first_seen'):
                    try:
                        token['first_seen'] = datetime.fromisoformat(token['first_seen']).timestamp()
                    except:
                        pass
                if token.get('last_updated'):
                    try:
                        token['last_updated'] = datetime.fromisoformat(token['last_updated']).timestamp()
                    except:
                        pass
                
                # Determine if pump or dump based on price change
                price_change = token.get('price_change_24h', 0)
                if price_change > 15:
                    token['type'] = 'pump'
                elif price_change < -15:
                    token['type'] = 'dump'
                else:
                    token['type'] = 'normal'
                
                tokens.append(token)
            
            conn.close()
            return tokens
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            if 'conn' in locals():
                conn.close()
            return []
        except Exception as e:
            logger.error(f"Error in get_all_tokens: {e}")
            if 'conn' in locals():
                conn.close()
            return []
    
    def get_token_count(self, filter_type: Optional[str] = None,
                       search: Optional[str] = None,
                       min_price_change: Optional[float] = None,
                       max_price_change: Optional[float] = None) -> int:
        """Get total token count with filters"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = 'SELECT COUNT(*) FROM tokens WHERE is_blacklisted = 0'
        params = []
        
        if filter_type == 'pump':
            query += ' AND price_change_24h > 15'
        elif filter_type == 'dump':
            query += ' AND price_change_24h < -15'
        elif filter_type == 'pumped':
            query += ' AND price_change_24h > 20'
        elif filter_type == 'dumped':
            query += ' AND price_change_24h < -20'
        
        if search:
            query += ' AND (symbol LIKE ? OR name LIKE ?)'
            params.extend([f'%{search}%', f'%{search}%'])
        
        if min_price_change is not None:
            query += ' AND price_change_24h >= ?'
            params.append(min_price_change)
        
        if max_price_change is not None:
            query += ' AND price_change_24h <= ?'
            params.append(max_price_change)
        
        cursor.execute(query, params)
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_price_history(self, token_address: str, hours: int = 24) -> List[Dict]:
        """Get price history for a token"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT price, volume, timestamp 
            FROM price_history
            WHERE token_address = ?
            AND timestamp >= datetime('now', '-{} hours')
            ORDER BY timestamp ASC
        '''.format(hours), (token_address,))
        
        rows = cursor.fetchall()
        history = []
        for row in rows:
            item = dict(row)
            # Convert datetime to timestamp
            if item.get('timestamp'):
                try:
                    dt = datetime.fromisoformat(item['timestamp'])
                    item['timestamp'] = dt.timestamp() * 1000  # Convert to milliseconds
                except:
                    pass
            history.append(item)
        
        conn.close()
        return history
    
    def get_statistics(self) -> Dict:
        """Get dashboard statistics - Optimized with single query"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Optimized: Use single query with aggregations
            cursor.execute('''
                SELECT 
                    (SELECT COUNT(*) FROM tokens WHERE is_blacklisted = 0) as total_tokens,
                    (SELECT COUNT(*) FROM tokens WHERE price_change_24h > 20 AND is_blacklisted = 0) as pumped_tokens,
                    (SELECT COUNT(*) FROM tokens WHERE price_change_24h < -20 AND is_blacklisted = 0) as dumped_tokens,
                    (SELECT COUNT(*) FROM trading_signals) as total_signals,
                    (SELECT COUNT(*) FROM trading_signals WHERE signal_type = 'LONG') as pump_signals,
                    (SELECT COUNT(*) FROM trading_signals WHERE signal_type = 'SHORT') as dump_signals,
                    (SELECT COUNT(*) FROM trades) as total_trades,
                    (SELECT COUNT(*) FROM trades WHERE status = 'OPEN') as open_trades,
                    (SELECT COALESCE(SUM(pnl), 0) FROM trades WHERE pnl IS NOT NULL) as total_pnl,
                    (SELECT COALESCE(AVG(price_change_24h), 0) FROM tokens WHERE is_blacklisted = 0) as avg_price_change
            ''')
            
            row = cursor.fetchone()
            stats = {
                'total_tokens': row[0] or 0,
                'pumped_tokens': row[1] or 0,
                'dumped_tokens': row[2] or 0,
                'total_signals': row[3] or 0,
                'pump_signals': row[4] or 0,
                'dump_signals': row[5] or 0,
                'total_trades': row[6] or 0,
                'open_trades': row[7] or 0,
                'total_pnl': row[8] or 0,
                'avg_price_change': row[9] or 0
            }
            
            conn.close()
            return stats
        except Exception as e:
            logger.error(f"Error in get_statistics: {e}")
            return {
                'total_tokens': 0,
                'pumped_tokens': 0,
                'dumped_tokens': 0,
                'total_signals': 0,
                'pump_signals': 0,
                'dump_signals': 0,
                'total_trades': 0,
                'open_trades': 0,
                'total_pnl': 0,
                'avg_price_change': 0
            }
    
    def get_pumped_tokens(self, limit: int = 50) -> List[Dict]:
        """Get top pumped tokens"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM tokens
            WHERE price_change_24h > 15 AND is_blacklisted = 0
            ORDER BY price_change_24h DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        tokens = [dict(row) for row in rows]
        conn.close()
        return tokens
    
    def get_dumped_tokens(self, limit: int = 50) -> List[Dict]:
        """Get top dumped tokens"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM tokens
            WHERE price_change_24h < -15 AND is_blacklisted = 0
            ORDER BY price_change_24h ASC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        tokens = [dict(row) for row in rows]
        conn.close()
        return tokens


# Initialize database
db = DashboardDatabase()

# Optimize database (create indexes)
if OPTIMIZATION_AVAILABLE:
    try:
        optimizer = DatabaseOptimizer(DB_PATH)
        optimizer.create_indexes()
        logger.info("Database optimization completed")
    except Exception as e:
        logger.warning(f"Database optimization skipped: {e}")

# Initialize CoinGecko
cg = None
if COINGECKO_AVAILABLE:
    try:
        cg = CoinGeckoClient()
        logger.info("CoinGecko client initialized")
    except Exception as e:
        logger.warning(f"CoinGecko init skipped: {e}")
        cg = None

# Initialize futures analyzer
futures_analyzer = None
if FUTURES_ANALYZER_AVAILABLE:
    try:
        # Try to load config for ByBit API keys
        config = {}
        if os.path.exists('config.json'):
            with open('config.json', 'r') as f:
                config = json.load(f)
        
        futures_analyzer = FuturesAnalyzer(
            api_key=config.get('bybit_api_key') or os.getenv('BYBIT_API_KEY'),
            api_secret=config.get('bybit_api_secret') or os.getenv('BYBIT_API_SECRET'),
            testnet=config.get('testnet', False)
        )
        futures_analyzer.load_params()
        logger.info("Futures analyzer initialized")
    except Exception as e:
        logger.error(f"Error initializing futures analyzer: {e}")
        futures_analyzer = None

# Initialize Nobitex trader
nobitex_trader = None
if NOBITEX_TRADER_AVAILABLE:
    try:
        # Try to load config for Nobitex API keys
        config = {}
        if os.path.exists('config.json'):
            with open('config.json', 'r') as f:
                config = json.load(f)
        
        nobitex_api_key = config.get('nobitex_api_key') or os.getenv('NOBITEX_API_KEY')
        nobitex_api_secret = config.get('nobitex_api_secret') or os.getenv('NOBITEX_API_SECRET')
        
        if nobitex_api_key and nobitex_api_secret:
            nobitex_trader = NobitexTrader(
                api_key=nobitex_api_key,
                api_secret=nobitex_api_secret,
                testnet=config.get('nobitex_testnet', False)
            )
            logger.info("Nobitex trader initialized")
        else:
            logger.warning("Nobitex API keys not found")
    except Exception as e:
        logger.error(f"Error initializing Nobitex trader: {e}")
        nobitex_trader = None

# Initialize Bitunix trader (preferred for trading and auto-trading)
bitunix_trader = None
if BITUNIX_TRADER_AVAILABLE:
    try:
        config = {}
        if os.path.exists('config.json'):
            with open('config.json', 'r') as f:
                config = json.load(f)
        bitunix_api_key = config.get('bitunix_api_key') or os.getenv('BITUNIX_API_KEY', '')
        bitunix_api_secret = config.get('bitunix_api_secret') or os.getenv('BITUNIX_API_SECRET', '')
        bitunix_trader = BitunixTrader(api_key=bitunix_api_key, api_secret=bitunix_api_secret, testnet=config.get('bitunix_testnet', False))
        logger.info("Bitunix trader initialized")
    except Exception as e:
        logger.error(f"Error initializing Bitunix trader: {e}")
        bitunix_trader = None

# Initialize Bybit client for market data
bybit_client = None
try:
    from bybit_client import BybitClient
    bybit_client = BybitClient()
    logger.info("Bybit client initialized")
except Exception as e:
    logger.error(f"Error initializing Bybit client: {e}")
    bybit_client = None


@app.route('/')
def index():
    """Render main dashboard page"""
    return render_template('dashboard.html')


@app.route('/about')
def about():
    """Render about page"""
    return render_template('about.html')


@app.route('/optimization')
def optimization():
    """Render optimization page"""
    return render_template('optimization.html')


@app.route('/auto-trade')
def auto_trade_page():
    """Render auto-trade params page"""
    return render_template('auto_trade.html')


@app.route('/settings')
def settings_page():
    return render_template('settings.html')


@app.route('/api/tokens', methods=['GET'])
@monitor_performance('get_tokens')
@rate_limit(max_requests=200, window=60)
def get_tokens():
    """Get tokens with filters"""
    try:
        # Validate inputs
        if validator:
            limit, offset = validator.validate_limit_offset(
                request.args.get('limit', 100),
                request.args.get('offset', 0)
            )
            search = validator.sanitize_string(request.args.get('search', '')) if request.args.get('search') else None
        else:
            limit = int(request.args.get('limit', 100))
            offset = int(request.args.get('offset', 0))
            search = request.args.get('search', None)
        
        filter_type = request.args.get('filter', None)
        if filter_type and filter_type not in ['pump', 'dump', 'pumped', 'dumped']:
            filter_type = None
        
        min_price_change = None
        max_price_change = None
        min_price = None
        max_price = None
        min_volume = None
        max_volume = None
        sort_by = request.args.get('sort_by', None)
        sort_dir = request.args.get('sort_dir', 'DESC')
        
        if request.args.get('min_price_change'):
            min_price_change = validator.validate_percent(request.args.get('min_price_change'), -100, 1000) if validator else float(request.args.get('min_price_change'))
        
        if request.args.get('max_price_change'):
            max_price_change = validator.validate_percent(request.args.get('max_price_change'), -100, 1000) if validator else float(request.args.get('max_price_change'))

        def parse_float(val):
            try:
                return float(val)
            except Exception:
                return None

        if request.args.get('min_price'):
            min_price = parse_float(request.args.get('min_price'))
        if request.args.get('max_price'):
            max_price = parse_float(request.args.get('max_price'))
        if request.args.get('min_volume'):
            min_volume = parse_float(request.args.get('min_volume'))
        if request.args.get('max_volume'):
            max_volume = parse_float(request.args.get('max_volume'))
        
        # Create cache key
        cache_key = f"tokens:{limit}:{offset}:{filter_type}:{search}:{min_price_change}:{max_price_change}:{min_price}:{max_price}:{min_volume}:{max_volume}:{sort_by}:{sort_dir}"
        
        # Try to get from cache
        if cache:
            cached_result = cache.get(cache_key)
            if cached_result:
                return jsonify(cached_result)
        
        tokens = db.get_all_tokens(
            limit=limit,
            offset=offset,
            filter_type=filter_type,
            search=search,
            min_price_change=min_price_change,
            max_price_change=max_price_change,
            min_price=min_price,
            max_price=max_price,
            min_volume=min_volume,
            max_volume=max_volume,
            sort_by=sort_by,
            sort_dir=sort_dir
        )
        
        total = db.get_token_count(
            filter_type=filter_type,
            search=search,
            min_price_change=min_price_change,
            max_price_change=max_price_change
        )
        
        result = {
            'tokens': tokens,
            'total': total,
            'limit': limit,
            'offset': offset
        }
        
        # Cache result for 30 seconds
        if cache:
            cache.set(cache_key, result, ttl=30)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting tokens: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/price-history/<token_address>', methods=['GET'])
def get_price_history(token_address):
    """Get price history for a token"""
    try:
        hours = int(request.args.get('hours', 24))
        history = db.get_price_history(token_address, hours=hours)
        return jsonify({'history': history})
    except Exception as e:
        logger.error(f"Error getting price history: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/statistics', methods=['GET'])
@monitor_performance('get_statistics')
def get_statistics():
    """Get dashboard statistics"""
    try:
        # Try to get from cache
        cache_key = 'statistics'
        if cache:
            cached_stats = cache.get(cache_key)
            if cached_stats:
                return jsonify(cached_stats)
        
        stats = db.get_statistics()
        
        # Cache for 60 seconds
        if cache:
            cache.set(cache_key, stats, ttl=60)
        
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/pumped', methods=['GET'])
def get_pumped_tokens():
    """Get pumped tokens"""
    try:
        limit = int(request.args.get('limit', 50))
        tokens = db.get_pumped_tokens(limit=limit)
        return jsonify({'tokens': tokens})
    except Exception as e:
        logger.error(f"Error getting pumped tokens: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/dumped', methods=['GET'])
def get_dumped_tokens():
    """Get dumped tokens"""
    try:
        limit = int(request.args.get('limit', 50))
        tokens = db.get_dumped_tokens(limit=limit)
        return jsonify({'tokens': tokens})
    except Exception as e:
        logger.error(f"Error getting dumped tokens: {e}")
        return jsonify({'error': str(e)}), 500


# Futures Analysis Routes
@app.route('/futures')
def futures_page():
    """Render futures analysis page"""
    return render_template('futures.html')


@app.route('/api/futures/analyze', methods=['GET'])
@monitor_performance('analyze_futures')
@rate_limit(max_requests=50, window=60)
def analyze_futures():
    """Analyze futures symbols"""
    if not futures_analyzer:
        return jsonify({'error': 'Futures analyzer not available'}), 503
    
    try:
        timeframes = request.args.get('timeframes', '15m,1m,1d').split(',')
        min_volume = float(request.args.get('min_volume', 1000000))
        limit = int(request.args.get('limit', 50))
        min_score = request.args.get('min_score')
        
        # Create cache key
        cache_key = f"futures_analyze:{timeframes}:{min_volume}:{limit}:{min_score}"
        
        # Try to get from cache (longer cache for analysis - 2 minutes)
        if cache:
            cached_result = cache.get(cache_key)
            if cached_result:
                return jsonify(cached_result)
        
        symbols = futures_analyzer.get_top_symbols(timeframes=timeframes, min_volume=min_volume)
        
        # Filter by min_score if provided
        if min_score:
            min_score = float(min_score)
            symbols = [s for s in symbols if s['avg_score'] >= min_score]
        
        result = {
            'symbols': symbols[:limit],
            'total': len(symbols)
        }
        
        # Cache result for 2 minutes (analysis takes longer)
        if cache:
            cache.set(cache_key, result, ttl=120)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error analyzing futures: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/futures/analyze-symbol', methods=['GET'])
def analyze_symbol():
    """Analyze a specific symbol"""
    if not futures_analyzer:
        return jsonify({'error': 'Futures analyzer not available'}), 503
    
    try:
        symbol = request.args.get('symbol')
        timeframe = request.args.get('timeframe', '15m')
        
        if not symbol:
            return jsonify({'error': 'Symbol parameter required'}), 400
        
        analysis = futures_analyzer.analyze_symbol(symbol, timeframe)
        
        if not analysis:
            return jsonify({'error': 'Could not analyze symbol'}), 404
        
        return jsonify(analysis)
    except Exception as e:
        logger.error(f"Error analyzing symbol: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/futures/params', methods=['GET', 'POST'])
def futures_params():
    """Get or update futures analysis parameters"""
    if not futures_analyzer:
        return jsonify({'error': 'Futures analyzer not available'}), 503
    
    try:
        if request.method == 'GET':
            return jsonify(futures_analyzer.params)
        else:
            # POST - update parameters
            new_params = request.get_json()
            if new_params:
                futures_analyzer.params.update(new_params)
                futures_analyzer.save_params()
                return jsonify({'success': True, 'params': futures_analyzer.params})
            return jsonify({'error': 'No parameters provided'}), 400
    except Exception as e:
        logger.error(f"Error handling futures params: {e}")
        return jsonify({'error': str(e)}), 500


# Auto-Trade Params
@app.route('/api/auto-trade/params', methods=['GET', 'POST'])
def auto_trade_params():
    """Get or update auto-trade parameters"""
    params_file = 'auto_trade_params.json'
    try:
        if request.method == 'GET':
            if os.path.exists(params_file):
                with open(params_file, 'r', encoding='utf-8') as f:
                    return jsonify(json.load(f))
            return jsonify({
                'entry_percent': 0.0,
                'stop_loss_percent': 2.0,
                'take_profit_percent': 4.0,
                'wallet_risk_percent': 2.0
            })
        else:
            new_params = request.get_json() or {}
            with open(params_file, 'w', encoding='utf-8') as f:
                json.dump(new_params, f, ensure_ascii=False, indent=2)
            return jsonify({'success': True, 'params': new_params})
    except Exception as e:
        logger.error(f"Error handling auto-trade params: {e}")
        return jsonify({'error': str(e)}), 500

# Nobitex Trading Routes
@app.route('/api/bitunix/klines', methods=['GET'])
def get_bitunix_klines():
    """Get klines from Bitunix for chart"""
    if not bitunix_trader:
        return jsonify({'error': 'Bitunix trader not available'}), 503
    
    try:
        symbol = request.args.get('symbol')
        interval = request.args.get('interval', '1')  # 1 minute
        limit = int(request.args.get('limit', 200))
        
        # Validate inputs
        if not symbol:
            return jsonify({'error': 'Symbol parameter required'}), 400
        
        if validator:
            if not validator.validate_symbol(symbol):
                return jsonify({'error': 'Invalid symbol format'}), 400
            
            if not validator.validate_timeframe(interval) and interval not in ['1', '3', '5', '15', '30', '60']:
                interval = '1'
            
            limit = min(max(1, limit), 500)  # Clamp between 1 and 500
        
        klines = bitunix_trader.get_klines(symbol, interval, limit)
        
        if not klines:
            return jsonify({'klines': [], 'error': 'No klines data available'})
        
        # Parse klines to standard format
        parsed_klines = klines
        
        # Parse klines for chart
        chart_data = []
        for kline in parsed_klines:
            try:
                # Handle both list and dict formats
                if isinstance(kline, list) and len(kline) >= 6:
                    chart_data.append({
                        'time': int(kline[0]),
                        'open': float(kline[1]),
                        'high': float(kline[2]),
                        'low': float(kline[3]),
                        'close': float(kline[4]),
                        'volume': float(kline[5])
                    })
                elif isinstance(kline, dict):
                    chart_data.append({
                        'time': int(kline.get('time', kline.get('timestamp', 0))),
                        'open': float(kline.get('open', 0)),
                        'high': float(kline.get('high', 0)),
                        'low': float(kline.get('low', 0)),
                        'close': float(kline.get('close', 0)),
                        'volume': float(kline.get('volume', 0))
                    })
            except Exception as e:
                logger.warning(f"Error parsing kline: {e}")
                continue
        
        return jsonify({'klines': chart_data})
    except Exception as e:
        logger.error(f"Error getting Bitunix klines: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/bybit/klines', methods=['GET'])
def get_bybit_klines():
    if not bybit_client:
        return jsonify({'error': 'Bybit client not available'}), 503
    try:
        symbol = request.args.get('symbol')
        interval = request.args.get('interval', '1')
        limit = int(request.args.get('limit', 200))
        if not symbol:
            return jsonify({'error': 'Symbol parameter required'}), 400
        if validator:
            if not validator.validate_symbol(symbol):
                return jsonify({'error': 'Invalid symbol format'}), 400
            limit = min(max(1, limit), 500)
        klines = bybit_client.get_klines(symbol, interval, limit, category='linear')
        chart_data = []
        for kline in klines:
            try:
                chart_data.append({
                    'time': int(kline[0]),
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5])
                })
            except Exception:
                continue
        return jsonify({'klines': chart_data})
    except Exception as e:
        logger.error(f"Error getting Bybit klines: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/bitunix/price', methods=['GET'])
def get_bitunix_price():
    """Get current price from Bitunix"""
    if not bitunix_trader:
        return jsonify({'error': 'Bitunix trader not available'}), 503
    
    try:
        symbol = request.args.get('symbol')
        if not symbol:
            return jsonify({'error': 'Symbol parameter required'}), 400
        
        price = bitunix_trader.get_current_price(symbol)
        if price is None:
            return jsonify({'error': 'Could not get price'}), 404
        
        return jsonify({'price': price})
    except Exception as e:
        logger.error(f"Error getting Bitunix price: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/bitunix/calculate', methods=['POST'])
def calculate_trade():
    """Calculate entry, stop loss, and take profit prices"""
    if not bitunix_trader:
        return jsonify({'error': 'Bitunix trader not available'}), 503
    
    try:
        data = request.get_json()
        symbol = data.get('symbol')
        current_price = float(data.get('current_price', 0))
        entry_percent = float(data.get('entry_percent', 0))
        stop_loss_percent = float(data.get('stop_loss_percent', 2))
        take_profit_percent = float(data.get('take_profit_percent', 4))
        side = data.get('side', 'Buy')
        
        if not symbol or current_price == 0:
            return jsonify({'error': 'Invalid parameters'}), 400
        
        result = bitunix_trader.calculate_entry_stop_take(
            current_price=current_price,
            entry_percent=entry_percent,
            stop_loss_percent=stop_loss_percent,
            take_profit_percent=take_profit_percent,
            side=side
        )
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error calculating trade: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/bitunix/place-order', methods=['POST'])
def place_bitunix_order():
    """Place an order on Bitunix"""
    if not bitunix_trader:
        return jsonify({'error': 'Bitunix trader not available'}), 503
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        symbol = data.get('symbol')
        side = data.get('side', 'Buy')
        order_type = data.get('order_type', 'Market')
        
        # Validate inputs
        if validator:
            if not symbol or not validator.validate_symbol(symbol):
                return jsonify({'error': 'Invalid symbol'}), 400
            
            if side not in ['Buy', 'Sell', 'buy', 'sell']:
                return jsonify({'error': 'Invalid side'}), 400
            
            if order_type not in ['Market', 'Limit', 'market', 'limit']:
                return jsonify({'error': 'Invalid order type'}), 400
            
            usd_amount = validator.validate_amount(data.get('usd_amount', 0), min_val=10, max_val=100000)
            entry_percent = validator.validate_percent(data.get('entry_percent', 0), -10, 10)
            stop_loss_percent = validator.validate_percent(data.get('stop_loss_percent', 2), 0.1, 20)
            take_profit_percent = validator.validate_percent(data.get('take_profit_percent', 4), 0.1, 50)
        else:
            usd_amount = float(data.get('usd_amount', 0))
            entry_percent = float(data.get('entry_percent', 0))
            stop_loss_percent = float(data.get('stop_loss_percent', 2))
            take_profit_percent = float(data.get('take_profit_percent', 4))
        
        if not usd_amount or usd_amount == 0:
            return jsonify({'error': 'Invalid amount'}), 400
        
        if entry_percent is None or stop_loss_percent is None or take_profit_percent is None:
            return jsonify({'error': 'Invalid percentage values'}), 400
        
        # Get current price
        current_price = bitunix_trader.get_current_price(symbol)
        if not current_price:
            return jsonify({'error': 'Could not get current price'}), 404
        
        # Calculate prices
        prices = bitunix_trader.calculate_entry_stop_take(
            current_price=current_price,
            entry_percent=entry_percent,
            stop_loss_percent=stop_loss_percent,
            take_profit_percent=take_profit_percent,
            side=side
        )
        
        # Calculate position size
        qty = bitunix_trader.calculate_position_size(
            symbol=symbol,
            usd_amount=usd_amount,
            current_price=prices['entry_price']
        )
        
        # Place order
        result = bitunix_trader.place_order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            qty=qty,
            price=prices['entry_price'] if order_type == 'Limit' else None,
            stop_loss=prices['stop_loss'],
            take_profit=prices['take_profit']
        )
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error placing order: {e}")
        return jsonify({'error': str(e), 'success': False}), 500


# Performance monitoring routes
@app.route('/api/performance/stats', methods=['GET'])
def get_performance_stats():
    """Get performance statistics"""
    if not OPTIMIZATION_AVAILABLE or not performance_monitor:
        return jsonify({'error': 'Performance monitoring not available'}), 503
    
    try:
        return jsonify({
            'operations': performance_monitor.get_all_stats(),
            'requests': performance_monitor.get_request_stats()
        })
    except Exception as e:
        logger.error(f"Error getting performance stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/cache/stats', methods=['GET'])
def get_cache_stats():
    """Get cache statistics"""
    if not OPTIMIZATION_AVAILABLE or not cache:
        return jsonify({'error': 'Cache not available'}), 503
    
    try:
        return jsonify(cache.get_stats())
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Clear cache"""
    if not OPTIMIZATION_AVAILABLE or not cache:
        return jsonify({'error': 'Cache not available'}), 503
    
    try:
        cache.clear()
        return jsonify({'success': True, 'message': 'Cache cleared'})
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/bitunix/keys', methods=['GET', 'POST'])
def bitunix_keys():
    try:
        conf = {}
        if os.path.exists('config.json'):
            with open('config.json', 'r') as f:
                conf = json.load(f)
        if request.method == 'GET':
            return jsonify({
                'bitunix_api_key': conf.get('bitunix_api_key') or os.getenv('BITUNIX_API_KEY', ''),
                'bitunix_api_secret': ''
            })
        data = request.get_json() or {}
        api_key = data.get('bitunix_api_key', '')
        api_secret = data.get('bitunix_api_secret', '')
        conf['bitunix_api_key'] = api_key
        conf['bitunix_api_secret'] = api_secret
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(conf, f, ensure_ascii=False, indent=2)
        os.environ['BITUNIX_API_KEY'] = api_key
        os.environ['BITUNIX_API_SECRET'] = api_secret
        global bitunix_trader
        bitunix_trader = BitunixTrader(api_key=api_key, api_secret=api_secret, testnet=conf.get('bitunix_testnet', False))
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error handling bitunix keys: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/db/tables', methods=['GET'])
def list_tables():
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
        rows = cur.fetchall()
        conn.close()
        tables = [r[0] for r in rows]
        return jsonify({'tables': tables})
    except Exception as e:
        logger.error(f"Error listing tables: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/db/table/<table_name>', methods=['GET'])
def get_table_data(table_name):
    try:
        limit = int(request.args.get('limit', 200))
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM {table_name} LIMIT ?", (limit,))
        rows = cur.fetchall()
        conn.close()
        if not rows:
            return jsonify({'columns': [], 'rows': []})
        cols = rows[0].keys()
        data_rows = [dict(r) for r in rows]
        return jsonify({'columns': list(cols), 'rows': data_rows})
    except Exception as e:
        logger.error(f"Error getting table data: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/coingecko/sync', methods=['POST'])
def coingecko_sync():
    """Sync market data from CoinGecko into tokens table"""
    if not cg:
        return jsonify({'error': 'CoinGecko client not available'}), 503
    try:
        pages = int(request.args.get('pages', 3))  # up to 750 coins
        vs_currency = request.args.get('vs_currency', 'usd')

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        # Ensure tokens table exists (minimal columns used by dashboard)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE,
                name TEXT,
                price REAL,
                price_change_24h REAL,
                volume_24h REAL,
                market_cap REAL,
                is_blacklisted INTEGER DEFAULT 0,
                first_seen TEXT,
                last_updated TEXT
            )
        """)

        upsert_sql = """
            INSERT INTO tokens (symbol, name, price, price_change_24h, volume_24h, market_cap, is_blacklisted, first_seen, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                name=excluded.name,
                price=excluded.price,
                price_change_24h=excluded.price_change_24h,
                volume_24h=excluded.volume_24h,
                market_cap=excluded.market_cap,
                last_updated=excluded.last_updated
        """

        total = 0
        now_iso = datetime.utcnow().isoformat()
        for p in range(1, pages + 1):
            markets = cg.get_markets(vs_currency=vs_currency, per_page=250, page=p) or []
            for m in markets:
                symbol = (m.get('symbol') or '').upper()
                name = m.get('name') or ''
                price = float(m.get('current_price') or 0)
                change = float(m.get('price_change_percentage_24h') or 0)
                volume = float(m.get('total_volume') or 0)
                mcap = float(m.get('market_cap') or 0)
                # First seen defaults to now on insert; ignored on update
                cur.execute(upsert_sql, (
                    symbol, name, price, change, volume, mcap, now_iso, now_iso
                ))
                total += 1

        conn.commit()
        conn.close()
        return jsonify({'success': True, 'synced': total})
    except Exception as e:
        logger.error(f"Error syncing CoinGecko: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Check if database exists
    if not os.path.exists(DB_PATH):
        logger.warning(f"Database {DB_PATH} not found. Please run the bot first to create the database.")
    
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    # Optimize database on startup
    if OPTIMIZATION_AVAILABLE:
        try:
            optimizer = DatabaseOptimizer(DB_PATH)
            optimizer.create_indexes()
            logger.info("Database indexes created/verified")
        except Exception as e:
            logger.warning(f"Could not optimize database: {e}")
    
    print("=" * 60)
    print("Crypto Trading Bot Dashboard")
    print("=" * 60)
    print(f"Dashboard will be available at: http://localhost:5000")
    if OPTIMIZATION_AVAILABLE:
        print("✅ Optimization features enabled (Cache, Performance Monitoring)")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)

