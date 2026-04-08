"""
GoldSignalBot - Signal Diagnostic Script
Checks every layer of the pipeline to find exactly why no signals are sent.
"""
import os
import logging
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()
logging.basicConfig(level=logging.WARNING)  # Suppress noise

print("=" * 60)
print("  GoldSignalBot - Full Signal Diagnostic")
print("=" * 60)

from modules.data_fetcher import DataFetcher
from modules.indicators import Indicators
from modules.market_calendar import is_market_open
from strategy.v1_strategy import V1Strategy

fetcher = DataFetcher()

# ─── CHECK 1: Market Open ─────────────────────────────────────
print("\n[1] MARKET HOURS CHECK")
is_open = is_market_open()
print(f"    Market Open: {'✅ YES' if is_open else '❌ NO (Market closed - all scans are skipped!)'}")

# ─── CHECK 2: News Filter ─────────────────────────────────────
print("\n[2] NEWS FILTER CHECK")
from modules.news_filter import NewsFilter
nf = NewsFilter()
if nf.api_key:
    safe = nf.is_safe_to_trade()
    print(f"    Finnhub Key: ✅ Found")
    print(f"    Safe to trade: {'✅ YES' if safe else '❌ NO (News filter is blocking ALL scans right now!)'}")
else:
    print(f"    Finnhub Key: ⚠️  MISSING - filter bypassed (safe=True)")

# ─── CHECK 3: Data Fetching ───────────────────────────────────
print("\n[3] DATA FETCH CHECK (1H timeframe)")
df_1h = fetcher.fetch_ohlcv("XAU/USD", "1h", 200)
if df_1h is None or df_1h.empty:
    print("    ❌ FAILED: No data returned. Bot cannot scan without data!")
else:
    print(f"    ✅ Fetched {len(df_1h)} candles. Last: {df_1h.index[-1]}")

# ─── CHECK 4: Indicators ─────────────────────────────────────
print("\n[4] INDICATORS CHECK")
if df_1h is not None and not df_1h.empty:
    df_1h = Indicators.add_all_indicators(df_1h)
    required = ['EMA_9', 'EMA_21', 'RSI_14', 'ATR_14', 'ATR_14_MA_20']
    missing = [c for c in required if c not in df_1h.columns]
    if missing:
        print(f"    ❌ Missing columns: {missing}")
    else:
        latest = df_1h.iloc[-1]
        prev    = df_1h.iloc[-2]
        print(f"    ✅ All indicators computed")
        print(f"    Last candle:  EMA9={latest['EMA_9']:.2f} | EMA21={latest['EMA_21']:.2f} | RSI={latest['RSI_14']:.1f} | ATR={latest['ATR_14']:.2f}")
        print(f"    Prev candle:  EMA9={prev['EMA_9']:.2f} | EMA21={prev['EMA_21']:.2f}")

        buy_cross  = (prev['EMA_9'] <= prev['EMA_21']) and (latest['EMA_9'] > latest['EMA_21'])
        sell_cross = (prev['EMA_9'] >= prev['EMA_21']) and (latest['EMA_9'] < latest['EMA_21'])
        high_vol   = latest['ATR_14'] > (latest['ATR_14_MA_20'] * 0.95)

        print(f"\n    EMA Cross conditions (most recent candle ONLY):")
        print(f"    BUY  cross detected: {'✅ YES' if buy_cross else '❌ NO'}")
        print(f"    SELL cross detected: {'✅ YES' if sell_cross else '❌ NO'}")
        print(f"    High volatility (ATR > MA_ATR*0.95): {'✅ YES' if high_vol else '❌ NO'} (ATR={latest['ATR_14']:.2f} vs MA={latest['ATR_14_MA_20']:.2f})")

# ─── CHECK 5: Historical Cross Scan ──────────────────────────
print("\n[5] EMA CROSS HISTORY (Last 7 days on 1H) — Did we MISS any crosses?")
if df_1h is not None and not df_1h.empty:
    cutoff = pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=7)
    if df_1h.index.tz is None:
        df_1h.index = df_1h.index.tz_localize('UTC')
    df_week = df_1h[df_1h.index >= cutoff]
    
    crosses_found = 0
    for i in range(1, len(df_week)):
        p = df_week.iloc[i-1]
        c = df_week.iloc[i]
        bc = (p['EMA_9'] <= p['EMA_21']) and (c['EMA_9'] > c['EMA_21'])
        sc = (p['EMA_9'] >= p['EMA_21']) and (c['EMA_9'] < c['EMA_21'])
        rsi_ok_buy  = c['RSI_14'] > 50
        rsi_ok_sell = c['RSI_14'] < 50
        atr_ok = c['ATR_14'] > (c['ATR_14_MA_20'] * 0.95)
        
        if bc and rsi_ok_buy and atr_ok:
            print(f"    🟢 MISSED BUY  SIGNAL @ {df_week.index[i]} | RSI={c['RSI_14']:.1f} | Conf=0.80+")
            crosses_found += 1
        elif sc and rsi_ok_sell and atr_ok:
            print(f"    🔴 MISSED SELL SIGNAL @ {df_week.index[i]} | RSI={c['RSI_14']:.1f} | Conf=0.80+")
            crosses_found += 1
        elif bc or sc:
            reason = []
            if bc: reason.append("BUY cross")
            if sc: reason.append("SELL cross")
            if not atr_ok: reason.append("low volatility")
            if bc and not rsi_ok_buy: reason.append("RSI<50")
            if sc and not rsi_ok_sell: reason.append("RSI>50")
            print(f"    ⚠️  Cross @ {df_week.index[i]} BLOCKED by: {', '.join(reason)}")
            crosses_found += 1
    
    if crosses_found == 0:
        print(f"    ❌ NO EMA crosses at all in the last 7 days on 1H! The market has been range-bound.")
    else:
        print(f"\n    Total cross events found: {crosses_found}")

# ─── CHECK 6: V1 Strategy on current data ────────────────────
print("\n[6] V1 STRATEGY LIVE TEST")
v1 = V1Strategy()
sig = v1.generate_signal(df_1h)
if sig:
    print(f"    ✅ Signal RIGHT NOW: {sig['direction']} | Conf={sig['confidence']}")
else:
    print(f"    ❌ No signal on current candle (expected — cross likely happened earlier)")

# ─── CHECK 7: Supabase Settings ──────────────────────────────
print("\n[7] SUPABASE SETTINGS CHECK")
from supabase import create_client
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
if url and key:
    try:
        sb = create_client(url, key)
        resp = sb.table("settings").select("trading_enabled,max_signals_per_day").eq("id", 1).single().execute()
        d = resp.data
        print(f"    trading_enabled:    {d.get('trading_enabled')}")
        print(f"    max_signals_per_day (if set): {d.get('max_signals_per_day', 'N/A (hardcoded to 5 in main.py)')}")
    except Exception as e:
        print(f"    ⚠️  Could not fetch: {e}")
else:
    print("    ❌ SUPABASE_URL or SUPABASE_KEY missing")

print("\n" + "=" * 60)
print("  Diagnostic Complete")
print("=" * 60)
