import pandas as pd
import pandas_ta as ta
import logging

logger = logging.getLogger(__name__)

class Indicators:
    @staticmethod
    def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        Adds EMA 9, EMA 21, RSI 14, and ATR 14 to the provided OHLCV DataFrame.
        Also calculates the 20-period average of the ATR as per V1 Strategy requirements.
        """
        if df is None or df.empty:
            logger.error("Empty dataframe provided to Indicators module.")
            return df
            
        required_cols = ['open', 'high', 'low', 'close']
        for col in required_cols:
            if col not in df.columns:
                logger.error(f"Missing required column for indicators: {col}")
                return df
                
        # Make a copy to avoid SettingWithCopy warnings
        df = df.copy()
        
        try:
            # 1. EMAs
            df['EMA_9'] = ta.ema(df['close'], length=9)
            df['EMA_21'] = ta.ema(df['close'], length=21)
            
            # 2. RSI
            df['RSI_14'] = ta.rsi(df['close'], length=14)
            
            # 3. ATR
            # pandas_ta true range requires high, low, close
            df['ATR_14'] = ta.atr(df['high'], df['low'], df['close'], length=14)
            
            # 4. Avg ATR (20-period average of the ATR_14) for volatility check
            if 'ATR_14' in df.columns:
                df['ATR_14_MA_20'] = ta.sma(df['ATR_14'], length=20)
                
            logger.debug("Successfully computed all V1 indicators.")
            
        except Exception as e:
            logger.error(f"Error computing indicators: {e}")
            
        return df

if __name__ == "__main__":
    # Simple self-test
    logging.basicConfig(level=logging.DEBUG)
    import numpy as np
    
    # Create mock OHLCV dataframe
    mock_df = pd.DataFrame({
        'timestamp': pd.date_range(start='2024-01-01', periods=100, freq='4h'),
        'open': np.random.uniform(2000, 2050, 100),
        'high': np.random.uniform(2030, 2080, 100),
        'low': np.random.uniform(1980, 2010, 100),
        'close': np.random.uniform(2000, 2050, 100),
        'volume': np.random.randint(100, 1000, 100)
    })
    
    res = Indicators.add_all_indicators(mock_df)
    print("Columns added:", [c for c in res.columns if c not in mock_df.columns])
    print(res[['close', 'EMA_9', 'EMA_21', 'RSI_14', 'ATR_14']].tail())
