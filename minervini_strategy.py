import os
import sys
import time
import csv
from typing import List, Tuple, Optional, Set, Dict, Any
from datetime import date, timedelta
from urllib.parse import quote

import requests

BASE_URL = "https://api.upstox.com/v3/historical-candle"

# Config via env
CSV_PATH = os.getenv("NIFTY500_CSV", "ind_nifty500list.csv")
NIFTY_INSTRUMENT = os.getenv("NIFTY_INSTRUMENT", "NSE_INDEX|Nifty 50")
EXCHANGE_PREFIX = os.getenv("UPSTOX_EXCHANGE", "NSE_EQ")
SERIES_FILTER = {s.strip().upper() for s in os.getenv("SERIES_FILTER", "EQ").split(",") if s.strip()}
LIMIT = int(os.getenv("UPSTOX_LIMIT", "0"))  # 0 = no limit
SLEEP_PER_CALL = float(os.getenv("UPSTOX_SLEEP_PER_CALL", "0.4"))
SLEEP_PER_INSTRUMENT = float(os.getenv("UPSTOX_SLEEP_PER_INSTRUMENT", "0.6"))

# Access token
ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN", "").strip()
if not ACCESS_TOKEN:
    print("ERROR: Please set the UPSTOX_ACCESS_TOKEN environment variable.")
    sys.exit(1)

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Authorization": f"Bearer {ACCESS_TOKEN}",
}

# ANSI Color codes
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def fmt(d: date) -> str:
    return d.strftime("%Y-%m-%d")

def bounded_date_range_for(unit: str, interval: int, today: date) -> tuple[str, str]:
    to_date = today

    if unit == "minutes":
        if 1 <= interval <= 15:
            from_date = to_date - timedelta(days=29)
        else:
            from_date = to_date - timedelta(days=89)
        availability_start = date(2022, 1, 1)
        if from_date < availability_start:
            from_date = availability_start

    elif unit == "hours":
        from_date = to_date - timedelta(days=89)
        availability_start = date(2022, 1, 1)
        if from_date < availability_start:
            from_date = availability_start

    elif unit == "days":
        from_date = to_date - timedelta(days=365)
        availability_start = date(2000, 1, 1)
        if from_date < availability_start:
            from_date = availability_start

    elif unit in ("weeks", "months"):
        from_date = date(2000, 1, 1)

    else:
        raise ValueError(f"Unsupported unit: {unit}")

    return fmt(from_date), fmt(to_date)

def fetch_candles(instrument_key: str, unit: str, interval: int, to_date: str, from_date: str):
    encoded_instrument_key = quote(instrument_key, safe="")
    url = f"{BASE_URL}/{encoded_instrument_key}/{unit}/{interval}/{to_date}/{from_date}"
    resp = requests.get(url, headers=HEADERS, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")
    return resp.json()

# ---------- Technical indicators ----------

def ema(values: List[float], period: int) -> Optional[float]:
    """Calculate EMA for last value"""
    n = len(values)
    if n < period or period <= 0:
        return None
    
    # Start with SMA
    sma_val = sum(values[:period]) / period
    k = 2.0 / (period + 1.0)
    ema_val = sma_val
    
    for i in range(period, n):
        ema_val = (values[i] - ema_val) * k + ema_val
    
    return ema_val

def rsi(closes: List[float], period: int = 14) -> Optional[float]:
    """Calculate RSI"""
    n = len(closes)
    if n < period + 1:
        return None
    
    gains = []
    losses = []
    for i in range(1, period + 1):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))
    
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    for i in range(period + 1, n):
        delta = closes[i] - closes[i - 1]
        gain = max(delta, 0.0)
        loss = max(-delta, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))

def calculate_52week_high(highs: List[float], period: int = 252) -> float:
    """Calculate 52-week high (approximately 252 trading days)"""
    if len(highs) < period:
        return max(highs) if highs else 0.0
    return max(highs[-period:])

def calculate_avg_volume(volumes: List[float], period: int = 20) -> float:
    """Calculate average volume"""
    if len(volumes) < period:
        return sum(volumes) / len(volumes) if volumes else 0.0
    return sum(volumes[-period:]) / period

def detect_base_breakout(highs: List[float], lows: List[float], closes: List[float], 
                         lookback: int = 42) -> Tuple[bool, Optional[float], Optional[float]]:
    """
    Detect if stock is breaking out of a base (consolidation pattern)
    Returns: (is_breakout, base_resistance, base_support)
    
    Base criteria:
    - 3-6 weeks (21-42 trading days) of consolidation
    - Higher lows or tight range
    - Low volatility (price range < 15%)
    """
    if len(closes) < lookback:
        return False, None, None
    
    # Look at last 21-42 days for base
    base_period = closes[-lookback:]
    base_highs = highs[-lookback:]
    base_lows = lows[-lookback:]
    
    # Calculate base resistance and support
    base_high = max(base_highs[:-1])  # Exclude today
    base_low = min(base_lows[:-1])
    
    # Check if range is tight (< 15% range)
    price_range = (base_high - base_low) / base_low * 100
    if price_range > 15:
        return False, None, None
    
    # Check if forming higher lows (bullish consolidation)
    mid_point = len(base_lows) // 2
    first_half_low = min(base_lows[:mid_point])
    second_half_low = min(base_lows[mid_point:-1])
    
    # Breakout condition: current close > base resistance
    current_close = closes[-1]
    is_breakout = current_close > base_high
    
    return is_breakout, base_high, base_low

def calculate_relative_strength(stock_closes: List[float], nifty_closes: List[float]) -> Tuple[Optional[float], bool]:
    """
    Calculate RS = Stock Close / Nifty Close
    Returns: (current_rs, is_rs_uptrend)
    """
    if not stock_closes or not nifty_closes:
        return None, False
    
    min_len = min(len(stock_closes), len(nifty_closes))
    if min_len < 50:
        return None, False
    
    # Calculate RS line
    rs_line = []
    for i in range(min_len):
        if nifty_closes[i] > 0:
            rs_line.append(stock_closes[i] / nifty_closes[i])
    
    if len(rs_line) < 50:
        return None, False
    
    current_rs = rs_line[-1]
    
    # Check if RS is in uptrend (simple: current > 50-day average)
    rs_50avg = sum(rs_line[-50:]) / 50
    is_uptrend = current_rs > rs_50avg
    
    return current_rs, is_uptrend

# ---------- Minervini SEPA Strategy ----------

def minervini_sepa_scan(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    volumes: List[float],
    nifty_closes: List[float]
) -> Tuple[str, List[str], Dict[str, Any]]:
    """
    Minervini SEPA Breakout Strategy
    
    Entry Conditions (ALL must be true):
    1. Price > 50 EMA and 150 EMA
    2. 50 EMA > 150 EMA (medium-term uptrend)
    3. RS line in uptrend (stock outperforming Nifty)
    4. Base breakout with strong volume (>= 1.5x avg)
    5. RSI between 55-70 (momentum confirmation)
    6. Price near 52-week high (within 10%)
    
    Returns: (signal, reasons, indicators)
    """
    reasons = []
    indicators = {}
    signal = "HOLD"
    
    if len(closes) < 150:
        return "HOLD", ["Insufficient data (need 150+ bars)"], indicators
    
    current_price = closes[-1]
    current_volume = volumes[-1] if volumes else 0
    
    indicators['current_price'] = current_price
    indicators['current_volume'] = current_volume
    
    # Condition 1 & 2: EMA Trend Filter
    ema_50 = ema(closes, 50)
    ema_150 = ema(closes, 150)
    
    indicators['ema_50'] = ema_50
    indicators['ema_150'] = ema_150
    
    if ema_50 is None or ema_150 is None:
        return "HOLD", ["Unable to calculate EMAs"], indicators
    
    condition1 = current_price > ema_50 and current_price > ema_150
    condition2 = ema_50 > ema_150
    
    if not condition1:
        reasons.append(f"❌ Price (₹{current_price:.2f}) not above both EMAs (50: ₹{ema_50:.2f}, 150: ₹{ema_150:.2f})")
        return "HOLD", reasons, indicators
    else:
        reasons.append(f"✅ Price (₹{current_price:.2f}) > EMA50 (₹{ema_50:.2f}) and EMA150 (₹{ema_150:.2f})")
    
    if not condition2:
        reasons.append(f"❌ EMA50 (₹{ema_50:.2f}) not > EMA150 (₹{ema_150:.2f}) - No medium-term uptrend")
        return "HOLD", reasons, indicators
    else:
        reasons.append(f"✅ EMA50 (₹{ema_50:.2f}) > EMA150 (₹{ema_150:.2f}) - Medium-term uptrend confirmed")
    
    # Condition 3: Relative Strength
    current_rs, rs_uptrend = calculate_relative_strength(closes, nifty_closes)
    indicators['relative_strength'] = current_rs
    indicators['rs_uptrend'] = rs_uptrend
    
    if current_rs is not None and rs_uptrend:
        reasons.append(f"✅ RS line in uptrend (RS: {current_rs:.4f}) - Outperforming Nifty")
    else:
        reasons.append(f"❌ RS not in uptrend - Not outperforming Nifty")
        return "HOLD", reasons, indicators
    
    # Condition 4: Base Breakout
    is_breakout, base_resistance, base_support = detect_base_breakout(highs, lows, closes, lookback=42)
    indicators['is_breakout'] = is_breakout
    indicators['base_resistance'] = base_resistance
    indicators['base_support'] = base_support
    
    if not is_breakout:
        reasons.append(f"❌ No breakout detected - Price not breaking base resistance")
        return "HOLD", reasons, indicators
    else:
        reasons.append(f"✅ BREAKOUT! Price (₹{current_price:.2f}) > Base Resistance (₹{base_resistance:.2f})")
    
    # Volume Confirmation
    avg_vol = calculate_avg_volume(volumes, 20)
    vol_ratio = current_volume / avg_vol if avg_vol > 0 else 0
    indicators['avg_volume_20'] = avg_vol
    indicators['volume_ratio'] = vol_ratio
    
    if vol_ratio >= 1.5:
        reasons.append(f"✅ Strong volume: {vol_ratio:.2f}x average ({current_volume:.0f} vs avg {avg_vol:.0f})")
    else:
        reasons.append(f"⚠️  Weak volume: {vol_ratio:.2f}x average - Breakout may fail")
        # Don't return HOLD yet, check other conditions
    
    # Condition 5: RSI Momentum
    rsi_val = rsi(closes, 14)
    indicators['rsi'] = rsi_val
    
    if rsi_val is not None:
        if 55 <= rsi_val <= 70:
            reasons.append(f"✅ RSI ({rsi_val:.2f}) in momentum zone (55-70)")
        else:
            reasons.append(f"⚠️  RSI ({rsi_val:.2f}) outside optimal range (55-70)")
            if rsi_val > 70:
                reasons.append(f"   RSI overbought - Higher risk of pullback")
            elif rsi_val < 55:
                reasons.append(f"   RSI weak - Momentum not confirmed")
    
    # Condition 6: Near 52-week high
    high_52w = calculate_52week_high(highs, 252)
    distance_from_high = (high_52w - current_price) / high_52w * 100
    indicators['52w_high'] = high_52w
    indicators['distance_from_52w_high_pct'] = distance_from_high
    
    if distance_from_high <= 10:
        reasons.append(f"✅ Near 52-week high: ₹{high_52w:.2f} ({distance_from_high:.1f}% away)")
    else:
        reasons.append(f"⚠️  {distance_from_high:.1f}% from 52-week high (₹{high_52w:.2f})")
    
    # Final Decision
    # Core conditions must all pass: EMA trend, RS uptrend, breakout
    # Volume should be strong (1.5x) but we give a warning if not
    critical_pass = condition1 and condition2 and rs_uptrend and is_breakout
    
    if critical_pass and vol_ratio >= 1.5:
        signal = "BUY"
        reasons.insert(0, f"🚀 STRONG BUY - Minervini SEPA Breakout Confirmed")
        
        # Add risk/reward info
        stop_loss = base_resistance if base_resistance else current_price * 0.97
        risk = current_price - stop_loss
        target1 = current_price + (risk * 2)  # 2:1 R/R
        target2 = current_price + (risk * 3)  # 3:1 R/R
        
        indicators['stop_loss'] = stop_loss
        indicators['target1'] = target1
        indicators['target2'] = target2
        
        reasons.append(f"\n📊 Trade Setup:")
        reasons.append(f"   Entry: ₹{current_price:.2f}")
        reasons.append(f"   Stop Loss: ₹{stop_loss:.2f} (Risk: ₹{risk:.2f})")
        reasons.append(f"   Target 1: ₹{target1:.2f} (R:R = 2:1)")
        reasons.append(f"   Target 2: ₹{target2:.2f} (R:R = 3:1)")
        
    elif critical_pass:
        signal = "WATCH"
        reasons.insert(0, f"👀 WATCH - Breakout with weak volume, wait for confirmation")
    else:
        signal = "HOLD"
        reasons.insert(0, f"⏸️  HOLD - Not all Minervini SEPA conditions met")
    
    return signal, reasons, indicators

def print_signal(symbol: str, company: str, signal: str, reasons: List[str]):
    """Print signal with colored output"""
    if signal == "BUY":
        color = Colors.GREEN
        icon = "🚀"
    elif signal == "WATCH":
        color = Colors.YELLOW
        icon = "👀"
    else:
        color = Colors.BLUE
        icon = "⏸️"
    
    print(f"\n{Colors.BOLD}{color}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{color}{icon} {symbol} ({company}) - {signal}{Colors.RESET}")
    print(f"{Colors.BOLD}{color}{'='*80}{Colors.RESET}")
    
    for reason in reasons:
        # Color code checkmarks and x marks
        if "✅" in reason:
            print(f"{Colors.GREEN}{reason}{Colors.RESET}")
        elif "❌" in reason:
            print(f"{Colors.RED}{reason}{Colors.RESET}")
        elif "⚠️" in reason:
            print(f"{Colors.YELLOW}{reason}{Colors.RESET}")
        elif "📊" in reason or "Entry:" in reason or "Stop" in reason or "Target" in reason:
            print(f"{Colors.CYAN}{reason}{Colors.RESET}")
        else:
            print(f"{color}{reason}{Colors.RESET}")
    
    print(f"{Colors.BOLD}{color}{'='*80}{Colors.RESET}\n")

def extract_ohlcv(candles: List[List[Any]]) -> Tuple[List[float], List[float], List[float], List[float]]:
    """Extract OHLCV data from candles"""
    candles = sorted(candles, key=lambda x: x[0])
    highs = [float(x[2]) for x in candles]
    lows = [float(x[3]) for x in candles]
    closes = [float(x[4]) for x in candles]
    volumes = [float(x[5]) for x in candles]
    return highs, lows, closes, volumes

# ---------- CSV instrument loading ----------

def load_instrument_keys_from_csv(
    csv_path: str,
    exchange_prefix: str,
    allow_series: Optional[Set[str]],
) -> List[Tuple[str, str, str]]:
    if not os.path.exists(csv_path):
        return []
    results: List[Tuple[str, str, str]] = []
    seen_isins: Set[str] = set()
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return []
        for row in reader:
            nrow = {(k.strip().lower() if isinstance(k, str) else k): (v.strip() if isinstance(v, str) else v)
                    for k, v in row.items()}
            company = nrow.get("company name", "")
            symbol = nrow.get("symbol", "")
            series = (nrow.get("series", "") or "").upper()
            isin = (nrow.get("isin code", "") or "").upper()
            if not isin or not isin.startswith("INE"):
                continue
            if allow_series and series not in allow_series:
                continue
            if isin in seen_isins:
                continue
            seen_isins.add(isin)
            instrument_key = f"{exchange_prefix}|{isin}"
            results.append((instrument_key, symbol, company))
    return results

def get_instrument_keys() -> List[Tuple[str, str, str]]:
    raw = os.getenv("UPSTOX_INSTRUMENT_KEYS", "").strip()
    if raw:
        keys = [part.strip() for part in raw.split(",") if part.strip()]
        return [(k, k.split("|")[-1], "from-env") for k in keys]
    from_csv = load_instrument_keys_from_csv(CSV_PATH, EXCHANGE_PREFIX, SERIES_FILTER)
    if LIMIT and LIMIT > 0:
        from_csv = from_csv[:LIMIT]
    if from_csv:
        return from_csv
    # Fallback
    return [(f"{EXCHANGE_PREFIX}|INE242A01010", "IOC", "Indian Oil Corporation Ltd.")]

# ---------- Main ----------

def main():
    today = date.today()
    instruments = get_instrument_keys()

    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}Minervini SEPA Breakout Scanner - {today}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}Total instruments: {len(instruments)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}\n")

    # Fetch Nifty data first for RS calculation
    print(f"{Colors.CYAN}Fetching Nifty 50 data for RS calculation...{Colors.RESET}")
    nifty_closes = []
    try:
        from_date, to_date = bounded_date_range_for("days", 1, today)
        nifty_payload = fetch_candles(NIFTY_INSTRUMENT, "days", 1, to_date, from_date)
        nifty_candles = (nifty_payload.get("data") or {}).get("candles") or []
        if nifty_candles:
            _, _, nifty_closes, _ = extract_ohlcv(nifty_candles)
            print(f"{Colors.GREEN}✓ Nifty data loaded: {len(nifty_closes)} bars{Colors.RESET}\n")
        else:
            print(f"{Colors.YELLOW}⚠️  Could not fetch Nifty data, RS will not be calculated{Colors.RESET}\n")
        time.sleep(SLEEP_PER_CALL)
    except Exception as e:
        print(f"{Colors.YELLOW}⚠️  Error fetching Nifty: {str(e)}{Colors.RESET}\n")
    
    buy_signals = []
    watch_signals = []
    
    for (instrument_key, symbol, company) in instruments:
        try:
            # Fetch daily data
            from_date, to_date = bounded_date_range_for("days", 1, today)
            payload = fetch_candles(instrument_key, "days", 1, to_date, from_date)
            candles = (payload.get("data") or {}).get("candles") or []
            
            if not candles or len(candles) < 150:
                print(f"{Colors.YELLOW}⚠️  {symbol}: Insufficient data (only {len(candles)} bars){Colors.RESET}\n")
                time.sleep(SLEEP_PER_CALL)
                continue
            
            highs, lows, closes, volumes = extract_ohlcv(candles)
            signal, reasons, indicators = minervini_sepa_scan(highs, lows, closes, volumes, nifty_closes)
            
            if signal == "BUY":
                buy_signals.append((symbol, company, signal, reasons))
                print_signal(symbol, company, signal, reasons)
            elif signal == "WATCH":
                watch_signals.append((symbol, company, signal, reasons))
                print_signal(symbol, company, signal, reasons)
            # Don't print HOLD signals to keep output clean
            
            time.sleep(SLEEP_PER_INSTRUMENT)
            
        except Exception as e:
            print(f"{Colors.RED}❌ Error processing {symbol}: {str(e)}{Colors.RESET}\n")
            time.sleep(SLEEP_PER_CALL)

    # Summary
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}SCAN SUMMARY{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}")
    print(f"{Colors.GREEN}🚀 BUY Signals: {len(buy_signals)}{Colors.RESET}")
    if buy_signals:
        for sym, _, _, _ in buy_signals:
            print(f"   • {sym}")
    
    print(f"\n{Colors.YELLOW}👀 WATCH List: {len(watch_signals)}{Colors.RESET}")
    if watch_signals:
        for sym, _, _, _ in watch_signals:
            print(f"   • {sym}")
    
    print(f"\n{Colors.CYAN}Total scanned: {len(instruments)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}\n")

if __name__ == "__main__":
    main()
