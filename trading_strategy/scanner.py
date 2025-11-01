"""
Live Scanner Module
Scans for current entry signals across stocks
"""

import pandas as pd
from typing import Dict, List

from indicators import calculate_all_indicators
from entry_signals import EntrySignalDetector


class LiveScanner:
    """Scans for current trading signals"""
    
    def __init__(self, config, account_equity: float = 100000):
        self.config = config
        self.entry_detector = EntrySignalDetector(config, account_equity)
    
    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare data with indicators
        
        Args:
            df: Raw OHLCV DataFrame
            
        Returns:
            DataFrame with indicators
        """
        if len(df) < 250:
            return None
        
        # Data quality checks
        df = df[
            (df['close'] > 0) &
            (df['volume'] >= 0) &
            (df['high'] >= df['low']) &
            (df['high'] >= df['close']) &
            (df['low'] <= df['close'])
        ].copy()
        
        if len(df) < 250:
            return None
        
        # Sort by date
        if 'timestamp' in df.columns:
            df = df.sort_values('timestamp')
            df = df.set_index('timestamp')
        else:
            df = df.sort_index()
        
        # Calculate indicators
        df = calculate_all_indicators(df, self.config)
        
        return df
    
    def scan_for_signals(self, data: Dict[str, pd.DataFrame]) -> List[Dict]:
        """
        Scan all stocks for current entry signals
        
        Args:
            data: Dictionary of {instrument_key: DataFrame with OHLCV data}
            
        Returns:
            List of signal dictionaries
        """
        signals = []
        
        for instrument_key, df in data.items():
            # Prepare data
            prepared_df = self.prepare_data(df)
            
            if prepared_df is None:
                continue
            
            # Check entry signal on latest bar
            latest_index = len(prepared_df) - 1
            entry_signal, trade_params = self.entry_detector.check_long_entry(
                prepared_df, latest_index
            )
            
            if entry_signal:
                latest_bar = prepared_df.iloc[latest_index]
                
                signal = {
                    'instrument_key': instrument_key,
                    'date': latest_bar.name if isinstance(latest_bar.name, pd.Timestamp) else latest_bar.get('timestamp'),
                    'entry_price': trade_params['entry_price'],
                    'stop_loss': trade_params['stop_loss'],
                    'target_2r': trade_params['target_2r'],
                    'position_size': trade_params['position_size'],
                    'risk_amount': trade_params['risk_amount'],
                    'risk_per_share': trade_params['risk_per_share'],
                    'rsi': trade_params['rsi'],
                    'atr': trade_params['atr']
                }
                
                signals.append(signal)
        
        return signals
    
    def print_signals(self, signals: List[Dict]):
        """
        Print formatted signal report
        
        Args:
            signals: List of signal dictionaries
        """
        if not signals:
            print("\nNo signals found.")
            return
        
        print("\n" + "=" * 80)
        print(f"CURRENT SIGNALS - {len(signals)} stocks")
        print("=" * 80)
        
        for i, signal in enumerate(signals, 1):
            print(f"\n[{i}] {signal['instrument_key']}")
            print(f"    Date: {signal['date']}")
            print(f"    Entry: ₹{signal['entry_price']:.2f}")
            print(f"    Stop Loss: ₹{signal['stop_loss']:.2f} ({((signal['entry_price'] - signal['stop_loss']) / signal['entry_price'] * 100):.2f}%)")
            print(f"    Target (2R): ₹{signal['target_2r']:.2f} ({((signal['target_2r'] - signal['entry_price']) / signal['entry_price'] * 100):.2f}%)")
            print(f"    Position Size: {signal['position_size']} shares")
            print(f"    Risk Amount: ₹{signal['risk_amount']:.2f}")
            print(f"    RSI: {signal['rsi']:.2f}")
            print(f"    ATR: ₹{signal['atr']:.2f}")
        
        print("\n" + "=" * 80)
