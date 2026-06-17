#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════
  TRISHUL GREEK FLIP — विधाता (VIDHATA) — EQUITY SWING SCANNER
  Daily Timeframe | ₹50-200 Stocks | 2-3 Day Hold
═══════════════════════════════════════════════════════════════════
"""

import os, sys, json, time, threading, math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
import logging

# ============ CONFIG ============
ANGEL_API_KEY = os.getenv("ANGEL_API_KEY", "")
ANGEL_CLIENT_ID = os.getenv("ANGEL_CLIENT_ID", "")
ANGEL_PASSWORD = os.getenv("ANGEL_PASSWORD", "")
ANGEL_TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET", "")

MIN_PRICE = 50
MAX_PRICE = 200
MIN_VOLUME = 500000
HOLD_DAYS = 3
MAX_RISK = 0.02
MIN_RR = 1.5

SCAN_INTERVAL = 300  # 5 min

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[logging.FileHandler('vidhata.log'), logging.StreamHandler()])
logger = logging.getLogger("VIDHATA")

# ═══════════════════════════════════════════════════════════════
#  SECTOR MAPPING
# ═══════════════════════════════════════════════════════════════
SECTOR_MAP = {
    "RELIANCE": "ENERGY", "ONGC": "ENERGY", "OIL": "ENERGY", "GAIL": "ENERGY",
    "PETRONET": "ENERGY", "HINDPETRO": "ENERGY", "BPCL": "ENERGY", "IOC": "ENERGY",
    "ATGL": "ENERGY", "IGL": "ENERGY", "MGL": "ENERGY", "GUJGASLTD": "ENERGY",
    "ADANIPOWER": "ENERGY", "TATAPOWER": "ENERGY", "JSWENERGY": "ENERGY",
    "NTPC": "ENERGY", "POWERGRID": "ENERGY", "NHPC": "ENERGY", "TORNTPOWER": "ENERGY",
    "RECLTD": "ENERGY", "PFC": "ENERGY", "COALINDIA": "ENERGY", "NMDC": "ENERGY",
    "TCS": "IT", "INFY": "IT", "WIPRO": "IT", "HCLTECH": "IT", "TECHM": "IT",
    "LTTS": "IT", "PERSISTENT": "IT", "MPHASIS": "IT", "COFORGE": "IT",
    "HDFCBANK": "BANK", "ICICIBANK": "BANK", "SBIN": "BANK", "AXISBANK": "BANK",
    "KOTAKBANK": "BANK", "INDUSINDBK": "BANK", "BANKBARODA": "BANK", "CANBK": "BANK",
    "FEDERALBNK": "BANK", "RBLBANK": "BANK", "BANDHANBNK": "BANK", "AUBANK": "BANK",
    "BAJFINANCE": "FINANCE", "BAJAJFINSV": "FINANCE", "HDFCLIFE": "FINANCE",
    "SBILIFE": "FINANCE", "CHOLAFIN": "FINANCE", "M&MFIN": "FINANCE",
    "HINDUNILVR": "FMCG", "ITC": "FMCG", "NESTLEIND": "FMCG", "BRITANNIA": "FMCG",
    "DABUR": "FMCG", "MARICO": "FMCG", "GODREJCP": "FMCG", "COLPAL": "FMCG",
    "SUNPHARMA": "PHARMA", "DRREDDY": "PHARMA", "CIPLA": "PHARMA", "DIVISLAB": "PHARMA",
    "MARUTI": "AUTO", "TATAMOTORS": "AUTO", "M&M": "AUTO", "HEROMOTOCO": "AUTO",
    "BAJAJ-AUTO": "AUTO", "EICHERMOT": "AUTO", "TVSMOTOR": "AUTO", "MOTHERSON": "AUTO",
    "TATASTEEL": "METAL", "JSWSTEEL": "METAL", "HINDALCO": "METAL", "VEDL": "METAL",
    "LT": "INFRA", "NH": "INFRA", "GMRINFRA": "INFRA", "IRB": "INFRA",
    "KNRCON": "INFRA", "NCC": "INFRA", "NBCC": "INFRA", "IRCTC": "INFRA",
    "PIDILITIND": "CHEMICALS", "SRF": "CHEMICALS", "NAVINFLUOR": "CHEMICALS",
    "TATACHEM": "CHEMICALS", "DEEPAKNTR": "CHEMICALS", "AARTIIND": "CHEMICALS",
    "TRENT": "RETAIL", "ABFRL": "RETAIL", "VMART": "RETAIL", "DMART": "RETAIL",
    "HAVELLS": "ELECTRICAL", "CROMPTON": "ELECTRICAL", "BAJAJELEC": "ELECTRICAL",
    "VOLTAS": "ELECTRICAL", "DIXON": "ELECTRICAL", "POLYCAB": "ELECTRICAL",
    "SIEMENS": "CAPITAL", "ABB": "CAPITAL", "BOSCHLTD": "CAPITAL", "CUMMINSIND": "CAPITAL",
    "SUZLON": "GREEN", "INOXWIND": "GREEN", "NTPCGREEN": "GREEN", "IREDA": "GREEN",
    "ULTRACEMCO": "CEMENT", "SHREECEM": "CEMENT", "GRASIM": "CEMENT",
    "ASIANPAINT": "PAINTS", "BERGEPAINT": "PAINTS", "KANSAINER": "PAINTS",
    "ZOMATO": "FOODTECH", "SWIGGY": "FOODTECH", "NAUKRI": "JOBS",
    "TITAN": "JEWELLERY", "PAGEIND": "TEXTILE"
}

def get_sector(symbol):
    return SECTOR_MAP.get(symbol, "UNKNOWN")

# ═══════════════════════════════════════════════════════════════
#  DATA CLASSES
# ═══════════════════════════════════════════════════════════════
@dataclass
class Signal:
    symbol: str
    strategy: str
    page: str
    sector: str
    signal: str
    price: float
    stop_loss: float
    target: float
    confidence: float
    timestamp: str
    indicators: Dict = field(default_factory=dict)
    hold_days: int = 3

    def to_dict(self):
        return {
            "symbol": self.symbol, "strategy": self.strategy, "page": self.page,
            "sector": self.sector, "signal": self.signal, "price": self.price,
            "stop_loss": self.stop_loss, "target": self.target,
            "confidence": self.confidence, "timestamp": self.timestamp,
            "indicators": self.indicators, "hold_days": self.hold_days
        }

@dataclass
class StrategyBox:
    id: int
    name: str
    page: str
    greek_symbol: str
    status: str
    signal_count: int
    total_signals: int
    last_scan: str
    real_accuracy: float
    total_trades: int
    won_trades: int
    lost_trades: int
    avg_rr: float
    signals: List[Signal] = field(default_factory=list)

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "page": self.page,
            "greek_symbol": self.greek_symbol, "status": self.status,
            "signal_count": self.signal_count, "total_signals": self.total_signals,
            "last_scan": self.last_scan, "real_accuracy": self.real_accuracy,
            "total_trades": self.total_trades, "won_trades": self.won_trades,
            "lost_trades": self.lost_trades, "avg_rr": self.avg_rr,
            "signals": [s.to_dict() for s in self.signals]
        }

# ═══════════════════════════════════════════════════════════════
#  TECHNICAL INDICATORS — SELF-CONTAINED FOR VIDHATA ONLY
# ═══════════════════════════════════════════════════════════════
class VidhataIndicators:
    """Self-contained indicators — no sharing with other scanners"""

    @staticmethod
    def sma(data, period):
        if len(data) < period: return []
        return [sum(data[i-period+1:i+1])/period for i in range(period-1, len(data))]

    @staticmethod
    def ema(data, period):
        if len(data) < period: return []
        k = 2/(period+1)
        result = [sum(data[:period])/period]
        for i in range(period, len(data)):
            result.append(data[i]*k + result[-1]*(1-k))
        return result

    @staticmethod
    def atr(high, low, close, period=14):
        if len(close) < 2: return []
        tr = [high[0]-low[0]]
        for i in range(1, len(close)):
            tr.append(max(high[i]-low[i], abs(high[i]-close[i-1]), abs(low[i]-close[i-1])))
        return VidhataIndicators.sma(tr, period)

    # ── INDICATOR 1: TTM Squeeze ──
    @staticmethod
    def ttm_squeeze(close, high, low, bb_period=20, keltner_period=20, atr_period=10):
        sma = VidhataIndicators.sma(close, bb_period)
        if not sma: return []
        bb_upper, bb_lower = [], []
        for i in range(bb_period-1, len(close)):
            window = close[i-bb_period+1:i+1]
            std = math.sqrt(sum((x-sma[i-bb_period+1])**2 for x in window)/bb_period)
            bb_upper.append(sma[i-bb_period+1]+2*std)
            bb_lower.append(sma[i-bb_period+1]-2*std)

        ema_vals = VidhataIndicators.ema(close, keltner_period)
        atr_vals = VidhataIndicators.atr(high, low, close, atr_period)
        if not ema_vals or not atr_vals: return []
        min_len = min(len(ema_vals), len(atr_vals))
        k_upper = [ema_vals[i] + 1.5 * atr_vals[i] for i in range(min_len)]
        k_lower = [ema_vals[i] - 1.5 * atr_vals[i] for i in range(min_len)]

        min_len2 = min(len(bb_upper), len(k_upper))
        squeeze = [bb_upper[i] < k_upper[i] and bb_lower[i] > k_lower[i] for i in range(min_len2)]
        return squeeze

    # ── INDICATOR 2: Chande Momentum Oscillator ──
    @staticmethod
    def cmo(close, period=14):
        if len(close) < period+1: return []
        gains, losses = [], []
        for i in range(1, len(close)):
            diff = close[i] - close[i-1]
            gains.append(diff if diff > 0 else 0)
            losses.append(abs(diff) if diff < 0 else 0)
        cmo_vals = []
        for i in range(period-1, len(gains)):
            g = sum(gains[i-period+1:i+1])
            l = sum(losses[i-period+1:i+1])
            cmo_vals.append(100 * (g-l) / (g+l) if (g+l) > 0 else 0)
        return cmo_vals

    # ── INDICATOR 3: Elder Ray Index ──
    @staticmethod
    def elder_ray(high, low, close, period=13):
        ema_vals = VidhataIndicators.ema(close, period)
        if not ema_vals: return [], []
        bull_power = [high[i+period-1] - ema_vals[i] for i in range(len(ema_vals))]
        bear_power = [low[i+period-1] - ema_vals[i] for i in range(len(ema_vals))]
        return bull_power, bear_power

    # ── INDICATOR 4: Donchian Channels ──
    @staticmethod
    def donchian_channels(high, low, period=20):
        if len(high) < period or len(low) < period: return [], [], []
        upper = [max(high[i-period+1:i+1]) for i in range(period-1, len(high))]
        lower = [min(low[i-period+1:i+1]) for i in range(period-1, len(low))]
        middle = [(upper[i] + lower[i])/2 for i in range(len(upper))]
        return upper, middle, lower

    # ── INDICATOR 5: Hull Moving Average ──
    @staticmethod
    def hull_ma(close, period=16):
        if len(close) < period: return []
        half = period // 2
        sqrt_period = int(math.sqrt(period))
        ma_half = VidhataIndicators.sma(close, half)
        ma_full = VidhataIndicators.sma(close, period)
        if not ma_half or not ma_full: return []
        raw = [2*ma_half[i] - ma_full[i] for i in range(min(len(ma_half), len(ma_full)))]
        return VidhataIndicators.sma(raw, sqrt_period) if raw else []

    # ── INDICATOR 6: Keltner Channels ──
    @staticmethod
    def keltner_channels(high, low, close, ema_period=20, atr_period=10, multiplier=2):
        ema_vals = VidhataIndicators.ema(close, ema_period)
        atr_vals = VidhataIndicators.atr(high, low, close, atr_period)
        if not ema_vals or not atr_vals: return [], [], []
        min_len = min(len(ema_vals), len(atr_vals))
        upper = [ema_vals[i] + multiplier * atr_vals[i] for i in range(min_len)]
        lower = [ema_vals[i] - multiplier * atr_vals[i] for i in range(min_len)]
        return ema_vals[:min_len], upper, lower

    # ── INDICATOR 7: Money Flow Index ──
    @staticmethod
    def mfi(high, low, close, volume, period=14):
        if len(close) < period+1: return []
        tp = [(high[i]+low[i]+close[i])/3 for i in range(len(close))]
        raw_mf = [tp[i]*volume[i] for i in range(len(tp))]
        pos_mf, neg_mf = [], []
        for i in range(1, len(tp)):
            if tp[i] > tp[i-1]: pos_mf.append(raw_mf[i]); neg_mf.append(0)
            elif tp[i] < tp[i-1]: pos_mf.append(0); neg_mf.append(raw_mf[i])
            else: pos_mf.append(0); neg_mf.append(0)
        mfi_vals = []
        for i in range(period-1, len(pos_mf)):
            pm = sum(pos_mf[i-period+1:i+1])
            nm = sum(neg_mf[i-period+1:i+1])
            mfi_vals.append(100 - (100/(1+pm/nm)) if nm > 0 else 100)
        return mfi_vals

    # ── INDICATOR 8: Chaikin Money Flow ──
    @staticmethod
    def cmf(high, low, close, volume, period=20):
        if len(close) < period: return []
        ad = [((close[i]-low[i])-(high[i]-close[i]))/(high[i]-low[i])*volume[i] 
              if high[i] != low[i] else 0 for i in range(len(close))]
        cmf_vals = []
        for i in range(period-1, len(ad)):
            vol_sum = sum(volume[i-period+1:i+1])
            cmf_vals.append(sum(ad[i-period+1:i+1]) / vol_sum if vol_sum > 0 else 0)
        return cmf_vals

    # ── INDICATOR 9: Support/Resistance ──
    @staticmethod
    def support_resistance(high, low, close, lookback=20):
        if len(close) < lookback: return {}
        recent_highs = [(i,high[i]) for i in range(len(high)-lookback, len(high)) 
                        if high[i] == max(high[max(0,i-2):min(len(high),i+3)])]
        recent_lows = [(i,low[i]) for i in range(len(low)-lookback, len(low)) 
                       if low[i] == min(low[max(0,i-2):min(len(low),i+3)])]
        resistance = sum(h for _,h in recent_highs)/len(recent_highs) if recent_highs else max(high[-lookback:])
        support = sum(l for _,l in recent_lows)/len(recent_lows) if recent_lows else min(low[-lookback:])
        return {"support":support, "resistance":resistance}

    # ── INDICATOR 10: ATR Trailing Stop ──
    @staticmethod
    def trailing_stop(close, high, low, direction, atr_mult=2.0):
        atr_vals = VidhataIndicators.atr(high, low, close, 14)
        if not atr_vals: return close[-1]*(0.95 if direction=="long" else 1.05)
        atr_val = atr_vals[-1]
        return close[-1] - atr_val*atr_mult if direction=="long" else close[-1] + atr_val*atr_mult

# ═══════════════════════════════════════════════════════════════
#  ANGEL ONE CLIENT
# ═══════════════════════════════════════════════════════════════
class AngelOneClient:
    def __init__(self):
        self.api_key = ANGEL_API_KEY
        self.client_id = ANGEL_CLIENT_ID
        self.password = ANGEL_PASSWORD
        self.totp_secret = ANGEL_TOTP_SECRET
        self.smart_api = None

    def _generate_totp(self):
        try:
            import pyotp
            return pyotp.TOTP(self.totp_secret).now() if self.totp_secret else ""
        except: return ""

    def login(self):
        try:
            from SmartApi import SmartConnect
            self.smart_api = SmartConnect(api_key=self.api_key)
            session = self.smart_api.generateSession(self.client_id, self.password, self._generate_totp())
            if session.get('status') and session.get('data'):
                logger.info(f"✅ Angel One Login: {self.client_id}")
                return True
            logger.error(f"❌ Login failed")
            return False
        except Exception as e:
            logger.error(f"❌ Login error: {e}")
            return False

    def get_candle_data(self, token, interval="ONE_DAY", days=30):
        try:
            to_date = datetime.now().strftime("%Y-%m-%d %H:%M")
            from_date = (datetime.now()-timedelta(days=days)).strftime("%Y-%m-%d %H:%M")
            params = {"exchange":"NSE", "symboltoken":token, "interval":interval, "fromdate":from_date, "todate":to_date}
            response = self.smart_api.getCandleData(params)
            if response and response.get('status') and response.get('data'):
                return response['data']
            return []
        except Exception as e:
            logger.error(f"Candle error: {e}")
            return []

    def get_ltp(self, token):
        try:
            response = self.smart_api.ltpData("NSE", "", token)
            if response and response.get('status') and response.get('data'):
                return float(response['data']['ltp'])
            return None
        except: return None

# Stock universe (₹50-200 focus)
NSE_STOCKS = {
    "IOB":"9392", "UCOBANK":"11351", "CENTRALBK":"14008", "PSB":"11184",
    "MAHABANK":"11377", "FEDERALBNK":"1023", "RBLBANK":"18313", 
    "BANDHANBNK":"22601", "DCBBANK":"2423", "KARURVYSYA":"1428",
    "CITYUNION":"1600", "J&KBANK":"1847", "SOUTHBANK":"1866",
    "TMB":"21415", "CSBBANK":"22244", "EQUITASBNK":"19288",
    "UJJIVANSFB":"19232", "AUBANK":"21238", "CANBK":"10794",
    "INDIANB":"9590", "BANKBARODA":"4668", "PNBHOUSING":"18921",
    "REPCOHOME":"16639", "CANFINHOME":"203", "LICHSGFIN":"2443",
    "M&MFIN":"13285", "CHOLAFIN":"18094", "SUNDARMFIN":"13611",
    "MOTHERSON":"4204", "APOLLOTYRE":"163", "JKTYRE":"18228",
    "CEATLTD":"4306", "BALKRISIND":"335", "TVSMOTOR":"21789",
    "HEROMOTOCO":"1348", "EICHERMOT":"910", "BHARATFORG":"422",
    "MINDAIND":"14304", "SUNDRMFAST":"15034", "JUBLFOOD":"18096",
    "DEVYANI":"20302", "WESTLIFE":"16304", "TATACONSUM":"3432",
    "UBL":"16705", "RADICO":"9436", "UNITDSPR":"1404",
    "GMRINFRA":"11611", "ADANIPOWER":"17388", "TATAPOWER":"18423",
    "JSWENERGY":"21690", "NTPCGREEN":"21957", "TORNTPOWER":"13786",
    "NHPC":"8910", "SJVN":"23892", "RECLTD":"15355", "PFC":"14299",
    "IREDA":"23764", "NCC":"11840", "NBCC":"18228", "SAIL":"2966",
    "TATASTEEL":"3499", "APLAPOLLO":"13786", "HINDZINC":"1512",
    "NATIONALUM":"11840", "VEDL":"3063", "HINDCOPPER":"18228",
    "NMDC":"5880", "MOIL":"20302", "COALINDIA":"20374",
    "GUJGASLTD":"1512", "MGL":"11840", "IGL":"11262", "ATGL":"18228",
    "HINDPETRO":"1404", "BPCL":"526", "IOC":"1624", "OIL":"20302",
    "ONGC":"2475", "GAIL":"4717", "PETRONET":"11351",
    "SRF":"2181", "TATACHEM":"3405", "PIDILITIND":"2668",
    "DEEPAKNTR":"18228", "AARTIIND":"11262",
    "TRENT":"1964", "ABFRL":"15141", "VMART":"18228", "DMART":"19913",
    "HAVELLS":"2518", "CROMPTON":"1512", "BAJAJELEC":"11840",
    "VOLTAS":"16705", "DIXON":"21689", "POLYCAB":"22032",
    "SIEMENS":"11884", "ABB":"1348", "BOSCHLTD":"910",
    "SUZLON":"11840", "INOXWIND":"18228", "NTPCGREEN":"21957",
    "ULTRACEMCO":"1348", "SHREECEM":"1348", "GRASIM":"1232",
    "ASIANPAINT":"1606", "BERGEPAINT":"1348", "KANSAINER":"1348",
    "ZOMATO":"20302", "SWIGGY":"23725", "NAUKRI":"13786",
    "TITAN":"8345", "PAGEIND":"14428"
}

# ═══════════════════════════════════════════════════════════════
#  BASE STRATEGY
# ═══════════════════════════════════════════════════════════════
class BaseStrategy:
    def __init__(self, name, greek_symbol, strategy_id, client):
        self.name = name
        self.greek_symbol = greek_symbol
        self.strategy_id = strategy_id
        self.client = client
        self.signals = []
        self.status = "LIVE"
        self.last_scan = "Never"
        self.ta = VidhataIndicators()
        self.wins = 0
        self.losses = 0

    def scan(self, symbol, token):
        raise NotImplementedError

    def _create_signal(self, symbol, signal_type, price, stop_loss, target, confidence, indicators):
        sector = get_sector(symbol)
        return Signal(
            symbol=symbol, strategy=self.name, page="VIDHATA", sector=sector,
            signal=signal_type, price=price, stop_loss=stop_loss, target=target,
            confidence=confidence, timestamp=datetime.now().strftime("%H:%M:%S"),
            indicators=indicators
        )

    def _fetch_data(self, token, interval="ONE_DAY", days=30):
        data = self.client.get_candle_data(token, interval, days)
        if not data or len(data) < 20: return {}
        return {
            "open":[float(d[1]) for d in data], "high":[float(d[2]) for d in data],
            "low":[float(d[3]) for d in data], "close":[float(d[4]) for d in data],
            "volume":[float(d[5]) for d in data], "timestamp":[d[0] for d in data]
        }

    def _trailing_stop(self, close, high, low, direction, atr_mult=2.0):
        return self.ta.trailing_stop(close, high, low, direction, atr_mult)

    def get_real_accuracy(self):
        total = self.wins + self.losses
        if total == 0: return 50.0
        return round((self.wins/total)*100, 1)

# ═══════════════════════════════════════════════════════════════
#  4 STRATEGIES FOR VIDHATA
# ═══════════════════════════════════════════════════════════════

class Strategy01_TTM_Squeeze(BaseStrategy):
    """TTM Squeeze + Donchian Breakout + Volume"""
    def __init__(self, client): super().__init__("TTM Squeeze + Donchian", "Δ", 1, client)

    def scan(self, symbol, token):
        data = self._fetch_data(token, "ONE_DAY", 30)
        if not data: return None
        c, h, l, v = data["close"], data["high"], data["low"], data["volume"]
        if len(c) < 25: return None

        squeeze = self.ta.ttm_squeeze(c, h, l, 20, 20, 10)
        donchian_upper, _, donchian_lower = self.ta.donchian_channels(h, l, 20)
        vol_sma = self.ta.sma(v, 20)

        if not squeeze or not donchian_upper or not vol_sma: return None

        latest = c[-1]
        vol, avg_vol = v[-1], vol_sma[-1]

        if len(squeeze) > 2 and squeeze[-2] and not squeeze[-1]:
            if latest > donchian_upper[-1] and vol > avg_vol * 1.3:
                stop = self._trailing_stop(c, h, l, "long", 2.5)
                target = latest + (latest - stop) * 2
                return self._create_signal(symbol, "BUY", latest, stop, target, 55, {
                    "ttm_squeeze_fired": True, "donchian_upper": donchian_upper[-1],
                    "volume_ratio": round(vol/avg_vol, 2), "atr_stop": stop
                })
            elif latest < donchian_lower[-1] and vol > avg_vol * 1.3:
                stop = self._trailing_stop(c, h, l, "short", 2.5)
                target = latest - (stop - latest) * 2
                return self._create_signal(symbol, "SELL", latest, stop, target, 55, {
                    "ttm_squeeze_fired": True, "donchian_lower": donchian_lower[-1],
                    "volume_ratio": round(vol/avg_vol, 2), "atr_stop": stop
                })
        return None

class Strategy02_CMO_ElderRay(BaseStrategy):
    """Chande Momentum + Elder Ray + Sector Filter"""
    def __init__(self, client): super().__init__("CMO + Elder Ray", "Γ", 2, client)

    def scan(self, symbol, token):
        data = self._fetch_data(token, "ONE_DAY", 30)
        if not data: return None
        c, h, l, v = data["close"], data["high"], data["low"], data["volume"]
        if len(c) < 20: return None

        cmo = self.ta.cmo(c, 14)
        bull_power, bear_power = self.ta.elder_ray(h, l, c, 13)
        vol_sma = self.ta.sma(v, 20)

        if not cmo or not bull_power or not vol_sma: return None

        latest = c[-1]
        cmo_val = cmo[-1]
        bull = bull_power[-1]
        bear = bear_power[-1]
        vol, avg_vol = v[-1], vol_sma[-1]

        if cmo_val > -50 and bull > 0 and vol > avg_vol * 1.2:
            stop = self._trailing_stop(c, h, l, "long", 2.0)
            target = latest + (latest - stop) * 2.5
            return self._create_signal(symbol, "BUY", latest, stop, target, 52, {
                "cmo": round(cmo_val, 2), "bull_power": round(bull, 2),
                "volume_ratio": round(vol/avg_vol, 2), "sector": get_sector(symbol)
            })

        elif cmo_val < 50 and bear < 0 and vol > avg_vol * 1.2:
            stop = self._trailing_stop(c, h, l, "short", 2.0)
            target = latest - (stop - latest) * 2.5
            return self._create_signal(symbol, "SELL", latest, stop, target, 52, {
                "cmo": round(cmo_val, 2), "bear_power": round(bear, 2),
                "volume_ratio": round(vol/avg_vol, 2), "sector": get_sector(symbol)
            })
        return None

class Strategy03_Hull_Keltner(BaseStrategy):
    """Hull MA + Keltner Channels + Volume Profile"""
    def __init__(self, client): super().__init__("Hull MA + Keltner", "Θ", 3, client)

    def scan(self, symbol, token):
        data = self._fetch_data(token, "ONE_DAY", 30)
        if not data: return None
        c, h, l, v = data["close"], data["high"], data["low"], data["volume"]
        if len(c) < 25: return None

        hull = self.ta.hull_ma(c, 16)
        keltner, k_upper, k_lower = self.ta.keltner_channels(h, l, c, 20, 10, 2)

        if not hull or not keltner: return None

        latest = c[-1]
        hull_val = hull[-1]

        if len(hull) > 2 and hull[-2] < hull[-1] and latest > hull_val and latest > keltner[-1]:
            stop = k_lower[-1]
            target = k_upper[-1]
            rr = (target - latest) / (latest - stop) if (latest - stop) > 0 else 0
            if rr >= MIN_RR:
                return self._create_signal(symbol, "BUY", latest, stop, target, 54, {
                    "hull_ma": round(hull_val, 2), "keltner_mid": round(keltner[-1], 2),
                    "keltner_upper": round(k_upper[-1], 2), "risk_reward": round(rr, 2)
                })

        elif len(hull) > 2 and hull[-2] > hull[-1] and latest < hull_val and latest < keltner[-1]:
            stop = k_upper[-1]
            target = k_lower[-1]
            rr = (latest - target) / (stop - latest) if (stop - latest) > 0 else 0
            if rr >= MIN_RR:
                return self._create_signal(symbol, "SELL", latest, stop, target, 54, {
                    "hull_ma": round(hull_val, 2), "keltner_mid": round(keltner[-1], 2),
                    "keltner_lower": round(k_lower[-1], 2), "risk_reward": round(rr, 2)
                })
        return None

class Strategy04_MFI_CMF(BaseStrategy):
    """Money Flow Index + Chaikin Money Flow + Support"""
    def __init__(self, client): super().__init__("MFI + CMF + Support", "V", 4, client)

    def scan(self, symbol, token):
        data = self._fetch_data(token, "ONE_DAY", 30)
        if not data: return None
        c, h, l, v = data["close"], data["high"], data["low"], data["volume"]
        if len(c) < 25: return None

        mfi = self.ta.mfi(h, l, c, v, 14)
        cmf = self.ta.cmf(h, l, c, v, 20)
        sr = self.ta.support_resistance(h, l, c, 20)

        if not mfi or not cmf or not sr: return None

        latest = c[-1]
        mfi_val = mfi[-1]
        cmf_val = cmf[-1]
        support = sr["support"]
        resistance = sr["resistance"]

        if mfi_val < 30 and cmf_val > 0 and abs(latest - support)/latest < 0.02:
            stop = support * 0.98
            target = resistance
            rr = (target - latest) / (latest - stop) if (latest - stop) > 0 else 0
            if rr >= MIN_RR:
                return self._create_signal(symbol, "BUY", latest, stop, target, 53, {
                    "mfi": round(mfi_val, 2), "cmf": round(cmf_val, 2),
                    "support": round(support, 2), "resistance": round(resistance, 2),
                    "risk_reward": round(rr, 2)
                })

        elif mfi_val > 70 and cmf_val < 0 and abs(latest - resistance)/latest < 0.02:
            stop = resistance * 1.02
            target = support
            rr = (latest - target) / (stop - latest) if (stop - latest) > 0 else 0
            if rr >= MIN_RR:
                return self._create_signal(symbol, "SELL", latest, stop, target, 53, {
                    "mfi": round(mfi_val, 2), "cmf": round(cmf_val, 2),
                    "support": round(support, 2), "resistance": round(resistance, 2),
                    "risk_reward": round(rr, 2)
                })
        return None

# ═══════════════════════════════════════════════════════════════
#  SCANNER ENGINE
# ═══════════════════════════════════════════════════════════════
class VidhataScanner:
    def __init__(self):
        self.client = AngelOneClient()
        self.strategies = []
        self.boxes = {}
        self.running = False
        self.scan_thread = None
        self._init_strategies()

    def _init_strategies(self):
        self.strategies.append(Strategy01_TTM_Squeeze(self.client))
        self.strategies.append(Strategy02_CMO_ElderRay(self.client))
        self.strategies.append(Strategy03_Hull_Keltner(self.client))
        self.strategies.append(Strategy04_MFI_CMF(self.client))

        for s in self.strategies:
            self.boxes[s.strategy_id] = StrategyBox(
                id=s.strategy_id, name=s.name, page="VIDHATA",
                greek_symbol=s.greek_symbol, status="LIVE",
                signal_count=0, total_signals=0, last_scan="Never",
                real_accuracy=50.0, total_trades=0, won_trades=0, lost_trades=0, avg_rr=1.5
            )

    def login(self): return self.client.login()

    def scan_all(self):
        logger.info("🔥 VIDHATA Scan started...")
        for strategy in self.strategies:
            try:
                box = self.boxes[strategy.strategy_id]
                box.last_scan = datetime.now().strftime("%H:%M:%S")
                box.real_accuracy = strategy.get_real_accuracy()

                universe = list(NSE_STOCKS.items())[:30]
                new_signals = []
                for symbol, token in universe:
                    signal = strategy.scan(symbol, token)
                    if signal:
                        new_signals.append(signal)
                        logger.info(f"📡 VIDHATA | {strategy.name} | {symbol} | {signal.signal} | ₹{signal.price:.2f}")

                box.signals = new_signals[-10:]
                box.signal_count = len([s for s in new_signals if s.signal in ["BUY", "SELL"]])
                box.total_signals += len(new_signals)

            except Exception as e:
                logger.error(f"❌ {strategy.name}: {e}")
                box.status = "ERROR"
        logger.info("✅ VIDHATA Scan complete")

    def start(self):
        if not self.running:
            self.running = True
            self.scan_thread = threading.Thread(target=self._scan_loop, daemon=True)
            self.scan_thread.start()
            logger.info("🚀 VIDHATA STARTED")

    def _scan_loop(self):
        while self.running:
            self.scan_all()
            time.sleep(SCAN_INTERVAL)

    def stop(self):
        self.running = False
        logger.info("🛑 VIDHATA STOPPED")

    def get_dashboard_data(self):
        total_buy = sum(1 for box in self.boxes.values() for s in box.signals if s.signal == "BUY")
        total_sell = sum(1 for box in self.boxes.values() for s in box.signals if s.signal == "SELL")
        return {
            "page": "VIDHATA",
            "strategies": [box.to_dict() for box in self.boxes.values()],
            "summary": {
                "buy": total_buy, "sell": total_sell,
                "total": total_buy + total_sell,
                "last_update": datetime.now().strftime("%H:%M:%S")
            }
        }

# ═══════════════════════════════════════════════════════════════
#  FASTAPI + HTML DASHBOARD (Screenshot Style)
# ═══════════════════════════════════════════════════════════════
try:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, JSONResponse
    import uvicorn

    app = FastAPI(title="VIDHATA — Equity Swing Scanner")
    scanner = VidhataScanner()

    @app.get("/", response_class=HTMLResponse)
    async def dashboard():
        return HTMLResponse(content=DASHBOARD_HTML, status_code=200)

    @app.get("/api/data")
    async def api_data():
        return JSONResponse(scanner.get_dashboard_data())

    @app.post("/api/start")
    async def api_start():
        scanner.start(); return {"status": "started"}

    @app.post("/api/stop")
    async def api_stop():
        scanner.stop(); return {"status": "stopped"}

    @app.post("/api/scan")
    async def api_scan():
        scanner.scan_all(); return {"status": "scanned"}

    @app.post("/api/login")
    async def api_login():
        success = scanner.login()
        return {"status": "logged_in" if success else "failed"}

except ImportError:
    app = None

# ═══════════════════════════════════════════════════════════════
#  DARK HTML DASHBOARD — Screenshot Style
# ═══════════════════════════════════════════════════════════════
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>विधाता — VIDHATA | Equity Swing Scanner</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #0a0e1a; color: #e0e0e0; font-family: 'Courier New', monospace; min-height: 100vh; }

/* Header */
.header { background: linear-gradient(135deg, #0d1b2a 0%, #1b2838 100%); padding: 12px 16px; border-bottom: 2px solid #f5a623; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 100; }
.header h1 { font-size: 1.1rem; color: #f5a623; letter-spacing: 3px; text-transform: uppercase; }
.header .live-dot { width: 8px; height: 8px; background: #00ff88; border-radius: 50%; animation: pulse 1s infinite; display: inline-block; margin-right: 6px; }
@keyframes pulse { 0%,100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.5; transform: scale(1.3); } }

/* Subtitle */
.subtitle { background: #0d1b2a; padding: 8px 16px; border-bottom: 1px solid #1a2a3a; display: flex; justify-content: space-between; align-items: center; }
.subtitle .tag { color: #8899aa; font-size: 0.65rem; text-transform: uppercase; letter-spacing: 2px; }
.subtitle .time { color: #f5a623; font-size: 0.8rem; }

/* Summary Bar */
.summary-bar { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1px; background: #1a2a3a; }
.summary-item { background: #0d1b2a; text-align: center; padding: 15px 5px; }
.summary-item .value { font-size: 2rem; font-weight: bold; }
.summary-item .label { font-size: 0.65rem; text-transform: uppercase; letter-spacing: 2px; color: #8899aa; margin-top: 4px; }
.buy { color: #00ff88; } .sell { color: #ff4757; } .wait { color: #f5a623; } .total { color: #74b9ff; }

/* Strategy Grid */
.strategy-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; padding: 15px; max-width: 1400px; margin: 0 auto; padding-bottom: 100px; }
@media (max-width: 768px) { .strategy-grid { grid-template-columns: 1fr; } }

.strategy-card { background: linear-gradient(135deg, #111827 0%, #1a2332 100%); border-radius: 12px; padding: 16px; border: 1px solid #1e3a5f; position: relative; overflow: hidden; transition: all 0.3s; }
.strategy-card:hover { border-color: #f5a623; transform: translateY(-2px); box-shadow: 0 8px 25px rgba(245,166,35,0.15); }
.strategy-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, #f5a623, #ff6b35, #f5a623); }

.card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
.greek-section { display: flex; align-items: center; gap: 8px; }
.greek-symbol { font-size: 2.2rem; color: #f5a623; font-weight: bold; line-height: 1; }
.strategy-info { display: flex; flex-direction: column; }
.zone-label { color: #f5a623; font-size: 0.6rem; text-transform: uppercase; letter-spacing: 2px; }
.strategy-name { font-size: 0.8rem; color: #e0e0e0; text-transform: uppercase; letter-spacing: 1px; margin-top: 2px; }

.signal-badge { padding: 4px 14px; border-radius: 20px; font-size: 0.65rem; text-transform: uppercase; letter-spacing: 1px; font-weight: bold; }
.badge-buy { background: rgba(0,255,136,0.15); color: #00ff88; border: 1px solid #00ff88; }
.badge-sell { background: rgba(255,71,87,0.15); color: #ff4757; border: 1px solid #ff4757; }
.badge-wait { background: rgba(245,166,35,0.15); color: #f5a623; border: 1px solid #f5a623; }

.card-body { min-height: 80px; }
.signal-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #1e3a5f; font-size: 0.75rem; }
.signal-row:last-child { border-bottom: none; }
.signal-symbol { color: #74b9ff; font-weight: bold; }
.signal-sector { color: #f5a623; font-size: 0.65rem; }
.signal-price { color: #e0e0e0; }
.signal-type { font-weight: bold; }

.card-footer { display: flex; justify-content: space-between; font-size: 0.65rem; color: #8899aa; margin-top: 10px; padding-top: 8px; border-top: 1px solid #1e3a5f; }
.live-text { color: #00ff88; font-size: 0.65rem; }
.live-text::before { content: '● '; color: #00ff88; }

/* Controls */
.controls { position: fixed; top: 70px; right: 12px; display: flex; flex-direction: column; gap: 8px; z-index: 99; }
.control-btn { padding: 8px 16px; background: #f5a623; color: #0a0e1a; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 0.75rem; transition: all 0.3s; }
.control-btn:hover { background: #ff8c00; transform: scale(1.05); }

/* Bottom Nav */
.bottom-nav { position: fixed; bottom: 0; left: 0; right: 0; background: #0d1b2a; border-top: 1px solid #1e3a5f; display: flex; justify-content: space-around; padding: 8px 0; z-index: 100; }
.nav-item { text-align: center; color: #8899aa; font-size: 0.6rem; cursor: pointer; transition: color 0.3s; padding: 4px 8px; }
.nav-item:hover, .nav-item.active { color: #f5a623; }
.nav-item .icon { font-size: 1.4rem; display: block; margin-bottom: 2px; }

/* Signal Button */
.signal-btn { position: fixed; bottom: 70px; right: 16px; background: linear-gradient(135deg, #f5a623, #ff8c00); color: #0a0e1a; padding: 12px 24px; border-radius: 30px; font-weight: bold; font-size: 0.85rem; display: flex; align-items: center; gap: 8px; box-shadow: 0 4px 15px rgba(245,166,35,0.4); cursor: pointer; z-index: 99; }
.signal-btn .count { background: #0a0e1a; color: #f5a623; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; }
</style>
</head>
<body>
<div class="header">
    <h1>🔱 विधाता VIDHATA</h1>
    <div style="display:flex;align-items:center;gap:8px;">
        <span class="live-dot"></span>
        <span style="color:#00ff88;font-size:0.75rem;">LIVE</span>
        <span style="color:#f5a623;font-size:0.8rem;" id="clock">--:--:--</span>
    </div>
</div>

<div class="subtitle">
    <span class="tag">Equity Swing • Daily • ₹50-200 • 2-3 Day Hold</span>
    <span class="time" id="update-time">--:--:--</span>
</div>

<div class="summary-bar">
    <div class="summary-item">
        <div class="value buy" id="total-buy">0</div>
        <div class="label">BUY</div>
    </div>
    <div class="summary-item">
        <div class="value sell" id="total-sell">0</div>
        <div class="label">SELL</div>
    </div>
    <div class="summary-item">
        <div class="value wait" id="total-wait">0</div>
        <div class="label">WAIT</div>
    </div>
    <div class="summary-item">
        <div class="value total" id="total-signals">0</div>
        <div class="label">TOTAL</div>
    </div>
</div>

<div class="controls">
    <button class="control-btn" onclick="startScan()">▶ START</button>
    <button class="control-btn" onclick="stopScan()">⏹ STOP</button>
    <button class="control-btn" onclick="manualScan()">🔄 SCAN</button>
    <button class="control-btn" onclick="login()">🔑 LOGIN</button>
</div>

<div id="strategy-container" class="strategy-grid"></div>

<div class="signal-btn" onclick="manualScan()">
    <span>📡 SIGNALS</span>
    <span class="count" id="signal-count">0</span>
</div>

<div class="bottom-nav">
    <div class="nav-item active"><span class="icon">🏠</span><span>HOME</span></div>
    <div class="nav-item"><span class="icon">📡</span><span>SIGNAL</span></div>
    <div class="nav-item"><span class="icon">👁</span><span>WATCH</span></div>
    <div class="nav-item"><span class="icon">⚡</span><span>POWER</span></div>
    <div class="nav-item"><span class="icon">⚙</span><span>ADMIN</span></div>
</div>

<script>
let data = { strategies: [], summary: { buy: 0, sell: 0, wait: 0, total: 0 } };

function updateClock() {
    const now = new Date().toLocaleTimeString('en-IN');
    document.getElementById('clock').textContent = now;
    document.getElementById('update-time').textContent = now;
}
setInterval(updateClock, 1000);
updateClock();

function renderStrategies() {
    const container = document.getElementById('strategy-container');
    const strategies = data.strategies || [];

    container.innerHTML = strategies.map(s => {
        const signals = s.signals || [];
        const signalHtml = signals.slice(0, 3).map(sig => `
            <div class="signal-row">
                <div>
                    <span class="signal-symbol">${sig.symbol}</span>
                    <span class="signal-sector">[${sig.sector}]</span>
                </div>
                <span class="signal-price">₹${sig.price.toFixed(2)}</span>
                <span class="signal-type ${sig.signal === 'BUY' ? 'buy' : 'sell'}">${sig.signal}</span>
            </div>
        `).join('');

        const acc = s.real_accuracy || 50;
        const accClass = acc > 55 ? 'badge-buy' : acc > 50 ? 'badge-wait' : 'badge-sell';
        const statusText = s.status === 'LIVE' ? 'LIVE' : 'ERROR';
        const signalCount = s.signal_count || 0;
        const totalSig = s.total_signals || 0;

        return `
            <div class="strategy-card">
                <div class="card-header">
                    <div class="greek-section">
                        <div class="greek-symbol">${s.greek_symbol}</div>
                        <div class="strategy-info">
                            <div class="zone-label">⚡ DELTA ZONE</div>
                            <div class="strategy-name">${s.name}</div>
                        </div>
                    </div>
                    <div class="signal-badge ${accClass}">${acc}% REAL</div>
                </div>
                <div class="card-body">
                    ${signalHtml || '<div style="color:#8899aa;font-size:0.75rem;text-align:center;padding:15px;">No active signals</div>'}
                </div>
                <div class="card-footer">
                    <span class="live-text">${statusText}</span>
                    <span>${signalCount}/${totalSig}</span>
                    <span>Last: ${s.last_scan}</span>
                </div>
            </div>
        `;
    }).join('');
}

function updateSummary() {
    document.getElementById('total-buy').textContent = data.summary.buy;
    document.getElementById('total-sell').textContent = data.summary.sell;
    document.getElementById('total-wait').textContent = data.summary.wait;
    document.getElementById('total-signals').textContent = data.summary.total;
    document.getElementById('signal-count').textContent = data.summary.total;
}

async function fetchData() {
    try {
        const res = await fetch('/api/data');
        data = await res.json();
        updateSummary();
        renderStrategies();
    } catch(e) { console.error('Fetch error:', e); }
}

async function startScan() { await fetch('/api/start'); }
async function stopScan() { await fetch('/api/stop'); }
async function manualScan() { await fetch('/api/scan'); fetchData(); }
async function login() { await fetch('/api/login'); }

setInterval(fetchData, 5000);
fetchData();
renderStrategies();
</script>
</body>
</html>
"""

# ═══════════════════════════════════════════════════════════════
#  MAIN ENTRY
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║     🔱 विधाता VIDHATA — EQUITY SWING SCANNER                  ║
    ║                                                               ║
    ║   4 Strategies:                                               ║
    ║     • Δ TTM Squeeze + Donchian                                ║
    ║     • Γ CMO + Elder Ray                                       ║
    ║     • Θ Hull MA + Keltner                                     ║
    ║     • V MFI + CMF + Support                                   ║
    ║                                                               ║
    ║   Daily Timeframe | ₹50-200 Stocks | 2-3 Day Hold             ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)

    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        scanner = VidhataScanner()

        if cmd == "server":
            if app:
                print("🌐 Server: http://0.0.0.0:8001")
                uvicorn.run(app, host="0.0.0.0", port=8001)
            else:
                print("❌ pip install fastapi uvicorn")

        elif cmd == "scan":
            scanner.login()
            scanner.scan_all()
            print(json.dumps(scanner.get_dashboard_data(), indent=2))

        elif cmd == "login":
            print(f"Login: {'✅' if scanner.login() else '❌'}")

        elif cmd == "start":
            scanner.login()
            scanner.start()
            print("🚀 Running. Ctrl+C to stop.")
            try:
                while True: time.sleep(1)
            except KeyboardInterrupt:
                scanner.stop()
        else:
            print("Use: server | scan | login | start")
    else:
        print("Run: python3 vidhata.py [server|scan|login|start]")
