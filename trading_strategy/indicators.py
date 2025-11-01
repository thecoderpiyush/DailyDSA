"""
Technical Indicators Module
Implements EMA, RSI, ATR and Volume indicators
"""

import pandas as pd
import numpy as np


def calculate_ema(data: pd.Series, period: int) -> pd.Series:
    """
    Calculate Exponential Moving Average
    
    Args:
        data: Price series (typically close prices)
        period: EMA period
        
    Returns:
        EMA series
    """
    return data.ewm(span=period, adjust=False).mean()


def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate RSI using Wilder's method
    
    Args:
        data: Price series (typically close prices)
        period: RSI period (default 14)
        
    Returns:
        RSI series
    """
    delta = data.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    # Use Wilder's smoothing (EMA with alpha=1/period)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Average True Range
    
    Args:
        high: High price series
        low: Low price series
        close: Close price series
        period: ATR period (default 14)
        
    Returns:
        ATR series
    """
    high_low = high - low
    high_prev_close = abs(high - close.shift(1))
    low_prev_close = abs(low - close.shift(1))
    
    true_range = pd.concat([high_low, high_prev_close, low_prev_close], axis=1).max(axis=1)
    atr = true_range.ewm(alpha=1/period, adjust=False).mean()
    
    return atr


def calculate_volume_indicators(volume: pd.Series, period: int = 20) -> tuple:
    """
    Calculate volume-based indicators
    
    Args:
        volume: Volume series
        period: Moving average period
        
    Returns:
        Tuple of (volume_ma, volume_ratio)
    """
    volume_ma = volume.rolling(window=period).mean()
    volume_ratio = volume / volume_ma
    
    return volume_ma, volume_ratio


def calculate_swing_low(low: pd.Series, period: int = 20) -> pd.Series:
    """
    Calculate swing low over a period
    
    Args:
        low: Low price series
        period: Lookback period
        
    Returns:
        Swing low series
    """
    return low.rolling(window=period).min()


def calculate_all_indicators(df: pd.DataFrame, config) -> pd.DataFrame:
    """
    Calculate all technical indicators for the strategy
    
    Args:
        df: DataFrame with OHLCV data (columns: open, high, low, close, volume)
        config: Strategy configuration object
        
    Returns:
        DataFrame with added indicator columns
    """
    df = df.copy()
    
    # EMA 200
    df['EMA200'] = calculate_ema(df['close'], config.EMA_PERIOD)
    
    # RSI 14
    df['RSI'] = calculate_rsi(df['close'], config.RSI_PERIOD)
    df['RSI_prev'] = df['RSI'].shift(1)
    
    # ATR 14
    df['ATR'] = calculate_atr(df['high'], df['low'], df['close'], config.ATR_PERIOD)
    
    # Volume indicators
    df['Volume_MA20'], df['Volume_Ratio'] = calculate_volume_indicators(
        df['volume'], config.VOLUME_MA_PERIOD
    )
    
    # Swing structure
    df['swing_low_20'] = calculate_swing_low(df['low'], 20)
    
    return df
