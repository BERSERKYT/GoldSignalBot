# GoldSignalBot V1 🏆

GoldSignalBot is a lightweight Python bot that generates 1–2 high-quality trading signals per day exclusively for **XAU/USD (gold)**.
It pairs perfectly with the provided stunning React + Tailwind Web Dashboard.

## Features (V1)
- 📊 **Intelligent Indicators**: Utilizes EMA 9, EMA 21, RSI 14, and ATR 14.
- 🚦 **V1 Core Strategy**: Trend following using EMA crosses, RSI confirmation, and Volatility checks.
- 🛡️ **Risk Management**: Strict 1:3 Risk:Reward minimum, utilizing Volatility-Adaptive (ATR) Stop Losses.
- 🗂️ **News Filter**: Automatically pauses trading ±60/30 mins around high-impact USD events (via Finnhub).
- 📈 **Signal Delivery**: Clear, English console output with CSV logging.
- 🖥️ **Web Dashboard**: High-fidelity React application using Tailwind CSS to visualize signals and performance.
- 🧪 **Backtesting Engine**: A basic engine to replay history and output directional win rate, max DD, and profit factors.

## Project Structure
```text
GoldSignalBot/
├── .env.example          # Example environment config
├── requirements.txt      # Python dependencies
├── main.py               # Bot execution loop
├── modules/
│   ├── data_fetcher.py   # GoldAPI / yFinance integration
│   ├── indicators.py     # pandas_ta wrapper
│   ├── logger.py         # Console formatting and CSV saving
│   └── news_filter.py    # Finnhub Economic Calendar check
├── strategy/
│   ├── base.py           # Abstract BaseClass
│   └── v1_strategy.py    # The core signal generation logic
├── backtest/
│   └── engine.py         # Strategy replays & metric generation
└── dashboard/            # React/Vite UI Application
```

## Setup & Execution (Backend)
1. Provide your Python 3.10+ runtime.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set your environment variables in `.env`:
   ```env
   GOLDAPI_KEY="your_goldapi_key"
   FINNHUB_KEY="your_finnhub_key"
   TIMEFRAME="4h"
   SCAN_INTERVAL_MINS="60"
   ```
4. Run the main bot loop:
   ```bash
   python main.py
   ```
5. *(Optional)* Run the backtester:
   ```bash
   python -m backtest.engine
   ```

## Setup & Execution (Web Dashboard)
1. Ensure Node.js 18+ is installed.
2. Provide terminal directory to `dashboard/`:
   ```bash
   cd dashboard
   npm install
   npm run dev
   ```
3. Open the provided `localhost:5173` link in your browser to view the high-fidelity Tailwind dashboard.

## 🕹️ Bot Operations (Start/Stop & Actions)

### 1. Activating the Bot
Once your `.env` file is configured with the correct API keys, open a terminal in the `GoldSignalBot` folder and run:
```bash
python main.py
```
*The bot will immediately fetch historical data, run the technical indicators, check the Finnhub news calendar, and evaluate the V1 Strategy. If no actionable setup is found, it will go to sleep for the duration specified in `SCAN_INTERVAL_MINS` (default: 60 mins).*

### 2. Deactivating the Bot
The bot runs in an infinite loop. To stop the bot safely at any time:
- Navigate to the terminal window where the bot is running.
- Press `Ctrl + C` (or `Cmd + C` on Mac).
- You will see a message: `Bot stopped by user.`, and the process will exit cleanly.

### 3. Reviewing Historical Signals
- **Console Log**: The bot prints detailed, colorful logs directly to your terminal.
- **CSV Log**: Every generated signal is permanently saved in the `data/signals.csv` file. You can open this file in Excel, Google Sheets, or view it via the React Dashboard.

### 4. Adjusting the Scanning Interval
If you want the bot to check the market more (or less) frequently:
1. Open the `.env` file.
2. Edit `SCAN_INTERVAL_MINS="60"` to your preferred timeframe (e.g., `15` or `30`).
3. Restart the bot (`Ctrl + C` then `python main.py`).
