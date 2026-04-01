import logging
import pandas as pd
from datetime import datetime, timedelta, timezone

from modules.data_fetcher import DataFetcher
from modules.indicators import Indicators
from strategy.v1_strategy import V1Strategy
from strategy.v4_strategy import V4Strategy

logging.basicConfig(level=logging.INFO)

fetcher = DataFetcher()
print("Fetching past 15 days of XAU/USD data (4h timeframe)...")
df = fetcher.fetch_ohlcv("XAU/USD", "4h", 200)

if df is None or df.empty:
    print("NO DATA RETURNED!")
    exit()

df = Indicators.add_all_indicators(df)

# Filter dataframe for dates after March 20
df.index = pd.to_datetime(df.index)
if df.index.tz is None:
    df.index = df.index.tz_localize('UTC')

df_slice = df[df.index >= pd.to_datetime("2026-03-20").tz_localize('UTC')]

v1 = V1Strategy()
v4 = V4Strategy(fetcher=fetcher)

v1_signals_generated = 0
v4_signals_generated = 0

print(f"Analyzing {len(df_slice)} 4H candles from March 20 to today...")

for i in range(1, len(df_slice)):
    # We pass a window up to the current candle to simulate real-time
    idx = df.index.get_loc(df_slice.index[i])
    window = df.iloc[:idx+1]
    
    cv1 = v1.generate_signal(window)
    if cv1:
        print(f"[V1] Found Signal at {df_slice.index[i]}: {cv1['direction']} | Conf: {cv1['confidence']}")
        v1_signals_generated += 1
        
    cv4 = v4.generate_signal(window)
    if cv4:
        print(f"[V4] Found Signal at {df_slice.index[i]}: {cv4['direction']} | Conf: {cv4['confidence']}")
        v4_signals_generated += 1

print(f"Total V1 Signals: {v1_signals_generated}")
print(f"Total V4 Signals: {v4_signals_generated}")
