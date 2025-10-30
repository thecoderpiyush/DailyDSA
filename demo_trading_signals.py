#!/usr/bin/env python3
"""
Demo script showing the output format of trading signals
This doesn't require API access - uses mock data
"""

import os
import sys

# Set a dummy token to allow import
os.environ['UPSTOX_ACCESS_TOKEN'] = 'demo_token'

from trading_signals import generate_signal, print_signal, Colors

# Create realistic mock data for 3 scenarios

# Scenario 1: Strong Bullish (Uptrend)
print(f"{Colors.BOLD}{Colors.CYAN}\n{'='*80}")
print("DEMO: Trading Signal Output Examples")
print(f"{'='*80}{Colors.RESET}\n")

print(f"{Colors.BOLD}Scenario 1: Strong Uptrend Stock{Colors.RESET}")
bullish_closes = list(range(100, 350, 1))  # Strong uptrend
bullish_highs = [c + 2 for c in bullish_closes]
bullish_lows = [c - 2 for c in bullish_closes]

signal, reasons, indicators = generate_signal(bullish_highs, bullish_lows, bullish_closes)
print_signal("RELIANCE", "Reliance Industries Ltd.", signal, reasons)

# Scenario 2: Strong Bearish (Downtrend)
print(f"{Colors.BOLD}Scenario 2: Strong Downtrend Stock{Colors.RESET}")
bearish_closes = list(range(350, 100, -1))  # Strong downtrend
bearish_highs = [c + 2 for c in bearish_closes]
bearish_lows = [c - 2 for c in bearish_closes]

signal, reasons, indicators = generate_signal(bearish_highs, bearish_lows, bearish_closes)
print_signal("EXAMPLE", "Example Company Ltd.", signal, reasons)

# Scenario 3: Sideways/Mixed (Consolidation)
print(f"{Colors.BOLD}Scenario 3: Consolidating Stock{Colors.RESET}")
import math
sideways_closes = [200 + 10 * math.sin(i * 0.1) for i in range(250)]  # Sideways
sideways_highs = [c + 3 for c in sideways_closes]
sideways_lows = [c - 3 for c in sideways_closes]

signal, reasons, indicators = generate_signal(sideways_highs, sideways_lows, sideways_closes)
print_signal("NEUTRAL", "Neutral Stock Ltd.", signal, reasons)

print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}")
print("End of Demo")
print(f"{'='*80}{Colors.RESET}\n")

print(f"{Colors.BOLD}Key Features Demonstrated:{Colors.RESET}")
print(f"  {Colors.GREEN}✓ Color-coded signals (GREEN=BUY, RED=SELL, YELLOW=HOLD){Colors.RESET}")
print(f"  {Colors.GREEN}✓ Detailed reasoning for each signal{Colors.RESET}")
print(f"  {Colors.GREEN}✓ Multiple technical indicators analyzed{Colors.RESET}")
print(f"  {Colors.GREEN}✓ Percentage-based confidence scoring{Colors.RESET}")
print(f"  {Colors.GREEN}✓ Professional formatting with icons{Colors.RESET}\n")
