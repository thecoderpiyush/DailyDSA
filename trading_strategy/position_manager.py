"""
Position Management Module
Handles opening, closing, and managing positions
"""

from typing import List, Dict
import pandas as pd


class PositionManager:
    """Manages trading positions and portfolio state"""
    
    def __init__(self, initial_capital: float, config):
        self.config = config
        self.initial_capital = initial_capital
        self.account_equity = initial_capital
        self.cash_available = initial_capital
        self.open_positions: List[Dict] = []
        self.closed_trades: List[Dict] = []
    
    def can_open_new_position(self) -> bool:
        """
        Check if a new position can be opened
        
        Returns:
            bool: True if new position can be opened
        """
        if len(self.open_positions) >= self.config.MAX_CONCURRENT_POSITIONS:
            return False
        
        if self.cash_available < self.account_equity * self.config.MIN_CASH_BUFFER:
            return False
        
        return True
    
    def open_position(self, instrument_key: str, trade_signal: dict, current_index: int) -> bool:
        """
        Open a new position
        
        Args:
            instrument_key: Stock symbol or identifier
            trade_signal: Trade parameters from entry signal
            current_index: Current bar index
            
        Returns:
            bool: True if position opened successfully
        """
        cost = trade_signal['entry_price'] * trade_signal['position_size']
        
        if cost > self.cash_available:
            return False
        
        position = {
            'instrument_key': instrument_key,
            'entry_date': trade_signal['date'],
            'entry_price': trade_signal['entry_price'],
            'entry_index': current_index,
            'stop_loss': trade_signal['stop_loss'],
            'target_2r': trade_signal['target_2r'],
            'position_size': trade_signal['position_size'],
            'initial_position_size': trade_signal['position_size'],
            'risk_amount': trade_signal['risk_amount'],
            'partial_taken': False,
            'atr': trade_signal['atr'],
            'rsi': trade_signal['rsi']
        }
        
        self.cash_available -= cost
        self.open_positions.append(position)
        
        return True
    
    def close_position(self, position: dict, exit_price: float, exit_reason: str, 
                      exit_date, current_index: int) -> dict:
        """
        Close a position
        
        Args:
            position: Position dictionary
            exit_price: Exit price
            exit_reason: Reason for exit
            exit_date: Exit date
            current_index: Current bar index
            
        Returns:
            dict: Trade record
        """
        proceeds = exit_price * position['position_size']
        self.cash_available += proceeds
        
        cost = position['entry_price'] * position['position_size']
        pnl = proceeds - cost
        pnl_pct = (exit_price - position['entry_price']) / position['entry_price'] * 100
        
        # Calculate R-multiple
        risk_per_share = position['entry_price'] - position['stop_loss']
        if risk_per_share > 0:
            r_multiple = (exit_price - position['entry_price']) / risk_per_share
        else:
            r_multiple = 0
        
        hold_days = current_index - position['entry_index']
        
        trade_record = {
            'instrument_key': position['instrument_key'],
            'entry_date': position['entry_date'],
            'entry_price': position['entry_price'],
            'exit_date': exit_date,
            'exit_price': exit_price,
            'position_size': position['position_size'],
            'initial_position_size': position['initial_position_size'],
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'r_multiple': r_multiple,
            'exit_reason': exit_reason,
            'hold_days': hold_days,
            'partial_taken': position['partial_taken']
        }
        
        self.closed_trades.append(trade_record)
        
        if position in self.open_positions:
            self.open_positions.remove(position)
        
        return trade_record
    
    def partial_exit(self, position: dict, exit_price: float, exit_date, current_index: int):
        """
        Take partial profit on a position
        
        Args:
            position: Position dictionary
            exit_price: Exit price
            exit_date: Exit date
            current_index: Current bar index
        """
        if position.get('partial_taken', False):
            return
        
        partial_size = int(position['position_size'] * self.config.PARTIAL_EXIT_PERCENT)
        remaining_size = position['position_size'] - partial_size
        
        # Close partial position
        proceeds = exit_price * partial_size
        self.cash_available += proceeds
        
        cost = position['entry_price'] * partial_size
        pnl = proceeds - cost
        pnl_pct = (exit_price - position['entry_price']) / position['entry_price'] * 100
        
        risk_per_share = position['entry_price'] - position['stop_loss']
        if risk_per_share > 0:
            r_multiple = (exit_price - position['entry_price']) / risk_per_share
        else:
            r_multiple = 0
        
        hold_days = current_index - position['entry_index']
        
        trade_record = {
            'instrument_key': position['instrument_key'],
            'entry_date': position['entry_date'],
            'entry_price': position['entry_price'],
            'exit_date': exit_date,
            'exit_price': exit_price,
            'position_size': partial_size,
            'initial_position_size': position['initial_position_size'],
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'r_multiple': r_multiple,
            'exit_reason': 'PARTIAL_2R',
            'hold_days': hold_days,
            'partial_taken': True
        }
        
        self.closed_trades.append(trade_record)
        
        # Update position with remaining shares
        position['position_size'] = remaining_size
        position['partial_taken'] = True
    
    def update_equity(self, current_prices: dict):
        """
        Update account equity with mark-to-market prices
        
        Args:
            current_prices: Dictionary of {instrument_key: current_price}
        """
        self.account_equity = self.cash_available
        
        for position in self.open_positions:
            if position['instrument_key'] in current_prices:
                current_price = current_prices[position['instrument_key']]
                self.account_equity += current_price * position['position_size']
    
    def get_portfolio_summary(self) -> dict:
        """
        Get current portfolio summary
        
        Returns:
            dict: Portfolio summary
        """
        return {
            'account_equity': self.account_equity,
            'cash_available': self.cash_available,
            'num_open_positions': len(self.open_positions),
            'num_closed_trades': len(self.closed_trades),
            'total_return_pct': ((self.account_equity - self.initial_capital) / 
                                self.initial_capital * 100)
        }
