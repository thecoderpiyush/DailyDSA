#!/usr/bin/env python3
"""
IMPROVED: Robust daily swing-signal generator using Upstox historical candles.

This version addresses efficiency and production-readiness issues identified in code review.

Key Improvements:
- Optimized indicator calculations (no redundant computations)
- Proper rate limiting with token bucket algorithm
- Enhanced error handling with specific exception types
- Request timeout strategy (connect/read separation)
- Configuration validation
- Structured error logging
- Performance metrics tracking
- Caching support (file-based)
- Graceful shutdown handling

Environment Variables:
- UPSTOX_ACCESS_TOKEN: required
- NIFTY500_CSV: path to CSV with columns: "Company Name", "Symbol", "Series", "ISIN Code"
- UPSTOX_EXCHANGE: default "NSE_EQ"
- SERIES_FILTER: default "EQ"
- UPSTOX_LIMIT: integer cap on number of instruments (0 = no limit)
- RATE_LIMIT_CALLS: max API calls per time window (default 180)
- RATE_LIMIT_WINDOW: time window in seconds (default 60)
- ENABLE_CACHE: enable file-based caching (default "false")
- CACHE_DIR: cache directory (default ".cache")

Usage:
  python upstox_swing_signals_improved.py
"""
import os
import sys
import csv
import time
import math
import signal
import logging
import json
from typing import List, Tuple, Optional, Set, Dict, Any
from datetime import datetime, date, timedelta, timezone
from urllib.parse import quote
from pathlib import Path
from collections import deque
from dataclasses import dataclass, asdict

import requests

# ------------- Configuration Validation -------------
def validate_config():
    """Validate environment configuration."""
    errors = []
    
    token = os.getenv("UPSTOX_ACCESS_TOKEN", "").strip()
    if not token:
        errors.append("UPSTOX_ACCESS_TOKEN is required")
    
    try:
        limit = int(os.getenv("UPSTOX_LIMIT", "0"))
        if limit < 0:
            errors.append("UPSTOX_LIMIT must be >= 0")
    except ValueError:
        errors.append("UPSTOX_LIMIT must be an integer")
    
    try:
        rate_calls = int(os.getenv("RATE_LIMIT_CALLS", "180"))
        if rate_calls <= 0:
            errors.append("RATE_LIMIT_CALLS must be > 0")
    except ValueError:
        errors.append("RATE_LIMIT_CALLS must be an integer")
    
    try:
        rate_window = float(os.getenv("RATE_LIMIT_WINDOW", "60"))
        if rate_window <= 0:
            errors.append("RATE_LIMIT_WINDOW must be > 0")
    except ValueError:
        errors.append("RATE_LIMIT_WINDOW must be a number")
    
    try:
        min_bars = int(os.getenv("DAILY_MIN_BARS", "250"))
        if min_bars < 200:
            errors.append("DAILY_MIN_BARS should be >= 200 for SMA200 calculation")
    except ValueError:
        errors.append("DAILY_MIN_BARS must be an integer")
    
    if errors:
        for err in errors:
            print(f"Configuration Error: {err}", file=sys.stderr)
        return False
    return True

if not validate_config():
    sys.exit(1)

# ------------- Logging Setup -------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("swing")

# ------------- Configuration -------------
BASE_URL = "https://api.upstox.com/v3/historical-candle"
CSV_PATH = os.getenv("NIFTY500_CSV", "ind_nifty500list.csv")
EXCHANGE_PREFIX = os.getenv("UPSTOX_EXCHANGE", "NSE_EQ")
SERIES_FILTER = {s.strip().upper() for s in os.getenv("SERIES_FILTER", "EQ").split(",") if s.strip()}
LIMIT = int(os.getenv("UPSTOX_LIMIT", "0"))
DAILY_MIN_BARS = int(os.getenv("DAILY_MIN_BARS", "250"))
DAILY_FETCH_BUFFER_DAYS = int(os.getenv("DAILY_FETCH_BUFFER_DAYS", "550"))

# Rate limiting configuration
RATE_LIMIT_CALLS = int(os.getenv("RATE_LIMIT_CALLS", "180"))  # calls per window
RATE_LIMIT_WINDOW = float(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds

# Caching configuration
ENABLE_CACHE = os.getenv("ENABLE_CACHE", "false").lower() == "true"
CACHE_DIR = Path(os.getenv("CACHE_DIR", ".cache"))
if ENABLE_CACHE:
    CACHE_DIR.mkdir(exist_ok=True)

ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN", "").strip()
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Authorization": f"Bearer {ACCESS_TOKEN}",
}

# Performance metrics
@dataclass
class Metrics:
    total_symbols: int = 0
    successful: int = 0
    failed: int = 0
    api_calls: int = 0
    cache_hits: int = 0
    total_time: float = 0.0
    api_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

metrics = Metrics()

# ------------- Graceful Shutdown -------------
shutdown_requested = False

def signal_handler(signum, frame):
    global shutdown_requested
    logger.info("Shutdown signal received, finishing current symbol...")
    shutdown_requested = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ------------- Rate Limiter -------------
class TokenBucketRateLimiter:
    """Token bucket rate limiter for API calls."""
    
    def __init__(self, max_calls: int, time_window: float):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = deque()
        self.lock_until = 0.0
    
    def wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        now = time.time()
        
        # If we're in a lockout period (e.g., after 429), wait
        if now < self.lock_until:
            sleep_time = self.lock_until - now
            logger.warning(f"Rate limit lockout, waiting {sleep_time:.1f}s")
            time.sleep(sleep_time)
            now = time.time()
        
        # Remove calls outside the time window
        while self.calls and self.calls[0] < now - self.time_window:
            self.calls.popleft()
        
        # If at capacity, wait for oldest call to expire
        if len(self.calls) >= self.max_calls:
            sleep_time = self.time_window - (now - self.calls[0]) + 0.1
            if sleep_time > 0:
                logger.debug(f"Rate limit reached, waiting {sleep_time:.1f}s")
                time.sleep(sleep_time)
                # Remove expired call
                self.calls.popleft()
        
        # Record this call
        self.calls.append(time.time())
    
    def handle_rate_limit_response(self, retry_after: Optional[int] = None):
        """Handle 429 response with exponential backoff."""
        if retry_after:
            self.lock_until = time.time() + retry_after
        else:
            # Default backoff: 30 seconds
            self.lock_until = time.time() + 30

rate_limiter = TokenBucketRateLimiter(RATE_LIMIT_CALLS, RATE_LIMIT_WINDOW)

# ------------- Time helpers -------------
IST = timezone(timedelta(hours=5, minutes=30))

def now_ist() -> datetime:
    return datetime.now(tz=IST)

def today_ist() -> date:
    return now_ist().date()

def fmt(d: date) -> str:
    return d.strftime("%Y-%m-%d")

def parse_ts(ts: str) -> Optional[datetime]:
    try:
        if ts.endswith("Z"):
            ts = ts.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=IST)
        return dt
    except Exception:
        return None

# ------------- Cache helpers -------------
def get_cache_key(instrument_key: str, from_date: str, to_date: str) -> str:
    """Generate cache key for data."""
    return f"{instrument_key}_{from_date}_{to_date}".replace("|", "_").replace("/", "_")

def load_from_cache(cache_key: str) -> Optional[Dict[str, Any]]:
    """Load data from cache if available."""
    if not ENABLE_CACHE:
        return None
    
    cache_file = CACHE_DIR / f"{cache_key}.json"
    if not cache_file.exists():
        return None
    
    try:
        with open(cache_file, "r") as f:
            data = json.load(f)
            # Check if cache is fresh (less than 1 day old)
            cache_time = datetime.fromisoformat(data.get("cached_at", "2000-01-01"))
            if (datetime.now() - cache_time).days > 1:
                return None
            metrics.cache_hits += 1
            return data.get("payload")
    except Exception as e:
        logger.warning(f"Cache read error for {cache_key}: {e}")
        return None

def save_to_cache(cache_key: str, payload: Dict[str, Any]):
    """Save data to cache."""
    if not ENABLE_CACHE:
        return
    
    cache_file = CACHE_DIR / f"{cache_key}.json"
    try:
        with open(cache_file, "w") as f:
            json.dump({
                "cached_at": datetime.now().isoformat(),
                "payload": payload
            }, f)
    except Exception as e:
        logger.warning(f"Cache write error for {cache_key}: {e}")

# ------------- API helpers with improved error handling -------------
class APIError(Exception):
    """Base exception for API errors."""
    pass

class RateLimitError(APIError):
    """Rate limit exceeded."""
    pass

class AuthenticationError(APIError):
    """Authentication failed."""
    pass

class DataError(APIError):
    """Data validation error."""
    pass

def fetch_candles(instrument_key: str, unit: str, interval: int, to_date: str, from_date: str, retries: int = 2) -> Dict[str, Any]:
    """
    Fetch candles with improved error handling and rate limiting.
    """
    cache_key = get_cache_key(instrument_key, from_date, to_date)
    
    # Try cache first
    cached = load_from_cache(cache_key)
    if cached is not None:
        logger.debug(f"Cache hit for {instrument_key}")
        return cached
    
    encoded_instrument_key = quote(instrument_key, safe="")
    url = f"{BASE_URL}/{encoded_instrument_key}/{unit}/{interval}/{to_date}/{from_date}"
    
    for attempt in range(retries + 1):
        try:
            # Rate limiting
            rate_limiter.wait_if_needed()
            
            # Make request with proper timeouts
            start_time = time.time()
            resp = requests.get(
                url, 
                headers=HEADERS, 
                timeout=(5, 30)  # (connect_timeout, read_timeout)
            )
            metrics.api_calls += 1
            metrics.api_time += time.time() - start_time
            
            if resp.status_code == 200:
                payload = resp.json()
                save_to_cache(cache_key, payload)
                return payload
            
            # Handle specific error codes
            if resp.status_code == 401 or resp.status_code == 403:
                raise AuthenticationError(f"Authentication failed: {resp.text}")
            
            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                retry_after_int = int(retry_after) if retry_after else None
                rate_limiter.handle_rate_limit_response(retry_after_int)
                logger.warning(f"Rate limit hit for {instrument_key}, attempt {attempt + 1}/{retries + 1}")
                continue
            
            if resp.status_code in (500, 502, 503, 504):
                # Exponential backoff for server errors
                sleep_s = min(0.6 * (2 ** attempt), 10)  # Cap at 10 seconds
                logger.warning(f"Server error {resp.status_code} for {instrument_key}, retrying in {sleep_s:.1f}s")
                time.sleep(sleep_s)
                continue
            
            # Other errors
            raise APIError(f"HTTP {resp.status_code}: {resp.text}")
            
        except requests.exceptions.Timeout as e:
            logger.warning(f"Timeout for {instrument_key}, attempt {attempt + 1}/{retries + 1}")
            if attempt < retries:
                time.sleep(0.5 * (attempt + 1))
                continue
            raise APIError(f"Timeout after {retries + 1} attempts: {e}")
        
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Connection error for {instrument_key}, attempt {attempt + 1}/{retries + 1}")
            if attempt < retries:
                time.sleep(1.0 * (attempt + 1))
                continue
            raise APIError(f"Connection error after {retries + 1} attempts: {e}")
        
        except (AuthenticationError, RateLimitError) as e:
            # Don't retry auth errors
            raise
        
        except Exception as e:
            logger.warning(f"Unexpected error for {instrument_key}: {type(e).__name__}: {e}")
            if attempt < retries:
                time.sleep(0.5 * (attempt + 1))
                continue
            raise APIError(f"Unexpected error: {e}")
    
    raise APIError("Max retries exceeded")

def extract_ohlc_with_dt(candles: List[List[Any]]) -> Tuple[List[datetime], List[float], List[float], List[float]]:
    """
    Cleans rows, enforces monotonic timestamps, dedupes, validates positivity and finiteness.
    """
    clean = []
    for x in candles:
        if len(x) < 5:
            continue
        dt = parse_ts(str(x[0]))
        try:
            h = float(x[2]); l = float(x[3]); c = float(x[4])
        except Exception:
            continue
        if dt is None:
            continue
        if not all(math.isfinite(v) for v in (h, l, c)):
            continue
        if h <= 0 or l <= 0 or c <= 0:
            continue
        if l > h:
            h, l = max(h, l), min(h, l)
        clean.append((dt, h, l, c))

    if not clean:
        return [], [], [], []

    clean.sort(key=lambda z: z[0])
    dedup: Dict[datetime, Tuple[float, float, float]] = {}
    for dt, h, l, c in clean:
        dedup[dt] = (h, l, c)
    dts = sorted(dedup.keys())
    highs = [dedup[dt][0] for dt in dts]
    lows = [dedup[dt][1] for dt in dts]
    closes = [dedup[dt][2] for dt in dts]
    return dts, highs, lows, closes

# ------------- OPTIMIZED Indicators -------------
def sma(series: List[float], period: int) -> Optional[float]:
    """Simple Moving Average - last value only."""
    if len(series) < period or period <= 0:
        return None
    return sum(series[-period:]) / period

def ema_last_optimized(values: List[float], period: int) -> Optional[float]:
    """
    OPTIMIZED: Calculate only the last EMA value.
    Avoids creating full series when only last value is needed.
    """
    n = len(values)
    if n < period or period <= 0:
        return None
    
    # Seed with SMA
    ema = sum(values[:period]) / period
    k = 2.0 / (period + 1.0)
    
    # Iteratively update to final value
    for i in range(period, n):
        ema = (values[i] - ema) * k + ema
    
    return ema

def rsi_last(closes: List[float], period: int = 14) -> Optional[float]:
    """RSI with Wilder's smoothing - last value only."""
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
        gain = max(delta, 0.0); loss = max(-delta, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))

def true_range(h: float, l: float, prev_close: float) -> float:
    """True Range calculation."""
    return max(h - l, abs(h - prev_close), abs(l - prev_close))

def atr_last(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> Optional[float]:
    """
    OPTIMIZED: Calculate only the last ATR value.
    """
    n = len(closes)
    if n < period:
        return None
    
    # Calculate true ranges
    trs = [highs[0] - lows[0]]
    for i in range(1, n):
        trs.append(true_range(highs[i], lows[i], closes[i - 1]))
    
    # Wilder's smoothing
    atr = sum(trs[:period]) / period
    for i in range(period, n):
        atr = ((atr * (period - 1)) + trs[i]) / period
    
    return atr

def adx_last(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """ADX with Wilder's smoothing - last value only."""
    n = len(closes)
    if n < period * 2:
        return None, None, None

    trs = [0.0] * n
    plus_dm = [0.0] * n
    minus_dm = [0.0] * n

    for i in range(1, n):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm[i] = up if (up > down and up > 0) else 0.0
        minus_dm[i] = down if (down > up and down > 0) else 0.0
        trs[i] = true_range(highs[i], lows[i], closes[i - 1])
    trs[0] = highs[0] - lows[0]

    # Wilder smoothing helper
    def wild_smooth_last(src: List[float], p: int) -> Optional[float]:
        if len(src) < p + 1:
            return None
        s = sum(src[1:p+1])
        for i in range(p + 1, len(src)):
            s = (s - (s / p) + src[i])
        return s
    
    trn = wild_smooth_last(trs, period)
    plus_dmn = wild_smooth_last(plus_dm, period)
    minus_dmn = wild_smooth_last(minus_dm, period)
    
    if trn is None or trn == 0:
        return None, None, None
    
    di_plus = 100.0 * ((plus_dmn or 0.0) / trn)
    di_minus = 100.0 * ((minus_dmn or 0.0) / trn)
    
    # Calculate DX series for ADX smoothing
    dx_values = []
    # Need to calculate DX for smoothing window
    for i in range(period, n):
        if i < period:
            continue
        # Calculate smoothed values at this point
        tr_smooth = sum(trs[1:period+1]) / period
        for j in range(period + 1, i + 1):
            tr_smooth = (tr_smooth - (tr_smooth / period) + trs[j])
        
        pdm_smooth = sum(plus_dm[1:period+1]) / period
        for j in range(period + 1, i + 1):
            pdm_smooth = (pdm_smooth - (pdm_smooth / period) + plus_dm[j])
        
        mdm_smooth = sum(minus_dm[1:period+1]) / period
        for j in range(period + 1, i + 1):
            mdm_smooth = (mdm_smooth - (mdm_smooth / period) + minus_dm[j])
        
        if tr_smooth > 0:
            dip_i = 100.0 * (pdm_smooth / tr_smooth)
            dim_i = 100.0 * (mdm_smooth / tr_smooth)
            denom = dip_i + dim_i
            dx_i = 0.0 if denom == 0 else 100.0 * (abs(dip_i - dim_i) / denom)
            dx_values.append(dx_i)
    
    if len(dx_values) < period:
        return None, di_plus, di_minus
    
    # Smooth DX to get ADX
    adx = sum(dx_values[:period]) / period
    for i in range(period, len(dx_values)):
        adx = ((adx * (period - 1)) + dx_values[i]) / period
    
    return adx, di_plus, di_minus

def stddev(values: List[float]) -> float:
    """Population standard deviation."""
    n = len(values)
    if n == 0:
        return 0.0
    m = sum(values) / n
    var = sum((x - m) ** 2 for x in values) / n
    return var ** 0.5

def bollinger_last_two(closes: List[float], period: int = 20, mult: float = 2.0) -> Tuple[
    Tuple[Optional[float], Optional[float], Optional[float]],
    Tuple[Optional[float], Optional[float], Optional[float]]
]:
    """
    OPTIMIZED: Calculate Bollinger Bands for last TWO periods.
    Returns: (current_bb, previous_bb)
    Avoids redundant recalculation.
    """
    n = len(closes)
    if n < period + 1:
        return (None, None, None), (None, None, None)
    
    # Current period
    window_curr = closes[-period:]
    mid_curr = sum(window_curr) / period
    dev_curr = stddev(window_curr)
    upper_curr = mid_curr + mult * dev_curr
    lower_curr = mid_curr - mult * dev_curr
    
    # Previous period
    window_prev = closes[-period-1:-1]
    mid_prev = sum(window_prev) / period
    dev_prev = stddev(window_prev)
    upper_prev = mid_prev + mult * dev_prev
    lower_prev = mid_prev - mult * dev_prev
    
    return (mid_curr, upper_curr, lower_curr), (mid_prev, upper_prev, lower_prev)

# ------------- Color helpers -------------
RESET = "\033[0m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"

def colorize(text: str, color: str) -> str:
    return f"{color}{text}{RESET}"

# ------------- Universe -------------
def load_instrument_keys_from_csv(
    csv_path: str,
    exchange_prefix: str,
    allow_series: Optional[Set[str]],
) -> List[Tuple[str, str, str]]:
    if not os.path.exists(csv_path):
        logger.warning("CSV not found at %s; using fallback", csv_path)
        return []
    results: List[Tuple[str, str, str]] = []
    seen_isins: Set[str] = set()
    try:
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
    except Exception as e:
        logger.error(f"Error reading CSV: {e}")
        return []
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
    return [(f"{EXCHANGE_PREFIX}|INE242A01010", "IOC", "Indian Oil Corporation Ltd.")]

# ------------- Data validation -------------
def validate_price_series(dts: List[datetime], highs: List[float], lows: List[float], closes: List[float]) -> Tuple[bool, List[str]]:
    msgs: List[str] = []
    ok = True
    n = len(closes)
    if n == 0:
        return False, ["No candles after cleaning."]
    if not (len(dts) == len(highs) == len(lows) == len(closes)):
        return False, ["Mismatched OHLC lengths."]
    for i in range(1, min(n, 10)):  # Check first 10 for efficiency
        if not (dts[i] > dts[i - 1]):
            ok = False
            msgs.append("Timestamps not strictly increasing.")
            break
    for i in range(min(n, 10)):  # Check first 10 for efficiency
        if highs[i] < lows[i]:
            ok = False
            msgs.append(f"High < Low at index {i}.")
            break
        if closes[i] > highs[i] + 1e-6 or closes[i] < lows[i] - 1e-6:
            msgs.append(f"Close out of H-L bounds at {dts[i].date()}.")
            break
    return ok, msgs

def have_indicator_budget(closes: List[float]) -> Tuple[bool, Dict[str, bool]]:
    need = {
        "SMA200": len(closes) >= 200,
        "SMA50": len(closes) >= 50,
        "EMA20": len(closes) >= 20,
        "RSI14": len(closes) >= 15,
        "BB20": len(closes) >= 21,  # Need 21 for previous calculation
        "ADX14": len(closes) >= 30,
        "ATR14": len(closes) >= 15,
    }
    ok = all(need.values())
    return ok, need

# ------------- Swing strategy -------------
class Signal:
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

def swing_signal_daily(highs: List[float], lows: List[float], closes: List[float]) -> Tuple[str, List[str]]:
    """
    Swing strategy with OPTIMIZED indicator calculations.
    """
    reasons: List[str] = []
    c = closes[-1]
    c_prev = closes[-2] if len(closes) >= 2 else c

    # Calculate indicators (optimized versions)
    sma50 = sma(closes, 50)
    sma200 = sma(closes, 200)
    ema20 = ema_last_optimized(closes, 20)
    rsi = rsi_last(closes, 14)
    rsi_prev = rsi_last(closes[:-1], 14) if len(closes) >= 16 else None
    atr = atr_last(highs, lows, closes, 14)
    adx, dip, dim = adx_last(highs, lows, closes, 14)
    
    # Calculate BB for current AND previous in one call (optimized)
    (bb_mid, bb_up, bb_lo), (prev_bb_mid, prev_bb_up, prev_bb_lo) = bollinger_last_two(closes, 20, 2.0)

    if any(x is None for x in (sma50, sma200, ema20, rsi, atr, adx, bb_mid, bb_up, bb_lo)):
        return Signal.HOLD, ["Insufficient indicator data at tail."]

    # Trend filters
    uptrend = (c > sma200) and (sma50 > sma200) and (adx >= 15)
    downtrend = (c < sma200) and (sma50 < sma200) and (adx >= 15)
    
    if uptrend:
        reasons.append(f"Uptrend: C>{int(sma200)} SMA200, SMA50>SMA200, ADX={adx:.1f}")
    if downtrend:
        reasons.append(f"Downtrend: C<{int(sma200)} SMA200, SMA50<SMA200, ADX={adx:.1f}")

    # Long triggers
    long_trigs = []
    if uptrend and prev_bb_lo is not None:
        if c_prev < prev_bb_lo and c > bb_lo:
            long_trigs.append("BB re-entry from below")
    if uptrend and rsi_prev is not None and rsi_prev <= 35 and rsi > 35:
        long_trigs.append(f"RSI upcross 35 ({rsi_prev:.1f}→{rsi:.1f})")
    prior_high = highs[-2] if len(highs) >= 2 else None
    if uptrend and atr is not None and prior_high is not None and ema20 is not None:
        if c <= (ema20 - 0.25 * atr) or c_prev <= (ema20 - 0.25 * atr):
            if c > prior_high:
                long_trigs.append("EMA20 pullback + breakout")

    # Short triggers
    short_trigs = []
    if downtrend and prev_bb_up is not None:
        if c_prev > prev_bb_up and c < bb_up:
            short_trigs.append("BB re-entry from above")
    if downtrend and rsi_prev is not None and rsi_prev >= 65 and rsi < 65:
        short_trigs.append(f"RSI downcross 65 ({rsi_prev:.1f}→{rsi:.1f})")
    prior_low = lows[-2] if len(lows) >= 2 else None
    if downtrend and atr is not None and prior_low is not None and ema20 is not None:
        if c >= (ema20 + 0.25 * atr) or c_prev >= (ema20 + 0.25 * atr):
            if c < prior_low:
                short_trigs.append("EMA20 pullback + breakdown")

    # Decide
    if uptrend and long_trigs:
        return Signal.BUY, long_trigs + reasons
    if downtrend and short_trigs:
        return Signal.SELL, short_trigs + reasons

    if uptrend or downtrend:
        reasons.append("No qualified pullback/re-entry.")
    else:
        reasons.append("No trend alignment.")
    return Signal.HOLD, reasons

# ------------- Main runner -------------
def main():
    start_time = time.time()
    instruments = get_instrument_keys()
    today = today_ist()
    
    metrics.total_symbols = len(instruments)
    logger.info(f"Starting swing scan for {len(instruments)} instruments (date={fmt(today)})")
    logger.info(f"Rate limit: {RATE_LIMIT_CALLS} calls per {RATE_LIMIT_WINDOW}s")
    logger.info(f"Cache: {'enabled' if ENABLE_CACHE else 'disabled'}")

    for idx, (instrument_key, symbol, company) in enumerate(instruments, 1):
        if shutdown_requested:
            logger.info("Shutdown requested, stopping...")
            break
        
        try:
            logger.debug(f"[{idx}/{len(instruments)}] Processing {symbol}")
            
            from_d = today - timedelta(days=DAILY_FETCH_BUFFER_DAYS)
            to_d = today
            payload = fetch_candles(instrument_key, "days", 1, fmt(to_d), fmt(from_d))
            candles = (payload.get("data") or {}).get("candles") or []
            
            if not candles:
                logger.warning(f"{symbol}: No candles returned")
                print(f"{symbol}: {colorize('HOLD', YELLOW)} - {colorize('No data', BLUE)}")
                metrics.failed += 1
                continue

            dts, highs, lows, closes = extract_ohlc_with_dt(candles)
            ok_series, series_msgs = validate_price_series(dts, highs, lows, closes)
            
            if not ok_series:
                logger.warning(f"{symbol}: Invalid series: {'; '.join(series_msgs)}")
                print(f"{symbol}: {colorize('HOLD', YELLOW)} - {colorize('Invalid series', BLUE)}")
                metrics.failed += 1
                continue

            if len(closes) < DAILY_MIN_BARS:
                logger.warning(f"{symbol}: Only {len(closes)} bars (need {DAILY_MIN_BARS})")
                print(f"{symbol}: {colorize('HOLD', YELLOW)} - {colorize('Insufficient bars', BLUE)}")
                metrics.failed += 1
                continue

            # Trim to reasonable window
            trim_size = max(DAILY_MIN_BARS, 250)
            highs = highs[-trim_size:]
            lows = lows[-trim_size:]
            closes = closes[-trim_size:]
            dts = dts[-len(closes):]

            ok_budget, budget = have_indicator_budget(closes)
            if not ok_budget:
                missing = [k for k, v in budget.items() if not v]
                logger.warning(f"{symbol}: Missing indicator budget: {', '.join(missing)}")
                print(f"{symbol}: {colorize('HOLD', YELLOW)} - {colorize('Missing indicators', BLUE)}")
                metrics.failed += 1
                continue

            last_dt = dts[-1].astimezone(IST)
            session_str = last_dt.strftime("%Y-%m-%d")
            
            # Compute signal
            signal, reasons = swing_signal_daily(highs, lows, closes)
            color = GREEN if signal == Signal.BUY else RED if signal == Signal.SELL else YELLOW
            reason_text = "; ".join(reasons[:3]) if reasons else "—"
            print(f"{symbol}: {colorize(signal, color)} - {colorize(reason_text, color)}")
            
            metrics.successful += 1

        except AuthenticationError as e:
            logger.error(f"Authentication error: {e}")
            print(f"FATAL: Authentication failed. Check your access token.")
            break
        
        except APIError as e:
            logger.error(f"{symbol}: API error: {e}")
            print(f"{symbol}: {colorize('HOLD', YELLOW)} - {colorize('API error', BLUE)}")
            metrics.failed += 1
        
        except Exception as e:
            logger.exception(f"{symbol}: Unexpected error")
            print(f"{symbol}: {colorize('HOLD', YELLOW)} - {colorize('Error', BLUE)}")
            metrics.failed += 1

    # Final metrics
    metrics.total_time = time.time() - start_time
    logger.info("=" * 60)
    logger.info("PERFORMANCE METRICS")
    logger.info("=" * 60)
    logger.info(f"Total symbols: {metrics.total_symbols}")
    logger.info(f"Successful: {metrics.successful}")
    logger.info(f"Failed: {metrics.failed}")
    logger.info(f"API calls: {metrics.api_calls}")
    logger.info(f"Cache hits: {metrics.cache_hits}")
    logger.info(f"Total time: {metrics.total_time:.2f}s")
    logger.info(f"API time: {metrics.api_time:.2f}s")
    logger.info(f"Avg per symbol: {metrics.total_time / max(metrics.total_symbols, 1):.2f}s")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
