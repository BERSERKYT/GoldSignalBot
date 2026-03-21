import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

print("Attempting to add smart_lots_enabled and risk_percentage to settings table...")

try:
    # We update row id=1 with the new keys. Supabase may reject if columns don't exist
    res = supabase.table("settings").update({
        "smart_lots_enabled": False,
        "risk_percentage": 1.0
    }).eq("id", 1).execute()
    print("Success! Response:", res.data)
except Exception as e:
    print("Error during update:", e)
    print("If you get a PGRST204 error, you need to manually add the columns in Supabase UI.")
