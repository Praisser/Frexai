import pandas as pd
import numpy as np
from ta.trend import MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from datetime import datetime
from src.journal import log_trade

def simulate_trade_execution(df, entry_idx, direction, entry, sl, tp):
    for j in range(entry_idx + 1, len(df)):
        high = df['High'].iloc[j]
        low = df['Low'].iloc[j]
        time = df.index[j]

        if direction == "Buy":
            if low <= sl:
                return "loss", -abs(entry - sl), time
            elif high >= tp:
                return "win", abs(tp - entry), time
        elif direction == "Sell":
            if high >= sl:
                return "loss", -abs(entry - sl), time
            elif low <= tp:
                return "win", abs(entry - tp), time
    return "open", 0, df.index[-1]


def run_backtest(df, capital=10000, strategy="MA Crossover"):
    df = df.copy()
    trades = []
    stop_loss_pct = 0.01
    take_profit_pct = 0.02

    if len(df) < 50:
        return {"total": 0, "wins": 0, "losses": 0, "winrate": 0, "trades": []}

    if strategy == "MA Crossover":
        df['MA_Short'] = df['Close'].rolling(10).mean()
        df['MA_Long'] = df['Close'].rolling(30).mean()
        for i in range(30, len(df)):
            if df['MA_Short'].iloc[i] > df['MA_Long'].iloc[i] and df['MA_Short'].iloc[i-1] <= df['MA_Long'].iloc[i-1]:
                entry = df['Close'].iloc[i]
                trades.append({"Type": "Buy", "Entry": entry, "SL": entry * 0.99, "TP": entry * 1.02, "entry_idx": i})
            elif df['MA_Short'].iloc[i] < df['MA_Long'].iloc[i] and df['MA_Short'].iloc[i-1] >= df['MA_Long'].iloc[i-1]:
                entry = df['Close'].iloc[i]
                trades.append({"Type": "Sell", "Entry": entry, "SL": entry * 1.01, "TP": entry * 0.98, "entry_idx": i})

    elif strategy == "MACD Signal":
        macd = MACD(df['Close'])
        df['macd'] = macd.macd()
        df['signal'] = macd.macd_signal()
        for i in range(1, len(df)):
            if df['macd'].iloc[i] > df['signal'].iloc[i] and df['macd'].iloc[i-1] <= df['signal'].iloc[i-1]:
                entry = df['Close'].iloc[i]
                trades.append({"Type": "Buy", "Entry": entry, "SL": entry * 0.99, "TP": entry * 1.02, "entry_idx": i})
            elif df['macd'].iloc[i] < df['signal'].iloc[i] and df['macd'].iloc[i-1] >= df['signal'].iloc[i-1]:
                entry = df['Close'].iloc[i]
                trades.append({"Type": "Sell", "Entry": entry, "SL": entry * 1.01, "TP": entry * 0.98, "entry_idx": i})

    elif strategy == "Pattern Trigger":
        for i in range(20, len(df)):
            recent = df['Close'].iloc[i-5:i]
            entry = df['Close'].iloc[i]
            if recent.is_monotonic_increasing:
                trades.append({"Type": "Sell", "Entry": entry, "SL": entry * 1.01, "TP": entry * 0.98, "entry_idx": i})
            elif recent.is_monotonic_decreasing:
                trades.append({"Type": "Buy", "Entry": entry, "SL": entry * 0.99, "TP": entry * 1.02, "entry_idx": i})

    elif strategy == "RSI Reversal":
        rsi = RSIIndicator(df['Close'])
        df['rsi'] = rsi.rsi()
        for i in range(1, len(df)):
            entry = df['Close'].iloc[i]
            if df['rsi'].iloc[i] > 30 and df['rsi'].iloc[i-1] <= 30:
                trades.append({"Type": "Buy", "Entry": entry, "SL": entry * 0.99, "TP": entry * 1.02, "entry_idx": i})
            elif df['rsi'].iloc[i] < 70 and df['rsi'].iloc[i-1] >= 70:
                trades.append({"Type": "Sell", "Entry": entry, "SL": entry * 1.01, "TP": entry * 0.98, "entry_idx": i})

    elif strategy == "Bollinger Bounce":
        bb = BollingerBands(df['Close'])
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_lower'] = bb.bollinger_lband()
        rsi = RSIIndicator(df['Close'])
        df['rsi'] = rsi.rsi()
        for i in range(1, len(df)):
            entry = df['Close'].iloc[i]
            if df['Close'].iloc[i] < df['bb_lower'].iloc[i] and df['rsi'].iloc[i] > df['rsi'].iloc[i-1]:
                trades.append({"Type": "Buy", "Entry": entry, "SL": entry * 0.99, "TP": entry * 1.02, "entry_idx": i})
            elif df['Close'].iloc[i] > df['bb_upper'].iloc[i] and df['rsi'].iloc[i] < df['rsi'].iloc[i-1]:
                trades.append({"Type": "Sell", "Entry": entry, "SL": entry * 1.01, "TP": entry * 0.98, "entry_idx": i})

    elif strategy == "ATR Breakout":
        atr = AverageTrueRange(df['High'], df['Low'], df['Close'])
        df['atr'] = atr.average_true_range()
        for i in range(14, len(df)):
            range_ = df['High'].iloc[i] - df['Low'].iloc[i]
            entry = df['Close'].iloc[i]
            if range_ > 1.5 * df['atr'].iloc[i]:
                if df['Close'].iloc[i] > df['Open'].iloc[i]:
                    trades.append({"Type": "Buy", "Entry": entry, "SL": entry * 0.99, "TP": entry * 1.02, "entry_idx": i})
                else:
                    trades.append({"Type": "Sell", "Entry": entry, "SL": entry * 1.01, "TP": entry * 0.98, "entry_idx": i})

    # --- Evaluate Trades ---
    wins, losses = 0, 0
    evaluated_trades = []

    for t in trades:
        entry_idx = t["entry_idx"]
        entry = t["Entry"]
        sl = t["SL"]
        tp = t["TP"]
        direction = t["Type"]

        result, profit, close_time = simulate_trade_execution(df, entry_idx, direction, entry, sl, tp)
        rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0

        t.update({
            "result": result,
            "profit": round(profit, 5),
            "RR": round(rr, 2),
            "date": close_time.strftime("%Y-%m-%d %H:%M")
        })

        if result == "win":
            wins += 1
        elif result == "loss":
            losses += 1

        log_trade(strategy=strategy, entry=entry, sl=sl, tp=tp, result=result, rr=rr, date=t["date"], chart_path="")

        evaluated_trades.append(t)

    total = len(evaluated_trades)
    winrate = round(100 * wins / total, 2) if total > 0 else 0

    return {
        "total": total,
        "wins": wins,
        "losses": losses,
        "winrate": winrate,
        "trades": evaluated_trades
    }

def optimize_rsi_strategy(df, oversold_list=[25, 30, 35], overbought_list=[65, 70, 75]):
    from ta.momentum import RSIIndicator
    results = []

    for os in oversold_list:
        for ob in overbought_list:
            if os >= ob:
                continue
            rsi = RSIIndicator(df['Close'])
            df['rsi'] = rsi.rsi()

            wins = 0
            losses = 0
            profit = 0
            for i in range(1, len(df)):
                entry = df['Close'].iloc[i]
                if df['rsi'].iloc[i] > os and df['rsi'].iloc[i - 1] <= os:
                    tp = entry * 1.02
                    sl = entry * 0.99
                    if tp > entry:
                        wins += 1
                        profit += tp - entry
                    else:
                        losses += 1
                        profit -= entry - sl

            total = wins + losses
            winrate = round(100 * wins / total, 2) if total else 0
            results.append({
                "Oversold": os,
                "Overbought": ob,
                "Trades": total,
                "Wins": wins,
                "Losses": losses,
                "Winrate (%)": winrate,
                "Total Profit": round(profit, 2)
            })

    return pd.DataFrame(results)
