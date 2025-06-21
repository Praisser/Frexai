# Frexai - Python project

An advanced, interactive AI-powered Forex analysis dashboard built with **Streamlit**, featuring:

- ✅ Real-time MetaTrader 5 support
- 📊 Automated trend detection, support/resistance zones, patterns & indicators
- 🧪 Backtesting engine with multiple strategies
- 🔔 Alerts via Email, Telegram & Audio
- 🧾 Trade journal logging
- 🔁 Auto-analysis scheduler
- 🔍 Multi-timeframe confluence checker
- 🧩 Custom strategy builder (JSON rules)
- 🌗 Theme toggle (Light/Dark)
- 💡 Clean, minimal modern design

---

## 🚀 Features

| Module                       | Description                                                                 |
|-----------------------------|-----------------------------------------------------------------------------|
| **Live Analysis**           | Streamlit-based UI for fetching, visualizing & analyzing MT5 forex charts   |
| **MT5 Integration**         | Pulls historical + live data via MetaTrader 5                              |
| **Signal Detection**        | Trend direction, confidence, support/resistance, MACD, RSI, patterns        |
| **Risk Management**         | Auto SL/TP/Entry suggestions with signal scoring                            |
| **Backtesting**             | Run multiple strategies, see equity curve, drawdown, PnL, winrate           |
| **Alerts**                  | Send email/Telegram with chart snapshot and trade details                   |
| **Strategy Optimizer**      | Parameter sweep for RSI/MA thresholds                                       |
| **Journal**                 | Logs live/backtest trades to CSV                                            |
| **Confluence Analysis**     | Compares signal across two timeframes                                       |
| **Auto Scheduler**          | Optionally rerun analysis every N minutes                                   |
| **Modern UI**               | Theme toggle + minimal dark/light design                                    |

---

## 📦 Installation

```bash
git clone https://github.com/yourusername/forex-analyzer-ai.git
cd forex-analyzer-ai

# Setup virtual environment (recommended)
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt
