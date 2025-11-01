"""
Backtesting Engine Module
Main backtesting loop and orchestration
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime

from config import StrategyConfig
from indicators import calculate_all_indicators
from entry_signals import EntrySignalDetector
from exit_signals import ExitSignalDetector
from position_manager import PositionManager


class BacktestEngine:
    """Main backtesting engine for the RSI Pullback strategy"""
    
    def __init__(self, config=None):
        self.config = config if config else StrategyConfig()
        self.position_manager = None
        self.entry_detector = None
        self.exit_detector = None
        self.daily_equity_curve = []
    
    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare and validate data
        
        Args:
            df: Raw OHLCV DataFrame
            
        Returns:
            Prepared DataFrame with indicators
        """
        # Data quality checks
        if len(df) < 250:
            raise ValueError("Insufficient data: need at least 250 bars")
        
        # Remove invalid rows
        df = df[
            (df['close'] > 0) &
            (df['volume'] >= 0) &
            (df['high'] >= df['low']) &
            (df['high'] >= df['close']) &
            (df['low'] <= df['close'])
        ].copy()
        
        # Sort by date
        if 'timestamp' in df.columns:
            df = df.sort_values('timestamp')
            df = df.set_index('timestamp')
        else:
            df = df.sort_index()
        
        # Calculate indicators
        df = calculate_all_indicators(df, self.config)
        
        return df
    
    def run_backtest(self, data: Dict[str, pd.DataFrame], 
                    start_date=None, end_date=None, 
                    initial_capital: float = 100000) -> tuple:
        """
        Run backtest on provided data
        
        Args:
            data: Dictionary of {instrument_key: DataFrame with OHLCV data}
            start_date: Start date for backtest (optional)
            end_date: End date for backtest (optional)
            initial_capital: Initial portfolio capital
            
        Returns:
            Tuple of (closed_trades, daily_equity_curve)
        """
        # Initialize managers
        self.position_manager = PositionManager(initial_capital, self.config)
        self.entry_detector = EntrySignalDetector(self.config, initial_capital)
        self.exit_detector = ExitSignalDetector(self.config)
        self.daily_equity_curve = []
        
        # Prepare all data
        prepared_data = {}
        for instrument_key, df in data.items():
            try:
                prepared_df = self.prepare_data(df)
                prepared_data[instrument_key] = prepared_df
            except ValueError as e:
                print(f"Skipping {instrument_key}: {e}")
                continue
        
        if not prepared_data:
            raise ValueError("No valid data after preparation")
        
        # Get all unique dates across all instruments
        all_dates = set()
        for df in prepared_data.values():
            all_dates.update(df.index)
        all_dates = sorted(all_dates)
        
        # Filter by date range if provided
        if start_date:
            all_dates = [d for d in all_dates if d >= pd.Timestamp(start_date)]
        if end_date:
            all_dates = [d for d in all_dates if d <= pd.Timestamp(end_date)]
        
        print(f"Running backtest from {all_dates[0]} to {all_dates[-1]}")
        print(f"Number of instruments: {len(prepared_data)}")
        print(f"Initial capital: ₹{initial_capital:,.2f}")
        
        # Main backtest loop
        for current_date in all_dates:
            # Update entry detector with current equity
            self.entry_detector.account_equity = self.position_manager.account_equity
            
            # Get current prices for all positions
            current_prices = {}
            for instrument_key, df in prepared_data.items():
                if current_date in df.index:
                    current_prices[instrument_key] = df.loc[current_date, 'close']
            
            # Update equity (mark-to-market)
            self.position_manager.update_equity(current_prices)
            
            # Record daily equity
            self.daily_equity_curve.append({
                'date': current_date,
                'equity': self.position_manager.account_equity,
                'cash': self.position_manager.cash_available,
                'num_positions': len(self.position_manager.open_positions)
            })
            
            # 1. Check exits for existing positions
            positions_to_close = []
            for position in self.position_manager.open_positions:
                instrument_key = position['instrument_key']
                
                if instrument_key not in prepared_data:
                    continue
                
                df = prepared_data[instrument_key]
                if current_date not in df.index:
                    continue
                
                current_index = df.index.get_loc(current_date)
                
                # Check for partial exit first
                if self.exit_detector.check_partial_exit(df, current_index, position):
                    self.position_manager.partial_exit(
                        position,
                        position['target_2r'],
                        current_date,
                        current_index
                    )
                
                # Check for full exit
                exit_triggered, exit_reason, exit_price = self.exit_detector.check_exits(
                    df, current_index, position
                )
                
                if exit_triggered:
                    positions_to_close.append((position, exit_price, exit_reason, current_date, current_index))
            
            # Close positions that triggered exits
            for position, exit_price, exit_reason, exit_date, current_index in positions_to_close:
                self.position_manager.close_position(
                    position, exit_price, exit_reason, exit_date, current_index
                )
            
            # 2. Scan for new entry signals
            if self.position_manager.can_open_new_position():
                open_instrument_keys = {p['instrument_key'] for p in self.position_manager.open_positions}
                
                for instrument_key, df in prepared_data.items():
                    # Skip if already have position
                    if instrument_key in open_instrument_keys:
                        continue
                    
                    if current_date not in df.index:
                        continue
                    
                    current_index = df.index.get_loc(current_date)
                    
                    # Check entry signal
                    entry_signal, trade_params = self.entry_detector.check_long_entry(
                        df, current_index
                    )
                    
                    if entry_signal:
                        # Open position
                        success = self.position_manager.open_position(
                            instrument_key, trade_params, current_index
                        )
                        
                        if success:
                            print(f"[{current_date.date()}] OPENED: {instrument_key} @ ₹{trade_params['entry_price']:.2f}, "
                                  f"Size: {trade_params['position_size']}, Stop: ₹{trade_params['stop_loss']:.2f}")
                        
                        # Check if max positions reached
                        if not self.position_manager.can_open_new_position():
                            break
        
        # Close any remaining positions at end date
        final_date = all_dates[-1]
        for position in list(self.position_manager.open_positions):
            instrument_key = position['instrument_key']
            if instrument_key in prepared_data:
                df = prepared_data[instrument_key]
                if final_date in df.index:
                    final_price = df.loc[final_date, 'close']
                    current_index = df.index.get_loc(final_date)
                    self.position_manager.close_position(
                        position, final_price, "END_OF_BACKTEST", final_date, current_index
                    )
        
        print(f"\nBacktest completed!")
        print(f"Total trades: {len(self.position_manager.closed_trades)}")
        print(f"Final equity: ₹{self.position_manager.account_equity:,.2f}")
        
        return self.position_manager.closed_trades, self.daily_equity_curve
    
    def get_results(self) -> dict:
        """
        Get backtest results
        
        Returns:
            dict: Results dictionary
        """
        if not self.position_manager:
            return {}
        
        return {
            'closed_trades': self.position_manager.closed_trades,
            'daily_equity_curve': self.daily_equity_curve,
            'portfolio_summary': self.position_manager.get_portfolio_summary()
        }
