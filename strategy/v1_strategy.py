from .base import BaseStrategy
from typing import Dict, Any, Optional
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class V1Strategy(BaseStrategy):
    """
    V1 Core Strategy for Gold XAU/USD
    
    BUY rules:
      - EMA9 crosses above EMA21
      - RSI(14) > 50
      - current ATR(14) > 20-period average ATR (volatility check)
      
    SELL rules:
      - EMA9 crosses below EMA21
      - RSI(14) < 50
      - current ATR(14) > 20-period average ATR
      
    Confidence (1-5):
      - 4-5 if RSI is in healthy zone (55-70 for BUY, 30-45 for SELL)
      - lower otherwise
      
    Risk Management:
      - Stop Loss (SL) = ATR(14) * 1.5
      - Take Profit (TP) = SL_distance * 3 (Risk:Reward 1:3)
    """
    def __init__(self):
        super().__init__(name="V1_Trend_Volatility")

    def generate_signal(self, df: pd.DataFrame, current_price: float = None) -> Optional[Dict[str, Any]]:
        if df is None or len(df) < 50:
            logger.warning("Not enough data to generate signal.")
            return None
            
        required_cols = ['EMA_9', 'EMA_21', 'RSI_14', 'ATR_14', 'ATR_14_MA_20', 'close']
        for col in required_cols:
            if col not in df.columns:
                logger.error(f"Missing indicator column: {col}. Run Indicators module first.")
                return None
                
        # Get the two most recent finalized candles (or current if running intray-bar, but usually we evaluate closed bars)
        latest = df.iloc[-1]
        previous = df.iloc[-2]
        
        # Determine cross conditions
        # Buy Cross: EMA9 previously below EMA21, but now above EMA21
        buy_cross = (previous['EMA_9'] <= previous['EMA_21']) and (latest['EMA_9'] > latest['EMA_21'])
        
        # Sell Cross: EMA9 previously above EMA21, but now below EMA21
        sell_cross = (previous['EMA_9'] >= previous['EMA_21']) and (latest['EMA_9'] < latest['EMA_21'])
        
        # Volatility condition
        high_volatility = latest['ATR_14'] > latest['ATR_14_MA_20']
        
        # Entry price (use latest close if current_price not explicitly provided)
        entry = current_price if current_price else latest['close']
        
        direction = "WAIT"
        confidence = 0
        sl = 0.0
        tp = 0.0
        reason = ""
        emoji = ""
        
        # --- Evaluate BUY ---
        if buy_cross and latest['RSI_14'] > 50 and high_volatility:
            direction = "BUY"
            
            # Confidence logic
            if 55 <= latest['RSI_14'] <= 70:
                confidence = 5
                reason = "Strong bullish EMA cross + ideal RSI healthy zone + high volatility"
            else:
                confidence = 3
                reason = "Bullish EMA cross + RSI > 50 + high volatility (RSI slightly tight/extreme)"
            emoji = "🟢"
            
            # Risk Management
            sl_distance = latest['ATR_14'] * 1.5
            sl = entry - sl_distance
            tp = entry + (sl_distance * 3) # R:R 1:3
            
        # --- Evaluate SELL ---
        elif sell_cross and latest['RSI_14'] < 50 and high_volatility:
            direction = "SELL"
            
            # Confidence logic
            if 30 <= latest['RSI_14'] <= 45:
                confidence = 5
                reason = "Strong bearish EMA cross + ideal RSI healthy zone + high volatility"
            else:
                confidence = 3
                reason = "Bearish EMA cross + RSI < 50 + high volatility (RSI slightly tight/extreme)"
            emoji = "🔴"
            
            # Risk Management
            sl_distance = latest['ATR_14'] * 1.5
            sl = entry + sl_distance
            tp = entry - (sl_distance * 3) # R:R 1:3
            
        if direction == "WAIT":
            return None # We return None for WAIT to avoid spamming the log.
            
        return {
            "direction": direction,
            "confidence": confidence,
            "entry_price": round(entry, 2),
            "sl": round(sl, 2),
            "tp": round(tp, 2),
            "reason": reason,
            "emoji": emoji,
            "timestamp": latest.get('timestamp', pd.Timestamp.now(tz="UTC"))
        }

if __name__ == "__main__":
    # Test script will be provided later
    pass
