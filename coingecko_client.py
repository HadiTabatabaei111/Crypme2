#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CoinGecko Client (lightweight)
Fetches public crypto market data without API keys (anti-sanction friendly)
"""

import time
import logging
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class CoinGeckoClient:
	BASE_URL = "https://api.coingecko.com/api/v3"

	def __init__(self, request_timeout: int = 15, retries: int = 2, sleep_between: float = 1.0):
		self.session = requests.Session()
		self.timeout = request_timeout
		self.retries = retries
		self.sleep_between = sleep_between

	def _get(self, path: str, params: Optional[Dict] = None) -> Optional[Dict]:
		url = f"{self.BASE_URL}{path}"
		for attempt in range(self.retries + 1):
			try:
				resp = self.session.get(url, params=params or {}, timeout=self.timeout)
				if resp.status_code == 429:
					# rate limited
					time.sleep(self.sleep_between * (attempt + 1))
					continue
				resp.raise_for_status()
				return resp.json()
			except requests.exceptions.RequestException as e:
				logger.warning(f"CoinGecko request error ({path}): {e}")
				time.sleep(self.sleep_between)
		return None

	def get_markets(self, vs_currency: str = "usd", per_page: int = 250, page: int = 1) -> List[Dict]:
		"""
		Get market data list (paginated)
		"""
		params = {
			'vs_currency': vs_currency,
			'order': 'market_cap_desc',
			'per_page': per_page,
			'page': page,
			'sparkline': 'false',
			'price_change_percentage': '24h'
		}
		data = self._get("/coins/markets", params=params)
		return data if isinstance(data, list) else []

	def get_coin_ohlc(self, coin_id: str, vs_currency: str = "usd", days: int = 1) -> List[List[float]]:
		"""
		Get OHLC for a coin (CoinGecko supports: 1,7,14,30,90,180,365,max)
		"""
		params = {'vs_currency': vs_currency, 'days': days}
		data = self._get(f"/coins/{coin_id}/ohlc", params=params)
		return data if isinstance(data, list) else []

	def get_simple_price(self, coin_ids: List[str], vs_currency: str = "usd") -> Dict[str, Dict]:
		"""
		Get simple price map
		"""
		params = {
			'ids': ",".join(coin_ids),
			'vs_currencies': vs_currency,
			'include_24hr_change': 'true'
		}
		data = self._get("/simple/price", params=params)
		return data if isinstance(data, dict) else {}


