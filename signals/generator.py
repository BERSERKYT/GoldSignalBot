"""
GoldSignalBot – signals/generator.py
======================================
Handles formatting, logging, and displaying of trading signals.

Features:
  - English and French language support based on config.
  - Console output formatting (clean and readable).
  - CSV logging to logs/signals.csv.
"""

import os
import csv
import logging
import configparser
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_PATH  = _PROJECT_ROOT / "config.ini"
_LOGS_DIR     = _PROJECT_ROOT / "logs"

config = configparser.ConfigParser()
config.read(_CONFIG_PATH)

# Ensure logs directory exists
os.makedirs(_LOGS_DIR, exist_ok=True)


class SignalGenerator:
    """
    Formats and logs trading signals.
    """

    def __init__(self):
        self.language = config.get("general", "language", fallback="en").lower()
        self.csv_path = _LOGS_DIR / "signals.csv"
        
        # Initialize CSV with headers if it doesn't exist
        if not self.csv_path.exists():
            with open(self.csv_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp_utc", "direction", "confidence", 
                    "entry", "sl", "tp", "reason"
                ])

    def process_signal(self, signal: Optional[Dict[str, Any]]):
        """
        Process a signal dict returned by a Strategy.
        If signal is None, logs a WAIT status.
        Otherwise, displays the signal and logs it to CSV.
        """
        if not signal:
            self._print_wait()
            return

        # 1. Format for display
        display_str = self._format_signal(signal)
        
        # 2. Print to console
        print(f"\n{'=' * 80}")
        print(display_str)
        print(f"{'=' * 80}\n")
        
        # 3. Save to CSV
        self._log_to_csv(signal)

    def _print_wait(self):
        """Print a quiet WAIT status to console."""
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        if self.language == "fr":
            msg = f"[{now_str} UTC] WAIT | Aucune configuration valide sur XAU/USD."
        else:
            msg = f"[{now_str} UTC] WAIT | No valid setup on XAU/USD right now."
            
        logger.info("Signal Status: %s", msg)

    def _format_signal(self, signal: Dict[str, Any]) -> str:
        """Format the signal dict into a readable English or French string."""
        ts = signal["timestamp"]
        if isinstance(ts, pd.Timestamp):
            ts_str = ts.strftime("%Y-%m-%d %H:%M UTC")
        else:
            ts_str = str(ts)
            
        direction = signal["direction"].upper()
        conf = signal["confidence"]
        entry = signal["entry"]
        sl = signal["sl"]
        tp = signal["tp"]
        
        # Determine R:R dynamically for display
        sl_dist = abs(entry - sl)
        tp_dist = abs(tp - entry)
        rr = tp_dist / sl_dist if sl_dist > 0 else 0
        
        reason_en = signal.get("reason", "")
        reason_fr = self._translate_reason_to_fr(reason_en)
        
        reason = reason_fr if self.language == "fr" else reason_en

        if self.language == "fr":
            return (
                f"[{ts_str}] {direction} | Confiance: {conf}/5\n"
                f"🪙 Entrée XAU/USD: {entry:.2f}\n"
                f"🛑 Stop Loss (SL): {sl:.2f}\n"
                f"🎯 Take Profit (TP): {tp:.2f} (R:R 1:{rr:.1f})\n"
                f"📝 Raison: {reason}"
            )
        else:
            return (
                f"[{ts_str}] {direction} | Confidence: {conf}/5\n"
                f"🪙 XAU/USD Entry: {entry:.2f}\n"
                f"🛑 Stop Loss (SL): {sl:.2f}\n"
                f"🎯 Take Profit (TP): {tp:.2f} (R:R 1:{rr:.1f})\n"
                f"📝 Reason: {reason}"
            )

    def _log_to_csv(self, signal: Dict[str, Any]):
        """Append signal data to logs/signals.csv"""
        ts = signal["timestamp"]
        if isinstance(ts, pd.Timestamp):
            ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
        else:
            ts_str = str(ts)
            
        row = [
            ts_str,
            signal["direction"],
            signal["confidence"],
            signal["entry"],
            signal["sl"],
            signal["tp"],
            signal.get("reason", "").replace(",", ";") # Avoid CSV commas in reason
        ]
        
        try:
            with open(self.csv_path, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(row)
            logger.debug("Signal logged to CSV.")
        except IOError as e:
            logger.error("Failed to write to signals.csv: %s", e)

    def _translate_reason_to_fr(self, text: str) -> str:
        """
        Simple keyword replacement for V1 strategy reasons.
        For a production app with infinite variations, grab an i18n library.
        """
        t = text
        t = t.replace("Bullish", "Haussier")
        t = t.replace("Bearish", "Baissier")
        t = t.replace("Cross", "Croisement")
        t = t.replace("Expansion", "en expansion")
        t = t.replace("ATR-based", "Basé sur ATR")
        t = t.replace("post-news calm", "calme post-annonce")
        return t
