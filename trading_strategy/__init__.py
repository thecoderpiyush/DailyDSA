"""
RSI Pullback Trading Strategy Package

A complete implementation of a trend-following RSI pullback strategy
with volume confirmation for swing trading.

Modules:
    - config: Strategy and portfolio configuration
    - indicators: Technical indicator calculations (EMA, RSI, ATR, Volume)
    - entry_signals: Entry signal detection logic
    - exit_signals: Exit signal detection logic
    - position_manager: Position and portfolio management
    - backtest_engine: Main backtesting engine
    - performance_analyzer: Performance metrics and reporting
    - scanner: Live signal scanning

Usage:
    from trading_strategy.backtest_engine import BacktestEngine
    from trading_strategy.config import StrategyConfig
    
    # Initialize and run backtest
    engine = BacktestEngine(StrategyConfig())
    closed_trades, equity_curve = engine.run_backtest(data)
"""

__version__ = "1.0.0"
__author__ = "TheCoderPiyush"

from .config import StrategyConfig, PortfolioConfig
from .backtest_engine import BacktestEngine
from .scanner import LiveScanner
from .performance_analyzer import PerformanceAnalyzer

__all__ = [
    'StrategyConfig',
    'PortfolioConfig',
    'BacktestEngine',
    'LiveScanner',
    'PerformanceAnalyzer',
]
