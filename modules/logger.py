import csv
import os
import logging
import pandas as pd
from datetime import datetime
from pathlib import Path
from supabase import create_client, Client

# Setup basic logging to console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("GoldSignalBot")

class SignalLogger:
    def __init__(self, data_dir="data", filename="signals.csv"):
        self.output_dir = Path(data_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.filepath = self.output_dir / filename
        self._ensure_csv_headers()
        
        # Initialize Supabase
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        if url and key:
            self.supabase: Client = create_client(url, key)
        else:
            self.supabase = None
            logger.warning("Supabase credentials not found. Cloud logging disabled.")

    def _ensure_csv_headers(self):
        if not self.filepath.exists():
            with open(self.filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Timestamp_UTC', 
                    'Asset', 
                    'Direction', 
                    'Confidence', 
                    'Entry_Price', 
                    'Stop_Loss', 
                    'Take_Profit', 
                    'Reason'
                ])

    def log_signal(self, signal: dict, asset: str = "XAU/USD"):
        """
        Logs a generated signal to the console and saves it to the local CSV history file.
        """
        if not signal:
            return
            
        # Format for Console
        timestamp = signal.get("timestamp", datetime.utcnow())
        if isinstance(timestamp, pd.Timestamp):
            timestamp = timestamp.to_pydatetime()
            
        time_str = timestamp.strftime('%Y-%m-%d %H:%M GMT')
        dir_str = signal.get("direction", "WAIT")
        conf = signal.get("confidence", 0)
        percentage = f"{int(conf * 100)}%" if conf <= 1.0 else f"{int((conf/5)*100)}%"
        
        entry = signal.get("entry_price", 0.0)
        sl = signal.get("sl", 0.0)
        tp = signal.get("tp", 0.0)
        reason = signal.get("reason", "")
        emoji = signal.get("emoji", "")
        
        console_msg = (
            f"\n{'='*60}\n"
            f"💰 NEW SIGNAL GENERATED 💰\n"
            f"Asset: {asset}\n"
            f"Time:  [{time_str}]\n"
            f"Trade: {emoji} {dir_str} (Confidence: {percentage})\n"
            f"Entry: {entry}\n"
            f"SL:    {sl} (ATR-based)\n"
            f"TP:    {tp} (R:R 1:3)\n"
            f"Note:  {reason}\n"
            f"{'='*60}\n"
        )
        logger.info(console_msg)

        # Save to CSV
        try:
            with open(self.filepath, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    time_str,
                    asset,
                    dir_str,
                    conf,
                    entry,
                    sl,
                    tp,
                    f"{reason} {emoji}"
                ])
        except Exception as e:
            logger.error(f"Failed to write signal to CSV: {e}")

        # Save to Supabase Cloud Database Let Supabase handle the exact created_at timestamp
        if hasattr(self, 'supabase') and self.supabase:
            try:
                db_payload = {
                    "direction": dir_str,
                    "confidence": conf,
                    "entry_price": entry,
                    "sl": sl,
                    "tp": tp,
                    "reason": reason,
                    "emoji": emoji,
                }
                
                # Use signal timestamp as created_at for historical accuracy
                if "timestamp" in signal:
                    ts = signal["timestamp"]
                    if isinstance(ts, pd.Timestamp):
                        ts = ts.to_pydatetime()
                    db_payload["created_at"] = ts.isoformat()

                # Add metadata
                if "timeframe" in signal:
                    db_payload["timeframe"] = signal["timeframe"]
                if "strategy" in signal:
                    db_payload["strategy"] = signal["strategy"]
                
                self.supabase.table("signals").insert(db_payload).execute()
                logger.info("🚀 Signal synchronized to Supabase Cloud successfully!")
            except Exception as e:
                logger.error(f"Failed to push signal to Supabase: {e}")

    def get_daily_count(self) -> int:
        """
        Returns the number of signals already generated today (UTC).
        """
        if not hasattr(self, 'supabase') or not self.supabase:
            return 0
            
        try:
            # Start of today in ISO format (UTC)
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            
            # Select signals created today
            response = self.supabase.table("signals").select("id").gt("created_at", today_start).execute()
            count = len(response.data) if response.data else 0
            logger.info(f"📊 Daily Signal Count: {count}")
            return count
        except Exception as e:
            logger.error(f"Failed to fetch daily signal count: {e}")
            return 0
