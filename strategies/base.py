"""
GoldSignalBot – strategies/base.py
====================================
Defines the abstract base class for all trading strategies.

Any new strategy (e.g., MACD breakout, Bollinger Bands bounce) should inherit from
Strategy and implement the `generate_signal` method. This ensures the signal
generator and backtester can swap strategies seamlessly.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd


class Strategy(ABC):
    """
    Abstract base class for trading strategies.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the strategy with a configuration dictionary.
        
        Args:
            config: Dictionary containing strategy parameters (e.g., from config.ini)
        """
        self.config = config
        
        # Standard configs that most strategies will need
        self.min_rr_ratio = float(config.get("min_rr_ratio", 3.0))
        self.atr_sl_multiplier = float(config.get("atr_sl_multiplier", 1.5))

    @abstractmethod
    def generate_signal(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Analyze the DataFrame and generate a trading signal for the LAST completed candle.
        
        Args:
            df: DataFrame containing OHLCV and all required indicators.
                Must be sorted chronologically (oldest to newest).
                The method should check df.iloc[-1] (the most recently closed candle).
                
        Returns:
            A dictionary containing signal details, or None if no signal condition is met.
            Required keys if returning a signal:
                - 'timestamp'  : (pd.Timestamp) Time of the candle that triggered the signal
                - 'direction'  : (str) "BUY" or "SELL"
                - 'confidence' : (int) 1 to 5 (5 is highest)
                - 'entry'      : (float) Suggested entry price (usually current close)
                - 'sl'         : (float) Stop Loss price
                - 'tp'         : (float) Take Profit price
                - 'reason'     : (str) Short explanation + emoji
        """
        pass
