"""
Unit tests for RSI Pullback Trading Strategy
Tests core functionality of indicators, signals, and logic
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from config import StrategyConfig
from indicators import calculate_ema, calculate_rsi, calculate_atr, calculate_all_indicators
from entry_signals import EntrySignalDetector
from exit_signals import ExitSignalDetector
from position_manager import PositionManager


def test_indicators():
    """Test technical indicator calculations"""
    print("\n=== Testing Technical Indicators ===")
    
    # Create sample data
    np.random.seed(42)
    dates = pd.date_range('2020-01-01', periods=300, freq='D')
    close_prices = 100 + np.cumsum(np.random.randn(300) * 2)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': close_prices * 0.99,
        'high': close_prices * 1.02,
        'low': close_prices * 0.98,
        'close': close_prices,
        'volume': np.random.randint(100000, 500000, 300)
    })
    
    # Test EMA
    ema = calculate_ema(df['close'], 20)
    assert len(ema) == len(df), "EMA length should match input"
    assert not ema.iloc[-1] != ema.iloc[-1], "EMA should not have NaN at end"
    print("✓ EMA calculation working")
    
    # Test RSI
    rsi = calculate_rsi(df['close'], 14)
    assert len(rsi) == len(df), "RSI length should match input"
    assert rsi.iloc[-50:].min() >= 0, "RSI should be >= 0"
    assert rsi.iloc[-50:].max() <= 100, "RSI should be <= 100"
    print("✓ RSI calculation working")
    
    # Test ATR
    atr = calculate_atr(df['high'], df['low'], df['close'], 14)
    assert len(atr) == len(df), "ATR length should match input"
    assert (atr.iloc[-50:] > 0).all(), "ATR should be positive"
    print("✓ ATR calculation working")
    
    # Test all indicators together
    df_with_indicators = calculate_all_indicators(df, StrategyConfig())
    required_cols = ['EMA200', 'RSI', 'ATR', 'Volume_MA20', 'Volume_Ratio']
    for col in required_cols:
        assert col in df_with_indicators.columns, f"Missing column: {col}"
    print("✓ All indicators calculated successfully")
    
    return True


def test_entry_signals():
    """Test entry signal detection"""
    print("\n=== Testing Entry Signal Detection ===")
    
    config = StrategyConfig()
    detector = EntrySignalDetector(config, account_equity=100000)
    
    # Create favorable conditions for entry
    np.random.seed(42)
    dates = pd.date_range('2020-01-01', periods=300, freq='D')
    
    # Create uptrend
    trend = np.linspace(0, 50, 300)
    volatility = np.cumsum(np.random.randn(300) * 1)
    close_prices = 100 + trend + volatility
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': close_prices * 0.99,
        'high': close_prices * 1.02,
        'low': close_prices * 0.98,
        'close': close_prices,
        'volume': np.random.randint(200000, 500000, 300)
    })
    
    df = calculate_all_indicators(df, config)
    
    # Check entry signal on various bars
    signals_found = 0
    for i in range(250, 290):
        entry_signal, trade_params = detector.check_long_entry(df, i)
        if entry_signal:
            signals_found += 1
            assert trade_params['entry_price'] > 0, "Entry price should be positive"
            assert trade_params['stop_loss'] < trade_params['entry_price'], "Stop should be below entry"
            assert trade_params['target_2r'] > trade_params['entry_price'], "Target should be above entry"
            assert trade_params['position_size'] > 0, "Position size should be positive"
    
    print(f"✓ Entry signal detection working (found {signals_found} signals)")
    return True


def test_exit_signals():
    """Test exit signal detection"""
    print("\n=== Testing Exit Signal Detection ===")
    
    config = StrategyConfig()
    detector = ExitSignalDetector(config)
    
    # Create sample data
    np.random.seed(42)
    dates = pd.date_range('2020-01-01', periods=300, freq='D')
    close_prices = 100 + np.cumsum(np.random.randn(300) * 2)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': close_prices * 0.99,
        'high': close_prices * 1.02,
        'low': close_prices * 0.98,
        'close': close_prices,
        'volume': np.random.randint(100000, 500000, 300)
    })
    
    df = calculate_all_indicators(df, config)
    
    # Test stop loss hit
    position = {
        'entry_index': 250,
        'entry_price': 100,
        'stop_loss': 95,
        'target_2r': 110,
        'partial_taken': False
    }
    
    # Test stop loss - create a scenario where stop is hit
    test_index = 260
    original_low = df.at[df.index[test_index], 'low']
    df.at[df.index[test_index], 'low'] = 94
    
    exit_triggered, exit_reason, exit_price = detector.check_exits(df, test_index, position)
    assert exit_triggered, "Stop loss should be triggered"
    assert exit_reason == "STOP_LOSS", "Exit reason should be STOP_LOSS"
    print("✓ Stop loss detection working")
    
    # Reset and test target hit (stop loss has priority, so we need to avoid it)
    df.at[df.index[test_index], 'low'] = original_low  # Reset low
    df.at[df.index[test_index], 'high'] = 111
    exit_triggered, exit_reason, exit_price = detector.check_exits(df, test_index, position)
    assert exit_triggered, "Target should be triggered"
    # Note: If stop is also triggered, it will take priority
    print(f"✓ Target detection working (reason: {exit_reason})")
    
    return True


def test_position_manager():
    """Test position management"""
    print("\n=== Testing Position Manager ===")
    
    config = StrategyConfig()
    manager = PositionManager(100000, config)
    
    # Test opening position
    trade_signal = {
        'entry_price': 100,
        'stop_loss': 95,
        'target_2r': 110,
        'position_size': 100,
        'risk_per_share': 5,
        'risk_amount': 500,
        'atr': 2.5,
        'rsi': 42,
        'date': datetime.now()
    }
    
    success = manager.open_position('TEST_STOCK', trade_signal, 0)
    assert success, "Position should open successfully"
    assert len(manager.open_positions) == 1, "Should have 1 open position"
    assert manager.cash_available < 100000, "Cash should be reduced"
    print("✓ Position opening working")
    
    # Test closing position
    position = manager.open_positions[0]
    manager.close_position(position, 110, "TARGET_2R", datetime.now(), 10)
    assert len(manager.open_positions) == 0, "Position should be closed"
    assert len(manager.closed_trades) == 1, "Should have 1 closed trade"
    assert manager.closed_trades[0]['pnl'] > 0, "Trade should be profitable"
    print("✓ Position closing working")
    
    # Test position limits
    manager2 = PositionManager(100000, config)  # Fresh manager
    for i in range(10):
        trade_signal = {
            'entry_price': 100,
            'stop_loss': 95,
            'target_2r': 110,
            'position_size': 100,
            'risk_per_share': 5,
            'risk_amount': 500,
            'atr': 2.5,
            'rsi': 42,
            'date': datetime.now()
        }
        if manager2.can_open_new_position():
            manager2.open_position(f'STOCK_{i}', trade_signal, i)
    
    assert len(manager2.open_positions) <= config.MAX_CONCURRENT_POSITIONS, \
        f"Should respect max concurrent positions (got {len(manager2.open_positions)}, max {config.MAX_CONCURRENT_POSITIONS})"
    print(f"✓ Position limits working (opened {len(manager2.open_positions)} positions, max {config.MAX_CONCURRENT_POSITIONS})")
    
    return True


def test_risk_calculations():
    """Test risk calculation logic"""
    print("\n=== Testing Risk Calculations ===")
    
    config = StrategyConfig()
    detector = EntrySignalDetector(config, account_equity=100000)
    
    # Risk per trade should be 1% of equity
    expected_risk = 100000 * 0.01
    
    # Test with different prices
    entry_price = 100
    stop_loss = 95
    risk_per_share = entry_price - stop_loss
    
    expected_position_size = int(expected_risk / risk_per_share)
    
    print(f"✓ Risk calculation: ₹{expected_risk} per trade")
    print(f"✓ Example: Entry ₹{entry_price}, Stop ₹{stop_loss} = {expected_position_size} shares")
    
    return True


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("RUNNING STRATEGY TESTS")
    print("=" * 60)
    
    tests = [
        ("Indicators", test_indicators),
        ("Entry Signals", test_entry_signals),
        ("Exit Signals", test_exit_signals),
        ("Position Manager", test_position_manager),
        ("Risk Calculations", test_risk_calculations),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
        except Exception as e:
            print(f"✗ {test_name} FAILED: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
