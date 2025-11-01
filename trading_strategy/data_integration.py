"""
Data Integration Examples
Shows how to integrate the strategy with various data sources
"""

import pandas as pd
from datetime import datetime, timedelta


# ============================================================================
# Example 1: PostgreSQL Database Integration
# ============================================================================

def load_from_postgresql(instrument_keys, start_date=None, end_date=None):
    """
    Load data from PostgreSQL database
    
    Example schema:
        CREATE TABLE candles (
            id SERIAL PRIMARY KEY,
            instrument_key VARCHAR(50),
            timestamp TIMESTAMP,
            open DECIMAL(10,2),
            high DECIMAL(10,2),
            low DECIMAL(10,2),
            close DECIMAL(10,2),
            volume BIGINT
        );
    """
    # Uncomment and install: pip install psycopg2-binary
    
    # import psycopg2
    # 
    # conn = psycopg2.connect(
    #     host="localhost",
    #     database="trading_db",
    #     user="your_username",
    #     password="your_password"
    # )
    # 
    # data = {}
    # for instrument_key in instrument_keys:
    #     query = """
    #         SELECT timestamp, open, high, low, close, volume
    #         FROM candles
    #         WHERE instrument_key = %s
    #     """
    #     params = [instrument_key]
    #     
    #     if start_date:
    #         query += " AND timestamp >= %s"
    #         params.append(start_date)
    #     if end_date:
    #         query += " AND timestamp <= %s"
    #         params.append(end_date)
    #     
    #     query += " ORDER BY timestamp ASC"
    #     
    #     df = pd.read_sql(query, conn, params=params)
    #     data[instrument_key] = df
    # 
    # conn.close()
    # return data
    
    print("PostgreSQL example - uncomment code to use")
    return {}


# ============================================================================
# Example 2: Yahoo Finance API
# ============================================================================

def load_from_yahoo(symbols, start_date=None, end_date=None):
    """
    Load data from Yahoo Finance
    
    Install: pip install yfinance
    """
    # Uncomment and install: pip install yfinance
    
    # import yfinance as yf
    # 
    # data = {}
    # for symbol in symbols:
    #     ticker = yf.Ticker(symbol)
    #     df = ticker.history(start=start_date, end=end_date)
    #     
    #     # Rename columns to match our format
    #     df = df.reset_index()
    #     df = df.rename(columns={
    #         'Date': 'timestamp',
    #         'Open': 'open',
    #         'High': 'high',
    #         'Low': 'low',
    #         'Close': 'close',
    #         'Volume': 'volume'
    #     })
    #     
    #     data[symbol] = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    # 
    # return data
    
    print("Yahoo Finance example - uncomment code to use")
    return {}


# ============================================================================
# Example 3: CSV Files
# ============================================================================

def load_from_csv(csv_directory):
    """
    Load data from CSV files
    
    Expected format:
        - One CSV per stock
        - Filename: SYMBOL.csv (e.g., RELIANCE.csv)
        - Columns: date,open,high,low,close,volume
    """
    import os
    import glob
    
    data = {}
    csv_files = glob.glob(os.path.join(csv_directory, "*.csv"))
    
    for csv_file in csv_files:
        # Extract symbol from filename
        symbol = os.path.basename(csv_file).replace('.csv', '')
        
        # Read CSV
        df = pd.read_csv(csv_file)
        
        # Ensure date column is datetime
        if 'date' in df.columns:
            df['timestamp'] = pd.to_datetime(df['date'])
        elif 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Ensure required columns exist
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        if all(col in df.columns for col in required_cols):
            data[symbol] = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        else:
            print(f"Warning: {csv_file} missing required columns")
    
    return data


# ============================================================================
# Example 4: MongoDB Integration
# ============================================================================

def load_from_mongodb(instrument_keys, start_date=None, end_date=None):
    """
    Load data from MongoDB
    
    Install: pip install pymongo
    """
    # Uncomment and install: pip install pymongo
    
    # from pymongo import MongoClient
    # 
    # client = MongoClient('mongodb://localhost:27017/')
    # db = client['trading_db']
    # collection = db['candles']
    # 
    # data = {}
    # for instrument_key in instrument_keys:
    #     query = {'instrument_key': instrument_key}
    #     
    #     if start_date or end_date:
    #         query['timestamp'] = {}
    #         if start_date:
    #             query['timestamp']['$gte'] = start_date
    #         if end_date:
    #             query['timestamp']['$lte'] = end_date
    #     
    #     cursor = collection.find(query).sort('timestamp', 1)
    #     df = pd.DataFrame(list(cursor))
    #     
    #     if not df.empty:
    #         data[instrument_key] = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    # 
    # return data
    
    print("MongoDB example - uncomment code to use")
    return {}


# ============================================================================
# Example 5: Zerodha Kite API
# ============================================================================

def load_from_kite(instrument_tokens, start_date, end_date, api_key, access_token):
    """
    Load data from Zerodha Kite API
    
    Install: pip install kiteconnect
    """
    # Uncomment and install: pip install kiteconnect
    
    # from kiteconnect import KiteConnect
    # 
    # kite = KiteConnect(api_key=api_key)
    # kite.set_access_token(access_token)
    # 
    # data = {}
    # for instrument_token in instrument_tokens:
    #     # Fetch historical data
    #     records = kite.historical_data(
    #         instrument_token=instrument_token,
    #         from_date=start_date,
    #         to_date=end_date,
    #         interval="day"
    #     )
    #     
    #     df = pd.DataFrame(records)
    #     df = df.rename(columns={'date': 'timestamp'})
    #     
    #     data[instrument_token] = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    # 
    # return data
    
    print("Kite API example - uncomment code to use")
    return {}


# ============================================================================
# Usage Example
# ============================================================================

def example_usage():
    """
    Example of using data integration with the strategy
    """
    from config import StrategyConfig, PortfolioConfig
    from backtest_engine import BacktestEngine
    from performance_analyzer import PerformanceAnalyzer
    
    # Option 1: Load from CSV
    data = load_from_csv('./data')
    
    # Option 2: Load from Yahoo Finance
    # data = load_from_yahoo(
    #     symbols=['RELIANCE.NS', 'TCS.NS', 'INFY.NS'],
    #     start_date='2020-01-01',
    #     end_date='2024-12-31'
    # )
    
    # Option 3: Load from Database
    # data = load_from_postgresql(
    #     instrument_keys=['RELIANCE', 'TCS', 'INFY'],
    #     start_date='2020-01-01',
    #     end_date='2024-12-31'
    # )
    
    if not data:
        print("No data loaded - check your data source configuration")
        return
    
    # Run backtest
    config = StrategyConfig()
    engine = BacktestEngine(config)
    
    closed_trades, daily_equity_curve = engine.run_backtest(
        data=data,
        initial_capital=PortfolioConfig.INITIAL_CAPITAL
    )
    
    # Analyze results
    analyzer = PerformanceAnalyzer(closed_trades, daily_equity_curve)
    analyzer.print_report()


# ============================================================================
# Data Validation
# ============================================================================

def validate_data(df, symbol):
    """
    Validate OHLCV data quality
    
    Args:
        df: DataFrame with OHLCV data
        symbol: Stock symbol
        
    Returns:
        bool: True if data is valid
    """
    required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    
    # Check required columns
    if not all(col in df.columns for col in required_cols):
        print(f"{symbol}: Missing required columns")
        return False
    
    # Check for negative prices
    if (df['close'] <= 0).any():
        print(f"{symbol}: Found negative or zero prices")
        return False
    
    # Check OHLC relationships
    if (df['high'] < df['low']).any():
        print(f"{symbol}: High is less than Low")
        return False
    
    if (df['high'] < df['close']).any():
        print(f"{symbol}: High is less than Close")
        return False
    
    if (df['low'] > df['close']).any():
        print(f"{symbol}: Low is greater than Close")
        return False
    
    # Check for sufficient data
    if len(df) < 250:
        print(f"{symbol}: Insufficient data (need at least 250 bars)")
        return False
    
    print(f"{symbol}: Data validation passed ✓")
    return True


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("DATA INTEGRATION EXAMPLES")
    print("=" * 60)
    print("\nThis file shows examples of integrating with various data sources.")
    print("Uncomment the relevant sections and install required packages.")
    print("\nSupported data sources:")
    print("1. PostgreSQL Database")
    print("2. Yahoo Finance API")
    print("3. CSV Files")
    print("4. MongoDB")
    print("5. Zerodha Kite API")
    print("\n" + "=" * 60)
