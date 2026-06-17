#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TRISHUL PRO - 16 Strategy Scanner + Expiry Gamma Blast
Digital Ocean Ready | Python 3.10+
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import requests

# ============================================================
# CONFIGURATION
# ============================================================

@dataclass
class Config:
    """All settings"""
    # API
    API_KEY: str = "YOUR_API_KEY"
    CLIENT_ID: str = "YOUR_CLIENT_ID"
    PASSWORD: str = "YOUR_PASSWORD"
    TOTP_SECRET: str = "YOUR_TOTP_SECRET"

    # Time
    MARKET_OPEN: str = "09:15"
    MARKET_CLOSE: str = "15:30"

    # Volume Zones (IST)
    VOLUME_ZONES = {
        "OPENING": ("09:15", "09:30"),
        "MORNING": ("09:30", "10:30"),
        "MID_MORNING": ("10:30", "11:30"),
        "PRE_EUROPE": ("11:30", "12:00"),
        "EUROPE": ("12:00", "13:00"),
        "AFTERNOON": ("13:00", "14:40"),
        "PRE_US": ("14:00", "14:40"),
        "US_PREMARKET": ("14:40", "15:30"),
        "CLOSING": ("15:20", "15:30"),
    }

    BEST_WINDOWS: List[str] = None

    def __post_init__(self):
        self.BEST_WINDOWS = ["MORNING", "US_PREMARKET"]

    # VIX
    VIX_LOW: float = 13.0
    VIX_NORMAL: float = 17.0
    VIX_HIGH: float = 22.0
    VIX_EXTREME: float = 30.0

    # Scalping
    SCALP_TARGET: int = 20
    SCALP_SL: int = 10
    TRAIL_STEP: int = 10

    # Expiry
    EXPIRY_START: str = "14:30"
    EXPIRY_END: str = "15:25"
    GAMMA_THRESHOLD: float = 0.05

    # Position Sizing
    LOT_SIZES: Dict[int, int] = None

    def __post_init__(self):
        self.BEST_WINDOWS = ["MORNING", "US_PREMARKET"]
        self.LOT_SIZES = {7: 10, 5: 5, 3: 2}

# ============================================================
# DATA FETCHER (Angel One API)
# ============================================================

class AngelOneAPI:
    """Angel One SmartAPI Integration"""

    BASE_URL = "https://apiconnect.angelone.in"

    def __init__(self, config: Config):
        self.config = config
        self.access_token = None
        self._login()

    def _login(self):
        """Login and get access token"""
        # Implementation needed
        pass

    def get_ltp(self, symbol: str, exchange: str = "NSE") -> float:
        """Get Last Traded Price"""
        # API call
        return 0.0

    def get_ohlc(self, symbol: str, interval: str = "15m", 
                 duration: int = 5) -> pd.DataFrame:
        """Get OHLC data"""
        # API call
        return pd.DataFrame()

    def get_option_chain(self, symbol: str, expiry: str) -> pd.DataFrame:
        """Get option chain with Greeks"""
        # API call
        return pd.DataFrame()

    def place_order(self, symbol: str, qty: int, 
                   side: str, order_type: str = "MARKET") -> dict:
        """Place order"""
        # API call
        return {}

# ============================================================
# INDICATORS
# ============================================================

class Indicators:
    """All technical indicators"""

    @staticmethod
    def ema(data: pd.Series, period: int) -> pd.Series:
        return data.ewm(span=period, adjust=False).mean()

    @staticmethod
    def sma(data: pd.Series, period: int) -> pd.Series:
        return data.rolling(window=period).mean()

    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, 
            period: int = 14) -> pd.Series:
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()

    @staticmethod
    def bollinger_bands(close: pd.Series, period: int = 20, 
                       std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        middle = close.rolling(window=period).mean()
        std = close.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return upper, middle, lower

    @staticmethod
    def vwap(high: pd.Series, low: pd.Series, close: pd.Series, 
             volume: pd.Series) -> pd.Series:
        typical_price = (high + low + close) / 3
        cumulative_tp_vol = (typical_price * volume).cumsum()
        cumulative_vol = volume.cumsum()
        return cumulative_tp_vol / cumulative_vol

    @staticmethod
    def supertrend(high: pd.Series, low: pd.Series, close: pd.Series,
                   period: int = 10, multiplier: float = 1.5) -> pd.Series:
        atr = Indicators.atr(high, low, close, period)
        hl2 = (high + low) / 2

        upper_band = hl2 + (multiplier * atr)
        lower_band = hl2 - (multiplier * atr)

        supertrend = pd.Series(index=close.index, dtype=float)
        direction = pd.Series(index=close.index, dtype=int)

        for i in range(len(close)):
            if i == 0:
                supertrend.iloc[i] = upper_band.iloc[i]
                direction.iloc[i] = 1
            else:
                if close.iloc[i] > supertrend.iloc[i-1]:
                    supertrend.iloc[i] = max(lower_band.iloc[i], supertrend.iloc[i-1])
                    direction.iloc[i] = 1
                else:
                    supertrend.iloc[i] = min(upper_band.iloc[i], supertrend.iloc[i-1])
                    direction.iloc[i] = -1

        return supertrend, direction

    @staticmethod
    def adx(high: pd.Series, low: pd.Series, close: pd.Series, 
            period: int = 14) -> pd.Series:
        plus_dm = high.diff()
        minus_dm = low.diff()

        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        minus_dm = abs(minus_dm)

        atr = Indicators.atr(high, low, close, period)

        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()

        return adx

    @staticmethod
    def macd(close: pd.Series, fast: int = 12, slow: int = 26, 
             signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        ema_fast = Indicators.ema(close, fast)
        ema_slow = Indicators.ema(close, slow)
        macd_line = ema_fast - ema_slow
        signal_line = Indicators.ema(macd_line, signal)
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    @staticmethod
    def stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
                   k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()

        k = 100 * (close - lowest_low) / (highest_high - lowest_low)
        d = k.rolling(window=d_period).mean()

        return k, d

    @staticmethod
    def cci(high: pd.Series, low: pd.Series, close: pd.Series,
            period: int = 20) -> pd.Series:
        tp = (high + low + close) / 3
        sma_tp = tp.rolling(window=period).mean()
        mean_dev = tp.rolling(window=period).apply(lambda x: abs(x - x.mean()).mean())
        cci = (tp - sma_tp) / (0.015 * mean_dev)
        return cci

    @staticmethod
    def cmf(high: pd.Series, low: pd.Series, close: pd.Series,
            volume: pd.Series, period: int = 20) -> pd.Series:
        mfm = ((close - low) - (high - close)) / (high - low)
        mfv = mfm * volume
        cmf = mfv.rolling(window=period).sum() / volume.rolling(window=period).sum()
        return cmf

    @staticmethod
    def mfi(high: pd.Series, low: pd.Series, close: pd.Series,
            volume: pd.Series, period: int = 14) -> pd.Series:
        typical_price = (high + low + close) / 3
        raw_money_flow = typical_price * volume

        tp_diff = typical_price.diff()
        positive_flow = pd.Series(index=close.index, dtype=float)
        negative_flow = pd.Series(index=close.index, dtype=float)

        positive_flow[tp_diff > 0] = raw_money_flow[tp_diff > 0]
        negative_flow[tp_diff < 0] = raw_money_flow[tp_diff < 0]

        positive_flow = positive_flow.fillna(0)
        negative_flow = negative_flow.fillna(0)

        positive_sum = positive_flow.rolling(window=period).sum()
        negative_sum = negative_flow.rolling(window=period).sum()

        money_ratio = positive_sum / negative_sum
        mfi = 100 - (100 / (1 + money_ratio))

        return mfi

    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        obv = pd.Series(index=close.index, dtype=float)
        obv.iloc[0] = volume.iloc[0]

        for i in range(1, len(close)):
            if close.iloc[i] > close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
            elif close.iloc[i] < close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]

        return obv

    @staticmethod
    def adl(high: pd.Series, low: pd.Series, close: pd.Series,
            volume: pd.Series) -> pd.Series:
        mfm = ((close - low) - (high - close)) / (high - low)
        mfv = mfm * volume
        adl = mfv.cumsum()
        return adl

    @staticmethod
    def fibonacci_pivot(high: float, low: float, close: float) -> Dict[str, float]:
        pivot = (high + low + close) / 3
        range_val = high - low

        return {
            "R3": pivot + range_val,
            "R2": pivot + (range_val * 0.618),
            "R1": pivot + (range_val * 0.382),
            "PIVOT": pivot,
            "S1": pivot - (range_val * 0.382),
            "S2": pivot - (range_val * 0.618),
            "S3": pivot - range_val,
        }

# ============================================================
# STRATEGY 1: VWAP EMA9 CROSS
# ============================================================

class Strategy1_VWAP_EMA9:
    """VWAP + EMA 9 Cross + Volume"""

    NAME = "VWAP_EMA9_CROSS"

    def __init__(self, config: Config):
        self.config = config

    def check(self, df: pd.DataFrame) -> Dict:
        """Check entry conditions"""
        if len(df) < 50:
            return {"signal": None}

        # Calculate indicators
        df['EMA9'] = Indicators.ema(df['close'], 9)
        df['VWAP'] = Indicators.vwap(df['high'], df['low'], df['close'], df['volume'])
        df['RSI'] = Indicators.rsi(df['close'], 14)
        df['ADX'] = Indicators.adx(df['high'], df['low'], df['close'], 14)
        df['ATR'] = Indicators.atr(df['high'], df['low'], df['close'], 14)
        df['CMF'] = Indicators.cmf(df['high'], df['low'], df['close'], df['volume'], 20)
        df['MFI'] = Indicators.mfi(df['high'], df['low'], df['close'], df['volume'], 14)
        df['OBV'] = Indicators.obv(df['close'], df['volume'])
        df['ADL'] = Indicators.adl(df['high'], df['low'], df['close'], df['volume'])

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        # Volume check
        avg_vol = df['volume'].rolling(20).mean().iloc[-1]
        vol_ratio = latest['volume'] / avg_vol if avg_vol > 0 else 0

        # Money Flow Score
        mf_score = 0
        if latest['CMF'] > 0.1: mf_score += 1
        if latest['MFI'] > 50: mf_score += 1
        if latest['OBV'] > df['OBV'].iloc[-5]: mf_score += 1
        if latest['ADL'] > df['ADL'].iloc[-5]: mf_score += 1

        # Buy conditions
        buy_conditions = [
            prev['EMA9'] <= prev['VWAP'] and latest['EMA9'] > latest['VWAP'],  # Cross
            latest['close'] > latest['VWAP'],
            vol_ratio > 2.0,
            latest['ADX'] > 25,
            45 < latest['RSI'] < 65,
            mf_score >= 3,
        ]

        # Sell conditions
        sell_conditions = [
            prev['EMA9'] >= prev['VWAP'] and latest['EMA9'] < latest['VWAP'],
            latest['close'] < latest['VWAP'],
            vol_ratio > 2.0,
            latest['ADX'] > 25,
            35 < latest['RSI'] < 55,
            mf_score >= 3,
        ]

        if all(buy_conditions):
            sl = latest['close'] - (1.5 * latest['ATR'])
            target = latest['close'] + (2.5 * latest['ATR'])
            return {
                "signal": "BUY",
                "entry": latest['close'],
                "sl": sl,
                "target": target,
                "qty_pct": self._get_qty(latest['ADX'], vol_ratio, mf_score),
                "mf_score": mf_score,
                "vol_ratio": vol_ratio,
            }

        elif all(sell_conditions):
            sl = latest['close'] + (1.5 * latest['ATR'])
            target = latest['close'] - (2.5 * latest['ATR'])
            return {
                "signal": "SELL",
                "entry": latest['close'],
                "sl": sl,
                "target": target,
                "qty_pct": self._get_qty(latest['ADX'], vol_ratio, mf_score),
                "mf_score": mf_score,
                "vol_ratio": vol_ratio,
            }

        return {"signal": None}

    def _get_qty(self, adx: float, vol_ratio: float, mf_score: int) -> int:
        score = 0
        if adx > 40: score += 3
        elif adx > 25: score += 2
        else: score += 1

        if vol_ratio > 3: score += 3
        elif vol_ratio > 2: score += 2
        else: score += 1

        score += mf_score

        if score >= 7: return 10
        elif score >= 5: return 5
        elif score >= 3: return 2
        return 0

# ============================================================
# STRATEGY 2: 15MIN BREAK + BOLLINGER + SUPERTRAND
# ============================================================

class Strategy2_15MinBreak:
    """15min Candle Break + Bollinger + SuperTrend"""

    NAME = "15MIN_BREAK"

    def __init__(self, config: Config):
        self.config = config

    def check(self, df: pd.DataFrame) -> Dict:
        if len(df) < 50:
            return {"signal": None}

        df['EMA9'] = Indicators.ema(df['close'], 9)
        df['EMA21'] = Indicators.ema(df['close'], 21)
        df['EMA50'] = Indicators.ema(df['close'], 50)
        df['EMA200'] = Indicators.ema(df['close'], 200)
        df['BB_UPPER'], df['BB_MIDDLE'], df['BB_LOWER'] = Indicators.bollinger_bands(df['close'])
        df['SUPERTREND'], df['ST_DIR'] = Indicators.supertrend(df['high'], df['low'], df['close'])
        df['RSI'] = Indicators.rsi(df['close'], 14)
        df['ADX'] = Indicators.adx(df['high'], df['low'], df['close'], 14)
        df['ATR'] = Indicators.atr(df['high'], df['low'], df['close'], 14)
        df['CMF'] = Indicators.cmf(df['high'], df['low'], df['close'], df['volume'], 20)
        df['MFI'] = Indicators.mfi(df['high'], df['low'], df['close'], df['volume'], 14)

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        avg_vol = df['volume'].rolling(20).mean().iloc[-1]
        vol_ratio = latest['volume'] / avg_vol if avg_vol > 0 else 0

        prev_high = df['high'].iloc[-2]
        prev_low = df['low'].iloc[-2]

        # Buy
        buy_conditions = [
            latest['close'] > prev_high,
            latest['close'] > df['BB_UPPER'].iloc[-1],
            latest['ST_DIR'] == 1,
            latest['close'] > latest['EMA9'] > latest['EMA21'] > latest['EMA50'] > latest['EMA200'],
            latest['RSI'] > 55,
            vol_ratio > 2.0,
            latest['ADX'] > 25,
            latest['CMF'] > 0.1,
            latest['MFI'] > 55,
        ]

        # Sell
        sell_conditions = [
            latest['close'] < prev_low,
            latest['close'] < df['BB_LOWER'].iloc[-1],
            latest['ST_DIR'] == -1,
            latest['close'] < latest['EMA9'] < latest['EMA21'] < latest['EMA50'] < latest['EMA200'],
            latest['RSI'] < 45,
            vol_ratio > 2.0,
            latest['ADX'] > 25,
            latest['CMF'] < -0.1,
            latest['MFI'] < 45,
        ]

        if all(buy_conditions):
            fib = Indicators.fibonacci_pivot(df['high'].iloc[-2], df['low'].iloc[-2], df['close'].iloc[-2])
            sl = max(fib['S1'], latest['close'] - (1.5 * latest['ATR']))
            target = latest['close'] + (2.5 * latest['ATR'])
            return {
                "signal": "BUY",
                "entry": latest['close'],
                "sl": sl,
                "target": target,
                "qty_pct": 10 if latest['ADX'] > 30 and vol_ratio > 2.5 else 5,
            }

        elif all(sell_conditions):
            fib = Indicators.fibonacci_pivot(df['high'].iloc[-2], df['low'].iloc[-2], df['close'].iloc[-2])
            sl = min(fib['R1'], latest['close'] + (1.5 * latest['ATR']))
            target = latest['close'] - (2.5 * latest['ATR'])
            return {
                "signal": "SELL",
                "entry": latest['close'],
                "sl": sl,
                "target": target,
                "qty_pct": 10 if latest['ADX'] > 30 and vol_ratio > 2.5 else 5,
            }

        return {"signal": None}

# ============================================================
# STRATEGY 3: SENTIMENT + NEWS + PROMOTER
# ============================================================

class Strategy3_Sentiment:
    """Market Sentiment + News + FII/DII + Promoter"""

    NAME = "SENTIMENT_NEWS"

    def __init__(self, config: Config):
        self.config = config

    def check(self, df: pd.DataFrame, sentiment_data: Dict) -> Dict:
        if len(df) < 20:
            return {"signal": None}

        latest = df.iloc[-1]

        # Sentiment Score (0-100)
        score = 0

        # Market trend (20%)
        if sentiment_data.get('nifty_above_20ema', False): score += 20

        # A/D ratio (15%)
        ad_ratio = sentiment_data.get('advance_decline_ratio', 1.0)
        if ad_ratio > 1.5: score += 15
        elif ad_ratio > 1.0: score += 10

        # Sector trend (15%)
        if sentiment_data.get('sector_green', False): score += 15

        # FII/DII (15%)
        fii_dii = sentiment_data.get('fii_dii_net', 0)
        if fii_dii > 500: score += 15
        elif fii_dii > 0: score += 10

        # News sentiment (15%)
        news = sentiment_data.get('news_sentiment', 'neutral')
        if news == 'positive': score += 15
        elif news == 'neutral': score += 7

        # Promoter (10%)
        promoter = sentiment_data.get('promoter_buying', False)
        if promoter: score += 10

        # VIX (10%)
        vix = sentiment_data.get('vix', 15)
        if vix < 20: score += 10
        elif vix < 25: score += 5

        # Candlestick pattern
        df['EMA5'] = Indicators.ema(df['close'], 5)

        # Bullish patterns
        bullish_candle = (
            latest['close'] > latest['open'] and
            (latest['close'] - latest['open']) > (latest['high'] - latest['low']) * 0.6
        )

        bearish_candle = (
            latest['close'] < latest['open'] and
            (latest['open'] - latest['close']) > (latest['high'] - latest['low']) * 0.6
        )

        if score >= 70 and bullish_candle:
            sl = latest['low'] - (0.5 * (latest['high'] - latest['low']))
            target = latest['close'] + (2.5 * (latest['close'] - sl))
            return {
                "signal": "BUY",
                "entry": latest['close'],
                "sl": sl,
                "target": target,
                "qty_pct": 10 if score >= 80 else 5,
                "sentiment_score": score,
            }

        elif score <= 30 and bearish_candle:
            sl = latest['high'] + (0.5 * (latest['high'] - latest['low']))
            target = latest['close'] - (2.5 * (sl - latest['close']))
            return {
                "signal": "SELL",
                "entry": latest['close'],
                "sl": sl,
                "target": target,
                "qty_pct": 10 if score <= 20 else 5,
                "sentiment_score": score,
            }

        return {"signal": None}

# ============================================================
# STRATEGY 4: S/R ZONE SNIPER
# ============================================================

class Strategy4_SRZone:
    """Support/Resistance Zone + Trendline + Candlestick"""

    NAME = "SR_ZONE_SNIPER"

    def __init__(self, config: Config):
        self.config = config
        self.zones = {}  # Pre-marked zones

    def mark_zones(self, df: pd.DataFrame, symbol: str):
        """Mark support/resistance zones"""
        highs = df['high'].rolling(20).max()
        lows = df['low'].rolling(20).min()

        # Psychological levels
        current = df['close'].iloc[-1]
        base = round(current / 500) * 500

        zones = {
            "support": [],
            "resistance": [],
        }

        # Multiple touches
        for i in range(3, len(df) - 3):
            if df['low'].iloc[i] == lows.iloc[i]:
                touch_count = sum(1 for j in range(i-5, i+5) 
                                if abs(df['low'].iloc[j] - df['low'].iloc[i]) < df['low'].iloc[i] * 0.002)
                if touch_count >= 3:
                    zones["support"].append(df['low'].iloc[i])

            if df['high'].iloc[i] == highs.iloc[i]:
                touch_count = sum(1 for j in range(i-5, i+5) 
                                if abs(df['high'].iloc[j] - df['high'].iloc[i]) < df['high'].iloc[i] * 0.002)
                if touch_count >= 3:
                    zones["resistance"].append(df['high'].iloc[i])

        self.zones[symbol] = zones
        return zones

    def check(self, df: pd.DataFrame, symbol: str) -> Dict:
        if len(df) < 50 or symbol not in self.zones:
            return {"signal": None}

        latest = df.iloc[-1]
        zones = self.zones[symbol]

        # Check if price near zone
        near_support = any(abs(latest['close'] - s) < s * 0.003 for s in zones["support"])
        near_resistance = any(abs(latest['close'] - r) < r * 0.003 for r in zones["resistance"])

        # Volume signature
        avg_vol = df['volume'].rolling(20).mean().iloc[-1]
        vol_spike = latest['volume'] > avg_vol * 2
        vol_dry = latest['volume'] < avg_vol * 0.5

        # Candlestick
        bullish = latest['close'] > latest['open'] and (latest['low'] < latest['open'])
        bearish = latest['close'] < latest['open'] and (latest['high'] > latest['open'])

        # Buy at support
        if near_support and (vol_spike or vol_dry) and bullish:
            sl = min(zones["support"]) * 0.997
            target = latest['close'] + (latest['close'] - sl) * 2.5
            return {
                "signal": "BUY",
                "entry": latest['close'],
                "sl": sl,
                "target": target,
                "qty_pct": 10,
                "zone": "support",
            }

        # Sell at resistance
        if near_resistance and (vol_spike or vol_dry) and bearish:
            sl = max(zones["resistance"]) * 1.003
            target = latest['close'] - (sl - latest['close']) * 2.5
            return {
                "signal": "SELL",
                "entry": latest['close'],
                "sl": sl,
                "target": target,
                "qty_pct": 10,
                "zone": "resistance",
            }

        return {"signal": None}

# ============================================================
# STRATEGY 5-8: INDEX STRATEGIES
# ============================================================

class IndexStrategy:
    """Base class for index strategies"""

    def __init__(self, config: Config, index_name: str):
        self.config = config
        self.index_name = index_name

    def market_check(self, df: pd.DataFrame, vix: float, 
                    sector_data: Dict, breadth: Dict) -> bool:
        """Common market checks for all index strategies"""
        latest = df.iloc[-1]

        # VIX check
        if vix > self.config.VIX_EXTREME:
            return False

        # Trend
        df['EMA9'] = Indicators.ema(df['close'], 9)
        df['EMA21'] = Indicators.ema(df['close'], 21)
        df['VWAP'] = Indicators.vwap(df['high'], df['low'], df['close'], df['volume'])

        # Sector breadth
        green_sectors = sector_data.get('green_pct', 50)
        green_stocks = breadth.get('advancing_pct', 50)

        return True

class Strategy5_NiftyTrend(IndexStrategy):
    """Nifty 50 Trend Follow"""
    NAME = "NIFTY_TREND"

    def __init__(self, config: Config):
        super().__init__(config, "NIFTY")

    def check(self, df: pd.DataFrame, vix: float, pcr: float,
             sector_data: Dict, breadth: Dict) -> Dict:
        if not self.market_check(df, vix, sector_data, breadth):
            return {"signal": None}

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        # Central pivot
        pivot = (df['high'].iloc[-2] + df['low'].iloc[-2] + df['close'].iloc[-2]) / 3

        # Conditions
        buy_conditions = [
            latest['close'] > latest['VWAP'],
            latest['EMA9'] > latest['EMA21'],
            latest['close'] > pivot,
            vix < self.config.VIX_HIGH,
            pcr < 1.0,
            sector_data.get('green_pct', 0) > 60,
            breadth.get('advancing_pct', 0) > 60,
        ]

        sell_conditions = [
            latest['close'] < latest['VWAP'],
            latest['EMA9'] < latest['EMA21'],
            latest['close'] < pivot,
            vix < self.config.VIX_HIGH,
            pcr > 1.0,
            sector_data.get('green_pct', 0) < 40,
            breadth.get('advancing_pct', 0) < 40,
        ]

        if all(buy_conditions):
            atr = Indicators.atr(df['high'], df['low'], df['close'], 14).iloc[-1]
            return {
                "signal": "BUY",
                "entry": latest['close'],
                "sl": latest['close'] - (1.5 * atr),
                "target": latest['close'] + (2.5 * atr),
                "qty_pct": 10 if vix < 17 else 5,
            }

        elif all(sell_conditions):
            atr = Indicators.atr(df['high'], df['low'], df['close'], 14).iloc[-1]
            return {
                "signal": "SELL",
                "entry": latest['close'],
                "sl": latest['close'] + (1.5 * atr),
                "target": latest['close'] - (2.5 * atr),
                "qty_pct": 10 if vix < 17 else 5,
            }

        return {"signal": None}

class Strategy6_BankNifty(IndexStrategy):
    """Bank Nifty Momentum"""
    NAME = "BANKNIFTY_MOMENTUM"

    def __init__(self, config: Config):
        super().__init__(config, "BANKNIFTY")

    def check(self, df: pd.DataFrame, lead_banks: Dict, vix: float) -> Dict:
        latest = df.iloc[-1]

        # Lead banks check
        hdfc = lead_banks.get('HDFCBANK', {})
        icici = lead_banks.get('ICICIBANK', {})
        sbi = lead_banks.get('SBIN', {})

        all_green = all(b.get('change', 0) > 0 for b in [hdfc, icici, sbi])
        all_red = all(b.get('change', 0) < 0 for b in [hdfc, icici, sbi])

        # Volume in lead bank
        hdfc_vol = hdfc.get('volume_ratio', 1.0)

        if all_green and hdfc_vol > 2.0:
            atr = Indicators.atr(df['high'], df['low'], df['close'], 14).iloc[-1]
            return {
                "signal": "BUY",
                "entry": latest['close'],
                "sl": latest['close'] - (1.5 * atr),
                "target": latest['close'] + (2.5 * atr),
                "qty_pct": 10 if vix < 15 else 5,
            }

        elif all_red and hdfc_vol > 2.0:
            atr = Indicators.atr(df['high'], df['low'], df['close'], 14).iloc[-1]
            return {
                "signal": "SELL",
                "entry": latest['close'],
                "sl": latest['close'] + (1.5 * atr),
                "target": latest['close'] - (2.5 * atr),
                "qty_pct": 10 if vix < 15 else 5,
            }

        return {"signal": None}

class Strategy7_FinNifty(IndexStrategy):
    """FinNifty Sector Play"""
    NAME = "FINNIFTY_SECTOR"

    def __init__(self, config: Config):
        super().__init__(config, "FINNIFTY")

    def check(self, df: pd.DataFrame, nbfc_data: Dict, vix: float) -> Dict:
        latest = df.iloc[-1]

        # Top financials
        hdfc = nbfc_data.get('HDFC', 0)
        icici = nbfc_data.get('ICICI', 0)
        bajaj = nbfc_data.get('BAJAJFINSV', 0)

        all_green = hdfc > 0 and icici > 0 and bajaj > 0
        all_red = hdfc < 0 and icici < 0 and bajaj < 0

        if all_green:
            return {
                "signal": "BUY",
                "entry": latest['close'],
                "qty_pct": 7 if vix < 18 else 5,
            }
        elif all_red:
            return {
                "signal": "SELL",
                "entry": latest['close'],
                "qty_pct": 7 if vix < 18 else 5,
            }

        return {"signal": None}

class Strategy8_Sensex(IndexStrategy):
    """Sensex Broad Market"""
    NAME = "SENSEX_BROAD"

    def __init__(self, config: Config):
        super().__init__(config, "SENSEX")

    def check(self, df: pd.DataFrame, sensex_stocks: Dict, vix: float) -> Dict:
        latest = df.iloc[-1]

        # Heavyweights
        reliance = sensex_stocks.get('RELIANCE', {}).get('change', 0)
        tcs = sensex_stocks.get('TCS', {}).get('change', 0)
        hdfc_bank = sensex_stocks.get('HDFCBANK', {}).get('change', 0)

        green_count = sum(1 for x in [reliance, tcs, hdfc_bank] if x > 0)

        if green_count >= 2:
            return {
                "signal": "BUY",
                "entry": latest['close'],
                "qty_pct": 10 if vix < 17 else 5,
            }
        elif green_count <= 1:
            return {
                "signal": "SELL",
                "entry": latest['close'],
                "qty_pct": 10 if vix < 17 else 5,
            }

        return {"signal": None}

# ============================================================
# STRATEGY 9-12: SCALPING
# ============================================================

class ScalpingStrategy:
    """Base scalping class"""

    def __init__(self, config: Config):
        self.config = config

    def trail_sl(self, entry: float, current: float, side: str) -> float:
        """Fixed step trailing SL"""
        profit = current - entry if side == "BUY" else entry - current

        if profit >= 30:
            return entry + 25 if side == "BUY" else entry - 25
        elif profit >= 25:
            return entry + 20 if side == "BUY" else entry - 20
        elif profit >= 20:
            return entry + 15 if side == "BUY" else entry - 15
        elif profit >= 15:
            return entry + 10 if side == "BUY" else entry - 10
        elif profit >= 10:
            return entry + 5 if side == "BUY" else entry - 5

        return entry - self.config.SCALP_SL if side == "BUY" else entry + self.config.SCALP_SL

class Strategy9_VWAPScalp(ScalpingStrategy):
    """1-Min VWAP Scalp"""
    NAME = "VWAP_SCALP"

    def check(self, df: pd.DataFrame) -> Dict:
        if len(df) < 20:
            return {"signal": None}

        latest = df.iloc[-1]
        df['VWAP'] = Indicators.vwap(df['high'], df['low'], df['close'], df['volume'])
        df['EMA9'] = Indicators.ema(df['close'], 9)

        avg_vol = df['volume'].rolling(10).mean().iloc[-1]
        vol_ratio = latest['volume'] / avg_vol if avg_vol > 0 else 0

        # Buy: Price touches VWAP from above
        if (abs(latest['close'] - latest['VWAP']) < latest['VWAP'] * 0.001 and
            latest['EMA9'] > latest['VWAP'] and
            vol_ratio > 1.5 and
            latest['close'] > latest['open']):

            return {
                "signal": "BUY",
                "entry": latest['close'],
                "sl": latest['close'] - (latest['close'] * 0.003),
                "target": latest['close'] + (latest['close'] * 0.005),
                "qty_pct": 5,
            }

        # Sell: Price touches VWAP from below
        if (abs(latest['close'] - latest['VWAP']) < latest['VWAP'] * 0.001 and
            latest['EMA9'] < latest['VWAP'] and
            vol_ratio > 1.5 and
            latest['close'] < latest['open']):

            return {
                "signal": "SELL",
                "entry": latest['close'],
                "sl": latest['close'] + (latest['close'] * 0.003),
                "target": latest['close'] - (latest['close'] * 0.005),
                "qty_pct": 5,
            }

        return {"signal": None}

class Strategy10_OBScalp(ScalpingStrategy):
    """3-Min Order Block Scalp"""
    NAME = "OB_SCALP"

    def check(self, df: pd.DataFrame) -> Dict:
        if len(df) < 30:
            return {"signal": None}

        latest = df.iloc[-1]

        # Find OB levels (recent swing low/high with volume)
        recent_lows = df['low'].rolling(5).min()
        recent_highs = df['high'].rolling(5).max()

        ob_low = recent_lows.iloc[-3]
        ob_high = recent_highs.iloc[-3]

        # Check if price at OB with volume
        at_ob_low = abs(latest['close'] - ob_low) < ob_low * 0.002
        at_ob_high = abs(latest['close'] - ob_high) < ob_high * 0.002

        avg_vol = df['volume'].rolling(10).mean().iloc[-1]
        vol_spike = latest['volume'] > avg_vol * 2

        if at_ob_low and vol_spike and latest['close'] > latest['open']:
            return {
                "signal": "BUY",
                "entry": latest['close'],
                "sl": ob_low * 0.998,
                "target": latest['close'] + (latest['close'] * 0.005),
                "qty_pct": 5,
            }

        if at_ob_high and vol_spike and latest['close'] < latest['open']:
            return {
                "signal": "SELL",
                "entry": latest['close'],
                "sl": ob_high * 1.002,
                "target": latest['close'] - (latest['close'] * 0.005),
                "qty_pct": 5,
            }

        return {"signal": None}

class Strategy11_BreakoutScalp(ScalpingStrategy):
    """5-Min Breakout Scalp"""
    NAME = "BREAKOUT_SCALP"

    def check(self, df: pd.DataFrame) -> Dict:
        if len(df) < 10:
            return {"signal": None}

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        # 5-min range
        range_high = df['high'].iloc[-5:].max()
        range_low = df['low'].iloc[-5:].min()

        avg_vol = df['volume'].rolling(5).mean().iloc[-1]
        vol_spike = latest['volume'] > avg_vol * 3

        # Breakout
        if latest['close'] > range_high and vol_spike:
            return {
                "signal": "BUY",
                "entry": latest['close'],
                "sl": range_low,
                "target": latest['close'] + (latest['close'] - range_low) * 1.5,
                "qty_pct": 5,
            }

        # Breakdown
        if latest['close'] < range_low and vol_spike:
            return {
                "signal": "SELL",
                "entry": latest['close'],
                "sl": range_high,
                "target": latest['close'] - (range_high - latest['close']) * 1.5,
                "qty_pct": 5,
            }

        return {"signal": None}

class Strategy12_FadeScalp(ScalpingStrategy):
    """15-Min Fade Scalp"""
    NAME = "FADE_SCALP"

    def check(self, df: pd.DataFrame) -> Dict:
        if len(df) < 20:
            return {"signal": None}

        latest = df.iloc[-1]
        df['BB_UPPER'], df['BB_MIDDLE'], df['BB_LOWER'] = Indicators.bollinger_bands(df['close'])
        df['RSI'] = Indicators.rsi(df['close'], 14)
        df['VWAP'] = Indicators.vwap(df['high'], df['low'], df['close'], df['volume'])

        # Overextended up
        if (latest['close'] > df['BB_UPPER'].iloc[-1] and 
            latest['RSI'] > 70 and
            latest['volume'] < df['volume'].rolling(10).mean().iloc[-1]):

            return {
                "signal": "SELL",
                "entry": latest['close'],
                "sl": latest['high'] * 1.005,
                "target": df['VWAP'].iloc[-1],
                "qty_pct": 5,
            }

        # Overextended down
        if (latest['close'] < df['BB_LOWER'].iloc[-1] and
            latest['RSI'] < 30 and
            latest['volume'] < df['volume'].rolling(10).mean().iloc[-1]):

            return {
                "signal": "BUY",
                "entry": latest['close'],
                "sl": latest['low'] * 0.995,
                "target": df['VWAP'].iloc[-1],
                "qty_pct": 5,
            }

        return {"signal": None}

# ============================================================
# STRATEGY 13-16: EXPIRY GAMMA BLAST
# ============================================================

class ExpiryGammaBlast:
    """Expiry Day Gamma Blast Strategy"""

    NAME = "EXPIRY_GAMMA_BLAST"

    def __init__(self, config: Config):
        self.config = config

    def calculate_gamma_score(self, option_chain: pd.DataFrame, 
                             spot: float) -> Dict:
        """Calculate gamma exposure"""
        # Find ATM strike
        atm_strike = round(spot / 50) * 50  # For Nifty

        atm_data = option_chain[option_chain['strike'] == atm_strike]

        if len(atm_data) == 0:
            return {"score": 0, "direction": None}

        ce_gamma = atm_data[atm_data['type'] == 'CE']['gamma'].values[0] if len(atm_data[atm_data['type'] == 'CE']) > 0 else 0
        pe_gamma = atm_data[atm_data['type'] == 'PE']['gamma'].values[0] if len(atm_data[atm_data['type'] == 'PE']) > 0 else 0

        # Net gamma
        net_gamma = ce_gamma - pe_gamma

        return {
            "score": abs(net_gamma),
            "direction": "BUY" if net_gamma > 0 else "SELL",
            "atm_strike": atm_strike,
            "ce_gamma": ce_gamma,
            "pe_gamma": pe_gamma,
        }

    def calculate_pcr(self, option_chain: pd.DataFrame) -> float:
        """Calculate Put-Call Ratio"""
        total_ce_oi = option_chain[option_chain['type'] == 'CE']['oi'].sum()
        total_pe_oi = option_chain[option_chain['type'] == 'PE']['oi'].sum()

        if total_ce_oi == 0:
            return 1.0

        return total_pe_oi / total_ce_oi

    def get_max_pain(self, option_chain: pd.DataFrame) -> float:
        """Calculate Max Pain"""
        strikes = option_chain['strike'].unique()

        pain = {}
        for strike in strikes:
            ce_oi = option_chain[(option_chain['strike'] == strike) & 
                                (option_chain['type'] == 'CE')]['oi'].sum()
            pe_oi = option_chain[(option_chain['strike'] == strike) & 
                                (option_chain['type'] == 'PE')]['oi'].sum()

            pain[strike] = ce_oi + pe_oi

        return min(pain, key=pain.get)

    def check(self, spot: float, option_chain: pd.DataFrame,
             vix: float, volume: float, avg_volume: float) -> Dict:
        """Check expiry setup"""

        # Time check
        current_time = datetime.now().strftime("%H:%M")
        if not (self.config.EXPIRY_START <= current_time <= self.config.EXPIRY_END):
            return {"signal": None, "reason": "Outside expiry window"}

        # Gamma score
        gamma_data = self.calculate_gamma_score(option_chain, spot)
        gamma_score = gamma_data['score']
        gamma_direction = gamma_data['direction']

        # PCR
        pcr = self.calculate_pcr(option_chain)

        # Max pain
        max_pain = self.get_max_pain(option_chain)

        # Volume
        vol_ratio = volume / avg_volume if avg_volume > 0 else 0

        # Lot size decision
        lot_size = self._get_lot_size(gamma_score, vol_ratio, pcr)

        # Direction from PCR extreme
        if pcr < 0.5:
            # Extreme call writing = short
            direction = "SELL"
            hedge = "BUY"
        elif pcr > 1.5:
            # Extreme put writing = long
            direction = "BUY"
            hedge = "SELL"
        else:
            # Follow gamma
            direction = gamma_direction
            hedge = "SELL" if direction == "BUY" else "BUY"

        # Main position
        main_lots = lot_size
        hedge_lots = max(2, lot_size // 3)  # 2-3 lots hedge

        # Strike selection
        atm_strike = gamma_data['atm_strike']

        if direction == "BUY":
            main_strike = atm_strike  # ATM CE
            hedge_strike = atm_strike + 100  # OTM PE
        else:
            main_strike = atm_strike  # ATM PE
            hedge_strike = atm_strike - 100  # OTM CE

        return {
            "signal": direction,
            "entry": spot,
            "main_lots": main_lots,
            "main_strike": main_strike,
            "main_type": "CE" if direction == "BUY" else "PE",
            "hedge_lots": hedge_lots,
            "hedge_strike": hedge_strike,
            "hedge_type": "PE" if direction == "BUY" else "CE",
            "sl": spot - 15 if direction == "BUY" else spot + 15,
            "target": spot + 30 if direction == "BUY" else spot - 30,
            "gamma_score": gamma_score,
            "pcr": pcr,
            "max_pain": max_pain,
            "vol_ratio": vol_ratio,
            "trail_step": 10,
        }

    def _get_lot_size(self, gamma: float, vol_ratio: float, pcr: float) -> int:
        """Calculate lot size based on confluence"""
        score = 0

        # Gamma
        if gamma > 0.05: score += 3
        elif gamma > 0.02: score += 2
        else: score += 1

        # Volume
        if vol_ratio > 3: score += 3
        elif vol_ratio > 2: score += 2
        else: score += 1

        # PCR extreme
        if pcr < 0.5 or pcr > 1.5: score += 3
        elif pcr < 0.7 or pcr > 1.3: score += 2
        else: score += 1

        if score >= 7: return 10
        elif score >= 5: return 5
        elif score >= 3: return 2
        return 0

class Strategy13_ExpiryMain(ExpiryGammaBlast):
    """Main Expiry Gamma Blast"""
    NAME = "EXPIRY_MAIN"

class Strategy14_ExpiryHedge(ExpiryGammaBlast):
    """Expiry Hedge Position"""
    NAME = "EXPIRY_HEDGE"

class Strategy15_ExpiryScalp(ExpiryGammaBlast):
    """Expiry Scalping (15 point steps)"""
    NAME = "EXPIRY_SCALP"

    def scalp_check(self, spot: float, entry: float, side: str) -> Dict:
        """15 point scalp within expiry"""
        profit = spot - entry if side == "BUY" else entry - spot

        if profit >= 15:
            return {"action": "BOOK_50", "trail_sl": entry + 10 if side == "BUY" else entry - 10}
        elif profit >= 30:
            return {"action": "BOOK_30", "trail_sl": entry + 20 if side == "BUY" else entry - 20}
        elif profit >= 45:
            return {"action": "BOOK_20", "trail_sl": entry + 35 if side == "BUY" else entry - 35}

        return {"action": "HOLD", "trail_sl": entry - 15 if side == "BUY" else entry + 15}

class Strategy16_ExpiryReversal(ExpiryGammaBlast):
    """Expiry Reversal (PCR extreme + gamma flip)"""
    NAME = "EXPIRY_REVERSAL"

    def check_reversal(self, pcr_history: List[float], 
                      gamma_history: List[float]) -> bool:
        """Check if reversal coming"""
        # PCR extreme then reversing
        if len(pcr_history) < 5:
            return False

        pcr_trend = pcr_history[-1] - pcr_history[-3]
        gamma_trend = gamma_history[-1] - gamma_history[-3]

        # PCR was extreme, now reversing
        if (pcr_history[-3] < 0.5 and pcr_trend > 0.1) or            (pcr_history[-3] > 1.5 and pcr_trend < -0.1):
            return True

        # Gamma flip
        if gamma_history[-3] > 0 and gamma_trend < -0.02:
            return True
        if gamma_history[-3] < 0 and gamma_trend > 0.02:
            return True

        return False

# ============================================================
# MAIN SCANNER ENGINE
# ============================================================

class TrishulProScanner:
    """Main scanner engine - runs all 16 strategies"""

    def __init__(self, config: Config):
        self.config = config
        self.api = AngelOneAPI(config)

        # Initialize all strategies
        self.strategies = {
            1: Strategy1_VWAP_EMA9(config),
            2: Strategy2_15MinBreak(config),
            3: Strategy3_Sentiment(config),
            4: Strategy4_SRZone(config),
            5: Strategy5_NiftyTrend(config),
            6: Strategy6_BankNifty(config),
            7: Strategy7_FinNifty(config),
            8: Strategy8_Sensex(config),
            9: Strategy9_VWAPScalp(config),
            10: Strategy10_OBScalp(config),
            11: Strategy11_BreakoutScalp(config),
            12: Strategy12_FadeScalp(config),
            13: Strategy13_ExpiryMain(config),
            14: Strategy14_ExpiryHedge(config),
            15: Strategy15_ExpiryScalp(config),
            16: Strategy16_ExpiryReversal(config),
        }

        self.active_signals = []
        self.positions = {}

    def scan_stock(self, symbol: str, df: pd.DataFrame, 
                   sentiment: Optional[Dict] = None) -> List[Dict]:
        """Scan single stock with all applicable strategies"""
        signals = []

        # Stock strategies (1-4)
        for i in [1, 2, 3, 4]:
            if i == 3 and sentiment:
                result = self.strategies[i].check(df, sentiment)
            else:
                result = self.strategies[i].check(df)

            if result.get("signal"):
                signals.append({
                    "strategy": self.strategies[i].NAME,
                    "strategy_num": i,
                    "symbol": symbol,
                    **result
                })

        return signals

    def scan_index(self, index_name: str, df: pd.DataFrame,
                  market_data: Dict) -> List[Dict]:
        """Scan index with index strategies"""
        signals = []

        # Index strategies (5-8)
        index_map = {
            "NIFTY": 5,
            "BANKNIFTY": 6,
            "FINNIFTY": 7,
            "SENSEX": 8,
        }

        if index_name in index_map:
            strategy_num = index_map[index_name]
            result = self.strategies[strategy_num].check(df, **market_data)

            if result.get("signal"):
                signals.append({
                    "strategy": self.strategies[strategy_num].NAME,
                    "strategy_num": strategy_num,
                    "symbol": index_name,
                    **result
                })

        return signals

    def scan_scalp(self, symbol: str, df: pd.DataFrame) -> List[Dict]:
        """Scan for scalping opportunities"""
        signals = []

        # Scalping strategies (9-12)
        for i in [9, 10, 11, 12]:
            result = self.strategies[i].check(df)

            if result.get("signal"):
                signals.append({
                    "strategy": self.strategies[i].NAME,
                    "strategy_num": i,
                    "symbol": symbol,
                    **result
                })

        return signals

    def scan_expiry(self, spot: float, option_chain: pd.DataFrame,
                   vix: float, volume: float, avg_volume: float) -> List[Dict]:
        """Scan for expiry gamma blast"""
        signals = []

        # Expiry strategies (13-16)
        for i in [13, 15, 16]:
            if i == 13:
                result = self.strategies[i].check(spot, option_chain, vix, volume, avg_volume)
            elif i == 15:
                # Scalp check needs active position
                continue
            elif i == 16:
                # Reversal check needs history
                continue

            if result and result.get("signal"):
                signals.append({
                    "strategy": self.strategies[i].NAME,
                    "strategy_num": i,
                    "symbol": "NIFTY_EXPIRY",
                    **result
                })

        return signals

    def execute_signal(self, signal: Dict) -> bool:
        """Execute trading signal"""
        # Place order via API
        # Implementation needed

        self.active_signals.append(signal)
        self.positions[signal['symbol']] = signal

        return True

    def trail_positions(self, current_prices: Dict):
        """Trail all active positions"""
        for symbol, position in self.positions.items():
            current = current_prices.get(symbol, 0)

            if position.get('strategy_num') in [9, 10, 11, 12, 15]:
                # Scalping - fixed step trail
                trail = ScalpingStrategy(self.config)
                new_sl = trail.trail_sl(
                    position['entry'], 
                    current, 
                    position['signal']
                )
                position['sl'] = new_sl
            else:
                # Regular - ATR trail
                pass  # Implement ATR trail

    def generate_report(self) -> pd.DataFrame:
        """Generate daily report"""
        return pd.DataFrame(self.active_signals)

# ============================================================
# DIGITAL OCEAN DEPLOYMENT
# ============================================================

"""
# requirements.txt
pandas==2.0.3
numpy==1.24.3
requests==2.31.0
python-dateutil==2.8.2
pyotp==2.9.0
websocket-client==1.6.1

# Dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "trishul_pro.py"]

# docker-compose.yml
version: '3.8'
services:
  trishul:
    build: .
    container_name: trishul_pro
    restart: unless-stopped
    environment:
      - API_KEY=${API_KEY}
      - CLIENT_ID=${CLIENT_ID}
      - PASSWORD=${PASSWORD}
      - TOTP_SECRET=${TOTP_SECRET}
    volumes:
      - ./logs:/app/logs
    networks:
      - trading

networks:
  trading:
    driver: bridge
"""

# ============================================================
# MAIN EXECUTION
# ============================================================

if __name__ == "__main__":
    # Initialize
    config = Config()
    scanner = TrishulProScanner(config)

    # Main loop
    while True:
        current_time = datetime.now().strftime("%H:%M")

        # Check market hours
        if config.MARKET_OPEN <= current_time <= config.MARKET_CLOSE:
            # Run scans
            # Implementation needed with real data
            pass

        # Sleep
        time.sleep(60)
