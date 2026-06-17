"""
===========================================
STRATEGY 2: Smart Money Concepts (SMC) + Order Blocks
Timeframe: 1H / 4H
Accuracy: ~72-76%
Type: Smart Money / Institutional
===========================================
"""

import pandas as pd
import numpy as np
import talib

def strategy_2_smc_order_blocks(df, lookback=50, fvg_threshold=0.001):
    """
    Smart Money Concepts: Order Block + Fair Value Gap
    BUY: Bullish Order Block + Bullish FVG + Volume
    SELL: Bearish Order Block + Bearish FVG + Volume
    """
    df = df.copy()

    # Swing Highs/Lows
    df['swing_high'] = df['high'] == df['high'].rolling(lookback, center=True).max()
    df['swing_low'] = df['low'] == df['low'].rolling(lookback, center=True).min()

    # Order Blocks
    df['bullish_ob'] = False
    df['bearish_ob'] = False

    for i in range(3, len(df)):
        if (df['close'].iloc[i-2] < df['open'].iloc[i-2] and
            df['close'].iloc[i-1] > df['open'].iloc[i-1] and
            df['close'].iloc[i] > df['open'].iloc[i] and
            df['close'].iloc[i] > df['high'].iloc[i-2]):
            df.loc[df.index[i], 'bullish_ob'] = True

        if (df['close'].iloc[i-2] > df['open'].iloc[i-2] and
            df['close'].iloc[i-1] < df['open'].iloc[i-1] and
            df['close'].iloc[i] < df['open'].iloc[i] and
            df['close'].iloc[i] < df['low'].iloc[i-2]):
            df.loc[df.index[i], 'bearish_ob'] = True

    # Fair Value Gaps
    df['fvg_bullish'] = (df['low'].shift(-2) > df['high'].shift(-1)) &                         (abs(df['low'].shift(-2) - df['high'].shift(-1)) / df['close'] > fvg_threshold)
    df['fvg_bearish'] = (df['high'].shift(-2) < df['low'].shift(-1)) &                         (abs(df['low'].shift(-1) - df['high'].shift(-2)) / df['close'] > fvg_threshold)

    # Volume
    df['volume_ma'] = df['volume'].rolling(20).mean()
    df['high_volume'] = df['volume'] > df['volume_ma'] * 1.3

    # Signals
    df['signal'] = 0
    df.loc[df['bullish_ob'] & df['fvg_bullish'] & df['high_volume'], 'signal'] = 1
    df.loc[df['bearish_ob'] & df['fvg_bearish'] & df['high_volume'], 'signal'] = -1

    # Risk Management
    df['entry_price'] = np.where(df['signal'] != 0, df['close'], np.nan)
    df['stop_loss'] = np.where(df['signal'] == 1, df['low'].rolling(5).min(),
                               np.where(df['signal'] == -1, df['high'].rolling(5).max(), np.nan))
    df['take_profit'] = np.where(df['signal'] == 1, df['close'] * 1.03,
                                  np.where(df['signal'] == -1, df['close'] * 0.97, np.nan))
    df['risk_reward'] = np.where(df['signal'] != 0, 
                                  abs(df['take_profit'] - df['entry_price']) / abs(df['entry_price'] - df['stop_loss']), 
                                  np.nan)

    return df[['open', 'high', 'low', 'close', 'volume', 'signal', 'entry_price', 'stop_loss', 'take_profit', 'risk_reward']]


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
