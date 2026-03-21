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
from modules.notifier import TelegramNotifier
from strategy.v1_strategy import V1Strategy
from strategy.v2_strategy import V2Strategy
from strategy.v3_strategy import V3Strategy
from modules.sync_engine import SyncEngine
from modules.market_calendar import is_market_open
from modules.sentiment_engine import SentimentEngine

# Strategy Factory
STRATEGIES = {
    "v1": V1Strategy(),
    "v2": V2Strategy(),
    "v3": V3Strategy()
}

TIMEFRAMES = ["15m", "1h", "4h", "1d"]

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
    logger.info("Initializing GoldSignalBot (Multi-Scan Mode)...")
    
    # 1. Setup Supabase Client once
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not url.startswith("https://"):
        logger.error(f"❌ INVALID SUPABASE_URL: '{url}'. Please check your GitHub Secrets!")
        sys.exit(1)
        
    if not key:
        logger.error("❌ SUPABASE_KEY IS MISSING. Please check your GitHub Secrets!")
        sys.exit(1)
        
    supabase_client: Client = create_client(url, key)
    logger.info("✅ Supabase Connection: Established.")

    # 2. Initialize components
    fetcher = DataFetcher()
    news_filter = NewsFilter()
    signal_logger = SignalLogger()
    notifier = TelegramNotifier()
    
    from modules.learning_engine import LearningEngine
    learning_engine = LearningEngine(supabase_client)
    sentiment_engine = SentimentEngine()
    
    # Initialize SyncEngine
    sync_engine = SyncEngine(supabase_client, fetcher, STRATEGIES, signal_logger)
    
    # 🏁 HISTORICAL RECOVERY
    sync_engine.backfill_gaps(start_date="2026-03-02")
    
    scan_interval_mins = int(os.getenv("SCAN_INTERVAL_MINS", "60"))
    logger.info(f"Bot successfully started. Universal Scan Mode Active.")

    while True:
        try:
            # 🛡️ 1. MARKET HOURS GUARD (XAU/USD)
            if not is_market_open():
                logger.warning("🌍 Market is CLOSED. Skipping all scans until Sunday open.")
                # If single run (GitHub Actions), we exit now to save minutes
                if os.getenv("SINGLE_RUN", "false").lower() == "true":
                    break
                time.sleep(3600) # Check again in 1 hour if in loop mode
                continue

            # 🛡️ 2. DAILY SIGNAL CAP (MAX 5)
            daily_count = signal_logger.get_daily_count()
            if daily_count >= 5:
                logger.warning(f"🛑 DAILY CAP REACHED ({daily_count}/5 signals). No more signals today.")
                if os.getenv("SINGLE_RUN", "false").lower() == "true":
                    break
                time.sleep(3600)
                continue

            # 0. Sync settings from Cloud Command Center
            db_settings = get_supabase_settings(supabase_client)
            trading_enabled = False
            smart_lots_enabled = False
            risk_percentage = 1.0
            if db_settings:
                trading_enabled = db_settings.get("trading_enabled", False)
                smart_lots_enabled = db_settings.get("smart_lots_enabled", False)
                risk_percentage = float(db_settings.get("risk_percentage", 1.0))
                logger.info(f"🔄 SYNC: Cloud Settings | Trading: {trading_enabled} | Smart Lots: {smart_lots_enabled} ({risk_percentage}% risk)")

            # 0.5 Update Outcomes for PENDING signals
            sync_engine.analyze_outcomes()

            # 🧠 AI MARKET SENTIMENT (News-Based)
            sentiment_data = sentiment_engine.get_market_sentiment()
            sentiment_score = sentiment_data["score"]
            sentiment_label = sentiment_data["label"]
            
            # Update Dashboard Status once at start of loop
            try:
                # Fetch recent price for dashboard sync
                df_sync = fetcher.fetch_ohlcv(symbol="XAU/USD", timeframe="15m", limit=5)
                if not df_sync.empty:
                    current_p = float(df_sync.iloc[-1]['close'])
                    prev_p = float(df_sync.iloc[-2]['close'])
                    chg_pct = round(((current_p - prev_p) / prev_p) * 100, 2)
                    
                    supabase_client.table("settings").update({
                        "current_price": round(current_p, 2),
                        "price_change": chg_pct,
                        "sentiment_score": sentiment_score, # 🧠 New
                        "sentiment_label": sentiment_label, # 🧠 New
                        "notifier_status": "ENABLED" if notifier.enabled else "DISABLED",
                        "notifier_error": notifier.last_error,
                        "updated_at": datetime.utcnow().isoformat()
                    }).eq("id", 1).execute()
                    
                    # Heartbeat
                    notifier.send_heartbeat(price=current_p, ai_status="Scanning", timeframe="MULTI")
            except Exception as e:
                logger.error(f"Metadata update failed: {e}")

            # --- 🚀 UNIVERSAL SCAN: ALL TIMEFRAMES & ALL STRATEGIES ---
            if not news_filter.is_safe_to_trade():
                logger.warning("News Filter active: Skipping scans.")
            else:
                for tf in TIMEFRAMES:
                    logger.info(f"🔍 Scanning Timeframe: {tf}")
                    df = fetcher.fetch_ohlcv(symbol="XAU/USD", timeframe=tf, limit=200)
                    
                    if df is None or df.empty:
                        logger.warning(f"No data for {tf}, skipping.")
                        continue
                        
                    df = Indicators.add_all_indicators(df)
                    curr_p = float(df.iloc[-1]['close'])

                    # 🧠 TF-SPECIFIC AI LEARNING
                    ai_adaptation = learning_engine.apply_learning({}, timeframe=tf)
                    sharpened_params = ai_adaptation["params"]
                    
                    for strat_name, strategy in STRATEGIES.items():
                        logger.info(f"   ∟ Checking {strat_name}...")
                        signal = strategy.generate_signal(df, current_price=curr_p, params=sharpened_params)
                        
                        if signal:
                            # 🛡️ 3. HIGH CONFIDENCE FILTER + SENTIMENT BIAS
                            conf = signal.get("confidence", 0)
                            
                            # Apply Sentiment Bias: Boost if sentiment aligns with trade direction
                            # Gold Sentiment > 0 is Bullish.
                            bias = 0
                            if sentiment_score > 0.2 and signal["direction"] == "BUY":
                                bias = 0.05
                            elif sentiment_score < -0.2 and signal["direction"] == "SELL":
                                bias = 0.05
                            elif sentiment_score > 0.2 and signal["direction"] == "SELL":
                                bias = -0.05 # Penalty for trading against news sentiment
                                
                            conf = round(conf + bias, 2)
                            signal["confidence"] = conf
                            signal["sentiment_bias"] = bias
                            signal["market_sentiment"] = sentiment_score
                            if conf < 0.8:
                                logger.info(f"⏩ Skipping {strat_name} signal: Confidence {conf:.2f} is below 0.8 floor.")
                                continue
                            
                            if conf >= 0.9:
                                logger.info(f"💎 PREMIUM SIGNAL FOUND: Confidence {conf:.2f} (90%+ Priority)")

                            # Add metadata
                            signal["timeframe"] = tf
                            signal["strategy"] = strat_name
                            # 🧠 Inject Smart Lots settings from cloud command center
                            signal["smart_lots_enabled"] = smart_lots_enabled
                            signal["risk_percentage"] = risk_percentage
                            
                            logger.info(f"🎯 SIGNAL FOUND: {tf} | {strat_name} | {signal['direction']}")
                            
                            # Execute & Notify
                            try:
                                if trading_enabled:
                                    from modules.mt5_execution import sync_execute_trade
                                    trade_res = sync_execute_trade(signal)
                                    if trade_res:
                                        signal["broker_ticket"] = trade_res.get("orderId")
                                        logger.info(f"💰 LIVE TRADE PLACED: {signal['broker_ticket']}")
                                else:
                                    logger.info(f"🛡️ TRADING DISABLED (Cloud Settings). Skipping execution.")
                            except Exception as e:
                                logger.warning(f"MT5 execution skipped: {e}")

                            try:
                                notifier.send_signal(signal)
                            except Exception as e:
                                logger.error(f"Notifier error: {e}")

                            signal_logger.log_signal(signal, asset="XAU/USD")
                        
            logger.info("Universal scan complete.")
            
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
