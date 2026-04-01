import os
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime
import logging
import concurrent.futures

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
            import requests
            
            # Map timeframe to Yahoo intervals
            interval_map = {"1m": "1m", "15m": "15m", "1h": "1h", "4h": "1h", "1d": "1d"}
            interval = interval_map.get(timeframe, "1h")
            
            # Yahoo Finance limits
            if timeframe == "1m": period = "7d"
            elif timeframe == "15m": period = "1mo"
            elif timeframe == "1d": period = "10y"
            else: period = "2mo"
                
            symbol_to_yf = "GC=F"
            
            logger.info(f"Fetching {symbol_to_yf} ({interval}, {period}) via Direct Yahoo API...")
            
            url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol_to_yf}?interval={interval}&range={period}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
            }
            
            # Strict 15-second timeout on requests
            res = requests.get(url, headers=headers, timeout=15)
            res.raise_for_status()
            data = res.json()
            
            if not data.get("chart", {}).get("result"):
                logger.warning(f"No result returned by Direct Yahoo API for {symbol_to_yf}")
                return pd.DataFrame()
                
            result = data["chart"]["result"][0]
            timestamps = result.get("timestamp", [])
            indicators = result.get("indicators", {}).get("quote", [{}])[0]
            
            if not timestamps or not indicators:
                logger.warning(f"Empty data returned by Direct Yahoo API for {symbol_to_yf}")
                return pd.DataFrame()
            
            # Parse the custom JSON structure into a DataFrame
            df = pd.DataFrame({
                "timestamp": [datetime.utcfromtimestamp(ts) for ts in timestamps],
                "open": indicators.get("open", []),
                "high": indicators.get("high", []),
                "low": indicators.get("low", []),
                "close": indicators.get("close", []),
                "volume": indicators.get("volume", [])
            })
            
            # Clean up missing data (Yahoo occasionally returns None in quotes)
            df.ffill(inplace=True)
            df.set_index("timestamp", inplace=True)

            # Custom Resampling for 4H
            if timeframe == "4h":
                df = df.resample('4h').agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }).dropna()
            
            # Slice to required limit
            df = df.tail(limit)
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Critical Failure in Direct Yahoo Fetcher: {e}")
            if "GC=F" in str(e):
                logger.error("💡 Suggestion: Check if 'GC=F' is still the correct ticker for Gold Futures.")
            return pd.DataFrame()
