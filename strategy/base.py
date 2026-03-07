import pandas as pd
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class BaseStrategy:
    """
    Abstract Base Class for GoldSignalBot Strategies.
    All future strategies should inherit from this class and implement generate_signal.
    """
    
    def __init__(self, name: str):
        self.name = name
        
    def generate_signal(self, df: pd.DataFrame, current_price: float = None) -> Optional[Dict[str, Any]]:
        """
        Takes a DataFrame containing historical prices and pre-computed indicators.
        Returns a dictionary representing the signal, or None if WAIT/No signal.
        
        Expected output format:
        {
            "direction": "BUY" | "SELL" | "WAIT",
            "confidence": int (1-5),
            "entry_price": float,
            "sl": float,
            "tp": float,
            "reason": str,
            "emoji": str
        }
        """
        raise NotImplementedError("Strategy must implement generate_signal method.")
