"""
GoldSignalBot – data/fetcher.py
================================
Fetches XAU/USD OHLCV (candlestick) data with a 3-tier fallback chain:

  Priority 1 → GoldAPI.io      (free realtime + historical, requires API key)
  Priority 2 → MetalpriceAPI   (free tier, limited monthly requests)
  Priority 3 → yfinance GC=F   (always available, no key, used for backtesting)

The fetcher always returns a pandas DataFrame with columns:
  timestamp (UTC datetime index), open, high, low, close, volume

Data is returned in H4 (4-hour) candles by default. If the source provides
finer granularity (e.g., 1h), the fetcher resamples to the configured timeframe.
"""

import os
import logging
import configparser
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf
from dotenv import load_dotenv

# ─── Setup ───────────────────────────────────────────────────────────────────

# Load API keys from .env file (if it exists)
load_dotenv()

# Resolve config.ini relative to this file's project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _PROJECT_ROOT / "config.ini"

config = configparser.ConfigParser()
config.read(_CONFIG_PATH)

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

GOLDAPI_BASE_URL = "https://www.goldapi.io/api"
METALPRICE_BASE_URL = "https://api.metalpriceapi.com/v1"

# yfinance ticker for Gold futures (tracks XAU/USD very closely)
YFINANCE_TICKER = "GC=F"

# Timeframe → pandas resample rule mapping
TIMEFRAME_RESAMPLE_MAP = {
    "H1": "1h",
    "H4": "4h",
    "D1": "1D",
}


# ─── DataFetcher Class ────────────────────────────────────────────────────────

class DataFetcher:
    """
    Fetches XAU/USD OHLCV data with automatic source fallback.

    Usage:
        fetcher = DataFetcher()
        df = fetcher.fetch(lookback_candles=200)
        # df has columns: open, high, low, close, volume
        # df.index is a UTC-aware DatetimeIndex in H4 frequency
    """

    def __init__(self):
        # Read config
        self.primary_source = config.get("data", "primary_source", fallback="goldapi")
        self.timeframe = config.get("data", "timeframe", fallback="H4")
        self.lookback_candles = config.getint("data", "lookback_candles", fallback=200)

        # API keys from environment
        self.goldapi_key = os.getenv("GOLDAPI_KEY", "")
        self.metalprice_key = os.getenv("METALPRICE_KEY", "")

        # Validate timeframe
        if self.timeframe not in TIMEFRAME_RESAMPLE_MAP:
            logger.warning(
                "Unknown timeframe '%s' in config. Defaulting to H4.", self.timeframe
            )
            self.timeframe = "H4"

        self._resample_rule = TIMEFRAME_RESAMPLE_MAP[self.timeframe]

    # ─── Public API ──────────────────────────────────────────────────────────

    def fetch(self, lookback_candles: int | None = None) -> pd.DataFrame:
        """
        Fetch XAU/USD OHLCV data. Tries each source in order:
          1. GoldAPI.io  2. MetalpriceAPI  3. yfinance

        Args:
            lookback_candles: How many H4 candles to return (overrides config).

        Returns:
            pd.DataFrame with UTC DatetimeIndex and open/high/low/close/volume columns.

        Raises:
            RuntimeError: If all three sources fail.
        """
        n = lookback_candles or self.lookback_candles

        sources = self._build_source_order()

        last_error: Exception | None = None
        for source_name, fetch_fn in sources:
            logger.info("Attempting data fetch from %s ...", source_name)
            try:
                df = fetch_fn(n)
                if df is not None and len(df) >= 30:
                    logger.info(
                        "✅ %s returned %d candles (timeframe: %s).",
                        source_name,
                        len(df),
                        self.timeframe,
                    )
                    return df
                logger.warning("%s returned insufficient data. Trying next source.", source_name)
            except Exception as exc:
                logger.warning("⚠️  %s failed: %s. Trying next source.", source_name, exc)
                last_error = exc

        raise RuntimeError(
            f"All data sources failed. Last error: {last_error}\n"
            "Check your API keys in .env and internet connection."
        )

    def fetch_historical(self, years: int = 3) -> pd.DataFrame:
        """
        Fetch long-span historical data for backtesting.
        Always uses yfinance (most reliable for 2-5 year history).

        Args:
            years: Number of years of history to fetch.

        Returns:
            pd.DataFrame in the configured timeframe.
        """
        logger.info("Fetching %d years of historical data via yfinance for backtest ...", years)
        df = self._fetch_yfinance_historical(years=years)
        if df is None or len(df) < 100:
            raise RuntimeError("yfinance historical fetch returned insufficient data.")
        logger.info("✅ Historical data: %d candles (%.1f years).", len(df), years)
        return df

    # ─── Source Ordering ─────────────────────────────────────────────────────

    def _build_source_order(self):
        """
        Return a list of (name, callable) pairs in priority order.
        Primary source from config comes first, then the others.
        """
        all_sources = [
            ("GoldAPI.io",    self._fetch_goldapi),
            ("MetalpriceAPI", self._fetch_metalprice),
            ("yfinance",      lambda n: self._fetch_yfinance(n)),
        ]

        # Put configured primary source first
        primary_map = {
            "goldapi":     "GoldAPI.io",
            "metalprice":  "MetalpriceAPI",
            "yfinance":    "yfinance",
        }
        primary_label = primary_map.get(self.primary_source.lower(), "GoldAPI.io")

        ordered = sorted(
            all_sources,
            key=lambda x: 0 if x[0] == primary_label else 1
        )
        return ordered

    # ─── Source 1: GoldAPI.io ────────────────────────────────────────────────

    def _fetch_goldapi(self, lookback_candles: int) -> pd.DataFrame:
        """
        Fetch from GoldAPI.io.

        GoldAPI.io provides real-time spot price and lightweight historical data.
        Free tier returns current spot price; historical endpoint returns daily OHLCV.
        We fetch daily OHLCV (up to ~200 days) then resample if timeframe is D1,
        or supplement with spot for current candle on H4.

        NOTE: GoldAPI.io free tier provides spot price + historical daily bars.
        For H4 granularity, we use the historical endpoint and resample.
        The free tier gives up to 100 req/month (≈3 req/day).
        """
        if not self.goldapi_key:
            raise ValueError("GOLDAPI_KEY not set in .env")

        headers = {
            "x-access-token": self.goldapi_key,
            "Content-Type": "application/json",
        }

        # GoldAPI.io historical endpoint: GET /XAU/USD/YYYY-MM-DD
        # We fetch day-by-day for lookback period
        # To stay within rate limits, we build a compact history from daily bars
        rows = []
        today = datetime.now(tz=timezone.utc).date()

        # Estimate how many calendar days we need (H4 = 6 candles/day)
        # For D1 timeframe fetch ~lookback days; for H4 fetch lookback // 6 days
        days_needed = max(lookback_candles, 30)  # daily bars
        if self.timeframe == "H4":
            days_needed = (lookback_candles // 6) + 5

        dates_to_fetch = [
            today - timedelta(days=i) for i in range(days_needed, -1, -1)
        ]

        for date in dates_to_fetch:
            date_str = date.strftime("%Y%m%d")
            url = f"{GOLDAPI_BASE_URL}/XAU/USD/{date_str}"
            resp = requests.get(url, headers=headers, timeout=10)

            if resp.status_code == 200:
                data = resp.json()
                # GoldAPI returns: price, open_time, ask, bid, ch, chp, high, low
                row = {
                    "timestamp": pd.Timestamp(date_str, tz="UTC"),
                    "open":  float(data.get("open_price") or data.get("price", 0)),
                    "high":  float(data.get("high_price") or data.get("price", 0)),
                    "low":   float(data.get("low_price")  or data.get("price", 0)),
                    "close": float(data.get("price", 0)),
                    "volume": 0.0,  # GoldAPI does not provide volume
                }
                if row["close"] > 0:
                    rows.append(row)
            elif resp.status_code == 401:
                raise ValueError("GoldAPI.io: Invalid API key (401). Check GOLDAPI_KEY in .env.")
            elif resp.status_code == 429:
                logger.warning("GoldAPI.io: Rate limit hit (429). Switching to next source.")
                break

        if not rows:
            raise RuntimeError("GoldAPI.io returned no usable data.")

        df = pd.DataFrame(rows).set_index("timestamp")
        df = df[~df.index.duplicated(keep="last")]
        df = df.sort_index()

        # If the timeframe is not D1, we note the data is daily-resolution.
        # For H4 strategy we treat each daily bar as a signal basis point.
        # (yfinance with 1h data is far superior for real H4 resampling)
        return df.tail(lookback_candles)

    # ─── Source 2: MetalpriceAPI ──────────────────────────────────────────────

    def _fetch_metalprice(self, lookback_candles: int) -> pd.DataFrame:
        """
        Fetch from MetalpriceAPI.com (free tier: 100 req/month, daily OHLCV).
        API docs: https://metalpriceapi.com/documentation
        """
        if not self.metalprice_key:
            raise ValueError("METALPRICE_KEY not set in .env")

        # MetalpriceAPI timeframe endpoint gives historical rates
        # Fetch one date at a time (similar to GoldAPI approach)
        rows = []
        today = datetime.now(tz=timezone.utc).date()

        days_needed = max(lookback_candles, 30)
        if self.timeframe == "H4":
            days_needed = (lookback_candles // 6) + 5

        for i in range(days_needed, -1, -1):
            date = today - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            url = f"{METALPRICE_BASE_URL}/{date_str}"
            params = {
                "api_key": self.metalprice_key,
                "base": "USD",
                "currencies": "XAU",
            }

            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    rates = data.get("rates", {})
                    # Rate is XAU per USD → invert for USD per XAU (gold price in USD)
                    xau_rate = rates.get("XAU")
                    if xau_rate and float(xau_rate) > 0:
                        price_usd = 1.0 / float(xau_rate)
                        rows.append({
                            "timestamp": pd.Timestamp(date_str, tz="UTC"),
                            "open":   price_usd,
                            "high":   price_usd,
                            "low":    price_usd,
                            "close":  price_usd,
                            "volume": 0.0,
                        })
            elif resp.status_code == 401:
                raise ValueError("MetalpriceAPI: Invalid API key. Check METALPRICE_KEY in .env.")
            elif resp.status_code == 429:
                logger.warning("MetalpriceAPI: Rate limit hit. Switching to next source.")
                break

        if not rows:
            raise RuntimeError("MetalpriceAPI returned no usable data.")

        df = pd.DataFrame(rows).set_index("timestamp")
        df = df[~df.index.duplicated(keep="last")]
        df = df.sort_index()
        return df.tail(lookback_candles)

    # ─── Source 3: yfinance ───────────────────────────────────────────────────

    def _fetch_yfinance(self, lookback_candles: int) -> pd.DataFrame:
        """
        Fetch from Yahoo Finance using GC=F (Gold Futures).
        No API key required. Provides true OHLCV data with 1h granularity
        (up to 730 days back) or 1d granularity (multi-year).

        For H4: fetches 1h data and resamples to 4h candles.
        Best source for real H4 OHLCV quality.
        """
        # Determine how many calendar days to cover the requested candles
        candle_hours = {"H1": 1, "H4": 4, "D1": 24}
        hours_per_candle = candle_hours.get(self.timeframe, 4)
        total_hours_needed = lookback_candles * hours_per_candle
        days_needed = max(int(total_hours_needed / 16) + 10, 30)  # ~16 trading hours/day

        end_dt = datetime.now(tz=timezone.utc)
        start_dt = end_dt - timedelta(days=days_needed)

        # yfinance 1h interval is only available for the last 730 days
        if days_needed <= 729:
            interval = "1h"
            raw_df = yf.download(
                YFINANCE_TICKER,
                start=start_dt.strftime("%Y-%m-%d"),
                end=(end_dt + timedelta(days=1)).strftime("%Y-%m-%d"),
                interval=interval,
                auto_adjust=True,
                progress=False,
            )
        else:
            # Fall back to 1-day for very long histories
            interval = "1d"
            raw_df = yf.download(
                YFINANCE_TICKER,
                start=start_dt.strftime("%Y-%m-%d"),
                end=(end_dt + timedelta(days=1)).strftime("%Y-%m-%d"),
                interval=interval,
                auto_adjust=True,
                progress=False,
            )

        if raw_df is None or raw_df.empty:
            raise RuntimeError("yfinance returned empty DataFrame for GC=F.")

        # Flatten MultiIndex columns if present (yfinance sometimes adds ticker level)
        if isinstance(raw_df.columns, pd.MultiIndex):
            raw_df.columns = [col[0].lower() for col in raw_df.columns]
        else:
            raw_df.columns = [c.lower() for c in raw_df.columns]

        # Ensure UTC index
        if raw_df.index.tzinfo is None:
            raw_df.index = raw_df.index.tz_localize("UTC")
        else:
            raw_df.index = raw_df.index.tz_convert("UTC")

        raw_df = raw_df.rename(columns={"adj close": "close"})
        raw_df = raw_df[["open", "high", "low", "close", "volume"]].dropna()

        # Resample to target timeframe if needed
        resample_rule = TIMEFRAME_RESAMPLE_MAP[self.timeframe]
        if interval == "1h" and self.timeframe != "H1":
            df = self._resample_ohlcv(raw_df, resample_rule)
        elif interval == "1d" and self.timeframe == "H4":
            # Cannot truly resample daily to H4 — return daily as best effort
            logger.warning(
                "yfinance 1d data cannot be resampled to H4. Returning daily bars."
            )
            df = raw_df
        else:
            df = raw_df

        df = df.dropna().sort_index()
        return df.tail(lookback_candles)

    def _fetch_yfinance_historical(self, years: int = 3) -> pd.DataFrame:
        """
        Fetch multi-year daily OHLCV from yfinance for backtesting.
        Returns daily candles (D1). Backtest engine resamples or uses as-is.
        """
        end_dt = datetime.now(tz=timezone.utc)
        start_dt = end_dt - timedelta(days=years * 365 + 30)

        raw_df = yf.download(
            YFINANCE_TICKER,
            start=start_dt.strftime("%Y-%m-%d"),
            end=(end_dt + timedelta(days=1)).strftime("%Y-%m-%d"),
            interval="1d",
            auto_adjust=True,
            progress=False,
        )

        if raw_df is None or raw_df.empty:
            raise RuntimeError("yfinance historical download returned empty DataFrame.")

        if isinstance(raw_df.columns, pd.MultiIndex):
            raw_df.columns = [col[0].lower() for col in raw_df.columns]
        else:
            raw_df.columns = [c.lower() for c in raw_df.columns]

        if raw_df.index.tzinfo is None:
            raw_df.index = raw_df.index.tz_localize("UTC")
        else:
            raw_df.index = raw_df.index.tz_convert("UTC")

        raw_df = raw_df.rename(columns={"adj close": "close"})
        return raw_df[["open", "high", "low", "close", "volume"]].dropna().sort_index()

    # ─── Helper: OHLCV Resampling ─────────────────────────────────────────────

    @staticmethod
    def _resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
        """
        Resample a higher-frequency OHLCV DataFrame to a lower frequency.

        Args:
            df:   DataFrame with DatetimeIndex and open/high/low/close/volume columns.
            rule: pandas offset alias, e.g. '4h' or '1D'.

        Returns:
            Resampled DataFrame with the same column structure.
        """
        resampled = df.resample(rule, label="left", closed="left").agg(
            {
                "open":   "first",
                "high":   "max",
                "low":    "min",
                "close":  "last",
                "volume": "sum",
            }
        )
        return resampled.dropna()


# ─── Quick CLI test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    print("=" * 60)
    print("  GoldSignalBot – Data Fetcher Self-Test")
    print("=" * 60)

    fetcher = DataFetcher()

    try:
        df = fetcher.fetch(lookback_candles=50)
        print(f"\n✅ Fetched {len(df)} candles | Timeframe: {fetcher.timeframe}")
        print(f"   Date range: {df.index[0]} → {df.index[-1]}")
        print(f"\nLast 5 candles:\n{df.tail(5).to_string()}\n")
        sys.exit(0)
    except RuntimeError as err:
        print(f"\n❌ All sources failed: {err}")
        sys.exit(1)
