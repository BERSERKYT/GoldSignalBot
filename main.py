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
from strategy.v4_strategy import V4Strategy
from strategy.v3_strategy import V3Strategy
from strategy.v5_strategy import V5Strategy
from modules.sync_engine import SyncEngine
from modules.market_calendar import is_market_open
from modules.sentiment_engine import SentimentEngine

# TIMEFRAMES monitored by the bot
TIMEFRAMES = ["15m", "1h", "2h", "4h", "1d"]

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
    
    # Strategy Factory (Now initialized inside main to pass fetcher to V4/V5)
    strategies_map = {
        "v1": V1Strategy(),
        "v4": V4Strategy(fetcher=fetcher),
        "v3": V3Strategy(),
        "v5": V5Strategy(fetcher=fetcher)
    }
    
    news_filter = NewsFilter()
    signal_logger = SignalLogger()
    notifier = TelegramNotifier()
    
    from modules.learning_engine import LearningEngine
    learning_engine = LearningEngine(supabase_client)
    sentiment_engine = SentimentEngine()
    
    # Initialize SyncEngine
    sync_engine = SyncEngine(supabase_client, fetcher, strategies_map, signal_logger)
    
    # HISTORICAL RECOVERY — only runs once on first setup (when DB has < 5 signals)
    try:
        existing_count = supabase_client.table("signals").select("id", count="exact").execute()
        if (existing_count.count or 0) < 5:
            logger.info("First-time setup detected. Running historical backfill...")
            sync_engine.backfill_gaps(start_date="2026-03-02")
        else:
            logger.info(f"Skipping backfill — {existing_count.count} signals already in DB.")
    except Exception as e:
        logger.warning(f"Could not check signal count for backfill gate: {e}")
    
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

            # 0. Sync settings from Cloud Command Center
            db_settings = get_supabase_settings(supabase_client)
            trading_enabled = False
            smart_lots_enabled = False
            risk_percentage = 1.0
            if db_settings:
                try:
                    trading_enabled = db_settings.get("trading_enabled", False) or False
                    smart_lots_enabled = db_settings.get("smart_lots_enabled", False) or False
                    risk_percentage = float(db_settings.get("risk_percentage") or 1.0)
                    logger.info(f"SYNC: Cloud Settings | Trading: {trading_enabled} | Smart Lots: {smart_lots_enabled} ({risk_percentage}% risk)")
                except Exception as e:
                    logger.warning(f"Supabase settings parse error (using defaults): {e}")

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
            found_signals = []
            
            if not news_filter.is_safe_to_trade():
                logger.warning("News Filter active: Skipping scans.")
            else:
                # Pre-fetch frames once per cycle for V4 and V5 Multi-Timeframe Alignment (avoids redundant calls)
                df_1wk_cache = fetcher.fetch_ohlcv(symbol="XAU/USD", timeframe="1wk", limit=100)
                df_1d_cache = fetcher.fetch_ohlcv(symbol="XAU/USD", timeframe="1d", limit=150)
                df_h1_cache = fetcher.fetch_ohlcv(symbol="XAU/USD", timeframe="1h", limit=200)
                df_h4_cache = fetcher.fetch_ohlcv(symbol="XAU/USD", timeframe="4h", limit=200)

                for tf in TIMEFRAMES:
                    logger.info(f"Scanning Timeframe: {tf}")
                    df = fetcher.fetch_ohlcv(symbol="XAU/USD", timeframe=tf, limit=200)
                    
                    if df is None or df.empty:
                        logger.warning(f"No data for {tf}, skipping.")
                        continue
                        
                    df = Indicators.add_all_indicators(df)
                    curr_p = float(df.iloc[-1]['close'])

                    # TF-SPECIFIC AI LEARNING
                    ai_adaptation = learning_engine.apply_learning({}, timeframe=tf)
                    sharpened_params = ai_adaptation["params"]
                    
                    # Update Cloud Status
                    if supabase_client:
                        try:
                            supabase_client.table("settings").update({
                                "ai_status": ai_adaptation["status"],
                                "ai_lessons": ai_adaptation["insight"]
                            }).eq("id", 1).execute()
                        except Exception as e:
                            logger.warning(f"Could not update AI status in Supabase: {e}")
                    
                    for strat_name, strategy in strategies_map.items():
                        logger.info(f"   Checking {strat_name}...")
                        # Pass pre-fetched H1/H4/D1/Weekly to avoid redundant HTTP calls
                        if strat_name == "v4":
                            signal = strategy.generate_signal(df, current_price=curr_p, params=sharpened_params,
                                                              df_h1=df_h1_cache, df_h4=df_h4_cache)
                        elif strat_name == "v5":
                            signal = strategy.generate_signal(df, current_price=curr_p, params=sharpened_params,
                                                              df_1wk=df_1wk_cache, df_1d=df_1d_cache, df_4h=df_h4_cache)
                        else:
                            signal = strategy.generate_signal(df, current_price=curr_p, params=sharpened_params)
                        
                        if signal:
                            # 🛡️ 3. HIGH CONFIDENCE FILTER + SENTIMENT BIAS
                            conf = signal.get("confidence", 0)
                            
                            # Apply Sentiment Bias
                            bias = 0
                            if sentiment_score > 0.2 and signal["direction"] == "BUY":
                                bias = 0.05
                            elif sentiment_score < -0.2 and signal["direction"] == "SELL":
                                bias = 0.05
                            elif sentiment_score > 0.2 and signal["direction"] == "SELL":
                                bias = -0.05 
                                
                            conf = round(conf + bias, 2)
                            signal["confidence"] = conf
                            signal["sentiment_bias"] = bias
                            signal["market_sentiment"] = sentiment_score
                            
                            if conf < 0.8:
                                logger.info(f"⏩ Discarding {strat_name} ({tf}): Confidence {conf:.2f} < 0.8")
                                continue
                            
                            # Add metadata
                            signal["timeframe"] = tf
                            signal["strategy"] = strat_name
                            signal["smart_lots_enabled"] = smart_lots_enabled
                            signal["risk_percentage"] = risk_percentage
                            
                            found_signals.append(signal)
                    
            # --- 🏆 BATCH PROCESSING & RANKING ---
            if found_signals:
                # 1. Sort by confidence (Highest First) to ensure we take only the BEST ones
                found_signals.sort(key=lambda x: x['confidence'], reverse=True)
                
                # 2. Check remaining slots for the day
                current_daily_count = signal_logger.get_daily_count()
                remaining_slots = max(0, 5 - current_daily_count)
                
                logger.info(f"🎯 Scan Cycle Complete. Found {len(found_signals)} potential signals. Remaining slots today: {remaining_slots}")
                
                # 3. Process only the top signals that fit
                for signal in found_signals[:remaining_slots]:
                    logger.info(f"✅ Processing Top Signal: {signal['timeframe']} {signal['strategy']} (Conf: {signal['confidence']:.2f})")
                    
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
                        logger.warning(f"MT5 execution failed: {e}")

                    try:
                        notifier.send_signal(signal)
                    except Exception as e:
                        logger.error(f"Notifier error: {e}")

                    signal_logger.log_signal(signal, asset="XAU/USD")
                
                if len(found_signals) > remaining_slots:
                    logger.warning(f"🛑 {len(found_signals) - remaining_slots} signals were discarded due to daily cap. Only the highest confidence ones were sent.")

            logger.info("Universal scan cycle complete.")
            
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
