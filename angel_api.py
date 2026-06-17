# angel_api.py — Angel One SmartAPI Connector
# Garuda Power Trading System

import requests
import json
import pyotp
import time
from datetime import datetime, timedelta
from SmartApi import SmartConnect

# ══════════════════════════════════════════════
# CONFIGURATION — .env file se load hoga
# ══════════════════════════════════════════════
import os
from dotenv import load_dotenv
load_dotenv()

API_KEY     = os.getenv("ANGEL_API_KEY")
CLIENT_ID   = os.getenv("ANGEL_CLIENT_ID")
PASSWORD    = os.getenv("ANGEL_PASSWORD")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")  # Google Authenticator secret

# ══════════════════════════════════════════════
# ANGEL ONE CONNECTION
# ══════════════════════════════════════════════
class AngelOneAPI:
    def __init__(self):
        self.obj = SmartConnect(api_key=API_KEY)
        self.session = None
        self.auth_token = None

    def login(self):
        """Angel One mein login karo"""
        try:
            totp = pyotp.TOTP(TOTP_SECRET).now()
            data = self.obj.generateSession(CLIENT_ID, PASSWORD, totp)
            self.auth_token = data['data']['jwtToken']
            self.session = data
            print(f"✅ Angel One Login Success — {datetime.now().strftime('%H:%M:%S')}")
            return True
        except Exception as e:
            print(f"❌ Login Failed: {e}")
            return False

    def get_ohlcv(self, symbol, exchange="NSE", interval="FIVE_MINUTE", days=5):
        """
        OHLCV data fetch karo
        interval options: ONE_MINUTE, FIVE_MINUTE, FIFTEEN_MINUTE, 
                          THIRTY_MINUTE, ONE_HOUR, ONE_DAY
        """
        try:
            to_date   = datetime.now().strftime("%Y-%m-%d %H:%M")
            from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M")

            # Symbol token lookup
            token = self._get_token(symbol, exchange)
            if not token:
                return None

            params = {
                "exchange": exchange,
                "symboltoken": token,
                "interval": interval,
                "fromdate": from_date,
                "todate": to_date
            }

            response = self.obj.getCandleData(params)

            if response['status'] and response['data']:
                candles = response['data']
                result = {
                    "symbol": symbol,
                    "interval": interval,
                    "timestamp": [c[0] for c in candles],
                    "open":      [float(c[1]) for c in candles],
                    "high":      [float(c[2]) for c in candles],
                    "low":       [float(c[3]) for c in candles],
                    "close":     [float(c[4]) for c in candles],
                    "volume":    [float(c[5]) for c in candles],
                }
                print(f"📊 {symbol} — {len(candles)} candles fetched")
                return result
            else:
                print(f"⚠️ No data for {symbol}")
                return None

        except Exception as e:
            print(f"❌ OHLCV Error [{symbol}]: {e}")
            return None

    def _get_token(self, symbol, exchange):
        """Symbol ka token ID dhundho"""
        try:
            # NSE common symbols token map (expandable)
            TOKEN_MAP = {
                "NIFTY":      "26000",
                "BANKNIFTY":  "26009",
                "RELIANCE":   "2885",
                "TCS":        "11536",
                "INFY":       "1594",
                "HDFCBANK":   "1333",
                "ICICIBANK":  "4963",
                "SBIN":       "3045",
                "WIPRO":      "3787",
                "HDFC":       "1330",
                "AXISBANK":   "5900",
                "KOTAKBANK":  "1922",
                "LT":         "11483",
                "BAJFINANCE":  "317",
                "MARUTI":     "10999",
            }
            return TOKEN_MAP.get(symbol.upper(), "26000")
        except:
            return "26000"

    def get_ltp(self, symbol, exchange="NSE"):
        """Last Traded Price"""
        try:
            token = self._get_token(symbol, exchange)
            data = self.obj.ltpData(exchange, symbol, token)
            if data['status']:
                return data['data']['ltp']
        except Exception as e:
            print(f"❌ LTP Error: {e}")
        return None

    def get_multiple_symbols(self, symbols, interval="FIVE_MINUTE"):
        """Multiple symbols ka data ek saath"""
        results = {}
        for sym in symbols:
            data = self.get_ohlcv(sym, interval=interval)
            if data:
                results[sym] = data
            time.sleep(0.3)  # Rate limiting
        return results


# ══════════════════════════════════════════════
# DEFAULT WATCHLIST
# ══════════════════════════════════════════════
DEFAULT_SYMBOLS = [
    "NIFTY", "BANKNIFTY", "RELIANCE", "TCS", "INFY",
    "HDFCBANK", "ICICIBANK", "SBIN", "WIPRO", "AXISBANK",
    "KOTAKBANK", "LT", "BAJFINANCE", "MARUTI", "HDFC"
]

# ══════════════════════════════════════════════
# MAIN — Test karne ke liye
# ══════════════════════════════════════════════
if __name__ == "__main__":
    api = AngelOneAPI()
    if api.login():
        data = api.get_ohlcv("RELIANCE", interval="FIVE_MINUTE", days=2)
        if data:
            print(f"\nReliance Close prices (last 5):")
            print(data['close'][-5:])
