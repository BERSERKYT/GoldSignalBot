import pandas as pd
from strategy.base import BaseStrategy
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class V5Strategy(BaseStrategy):
    """
    V5 Pure Structure & Confirmation Strategy
    Multi-timeframe logic:
    - Weekly/Daily for structure and bias (Swing Analysis)
    - 4H for identifying Areas of Interest (Support/Resistance)
    - 2H/1H for Candlestick Triggers (Engulfing / Morning/Evening Stars) at the AoI
    """
    def __init__(self, fetcher=None):
        super().__init__(name="V5_Strct_Conf")
        self.fetcher = fetcher

    def _get_swings(self, df: pd.DataFrame, left: int = 3, right: int = 3):
        """Identifies Swing Highs and Swing Lows in a DataFrame."""
        highs = []
        lows = []
        for i in range(left, len(df) - right):
            window = df.iloc[i-left:i+right+1]
            center = df.iloc[i]
            
            # Check for Swing High
            if center['high'] == window['high'].max():
                highs.append({"index": i, "time": df.index[i], "price": center['high']})
                
            # Check for Swing Low
            if center['low'] == window['low'].min():
                lows.append({"index": i, "time": df.index[i], "price": center['low']})
                
        return highs, lows

    def _determine_daily_bias(self, df_1d: pd.DataFrame) -> str:
        """Determines if the structural bias on the Daily is Bullish or Bearish."""
        highs, lows = self._get_swings(df_1d, left=3, right=3)
        if len(highs) < 2 or len(lows) < 2:
            return "NEUTRAL"
        
        # Last two swing lows to check for a structural break
        last_low = lows[-1]['price']
        prev_low = lows[-2]['price']
        
        # Last two swing highs
        last_high = highs[-1]['price']
        prev_high = highs[-2]['price']
        
        latest_close = df_1d.iloc[-1]['close']
        
        # Simple MSS logic: If we broke a previous higher low, bias is bearish
        if last_low < prev_low and latest_close < prev_low:
            return "BEARISH"
        
        # If we broke a previous lower high, bias is bullish
        if last_high > prev_high and latest_close > prev_high:
            return "BULLISH"
            
        # Fallback to general sequence
        if last_high > prev_high and last_low > prev_low:
            return "BULLISH"
        if last_high < prev_high and last_low < prev_low:
            return "BEARISH"
            
        return "NEUTRAL"

    def _get_4h_zone(self, df_4h: pd.DataFrame, bias: str) -> Optional[Dict[str, float]]:
        """Finds the most recent relevant Support or Resistance zone based on bias."""
        highs, lows = self._get_swings(df_4h, left=5, right=3)
        
        if bias == "BEARISH" and len(highs) > 0:
            # We want to sell at Resistance (the last valid Swing High)
            res_price = highs[-1]['price']
            # Zone is price to roughly 0.15% below it
            return {"type": "RESISTANCE", "top": res_price, "bottom": res_price * 0.9985}
            
        elif bias == "BULLISH" and len(lows) > 0:
            # We want to buy at Support (the last valid Swing Low)
            sup_price = lows[-1]['price']
            # Zone is price to roughly 0.15% above it
            return {"type": "SUPPORT", "bottom": sup_price, "top": sup_price * 1.0015}
            
        return None

    def _check_candlestick_confirmation(self, df_1h: pd.DataFrame, bias: str) -> bool:
        """Looks for Engulfing or Evening/Morning Star on the execution timeframe."""
        if len(df_1h) < 4:
            return False
            
        c1 = df_1h.iloc[-1]   # Current (completed)
        c2 = df_1h.iloc[-2]   # Previous
        c3 = df_1h.iloc[-3]   # 2 bars ago
        
        # Bodies
        body1 = abs(c1['close'] - c1['open'])
        body2 = abs(c2['close'] - c2['open'])
        body3 = abs(c3['close'] - c3['open'])
        
        is_bull_c1 = c1['close'] > c1['open']
        is_bear_c1 = c1['close'] < c1['open']
        is_bull_c2 = c2['close'] > c2['open']
        is_bear_c2 = c2['close'] < c2['open']
        is_bull_c3 = c3['close'] > c3['open']
        
        if bias == "BEARISH":
            # Confirmation 1: Bearish Engulfing (c2 is Bullish, c1 is Bearish completely covering c2's body)
            if is_bull_c2 and is_bear_c1 and c1['open'] >= c2['close'] and c1['close'] <= c2['open']:
                return True
                
            # Confirmation 2: Evening Star
            if is_bull_c3 and is_bear_c1:
                # c2 is a small candle (star) above the bodies of c3 and c1
                if body2 < body3 * 0.3 and c2['close'] > c3['close'] and c1['close'] < (c3['open'] + c3['close']) / 2:
                    return True
                    
        elif bias == "BULLISH":
            # Confirmation 1: Bullish Engulfing (c2 is Bearish, c1 is Bullish completely covering c2's body)
            if is_bear_c2 and is_bull_c1 and c1['open'] <= c2['close'] and c1['close'] >= c2['open']:
                return True
                
            # Confirmation 2: Morning Star
            if not is_bull_c3 and is_bull_c1:
                if body2 < body3 * 0.3 and c2['close'] < c3['close'] and c1['close'] > (c3['open'] + c3['close']) / 2:
                    return True

        return False

    def generate_signal(self, df: pd.DataFrame, current_price: float = None, params: Dict[str, Any] = None,
                         df_1wk: pd.DataFrame = None, df_1d: pd.DataFrame = None, df_4h: pd.DataFrame = None) -> Optional[Dict[str, Any]]:
        # V5 Execution Frame is typically 1H or 2H. Passed `df` is the active scanning timeframe.
        if df is None or len(df) < 50:
            return None

        # Fallback Fetch Data if not pre-fetched (avoids failing if main loop didn't provide it)
        if df_1d is None or df_4h is None:
            if not self.fetcher:
                return None
            if df_1d is None: df_1d = self.fetcher.fetch_ohlcv(symbol="XAU/USD", timeframe="1d", limit=100)
            if df_4h is None: df_4h = self.fetcher.fetch_ohlcv(symbol="XAU/USD", timeframe="4h", limit=200)

        # 1. Structural Bias Check (Daily)
        bias = self._determine_daily_bias(df_1d)
        if bias == "NEUTRAL":
            return None

        # 2. Key Areas of Interest (4H)
        zone = self._get_4h_zone(df_4h, bias)
        if not zone:
            return None

        price = current_price if current_price else df.iloc[-1]['close']

        # 3. Retest Wait (Is price inside our marked Resistance/Support zone?)
        in_zone = False
        if bias == "BEARISH" and zone["type"] == "RESISTANCE":
            if zone["bottom"] <= price <= zone["top"] * 1.002: # Allow slightly above
                in_zone = True
        elif bias == "BULLISH" and zone["type"] == "SUPPORT":
            if zone["bottom"] * 0.998 <= price <= zone["top"]: # Allow slightly below
                in_zone = True
                
        if not in_zone:
            return None

        # 4. Entry Confirmation (1H/2H Candle patterns)
        if not self._check_candlestick_confirmation(df, bias):
            return None

        # All rules met. Time to enter.
        # 5/6/7. Risk to Reward: strict 1:3 targets and protective stops above structure.
        if bias == "BEARISH":
            # SL just above the top of the 4H resistance zone
            sl = round(zone["top"] * 1.0015, 2)
            risk = sl - price
            # Force minimum structure size to avoid spread hunting
            if risk < 3.0: 
                risk = 3.0
                sl = price + risk
            
            tp = round(price - (risk * 3.0), 2) # Strict 1:3 RR
            direction = "SELL"
            reason = "V5 Pure Structure: D1 Bearish Bias + 4H Resistance Retest + Engulfing/Star Confirmed"
            
        else: # BULLISH
            # SL just below the bottom of the 4H support zone
            sl = round(zone["bottom"] * 0.9985, 2)
            risk = price - sl
            if risk < 3.0:
                risk = 3.0
                sl = price - risk
                
            tp = round(price + (risk * 3.0), 2) # Strict 1:3 RR
            direction = "BUY"
            reason = "V5 Pure Structure: D1 Bullish Bias + 4H Support Retest + Engulfing/Star Confirmed"

        return {
            "direction": direction,
            "confidence": 0.95, # Pure structure trades are inherently high confidence if they pass this filter
            "entry_price": round(price, 2),
            "sl": round(sl, 2),
            "tp": round(tp, 2),
            "reason": reason,
            "emoji": "📐", # Geometry rule
            "timestamp": df.index[-1]
        }
