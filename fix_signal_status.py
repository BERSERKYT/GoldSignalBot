import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

def fix_signals():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    supabase = create_client(url, key)
    
    # 1. Manually close the user-reported trade
    target_id = "5321f04f-a7f9-443f-b3da-f9cb905965c1"
    res = supabase.table("signals").update({
        "status": "LOSS",
        "close_price": 5233.6
    }).eq("id", target_id).execute()
    
    if res.data:
        print(f"✅ Fixed Signal {target_id}: Marked as LOSS.")
    else:
        print(f"❌ Failed to find/update Signal {target_id}.")

    # 2. Check for other old pending signals that might be dead
    # Based on the list:
    # 02371de5... created 2026-03-03. BUY 5105.3, SL 4940.3
    # 5e6a63ea... created 2026-03-05. BUY 5077.6, SL 4989.1
    # Current price is 5185. These are in profit! But maybe they hit SL earlier?
    
    # For now, let's just fix the one the user specifically asked for.
    # The new 1m SyncEngine will handle the rest in the next scan.

if __name__ == "__main__":
    fix_signals()
