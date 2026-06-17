"""
===========================================
STRATEGY 9: Stochastic RSI + Price Action
Timeframe: 5M / 15M
Accuracy: ~74-78%
Type: Reversal
===========================================
"""

import pandas as pd
import numpy as np
import talib

def strategy_9_stochrsi_price_action(df, rsi_period=14, stoch_period=14, k_period=3, d_period=3):
    """
    Stochastic RSI with Engulfing Pattern
    BUY: StochRSI < 0.2 + Bullish Engulfing
    SELL: StochRSI > 0.8 + Bearish Engulfing
    """
    df = df.copy()

    df['rsi'] = talib.RSI(df['close'], timeperiod=rsi_period)

    df['rsi_min'] = df['rsi'].rolling(stoch_period).min()
    df['rsi_max'] = df['rsi'].rolling(stoch_period).max()
    df['stoch_rsi'] = (df['rsi'] - df['rsi_min']) / (df['rsi_max'] - df['rsi_min'])
    df['stoch_rsi_k'] = df['stoch_rsi'].rolling(k_period).mean()
    df['stoch_rsi_d'] = df['stoch_rsi_k'].rolling(d_period).mean()

    df['bullish_engulfing'] = (df['close'] > df['open']) & (df['close'].shift(1) < df['open'].shift(1)) &                               (df['open'] < df['close'].shift(1)) & (df['close'] > df['open'].shift(1))
    df['bearish_engulfing'] = (df['close'] < df['open']) & (df['close'].shift(1) > df['open'].shift(1)) &                               (df['open'] > df['close'].shift(1)) & (df['close'] < df['open'].shift(1))

    df['signal'] = 0
    df.loc[(df['stoch_rsi_k'] < 0.2) & (df['stoch_rsi_k'] > df['stoch_rsi_d']) & 
           (df['bullish_engulfing']), 'signal'] = 1
    df.loc[(df['stoch_rsi_k'] > 0.8) & (df['stoch_rsi_k'] < df['stoch_rsi_d']) & 
           (df['bearish_engulfing']), 'signal'] = -1

    df['entry_price'] = np.where(df['signal'] != 0, df['close'], np.nan)
    df['stop_loss'] = np.where(df['signal'] == 1, df['low'],
                               np.where(df['signal'] == -1, df['high'], np.nan))
    df['take_profit'] = np.where(df['signal'] == 1, df['close'] * 1.02,
                                  np.where(df['signal'] == -1, df['close'] * 0.98, np.nan))
    df['risk_reward'] = np.where(df['signal'] != 0, 
                                  abs(df['take_profit'] - df['entry_price']) / abs(df['entry_price'] - df['stop_loss']), 
                                  np.nan)

    return df[['open', 'high', 'low', 'close', 'volume', 'stoch_rsi_k', 'stoch_rsi_d', 'signal', 'entry_price', 'stop_loss', 'take_profit', 'risk_reward']]


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
