import pandas as pd
from typing import Dict, Any, List
from modules.logger import logger

class LearningEngine:
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.lookback_period = 20
        self.base_config = {
            "rsi_period": 14,
            "rsi_overbought": 70,
            "rsi_oversold": 30,
            "atr_multiplier": 2.0,
            "min_confidence": 3
        }

    def get_current_adaptation(self) -> Dict[str, Any]:
        """
        Analyzes the last N signals and returns strategy offsets.
        Returns a dictionary of 'adjustments' and a 'status' string for the UI.
        """
        try:
            # Fetch last signals
            response = self.supabase.from_('signals') \
                .select('status, direction, confidence') \
                .neq('direction', 'WAIT') \
                .order('created_at', { 'ascending': False }) \
                .limit(self.lookback_period) \
                .execute()

            signals = response.data
            if not signals or len(signals) < 5:
                return {
                    "offsets": {},
                    "status": "Learning (Need more data)",
                    "win_rate": 0
                }

            wins = len([s for s in signals if s['status'] == 'WIN'])
            losses = len([s for s in signals if s['status'] == 'LOSS'])
            total_resolved = wins + losses

            if total_resolved == 0:
                return {"offsets": {}, "status": "Stable (Initializing)", "win_rate": 0}

            win_rate = (wins / total_resolved) * 100
            
            adjustments = {}
            status = "Stable"

            # 1. Logic: If Win Rate is Low (< 45%), become more conservative
            if win_rate < 45:
                # Tighten RSI (require more extreme oversold/overbought)
                adjustments["rsi_oversold_offset"] = -5 # e.g. 30 -> 25
                adjustments["rsi_overbought_offset"] = 5 # e.g. 70 -> 75
                # Increase minimum confidence
                adjustments["min_confidence_offset"] = 1
                status = "Defensive (Sharpening)"
            
            # 2. Logic: If Win Rate is Excellent (> 70%), maintain strictness but allow more signals
            elif win_rate > 70:
                status = "Optimized (High Accuracy)"
            
            # 3. Logic: If many Recent losses, widen SL slightly to avoid noise hunts
            # (Simplified check: last 3 signals)
            last_3 = signals[:3]
            recent_losses = len([s for s in last_3 if s['status'] == 'LOSS'])
            if recent_losses >= 2:
                adjustments["atr_multiplier_offset"] = 0.5 # e.g. 2.0 -> 2.5
                status = "Adaptive (Volatility Filter)"

            logger.info(f"🧠 Learning Engine: Win Rate {win_rate:.1f}% | Mode: {status}")
            
            return {
                "offsets": adjustments,
                "status": status,
                "win_rate": win_rate,
                "sample_size": total_resolved
            }

        except Exception as e:
            logger.error(f"Error in LearningEngine: {e}")
            return {"offsets": {}, "status": "Error (Stable Mode)", "win_rate": 0}

    def apply_learning(self, current_strategy_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point for main.py. Takes current params, returns sharpened ones.
        """
        adaptation = self.get_current_adaptation()
        offsets = adaptation["offsets"]
        
        sharpened = current_strategy_params.copy()
        
        # Apply RSI offsets
        if "rsi_oversold_offset" in offsets:
            sharpened["rsi_oversold"] += offsets["rsi_oversold_offset"]
        if "rsi_overbought_offset" in offsets:
            sharpened["rsi_overbought"] += offsets["rsi_overbought_offset"]
            
        # Apply ATR multiplier offset
        if "atr_multiplier_offset" in offsets:
            sharpened["atr_multiplier"] += offsets["atr_multiplier_offset"]

        # Apply Confidence offset
        if "min_confidence_offset" in offsets:
            sharpened["min_confidence"] = max(sharpened.get("min_confidence", 3), 3) + offsets["min_confidence_offset"]

        return {
            "params": sharpened,
            "status": adaptation["status"]
        }
