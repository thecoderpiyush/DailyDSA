# 🚀 DSA Practice Repository

Welcome to **TheCoderPiyush's DSA Practice Repo** 🎯  

This repository contains my solutions to **Data Structures & Algorithms (DSA)** problems from platforms like **LeetCode, GeeksforGeeks, and InterviewBit**.  
The goal is to improve problem-solving skills, write clean and efficient code, and stay consistent with practice.  

---

## 📌 Repository Structure
- `problems/` → All solved problems organized by topic (Arrays, Strings, DP, etc.)
- `notes/` → Topic-wise learning notes, explanations, and approaches
- `README.md` → Project documentation
- `.gitignore` → To avoid committing unnecessary files
- `LICENSE` → Open-source license
- `minervini_strategy.py` → 🚀 **Minervini SEPA Breakout Scanner (RECOMMENDED)**
- `trading_signals.py` → 📊 Legacy multi-indicator analysis tool

---

## 📊 Trading Strategy Tools

This repository includes **professional trading strategy scanners** built in Python!

### 🚀 Minervini SEPA Breakout Strategy (RECOMMENDED)

Based on Mark Minervini's proven method from "Trade Like a Stock Market Wizard"

**Features:**
- 📈 **Strict entry criteria** - ALL conditions must pass for BUY signal
- 🎯 **Clear trade setup** with entry, stop-loss, and profit targets
- 📊 **Relative Strength** analysis vs Nifty 50
- 🔍 **Base breakout detection** with volume confirmation
- ⚡ **Momentum filters** - only stocks ready to move
- 💪 **Trend confirmation** - 50 EMA > 150 EMA

**Strategy Components:**
1. ✅ Price above 50 & 150 EMAs
2. ✅ 50 EMA > 150 EMA (medium-term uptrend)
3. ✅ RS line outperforming Nifty
4. ✅ Base consolidation breakout
5. ✅ Volume ≥ 1.5x average
6. ✅ RSI 55-70 (momentum zone)
7. ✅ Near 52-week high (within 10%)

**Quick Start:**
```bash
# Install dependencies
pip install -r requirements.txt

# Set your API token
export UPSTOX_ACCESS_TOKEN="your_token_here"

# Run Minervini scanner
python3 minervini_strategy.py

# Or run the demo (no API needed)
python3 demo_minervini.py
```

📚 **Full Documentation:** See [MINERVINI_STRATEGY_README.md](MINERVINI_STRATEGY_README.md)

### 📊 Legacy Multi-Indicator Strategy

Previous strategy using 10+ indicators with consensus-based signals. Still available but Minervini SEPA is recommended for better risk/reward.

- File: `trading_signals.py`
- Documentation: [TRADING_SIGNALS_README.md](TRADING_SIGNALS_README.md)

---

## 🛠️ Tech Stack
- **Java (Spring Boot background, DSA in Java for interviews)**
- **Python (ML/extra practice)**

---

## 🎯 Goals
- Solve **500+ problems** before interviews
- Focus on **patterns** (sliding window, recursion, DP, etc.)
- Write **optimized solutions** with explanations

---

## 📖 Problem Categories
- ✅ Arrays
- ✅ Strings
- ✅ Linked List
- ✅ Trees & Graphs
- ✅ Dynamic Programming
- ✅ Greedy & Backtracking

---

## 📌 How to Use
1. Clone the repo  

