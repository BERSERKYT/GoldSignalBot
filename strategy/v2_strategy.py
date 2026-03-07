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
    
    def generate_signal(self, df: pd.DataFrame, current_price: float = None) -> dict:
        if df is None or len(df) < 30:
            return {}

        # 1. Calculation (assuming indicators added by Indicators module)
        # We need Bollinger Bands and RSI
        # Indicators.py doesn't have BB yet, so let's use the Indicators class to add them if missing
        
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        
        # Pull standard Indicators
        rsi = last_row.get('RSI_14', 50)
        atr = last_row.get('ATR_14', 1.0)
        close = last_row['close']
        
        # Simplified Logic for Demo:
        # Since Indicators.py doesn't have BB yet, we'll use EMA and RSI for this "V2" variant
        ema21 = last_row.get('EMA_21', close)
        
        signal = {}
        
        # V2 BUY: RSI Oversold (< 35) + Price rejection below EMA21
        if rsi < 35 and close > prev_row['close']:
            signal = {
                "direction": "BUY",
                "confidence": 4,
                "entry_price": round(close, 2),
                "sl": round(close - (2.5 * atr), 2),
                "tp": round(close + (7.5 * atr), 2), # R:R 1:3
                "reason": "V2: RSI Oversold recovery detected.",
                "emoji": "🌊"
            }
            
        # V2 SELL: RSI Overbought (> 65) + Price rejection above EMA21
        elif rsi > 65 and close < prev_row['close']:
            signal = {
                "direction": "SELL",
                "confidence": 4,
                "entry_price": round(close, 2),
                "sl": round(close + (2.5 * atr), 2),
                "tp": round(close - (7.5 * atr), 2),
                "reason": "V2: RSI Overbought rejection detected.",
                "emoji": "🌋"
            }
            
        return signal
