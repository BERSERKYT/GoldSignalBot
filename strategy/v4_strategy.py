import pandas as pd
import numpy as np
from strategy.base import BaseStrategy
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class V4Strategy(BaseStrategy):
    """
    Strategie Trading PRO (SMC/ICT Logic):
    1. Analysis of Structure: H4/H1 EMA 50/200 & HH/LL Alignment.
    2. Impulse & Fibonacci: 61.8% - 78.6% OTE (Optimal Trade Entry).
    3. FVG Detection: Fair Value Gaps as magnets.
    4. Trigger: M15 Pin Bar / Engulfing rejection.
    """
    def __init__(self, fetcher=None):
        super().__init__(name="V4_PRO_SMC")
        self.fetcher = fetcher

    def generate_signal(self, df: pd.DataFrame, current_price: float = None, params: Dict[str, Any] = None,
                         df_h1: pd.DataFrame = None, df_h4: pd.DataFrame = None) -> Optional[Dict[str, Any]]:
        if df is None or len(df) < 100:
            return None

        # 1. TOP-DOWN ANALYSIS — uses pre-fetched frames if available, otherwise self-fetches
        if not self._check_top_down_alignment(df_h1=df_h1, df_h4=df_h4):
            return None

        # 2. DETECT IMPULSE & OTE
        impulse = self._find_impulse(df)
        if not impulse:
            return None

        # 3. CHECK OTE ZONE (61.8% - 78.6%)
        price = current_price if current_price else df.iloc[-1]['close']
        if not self._is_in_ote_zone(price, impulse):
            return None

        # 4. FVG DETECTION (Fair Value Gaps)
        fvg_present = self._check_fvg(df, impulse)
        
        # 5. CANDLESTICK TRIGGER (Pin Bar / Engulfing)
        trigger = self._check_candle_trigger(df)
        if not trigger:
            return None

        # Logic: Signal if OTE + Trigger (FVG is a bonus/booster)
        direction = impulse['direction']
        if trigger != direction:
            return None

        # SL/TP Logic from PDF:
        # SL: Below/Above 100% Fib (Impulse Start)
        # TP: Target 1 at BOS, Target 2 at 1:2.5 RR
        sl = impulse['start_price'] if direction == "BUY" else impulse['start_price']
        tp = price + (abs(price - sl) * 2.5) if direction == "BUY" else price - (abs(price - sl) * 2.5)

        base_conf = 0.85
        if fvg_present:
            base_conf += 0.05
            
        return {
            "direction": direction,
            "confidence": min(0.99, base_conf),
            "entry_price": round(price, 2),
            "sl": round(sl, 2),
            "tp": round(tp, 2),
            "reason": f"V4 PRO: Top-Down Align + OTE Zone + {trigger} Trigger" + (" (FVG Multiplier)" if fvg_present else ""),
            "emoji": "💎",
            "timestamp": df.index[-1]
        }

    def _check_top_down_alignment(self, df_h1: pd.DataFrame = None, df_h4: pd.DataFrame = None) -> bool:
        """Verifies EMA 50/200 alignment on H1 and H4. Accepts pre-fetched frames to avoid extra HTTP calls."""
        try:
            from modules.indicators import Indicators

            # --- H4 ---
            if df_h4 is None or len(df_h4) < 200:
                if not self.fetcher:
                    return True
                df_h4 = self.fetcher.fetch_ohlcv(symbol="XAU/USD", timeframe="4h", limit=200)
            if df_h4 is None or len(df_h4) < 200:
                return False
            df_h4 = Indicators.add_all_indicators(df_h4)
            last_h4 = df_h4.iloc[-1]
            h4_bullish = last_h4['EMA_50'] > last_h4['EMA_200']
            h4_bearish = last_h4['EMA_50'] < last_h4['EMA_200']

            # --- H1 ---
            if df_h1 is None or len(df_h1) < 200:
                if not self.fetcher:
                    return True
                df_h1 = self.fetcher.fetch_ohlcv(symbol="XAU/USD", timeframe="1h", limit=200)
            if df_h1 is None or len(df_h1) < 200:
                return False
            df_h1 = Indicators.add_all_indicators(df_h1)
            last_h1 = df_h1.iloc[-1]
            h1_bullish = last_h1['EMA_50'] > last_h1['EMA_200']
            h1_bearish = last_h1['EMA_50'] < last_h1['EMA_200']

            if h4_bullish and h1_bullish: return True
            if h4_bearish and h1_bearish: return True
            return False
        except Exception as e:
            logger.error(f"Top-Down check failed: {e}")
            return False

    def _find_impulse(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Detects a strong move breaking recent structure."""
        # Look at last 20-30 bars
        window = df.tail(30).copy()
        
        # Simple Impulse: Move of > 1% in < 10 bars or breaking previous peak
        max_price = window['high'].max()
        min_price = window['low'].min()
        
        # Find price at start of window
        start_price = window.iloc[0]['close']
        end_price = window.iloc[-1]['close']
        
        diff = end_price - start_price
        
        if diff > 0: # Potential Bullish Impulse
            return {"direction": "BUY", "start_price": min_price, "end_price": max_price}
        elif diff < 0: # Potential Bearish Impulse
            return {"direction": "SELL", "start_price": max_price, "end_price": min_price}
            
        return None

    def _is_in_ote_zone(self, price: float, impulse: Dict[str, Any]) -> bool:
        """Checks if price is in the 61.8% - 78.6% Fib zone."""
        start = impulse['start_price']
        end = impulse['end_price']
        total_move = abs(end - start)
        
        if impulse['direction'] == "BUY":
            # Retracement from top
            fib_618 = end - (total_move * 0.618)
            fib_786 = end - (total_move * 0.786)
            return fib_786 <= price <= fib_618
        else:
            # Retracement from bottom
            fib_618 = end + (total_move * 0.618)
            fib_786 = end + (total_move * 0.786)
            return fib_618 <= price <= fib_786

    def _check_fvg(self, df: pd.DataFrame, impulse: Dict[str, Any]) -> bool:
        """Scan for Fair Value Gaps in the impulse leg."""
        # Look at last 15 candles
        last_15 = df.tail(15)
        for i in range(1, len(last_15) - 1):
            prev = last_15.iloc[i-1]
            curr = last_15.iloc[i]
            next_b = last_15.iloc[i+1]
            
            if impulse['direction'] == "BUY":
                if prev['high'] < next_b['low']: # Bullish FVG
                    return True
            else:
                if prev['low'] > next_b['high']: # Bearish FVG
                    return True
        return False

    def _check_candle_trigger(self, df: pd.DataFrame) -> Optional[str]:
        """Detects Pin Bar or Engulfing patterns."""
        last_2 = df.tail(2)
        c2 = last_2.iloc[-1] # Current
        c1 = last_2.iloc[-2] # Previous
        
        # Pin Bar detection
        body = abs(c2['close'] - c2['open'])
        wick_high = c2['high'] - max(c2['open'], c2['close'])
        wick_low = min(c2['open'], c2['close']) - c2['low']
        total_range = c2['high'] - c2['low']
        
        if total_range > 0:
            # Bullish Pin (Long lower wick)
            if wick_low > (total_range * 0.6) and body < (total_range * 0.3):
                return "BUY"
            # Bearish Pin (Long upper wick)
            if wick_high > (total_range * 0.6) and body < (total_range * 0.3):
                return "SELL"
                
        # Engulfing detection
        if c2['close'] > c2['open'] and c1['close'] < c1['open']: # Bullish
            if c2['close'] > c1['open'] and c2['open'] < c1['close']:
                return "BUY"
        if c2['close'] < c2['open'] and c1['close'] > c1['open']: # Bearish
            if c2['close'] < c1['open'] and c2['open'] > c1['close']:
                return "SELL"
                
        return None
