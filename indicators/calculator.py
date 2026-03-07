"""
GoldSignalBot – indicators/calculator.py
==========================================
Computes all technical indicators required by the V1 strategy:
  - EMA(9)  & EMA(21) : Exponential Moving Averages for trend direction
  - RSI(14)            : Relative Strength Index for momentum filter
  - ATR(14)            : Average True Range for volatility measurement
  - ATR_avg(20)        : 20-period rolling mean of ATR for expansion check

Uses pandas_ta for clean, vectorized calculations. All indicators are appended
as new columns to the input DataFrame and returned.

Expected input columns: open, high, low, close, volume
Expected index: UTC-aware DatetimeIndex
"""

import logging
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ─── Attempt to import pandas_ta ─────────────────────────────────────────────
try:
    import pandas_ta as ta
    _PANDAS_TA_AVAILABLE = True
except ImportError:
    _PANDAS_TA_AVAILABLE = False
    logger.warning(
        "pandas_ta not found – falling back to manual indicator calculations. "
        "Install it with: pip install pandas_ta"
    )


# ─── Public function ─────────────────────────────────────────────────────────

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute all indicators and append as columns to df.

    Args:
        df: DataFrame with columns open, high, low, close, volume and UTC DatetimeIndex.
            Must have at least 30 rows for stable calculations.

    Returns:
        Same DataFrame with these additional columns:
          EMA_9, EMA_21, RSI_14, ATR_14, ATR_avg_20,
          EMA_cross  (1 = bullish cross, -1 = bearish cross, 0 = no cross)
    """
    if df is None or len(df) < 21:
        raise ValueError(
            f"DataFrame too short ({len(df) if df is not None else 0} rows). "
            "Need at least 21 rows for reliable EMA21 calculations."
        )

    df = df.copy()  # Do not mutate the caller's DataFrame

    required_cols = {"open", "high", "low", "close"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"DataFrame is missing required columns: {missing}")

    if _PANDAS_TA_AVAILABLE:
        df = _compute_with_pandas_ta(df)
    else:
        df = _compute_manually(df)

    df = _compute_ema_crossover(df)
    df = _compute_atr_average(df)

    # Drop rows where any key indicator is NaN (warm-up period)
    df = df.dropna(subset=["EMA_9", "EMA_21", "RSI_14", "ATR_14"])

    logger.debug(
        "Indicators computed: %d rows. Columns: %s",
        len(df),
        [c for c in df.columns if c not in ("open", "high", "low", "close", "volume")],
    )
    return df


# ─── pandas_ta Implementation ────────────────────────────────────────────────

def _compute_with_pandas_ta(df: pd.DataFrame) -> pd.DataFrame:
    """Compute EMA, RSI, ATR using pandas_ta (preferred method)."""
    import pandas_ta as ta  # re-import inside to satisfy linters

    # EMA 9 and 21


    df["EMA_9"]  = ta.ema(df["close"], length=9)
    df["EMA_21"] = ta.ema(df["close"], length=21)

    # RSI 14
    df["RSI_14"] = ta.rsi(df["close"], length=14)

    # ATR 14 (requires high, low, close)
    df["ATR_14"] = ta.atr(df["high"], df["low"], df["close"], length=14)

    return df


# ─── Manual Implementation (fallback) ────────────────────────────────────────

def _compute_manually(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute EMA, RSI, ATR manually using pure pandas.
    Used as fallback if pandas_ta is not installed.
    """
    # ── EMA ──────────────────────────────────────────────────────────────────
    df["EMA_9"]  = df["close"].ewm(span=9,  adjust=False).mean()
    df["EMA_21"] = df["close"].ewm(span=21, adjust=False).mean()

    # ── RSI (Wilder's smoothing) ──────────────────────────────────────────────
    delta = df["close"].diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)

    # Use exponential moving average with alpha=1/14 (Wilder's method)
    avg_gain = gain.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, float("nan"))
    df["RSI_14"] = 100 - (100 / (1 + rs))

    # ── ATR ───────────────────────────────────────────────────────────────────
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"]  - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    # Wilder's smoothed ATR
    df["ATR_14"] = tr.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()

    return df


# ─── Crossover Detection ─────────────────────────────────────────────────────

def _compute_ema_crossover(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect EMA crossover events:
      EMA_cross =  1 → bullish crossover (EMA9 crossed above EMA21 this candle)
      EMA_cross = -1 → bearish crossover (EMA9 crossed below EMA21 this candle)
      EMA_cross =  0 → no crossover

    A crossover is defined as: previous candle EMA9 was BELOW/ABOVE EMA21,
    and current candle EMA9 is ABOVE/BELOW EMA21 respectively.
    """
    ema9  = df["EMA_9"]
    ema21 = df["EMA_21"]

    prev_above = (ema9.shift(1) > ema21.shift(1))  # was EMA9 above EMA21 last bar?
    curr_above = (ema9 > ema21)                     # is EMA9 above EMA21 now?

    bullish_cross = (~prev_above) & curr_above       # was below, now above
    bearish_cross = prev_above   & (~curr_above)     # was above, now below

    df["EMA_cross"] = 0
    df.loc[bullish_cross, "EMA_cross"] = 1
    df.loc[bearish_cross, "EMA_cross"] = -1

    return df


# ─── ATR Average ─────────────────────────────────────────────────────────────

def _compute_atr_average(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """
    Compute a rolling mean of ATR_14 over the last `window` bars.
    Used to detect ATR expansion (current ATR > average ATR → elevated volatility).
    """
    df["ATR_avg_20"] = df["ATR_14"].rolling(window=window).mean()
    return df


# ─── CLI self-test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import logging
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
    from data.fetcher import DataFetcher

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] – %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    print("=" * 60)
    print("  GoldSignalBot – Indicator Calculator Self-Test")
    print("=" * 60)

    fetcher = DataFetcher()
    raw_df  = fetcher.fetch(lookback_candles=100)
    df      = compute_indicators(raw_df)

    indicator_cols = ["EMA_9", "EMA_21", "RSI_14", "ATR_14", "ATR_avg_20", "EMA_cross"]
    print(f"\n✅ Indicators computed. Shape: {df.shape}")
    print(f"\nLast 5 rows:\n{df[indicator_cols].tail(5).to_string()}\n")
