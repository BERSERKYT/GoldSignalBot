import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any
from modules.indicators import Indicators

logger = logging.getLogger("SyncEngine")

class SyncEngine:
    def __init__(self, supabase, fetcher, strategy_factory, signal_logger):
        self.supabase = supabase
        self.fetcher = fetcher
        self.strategy_factory = strategy_factory
        self.signal_logger = signal_logger

    def analyze_outcomes(self):
        """Checks PENDING signals to see if they hit TP or SL."""
        try:
            if not self.supabase: return
            # Fetch pending signals
            response = self.supabase.table("signals").select("*").eq("status", "PENDING").execute()
            pending_signals = response.data
            
            if not pending_signals:
                return

            logger.info(f"🔍 Analyzing outcomes for {len(pending_signals)} pending signals...")
            
            for sig in pending_signals:
                self._check_single_outcome(sig)
                
        except Exception as e:
            logger.error(f"Error in analyze_outcomes: {e}")

    def _check_single_outcome(self, signal: Dict[str, Any]):
        """Check if a specific signal hit TP or SL using higher resolution data (1h)."""
        try:
            # Ensure entry_time is offset-aware UTC
            entry_time = pd.to_datetime(signal['created_at'])
            if entry_time.tzinfo is None:
                entry_time = entry_time.tz_localize('UTC')
            else:
                entry_time = entry_time.tz_convert('UTC')

            # Fetch data from entry time to now
            df = self.fetcher.fetch_ohlcv(symbol="XAU/USD", timeframe="1h", limit=500) 
            if df is None or df.empty:
                logger.warning(f"No data returned for outcome check (Signal {signal['id']})")
                return

            entry_price = float(signal['entry_price'])
            tp = float(signal['tp'])
            sl = float(signal['sl'])
            
            # Ensure index is datetime offset-aware UTC
            df.index = pd.to_datetime(df.index)
            if df.index.tz is None:
                df.index = df.index.tz_localize('UTC')
            else:
                df.index = df.index.tz_convert('UTC')
            
            # Filter data strictly AFTER entry time
            after_entry = df[df.index >= entry_time]
            
            if after_entry.empty:
                logger.info(f"⌛ Signal {signal['id']} is pending - entry_time ({entry_time}) is after latest data ({df.index[-1]})")
                return

            status = "PENDING"
            close_price = None
            
            # Track price ranges for logging
            highest_high = after_entry['high'].max()
            lowest_low = after_entry['low'].min()
            
            for timestamp, row in after_entry.iterrows():
                high = float(row['high'])
                low = float(row['low'])
                
                if signal['direction'] == "BUY":
                    if high >= tp:
                        status = "WIN"
                        close_price = tp
                        break
                    if low <= sl:
                        status = "LOSS"
                        close_price = sl
                        break
                else: # SELL
                    if low <= tp:
                        status = "WIN"
                        close_price = tp
                        break
                    if high >= sl:
                        status = "LOSS"
                        close_price = sl
                        break
            
            if status != "PENDING":
                update_payload = {
                    "status": status,
                    "close_price": close_price
                }
                # Check if id is numeric or uuid
                sig_id = signal['id']
                try:
                    sig_id = int(sig_id)
                except:
                    pass
                    
                self.supabase.table("signals").update(update_payload).eq("id", sig_id).execute()
                logger.info(f"🎯 Outcome Finalized: Signal {signal['id']} -> {status} (Close: {close_price})")
            else:
                logger.info(f"⚖️ Signal {signal['id']} remains PENDING (Range: {lowest_low:.1f} - {highest_high:.1f} | TP: {tp} SL: {sl})")

        except Exception as e:
            logger.error(f"Error checking outcome for signal {signal['id']}: {e}")

    def backfill_gaps(self, start_date: str = "2026-03-02"):
        """Fills historical signal gaps since start_date, max 2 per day."""
        try:
            if not self.supabase: return
            # Fetch historical data (using 1h for more signals)
            logger.info(f"🏺 Starting Backfill from {start_date} (1H resolution)...")
            df = self.fetcher.fetch_ohlcv(symbol="XAU/USD", timeframe="1h", limit=1500) 
            if df is None or df.empty:
                logger.warning("No data returned for backfill.")
                return

            # Add Indicators
            df = Indicators.add_all_indicators(df)
            
            df.index = pd.to_datetime(df.index)
            if df.index.tz is None:
                df.index = df.index.tz_localize('UTC')
            
            start_ts = pd.to_datetime(start_date).tz_localize('UTC')
            df_slice = df[df.index >= start_ts]
            
            logger.info(f"🔍 Analyzing {len(df_slice)} bars of historical data...")

            # Get existing signal timestamps
            existing = self.supabase.table("signals").select("created_at").execute()
            existing_dates = {pd.to_datetime(s['created_at']).date() for s in existing.data}

            v1 = self.strategy_factory.get("v1")
            v2 = self.strategy_factory.get("v2")
            
            daily_signals = {}
            total_filled = 0

            # Iterate through bars
            for i in range(len(df_slice)):
                current_time = df_slice.index[i]
                current_date = current_time.date()
                
                if current_date in existing_dates: continue
                if daily_signals.get(current_date, 0) >= 2: continue

                idx_in_full = df.index.get_loc(current_time)
                window = df.iloc[:idx_in_full+1]
                
                # Try v1
                sig = v1.generate_signal(window)
                # If v1 fails, try v2
                if not sig:
                    sig = v2.generate_signal(window)
                
                if sig:
                    sig["timeframe"] = "1h"
                    sig["strategy"] = "v1" if sig.get("emoji") == "🟢" or sig.get("emoji") == "🔴" else "v2"
                    sig["timestamp"] = current_time
                    self.signal_logger.log_signal(sig)
                    
                    daily_signals[current_date] = daily_signals.get(current_date, 0) + 1
                    total_filled += 1
                    
            logger.info(f"🏺 Backfill complete! Added {total_filled} historical signals.")

        except Exception as e:
            logger.error(f"Error in backfill_gaps: {e}", exc_info=True)
