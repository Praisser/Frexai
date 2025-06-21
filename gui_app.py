import streamlit as st
import pandas as pd
import json
import os
import time
import plotly.graph_objects as go
from src.ml_model import predict_signal, train_model 

from datetime import datetime
from src.mt5_fetcher import fetch_mt5_data, is_mt5_available
from src.data_handler import load_forex_data, fetch_live_forex
from src.trend_analyzer import detect_trend
from src.sr_levels import identify_sr_levels
from src.chart_patterns import detect_double_top_bottom
from src.indicator_analysis import analyze_indicators
from src.risk_manager import suggest_trade_levels
from src.visualizer import plot_chart_with_levels
from src.alerts import send_email_alert, send_telegram_alert
from src.backtester import run_backtest
from src.journal import log_trade
from src.multi_timeframe import analyze_confluence
from src.backtester import optimize_rsi_strategy

# --- Custom CSS Injection ---
def inject_custom_css():
    st.markdown("""
        <style>
        /* General layout tweaks */
        .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
        }

        /* Buttons */
        .stButton>button {
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 0.6rem 1rem;
            border-radius: 5px;
        }
        .stButton>button:hover {
            background-color: #45a049;
        }

        /* Sidebar (optional for dark mode look) */
        .stSidebar {
            background-color: #1c1c1c;
        }

        /* Headings */
        h1, h2, h3, h4 {
            color: #4CAF50;
        }

        /* Remove Streamlit footer */
        footer {
            visibility: hidden;
        }
        </style>
    """, unsafe_allow_html=True)

st.set_page_config(page_title="Forex Analyzer AI", layout="wide")
inject_custom_css()


st.title("Forex Analyzer AI — Streamlit GUI")

# --- Load Secrets ---
with open("secrets.json", "r") as f:
    secrets = json.load(f)

email_config = secrets["email"]
telegram_config = secrets["telegram"]

# --- Load Config ---
CONFIG_FILE = "user_config.json"
if os.path.exists(CONFIG_FILE):
    config = json.load(open(CONFIG_FILE))
else:
    config = {}

# --- Sidebar Config ---
with st.sidebar:
    st.subheader("Settings")

    capital = st.number_input("Trading Capital", min_value=100.0, value=float(config.get("capital", 10000.0)))
    config["capital"] = capital

    use_plotly = st.checkbox("Interactive Plotly Chart", value=config.get("use_plotly", True))
    show_atr = st.checkbox("Show ATR Bands", value=config.get("show_atr", True))
    show_bb = st.checkbox("Show Bollinger Bands", value=config.get("show_bollinger", True))
    config.update({"use_plotly": use_plotly, "show_atr": show_atr, "show_bollinger": show_bb})

    source = st.radio("Data Source", ["MT5", "CSV File"], index=0)

    if source == "CSV File":
        uploaded_file = st.file_uploader("Upload CSV File", type=["csv"])
    else:
        pair = st.selectbox("Forex Pair", ['EURUSD', 'GBPJPY', 'USDJPY', 'AUDUSD', 'USDCAD'])
        tf_choice = st.selectbox("Timeframe", ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1'])

    auto_run = st.checkbox("🔁 Auto-run analysis")
    auto_interval = st.selectbox("Interval (minutes)", [1, 2, 5, 10], index=0)
    audio_alerts = st.sidebar.checkbox("🔔 Enable Audio Alerts", value=True)

    if auto_run:
        config["auto_run"] = True
        config["auto_interval"] = auto_interval
    else:
        config["auto_run"] = False

    run_btn = st.button("Run Analysis")



with st.expander("🔁 Multi-Timeframe Confluence Analysis"):
    symbol = st.selectbox("Symbol for Confluence", ['EURUSD', 'GBPJPY', 'USDJPY', 'AUDUSD', 'USDCAD'], key="mtf_symbol")
    tf1 = st.selectbox("Timeframe 1", ['M5', 'M15', 'M30'], key="tf1")
    tf2 = st.selectbox("Timeframe 2", ['H1', 'H4', 'D1'], key="tf2")
    if st.button("Compare Timeframes"):
        with st.spinner("Running confluence analysis..."):
            result = analyze_confluence(symbol, tf1, tf2, capital=capital)
            st.markdown(f"**Trend in {tf1}:** {result['trend_1']['trend']} ({result['trend_1']['confidence']})")
            st.markdown(f"**Trend in {tf2}:** {result['trend_2']['trend']} ({result['trend_2']['confidence']})")
            st.markdown(f"### 🔍 Verdict: {result['verdict']}")

            st.subheader(f"📊 Risk Levels - {tf1}")
            st.json(result['risk_1'])

            st.subheader(f"📊 Risk Levels - {tf2}")
            st.json(result['risk_2'])

   
# --- Auto-refresh scheduler ---
if config.get("auto_run"):
    if "last_run_time" not in st.session_state:
        st.session_state["last_run_time"] = time.time()
    elapsed = time.time() - st.session_state["last_run_time"]
    if elapsed >= config.get("auto_interval", 1) * 60:
        st.session_state["last_run_time"] = time.time()
        st.experimental_rerun()

# --- Analysis Logic ---
if run_btn:
    with st.spinner("Fetching data and running analysis..."):
        # Load Data
        if source == "CSV File" and uploaded_file:
            df = pd.read_csv(uploaded_file, index_col=0, parse_dates=True)
            inferred_tf = tf_choice = "Custom"
            pair = uploaded_file.name
        elif source == "MT5":
            if not is_mt5_available():
                st.error("MT5 is not available. Please ensure it is running.")
                st.stop()
            df = fetch_mt5_data(pair, tf_choice)
            inferred_tf = tf_choice
        else:
            st.error("Only MT5 and CSV File supported currently.")
            st.stop()

        df = df[df.index >= df.index.max() - pd.Timedelta(days=2)]
        st.session_state.df = df.copy()  # For backtesting reuse

        # Analysis
        trend_result = detect_trend(df)
        sr_result = identify_sr_levels(df)
        patterns = detect_double_top_bottom(df)
        indicators = analyze_indicators(df)
        risk_info = suggest_trade_levels(
            df=df,
            trend=trend_result['trend'],
            support_levels=sr_result['support'],
            resistance_levels=sr_result['resistance'],
            capital=capital,
            risk_percent=1.0,
            rr_threshold=1.5,
            slippage=0.0002
        )
        st.session_state['df'] = df
        st.session_state['sr_result'] = sr_result

        if "signal_score" in risk_info and risk_info['signal_score']['value'] >= 75:
            st.success("🚨 High-Confidence Signal Detected!")

            # --- 🔊 Play Audio Alert
            st.audio("assets/alert.mp3", format="audio/mp3", start_time=0)

            # --- 💬 Popup Notification (HTML workaround)
            st.components.v1.html("""
                <script>
                const msg = new SpeechSynthesisUtterance("High confidence trade signal detected");
                window.speechSynthesis.speak(msg);
                </script>
                """, height=0)

        # Summary Display
        st.subheader("Analysis Summary")
        st.write(f"**Pair:** {pair}")
        st.write(f"**Timeframe:** {inferred_tf}")
        st.write(f"**Trend:** {trend_result['trend']} ({trend_result['confidence']})")
        st.write(f"**Support Levels:** {[s['price'] for s in sr_result['support']]}")
        st.write(f"**Resistance Levels:** {[r['price'] for r in sr_result['resistance']]}")

        if patterns:
            latest = patterns[-1]
            st.write(f"**Pattern:** {latest['name']} ({latest['status']})")
        else:
            st.write("**Pattern:** None")

        st.write("**RSI:**", indicators['rsi'])
        st.write("**MACD:**", indicators['macd']['status'], "-", indicators['macd']['note'])

        st.write("**Trade Suggestion:**")
        st.json(risk_info)

        # Chart
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = f"charts/chart_{timestamp}.{'html' if use_plotly else 'png'}"
        plot_chart_with_levels(
            df,
            sr_result,
            trend_info=trend_result,
            patterns=patterns,
            risk_info=risk_info,
            save_file=save_path,
            show_atr=show_atr,
            show_bollinger=show_bb,
            interactive=use_plotly
        )

        if use_plotly:
            with open(save_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            st.components.v1.html(html_content, height=600)
        else:
            st.image(save_path)

        st.success("Analysis Complete ✅")

        # Alert Section
        if st.checkbox("📨 Send Alert"):
            alert_msg = f"""🚨 Trade Signal Alert: {pair} @ {inferred_tf}
Direction: {risk_info.get('trade_direction')}
Confidence: {risk_info.get('signal_score', {}).get('value')} ({risk_info.get('signal_score', {}).get('level')})
Entry Zone: {risk_info.get('entry_zone')}
SL: {risk_info.get('stop_loss')} | TP: {risk_info.get('take_profit_levels')}
Chart: {save_path}
"""
            send_email_alert(
                subject="🚨 Trade Alert",
                body=alert_msg,
                to_email=email_config["to_email"],
                from_email=email_config["from_email"],
                smtp_server=email_config["smtp_server"],
                smtp_port=email_config["smtp_port"],
                password=email_config["password"],
                attachments=[save_path]
            )
            send_telegram_alert(
                bot_token=telegram_config["bot_token"],
                chat_id=telegram_config["chat_id"],
                message=alert_msg,
                image_path=save_path
            )
            st.success("✅ Alerts sent!")

        if "df" in st.session_state and "sr_result" in st.session_state:
            with st.expander("🤖 ML Signal Prediction"):
                try:
                    signal, confidence = predict_signal(
                        st.session_state.df,
                        st.session_state.sr_result['support'],
                        st.session_state.sr_result['resistance']
            )
                    st.markdown(f"### 🧠 Predicted Signal: `{signal}` with {confidence:.1f}% confidence")
                except Exception as e:
                    st.warning(f"⚠️ ML Prediction failed: {e}")
        with st.expander("🛠 Retrain ML Model (Optional)"):
            if st.button("Train Model on Current Data"):
                try:
                    model = train_model(
                        st.session_state.df,
                        st.session_state.sr_result['support'],
                        st.session_state.sr_result['resistance']
                    )
                    st.success("✅ Model trained successfully and saved.")
                except Exception as e:
                    st.error(f"❌ Training failed: {e}")



# --- Backtesting ---
st.subheader("📊 Backtesting")

with st.expander("🧪 Optimize RSI Reversal Strategy"):
    st.write("Test RSI threshold combinations for reversal entries.")

    overbought_min = st.slider("Overbought Threshold Min", 60, 80, 65)
    overbought_max = st.slider("Overbought Threshold Max", overbought_min + 5, 90, 75)
    oversold_min = st.slider("Oversold Threshold Min", 10, 30, 25)
    oversold_max = st.slider("Oversold Threshold Max", oversold_min + 5, 40, 35)

    if st.button("Run RSI Optimization"):
        if "df" not in st.session_state:
            st.warning("⚠️ Please run analysis first to load data.")
        else:
            df_bt = st.session_state.df.copy()

            

            with st.spinner("Optimizing RSI thresholds..."):
                df_rsi_opt = optimize_rsi_strategy(
                    df_bt,
                    oversold_list=list(range(oversold_min, oversold_max + 1, 5)),
                    overbought_list=list(range(overbought_min, overbought_max + 1, 5))
                )

            if df_rsi_opt.empty:
                st.warning("No valid combinations found.")
            else:
                st.success(f"✅ Tested {len(df_rsi_opt)} combinations")
                st.dataframe(df_rsi_opt)

                # ✅ Plain bar chart without multi-indexing
                st.subheader("📊 RSI Optimization Results")
                st.bar_chart(df_rsi_opt[["Winrate (%)", "Total Profit"]])

                # ✅ Optional heatmap (pivot table for Winrate)
                st.subheader("🔥 Winrate Heatmap (Pivot View)")
                pivot = df_rsi_opt.pivot(index="Oversold", columns="Overbought", values="Winrate (%)")
                st.dataframe(pivot.style.background_gradient(cmap="YlGnBu"))



with st.expander("Run Backtest"):
    strategy = st.selectbox("Select Strategy", [
        "MA Crossover",
        "MACD Signal",
        "Pattern Trigger",
        "RSI Reversal",
        "Bollinger Bounce",
        "ATR Breakout"
    ])
    run_bt = st.button("Run Backtest")

    if run_bt:
        if "df" not in st.session_state:
            st.error("❌ Please run analysis first.")
        else:
            df_bt = st.session_state.df.copy()
            bt_result = run_backtest(df_bt, capital=capital, strategy=strategy)

            st.write(f"**Total Trades:** {bt_result['total']}")
            st.write(f"**Wins:** {bt_result['wins']} | **Losses:** {bt_result['losses']}")
            st.write(f"**Winrate:** {bt_result['winrate']}%")

            if bt_result['trades']:
                bt_df = pd.DataFrame(bt_result['trades'])
                st.session_state.bt_df = bt_df  # ✅ Store globally

                st.dataframe(bt_df)

                if "profit" in bt_df.columns:
                    bt_df['cumulative_profit'] = bt_df['profit'].cumsum()
                    bt_df['equity'] = capital + bt_df['cumulative_profit']
                    bt_df['winrate'] = bt_df['result'].eq("win").cumsum() / (bt_df.index + 1) * 100

                    # --- Charts ---
                    # --- Winrate ---
                    st.subheader("📈 Winrate Over Time")
                    winrate_smooth_window = st.slider("Winrate Smoothing Window", 1, 50, 10, key="winrate_smooth")
                    bt_df['winrate_smooth'] = bt_df['winrate'].rolling(winrate_smooth_window).mean()
                    st.line_chart(bt_df[['winrate', 'winrate_smooth']].rename(columns={
                            "winrate": "Raw Winrate", "winrate_smooth": f"{winrate_smooth_window}-Trade Avg"
                        }))

                    # --- Interactive Equity Plot (Plotly) ---
                    st.subheader("📊 Interactive Equity Curve")
                    bt_df['equity_smooth'] = bt_df['equity'].rolling(10).mean()
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(y=bt_df['equity'], name="Raw Equity", mode='lines'))
                    fig.add_trace(go.Scatter(y=bt_df['equity_smooth'], name="Smoothed Equity", mode='lines'))
                    fig.update_layout(title="Equity Curve", xaxis_title="Trade #", yaxis_title="Equity ($)", template="plotly_white")
                    st.plotly_chart(fig, use_container_width=True)


                    st.subheader("📊 Cumulative Profit / Loss")
                    st.line_chart(bt_df['cumulative_profit'])

                    # --- Advanced Metrics ---
                    returns = bt_df['profit']
                    sharpe = returns.mean() / returns.std() * (252 ** 0.5) if returns.std() != 0 else 0
                    drawdown = (bt_df['equity'].cummax() - bt_df['equity']) / bt_df['equity'].cummax()
                    max_drawdown = drawdown.max()
                    profit_factor = returns[returns > 0].sum() / abs(returns[returns < 0].sum()) if returns[returns < 0].sum() != 0 else 0

                    st.markdown("### 📈 Backtest Performance Metrics")
                    st.write(f"**Sharpe Ratio:** {sharpe:.2f}")
                    st.write(f"**Max Drawdown:** {max_drawdown:.2%}")
                    st.write(f"**Profit Factor:** {profit_factor:.2f}")

                    # --- Drawdown ---
                    st.subheader("📉 Drawdown Curve")
                    drawdown_smooth_window = st.slider("Drawdown Smoothing Window", 1, 50, 10, key="dd_smooth")
                    bt_df['drawdown'] = (bt_df['equity'].cummax() - bt_df['equity']) / bt_df['equity'].cummax()
                    bt_df['drawdown_smooth'] = bt_df['drawdown'].rolling(drawdown_smooth_window).mean()
                    st.line_chart(bt_df[['drawdown', 'drawdown_smooth']].rename(columns={
                        "drawdown": "Raw Drawdown", "drawdown_smooth": f"{drawdown_smooth_window}-Trade Avg"
                    }))

                    # --- Rolling Winrate ---
                    st.subheader("📊 Rolling Winrate (10-trade window)")
                    bt_df['rolling_winrate'] = bt_df['result'].eq("win").rolling(10).mean() * 100
                    st.line_chart(bt_df['rolling_winrate'])

                    # --- CSV Export ---
                    st.download_button(
                        label="📥 Download Trade Log (CSV)",
                        data=bt_df.to_csv(index=False).encode(),
                        file_name="backtest_trades.csv",
                        mime='text/csv'
                    )

                    # --- Summary Stats Box ---
                    st.markdown("### 📦 Summary Stats")
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total P/L", f"{bt_df['profit'].sum():.2f}")
                    col2.metric("Avg Trade", f"{bt_df['profit'].mean():.4f}")
                    col3.metric("Median Trade", f"{bt_df['profit'].median():.4f}")



with st.expander("🧩 Modular Strategy Builder"):
    st.write("Define your custom strategy logic using JSON rules.")

    sample_json = {
        "entry": "MACD > Signal and RSI < 30",
        "exit": "RSI > 50 or SL or TP"
    }
    default_json = json.dumps(sample_json, indent=2)

    user_json_input = st.text_area("🧠 Strategy Rules (JSON)", value=default_json, height=150)

    if st.button("🧪 Run Custom Strategy"):
        try:
            rules = json.loads(user_json_input)
            st.success("✅ Strategy rules loaded.")
            if "df" not in st.session_state:
                st.warning("⚠️ Please run analysis first.")
            else:
                from src.strategy_engine import run_custom_strategy
                df_bt = st.session_state.df.copy()
                result = run_custom_strategy(df_bt, rules)

                st.write(f"**Trades:** {len(result)}")
                if result:
                    st.dataframe(pd.DataFrame(result))
        except json.JSONDecodeError as e:
            st.error(f"❌ Invalid JSON: {e}")


# --- Loss Streak Visualization ---
st.subheader("📉 Loss Streak Analysis")

if "bt_df" in st.session_state:
    bt_df = st.session_state.bt_df
    if "result" in bt_df.columns:
        streaks = []
        current = 0
        for r in bt_df["result"]:
            if r == "loss":
                current += 1
            else:
                if current > 0:
                    streaks.append(current)
                current = 0
        if current > 0:
            streaks.append(current)

        if streaks:
            max_streak = max(streaks)
            st.write(f"**📛 Longest Loss Streak:** {max_streak} trades")

            streak_series = pd.Series(streaks)
            streak_counts = streak_series.value_counts().sort_index()
            st.bar_chart(streak_counts.rename("Streak Count"))
        else:
            st.write("✅ No loss streaks detected.")
    else:
        st.info("ℹ️ Backtest results do not include trade outcomes.")
else:
    st.info("ℹ️ Run a backtest first to view loss streaks.")


# --- Daily P&L Aggregation ---
st.subheader("📆 Daily Profit/Loss Summary")

if "bt_df" in st.session_state:
    bt_df = st.session_state.bt_df
    if "profit" in bt_df.columns:
        bt_df['date_only'] = pd.to_datetime(bt_df['date']).dt.date
        daily_pl = bt_df.groupby('date_only')['profit'].sum()

        st.line_chart(daily_pl.cumsum().rename("Cumulative P&L"))
        st.bar_chart(daily_pl.rename("Daily P&L"))

        st.write("**P&L by Day:**")
        st.dataframe(daily_pl.reset_index().rename(columns={"date_only": "Date", "profit": "Net P&L"}))
    else:
        st.info("ℹ️ No profit data found in backtest results.")
else:
    st.info("ℹ️ Run a backtest first to view daily P&L.")


# --- Strategy Comparison ---
st.subheader("📊 Strategy Comparison")

compare_strategies = st.button("Compare All Strategies")

if compare_strategies:
    strategy_list = ["MA Crossover", "MACD Signal", "Pattern Trigger", "RSI Reversal", "Bollinger Bounce", "ATR Breakout"]
    if "df" not in st.session_state:
        st.error("❌ Please run analysis first to load data.")
    else:
        df_bt = st.session_state.df.copy()
        results = []

        for strat in strategy_list:
            bt_result = run_backtest(df_bt, capital=capital, strategy=strat)
            cumulative_profit = sum([t.get("profit", 0) for t in bt_result["trades"]])
            results.append({
                "Strategy": strat,
                "Total Trades": bt_result["total"],
                "Wins": bt_result["wins"],
                "Losses": bt_result["losses"],
                "Winrate (%)": bt_result["winrate"],
                "Cumulative P/L": round(cumulative_profit, 2)
            })

        comp_df = pd.DataFrame(results)
        st.dataframe(comp_df)

        st.bar_chart(comp_df.set_index("Strategy")[["Winrate (%)", "Cumulative P/L"]])


st.subheader("🧾 Trade Journal")

if os.path.exists("trade_journal.csv"):
    journal_df = pd.read_csv("trade_journal.csv")
    st.dataframe(journal_df)
    if st.button("📤 Export Journal"):
        st.download_button("Download CSV", journal_df.to_csv(index=False), file_name="trade_journal.csv", mime="text/csv")
else:
    st.info("No trades logged yet.")


# ✅ Log live signal to journal if available
if "risk_info" in st.session_state:
    risk_info = st.session_state["risk_info"]

    if "signal_score" in risk_info and "entry_zone" in risk_info:
        from src.journal import log_trade

        entry_zone = risk_info["entry_zone"].split(" - ")
        entry_price = round((float(entry_zone[0]) + float(entry_zone[1])) / 2, 5)
        rr_val = float(risk_info['risk_reward_ratio'].split(":")[1]) if ':' in risk_info['risk_reward_ratio'] else 1.0

        log_trade(
            strategy="Live Signal",
            entry=entry_price,
            sl=risk_info.get("stop_loss", 0),
            tp=risk_info.get("take_profit_levels", [0])[0],
            result="Pending",
            rr=rr_val,
            date=datetime.now().strftime("%Y-%m-%d %H:%M"),
            chart_path=st.session_state.get("chart_path", "")
        )

# --- Save Config ---
with open(CONFIG_FILE, "w") as f:
    json.dump(config, f, indent=2)
