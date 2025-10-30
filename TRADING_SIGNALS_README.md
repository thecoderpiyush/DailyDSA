# Trading Signal Analysis Tool

## Overview
This Python script performs comprehensive technical analysis on stocks and generates BUY/SELL/HOLD signals based on multiple technical indicators.

## Features

### Technical Indicators Used:
1. **Moving Averages**
   - Simple Moving Average (SMA) 50 & 200
   - Exponential Moving Average (EMA) 20 & 50
   - Golden Cross / Death Cross detection

2. **Momentum Indicators**
   - RSI (Relative Strength Index) - 14 period
   - MACD (Moving Average Convergence Divergence)
   - ADX (Average Directional Index) with +DI/-DI

3. **Volatility Indicators**
   - Bollinger Bands (20 period, 2 std dev)
   - ATR (Average True Range)

4. **Trend Following**
   - SuperTrend (10 period, 3x multiplier)
   - Ichimoku Cloud (Tenkan, Kijun, Span A/B)

### Signal Generation Logic:
- **BUY Signal**: Generated when ≥65% of indicators show bullish signals
  - Green color output with 📈 icon
  - Detailed reasons for each bullish indicator
  
- **SELL Signal**: Generated when ≥65% of indicators show bearish signals
  - Red color output with 📉 icon
  - Detailed reasons for each bearish indicator
  
- **HOLD Signal**: Generated when signals are mixed or inconclusive
  - Yellow color output with ➡️ icon
  - Shows conflicting indicators

## Requirements

```bash
pip install requests
```

## Configuration

### Environment Variables:

```bash
# Required
export UPSTOX_ACCESS_TOKEN="your_access_token_here"

# Optional
export NIFTY500_CSV="ind_nifty500list.csv"          # Path to CSV with stock list
export UPSTOX_EXCHANGE="NSE_EQ"                      # Exchange prefix
export SERIES_FILTER="EQ"                            # Series filter (comma-separated)
export UPSTOX_LIMIT="5"                              # Limit number of stocks (0 = no limit)
export UPSTOX_SLEEP_PER_CALL="0.4"                   # Sleep between API calls
export UPSTOX_SLEEP_PER_INSTRUMENT="0.6"             # Sleep between instruments

# Alternative: specify instruments directly
export UPSTOX_INSTRUMENT_KEYS="NSE_EQ|INE242A01010,NSE_EQ|INE002A01018"
```

## Usage

### Basic Usage:
```bash
python3 trading_signals.py
```

### With Custom Configuration:
```bash
export UPSTOX_ACCESS_TOKEN="your_token"
export UPSTOX_LIMIT="10"
python3 trading_signals.py
```

## CSV Format

The script expects a CSV file with the following columns:
- Company Name
- Symbol
- Series
- ISIN Code

Example:
```csv
Company Name,Symbol,Series,ISIN Code
Indian Oil Corporation Ltd.,IOC,EQ,INE242A01010
Reliance Industries Ltd.,RELIANCE,EQ,INE002A01018
```

## Output Format

The script outputs colored signals with detailed reasoning:

```
================================================================================
📈 RELIANCE (Reliance Industries Ltd.) - BUY
================================================================================
1. Overall buy strength: 75.0% (9 buy vs 3 sell signals)
2. Price (2456.30) above SMA200 (2234.50) - Long-term uptrend
3. Golden Cross: SMA50 (2398.20) > SMA200 (2234.50)
4. RSI (58.45) above neutral - Bullish bias
5. MACD histogram positive (12.3456) - Bullish momentum
6. Strong trend (ADX=28.50) with +DI (25.30) > -DI (18.20) - Strong buy
7. SuperTrend bullish (value: 2380.50) - Strong uptrend
8. Price above Ichimoku cloud (top: 2350.00) - Bullish
================================================================================
```

## Indicator Calculations

### RSI (Relative Strength Index)
- Period: 14
- Oversold: < 30 (Strong buy signal)
- Overbought: > 70 (Strong sell signal)

### MACD
- Fast: 12, Slow: 26, Signal: 9
- Positive histogram: Bullish
- Negative histogram: Bearish

### ADX (Average Directional Index)
- Period: 14
- Strong trend: ADX ≥ 25
- Weak trend: ADX < 20

### Bollinger Bands
- Period: 20, Multiplier: 2.0
- Price below lower band: Oversold
- Price above upper band: Overbought

### SuperTrend
- Period: 10, Multiplier: 3.0
- Direction: 1 (bullish) or -1 (bearish)

### Ichimoku Cloud
- Tenkan-sen: 9 period
- Kijun-sen: 26 period
- Senkou Span A & B: 52 period
- Price above cloud: Bullish
- Price below cloud: Bearish

## Error Handling

The script includes comprehensive error handling:
- API call failures are logged but don't stop execution
- Insufficient data warnings are displayed in yellow
- Each stock is processed independently

## Color Coding

- 🟢 **Green**: BUY signals
- 🔴 **Red**: SELL signals
- 🟡 **Yellow**: HOLD signals or warnings
- 🔵 **Cyan**: Informational headers

## Notes

- All technical indicators are calculated using pure Python (no external TA libraries)
- The script uses the Upstox API for historical candle data
- Minimum 200 daily bars required for accurate signal generation
- API rate limiting is respected with configurable sleep intervals

## Disclaimer

This tool is for educational and informational purposes only. It should not be considered as financial advice. Always do your own research and consult with a financial advisor before making investment decisions.

## License

This script is part of the DailyDSA repository and follows the same license terms.
