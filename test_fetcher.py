import os
import pandas as pd
import yfinance as yf
from modules.data_fetcher import DataFetcher
from dotenv import load_dotenv

load_dotenv()

def test_fetcher():
    fetcher = DataFetcher()
    print("Testing 1h fetch...")
    df = fetcher.fetch_ohlcv(symbol="XAU/USD", timeframe="1h", limit=5)
    
    if df is not None and not df.empty:
        print("Columns found:", df.columns.tolist())
        if 'close' in df.columns:
            print(f"Latest Close: {df['close'].iloc[-1]}")
            print("SUCCESS: 'close' column identified.")
        else:
            print("FAILURE: 'close' column MISSING. Columns are:", df.columns.tolist())
    else:
        print("FAILURE: No data returned.")

if __name__ == "__main__":
    test_fetcher()
