import os
import pandas as pd
from supabase import create_client
from dotenv import load_dotenv
from modules.data_fetcher import DataFetcher

load_dotenv()

def debug_signal_outcome(signal_id):
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    supabase = create_client(url, key)
    
    res = supabase.table("signals").select("*").eq("id", signal_id).single().execute()
    signal = res.data
    if not signal:
        print("Signal not found.")
        return

    print(f"Debugging Signal {signal_id}")
    print(f"Direction: {signal['direction']} | Entry: {signal['entry_price']} | SL: {signal['sl']} | TP: {signal['tp']}")
    print(f"Created At: {signal['created_at']}")

    fetcher = DataFetcher()
    df = fetcher.fetch_ohlcv(symbol="XAU/USD", timeframe="1m", limit=3000)
    
    entry_time = pd.to_datetime(signal['created_at'])
    if entry_time.tzinfo is None:
        entry_time = entry_time.tz_localize('UTC')
    else:
        entry_time = entry_time.tz_convert('UTC')

    df.index = pd.to_datetime(df.index)
    if df.index.tz is None:
        df.index = df.index.tz_localize('UTC')
    else:
        df.index = df.index.tz_convert('UTC')

    after_entry = df[df.index >= entry_time]
    print(f"Bars after entry: {len(after_entry)}")
    
    if not after_entry.empty:
        print("Recent 1h Bars:")
        print(after_entry[['open', 'high', 'low', 'close']].tail(10))
        max_high = after_entry['high'].max()
        min_low = after_entry['low'].min()
        print(f"Max High: {max_high} | Min Low: {min_low}")

        if signal['direction'] == 'SELL':
            if max_high >= float(signal['sl']):
                print(">>> SL HIT DETECTED! (Max High >= SL)")
            else:
                print(f">>> SL NOT HIT. (Max High {max_high} < SL {signal['sl']})")

if __name__ == "__main__":
    debug_signal_outcome("5321f04f-a7f9-443f-b3da-f9cb905965c1")
