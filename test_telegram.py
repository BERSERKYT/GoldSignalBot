import os
import requests
from dotenv import load_dotenv

def test_telegram():
    load_dotenv()
    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    print(f"--- Telegram Diagnostic ---")
    print(f"Token present: {'Yes' if bot_token else 'No'}")
    print(f"Chat ID present: {'Yes' if chat_id else 'No'}")
    
    if not bot_token or not chat_id:
        print("❌ Error: Missing credentials in .env")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": "🧪 GoldSignalBot: Telegram Diagnostic Test Message.\nIf you see this, your credentials are correct!"
    }
    
    print(f"Sending test message to {chat_id}...")
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("✅ Success! Check your Telegram.")
        else:
            print(f"❌ API Error ({response.status_code}): {response.text}")
            if response.status_code == 401:
                print("   Hint: Your BOT_TOKEN might be invalid.")
            elif response.status_code == 400:
                print("   Hint: Your CHAT_ID might be invalid or the bot hasn't been started by you.")
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    test_telegram()
