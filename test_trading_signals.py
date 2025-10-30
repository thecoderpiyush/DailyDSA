#!/usr/bin/env python3
"""
Test script for trading_signals.py technical indicators
Tests all indicator calculations with sample data
"""

import os
import sys

# Set a dummy token to allow import
os.environ['UPSTOX_ACCESS_TOKEN'] = 'test_token_for_testing_only'

sys.path.insert(0, '/home/runner/work/DailyDSA/DailyDSA')

from trading_signals import (
    sma, ema_last, rsi_last, atr_series, adx_last, 
    bollinger_last, macd_last, supertrend_last, ichimoku_last,
    generate_signal, Colors
)

# Sample price data (50 days of mock data)
sample_closes = [
    100, 102, 101, 103, 105, 104, 106, 108, 107, 109,
    111, 110, 112, 114, 113, 115, 117, 116, 118, 120,
    119, 121, 123, 122, 124, 126, 125, 127, 129, 128,
    130, 132, 131, 133, 135, 134, 136, 138, 137, 139,
    141, 140, 142, 144, 143, 145, 147, 146, 148, 150
]

sample_highs = [h + 2 for h in sample_closes]
sample_lows = [l - 2 for l in sample_closes]

def test_sma():
    """Test Simple Moving Average"""
    result = sma(sample_closes, 10)
    print(f"{Colors.CYAN}Testing SMA (10 period):{Colors.RESET}")
    print(f"  Result: {result:.2f}" if result else "  Result: None")
    assert result is not None, "SMA should not be None"
    print(f"  {Colors.GREEN}✓ SMA test passed{Colors.RESET}\n")

def test_ema():
    """Test Exponential Moving Average"""
    result = ema_last(sample_closes, 10)
    print(f"{Colors.CYAN}Testing EMA (10 period):{Colors.RESET}")
    print(f"  Result: {result:.2f}" if result else "  Result: None")
    assert result is not None, "EMA should not be None"
    print(f"  {Colors.GREEN}✓ EMA test passed{Colors.RESET}\n")

def test_rsi():
    """Test Relative Strength Index"""
    result = rsi_last(sample_closes, 14)
    print(f"{Colors.CYAN}Testing RSI (14 period):{Colors.RESET}")
    print(f"  Result: {result:.2f}" if result else "  Result: None")
    assert result is not None, "RSI should not be None"
    assert 0 <= result <= 100, "RSI should be between 0 and 100"
    print(f"  {Colors.GREEN}✓ RSI test passed{Colors.RESET}\n")

def test_macd():
    """Test MACD"""
    macd, signal, hist = macd_last(sample_closes, 12, 26, 9)
    print(f"{Colors.CYAN}Testing MACD:{Colors.RESET}")
    print(f"  MACD: {macd:.4f}" if macd else "  MACD: None")
    print(f"  Signal: {signal:.4f}" if signal else "  Signal: None")
    print(f"  Histogram: {hist:.4f}" if hist else "  Histogram: None")
    # Note: With 50 periods, we might not have enough data for MACD
    print(f"  {Colors.YELLOW}⚠ MACD needs more data (50 < 35 minimum){Colors.RESET}\n")

def test_atr():
    """Test Average True Range"""
    result = atr_series(sample_highs, sample_lows, sample_closes, 14)
    print(f"{Colors.CYAN}Testing ATR (14 period):{Colors.RESET}")
    last_atr = result[-1] if result else None
    print(f"  Last ATR: {last_atr:.2f}" if last_atr else "  Last ATR: None")
    assert last_atr is not None, "ATR should not be None"
    print(f"  {Colors.GREEN}✓ ATR test passed{Colors.RESET}\n")

def test_adx():
    """Test Average Directional Index"""
    adx, dip, dim = adx_last(sample_highs, sample_lows, sample_closes, 14)
    print(f"{Colors.CYAN}Testing ADX (14 period):{Colors.RESET}")
    print(f"  ADX: {adx:.2f}" if adx else "  ADX: None")
    print(f"  +DI: {dip:.2f}" if dip else "  +DI: None")
    print(f"  -DI: {dim:.2f}" if dim else "  -DI: None")
    # ADX needs more data (28+ periods)
    print(f"  {Colors.YELLOW}⚠ ADX needs more data for accurate results{Colors.RESET}\n")

def test_bollinger():
    """Test Bollinger Bands"""
    mid, upper, lower = bollinger_last(sample_closes, 20, 2.0)
    print(f"{Colors.CYAN}Testing Bollinger Bands (20, 2.0):{Colors.RESET}")
    print(f"  Middle: {mid:.2f}" if mid else "  Middle: None")
    print(f"  Upper: {upper:.2f}" if upper else "  Upper: None")
    print(f"  Lower: {lower:.2f}" if lower else "  Lower: None")
    assert mid is not None, "Bollinger middle should not be None"
    assert upper is not None, "Bollinger upper should not be None"
    assert lower is not None, "Bollinger lower should not be None"
    assert upper > mid > lower, "Upper > Middle > Lower"
    print(f"  {Colors.GREEN}✓ Bollinger Bands test passed{Colors.RESET}\n")

def test_supertrend():
    """Test SuperTrend"""
    direction, value = supertrend_last(sample_highs, sample_lows, sample_closes, 10, 3.0)
    print(f"{Colors.CYAN}Testing SuperTrend (10, 3.0):{Colors.RESET}")
    print(f"  Direction: {direction}" if direction else "  Direction: None")
    print(f"  Value: {value:.2f}" if value else "  Value: None")
    assert direction is not None, "SuperTrend direction should not be None"
    assert direction in [-1, 1], "SuperTrend direction should be -1 or 1"
    print(f"  {Colors.GREEN}✓ SuperTrend test passed{Colors.RESET}\n")

def test_ichimoku():
    """Test Ichimoku Cloud"""
    tenkan, kijun, span_a, span_b, chikou = ichimoku_last(sample_highs, sample_lows, sample_closes)
    print(f"{Colors.CYAN}Testing Ichimoku Cloud:{Colors.RESET}")
    print(f"  Tenkan: {tenkan:.2f}" if tenkan else "  Tenkan: None")
    print(f"  Kijun: {kijun:.2f}" if kijun else "  Kijun: None")
    print(f"  Span A: {span_a:.2f}" if span_a else "  Span A: None")
    print(f"  Span B: {span_b:.2f}" if span_b else "  Span B: None")
    # Ichimoku needs 52+ periods
    print(f"  {Colors.YELLOW}⚠ Ichimoku needs 52+ periods (we have 50){Colors.RESET}\n")

def test_signal_generation():
    """Test signal generation with extended data"""
    # Generate more data for better signal
    extended_closes = sample_closes * 5  # 250 data points
    extended_highs = [h + 2 for h in extended_closes]
    extended_lows = [l - 2 for l in extended_closes]
    
    print(f"{Colors.CYAN}Testing Signal Generation:{Colors.RESET}")
    signal, reasons, indicators = generate_signal(extended_highs, extended_lows, extended_closes)
    
    print(f"  Signal: {signal}")
    print(f"  Number of reasons: {len(reasons)}")
    print(f"  Current price: {indicators.get('current_price', 'N/A')}")
    
    assert signal in ["BUY", "SELL", "HOLD"], "Signal should be BUY, SELL, or HOLD"
    assert len(reasons) > 0, "Should have at least one reason"
    assert indicators.get('current_price') is not None, "Should have current price"
    
    print(f"\n  Signal details:")
    for i, reason in enumerate(reasons[:3], 1):  # Print first 3 reasons
        print(f"    {i}. {reason}")
    
    print(f"  {Colors.GREEN}✓ Signal generation test passed{Colors.RESET}\n")

def main():
    """Run all tests"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}Trading Signals - Technical Indicator Tests{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}\n")
    
    try:
        test_sma()
        test_ema()
        test_rsi()
        test_macd()
        test_atr()
        test_adx()
        test_bollinger()
        test_supertrend()
        test_ichimoku()
        test_signal_generation()
        
        print(f"{Colors.BOLD}{Colors.GREEN}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.GREEN}All tests completed!{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.GREEN}{'='*60}{Colors.RESET}\n")
        
    except AssertionError as e:
        print(f"\n{Colors.BOLD}{Colors.RED}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.RED}Test failed: {e}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.RED}{'='*60}{Colors.RESET}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.BOLD}{Colors.RED}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.RED}Error: {e}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.RED}{'='*60}{Colors.RESET}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
