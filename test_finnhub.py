import os
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
finnhub_key = os.getenv("FINNHUB_KEY")

def test_finnhub_candles():
    print(f"Testing Finnhub with key: {finnhub_key[:5]}...")
    # Finnhub requires UNIX timestamps. Last 5 days for 60-min candles.
    import time
    end_time = int(time.time())
    start_time = end_time - (5 * 24 * 60 * 60)
    
    # Check OANDA:XAU_USD
    url = f"https://finnhub.io/api/v1/stock/candle?symbol=OANDA:XAU_USD&resolution=60&from={start_time}&to={end_time}&token={finnhub_key}"
    
    res = requests.get(url)
    if res.status_code == 200:
        data = res.json()
        if data.get("s") == "ok":
            print(f"SUCCESS: Finnhub fetched {len(data['c'])} candles for XAU_USD!")
            return True
        else:
            print(f"Finnhub returned no data (status: {data.get('s')})")
    else:
        print(f"Error {res.status_code}: {res.text}")
    return False

test_finnhub_candles()
