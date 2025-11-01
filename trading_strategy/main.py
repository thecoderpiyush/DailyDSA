"""
RSI Pullback Trading Strategy - Main Entry Point

This script demonstrates how to use the trading strategy with sample data.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from config import StrategyConfig, PortfolioConfig
from backtest_engine import BacktestEngine
from performance_analyzer import PerformanceAnalyzer
from scanner import LiveScanner


def generate_sample_data(symbol: str, num_days: int = 500, seed: int = None) -> pd.DataFrame:
    """
    Generate synthetic OHLCV data for testing
    
    Args:
        symbol: Stock symbol
        num_days: Number of days to generate
        seed: Random seed for reproducibility
        
    Returns:
        DataFrame with OHLCV data
    """
    if seed is not None:
        np.random.seed(seed)
    
    # Start date
    start_date = datetime.now() - timedelta(days=num_days)
    dates = pd.date_range(start=start_date, periods=num_days, freq='D')
    
    # Generate price data with trend and volatility
    base_price = 100
    trend = np.linspace(0, 20, num_days)  # Upward trend
    volatility = np.random.randn(num_days) * 2
    
    close_prices = base_price + trend + np.cumsum(volatility)
    close_prices = np.maximum(close_prices, 1)  # Ensure positive prices
    
    # Generate OHLC
    high_prices = close_prices * (1 + np.abs(np.random.randn(num_days) * 0.02))
    low_prices = close_prices * (1 - np.abs(np.random.randn(num_days) * 0.02))
    open_prices = close_prices * (1 + np.random.randn(num_days) * 0.01)
    
    # Generate volume
    base_volume = 500000
    volume = base_volume + np.random.randint(-100000, 200000, num_days)
    volume = np.maximum(volume, 10000)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volume
    })
    
    return df


def run_sample_backtest():
    """Run a sample backtest with synthetic data"""
    
    print("=" * 80)
    print("RSI PULLBACK STRATEGY - SAMPLE BACKTEST")
    print("=" * 80)
    
    # Generate sample data for multiple stocks
    print("\nGenerating sample data...")
    stocks = {
        'STOCK_A': generate_sample_data('STOCK_A', 500, seed=42),
        'STOCK_B': generate_sample_data('STOCK_B', 500, seed=43),
        'STOCK_C': generate_sample_data('STOCK_C', 500, seed=44),
        'STOCK_D': generate_sample_data('STOCK_D', 500, seed=45),
        'STOCK_E': generate_sample_data('STOCK_E', 500, seed=46),
    }
    
    print(f"Generated data for {len(stocks)} stocks")
    
    # Initialize strategy
    config = StrategyConfig()
    engine = BacktestEngine(config)
    
    # Run backtest
    print("\nRunning backtest...")
    closed_trades, daily_equity_curve = engine.run_backtest(
        data=stocks,
        initial_capital=PortfolioConfig.INITIAL_CAPITAL
    )
    
    # Analyze performance
    print("\nAnalyzing performance...")
    analyzer = PerformanceAnalyzer(closed_trades, daily_equity_curve)
    analyzer.print_report()
    
    # Print some sample trades
    if closed_trades:
        print("\n" + "=" * 80)
        print("SAMPLE TRADES (First 5)")
        print("=" * 80)
        
        for i, trade in enumerate(closed_trades[:5], 1):
            print(f"\n[{i}] {trade['instrument_key']}")
            print(f"    Entry: {trade['entry_date'].date()} @ ₹{trade['entry_price']:.2f}")
            print(f"    Exit:  {trade['exit_date'].date()} @ ₹{trade['exit_price']:.2f}")
            print(f"    P&L:   ₹{trade['pnl']:,.2f} ({trade['pnl_pct']:.2f}%)")
            print(f"    R-Multiple: {trade['r_multiple']:.2f}R")
            print(f"    Exit Reason: {trade['exit_reason']}")
            print(f"    Hold Days: {trade['hold_days']}")
    
    return engine, analyzer


def run_sample_scanner():
    """Run a sample signal scanner"""
    
    print("\n" + "=" * 80)
    print("RSI PULLBACK STRATEGY - LIVE SCANNER")
    print("=" * 80)
    
    # Generate recent data for scanning
    print("\nGenerating recent data...")
    stocks = {
        'STOCK_A': generate_sample_data('STOCK_A', 300, seed=50),
        'STOCK_B': generate_sample_data('STOCK_B', 300, seed=51),
        'STOCK_C': generate_sample_data('STOCK_C', 300, seed=52),
        'STOCK_D': generate_sample_data('STOCK_D', 300, seed=53),
        'STOCK_E': generate_sample_data('STOCK_E', 300, seed=54),
    }
    
    # Initialize scanner
    config = StrategyConfig()
    scanner = LiveScanner(config, account_equity=100000)
    
    # Scan for signals
    print("\nScanning for entry signals...")
    signals = scanner.scan_for_signals(stocks)
    
    # Print signals
    scanner.print_signals(signals)
    
    return signals


def main():
    """Main entry point"""
    
    print("\n" + "=" * 80)
    print("WELCOME TO RSI PULLBACK TRADING STRATEGY")
    print("=" * 80)
    print("\nThis is a demonstration using synthetic data.")
    print("In production, you would connect to a real data source (database/API).")
    
    # Run backtest
    print("\n\n--- RUNNING BACKTEST ---")
    engine, analyzer = run_sample_backtest()
    
    # Run scanner
    print("\n\n--- RUNNING LIVE SCANNER ---")
    signals = run_sample_scanner()
    
    print("\n" + "=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Connect to your data source (database or market data API)")
    print("2. Implement data loading functions in a separate module")
    print("3. Run backtest on historical data")
    print("4. Optimize parameters using walk-forward analysis")
    print("5. Paper trade for validation")
    print("6. Go live with proper risk management")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
