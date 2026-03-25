import os
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

def main():
    load_dotenv()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("Error: Supabase credentials missing.")
        return

    supabase: Client = create_client(url, key)
    
    # Fetch all finalized signals
    response = supabase.table("signals").select("strategy, status").execute()
    data = response.data
    
    if not data:
        print("No signal data found in Supabase.")
        return
        
    df = pd.DataFrame(data)
    
    # Group by strategy and calculate stats
    stats = []
    for strat in df['strategy'].unique():
        strat_df = df[df['strategy'] == strat]
        total = len(strat_df)
        wins = len(strat_df[strat_df['status'] == 'WIN'])
        losses = len(strat_df[strat_df['status'] == 'LOSS'])
        pendings = len(strat_df[strat_df['status'] == 'PENDING'])
        
        win_rate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0
        loss_rate = (losses / (wins + losses)) * 100 if (wins + losses) > 0 else 0
        
        stats.append({
            "Strategy": strat,
            "Total": total,
            "Wins": wins,
            "Losses": losses,
            "Pending": pendings,
            "WinRate": f"{win_rate:.1f}%",
            "LossRate": f"{loss_rate:.1f}%",
            "RawLossRate": loss_rate
        })
        
    stats_df = pd.DataFrame(stats).sort_values(by="RawLossRate", ascending=False)
    print("\n--- Strategy Performance Audit ---")
    print(stats_df.to_string(index=False))
    
    if not stats_df.empty:
        worst = stats_df.iloc[0]['Strategy']
        print(f"\nWorst Strategy to remove: {worst}")

if __name__ == "__main__":
    main()
