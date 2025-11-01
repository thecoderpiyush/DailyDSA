# RSI Pullback Trading Strategy 📈

A comprehensive Python implementation of a **Trend + RSI Pullback with Volume Confirmation** swing trading strategy.

## Strategy Overview

**Type:** Swing Trading (3 days to 3 months)  
**Universe:** Nifty 500 liquid stocks  
**Timeframe:** Daily bars  

### Core Logic
1. **Trend Filter:** Stock must be above 200-day EMA
2. **RSI Pullback:** RSI dips into 35-45 range (pullback zone)
3. **RSI Recovery:** RSI crosses back above 40 (momentum recovery)
4. **Volume Confirmation:** Volume >= 80% of 20-day average
5. **Entry:** Buy at close when all conditions met

### Exit Rules
- **Stop Loss:** 1.5 × ATR or below 200 EMA (whichever is tighter)
- **Profit Target:** 2R (Risk-Reward ratio of 2:1)
- **Partial Exit:** Take 50% profit at 2R, trail remaining
- **Trailing Stop:** After 5% gain, trail by 1.5 × ATR
- **Time Stop:** Exit after 30 days if gain < 2%
- **Trend Break:** Exit if close below 200 EMA

---

## 📁 Project Structure

```
trading_strategy/
├── __init__.py                 # Package initialization
├── config.py                   # Strategy parameters and configuration
├── indicators.py               # Technical indicators (EMA, RSI, ATR)
├── entry_signals.py            # Entry signal detection
├── exit_signals.py             # Exit signal detection
├── position_manager.py         # Position and portfolio management
├── backtest_engine.py          # Main backtesting engine
├── performance_analyzer.py     # Performance metrics
├── scanner.py                  # Live signal scanner
├── main.py                     # Example usage
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

---

## 🚀 Quick Start

### 1. Installation

```bash
cd trading_strategy
pip install -r requirements.txt
```

### 2. Run Sample Backtest

```bash
python main.py
```

This will run a demonstration using synthetic data.

### 3. Use in Your Code

```python
from trading_strategy import BacktestEngine, StrategyConfig
import pandas as pd

# Prepare your data
data = {
    'RELIANCE': pd.DataFrame({...}),  # OHLCV data
    'TCS': pd.DataFrame({...}),
    # ... more stocks
}

# Run backtest
config = StrategyConfig()
engine = BacktestEngine(config)
closed_trades, equity_curve = engine.run_backtest(
    data=data,
    initial_capital=100000
)

# Analyze results
from trading_strategy import PerformanceAnalyzer
analyzer = PerformanceAnalyzer(closed_trades, equity_curve)
analyzer.print_report()
```

---

## 📊 Data Requirements

Your data should be a Pandas DataFrame with these columns:

- `timestamp` or index: Trading dates
- `open`: Opening price
- `high`: High price
- `low`: Low price
- `close`: Closing price
- `volume`: Trading volume

**Example:**

```python
import pandas as pd

df = pd.DataFrame({
    'timestamp': pd.date_range('2020-01-01', periods=500),
    'open': [...],
    'high': [...],
    'low': [...],
    'close': [...],
    'volume': [...]
})
```

---

## ⚙️ Configuration

### Key Parameters (in `config.py`)

#### Indicator Parameters
```python
EMA_PERIOD = 200           # Trend filter
RSI_PERIOD = 14            # RSI calculation
ATR_PERIOD = 14            # Volatility measure
VOLUME_MA_PERIOD = 20      # Volume average
```

#### Entry Thresholds
```python
RSI_PULLBACK_LOWER = 35    # Lower bound of pullback zone
RSI_PULLBACK_UPPER = 45    # Upper bound of pullback zone
RSI_RECOVERY_THRESHOLD = 40  # Recovery signal
VOLUME_MULTIPLIER = 0.8    # Min 80% of avg volume
```

#### Risk Management
```python
RISK_PER_TRADE = 0.01      # 1% portfolio risk per trade
ATR_STOP_MULTIPLIER = 1.5  # Stop loss distance
PROFIT_TAKE_RATIO = 2.0    # 2:1 reward-to-risk
PARTIAL_EXIT_PERCENT = 0.5 # Take 50% at target
```

#### Position Limits
```python
MAX_CONCURRENT_POSITIONS = 5        # Max open positions
MAX_POSITION_SIZE_OF_ADV = 0.02    # Max 2% of avg volume
```

### Customizing Parameters

```python
from trading_strategy.config import StrategyConfig

config = StrategyConfig()
config.RSI_PULLBACK_LOWER = 30
config.RSI_PULLBACK_UPPER = 40
config.MAX_CONCURRENT_POSITIONS = 10

engine = BacktestEngine(config)
```

---

## 📈 Performance Metrics

The strategy calculates comprehensive metrics:

### Basic Metrics
- Total trades
- Win rate
- Total P&L
- Average win/loss
- Profit factor
- Average R-multiple

### Risk Metrics
- CAGR (Compound Annual Growth Rate)
- Maximum drawdown
- Sharpe ratio
- Sortino ratio
- Calmar ratio

### Trade Statistics
- Average holding period
- Maximum consecutive wins/losses
- Exit reason breakdown

---

## 🔍 Live Scanner

Scan for current signals across your universe:

```python
from trading_strategy import LiveScanner, StrategyConfig

scanner = LiveScanner(StrategyConfig(), account_equity=100000)
signals = scanner.scan_for_signals(data)
scanner.print_signals(signals)
```

Output includes:
- Entry price
- Stop loss level
- Target price (2R)
- Position size
- Risk amount
- Current RSI
- ATR

---

## 🛠️ Advanced Usage

### Walk-Forward Optimization

```python
# Split data into training and testing periods
train_data = {...}  # 2018-2021
test_data = {...}   # 2022-2024

# Optimize on training data
# ... parameter optimization code ...

# Validate on test data
engine = BacktestEngine(optimized_config)
results = engine.run_backtest(test_data)
```

### Monte Carlo Simulation

```python
# Run multiple simulations with randomized trade sequences
# ... Monte Carlo code ...
```

### Portfolio-Level Analysis

```python
# Analyze correlations, sector exposure, etc.
# ... portfolio analysis code ...
```

---

## 📋 Pre-Live Checklist

Before live trading:

- [ ] Backtest on 5+ years of data
- [ ] Test on bull, bear, and sideways markets
- [ ] Walk-forward optimization
- [ ] Out-of-sample validation
- [ ] Monte Carlo simulation (1000+ runs)
- [ ] Parameter sensitivity analysis
- [ ] Transaction cost impact (0.1%-0.3%)
- [ ] Slippage simulation (0.1%-0.5%)
- [ ] Paper trade for 3+ months
- [ ] Verify Sharpe ratio > 1.0
- [ ] Verify profit factor > 1.5
- [ ] Verify win rate > 45%
- [ ] Check max drawdown tolerance

---

## 🔌 Integrating with Data Sources

### Database (PostgreSQL/MySQL)

```python
import psycopg2
import pandas as pd

def load_data_from_db(instrument_key):
    conn = psycopg2.connect(...)
    query = """
        SELECT timestamp, open, high, low, close, volume
        FROM candles
        WHERE instrument_key = %s
        ORDER BY timestamp
    """
    df = pd.read_sql(query, conn, params=[instrument_key])
    return df
```

### Market Data API (Yahoo Finance)

```python
import yfinance as yf

def load_data_from_yahoo(symbol, start_date, end_date):
    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start_date, end=end_date)
    df = df.reset_index()
    df.columns = [c.lower() for c in df.columns]
    return df[['date', 'open', 'high', 'low', 'close', 'volume']]
```

---

## 📝 Notes

1. **Data Quality:** Ensure OHLCV data is adjusted for splits/dividends
2. **Execution:** Assumes fills at close price (add slippage in production)
3. **Commissions:** Include realistic brokerage in final implementation
4. **Slippage:** Add 0.1-0.3% slippage for market orders
5. **Liquidity:** Strategy rejects signals if position > 2% of ADV

---

## 🎯 Performance Expectations

Based on the strategy design, expected metrics (on well-designed strategies):

- **Win Rate:** 45-55%
- **Profit Factor:** 1.5-2.5
- **Sharpe Ratio:** 1.0-2.0
- **Max Drawdown:** 15-25%
- **CAGR:** 12-25% (market dependent)

**Note:** Past performance does not guarantee future results.

---

## 🤝 Contributing

This is a complete implementation of the strategy pseudocode. Feel free to:
- Optimize parameters
- Add new features
- Improve performance
- Report bugs

---

## 📄 License

This implementation is part of the DailyDSA repository.

---

## ⚠️ Disclaimer

**This code is for educational and research purposes only.**

Trading stocks carries risk. This strategy:
- Has NOT been tested on real market data
- May not perform as expected in live markets
- Should be thoroughly validated before use
- Requires proper risk management

**Never trade with money you cannot afford to lose.**

---

## 📞 Support

For questions or issues, please create an issue in the repository.

---

**Built with ❤️ by TheCoderPiyush**
