import os
import requests
import logging
from typing import Dict, Any

logger = logging.getLogger("TelegramNotifier")

class TelegramNotifier:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.enabled = bool(self.bot_token and self.chat_id)
        
        if not self.enabled:
            logger.warning("⚠️ Telegram credentials missing. Notifications disabled.")

    def send_signal(self, signal: Dict[str, Any]):
        """
        Sends a formatted trading signal to Telegram with an MT5 deep link.
        """
        if not self.enabled:
            return

        direction_emoji = "🟢 BUY" if signal['direction'] == "BUY" else "🔴 SELL"
        
        # MT5 Deep Link logic:
        # mt5://trade?symbol=XAUUSD&type=buy&volume=0.1&stoploss=...&takeprofit=...
        # Note: Brokers use different symbols (XAUUSD, GOLD, XAUUSD.m)
        symbol = "XAUUSD" 
        
        message = (
            f"🚀 **GOLD SIGNAL DETECTED** 🚀\n\n"
            f"**Action:** {direction_emoji}\n"
            f"**Entry:** {signal['entry_price']}\n"
            f"**TP:** {signal['tp']}\n"
            f"**SL:** {signal['sl']}\n\n"
            f"🧠 **AI Context:**\n_{signal['reason']}_\n\n"
            f"📊 **Timeframe:** {signal.get('timeframe', 'Unknown')}\n"
            f"⚡ **Confidence:** {signal['confidence']}/5"
        )

        # Telegram API URL
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        
        # Inline Keyboard for MT5 Deep Link
        # Note: Deep link format can vary by OS, but standard MT5 link is often:
        # mql5.com/en/market-mobile-trading
        # For a truly direct trade link, we use a custom URL scheme if supported.
        # Otherwise, a button to open MT5 is best.
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "reply_markup": {
                "inline_keyboard": [[
                    {"text": "📱 Open MetaTrader 5", "url": "https://www.mql5.com/en/mobile-trading"}
                ]]
            }
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info("✅ Telegram signal sent successfully.")
            else:
                logger.error(f"❌ Telegram API Error: {response.text}")
        except Exception as e:
            logger.error(f"❌ Failed to send Telegram message: {e}")

if __name__ == "__main__":
    # Test
    from dotenv import load_dotenv
    load_dotenv()
    notifier = TelegramNotifier()
    test_sig = {
        "direction": "BUY",
        "entry_price": 2040.50,
        "tp": 2060.00,
        "sl": 2030.00,
        "reason": "AI Test Signal",
        "confidence": 5,
        "timeframe": "1h"
    }
    notifier.send_signal(test_sig)
