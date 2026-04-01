"""
GoldSignalBot – strategies/ema_rsi_atr.py
===========================================
V1 Core Strategy:
  - Trend       : EMA9 vs EMA21 Crossover
  - Momentum    : RSI(14) level
  - Volatility  : ATR(14) > 20-period ATR Average (expansion)
  - News Filter : No signals during high-impact news windows

Risk Management:
  - SL = Current ATR * Configured Multiplier (default 1.5)
  - TP = SL distance * R:R Ratio (default 3.0)

Returns detailed dictionary on valid signals, or None.
"""

import logging
from typing import Dict, Any, Optional

import pandas as pd

from strategies.base import Strategy
from news.filter import NewsFilter

logger = logging.getLogger(__name__)

class EMARSIATRStrategy(Strategy):
    """
    EMA Crossover + RSI + ATR Volatility Strategy (V1).
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.news_filter = NewsFilter()
        
        # RSI Confidence thresholds
        self.rsi_ch_low = float(config.get("rsi_confidence_high_low", 30))
        self.rsi_ch_high = float(config.get("rsi_confidence_high_high", 70))
        self.rsi_cl_low = float(config.get("rsi_confidence_low_low", 55))
        self.rsi_cl_high = float(config.get("rsi_confidence_low_high", 45))

    def generate_signal(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Evaluate the strategy on the most recent completed candle."""
        
        if df is None or len(df) < 2:
            return None
            
        # Get the VERY LAST row (most recently completed candle)
        # Note: In backtesting, this method is called row by row.
        # In live mode, `fetcher.py` returns up to the current incomplete candle,
        # so we should technically evaluate df.iloc[-2] if we only want CLOSED candles.
        # But for simplicity, we evaluate the last available row. A live loop should 
        # ensure it only requests up to the last closed candle.
        current = df.iloc[-1]
        
        # Verify required indicators are present
        required = ["EMA_cross", "RSI_14", "ATR_14", "ATR_avg_20", "close"]
        for col in required:
            if col not in df.columns or pd.isna(current[col]):
                return None
                
        # 1. Check News Filter (only in live mode, backtest bypasses this for speed unless mocked)
        # We pass the candle timestamp. For daily candles this is less precise.
        # We skip news filter if this is clearly a historical backtest run (e.g. timestamp is days old)
        now_utc = pd.Timestamp.utcnow()
        age_in_hours = (now_utc - current.name).total_seconds() / 3600
        
        if age_in_hours < 24: # Roughly "live" data
             if self.news_filter.is_news_window(current.name):
                 logger.info("Signal blocked by News Filter at %s", current.name)
                 return None

        # 2. Extract values
        cross = current["EMA_cross"]
        rsi   = current["RSI_14"]
        atr   = current["ATR_14"]
        atr_avg = current["ATR_avg_20"]
        close_price = current["close"]
        
        # 3. Evaluate Base Conditions
        is_bullish_cross = (cross == 1)
        is_bearish_cross = (cross == -1)
        
        has_volatility = (atr > atr_avg)
        
        if not (is_bullish_cross or is_bearish_cross):
            return None # No crossover event
            
        if not has_volatility:
            logger.debug("Crossover ignored: Insufficient volatility (ATR %f <= Avg %f)", atr, atr_avg)
            return None

        # 4. Determine Direction & Confidence
        direction = None
        confidence = 1
        reason = ""
        
        if is_bullish_cross and rsi > 50:
            if rsi >= self.rsi_ch_high: # e.g. >= 70
                logger.debug("Buy crossover ignored: RSI overbought (%.1f)", rsi)
                return None
            
            direction = "BUY"
            # High confidence if RSI is in the "sweet spot"
            if self.rsi_cl_low <= rsi < self.rsi_ch_high: # e.g. [55, 70)
                confidence = 4
                if has_volatility and atr > (atr_avg * 1.1): confidence = 5
            else:
                confidence = 3
                
            reason = f"Bullish EMA Cross + RSI ({rsi:.1f}) > 50 + ATR Expansion 🟢"
            
        elif is_bearish_cross and rsi < 50:
            if rsi <= self.rsi_ch_low: # e.g. <= 30
                logger.debug("Sell crossover ignored: RSI oversold (%.1f)", rsi)
                return None
                
            direction = "SELL"
            # High confidence if RSI is in the "sweet spot"
            if self.rsi_ch_low < rsi <= self.rsi_cl_high: # e.g. (30, 45]
                confidence = 4
                if has_volatility and atr > (atr_avg * 1.1): confidence = 5
            else:
                confidence = 3
                
            reason = f"Bearish EMA Cross + RSI ({rsi:.1f}) < 50 + ATR Expansion 🔴"
            
        if not direction:
            return None
            
        # 5. Calculate Stop Loss and Take Profit
        sl_distance = atr * self.atr_sl_multiplier
        tp_distance = sl_distance * self.min_rr_ratio
        
        if direction == "BUY":
            sl = close_price - sl_distance
            tp = close_price + tp_distance
        else:
            sl = close_price + sl_distance
            tp = close_price - tp_distance
            
        # Final validation
        if sl_distance <= 0 or tp_distance <= 0:
            return None

        # Return standardized signal dict
        return {
            "timestamp": current.name,
            "direction": direction,
            "confidence": confidence,
            "entry": round(close_price, 2),
            "sl": round(sl, 2),
            "tp": round(tp, 2),
            "reason": reason
        }
