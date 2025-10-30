#!/usr/bin/env python3
"""
Robust daily swing-signal generator using Upstox historical candles.

Highlights
- Fetches historical data up to today (last available session).
- Cleans and validates data (timestamps, NaNs, duplicates, non-positive prices).
- Verifies indicator prerequisites per symbol and logs sufficiency.
- Implements a well-known swing strategy:
  Trend filter + Pullback + Re-entry/confirmation
  - Longs only in uptrends (Close > SMA200 and SMA50 > SMA200, ADX >= 15)
  - Shorts only in downtrends (Close < SMA200 and SMA50 < SMA200, ADX >= 15)
  - Entry triggers:
    1) Bollinger Band Re-entry: previous close outside band and today closes back inside (fade/reversion)
    2) RSI(14) extreme reversal: RSI crosses back from <=35 (long) or >=65 (short)
    3) EMA20 pullback confirmation with minor ATR threshold

- Produces BUY / SELL / HOLD with concise colored reasons.
- Uses environment variables to configure tokens and universe.

Environment
- UPSTOX_ACCESS_TOKEN: required
- NIFTY500_CSV: path to CSV with columns: "Company Name", "Symbol", "Series", "ISIN Code"
- UPSTOX_EXCHANGE: default "NSE_EQ"
- SERIES_FILTER: default "EQ"
- UPSTOX_LIMIT: integer cap on number of instruments (0 = no limit)
- SLEEP_PER_CALL, SLEEP_PER_INSTRUMENT

Usage
  python upstox_swing_signals.py
"""
import os
import sys
import csv
import time
import math
import logging
from typing import List, Tuple, Optional, Set, Dict, Any
from datetime import datetime, date, timedelta, timezone
from urllib.parse import quote

import requests

# ------------- Logging -------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("swing")

# ------------- Upstox API config -------------
BASE_URL = "https://api.upstox.com/v3/historical-candle"

CSV_PATH = os.getenv("NIFTY500_CSV", "ind_nifty500list.csv")
EXCHANGE_PREFIX = os.getenv("UPSTOX_EXCHANGE", "NSE_EQ")
SERIES_FILTER = {s.strip().upper() for s in os.getenv("SERIES_FILTER", "EQ").split(",") if s.strip()}
LIMIT = int(os.getenv("UPSTOX_LIMIT", "0"))  # 0 = no limit
SLEEP_PER_CALL = float(os.getenv("SLEEP_PER_CALL", "0.35"))
SLEEP_PER_INSTRUMENT = float(os.getenv("SLEEP_PER_INSTRUMENT", "0.5"))

# Fetch window for daily bars
DAILY_MIN_BARS = int(os.getenv("DAILY_MIN_BARS", "250"))   # for indicator stability
DAILY_FETCH_BUFFER_DAYS = int(os.getenv("DAILY_FETCH_BUFFER_DAYS", "550"))  # more to ensure >= 250 valid bars

# Access token
ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN", "").strip()
if not ACCESS_TOKEN:
    logger.error("Please set the UPSTOX_ACCESS_TOKEN environment variable.")
    sys.exit(1)

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Authorization": f"Bearer {ACCESS_TOKEN}",
}

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

# ------------- API helpers -------------
def fetch_candles(instrument_key: str, unit: str, interval: int, to_date: str, from_date: str, retries: int = 2):
    """
    Upstox path order: .../{unit}/{interval}/{to_date}/{from_date}
    """
    encoded_instrument_key = quote(instrument_key, safe="")
    url = f"{BASE_URL}/{encoded_instrument_key}/{unit}/{interval}/{to_date}/{from_date}"
    last_err = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=60)
            if resp.status_code == 200:
                return resp.json()
            last_err = RuntimeError(f"HTTP {resp.status_code}: {resp.text}")
            # backoff only for rate-limits/transient
            if resp.status_code in (429, 500, 502, 503, 504):
                sleep_s = 0.6 * (attempt + 1)
                logger.warning("Transient HTTP %s for %s; retrying in %.1fs", resp.status_code, instrument_key, sleep_s)
                time.sleep(sleep_s)
                continue
            break
        except Exception as e:
            last_err = e
            sleep_s = 0.6 * (attempt + 1)
            logger.warning("Fetch error %s for %s; retrying in %.1fs", type(e).__name__, instrument_key, sleep_s)
            time.sleep(sleep_s)
    raise last_err if last_err else RuntimeError("Unknown fetch error")

def extract_ohlc_with_dt(candles: List[List[Any]]) -> Tuple[List[datetime], List[float], List[float], List[float]]:
    """
    Cleans rows, enforces monotonic timestamps, dedupes, validates positivity and finiteness.
    """
    clean = []
    for x in candles:
        # Expected: [timestamp, open, high, low, close, ...]
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
            # swap if data glitch
            h, l = max(h, l), min(h, l)
        clean.append((dt, h, l, c))

    if not clean:
        return [], [], [], []

    # sort and dedupe by dt (keep latest occurrence)
    clean.sort(key=lambda z: z[0])
    dedup: Dict[datetime, Tuple[float, float, float]] = {}
    for dt, h, l, c in clean:
        dedup[dt] = (h, l, c)
    dts = sorted(dedup.keys())
    highs = [dedup[dt][0] for dt in dts]
    lows = [dedup[dt][1] for dt in dts]
    closes = [dedup[dt][2] for dt in dts]
    return dts, highs, lows, closes

# ------------- Indicators (pure Python, Wilder-correct) -------------
def sma(series: List[float], period: int) -> Optional[float]:
    if len(series) < period:
        return None
    return sum(series[-period:]) / period

def ema_series(values: List[float], period: int) -> List[Optional[float]]:
    n = len(values)
    out: List[Optional[float]] = [None] * n
    if n < period or period <= 0:
        return out
    sma0 = sum(values[:period]) / period
    out[period - 1] = sma0
    k = 2.0 / (period + 1.0)
    for i in range(period, n):
        prev = out[i - 1] if out[i - 1] is not None else values[i - 1]
        out[i] = (values[i] - prev) * k + prev
    return out

def ema_last(values: List[float], period: int) -> Optional[float]:
    es = ema_series(values, period)
    return es[-1]

def rsi_last(closes: List[float], period: int = 14) -> Optional[float]:
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
    return max(h - l, abs(h - prev_close), abs(l - prev_close))

def atr_series(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> List[Optional[float]]:
    n = len(closes)
    atr: List[Optional[float]] = [None] * n
    if n == 0:
        return atr
    trs: List[float] = [0.0] * n
    trs[0] = highs[0] - lows[0]
    for i in range(1, n):
        trs[i] = true_range(highs[i], lows[i], closes[i - 1])
    if n < period:
        return atr
    atr0 = sum(trs[:period]) / period
    atr[period - 1] = atr0
    for i in range(period, n):
        prev = atr[i - 1] if atr[i - 1] is not None else atr0
        atr[i] = ((prev * (period - 1)) + trs[i]) / period
    return atr

def adx_last(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    n = len(closes)
    if n < period + 1:
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

    # Wilder smoothing
    def wild_smooth(src: List[float], p: int) -> List[Optional[float]]:
        out: List[Optional[float]] = [None] * n
        if n < p:
            return out
        s0 = sum(src[1:p+1])  # from bar 1 to p inclusive
        out[p] = s0
        for i in range(p + 1, n):
            prev = out[i - 1] if out[i - 1] is not None else s0
            out[i] = (prev - (prev / p) + src[i])
        return out

    p = period
    trn = wild_smooth(trs, p)
    plus_dmn = wild_smooth(plus_dm, p)
    minus_dmn = wild_smooth(minus_dm, p)

    di_plus: List[Optional[float]] = [None] * n
    di_minus: List[Optional[float]] = [None] * n
    dx: List[Optional[float]] = [None] * n
    for i in range(n):
        if trn[i] is None or trn[i] == 0:
            continue
        di_plus[i] = 100.0 * ((plus_dmn[i] or 0.0) / trn[i])
        di_minus[i] = 100.0 * ((minus_dmn[i] or 0.0) / trn[i])
        denom = (abs((di_plus[i] or 0.0) + (di_minus[i] or 0.0)))
        dx[i] = 0.0 if denom == 0 else 100.0 * (abs((di_plus[i] or 0.0) - (di_minus[i] or 0.0)) / ((di_plus[i] or 0.0) + (di_minus[i] or 0.0)))

    # ADX smoothing of DX
    adx: List[Optional[float]] = [None] * n
    start = p * 2
    if n > start:
        valid_dx = [d for d in dx[p + 1:start + 1] if d is not None]
        if valid_dx:
            adx[start] = sum(valid_dx) / len(valid_dx)
            for i in range(start + 1, n):
                prev = adx[i - 1] if adx[i - 1] is not None else adx[start]
                adx[i] = ((prev * (p - 1)) + (dx[i] or 0.0)) / p

    last_idx = n - 1
    return (adx[last_idx] if last_idx < len(adx) else None,
            di_plus[last_idx] if last_idx < len(di_plus) else None,
            di_minus[last_idx] if last_idx < len(di_minus) else None)

def stddev(values: List[float]) -> float:
    n = len(values)
    if n == 0:
        return 0.0
    m = sum(values) / n
    var = sum((x - m) ** 2 for x in values) / n
    return var ** 0.5

def bollinger_last(closes: List[float], period: int = 20, mult: float = 2.0) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    if len(closes) < period:
        return None, None, None
    window = closes[-period:]
    mid = sum(window) / period
    dev = stddev(window)
    upper = mid + mult * dev
    lower = mid - mult * dev
    return mid, upper, lower

# ------------- Color helpers -------------
RESET = "\033[0m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
BOLD = "\033[1m"

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
    # Fallback IOC
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
    # monotonic check (already sorted, but ensure strictly increasing)
    for i in range(1, n):
        if not (dts[i] > dts[i - 1]):
            ok = False
            msgs.append("Timestamps not strictly increasing.")
            break
    # value checks
    for i in range(n):
        if highs[i] < lows[i]:
            ok = False
            msgs.append(f"High < Low at index {i}.")
            break
        if closes[i] > highs[i] + 1e-6 or closes[i] < lows[i] - 1e-6:
            # sometimes vendors have HLCC with rounding; keep as warning
            msgs.append(f"Close out of H-L bounds at {dts[i].date()}.")
            break
    return ok, msgs

def have_indicator_budget(closes: List[float]) -> Tuple[bool, Dict[str, bool]]:
    need = {
        "SMA200": len(closes) >= 200,
        "SMA50": len(closes) >= 50,
        "EMA20": len(closes) >= 20,
        "RSI14": len(closes) >= 15,
        "BB20": len(closes) >= 20,
        "ADX14": len(closes) >= 30,  # allow Wilder seed (~2*period)
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
    Well-known swing approach: trend filter + pullback + re-entry confirmation.
    """
    reasons: List[str] = []
    c = closes[-1]
    c_prev = closes[-2] if len(closes) >= 2 else c

    sma50 = sma(closes, 50)
    sma200 = sma(closes, 200)
    ema20 = ema_last(closes, 20)
    rsi = rsi_last(closes, 14)
    atrs = atr_series(highs, lows, closes, 14)
    atr = atrs[-1] if atrs and atrs[-1] is not None else None
    adx, dip, dim = adx_last(highs, lows, closes, 14)
    bb_mid, bb_up, bb_lo = bollinger_last(closes, 20, 2.0)

    if any(x is None for x in (sma50, sma200, ema20, rsi, atr, adx, bb_mid, bb_up, bb_lo)):
        return Signal.HOLD, ["Insufficient indicator data at tail."]

    # Trend filters
    uptrend = (c > sma200) and (sma50 > sma200) and (adx is not None and adx >= 15)
    downtrend = (c < sma200) and (sma50 < sma200) and (adx is not None and adx >= 15)
    if uptrend:
        reasons.append(f"Uptrend: Close>{int(sma200)} SMA200 and SMA50>SMA200; ADX={adx:.1f}")
    if downtrend:
        reasons.append(f"Downtrend: Close<{int(sma200)} SMA200 and SMA50<SMA200; ADX={adx:.1f}")

    # Pullback + confirmation LONG
    long_trigs = []
    # 1) BB re-entry (yday below band, today back above)
    prev_bb_mid, prev_bb_up, prev_bb_lo = bollinger_last(closes[:-1], 20, 2.0) if len(closes) >= 21 else (None, None, None)
    if uptrend and prev_bb_lo is not None:
        if c_prev < prev_bb_lo and c > (bb_lo or -1e9):
            long_trigs.append("BB re-entry from below")
    # 2) RSI reversion
    rsi_prev = rsi_last(closes[:-1], 14) if len(closes) >= 16 else None
    if uptrend and rsi_prev is not None and rsi_prev <= 35 and rsi > 35:
        long_trigs.append(f"RSI upcross 35 (prev={rsi_prev:.1f}→{rsi:.1f})")
    # 3) EMA20 pullback with ATR cushion and bullish close over prior high
    prior_high = highs[-2] if len(highs) >= 2 else None
    if uptrend and atr is not None and prior_high is not None and ema20 is not None:
        if c <= (ema20 - 0.25 * atr) or c_prev <= (ema20 - 0.25 * atr):
            if c > prior_high:
                long_trigs.append("EMA20 pullback + breakout > prior high")

    # Pullback + confirmation SHORT
    short_trigs = []
    if downtrend and prev_bb_up is not None:
        if c_prev > prev_bb_up and c < (bb_up or 1e9):
            short_trigs.append("BB re-entry from above")
    if downtrend and rsi_prev is not None and rsi_prev >= 65 and rsi < 65:
        short_trigs.append(f"RSI downcross 65 (prev={rsi_prev:.1f}→{rsi:.1f})")
    if downtrend and atr is not None and prior_high is not None and ema20 is not None:
        prior_low = lows[-2] if len(lows) >= 2 else None
        if prior_low is not None:
            if c >= (ema20 + 0.25 * atr) or c_prev >= (ema20 + 0.25 * atr):
                if c < prior_low:
                    short_trigs.append("EMA20 pullback + breakdown < prior low")

    # Decide
    if uptrend and len(long_trigs) > 0:
        return Signal.BUY, long_trigs + reasons
    if downtrend and len(short_trigs) > 0:
        return Signal.SELL, short_trigs + reasons

    # If no signals, provide context
    if uptrend or downtrend:
        reasons.append("No qualified pullback/re-entry today.")
    else:
        reasons.append("No trend alignment (filter not satisfied).")
    return Signal.HOLD, reasons

# ------------- Runner -------------
def main():
    instruments = get_instrument_keys()
    today = today_ist()
    logger.info("Starting swing scan for %d instruments (target date=%s)", len(instruments), fmt(today))

    for (instrument_key, symbol, company) in instruments:
        try:
            # Fetch daily data covering necessary bars
            from_d = today - timedelta(days=DAILY_FETCH_BUFFER_DAYS)
            to_d = today
            payload = fetch_candles(instrument_key, "days", 1, fmt(to_d), fmt(from_d))
            candles = (payload.get("data") or {}).get("candles") or []
            if not candles:
                logger.warning("%s: No candles returned.", symbol)
                print(f"{symbol}: {colorize('HOLD', YELLOW)} - {colorize('No data', BLUE)}")
                time.sleep(SLEEP_PER_INSTRUMENT); continue

            dts, highs, lows, closes = extract_ohlc_with_dt(candles)
            ok_series, series_msgs = validate_price_series(dts, highs, lows, closes)
            if not ok_series:
                logger.warning("%s: Bad series: %s", symbol, "; ".join(series_msgs))
                print(f"{symbol}: {colorize('HOLD', YELLOW)} - {colorize('Invalid series', BLUE)}")
                time.sleep(SLEEP_PER_INSTRUMENT); continue

            # Ensure we have at least DAILY_MIN_BARS
            if len(closes) < DAILY_MIN_BARS:
                logger.warning("%s: Only %d bars available (<%d).", symbol, len(closes), DAILY_MIN_BARS)
                print(f"{symbol}: {colorize('HOLD', YELLOW)} - {colorize('Insufficient bars', BLUE)}")
                time.sleep(SLEEP_PER_INSTRUMENT); continue

            # Trim to last N bars for stability
            highs = highs[-max(DAILY_MIN_BARS, 220):]
            lows = lows[-max(DAILY_MIN_BARS, 220):]
            closes = closes[-max(DAILY_MIN_BARS, 220):]
            dts = dts[-len(closes):]

            # Indicator budget check
            ok_budget, budget = have_indicator_budget(closes)
            missing = [k for k, v in budget.items() if not v]
            if not ok_budget:
                logger.warning("%s: Missing indicator budget for %s", symbol, ", ".join(missing))
                print(f"{symbol}: {colorize('HOLD', YELLOW)} - {colorize('Missing indicator budget', BLUE)}")
                time.sleep(SLEEP_PER_INSTRUMENT); continue

            # Info logging on most recent session used
            last_dt = dts[-1].astimezone(IST)
            session_str = last_dt.strftime("%Y-%m-%d")
            if last_dt.date() != today:
                logger.info("%s: Using last available session %s (today candle absent).", symbol, session_str)
            else:
                logger.info("%s: Using today's session %s.", symbol, session_str)

            # Compute signal
            signal, reasons = swing_signal_daily(highs, lows, closes)
            color = GREEN if signal == Signal.BUY else RED if signal == Signal.SELL else YELLOW
            reason_text = "; ".join(reasons[:4]) if reasons else "—"
            print(f"{symbol}: {colorize(signal, color)} - {colorize(reason_text, color)}")

            time.sleep(SLEEP_PER_INSTRUMENT)

        except Exception as e:
            logger.exception("%s: Unhandled error", symbol)
            print(f"{symbol}: {colorize('HOLD', YELLOW)} - {colorize('Error fetching/calculating', BLUE)}")
            time.sleep(SLEEP_PER_INSTRUMENT)

if __name__ == "__main__":
    main()
