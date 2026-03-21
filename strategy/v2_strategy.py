import pandas as pd
from strategy.base import BaseStrategy

class V2Strategy(BaseStrategy):
    """
    V2 Strategy: Mean Reversion / Breakout using Bollinger Bands & RSI.
    - BUY: Price crosses below Lower Band + RSI < 30 (Oversold)
    - SELL: Price crosses above Upper Band + RSI > 70 (Overbought)
    - Confidence: Based on the strength of the RSI signal.
    """
    def __init__(self):
        super().__init__(name="V2_RSI_Mean_Reversion")
    
    def generate_signal(self, df: pd.DataFrame, current_price: float = None, params: dict = None) -> dict:
        if df is None or len(df) < 30:
            return {}

        # Strategy Parameters (Default vs Sharpened)
        p = {
            "rsi_oversold": 35,
            "rsi_overbought": 65,
            "atr_multiplier": 2.5
        }
        if params:
            p.update(params)
        
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        
        # Pull standard Indicators
        rsi = last_row.get('RSI_14', 50)
        atr = last_row.get('ATR_14', 1.0)
        close = last_row['close']
        
        signal = None
        
        # V2 BUY: RSI Oversold (< 35) + Price rejection
        if rsi < p["rsi_oversold"] and close > prev_row['close']:
            base_conf = 0.8
            rsi_bonus = 0.1 if rsi < 25 else 0.0
            confidence = round(base_conf + rsi_bonus, 2)
            
            signal = {
                "direction": "BUY",
                "confidence": confidence,
                "entry_price": round(close, 2),
                "sl": round(close - (p["atr_multiplier"] * atr), 2),
                "tp": round(close + (p["atr_multiplier"] * 3 * atr), 2), 
                "reason": f"V2: RSI Oversold ({rsi:.1f}) + Bullish Rejection",
                "emoji": "🌊",
                "timestamp": df.index[-1]
            }
            
        # V2 SELL: RSI Overbought (> 65) + Price rejection
        elif rsi > p["rsi_overbought"] and close < prev_row['close']:
            base_conf = 0.8
            rsi_bonus = 0.1 if rsi > 75 else 0.0
            confidence = round(base_conf + rsi_bonus, 2)
            
            signal = {
                "direction": "SELL",
                "confidence": confidence,
                "entry_price": round(close, 2),
                "sl": round(close + (p["atr_multiplier"] * atr), 2),
                "tp": round(close - (p["atr_multiplier"] * 3 * atr), 2),
                "reason": f"V2: RSI Overbought ({rsi:.1f}) + Bearish Rejection",
                "emoji": "🌋",
                "timestamp": df.index[-1]
            }
            
        return signal
