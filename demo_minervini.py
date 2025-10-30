#!/usr/bin/env python3
"""
Demo script for Minervini SEPA Breakout Strategy
Shows example output without requiring API access
"""

import os
import sys

# Set dummy token for demo
os.environ['UPSTOX_ACCESS_TOKEN'] = 'DEMO_MODE_NO_API_REQUIRED'

from minervini_strategy import minervini_sepa_scan, print_signal, Colors

print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}")
print(f"{Colors.BOLD}{Colors.CYAN}Minervini SEPA Strategy - Demo Scenarios{Colors.RESET}")
print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}\n")

# Scenario 1: Perfect SEPA Breakout - Strong BUY
print(f"{Colors.BOLD}Scenario 1: Perfect SEPA Breakout (Strong Uptrend + Breakout){Colors.RESET}\n")

# Create data for a stock in perfect SEPA setup
# Need 200+ days: initial build, base formation, breakout
initial_build = list(range(100, 180, 1))  # 80 days uptrend
steady_trend = [180 + i * 0.5 for i in range(70)]  # 70 days steady
base_prices = [195 + (i % 10) * 0.5 for i in range(42)]  # 42 days consolidation (6 weeks)
breakout_prices = initial_build + steady_trend + base_prices + [210, 215, 220]  # Breakout!

highs = [p + 2 for p in breakout_prices]
lows = [p - 2 for p in breakout_prices]
closes = breakout_prices
volumes = [100000] * len(closes)
volumes[-1] = 180000  # Strong volume on breakout (1.8x)

# Nifty data (flat to show outperformance)
nifty_closes = [18000 + i * 1 for i in range(len(closes))]

signal, reasons, indicators = minervini_sepa_scan(highs, lows, closes, volumes, nifty_closes)
print_signal("RELIANCE", "Reliance Industries Ltd.", signal, reasons)

# Scenario 2: Weak Volume Breakout - WATCH
print(f"\n{Colors.BOLD}Scenario 2: Breakout with Weak Volume{Colors.RESET}\n")

signal2, reasons2, indicators2 = minervini_sepa_scan(
    highs, lows, closes,
    [100000] * len(closes),  # Normal volume, no spike
    nifty_closes
)
print_signal("TCS", "Tata Consultancy Services", signal2, reasons2)

# Scenario 3: No Breakout - HOLD
print(f"\n{Colors.BOLD}Scenario 3: In Consolidation (No Breakout Yet){Colors.RESET}\n")

# Stock still in base, not broken out
initial_build3 = list(range(100, 180, 1))
steady_trend3 = [180 + i * 0.5 for i in range(70)]
consolidation_prices = [195, 196, 197, 198, 199, 197, 196, 198, 199, 198]  # Still in base
consolidation_closes = initial_build3 + steady_trend3 + consolidation_prices
consolidation_highs = [p + 2 for p in consolidation_closes]
consolidation_lows = [p - 2 for p in consolidation_closes]
volumes3 = [100000] * len(consolidation_closes)

signal3, reasons3, indicators3 = minervini_sepa_scan(
    consolidation_highs, consolidation_lows, consolidation_closes,
    volumes3, nifty_closes[:len(consolidation_closes)]
)
print_signal("INFY", "Infosys Ltd.", signal3, reasons3)

# Scenario 4: Downtrend - HOLD
print(f"\n{Colors.BOLD}Scenario 4: Downtrend (Failed EMA Check){Colors.RESET}\n")

# Build up first, then downtrend
buildup4 = list(range(100, 200, 1))
downtrend_prices = list(range(200, 150, -1)) + [155, 160, 158, 156, 154]
downtrend_closes = buildup4 + downtrend_prices
downtrend_highs = [p + 2 for p in downtrend_closes]
downtrend_lows = [p - 2 for p in downtrend_closes]
volumes4 = [100000] * len(downtrend_closes)

signal4, reasons4, indicators4 = minervini_sepa_scan(
    downtrend_highs, downtrend_lows, downtrend_closes,
    volumes4, nifty_closes[:len(downtrend_closes)]
)
print_signal("EXAMPLE", "Example Downtrend Stock", signal4, reasons4)

print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}")
print(f"{Colors.BOLD}{Colors.CYAN}Key Differences from Previous Strategy:{Colors.RESET}")
print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}")
print(f"{Colors.GREEN}✓ Based on Mark Minervini's proven SEPA method{Colors.RESET}")
print(f"{Colors.GREEN}✓ Focuses on trend + momentum + breakout{Colors.RESET}")
print(f"{Colors.GREEN}✓ Requires ALL conditions to pass for BUY{Colors.RESET}")
print(f"{Colors.GREEN}✓ Includes relative strength vs Nifty{Colors.RESET}")
print(f"{Colors.GREEN}✓ Detects base consolidation patterns{Colors.RESET}")
print(f"{Colors.GREEN}✓ Volume confirmation required{Colors.RESET}")
print(f"{Colors.GREEN}✓ Provides clear entry, stop-loss, and targets{Colors.RESET}")
print(f"{Colors.GREEN}✓ Only signals stocks ready for immediate action{Colors.RESET}\n")

print(f"{Colors.BOLD}{Colors.YELLOW}Strategy Philosophy:{Colors.RESET}")
print(f"{Colors.YELLOW}Buy stocks that are ALREADY strong, moving higher,{Colors.RESET}")
print(f"{Colors.YELLOW}and breaking out with strong volume.{Colors.RESET}")
print(f"{Colors.YELLOW}Not catching falling knives or reversals.{Colors.RESET}\n")
