# GoldSignalBot - Project Tracker

This file serves as the official living document for the GoldSignalBot project. 
Because the initial conversation history was lost, this tracker documents the **current state** as of April 2026, and will be used to record all **future modifications, features, and fixes**.

## 📍 Current State (Baseline)
*Over 40+ implementation steps have been completed to reach this baseline.*

### Core Bot Backend (Python)
- **`main.py`**: The core execution loop of the bot.
- **`modules/`**: Contains the essential building blocks:
  - `data_fetcher.py`: Integrates with GoldAPI/yFinance.
  - `indicators.py`: Technical indicators using `pandas_ta` (EMA, RSI, ATR).
  - `news_filter.py`: High-impact USD event tracking via Finnhub.
  - `logger.py`: Console formatting and generation of CSV signals.
- **`strategy/` / `strategies/`**: Houses the V1 trading strategy logic (EMA crosses + RSI confirmation + Risk Management).
- **`backtest/`**: Backtesting engine to replay historical data and calculate max drawdown, profit factor, and win rate.
- **`signals/` / `data/`**: Directories that store generated signals (CSV) and logging data.
- **`scripts/`**: Holds miscellaneous and helper scripts (e.g., `add_smart_lots_cols.py`).

### Web Interface
- **`dashboard/`**: A high-fidelity frontend web application built using React, Vite, and Tailwind CSS. It connects to the generated signals to display performance metrics, win rates, and signal tables.

### Documentation & Config
- **`README.md` & `DEPLOYMENT.md`**: Setup, running instructions, and deployment guides.
- **`.env` / `config.ini`**: Environment variable configurations and scanner scheduling.
- **`Strategie_Trading_PRO.pdf`**: Detailed documentation for the professional trading strategy utilized.

---

## 📝 Changelog & Future Tasks
*Whenever we add new features, fix bugs, or modify the architecture, we will log them here to maintain a permanent record of our work.*

### [Unreleased / Next Steps]
- **Task 1**: [To be defined]
- **Task 2**: [To be defined]

### [April 1, 2026]
- **Documentation**: Created `PROJECT_TRACKER.md` to establish a persistent record of the project structure and future edits.

