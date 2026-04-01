import requests
import pandas as pd
from datetime import datetime
import json

def fetch_yahoo_raw(symbol="GC=F", interval="1h", range_val="2mo"):
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?interval={interval}&range={range_val}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        print(f"Fetching from {url}...")
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if not data.get("chart", {}).get("result"):
                print("No result in JSON!")
                return None
            
            result = data["chart"]["result"][0]
            timestamps = result.get("timestamp", [])
            indicators = result["indicators"]["quote"][0]
            
            df = pd.DataFrame({
                "timestamp": [datetime.utcfromtimestamp(ts) for ts in timestamps],
                "open": indicators["open"],
                "high": indicators["high"],
                "low": indicators["low"],
                "close": indicators["close"],
                "volume": indicators["volume"]
            })
            df.set_index("timestamp", inplace=True)
            df.dropna(inplace=True)
            print(f"SUCCESS: Fetched {len(df)} candles!")
            print(df.tail(2))
            return df
        else:
            print(f"Error {res.status_code}: {res.text[:200]}")
    except Exception as e:
        print(f"Exception: {e}")

fetch_yahoo_raw()
