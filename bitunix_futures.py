import hmac
import hashlib
import time
import requests
import json

class BitunixFutures:
    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        self.url = "https://openapi.bitunix.com"

    def _sign(self, payload):
        return hmac.new(self.api_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

    def place_order(self, symbol, side, qty, price=None, order_type="LIMIT"):
        timestamp = int(time.time() * 1000)
        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": str(qty),
            "timestamp": timestamp
        }
        if price:
            params["price"] = str(price)
        query = "&".join([f"{k}={v}" for k, v in params.items()])
        params["signature"] = self._sign(query)
        try:
            return requests.post(
                self.url + "/api/v1/futures/order",
                headers={"X-BAPI-API-KEY": self.api_key, "Content-Type": "application/json"},
                data=json.dumps(params),
                timeout=10
            ).json()
        except Exception as e:
            print(f"[FUTURES ERROR] {e}")
            return None
