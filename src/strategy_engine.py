import pandas as pd
from ta.trend import MACD
from ta.momentum import RSIIndicator

def run_custom_strategy(df, rules: dict):
    df = df.copy()
    df['macd'] = MACD(df['Close']).macd()
    df['signal'] = MACD(df['Close']).macd_signal()
    df['rsi'] = RSIIndicator(df['Close']).rsi()

    # Simple logic evaluator
    trades = []
    for i in range(1, len(df)):
        entry_cond = (
            df['macd'].iloc[i] > df['signal'].iloc[i] and
            df['rsi'].iloc[i] < 30
        ) if rules["entry"] == "MACD > Signal and RSI < 30" else False

        if entry_cond:
            entry = df['Close'].iloc[i]
            sl = entry * 0.99
            tp = entry * 1.02
            trades.append({
                "Type": "Buy",
                "Entry": round(entry, 5),
                "SL": round(sl, 5),
                "TP": round(tp, 5),
                "Date": df.index[i].strftime("%Y-%m-%d %H:%M")
            })

    return trades
