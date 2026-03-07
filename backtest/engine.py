import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import logging

from modules.indicators import Indicators
from strategy.v1_strategy import V1Strategy

logger = logging.getLogger(__name__)

class Backtester:
    """
    Basic Backtesting Engine for GoldSignalBot V1.
    Downloads 2 years of daily or 4H data using yfinance (fallback),
    runs the strategy bar-by-bar, tracks trades, and outputs stats.
    """
    def __init__(self, initial_capital: float = 10000.0, risk_per_trade_pct: float = 0.02):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.risk_per_trade_pct = risk_per_trade_pct
        self.strategy = V1Strategy()
        
        self.trades = []
        self.equity_curve = [initial_capital]
        self.peak_capital = initial_capital
        self.max_drawdown = 0.0
        
    def fetch_historical_data(self, symbol="GC=F", period="2y", interval="1d") -> pd.DataFrame:
        """
        Fetches historical data for backtesting. 
        Using '1d' by default since yfinance limits '1h' to 730 days max anyway.
        """
        logger.info(f"Fetching {period} of {interval} historical data for {symbol}...")
        df = yf.download(symbol, period=period, interval=interval, progress=False)
        
        if df.empty:
            logger.error("Failed to fetch historical data for backtesting.")
            return pd.DataFrame()
            
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0].lower() for col in df.columns]
        else:
            df.columns = [col.lower() for col in df.columns]
            
        df.reset_index(inplace=True)
        if 'Datetime' in df.columns:
            df.rename(columns={'Datetime': 'timestamp'}, inplace=True)
        elif 'Date' in df.columns:
            df.rename(columns={'Date': 'timestamp'}, inplace=True)
            
        logger.info(f"Fetched {len(df)} historical bars.")
        return df

    def run(self, df: pd.DataFrame):
        if df is None or df.empty:
            return
            
        logger.info("Applying indicators...")
        df = Indicators.add_all_indicators(df)
        df.dropna(inplace=True)
        df.reset_index(drop=True, inplace=True)
        
        logger.info("Starting simulation loop...")
        
        # We simulate this without a strict bar-by-bar loop for simplicity since our Strategy 
        # normally just returns the latest signal. Oh wait, `generate_signal` evaluates the *last* 
        # rows of the passed dataframe. 
        # To backtest, we must feed it expanding windows.
        
        active_trade = None
        
        for i in range(50, len(df)):
            # Create a slice of the dataframe up to index i
            window = df.iloc[:i+1]
            current_bar = window.iloc[-1]
            current_price = current_bar['close']
            
            # --- Manage active trade ---
            if active_trade:
                trade_type = active_trade['type']
                entry = active_trade['entry']
                sl = active_trade['sl']
                tp = active_trade['tp']
                
                # Check simplified exit conditions (Low hits SL, High hits TP)
                high = current_bar['high']
                low = current_bar['low']
                
                closed_pnl = 0
                closed = False
                
                if trade_type == "BUY":
                    if low <= sl:
                        closed_pnl = -self._pnl(entry, sl)
                        closed = True
                    elif high >= tp:
                        closed_pnl = self._pnl(entry, tp, is_profit=True)
                        closed = True
                        
                elif trade_type == "SELL":
                    if high >= sl:
                        closed_pnl = -self._pnl(sl, entry)
                        closed = True
                    elif low <= tp:
                        closed_pnl = self._pnl(tp, entry, is_profit=True)
                        closed = True
                        
                if closed:
                    self.capital += closed_pnl
                    self.equity_curve.append(self.capital)
                    
                    # Update max Drawdown
                    if self.capital > self.peak_capital:
                        self.peak_capital = self.capital
                    else:
                        dd = (self.peak_capital - self.capital) / self.peak_capital
                        if dd > self.max_drawdown:
                            self.max_drawdown = dd
                            
                    active_trade['exit_pnl'] = closed_pnl
                    active_trade['exit_time'] = current_bar['timestamp']
                    self.trades.append(active_trade)
                    active_trade = None
            
            # --- Scan for new signal if no active trade ---
            if not active_trade:
                signal = self.strategy.generate_signal(window, current_price=current_price)
                if signal:
                    active_trade = {
                        'type': signal['direction'],
                        'entry': signal['entry_price'],
                        'sl': signal['sl'],
                        'tp': signal['tp'],
                        'time': signal['timestamp']
                    }
                    
        self._print_stats()

    def _pnl(self, start_price, end_price, is_profit=False):
        # A mock PNL calculation based on fixed risk 
        # Assuming we risk fixed $ amount based on capital
        risk_amount = self.initial_capital * self.risk_per_trade_pct
        
        if not is_profit:
            return risk_amount # Lost 1R
        else:
            return risk_amount * 3 # R:R is 1:3 hardcoded in signal

    def _print_stats(self):
        print("\n" + "="*40)
        print(" BACKTEST RESULTS ")
        print("="*40)
        print(f"Initial Capital: ${self.initial_capital:,.2f}")
        print(f"Final Capital:   ${self.capital:,.2f}")
        
        net_profit = self.capital - self.initial_capital
        print(f"Net Profit:      ${net_profit:,.2f} ({(net_profit/self.initial_capital)*100:.2f}%)")
        print(f"Max Drawdown:    {self.max_drawdown*100:.2f}%")
        
        total_trades = len(self.trades)
        wins = len([t for t in self.trades if t.get('exit_pnl', 0) > 0])
        losses = total_trades - wins
        
        win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0.0
        
        print("\nTRADE STATS")
        print(f"Total Trades: {total_trades}")
        print(f"Wins:         {wins}")
        print(f"Losses:       {losses}")
        print(f"Win Rate:     {win_rate:.2f}%")
        print("="*40 + "\n")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bt = Backtester(initial_capital=10000)
    df = bt.fetch_historical_data(symbol="GC=F", period="2y", interval="1d")
    bt.run(df)
