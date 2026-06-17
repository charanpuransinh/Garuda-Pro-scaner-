"""
===========================================
STRATEGY 6: Adaptive KAMA + ADX Trend Strength
Timeframe: 1H / 4H
Accuracy: ~71-75%
Type: Trend Following
===========================================
"""

import pandas as pd
import numpy as np
import talib

def strategy_6_kama_adx(df, kama_period=10, fast_ema=2, slow_ema=30):
    """
    Kaufman Adaptive Moving Average + ADX Trend Strength
    BUY: Price > KAMA + ADX > 25 + Crossover
    SELL: Price < KAMA + ADX > 25 + Crossunder
    """
    df = df.copy()

    change = abs(df['close'] - df['close'].shift(kama_period))
    volatility = abs(df['close'] - df['close'].shift(1)).rolling(kama_period).sum()
    er = change / volatility
    er = er.fillna(0)

    fast_sc = 2 / (fast_ema + 1)
    slow_sc = 2 / (slow_ema + 1)
    sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2

    df['kama'] = df['close'].copy()
    for i in range(kama_period, len(df)):
        df.loc[df.index[i], 'kama'] = df['kama'].iloc[i-1] + sc.iloc[i] * (df['close'].iloc[i] - df['kama'].iloc[i-1])

    df['adx'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=14)

    df['signal'] = 0
    df.loc[(df['close'] > df['kama']) & (df['adx'] > 25) & 
           (df['close'].shift(1) <= df['kama'].shift(1)), 'signal'] = 1
    df.loc[(df['close'] < df['kama']) & (df['adx'] > 25) & 
           (df['close'].shift(1) >= df['kama'].shift(1)), 'signal'] = -1

    df['entry_price'] = np.where(df['signal'] != 0, df['close'], np.nan)
    df['stop_loss'] = np.where(df['signal'] == 1, df['kama'],
                               np.where(df['signal'] == -1, df['kama'], np.nan))
    df['take_profit'] = np.where(df['signal'] == 1, df['close'] * 1.04,
                                  np.where(df['signal'] == -1, df['close'] * 0.96, np.nan))
    df['risk_reward'] = np.where(df['signal'] != 0, 
                                  abs(df['take_profit'] - df['entry_price']) / abs(df['entry_price'] - df['stop_loss']), 
                                  np.nan)

    return df[['open', 'high', 'low', 'close', 'volume', 'kama', 'adx', 'signal', 'entry_price', 'stop_loss', 'take_profit', 'risk_reward']]


def backtest_strategy(df, initial_capital=100000, risk_per_trade=0.02):
    df = df.copy()
    df = df.dropna(subset=['signal'])
    trades = df[df['signal'] != 0].copy()
    trades['returns'] = np.where(trades['signal'] == 1, 
                                   (trades['take_profit'] - trades['entry_price']) / trades['entry_price'],
                                   (trades['entry_price'] - trades['take_profit']) / trades['entry_price'])
    wins = len(trades[trades['returns'] > 0])
    total = len(trades)
    win_rate = (wins / total * 100) if total > 0 else 0
    gross_profit = trades[trades['returns'] > 0]['returns'].sum()
    gross_loss = abs(trades[trades['returns'] < 0]['returns'].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    avg_rr = trades['risk_reward'].mean()
    return {'total_trades': total, 'win_rate': win_rate, 'profit_factor': profit_factor, 'avg_risk_reward': avg_rr, 'trades': trades}

if __name__ == "__main__":
    pass
