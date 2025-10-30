import os
import sys
import time
import csv
from typing import List, Tuple, Optional, Set, Dict, Any
from datetime import date, timedelta
from urllib.parse import quote

import requests
from math import fabs

BASE_URL = "https://api.upstox.com/v3/historical-candle"

# Config via env
CSV_PATH = os.getenv("NIFTY500_CSV", "ind_nifty500list.csv")
EXCHANGE_PREFIX = os.getenv("UPSTOX_EXCHANGE", "NSE_EQ")
SERIES_FILTER = {s.strip().upper() for s in os.getenv("SERIES_FILTER", "EQ").split(",") if s.strip()}
LIMIT = int(os.getenv("UPSTOX_LIMIT", "0"))  # 0 = no limit
SLEEP_PER_CALL = float(os.getenv("UPSTOX_SLEEP_PER_CALL", "0.4"))
SLEEP_PER_INSTRUMENT = float(os.getenv("UPSTOX_SLEEP_PER_INSTRUMENT", "0.6"))

# Access token
ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN", "").strip()
if not ACCESS_TOKEN:
    # Keep console clean as requested; but we must exit if missing token
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
        from_date = to_date - timedelta(days=3650)
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

# ---------- Technical indicators (pure Python) ----------

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
        prev = out[i - 1] if out[i - 1] is not None else values[i - 1]  # fallback
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
        gain = max(delta, 0.0)
        loss = max(-delta, 0.0)
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
        atr[i] = ((atr[i - 1] if atr[i - 1] is not None else atr0) * (period - 1) + trs[i]) / period
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
        s0 = sum(src[1:p+1])  # from 1..p inclusive (p periods after first bar)
        out[p] = s0
        for i in range(p + 1, n):
            out[i] = (out[i - 1] - (out[i - 1] / p) + src[i]) if out[i - 1] is not None else src[i]
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
        if denom == 0:
            dx[i] = 0.0
        else:
            dx[i] = 100.0 * (abs((di_plus[i] or 0.0) - (di_minus[i] or 0.0)) / ((di_plus[i] or 0.0) + (di_minus[i] or 0.0)))

    # ADX as Wilder smoothed DX
    adx: List[Optional[float]] = [None] * n
    # first ADX value at index 2p (conventional), but we can seed at p*2 safely if enough data
    start = p * 2
    # initialize ADX as average of DX from p+1..start
    if n > start:
        valid_dx = [d for d in dx[p + 1:start + 1] if d is not None]
        if valid_dx:
            adx[start] = sum(valid_dx) / len(valid_dx)
            for i in range(start + 1, n):
                adx[i] = ((adx[i - 1] if adx[i - 1] is not None else adx[start]) * (p - 1) + (dx[i] or 0.0)) / p

    # Fallback if not enough bars
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

def macd_last(closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    if len(closes) < slow + signal:
        return None, None, None
    ema_fast = ema_series(closes, fast)
    ema_slow = ema_series(closes, slow)
    n = len(closes)
    macd_line: List[Optional[float]] = [None] * n
    for i in range(n):
        if ema_fast[i] is not None and ema_slow[i] is not None:
            macd_line[i] = ema_fast[i] - ema_slow[i]
    # Signal EMA over MACD line (skip Nones)
    macd_vals = [x if x is not None else 0.0 for x in macd_line]
    signal_series = ema_series(macd_vals, signal)
    macd = macd_line[-1]
    sig = signal_series[-1]
    hist = (macd - sig) if (macd is not None and sig is not None) else None
    return macd, sig, hist

def supertrend_last(highs: List[float], lows: List[float], closes: List[float], period: int = 10, multiplier: float = 3.0) -> Tuple[Optional[int], Optional[float]]:
    n = len(closes)
    if n < period + 2:
        return None, None
    atr = atr_series(highs, lows, closes, period)
    bub: List[Optional[float]] = [None] * n
    blb: List[Optional[float]] = [None] * n
    fub: List[Optional[float]] = [None] * n
    flb: List[Optional[float]] = [None] * n
    st: List[Optional[float]] = [None] * n
    trend: List[Optional[int]] = [None] * n

    for i in range(n):
        if atr[i] is None:
            continue
        mprice = (highs[i] + lows[i]) / 2.0
        bub[i] = mprice + multiplier * atr[i]
        blb[i] = mprice - multiplier * atr[i]
        if i == 0 or fub[i - 1] is None or flb[i - 1] is None:
            fub[i] = bub[i]
            flb[i] = blb[i]
            st[i] = flb[i]
            trend[i] = 1 if closes[i] >= (flb[i] or 0) else -1
            continue
        fub[i] = bub[i] if (bub[i] is not None and (bub[i] < (fub[i - 1] or 0) or closes[i - 1] > (fub[i - 1] or 0))) else fub[i - 1]
        flb[i] = blb[i] if (blb[i] is not None and (blb[i] > (flb[i - 1] or 0) or closes[i - 1] < (flb[i - 1] or 0))) else flb[i - 1]
        if st[i - 1] == fub[i - 1]:
            if closes[i] <= (fub[i] or 0):
                st[i] = fub[i]
                trend[i] = -1
            else:
                st[i] = flb[i]
                trend[i] = 1
        else:  # st[i-1] == flb[i-1]
            if closes[i] >= (flb[i] or 0):
                st[i] = flb[i]
                trend[i] = 1
            else:
                st[i] = fub[i]
                trend[i] = -1
    return trend[-1], st[-1]

def ichimoku_last(highs: List[float], lows: List[float], closes: List[float]) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float], Optional[float]]:
    n = len(closes)
    if n < 52:
        return None, None, None, None, None
    def hl_avg(hh: List[float], ll: List[float], period: int, idx: int) -> float:
        window_h = max(hh[idx - period + 1: idx + 1])
        window_l = min(ll[idx - period + 1: idx + 1])
        return (window_h + window_l) / 2.0

    i = n - 1
    tenkan = hl_avg(highs, lows, 9, i) if i >= 8 else None
    kijun = hl_avg(highs, lows, 26, i) if i >= 25 else None
    span_a = ((tenkan or 0.0) + (kijun or 0.0)) / 2.0 if (tenkan is not None and kijun is not None) else None
    span_b = hl_avg(highs, lows, 52, i) if i >= 51 else None
    chikou = closes[i - 26] if i >= 26 else None  # lagging close

    return tenkan, kijun, span_a, span_b, chikou

# ---------- Signal generation ----------

def generate_signal(highs: List[float], lows: List[float], closes: List[float]) -> Tuple[str, List[str], Dict[str, Any]]:
    """
    Generate BUY/SELL/HOLD signal with detailed reasons based on multiple technical indicators.
    Returns: (signal, reasons, indicators_dict)
    """
    reasons = []
    indicators = {}
    buy_signals = 0
    sell_signals = 0
    
    c = closes[-1]
    indicators['current_price'] = c
    
    # Moving Averages
    sma50 = sma(closes, 50)
    sma200 = sma(closes, 200)
    ema20 = ema_last(closes, 20)
    ema50 = ema_last(closes, 50)
    
    indicators['sma50'] = sma50
    indicators['sma200'] = sma200
    indicators['ema20'] = ema20
    indicators['ema50'] = ema50
    
    if sma200 is not None:
        if c > sma200:
            buy_signals += 2
            reasons.append(f"Price ({c:.2f}) above SMA200 ({sma200:.2f}) - Long-term uptrend")
        else:
            sell_signals += 2
            reasons.append(f"Price ({c:.2f}) below SMA200 ({sma200:.2f}) - Long-term downtrend")
    
    if sma50 is not None and sma200 is not None:
        if sma50 > sma200:
            buy_signals += 1
            reasons.append(f"Golden Cross: SMA50 ({sma50:.2f}) > SMA200 ({sma200:.2f})")
        else:
            sell_signals += 1
            reasons.append(f"Death Cross: SMA50 ({sma50:.2f}) < SMA200 ({sma200:.2f})")
    
    if ema20 is not None and ema50 is not None:
        if ema20 > ema50:
            buy_signals += 1
            reasons.append(f"EMA20 ({ema20:.2f}) > EMA50 ({ema50:.2f}) - Short-term bullish")
        else:
            sell_signals += 1
            reasons.append(f"EMA20 ({ema20:.2f}) < EMA50 ({ema50:.2f}) - Short-term bearish")
    
    # RSI
    rsi = rsi_last(closes, 14)
    indicators['rsi'] = rsi
    if rsi is not None:
        if rsi < 30:
            buy_signals += 2
            reasons.append(f"RSI ({rsi:.2f}) oversold (<30) - Strong buy signal")
        elif rsi < 45:
            buy_signals += 1
            reasons.append(f"RSI ({rsi:.2f}) below neutral - Bullish bias")
        elif rsi > 70:
            sell_signals += 2
            reasons.append(f"RSI ({rsi:.2f}) overbought (>70) - Strong sell signal")
        elif rsi > 55:
            sell_signals += 1
            reasons.append(f"RSI ({rsi:.2f}) above neutral - Bearish bias")
    
    # MACD
    macd, sig, hist = macd_last(closes, 12, 26, 9)
    indicators['macd'] = macd
    indicators['macd_signal'] = sig
    indicators['macd_histogram'] = hist
    
    if hist is not None:
        if hist > 0:
            buy_signals += 1
            reasons.append(f"MACD histogram positive ({hist:.4f}) - Bullish momentum")
        else:
            sell_signals += 1
            reasons.append(f"MACD histogram negative ({hist:.4f}) - Bearish momentum")
    
    # ADX and Directional Indicators
    adx, dip, dim = adx_last(highs, lows, closes, 14)
    indicators['adx'] = adx
    indicators['di_plus'] = dip
    indicators['di_minus'] = dim
    
    if adx is not None and dip is not None and dim is not None:
        if adx >= 25:
            if dip > dim:
                buy_signals += 2
                reasons.append(f"Strong trend (ADX={adx:.2f}) with +DI ({dip:.2f}) > -DI ({dim:.2f}) - Strong buy")
            else:
                sell_signals += 2
                reasons.append(f"Strong trend (ADX={adx:.2f}) with -DI ({dim:.2f}) > +DI ({dip:.2f}) - Strong sell")
        elif adx < 20:
            reasons.append(f"Weak trend (ADX={adx:.2f}) - Consolidation phase")
    
    # Bollinger Bands
    mid, upper, lower = bollinger_last(closes, 20, 2.0)
    indicators['bb_mid'] = mid
    indicators['bb_upper'] = upper
    indicators['bb_lower'] = lower
    
    if mid is not None and upper is not None and lower is not None:
        if c < lower:
            buy_signals += 1
            reasons.append(f"Price ({c:.2f}) below lower BB ({lower:.2f}) - Oversold")
        elif c > upper:
            sell_signals += 1
            reasons.append(f"Price ({c:.2f}) above upper BB ({upper:.2f}) - Overbought")
        elif c > mid:
            buy_signals += 0.5
        else:
            sell_signals += 0.5
    
    # SuperTrend
    st_dir, st_val = supertrend_last(highs, lows, closes, 10, 3.0)
    indicators['supertrend_direction'] = st_dir
    indicators['supertrend_value'] = st_val
    
    if st_dir is not None:
        if st_dir > 0:
            buy_signals += 2
            reasons.append(f"SuperTrend bullish (value: {st_val:.2f}) - Strong uptrend")
        else:
            sell_signals += 2
            reasons.append(f"SuperTrend bearish (value: {st_val:.2f}) - Strong downtrend")
    
    # Ichimoku Cloud
    tenkan, kijun, span_a, span_b, chikou = ichimoku_last(highs, lows, closes)
    indicators['ichimoku_tenkan'] = tenkan
    indicators['ichimoku_kijun'] = kijun
    indicators['ichimoku_span_a'] = span_a
    indicators['ichimoku_span_b'] = span_b
    
    if span_a is not None and span_b is not None:
        cloud_top = max(span_a, span_b)
        cloud_bot = min(span_a, span_b)
        if c > cloud_top:
            buy_signals += 1
            reasons.append(f"Price above Ichimoku cloud (top: {cloud_top:.2f}) - Bullish")
        elif c < cloud_bot:
            sell_signals += 1
            reasons.append(f"Price below Ichimoku cloud (bottom: {cloud_bot:.2f}) - Bearish")
        else:
            reasons.append(f"Price inside Ichimoku cloud - Neutral/Consolidation")
    
    # Determine final signal
    total_signals = buy_signals + sell_signals
    if total_signals == 0:
        return "HOLD", ["Insufficient data for signal generation"], indicators
    
    buy_percentage = (buy_signals / total_signals) * 100
    sell_percentage = (sell_signals / total_signals) * 100
    
    if buy_percentage >= 65:
        signal = "BUY"
        reasons.insert(0, f"Overall buy strength: {buy_percentage:.1f}% ({buy_signals} buy vs {sell_signals} sell signals)")
    elif sell_percentage >= 65:
        signal = "SELL"
        reasons.insert(0, f"Overall sell strength: {sell_percentage:.1f}% ({sell_signals} sell vs {buy_signals} buy signals)")
    else:
        signal = "HOLD"
        reasons.insert(0, f"Mixed signals: {buy_percentage:.1f}% buy vs {sell_percentage:.1f}% sell - No clear direction")
    
    return signal, reasons, indicators

def print_signal(symbol: str, company: str, signal: str, reasons: List[str]):
    """Print signal with colored output"""
    if signal == "BUY":
        color = Colors.GREEN
        icon = "📈"
    elif signal == "SELL":
        color = Colors.RED
        icon = "📉"
    else:
        color = Colors.YELLOW
        icon = "➡️"
    
    print(f"\n{Colors.BOLD}{color}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{color}{icon} {symbol} ({company}) - {signal}{Colors.RESET}")
    print(f"{Colors.BOLD}{color}{'='*80}{Colors.RESET}")
    
    for i, reason in enumerate(reasons, 1):
        print(f"{color}{i}. {reason}{Colors.RESET}")
    
    print(f"{Colors.BOLD}{color}{'='*80}{Colors.RESET}\n")

# ---------- Trend scoring ----------

def label_from_score(score: float) -> str:
    if score >= 2.0:
        return "Bullish"
    if score <= -2.0:
        return "Bearish"
    return "Neutral"

def timeframe_key(unit: str, interval: int) -> str:
    if unit == "days" and interval == 1:
        return "D"
    if unit == "hours" and interval == 1:
        return "H1"
    if unit == "minutes" and interval == 15:
        return "M15"
    return f"{unit}{interval}"

def compute_timeframe_score(highs: List[float], lows: List[float], closes: List[float]) -> float:
    # Votes with reasonable weights
    score = 0.0
    c = closes[-1]

    sma50 = sma(closes, 50)
    sma200 = sma(closes, 200)
    ema20 = ema_last(closes, 20)
    ema50 = ema_last(closes, 50)

    if sma200 is not None:
        score += 2.0 if c > sma200 else -2.0
    if sma50 is not None and sma200 is not None:
        score += 1.0 if sma50 > sma200 else -1.0
    if ema20 is not None and ema50 is not None:
        score += 0.5 if ema20 > ema50 else -0.5

    rsi = rsi_last(closes, 14)
    if rsi is not None:
        if rsi >= 55:
            score += 0.5
        elif rsi <= 45:
            score -= 0.5

    macd, sig, hist = macd_last(closes, 12, 26, 9)
    if hist is not None:
        score += 0.75 if hist > 0 else -0.75

    adx, dip, dim = adx_last(highs, lows, closes, 14)
    if adx is not None and dip is not None and dim is not None:
        if adx >= 20:
            score += 1.0 if dip > dim else -1.0
        elif adx <= 15:
            # weak trend, nudge toward neutral
            score *= 0.9

    mid, upper, lower = bollinger_last(closes, 20, 2.0)
    if mid is not None:
        score += 0.25 if c > mid else -0.25

    st_dir, _ = supertrend_last(highs, lows, closes, 10, 3.0)
    if st_dir is not None:
        score += 1.0 if st_dir > 0 else -1.0

    tenkan, kijun, span_a, span_b, _ = ichimoku_last(highs, lows, closes)
    if span_a is not None and span_b is not None:
        cloud_top = max(span_a, span_b)
        cloud_bot = min(span_a, span_b)
        if c > cloud_top:
            score += 1.0
        elif c < cloud_bot:
            score -= 1.0
        # inside cloud -> no vote

    return score

def extract_ohlc(candles: List[List[Any]]) -> Tuple[List[float], List[float], List[float]]:
    # Ensure ascending by timestamp
    candles = sorted(candles, key=lambda x: x[0])
    highs = [float(x[2]) for x in candles]
    lows = [float(x[3]) for x in candles]
    closes = [float(x[4]) for x in candles]
    return highs, lows, closes

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
        # Symbol shown as last token after '|' (ISIN) when using env
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
    print(f"{Colors.BOLD}{Colors.CYAN}Trading Signal Analysis for {today}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}Total instruments: {len(instruments)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}\n")

    for (instrument_key, symbol, company) in instruments:
        try:
            # Fetch daily data for signal generation
            unit, interval = "days", 1
            from_date, to_date = bounded_date_range_for(unit, interval, today)
            payload = fetch_candles(instrument_key, unit, interval, to_date, from_date)
            candles = (payload.get("data") or {}).get("candles") or []
            
            if not candles or len(candles) < 200:
                print(f"{Colors.YELLOW}⚠️  {symbol} ({company}): Insufficient data (only {len(candles)} bars){Colors.RESET}\n")
                time.sleep(SLEEP_PER_CALL)
                continue
            
            highs, lows, closes = extract_ohlc(candles)
            signal, reasons, indicators = generate_signal(highs, lows, closes)
            print_signal(symbol, company, signal, reasons)
            
            time.sleep(SLEEP_PER_INSTRUMENT)
            
        except Exception as e:
            print(f"{Colors.RED}❌ Error processing {symbol} ({company}): {str(e)}{Colors.RESET}\n")
            time.sleep(SLEEP_PER_CALL)

    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}Analysis completed!{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}\n")

if __name__ == "__main__":
    main()
