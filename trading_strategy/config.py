"""
Configuration file for RSI Pullback Trading Strategy
Contains all strategy parameters and settings
"""


class StrategyConfig:
    """Strategy parameters for RSI Pullback with Volume Confirmation"""
    
    # Indicator Parameters
    EMA_PERIOD = 200
    RSI_PERIOD = 14
    VOLUME_MA_PERIOD = 20
    ATR_PERIOD = 14
    
    # Entry Thresholds
    RSI_PULLBACK_LOWER = 35
    RSI_PULLBACK_UPPER = 45
    RSI_RECOVERY_THRESHOLD = 40
    VOLUME_MULTIPLIER = 0.8  # Min 80% of avg volume
    
    # Risk Management
    RISK_PER_TRADE = 0.01  # 1% of portfolio
    ATR_STOP_MULTIPLIER = 1.5
    PROFIT_TAKE_RATIO = 2.0  # 2R
    PARTIAL_EXIT_PERCENT = 0.5  # Take 50% at 2R
    TRAIL_STOP_ATR = 1.5
    
    # Position Limits
    MAX_CONCURRENT_POSITIONS = 5
    MAX_POSITION_SIZE_OF_ADV = 0.02  # Max 2% of avg daily volume
    
    # Liquidity Filter
    MIN_AVG_VOLUME = 100000
    MIN_PRICE = 50  # Avoid penny stocks
    
    # Risk Constraints
    MAX_STOP_LOSS_PERCENT = 0.10  # Max 10% stop loss
    MIN_CASH_BUFFER = 0.20  # Keep 20% cash buffer
    
    # Time-based Exits
    TIME_STOP_DAYS = 30
    TIME_STOP_MIN_GAIN = 0.02  # 2% minimum gain for time stop
    
    # Trailing Stop Activation
    TRAILING_STOP_ACTIVATION_GAIN = 0.05  # 5% gain to activate trailing stop


class PortfolioConfig:
    """Portfolio configuration"""
    
    INITIAL_CAPITAL = 100000
    
    # Slippage and Costs
    SLIPPAGE_PERCENT = 0.002  # 0.2% slippage
    COMMISSION_PERCENT = 0.0003  # 0.03% commission
    COMMISSION_MIN = 20  # Minimum ₹20 per trade
