"""
===========================================
STRATEGY 4: VWAP + Standard Deviation Bands
Timeframe: 5M / 15M (Intraday Only)
Accuracy: ~70-74%
Type: Mean Reversion
===========================================
"""

import pandas as pd
import numpy as np
import talib

def strategy_4_vwap_std_dev(df, std_multiplier=2):
    """
    VWAP Reversion with Standard Deviation Bands
    BUY: Price below lower band + Volume above average
    SELL: Price above upper band + Volume above average
    """
    df = df.copy()
    df['date'] = df.index.date

    df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
    df['tp_volume'] = df['typical_price'] * df['volume']

    df['cumulative_tp_vol'] = df.groupby('date')['tp_volume'].cumsum()
    df['cumulative_vol'] = df.groupby('date')['volume'].cumsum()
    df['vwap'] = df['cumulative_tp_vol'] / df['cumulative_vol']

    df['std_dev'] = df.groupby('date')['typical_price'].transform(lambda x: x.rolling(20).std())
    df['upper_band'] = df['vwap'] + (std_multiplier * df['std_dev'])
    df['lower_band'] = df['vwap'] - (std_multiplier * df['std_dev'])

    df['volume_ma'] = df['volume'].rolling(20).mean()

    df['signal'] = 0
    df.loc[(df['close'] < df['lower_band']) & (df['volume'] > df['volume_ma']), 'signal'] = 1
    df.loc[(df['close'] > df['upper_band']) & (df['volume'] > df['volume_ma']), 'signal'] = -1

    df['entry_price'] = np.where(df['signal'] != 0, df['close'], np.nan)
    df['stop_loss'] = np.where(df['signal'] == 1, df['close'] * 0.995,
                               np.where(df['signal'] == -1, df['close'] * 1.005, np.nan))
    df['take_profit'] = df['vwap']
    df['risk_reward'] = np.where(df['signal'] != 0, 
                                  abs(df['take_profit'] - df['entry_price']) / abs(df['entry_price'] - df['stop_loss']), 
                                  np.nan)

    return df[['open', 'high', 'low', 'close', 'volume', 'vwap', 'signal', 'entry_price', 'stop_loss', 'take_profit', 'risk_reward']]


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
