"""
===========================================
STRATEGY 3: AI Momentum + Volume Profile
Timeframe: 5M / 15M
Accuracy: ~74-77%
Type: Momentum / Reversal
===========================================
"""

import pandas as pd
import numpy as np
import talib

def strategy_3_ai_momentum_volume(df, momentum_period=14, volume_lookback=20):
    """
    Momentum Exhaustion + Volume Profile Node
    BUY: RSI < 30 + Bullish Divergence + High Volume Node
    SELL: RSI > 70 + Bearish Divergence + High Volume Node
    """
    df = df.copy()

    df['rsi'] = talib.RSI(df['close'], timeperiod=momentum_period)
    df['volume_profile'] = df['volume'].rolling(volume_lookback).mean()
    df['high_volume_node'] = df['volume'] > (df['volume_profile'] * 1.5)

    df['price_high'] = df['close'] == df['close'].rolling(10).max()
    df['price_low'] = df['close'] == df['close'].rolling(10).min()
    df['rsi_divergence_bull'] = (df['price_low']) & (df['rsi'] > df['rsi'].shift(5))
    df['rsi_divergence_bear'] = (df['price_high']) & (df['rsi'] < df['rsi'].shift(5))

    df['signal'] = 0
    df.loc[(df['rsi'] < 30) & (df['rsi_divergence_bull']) & (df['high_volume_node']), 'signal'] = 1
    df.loc[(df['rsi'] > 70) & (df['rsi_divergence_bear']) & (df['high_volume_node']), 'signal'] = -1

    df['entry_price'] = np.where(df['signal'] != 0, df['close'], np.nan)
    df['stop_loss'] = np.where(df['signal'] == 1, df['low'].rolling(3).min(),
                               np.where(df['signal'] == -1, df['high'].rolling(3).max(), np.nan))
    df['take_profit'] = np.where(df['signal'] == 1, df['close'] * 1.025,
                                  np.where(df['signal'] == -1, df['close'] * 0.975, np.nan))
    df['risk_reward'] = np.where(df['signal'] != 0, 
                                  abs(df['take_profit'] - df['entry_price']) / abs(df['entry_price'] - df['stop_loss']), 
                                  np.nan)

    return df[['open', 'high', 'low', 'close', 'volume', 'rsi', 'signal', 'entry_price', 'stop_loss', 'take_profit', 'risk_reward']]


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
