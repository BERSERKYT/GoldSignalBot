import os
from supabase import create_client
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

def get_v4_stats():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("Missing Supabase credentials.")
        return

    sb = create_client(url, key)
    
    print("Fetching V4 signals from Supabase...")
    # Fetch all signals
    # We filter by checking if reason contains 'V4' or 'SMC' or emoji is '💎' or strategy='v4'
    response = sb.table("signals").select("*").execute()
    data = response.data
    
    if not data:
        print("No signals found in the database.")
        return

    df = pd.DataFrame(data)
    
    # Filter for V4 specifically:
    # 1. strategy column == 'v4' 
    # 2. Or reason contains 'V4'
    # 3. Or emoji == '💎'
    mask = (
        (df.get('strategy') == 'v4') |
        (df['reason'].str.contains('V4', case=False, na=False)) |
        (df['emoji'] == '💎')
    )
    v4_df = df[mask]
    
    print("=" * 40)
    print("V4 (PRO SMC/ICT) OVERALL STATS")
    print("=" * 40)
    
    if v4_df.empty:
        print("No V4 signals have been generated or backfilled yet.")
        return
        
    total = len(v4_df)
    status_counts = v4_df['status'].value_counts()
    
    wins = status_counts.get('WIN', 0)
    losses = status_counts.get('LOSS', 0)
    pending = status_counts.get('PENDING', 0)
    
    resolved = wins + losses
    win_rate = (wins / resolved * 100) if resolved > 0 else 0
    
    print(f"Total V4 Signals: {total}")
    print(f"Resolved Trades:  {resolved}")
    print(f"Pending Trades:   {pending}")
    print(f"Wins:             {wins}")
    print(f"Losses:           {losses}")
    print(f"Win Rate:         {win_rate:.2f}%")
    print("-" * 40)
    
    # Breakdown by Direction
    buy_v4 = v4_df[v4_df['direction'] == 'BUY']
    sell_v4 = v4_df[v4_df['direction'] == 'SELL']
    
    print(f"BUY Signals:  {len(buy_v4)} (Wins: {sum(buy_v4['status']=='WIN')}, Losses: {sum(buy_v4['status']=='LOSS')})")
    print(f"SELL Signals: {len(sell_v4)} (Wins: {sum(sell_v4['status']=='WIN')}, Losses: {sum(sell_v4['status']=='LOSS')})")
    print("=" * 40)

if __name__ == "__main__":
    get_v4_stats()
