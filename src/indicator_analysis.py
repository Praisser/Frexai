# src/indicator_analysis.py

import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD
from ta.trend import SMAIndicator

def analyze_indicators(df: pd.DataFrame) -> dict:
    df = df.copy()

    # --- RSI ---
    rsi = RSIIndicator(close=df['Close'], window=14)
    df['rsi'] = rsi.rsi()
    rsi_value = df['rsi'].iloc[-1]

    if rsi_value > 70:
        rsi_status = "Overbought"
    elif rsi_value < 30:
        rsi_status = "Oversold"
    else:
        rsi_status = "Neutral"

    # --- MACD ---
    macd = MACD(close=df['Close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['macd_hist'] = macd.macd_diff()

    macd_val = df['macd'].iloc[-1]
    signal_val = df['macd_signal'].iloc[-1]
    hist_val = df['macd_hist'].iloc[-1]

    if macd_val > signal_val:
        macd_status = "Bullish Crossover"
    elif macd_val < signal_val:
        macd_status = "Bearish Crossover"
    else:
        macd_status = "Neutral"

    hist_direction = "Increasing" if df['macd_hist'].iloc[-1] > df['macd_hist'].iloc[-2] else "Decreasing"

    # --- Moving Averages ---
    sma_50 = SMAIndicator(close=df['Close'], window=50).sma_indicator()
    sma_200 = SMAIndicator(close=df['Close'], window=200).sma_indicator()

    sma_50_val = sma_50.iloc[-1]
    sma_200_val = sma_200.iloc[-1]
    price = df['Close'].iloc[-1]

    price_relation = (
        "Above 50 SMA & 200 SMA" if price > sma_50_val and price > sma_200_val
        else "Below 50 SMA & 200 SMA" if price < sma_50_val and price < sma_200_val
        else "Mixed"
    )

    if sma_50_val > sma_200_val:
        crossover = "Golden Cross"
    elif sma_50_val < sma_200_val:
        crossover = "Death Cross"
    else:
        crossover = "No clear crossover"

    # --- Summary Logic ---
    confirmations = []
    if rsi_status == "Oversold" and macd_status == "Bullish Crossover" and "Above" in price_relation:
        summary = "Indicators confirm bullish bias."
    elif rsi_status == "Overbought" and macd_status == "Bearish Crossover" and "Below" in price_relation:
        summary = "Indicators confirm bearish bias."
    else:
        summary = "Indicators show mixed signals."

    return {
        "rsi": {
            "value": round(rsi_value, 2),
            "status": rsi_status,
            "note": "No divergence check yet"
        },
        "macd": {
            "macd_line": round(macd_val, 5),
            "signal_line": round(signal_val, 5),
            "status": macd_status,
            "note": f"Histogram is {hist_direction}"
        },
        "moving_averages": {
            "price_relation": price_relation,
            "crossovers": crossover
        },
        "summary": summary
    }
