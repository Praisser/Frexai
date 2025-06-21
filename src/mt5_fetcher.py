import MetaTrader5 as mt5
import pandas as pd
import time

# Map string timeframe to MT5 constant
TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1
}

def is_mt5_available() -> bool:
    try:
        return mt5.initialize()
    except Exception:
        return False

def fetch_mt5_data(symbol="EURUSD", timeframe_str="M15", bars=500):
    if not mt5.initialize():
        raise ConnectionError("❌ MT5 initialization failed. Ensure terminal is open and logged in.")

    timeframe = TIMEFRAME_MAP.get(timeframe_str.upper())
    if timeframe is None:
        raise ValueError(f"Invalid timeframe: {timeframe_str}")

    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
    if rates is None or len(rates) == 0:
        raise RuntimeError(f"❌ No data returned from MT5 for {symbol} {timeframe_str}")

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    df.rename(columns={
        'open': 'Open',
        'high': 'High',
        'low': 'Low',
        'close': 'Close',
        'tick_volume': 'Volume'
    }, inplace=True)
    df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
    return df

# --- Real-time bar stream preview ---
def stream_mt5_bars(symbol, timeframe_str="M1", interval_sec=60, bars=100, updates=5):
    from .mt5_fetcher import fetch_mt5_data

    for i in range(updates):
        df = fetch_mt5_data(symbol, timeframe_str, bars)
        print(f"\n📊 Update {i+1} — Last Close: {df['Close'].iloc[-1]}")
        time.sleep(interval_sec)


def stream_and_analyze(
    symbol="EURUSD",
    timeframe_str="M1",
    interval_sec=60,
    bars=200,
    updates=5,
    capital=10000
):
    from src.trend_analyzer import detect_trend
    from src.sr_levels import identify_sr_levels
    from src.chart_patterns import detect_double_top_bottom
    from src.indicator_analysis import analyze_indicators
    from src.risk_manager import suggest_trade_levels

    print(f"\n📡 Starting live MT5 analysis: {symbol} @ {timeframe_str}, every {interval_sec}s\n")

    for i in range(updates):
        try:
            df = fetch_mt5_data(symbol, timeframe_str, bars)
            print(f"\n⏱ Update {i+1}: Last bar @ {df.index[-1]}")

            # Trend
            trend_result = detect_trend(df)
            print(f"→ Trend: {trend_result['trend']} | Confidence: {trend_result['confidence']}")

            # Support/Resistance
            sr_result = identify_sr_levels(df)
            support = [f"{s['price']} ({s['strength']})" for s in sr_result['support']]
            resistance = [f"{r['price']} ({r['strength']})" for r in sr_result['resistance']]
            print(f"→ Support: {', '.join(support[:2])}")
            print(f"→ Resistance: {', '.join(resistance[:2])}")

            # Patterns
            patterns = detect_double_top_bottom(df)
            if patterns:
                p = patterns[-1]
                print(f"→ Pattern: {p['name']} ({p['status']}) @ Target: {p['projected_target']}")
            else:
                print("→ Pattern: None")

            # Indicators
            indicators = analyze_indicators(df)
            print(f"→ RSI: {indicators['rsi']['value']} ({indicators['rsi']['status']})")
            print(f"→ MACD: {indicators['macd']['status']}, {indicators['macd']['note']}")

            # Risk Management
            risk_info = suggest_trade_levels(
                df=df,
                trend=trend_result['trend'],
                support_levels=sr_result['support'],
                resistance_levels=sr_result['resistance'],
                capital=capital
            )

            if 'note' in risk_info:
                print(f"→ Trade Signal: {risk_info['note']}")
            else:
                print(f"→ Trade: {risk_info['trade_direction']} | RR: {risk_info['risk_reward_ratio']}")

        except Exception as e:
            print(f"⚠️ Error in update {i+1}: {e}")

        time.sleep(interval_sec)

    print("\n✅ Finished live analysis loop.")
