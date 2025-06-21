from datetime import datetime
import os
import json
import pandas as pd
import json
from src.data_handler import load_forex_data, fetch_live_forex
from src.mt5_fetcher import fetch_mt5_data, is_mt5_available
from src.trend_analyzer import detect_trend
from src.sr_levels import identify_sr_levels
from src.chart_patterns import detect_double_top_bottom
from src.visualizer import plot_chart_with_levels
from src.indicator_analysis import analyze_indicators
from src.risk_manager import suggest_trade_levels
from src.alerts import send_email_alert, send_telegram_alert

CONFIG_FILE = "user_config.json"
with open("secrets.json", "r") as f:
    secrets = json.load(f)

email_config = secrets["email"]
telegram_config = secrets["telegram"]
# --- Load or Create Config ---
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
    except Exception:
        config = {}
        print("⚠️ Failed to load config. Using defaults.")
else:
    config = {}

# --- Capital Input ---
capital = float(config.get("capital", 10000))
print(f"\n💰 Last used capital: ${capital}")
if input("✏️ Change capital? (y/n): ").strip().lower() == "y":
    while True:
        try:
            capital = float(input("Enter trading capital: ").strip())
            config["capital"] = capital
            break
        except ValueError:
            print("❌ Invalid number. Try again.")

# --- Chart Preferences ---
def ask_or_remember(key, question):
    if key not in config:
        config[key] = input(question + " (y/n): ").strip().lower() == "y"
    return config[key]

use_plotly = ask_or_remember("use_plotly", "\n🌐 Use interactive Plotly HTML charts?")
show_atr = ask_or_remember("show_atr", "📏 Show ATR Bands?")
show_bb = ask_or_remember("show_bollinger", "📈 Show Bollinger Bands?")

# --- Choose Data Source ---
mode = input("\n🔄 Use live Forex data? (y/n): ").strip().lower()
if mode == "y":
    if is_mt5_available():
        source = "mt5"
        print("🟢 MT5 is available.")
    else:
        source = "td"
        print("🔵 Falling back to TwelveData.")

    # --- Pair Selection ---
    print("\n📈 Available Pairs:")
    pairs = ['EURUSD', 'GBPJPY', 'USDJPY', 'AUDUSD', 'USDCAD']
    for i, p in enumerate(pairs, 1):
        print(f"{i}. {p}")
    try:
        pair = pairs[int(input("Select pair number: ")) - 1]
    except:
        pair = 'EURUSD'

    # --- Timeframe Selection ---
    print("\n⏱ Timeframes:")
    timeframes = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1']
    for i, tf in enumerate(timeframes, 1):
        print(f"{i}. {tf}")
    try:
        tf_choice = timeframes[int(input("Select timeframe: ")) - 1]
    except:
        tf_choice = 'M15'

    if source == "mt5":
        df = fetch_mt5_data(pair, tf_choice)
    else:
        interval_map = {'M1': '1min', 'M5': '5min', 'M15': '15min', 'M30': '30min', 'H1': '1h', 'H4': '4h', 'D1': '1day'}
        df, _ = fetch_live_forex(pair, interval_map[tf_choice])

    inferred_tf = tf_choice
    config["last_pair"] = pair
    config["last_timeframe"] = tf_choice

else:
    df, inferred_tf = load_forex_data('data/AUXAUD_M1_2024.csv')
    pair = "AUX/AUD (file)"
    print(f"\n⏱ Inferred timeframe: {inferred_tf}")
    print("⏱ Resample?")
    timeframes = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1']
    try:
        tf_choice = timeframes[int(input("Enter timeframe number or blank: ")) - 1]
        resample_map = {'M1': '1min', 'M5': '5min', 'M15': '15min', 'M30': '30min', 'H1': '1H', 'H4': '4H', 'D1': '1D'}
        df = df.resample(resample_map[tf_choice]).agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
        }).dropna()
        inferred_tf = tf_choice
    except:
        print("❌ Keeping original.")

# --- Filter Last 2 Days ---
df = df[df.index >= df.index.max() - pd.Timedelta(days=2)]
print(f"\n📅 Loaded {len(df)} candles at {inferred_tf}")

# --- ANALYSIS ---
trend_result = detect_trend(df)
sr_result = identify_sr_levels(df)
patterns = detect_double_top_bottom(df)
indicators = analyze_indicators(df)
risk_info = suggest_trade_levels(
    df, trend_result['trend'], sr_result['support'], sr_result['resistance'],
    capital=capital, risk_percent=1.0, rr_threshold=1.5, slippage=0.0002
)

# --- PRINT RESULTS ---
print("\n🔍 Trend Analysis:")
print(f"→ Trend: {trend_result['trend']} ({trend_result['confidence']}) — {trend_result['justification']}")

print("\n📉 Support:")
for s in sr_result['support']: print(f"→ {s['price']} ({s['strength']})")

print("\n📈 Resistance:")
for r in sr_result['resistance']: print(f"→ {r['price']} ({r['strength']})")

print("\n📊 Chart Patterns:")
if patterns:
    for p in patterns:
        print(f"→ {p['name']} ({p['status']} @ {p['projected_target']})")
else:
    print("→ None")

print("\n📌 Indicators:")
print(f"→ RSI: {indicators['rsi']['value']} ({indicators['rsi']['status']})")
print(f"→ MACD: {indicators['macd']['status']} — {indicators['macd']['note']}")
print(f"→ MAs: {indicators['moving_averages']['price_relation']}, {indicators['moving_averages']['crossovers']}")
print(f"→ Summary: {indicators['summary']}")

print("\n⚠️ Risk Suggestion:")
if 'note' in risk_info:
    print(f"→ {risk_info['note']}")
else:
    print(f"→ Direction: {risk_info['trade_direction']}")
    print(f"→ Entry: {risk_info['entry_zone']} | SL: {risk_info['stop_loss']} | TP: {risk_info['take_profit_levels']}")
    print(f"→ RR: {risk_info['risk_reward_ratio']}")
    print(f"→ Position Size: {risk_info['position_sizing_guidance']}")
    if risk_info.get("rr_alert"):
        print(f"   {risk_info['rr_alert']}")
    if "signal_score" in risk_info:
        print(f"\n📊 Signal Score: {risk_info['signal_score']['value']} ({risk_info['signal_score']['level']})")
        for reason in risk_info['signal_score']['reasoning']:
            print(f"   → {reason}")

# --- Save Chart ---
timestamp = datetime.now().strftime("%Y%m%d_%H%M")
os.makedirs("charts", exist_ok=True)
save_path = f"charts/chart_{timestamp}.{'html' if use_plotly else 'png'}"

plot_chart_with_levels(
    df, sr_result, trend_info=trend_result, patterns=patterns, risk_info=risk_info,
    save_file=save_path, show_atr=show_atr, show_bollinger=show_bb, interactive=use_plotly
)
print(f"\n🖼 Chart saved: {save_path}")

# --- Stream Live Reanalysis (Optional) ---
if input("📡 Stream live MT5 re-analysis every 60s? (y/n): ").strip().lower() == "y" and source == "mt5":
    from src.mt5_fetcher import stream_and_analyze
    stream_and_analyze(symbol=pair, timeframe_str=tf_choice, interval_sec=60, updates=10, capital=capital)

# --- Save JSON Summary ---
summary = {
    "pair": pair, "timeframe": inferred_tf, "trend": trend_result,
    "support": sr_result['support'], "resistance": sr_result['resistance'],
    "patterns": patterns, "indicators": indicators, "risk_info": risk_info
}
json_path = f"charts/summary_{timestamp}.json"
with open(json_path, "w") as f:
    json.dump(summary, f, indent=2)
print(f"📄 Summary saved: {json_path}")

# --- Save Config ---
with open(CONFIG_FILE, "w") as f:
    json.dump(config, f, indent=2)

# --- Alerts ---
if "signal_score" in risk_info:
    alert_msg = f"""🚨 Trade Alert: {pair} @ {inferred_tf}
Direction: {risk_info['trade_direction']}
Confidence: {risk_info['signal_score']['value']} ({risk_info['signal_score']['level']})
Entry: {risk_info['entry_zone']}
SL: {risk_info['stop_loss']} | TP: {risk_info['take_profit_levels']}
Chart: {save_path}"""

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
