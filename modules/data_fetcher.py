import os
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DataFetcher:
    def __init__(self):
        self.goldapi_key = os.getenv("GOLDAPI_KEY")
        self.metalprice_key = os.getenv("METALPRICE_KEY")
        
    def fetch_ohlcv(self, symbol="XAU/USD", timeframe="4h", limit=500) -> pd.DataFrame:
        """
        Attempts to fetch OHLCV data for the given symbol and timeframe.
        Priority: GoldAPI.io -> MetalpriceAPI -> yfinance
        """
        df = None
        
        # 1. Try GoldAPI if API key is provided (Optional)
        if self.goldapi_key:
            # Note: For now, we prefer the reliability of yfinance for OHLCV history in the MVP.
            pass
                
        # 3. Fallback to yfinance (GC=F for Gold Futures)
        return self._fetch_yfinance(timeframe, limit)

    def _fetch_yfinance(self, timeframe, limit) -> pd.DataFrame:
        try:
            # Map timeframe to yfinance intervals
            interval_map = {
                "15m": "15m",
                "1h": "1h",
                "4h": "1h", # We fetch 1h and resample to 4h
                "1d": "1d"
            }
            interval = interval_map.get(timeframe, "1h")
            
            # yfinance limits: 15m data max 59 days.
            if timeframe == "15m":
                period = "1mo"
            elif timeframe == "1d":
                period = "max"
            else:
                period = "2mo"
                
            symbol_to_yf = "GC=F"
            
            logger.info(f"Fetching {symbol_to_yf} data from yfinance ({interval}, {period})...")
            df = yf.download(symbol_to_yf, interval=interval, period=period, progress=False, auto_adjust=True)
            
            if df is None or df.empty:
                logger.warning(f"No data returned for {symbol_to_yf} ({interval}, {period})")
                return pd.DataFrame()
                
            # Flatten columns robustly for different yfinance versions
            if isinstance(df.columns, pd.MultiIndex):
                # Handle MultiIndex by taking the first level (e.g., ('Close', 'GC=F') -> 'Close')
                df.columns = [col[0].lower() for col in df.columns]
            else:
                # Handle single Index
                df.columns = [col.lower() for col in df.columns]
            
            # Additional safety: rename 'adj close' to 'close' if present and 'close' is missing
            if 'adj close' in df.columns and 'close' not in df.columns:
                df.rename(columns={'adj close': 'close'}, inplace=True)
            
            # Remove any duplicated columns if any
            df = df.loc[:, ~df.columns.duplicated()]

            # Custom Resampling for 4H
            if timeframe == "4h":
                df = df.resample('4h').agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }).dropna()

            # Ensure the Index is the timestamp column
            if 'timestamp' not in df.columns:
                df.index.name = 'timestamp'
                # Don't reset_index yet, let SyncEngine use the index or reset it itself.
                # To maintain compatibility with existing logger and strategies that expect 'close' col etc.
                pass
            
            # Slice to limit
            df = df.tail(limit)
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Critical Failure in yfinance Fetcher: {e}")
            if "GC=F" in str(e):
                logger.error("💡 Suggestion: Check if 'GC=F' is still the correct ticker for Gold Futures.")
            return pd.DataFrame()
