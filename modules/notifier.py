import os
import requests
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("TelegramNotifier")

class TelegramNotifier:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.enabled = bool(self.bot_token and self.chat_id)
        
        if not self.enabled:
            logger.warning("⚠️ Telegram credentials missing. Notifications disabled.")

    def _send(self, message: str, reply_markup: Optional[dict] = None):
        """Core helper to send any message (Plaintext for stability)."""
        if not self.enabled:
            return
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message
            # Removed parse_mode: Markdown to avoid recurring crashes with special characters
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info("✅ Telegram message sent successfully.")
            else:
                logger.error(f"❌ Telegram API Error: {response.text}")
        except Exception as e:
            logger.error(f"❌ Failed to send Telegram message: {e}")

    def send_heartbeat(self, price: float, ai_status: str, timeframe: str):
        """Sends a 'Bot is Alive' ping at startup."""
        message = (
            f"🤖 GoldSignalBot Online\n\n"
            f"📡 Scan started successfully.\n"
            f"💰 Gold Price: ${price:,.2f}\n"
            f"🧠 AI Status: {ai_status}\n"
            f"📊 Timeframe: {timeframe}\n\n"
            f"Scanning market for high-confidence setups..."
        )
        self._send(message)

    def send_no_signal(self, timeframe: str, strategy: str):
        """Notifies user no signal was found."""
        message = (
            f"🔍 Scan Complete - No Signal\n\n"
            f"Strategy {strategy.upper()} on {timeframe} found no setup this hour.\n"
            f"Market conditions do not align with criteria.\n\n"
            f"✅ Bot is healthy and will scan again next hour."
        )
        self._send(message)

    def send_signal(self, signal: Dict[str, Any]):
        """Sends a formatted trading alert with direct MT5 app link."""
        direction = signal['direction']
        dir_emoji = "🟢 BUY" if direction == "BUY" else "🔴 SELL"
        reason = signal.get('reason', 'AI Confluence Detected')
        tf = signal.get('timeframe', '4h')
        
        # Build Universal Redirect Link (HTTPS is clickable everywhere)
        action = direction.lower()
        sl = signal['sl']
        tp = signal['tp']
        
        # Link to our bridge page on the dashboard
        mt5_bridge = f"https://gold-signal-bot.vercel.app/mt5.html?action={action}&symbol=XAUUSD&sl={sl}&tp={tp}"

        message = (
            f"🚨 GOLD SIGNAL DETECTED 🚨\n\n"
            f"Action: {dir_emoji}\n"
            f"Entry: ${signal['entry_price']:,.2f}\n"
            f"Take Profit: ${tp:,.2f} ✅\n"
            f"Stop Loss: ${sl:,.2f} 🛑\n\n"
            f"🔗 ONE-TAP ENTRY (Click to open App):\n"
            f"{mt5_bridge}\n\n"
            f"🧠 Analysis:\n{reason}\n\n"
            f"📊 TF: {tf} | Confidence: {signal.get('confidence', '?')}/5\n\n"
            f"⚠️ Trade at your own risk."
        )
        
        keyboard = {
            "inline_keyboard": [[
                {"text": "📊 View Dashboard", "url": "https://gold-signal-bot.vercel.app"}
            ]]
        }
        self._send(message, reply_markup=keyboard)
