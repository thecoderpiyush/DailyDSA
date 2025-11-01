"""
Entry Signal Detection Module
Implements logic for detecting long entry signals
"""

import pandas as pd
import numpy as np


class EntrySignalDetector:
    """Detects entry signals based on strategy rules"""
    
    def __init__(self, config, account_equity: float):
        self.config = config
        self.account_equity = account_equity
    
    def check_long_entry(self, df: pd.DataFrame, current_index: int) -> tuple:
        """
        Check if long entry conditions are met
        
        Args:
            df: DataFrame with price data and indicators
            current_index: Current bar index
            
        Returns:
            Tuple of (entry_signal: bool, trade_params: dict or None)
        """
        # Skip if not enough history
        if current_index < 250:
            return False, None
        
        current_bar = df.iloc[current_index]
        prev_bar = df.iloc[current_index - 1]
        
        # Skip if indicators are NaN
        required_fields = ['EMA200', 'RSI', 'ATR', 'Volume_MA20']
        if any(pd.isna(current_bar[field]) for field in required_fields):
            return False, None
        
        # === ENTRY CONDITIONS ===
        
        # 1. TREND FILTER: Price above 200 EMA
        trend_valid = current_bar['close'] > current_bar['EMA200']
        if not trend_valid:
            return False, None
        
        # 2. LIQUIDITY FILTER
        liquid = (current_bar['Volume_MA20'] > self.config.MIN_AVG_VOLUME and 
                  current_bar['close'] > self.config.MIN_PRICE)
        if not liquid:
            return False, None
        
        # 3. RSI PULLBACK PATTERN
        # Check if RSI was in pullback zone in last 5 bars
        pullback_occurred = False
        for i in range(1, 6):
            if current_index - i < 0:
                break
            lookback_bar = df.iloc[current_index - i]
            if (self.config.RSI_PULLBACK_LOWER <= lookback_bar['RSI'] <= 
                self.config.RSI_PULLBACK_UPPER):
                pullback_occurred = True
                break
        
        # Check current RSI recovery
        rsi_recovery = (current_bar['RSI'] > self.config.RSI_RECOVERY_THRESHOLD and
                       prev_bar['RSI'] <= self.config.RSI_RECOVERY_THRESHOLD)
        
        rsi_valid = pullback_occurred and rsi_recovery
        if not rsi_valid:
            return False, None
        
        # 4. PRICE STRUCTURE: Must not close below 200 EMA on signal bar
        price_structure_valid = current_bar['close'] > current_bar['EMA200']
        if not price_structure_valid:
            return False, None
        
        # 5. VOLUME CONFIRMATION
        volume_confirmed = current_bar['Volume_Ratio'] >= self.config.VOLUME_MULTIPLIER
        if not volume_confirmed:
            return False, None
        
        # === ALL CONDITIONS MET - CALCULATE TRADE PARAMETERS ===
        
        entry_price = current_bar['close']
        
        # Calculate stop loss options
        atr_stop = entry_price - (self.config.ATR_STOP_MULTIPLIER * current_bar['ATR'])
        ema_stop = current_bar['EMA200']
        swing_stop = current_bar['swing_low_20'] - (0.5 * current_bar['ATR'])
        
        # Choose the tightest (highest) stop that's still below entry
        stop_loss = max(atr_stop, ema_stop, swing_stop)
        
        # Validate stop
        if stop_loss >= entry_price:
            return False, None  # Invalid stop
        
        if (entry_price - stop_loss) / entry_price > self.config.MAX_STOP_LOSS_PERCENT:
            return False, None  # Stop too wide
        
        # Calculate risk and position size
        risk_per_share = entry_price - stop_loss
        risk_amount = self.account_equity * self.config.RISK_PER_TRADE
        position_size = int(risk_amount / risk_per_share)
        
        # Liquidity constraint: don't exceed 2% of average daily volume
        max_shares = int(current_bar['Volume_MA20'] * self.config.MAX_POSITION_SIZE_OF_ADV)
        position_size = min(position_size, max_shares)
        
        if position_size <= 0:
            return False, None
        
        # Calculate targets
        target_2r = entry_price + (self.config.PROFIT_TAKE_RATIO * risk_per_share)
        
        trade_signal = {
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'target_2r': target_2r,
            'position_size': position_size,
            'risk_per_share': risk_per_share,
            'risk_amount': position_size * risk_per_share,
            'atr': current_bar['ATR'],
            'rsi': current_bar['RSI'],
            'date': current_bar.name if isinstance(current_bar.name, pd.Timestamp) else current_bar['timestamp']
        }
        
        return True, trade_signal
