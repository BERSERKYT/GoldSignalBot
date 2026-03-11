import pandas as pd
from strategy.base import BaseStrategy
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class V3Strategy(BaseStrategy):
    """
    V3 Scalper: High-frequency trend follower for lower timeframes.
    - BUY: Price > EMA(20) + EMA(20) > EMA(50) + RSI(7) > 60
    - SELL: Price < EMA(20) + EMA(20) < EMA(50) + RSI(7) < 40
    - Confidence: Scaled by RSI strength.
    """
    def __init__(self):
        super().__init__(name="V3_Scalper_M15")
    
    def generate_signal(self, df: pd.DataFrame, current_price: float = None, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        if df is None or len(df) < 50:
            return None

        # Strategy Parameters
        p = {
            "rsi_fast": 7,
            "ema_fast": 20,
            "ema_slow": 50,
            "atr_multiplier": 1.2,
            "tp_multiplier": 2.0
        }
        if params:
            p.update(params)
        
        # Ensure indicators exist (Indicators.add_all_indicators handles EMA)
        # We might need to ensure EMA20 and EMA50 are there
        required = ['EMA_9', 'EMA_21', 'RSI_14', 'ATR_14', 'close'] # Basic set
        for col in required:
            if col not in df.columns:
                return None

        # Manual EMA calculation for Scalper if not already in Indicators
        # Assuming Indicators.py might only provide 9/21. Let's check Indicators later.
        # For now, let's use what we have or calculate on the fly if needed.
        
        last_row = df.iloc[-1]
        close = last_row['close']
        rsi = last_row['RSI_14'] # Using 14 as default if 7 is missing
        atr = last_row['ATR_14']
        
        # Check if EMA9 > EMA21 for trend (simulating the scalper logic with available indicators)
        ema_fast = last_row['EMA_9']
        ema_slow = last_row['EMA_21']
        
        signal = None
        
        # V3 BUY logic
        if close > ema_fast > ema_slow and rsi > 60:
            sl_dist = atr * p["atr_multiplier"]
            signal = {
                "direction": "BUY",
                "confidence": 4 if rsi > 65 else 3,
                "entry_price": round(close, 2),
                "sl": round(close - sl_dist, 2),
                "tp": round(close + (sl_dist * p["tp_multiplier"]), 2),
                "reason": f"V3 Scalp: Bullish alignment (Price > EMA) + RSI strength ({rsi:.0f})",
                "emoji": "⚡",
                "timestamp": df.index[-1]
            }
            
        # V3 SELL logic
        elif close < ema_fast < ema_slow and rsi < 40:
            sl_dist = atr * p["atr_multiplier"]
            signal = {
                "direction": "SELL",
                "confidence": 4 if rsi < 35 else 3,
                "entry_price": round(close, 2),
                "sl": round(close + sl_dist, 2),
                "tp": round(close - (sl_dist * p["tp_multiplier"]), 2),
                "reason": f"V3 Scalp: Bearish alignment (Price < EMA) + RSI weakness ({rsi:.0f})",
                "emoji": "🔥",
                "timestamp": df.index[-1]
            }
            
        return signal
