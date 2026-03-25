import os
from supabase import create_client
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

def list_pending_signals():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    supabase = create_client(url, key)
    
    res = supabase.table("signals").select("*").eq("status", "PENDING").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        print("Pending Signals:")
        print(df[['id', 'direction', 'entry_price', 'tp', 'sl', 'created_at']])
    else:
        print("No pending signals found.")

if __name__ == "__main__":
    list_pending_signals()
