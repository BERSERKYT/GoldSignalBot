import sys
from modules.data_fetcher import DataFetcher
from modules.indicators import Indicators
from strategy.v1_strategy import V1Strategy
from strategy.v4_strategy import V4Strategy
import logging

logging.basicConfig(level=logging.INFO)

print("Fetching Data...")
fetcher = DataFetcher()
df = fetcher.fetch_ohlcv("XAU/USD", "4h", 200)

if df is None or df.empty:
    print("NO DATA returned by fetcher. This is the issue!")
    sys.exit()

print(f"Data fetched! Last date in DataFrame: {df.index[-1]}")

df = Indicators.add_all_indicators(df)

v1 = V1Strategy()
sig_v1 = v1.generate_signal(df)
print(f"V1 Signal: {sig_v1}")

v4 = V4Strategy(fetcher=fetcher)
sig_v4 = v4.generate_signal(df)
print(f"V4 Signal: {sig_v4}")

print("Test complete.")
