#!/usr/bin/env python3
"""
Unit tests for upstox_swing_signals_improved.py

Tests critical indicator calculations with known inputs/outputs.
Run with: python -m pytest test_upstox_indicators.py -v
or: python test_upstox_indicators.py
"""
import sys
import os
import math
from typing import List

# Set dummy token for testing (configuration validation requires it)
os.environ.setdefault("UPSTOX_ACCESS_TOKEN", "dummy_token_for_testing")

# Import functions to test (assuming they're in the same directory)
try:
    from upstox_swing_signals_improved import (
        sma, ema_last_optimized, rsi_last, atr_last, 
        stddev, bollinger_last_two, true_range
    )
except ImportError:
    print("Error: Could not import from upstox_swing_signals_improved.py")
    print("Make sure the file is in the same directory.")
    sys.exit(1)

# Test framework (simple, no external dependencies)
class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def assert_equal(self, actual, expected, msg=""):
        if actual == expected:
            self.passed += 1
            print(f"  ✓ {msg}")
        else:
            self.failed += 1
            print(f"  ✗ {msg}")
            print(f"    Expected: {expected}")
            print(f"    Got: {actual}")
    
    def assert_almost_equal(self, actual, expected, tolerance=1e-6, msg=""):
        if actual is None and expected is None:
            self.passed += 1
            print(f"  ✓ {msg}")
        elif actual is None or expected is None:
            self.failed += 1
            print(f"  ✗ {msg}")
            print(f"    Expected: {expected}")
            print(f"    Got: {actual}")
        elif abs(actual - expected) < tolerance:
            self.passed += 1
            print(f"  ✓ {msg}")
        else:
            self.failed += 1
            print(f"  ✗ {msg}")
            print(f"    Expected: {expected}")
            print(f"    Got: {actual}")
            print(f"    Difference: {abs(actual - expected)}")
    
    def assert_none(self, actual, msg=""):
        if actual is None:
            self.passed += 1
            print(f"  ✓ {msg}")
        else:
            self.failed += 1
            print(f"  ✗ {msg}")
            print(f"    Expected: None")
            print(f"    Got: {actual}")
    
    def summary(self):
        total = self.passed + self.failed
        print("\n" + "=" * 60)
        print(f"Test Results: {self.passed}/{total} passed")
        if self.failed > 0:
            print(f"FAILED: {self.failed} tests failed")
            return False
        else:
            print("SUCCESS: All tests passed!")
            return True

runner = TestRunner()

# Test SMA
def test_sma():
    print("\n### Testing SMA (Simple Moving Average) ###")
    
    # Basic test
    data = [1.0, 2.0, 3.0, 4.0, 5.0]
    result = sma(data, 3)
    runner.assert_almost_equal(result, 4.0, msg="SMA([1,2,3,4,5], 3) = 4.0")
    
    # Full series
    result = sma(data, 5)
    runner.assert_almost_equal(result, 3.0, msg="SMA([1,2,3,4,5], 5) = 3.0")
    
    # Insufficient data
    result = sma(data, 10)
    runner.assert_none(result, msg="SMA with insufficient data returns None")
    
    # Single value
    result = sma([5.0], 1)
    runner.assert_almost_equal(result, 5.0, msg="SMA([5.0], 1) = 5.0")

# Test EMA
def test_ema():
    print("\n### Testing EMA (Exponential Moving Average) ###")
    
    # Simple test
    data = [1.0, 2.0, 3.0, 4.0, 5.0]
    result = ema_last_optimized(data, 3)
    # EMA(3) with k=2/(3+1)=0.5
    # Start: SMA(1,2,3) = 2.0
    # EMA[3] = (4-2)*0.5 + 2 = 3.0
    # EMA[4] = (5-3)*0.5 + 3 = 4.0
    runner.assert_almost_equal(result, 4.0, msg="EMA([1,2,3,4,5], 3)")
    
    # Insufficient data
    result = ema_last_optimized(data, 10)
    runner.assert_none(result, msg="EMA with insufficient data returns None")
    
    # Test with real-world-like data
    prices = [100.0, 102.0, 101.0, 103.0, 105.0, 104.0, 106.0, 108.0]
    result = ema_last_optimized(prices, 5)
    # Should be close to recent prices due to exponential weighting
    runner.assert_equal(result is not None and result > 100, True, msg="EMA result is reasonable")

# Test RSI
def test_rsi():
    print("\n### Testing RSI (Relative Strength Index) ###")
    
    # All gains -> RSI = 100
    all_gains = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0, 111.0, 112.0, 113.0, 114.0]
    result = rsi_last(all_gains, 14)
    runner.assert_almost_equal(result, 100.0, msg="RSI with all gains = 100.0")
    
    # All losses -> RSI = 0 (avg_loss > 0, avg_gain = 0)
    all_losses = [100.0, 99.0, 98.0, 97.0, 96.0, 95.0, 94.0, 93.0, 92.0, 91.0, 90.0, 89.0, 88.0, 87.0, 86.0]
    result = rsi_last(all_losses, 14)
    runner.assert_almost_equal(result, 0.0, tolerance=0.1, msg="RSI with all losses ≈ 0.0")
    
    # Neutral (equal gains and losses)
    neutral = [100.0, 101.0, 100.0, 101.0, 100.0, 101.0, 100.0, 101.0, 100.0, 101.0, 100.0, 101.0, 100.0, 101.0, 100.0]
    result = rsi_last(neutral, 14)
    runner.assert_almost_equal(result, 50.0, tolerance=5.0, msg="RSI with neutral = ~50.0")
    
    # Insufficient data
    result = rsi_last([100.0, 101.0], 14)
    runner.assert_none(result, msg="RSI with insufficient data returns None")

# Test True Range
def test_true_range():
    print("\n### Testing True Range ###")
    
    # Case 1: H-L is max
    tr = true_range(105.0, 100.0, 102.0)
    runner.assert_almost_equal(tr, 5.0, msg="TR where H-L is maximum")
    
    # Case 2: |H-PC| is max (gap up)
    tr = true_range(110.0, 108.0, 100.0)
    runner.assert_almost_equal(tr, 10.0, msg="TR where |H-PC| is maximum (gap up)")
    
    # Case 3: |L-PC| is max (gap down)
    tr = true_range(102.0, 95.0, 105.0)
    runner.assert_almost_equal(tr, 10.0, msg="TR where |L-PC| is maximum (gap down)")

# Test ATR
def test_atr():
    print("\n### Testing ATR (Average True Range) ###")
    
    # Simple test with consistent range
    highs = [105.0, 106.0, 107.0, 108.0, 109.0, 110.0, 111.0, 112.0, 113.0, 114.0, 115.0, 116.0, 117.0, 118.0, 119.0]
    lows = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0, 111.0, 112.0, 113.0, 114.0]
    closes = [103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0, 111.0, 112.0, 113.0, 114.0, 115.0, 116.0, 117.0]
    result = atr_last(highs, lows, closes, 14)
    # TR is consistently 5.0, so ATR should be ~5.0
    runner.assert_almost_equal(result, 5.0, tolerance=0.5, msg="ATR with consistent range")
    
    # Insufficient data
    result = atr_last([105.0], [100.0], [103.0], 14)
    runner.assert_none(result, msg="ATR with insufficient data returns None")

# Test Standard Deviation
def test_stddev():
    print("\n### Testing Standard Deviation ###")
    
    # Simple test
    data = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
    result = stddev(data)
    # Mean = 5.0, variance = 4.0, stddev = 2.0
    runner.assert_almost_equal(result, 2.0, msg="StdDev of [2,4,4,4,5,5,7,9] = 2.0")
    
    # All same values -> stddev = 0
    result = stddev([5.0, 5.0, 5.0, 5.0])
    runner.assert_almost_equal(result, 0.0, msg="StdDev of constant values = 0.0")
    
    # Empty list
    result = stddev([])
    runner.assert_almost_equal(result, 0.0, msg="StdDev of empty list = 0.0")

# Test Bollinger Bands (last two)
def test_bollinger():
    print("\n### Testing Bollinger Bands ###")
    
    # Create data with 25 points (need 21+ for last two BB calculations)
    closes = [100.0] * 25
    for i in range(5):
        closes[20 + i] = 100.0 + i  # Add some variation at the end
    
    (curr_mid, curr_up, curr_lo), (prev_mid, prev_up, prev_lo) = bollinger_last_two(closes, 20, 2.0)
    
    # Current midline should be around 101.0 (average of last 20)
    runner.assert_equal(curr_mid is not None, True, msg="Current BB mid is calculated")
    runner.assert_equal(curr_up is not None, True, msg="Current BB upper is calculated")
    runner.assert_equal(curr_lo is not None, True, msg="Current BB lower is calculated")
    
    # Previous should also be calculated
    runner.assert_equal(prev_mid is not None, True, msg="Previous BB mid is calculated")
    runner.assert_equal(prev_up is not None, True, msg="Previous BB upper is calculated")
    runner.assert_equal(prev_lo is not None, True, msg="Previous BB lower is calculated")
    
    # Upper should be > mid > lower
    if all(x is not None for x in (curr_mid, curr_up, curr_lo)):
        runner.assert_equal(curr_up > curr_mid > curr_lo, True, msg="BB bands are ordered correctly")
    
    # Insufficient data
    (curr_mid, _, _), (prev_mid, _, _) = bollinger_last_two([100.0] * 10, 20, 2.0)
    runner.assert_none(curr_mid, msg="BB with insufficient data returns None")

# Test edge cases
def test_edge_cases():
    print("\n### Testing Edge Cases ###")
    
    # Empty lists
    result = sma([], 5)
    runner.assert_none(result, msg="SMA of empty list returns None")
    
    result = ema_last_optimized([], 5)
    runner.assert_none(result, msg="EMA of empty list returns None")
    
    result = rsi_last([], 14)
    runner.assert_none(result, msg="RSI of empty list returns None")
    
    # Period = 0
    result = sma([1.0, 2.0, 3.0], 0)
    runner.assert_none(result, msg="SMA with period=0 returns None")
    
    result = ema_last_optimized([1.0, 2.0, 3.0], 0)
    runner.assert_none(result, msg="EMA with period=0 returns None")
    
    # Negative period
    result = sma([1.0, 2.0, 3.0], -5)
    runner.assert_none(result, msg="SMA with negative period returns None")

# Run all tests
if __name__ == "__main__":
    print("=" * 60)
    print("RUNNING UNIT TESTS FOR UPSTOX INDICATORS")
    print("=" * 60)
    
    test_sma()
    test_ema()
    test_rsi()
    test_true_range()
    test_atr()
    test_stddev()
    test_bollinger()
    test_edge_cases()
    
    # Summary
    success = runner.summary()
    sys.exit(0 if success else 1)
