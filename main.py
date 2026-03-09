import os
import sys
import time
import logging
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# Load config from .env
load_dotenv()

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("GoldBot_Main")

from modules.data_fetcher import DataFetcher
from modules.indicators import Indicators
from modules.news_filter import NewsFilter
from modules.logger import SignalLogger
from strategy.v1_strategy import V1Strategy
from strategy.v2_strategy import V2Strategy
from modules.sync_engine import SyncEngine

# Strategy Factory
STRATEGIES = {
    "v1": V1Strategy(),
    "v2": V2Strategy()
}

def get_supabase_settings(supabase: Client):
    """Fetch active settings from Supabase command center."""
    if not supabase:
        return None
    
    try:
        response = supabase.table("settings").select("*").eq("id", 1).single().execute()
        return response.data
    except Exception as e:
        logger.error(f"Failed to fetch Supabase settings: {e}")
        return None

def main():
    logger.info("Initializing GoldSignalBot...")
    
    # 1. Setup Supabase Client once
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        logger.error("SUPABASE_URL or SUPABASE_KEY missing in .env")
        sys.exit(1)
        
    supabase_client: Client = create_client(url, key)
    logger.info("✅ Supabase Connection: Established.")

    # 2. Initialize components
    fetcher = DataFetcher()
    news_filter = NewsFilter()
    signal_logger = SignalLogger()
    
    # Initial Configuration Defaults
    timeframe = os.getenv("TIMEFRAME", "4h")
    scan_interval_mins = int(os.getenv("SCAN_INTERVAL_MINS", "60"))
    active_strategy_name = "v1"

    # Initialize SyncEngine with the global client
    sync_engine = SyncEngine(supabase_client, fetcher, STRATEGIES, signal_logger)
    
    # 🏁 HISTORICAL RECOVERY (Runs once on startup)
    sync_engine.backfill_gaps(start_date="2026-03-02")
    
    logger.info(f"Bot successfully started. Scan interval: {scan_interval_mins} mins.")

    while True:
        try:
            # 0. Sync settings from Cloud Command Center
            db_settings = get_supabase_settings(supabase_client)
            if db_settings:
                timeframe = db_settings.get("active_timeframe", timeframe)
                active_strategy_name = db_settings.get("active_strategy", active_strategy_name)
                logger.info(f"🔄 SYNC: Cloud Settings Loaded - {timeframe} | Strategy: {active_strategy_name}")
            
            # 0.5 Update Outcomes for PENDING signals
            sync_engine.analyze_outcomes()
            
            # Select Strategy from Factory
            strategy = STRATEGIES.get(active_strategy_name, STRATEGIES["v1"])
            
            logger.info(f"--- Starting new scan cycle ({timeframe} | {active_strategy_name}) ---")
            
            # 1. Fetch Data
            df = fetcher.fetch_ohlcv(symbol="XAU/USD", timeframe=timeframe, limit=200)
            
            if df is None or df.empty:
                logger.error("Failed to fetch data. Retrying in next cycle.")
            else:
                logger.info(f"Successfully fetched {len(df)} candles.")
                
                # 1.5 Update Current Price in Supabase for Dashboard Header
                try:
                    current_price = float(df.iloc[-1]['close'])
                    prev_close = float(df.iloc[-2]['close'])
                    price_change_pct = ((current_price - prev_close) / prev_close) * 100
                    
                    logger.info(f"📤 Updating Supabase: Price={current_price:.2f}, Change={price_change_pct:.2f}%")
                    
                    res = supabase_client.table("settings").update({
                        "current_price": round(current_price, 2),
                        "price_change": round(price_change_pct, 2),
                        "updated_at": datetime.utcnow().isoformat()
                    }).eq("id", 1).execute()
                    
                    if not res.data:
                        logger.warning("Supabase update returned no data - check if ID 1 exists and is accessible.")
                    else:
                        logger.info("✅ Supabase settings updated successfully.")
                except Exception as e:
                    logger.error(f"❌ Failed to update live price in Supabase: {e}")

                # 2. Add Indicators
                df = Indicators.add_all_indicators(df)
                
                # 3. Check News Filter
                if not news_filter.is_safe_to_trade():
                    logger.warning("News Filter active: Skipped signal generation this cycle.")
                else:
                    # 4. Run Strategy
                    curr_p = df.iloc[-1]['close'] if not df.empty else None
                    signal = strategy.generate_signal(df, current_price=curr_p)
                    
                    if signal:
                        # Add metadata for Supabase
                        signal["timeframe"] = timeframe
                        signal["strategy"] = active_strategy_name
                        # 5. Log & Output Signal
                        signal_logger.log_signal(signal, asset="XAU/USD")
                    else:
                        logger.info(f"No actionable signal for {active_strategy_name} on {timeframe}")
                        
        except Exception as e:
            logger.error(f"Critical error in main loop: {e}", exc_info=True)
            
        # 6. Check for Single Run mode (for GitHub Actions)
        if os.getenv("SINGLE_RUN", "false").lower() == "true":
            logger.info("✅ Single run complete. Exiting...")
            break

        # 7. Sleep for next cycle
        logger.info(f"Sleeping for {scan_interval_mins} minutes...")
        time.sleep(scan_interval_mins * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
        sys.exit(0)
