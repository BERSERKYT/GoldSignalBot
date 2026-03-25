import yfinance as yf
import pandas as pd

def test_gold_symbols():
    symbols = ['GC=F', 'GLD', 'IAU', 'XAUUSD=X', 'XAU=X']
    results = {}
    for s in symbols:
        try:
            ticker = yf.Ticker(s)
            price = ticker.fast_info['last_price']
            results[s] = price
            print(f"{s}: {price}")
        except Exception as e:
            print(f"{s}: Error - {e}")

test_gold_symbols()
