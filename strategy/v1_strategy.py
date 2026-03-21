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

    def generate_signal(self, df: pd.DataFrame, current_price: float = None, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        if df is None or len(df) < 50:
            logger.warning("Not enough data to generate signal.")
            return None
            
        # Strategy Parameters (Default vs Sharpened)
        p = {
            "rsi_buy": 50,
            "rsi_sell": 50,
            "rsi_healthy_buy_low": 55,
            "rsi_healthy_buy_high": 70,
            "rsi_healthy_sell_low": 30,
            "rsi_healthy_sell_high": 45,
            "atr_multiplier": 1.5,
            "min_confidence": 3
        }
        if params:
            p.update(params)

        required_cols = ['EMA_9', 'EMA_21', 'RSI_14', 'ATR_14', 'ATR_14_MA_20', 'close']
        for col in required_cols:
            if col not in df.columns:
                logger.error(f"Missing indicator column: {col}. Run Indicators module first.")
                return None
                
        # Get the two most recent finalized candles
        latest = df.iloc[-1]
        previous = df.iloc[-2]
        
        # Determine cross conditions
        buy_cross = (previous['EMA_9'] <= previous['EMA_21']) and (latest['EMA_9'] > latest['EMA_21'])
        sell_cross = (previous['EMA_9'] >= previous['EMA_21']) and (latest['EMA_9'] < latest['EMA_21'])
        
        # Volatility condition
        high_volatility = latest['ATR_14'] > (latest['ATR_14_MA_20'] * 0.95) # Slight buffer
        
        # Entry price
        entry = current_price if current_price else latest['close']
        
        direction = "WAIT"
        confidence = 0
        sl = 0.0
        tp = 0.0
        reason = ""
        emoji = ""
        
        # --- Evaluate BUY ---
        if buy_cross and latest['RSI_14'] > p["rsi_buy"] and high_volatility:
            direction = "BUY"
            
            # 🧠 NEW: Decimal Confidence (0.0 - 1.0)
            base_conf = 0.8  # Floor is 80%
            rsi_bonus = 0.1 if p["rsi_healthy_buy_low"] <= latest['RSI_14'] <= p["rsi_healthy_buy_high"] else 0.0
            volat_bonus = 0.1 if latest['ATR_14'] > (latest['ATR_14_MA_20'] * 1.5) else 0.0
            
            confidence = round(base_conf + rsi_bonus + volat_bonus, 2)
            reason = f"V1: EMA Cross + RSI {latest['RSI_14']:.1f} + Volat Factor {latest['ATR_14']/latest['ATR_14_MA_20']:.1f}x"
            emoji = "🟢"
            
            # Risk Management
            sl_distance = latest['ATR_14'] * p["atr_multiplier"]
            sl = entry - sl_distance
            tp = entry + (sl_distance * 3) # R:R 1:3
            
        # --- Evaluate SELL ---
        elif sell_cross and latest['RSI_14'] < p["rsi_sell"] and high_volatility:
            direction = "SELL"
            
            # 🧠 NEW: Decimal Confidence (0.0 - 1.0)
            base_conf = 0.8  # Floor is 80%
            rsi_bonus = 0.1 if p["rsi_healthy_sell_low"] <= latest['RSI_14'] <= p["rsi_healthy_sell_high"] else 0.0
            volat_bonus = 0.1 if latest['ATR_14'] > (latest['ATR_14_MA_20'] * 1.5) else 0.0
            
            confidence = round(base_conf + rsi_bonus + volat_bonus, 2)
            reason = f"V1: EMA Cross + RSI {latest['RSI_14']:.1f} + Volat Factor {latest['ATR_14']/latest['ATR_14_MA_20']:.1f}x"
            emoji = "🔴"
            
            # Risk Management
            sl_distance = latest['ATR_14'] * p["atr_multiplier"]
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
