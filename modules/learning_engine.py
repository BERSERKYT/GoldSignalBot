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
            "min_confidence": 0.8
        }

    def get_current_adaptation(self, timeframe: str = None) -> Dict[str, Any]:
        """
        Analyzes the last N signals (filtered by timeframe if provided) and returns strategy offsets.
        """
        try:
            query = self.supabase.from_('signals') \
                .select('status, direction, confidence, timeframe') \
                .neq('direction', 'WAIT') \
                .order('created_at', desc=True) \
                .limit(self.lookback_period)

            if timeframe:
                query = query.eq('timeframe', timeframe)

            response = query.execute()
            signals = response.data
            
            if not signals or len(signals) < 3:
                return {
                    "offsets": {},
                    "status": f"Learning {timeframe or 'Global'}",
                    "win_rate": 0
                }

            wins = len([s for s in signals if s['status'] == 'WIN'])
            losses = len([s for s in signals if s['status'] == 'LOSS'])
            total_resolved = wins + losses
            
            win_rate = (wins / total_resolved) * 100 if total_resolved > 0 else 0
            
            adjustments = {}
            status = "Stable"

            # ⚙️ LOGIC A: If Win Rate is Low (< 45%), become more conservative
            if win_rate < 45 and total_resolved >= 3:
                adjustments["rsi_oversold_offset"] = -5 
                adjustments["rsi_overbought_offset"] = 5 
                adjustments["min_confidence_offset"] = 0.05 
                status = "Defensive"
            
            # ⚙️ LOGIC B: Widen SL if recent noise is high
            last_3 = [s for s in signals if s['status'] in ['WIN', 'LOSS']][:3]
            recent_losses = len([s for s in last_3 if s['status'] == 'LOSS'])
            if recent_losses >= 2:
                adjustments["atr_multiplier_offset"] = 0.5 
                status = "Adaptive"

            logger.info(f"🧠 [AI:{timeframe or 'Global'}] Win Rate {win_rate:.1f}% ({total_resolved} trades) | Status: {status}")
            
            return {
                "offsets": adjustments,
                "status": status,
                "win_rate": win_rate,
                "sample_size": total_resolved
            }

        except Exception as e:
            logger.error(f"Error in LearningEngine: {e}")
            return {"offsets": {}, "status": "Error (Stable Mode)", "win_rate": 0}

    def apply_learning(self, current_strategy_params: Dict[str, Any], timeframe: str = None) -> Dict[str, Any]:
        """
        Main entry point for main.py. Takes current params, returns sharpened ones per timeframe.
        """
        adaptation = self.get_current_adaptation(timeframe=timeframe)
        offsets = adaptation["offsets"]
        
        sharpened = current_strategy_params.copy()
        
        # Helper to get base or default
        def b(key): return sharpened.get(key, self.base_config.get(key, 0))

        # Apply RSI offsets
        if "rsi_oversold_offset" in offsets:
            sharpened["rsi_oversold"] = b("rsi_oversold") + offsets["rsi_oversold_offset"]
        if "rsi_overbought_offset" in offsets:
            sharpened["rsi_overbought"] = b("rsi_overbought") + offsets["rsi_overbought_offset"]
            
        # Apply ATR multiplier offset
        if "atr_multiplier_offset" in offsets:
            sharpened["atr_multiplier"] = b("atr_multiplier") + offsets["atr_multiplier_offset"]

        # Apply Confidence offset
        if "min_confidence_offset" in offsets:
            base_conf = sharpened.get("min_confidence", self.base_config.get("min_confidence", 0.8))
            sharpened["min_confidence"] = base_conf + offsets["min_confidence_offset"]

        return {
            "params": sharpened,
            "status": adaptation["status"]
        }
