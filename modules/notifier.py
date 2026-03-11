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
        """Core helper to send any message."""
        if not self.enabled:
            return
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown"
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
        """Sends a 'Bot is Alive' ping at startup so user knows it ran."""
        message = (
            f"🤖 *GoldSignalBot Online*\n\n"
            f"📡 Scan started successfully.\n"
            f"💰 Gold Price: *${price:,.2f}*\n"
            f"🧠 AI Status: _{ai_status}_\n"
            f"📊 Timeframe: `{timeframe}`\n\n"
            f"_Scanning market for high-confidence setups..._"
        )
        self._send(message)

    def send_no_signal(self, timeframe: str, strategy: str):
        """Notifies user that the scan ran but no actionable signal was found."""
        message = (
            f"🔍 *Scan Complete — No Signal*\n\n"
            f"Strategy `{strategy.upper()}` on `{timeframe}` found no setup this hour.\n"
            f"_Market conditions do not align with entry criteria yet._\n\n"
            f"✅ Bot is healthy and will scan again next hour."
        )
        self._send(message)

    def send_signal(self, signal: Dict[str, Any]):
        """Sends a formatted trading signal alert with MT5 deeplink button."""
        direction_emoji = "🟢 BUY" if signal['direction'] == "BUY" else "🔴 SELL"

        message = (
            f"🚨 *GOLD SIGNAL DETECTED* 🚨\n\n"
            f"*Action:* {direction_emoji}\n"
            f"*Entry:* `${signal['entry_price']:,.2f}`\n"
            f"*Take Profit:* `${signal['tp']:,.2f}` ✅\n"
            f"*Stop Loss:* `${signal['sl']:,.2f}` 🛑\n\n"
            f"🧠 *Analysis:*\n_{signal.get('reason', 'AI Confluence Detected')}_\n\n"
            f"📊 Timeframe: `{signal.get('timeframe', '?')}` | "
            f"⚡ Confidence: `{signal.get('confidence', '?')}/5`\n\n"
            f"⚠️ _This is a signal, not financial advice. Use proper risk management._"
        )
        
        keyboard = {
            "inline_keyboard": [[
                {"text": "📱 Trade on MT5 (App)", "url": "https://t.me/mt5_bot"},
                {"text": "📊 View Dashboard", "url": "https://gold-signal-bot.vercel.app"}
            ]]
        }
        self._send(message, reply_markup=keyboard)
