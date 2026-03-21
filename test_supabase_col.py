import os
from dotenv import load_dotenv
from supabase import create_client, Client

def check_supabase():
    load_dotenv()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    supabase: Client = create_client(url, key)
    
    print("Testing update to settings table with 'notifier_status'...")
    try:
        res = supabase.table("settings").update({"notifier_status": "ENABLED"}).eq("id", 1).execute()
        print("Update response:", res.data)
    except Exception as e:
        print(f"Error during update: {e}")

if __name__ == "__main__":
    check_supabase()
