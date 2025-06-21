from ta.volatility import AverageTrueRange
import pandas as pd

def suggest_trade_levels(
    df: pd.DataFrame,
    trend: str,
    support_levels: list,
    resistance_levels: list,
    risk_percent: float = 1.0,
    capital: float = 10000,
    rr_threshold: float = 1.5,
    slippage: float = 0.0002  # e.g., 2 pips
) -> dict:

    df = df.copy()

    MIN_CANDLES = 20
    if len(df) < MIN_CANDLES:
        return {
            "trade_direction": "Not available",
            "note": f"Not enough candles to compute ATR (need {MIN_CANDLES}, got {len(df)})."
        }

    current_price = df['Close'].iloc[-1]

    try:
        atr_series = AverageTrueRange(high=df['High'], low=df['Low'], close=df['Close'], window=14).average_true_range()
        atr_value = atr_series.dropna().iloc[-1]
    except Exception:
        atr_value = (df['High'] - df['Low']).rolling(5).mean().iloc[-1]  # fallback: 5-bar range average

    if pd.isna(atr_value) or atr_value == 0:
        return {
            "note": f"Not enough candles to compute ATR (need 20+, got {len(df)}).",
            "trade_direction": "Insufficient data"
    }


    sl_buffer = atr_value
    tp_buffer = 2 * atr_value
    trailing_stop = round(current_price - atr_value if trend.lower() == "uptrend" else current_price + atr_value, 5)

    if trend.lower() == "uptrend":
        direction = "Long"
        entry = round(current_price + slippage, 5)
        stop_loss = round(entry - sl_buffer, 5)
        take_profits = [round(entry + tp_buffer, 5)]
    elif trend.lower() == "downtrend":
        direction = "Short"
        entry = round(current_price - slippage, 5)
        stop_loss = round(entry + sl_buffer, 5)
        take_profits = [round(entry - tp_buffer, 5)]
    else:
        return {
            "trade_direction": "No clear direction",
            "note": "Trend not strong enough to justify a trade"
        }

    # --- Risk-Reward Calculation ---
    risk_per_unit = abs(entry - stop_loss)
    reward_per_unit = abs(take_profits[0] - entry)
    rr_ratio = round(reward_per_unit / risk_per_unit, 2) if risk_per_unit else 0.0

    rr_warning = None
    if rr_ratio < rr_threshold:
        rr_warning = f"⚠️ Risk-Reward Ratio {rr_ratio} is below threshold {rr_threshold}!"

    # --- Position Size Calculation ---
    risk_capital = capital * (risk_percent / 100)
    position_size = round(risk_capital / risk_per_unit, 2) if risk_per_unit else 0



    # --- Confidence Scoring ---
    score = 0
    details = []

    # Trend
    if trend.lower() == "uptrend" or trend.lower() == "downtrend":
        score += 30
        details.append("Trend confirmed")
    else:
        details.append("No clear trend")

    # Indicators (optional: pass in indicators dict if needed)
    # For now we just assume that if risk_info got here, indicators agree
    score += 20
    details.append("Indicators assumed aligned")

    # Risk-Reward
    rr_val = rr_ratio
    if rr_val >= 2:
        score += 30
        details.append("RR ≥ 2.0")
    elif rr_val >= 1.5:
        score += 20
        details.append("RR ≥ 1.5")
    elif rr_val >= 1.2:
        score += 10
        details.append("RR ≥ 1.2")
    else:
        details.append("Poor RR")

    # ATR Valid
    if atr_value > 0:
        score += 20
        details.append("ATR valid")

    # Tag
    if score >= 75:
        confidence_level = "Strong"
    elif score >= 50:
        confidence_level = "Moderate"
    else:
        confidence_level = "Weak"

    return {
        "trade_direction": direction,
        "entry_zone": f"{round(entry * 0.999, 5)} - {round(entry * 1.001, 5)}",
        "stop_loss": stop_loss,
        "take_profit_levels": take_profits,
        "risk_reward_ratio": f"1:{rr_ratio} (to first TP)",
        "atr": round(atr_value, 5),
        "trailing_stop_suggestion": trailing_stop,
        "position_sizing_guidance": f"Risking {risk_percent}% of ${capital} = ${risk_capital:.2f}; suggested size: {position_size} units",
        "slippage_applied": slippage,
        "rr_alert": rr_warning,
        "signal_score": {
            "value": score,
            "level": confidence_level,
            "reasoning": details
        }
    }
