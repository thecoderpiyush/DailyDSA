"""
Exit Signal Detection Module
Implements logic for detecting exit signals
"""

import pandas as pd
import numpy as np


class ExitSignalDetector:
    """Detects exit signals based on strategy rules"""
    
    def __init__(self, config):
        self.config = config
    
    def check_exits(self, df: pd.DataFrame, current_index: int, position: dict) -> tuple:
        """
        Check if exit conditions are met for a position
        
        Args:
            df: DataFrame with price data and indicators
            current_index: Current bar index
            position: Position dictionary
            
        Returns:
            Tuple of (exit_triggered: bool, exit_reason: str, exit_price: float)
        """
        current_bar = df.iloc[current_index]
        
        # === EXIT CONDITIONS (checked in priority order) ===
        
        # 1. STOP LOSS HIT (highest priority)
        if current_bar['low'] <= position['stop_loss']:
            return True, "STOP_LOSS", position['stop_loss']
        
        # 2. PROFIT TARGET HIT (2R)
        if current_bar['high'] >= position['target_2r']:
            return True, "TARGET_2R", position['target_2r']
        
        # 3. TREND INVALIDATION (close below 200 EMA)
        if pd.notna(current_bar['EMA200']) and current_bar['close'] < current_bar['EMA200']:
            return True, "EMA200_BREAK", current_bar['close']
        
        # 4. TRAILING STOP (only after reaching 5% gain)
        highest_since_entry = df.iloc[position['entry_index']:current_index + 1]['high'].max()
        gain_pct = (highest_since_entry - position['entry_price']) / position['entry_price']
        
        if gain_pct >= self.config.TRAILING_STOP_ACTIVATION_GAIN:
            trailing_stop = highest_since_entry - (self.config.TRAIL_STOP_ATR * current_bar['ATR'])
            
            if current_bar['close'] < trailing_stop:
                return True, "TRAILING_STOP", current_bar['close']
        
        # 5. TIME STOP (30 days with minimal progress)
        hold_days = current_index - position['entry_index']
        if hold_days >= self.config.TIME_STOP_DAYS:
            gain_pct = (current_bar['close'] - position['entry_price']) / position['entry_price']
            if gain_pct < self.config.TIME_STOP_MIN_GAIN:
                return True, "TIME_STOP", current_bar['close']
        
        return False, "", 0.0
    
    def check_partial_exit(self, df: pd.DataFrame, current_index: int, position: dict) -> bool:
        """
        Check if partial profit taking should occur
        
        Args:
            df: DataFrame with price data and indicators
            current_index: Current bar index
            position: Position dictionary
            
        Returns:
            bool: True if partial exit should occur
        """
        if position.get('partial_taken', False):
            return False
        
        current_bar = df.iloc[current_index]
        
        # Partial exit at 2R target
        if current_bar['high'] >= position['target_2r']:
            return True
        
        return False
