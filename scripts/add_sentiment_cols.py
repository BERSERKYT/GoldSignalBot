import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

def add_sentiment_columns():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    supabase: Client = create_client(url, key)
    
    print("Attempting to add sentiment_score and sentiment_label to 'settings' table...")
    
    # Since we can't run ALTER TABLE directly via DB client, we'll try to update a test row 
    # and see if it fails (indicating missing columns).
    # However, the best way is for the user to run SQL.
    # I'll provide the SQL and also attempt an RPC if one exists (unlikely).
    
    # Let's provide the SQL instructions.
    sql = """
    ALTER TABLE settings ADD COLUMN IF NOT EXISTS sentiment_score FLOAT DEFAULT 0;
    ALTER TABLE settings ADD COLUMN IF NOT EXISTS sentiment_label TEXT DEFAULT 'NEUTRAL';
    """
    
    print("\n--- SQL INSTRUCTIONS ---")
    print("Please run the following in your Supabase SQL Editor:")
    print(sql)
    print("------------------------\n")
    
    # Fallback: check if we can update
    try:
        supabase.table("settings").update({"sentiment_score": 0}).eq("id", 1).execute()
        print("✅ Columns seem to exist or update succeeded!")
    except Exception as e:
        print(f"❌ Columns likely missing: {e}")

if __name__ == "__main__":
    add_sentiment_columns()
