# Minervini SEPA Breakout Strategy - Documentation

## 🎯 Strategy Overview

This implementation is based on **Mark Minervini's SEPA (Specific Entry Point Analysis)** method from his book *"Trade Like a Stock Market Wizard"*. Minervini was the U.S. Investing Champion in 1997 and is known for identifying strong trend continuation setups right before major breakouts.

### Core Philosophy
> "Buy stocks that are already strong, moving higher, and breaking out of well-defined bases with strong volume."

This is a **momentum + trend continuation** strategy, **NOT a reversal strategy**. We don't try to catch falling knives or bottom-fish.

## 📊 Strategy Components

### 1️⃣ Trend Filter (Strength Check)
- **Price must be above both 50-day EMA and 150-day EMA**
- **50 EMA > 150 EMA** → Confirms medium-term uptrend
- This ensures we're only looking at stocks in established uptrends

### 2️⃣ Relative Strength (RS Line)
- **Stock must outperform Nifty 50**
- RS = Stock Close / Nifty Close
- **RS line must be in uptrend**
- Stocks that outperform the index tend to continue outperforming

### 3️⃣ Base Formation (Consolidation Pattern)
- Look for **3–6 weeks (21-42 days) of consolidation** after uptrend
- Stock forms **higher lows or tight range** (low volatility)
- Price range should be **< 15%** during base formation
- This is the "coiling" before the breakout

### 4️⃣ Volume Confirmation
- **Breakout volume must be ≥ 1.5x the 20-day average**
- Strong volume confirms institutional interest
- Weak volume breakouts often fail

### 5️⃣ Momentum Confirmation (RSI)
- **RSI should be between 55-70**
- Below 55: Momentum not strong enough
- Above 70: Overbought, higher risk of pullback

### 6️⃣ Near 52-Week High
- **Stock should be within 10% of 52-week high**
- Leaders make new highs, laggards don't

## 🟢 BUY Entry Conditions

**ALL of the following must be true:**

1. ✅ Price > 50 EMA AND Price > 150 EMA
2. ✅ 50 EMA > 150 EMA (medium-term uptrend)
3. ✅ RS line in uptrend (outperforming Nifty)
4. ✅ Price breaks above base resistance
5. ✅ Volume ≥ 1.5x 20-day average
6. ✅ RSI between 55-70 (ideally)
7. ✅ Near 52-week high (within 10%)

### Entry Trigger
**Buy when price breaks above base resistance with strong volume and all conditions pass.**

## 🔴 Stop Loss & Exit Strategy

### Stop Loss
- **Primary Stop:** Below breakout level (base resistance)
- **Alternative:** Below 10-day EMA for tighter stops
- **Risk:** Entry - Stop Loss

### Take Profit Targets
- **Target 1:** Entry + (2 × Risk) → 2:1 R/R ratio
- **Target 2:** Entry + (3 × Risk) → 3:1 R/R ratio

### Exit Early If:
- Price drops back below breakout level
- RS line weakens (stock underperforming Nifty)
- Stock becomes extended >15% above 50 EMA

## 📈 Example Trade Setup

**Stock:** Tata Motors

**Entry Conditions:**
- 50 EMA = ₹910
- 150 EMA = ₹850
- Price consolidates ₹980–₹1020 for 4 weeks
- Nifty flat but Tata Motors RS rising
- Breaks ₹1020 with 2x average volume
- RSI = 62

**Trade Setup:**
- ✅ **Entry:** ₹1025
- 🛑 **Stop Loss:** ₹995 (Risk: ₹30)
- 🎯 **Target 1:** ₹1085 (R:R = 2:1)
- 🎯 **Target 2:** ₹1115 (R:R = 3:1)

## 🧮 Risk Management

### Position Sizing
```
Risk per trade = 1% of total capital
Position Size = (1% of Capital) / (Entry - Stop Loss)
```

**Example:**
- Capital: ₹10,00,000
- Risk per trade: ₹10,000 (1%)
- Entry: ₹1025
- Stop: ₹995
- Risk per share: ₹30
- **Position Size:** ₹10,000 / ₹30 = 333 shares

## 🚦 Signal Types

### 🚀 BUY (Green)
All SEPA conditions met with strong volume. Ready for immediate entry.

### 👀 WATCH (Yellow)
All trend conditions met but volume weak (<1.5x). Wait for volume confirmation.

### ⏸️ HOLD (Blue)
One or more conditions not met. Stock not ready for entry.

## 📁 Files

### Main Script
- `minervini_strategy.py` - Production scanner

### Demo/Testing
- `demo_minervini.py` - Demo with mock data (no API needed)

## 🚀 Usage

### Basic Scan
```bash
export UPSTOX_ACCESS_TOKEN="your_token"
python3 minervini_strategy.py
```

### With Custom Settings
```bash
export UPSTOX_ACCESS_TOKEN="your_token"
export UPSTOX_LIMIT="50"              # Scan 50 stocks
export NIFTY_INSTRUMENT="NSE_INDEX|Nifty 50"
python3 minervini_strategy.py
```

### Demo (No API Required)
```bash
python3 demo_minervini.py
```

## 📊 Output Format

```
================================================================================
🚀 RELIANCE (Reliance Industries Ltd.) - BUY
================================================================================
🚀 STRONG BUY - Minervini SEPA Breakout Confirmed
✅ Price (₹2,450.00) > EMA50 (₹2,380.00) and EMA150 (₹2,250.00)
✅ EMA50 (₹2,380.00) > EMA150 (₹2,250.00) - Medium-term uptrend confirmed
✅ RS line in uptrend (RS: 0.1345) - Outperforming Nifty
✅ BREAKOUT! Price (₹2,450.00) > Base Resistance (₹2,420.00)
✅ Strong volume: 1.85x average (1,850,000 vs avg 1,000,000)
✅ RSI (62.45) in momentum zone (55-70)
✅ Near 52-week high: ₹2,480.00 (1.2% away)

📊 Trade Setup:
   Entry: ₹2,450.00
   Stop Loss: ₹2,420.00 (Risk: ₹30.00)
   Target 1: ₹2,510.00 (R:R = 2:1)
   Target 2: ₹2,540.00 (R:R = 3:1)
================================================================================
```

## ⚡ Key Differences from Previous Strategy

| Aspect | Previous (Multi-Indicator) | New (Minervini SEPA) |
|--------|---------------------------|----------------------|
| Philosophy | Mixed signals consensus | Trend continuation only |
| Entry | 65% indicator agreement | ALL conditions must pass |
| False Signals | Higher (conflicting indicators) | Lower (strict criteria) |
| Risk/Reward | Not defined | Clear R:R ratios provided |
| Volume | Not emphasized | Critical requirement |
| Relative Strength | Not used | Core component |
| Base Detection | Not used | Required for entry |
| Stop Loss | Not provided | Clear levels given |

## 📚 Learning Resources

- **Book:** "Trade Like a Stock Market Wizard" by Mark Minervini
- **Key Concept:** SEPA (Specific Entry Point Analysis)
- **Strategy Type:** Trend following + Momentum

## ⚠️ Important Notes

1. **Not a Holy Grail:** No strategy wins 100% of the time
2. **Risk Management:** Always use stop losses
3. **Position Sizing:** Never risk more than 1-2% per trade
4. **Market Conditions:** Works best in bull markets or strong sectors
5. **Patience Required:** Few stocks pass all criteria at any given time
6. **Exit Discipline:** Follow your stop loss rules

## 🔒 Disclaimer

This tool is for educational purposes only. It is not financial advice. Past performance does not guarantee future results. Always do your own research and consult with a licensed financial advisor before making investment decisions.

## 🤝 Credits

Strategy developed by Mark Minervini.
Implementation adapted for NSE (National Stock Exchange of India) by @copilot for @thecoderpiyush.
