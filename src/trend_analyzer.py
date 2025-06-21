import pandas as pd
import numpy as np
from ta.trend import MACD

def detect_trend(df: pd.DataFrame, short_window=20, long_window=50) -> dict:
    df = df.copy()

    # Calculate Moving Averages
    df['SMA_short'] = df['Close'].rolling(window=short_window).mean()
    df['SMA_long'] = df['Close'].rolling(window=long_window).mean()

    # Price Slope
    y = df['Close'].tail(20).values
    x = np.arange(len(y))
    slope = np.polyfit(x, y, 1)[0]

    # MACD
    macd = MACD(close=df['Close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    macd_value = df['macd'].iloc[-1]
    macd_signal = df['macd_signal'].iloc[-1]

    # Price structure
    recent_highs = df['High'].tail(10)
    recent_lows = df['Low'].tail(10)
    is_hh = recent_highs.is_monotonic_increasing
    is_hl = recent_lows.is_monotonic_increasing
    is_lh = recent_highs.is_monotonic_decreasing
    is_ll = recent_lows.is_monotonic_decreasing

    sma_short = df['SMA_short'].iloc[-1]
    sma_long = df['SMA_long'].iloc[-1]
    price = df['Close'].iloc[-1]

    trend = "Sideways"
    confidence = 0.5
    reasons = []

    # Build logic
    bullish_signals = 0
    bearish_signals = 0

    # MA alignment
    if sma_short > sma_long:
        bullish_signals += 1
        reasons.append("20 SMA is above 50 SMA (bullish)")
    elif sma_short < sma_long:
        bearish_signals += 1
        reasons.append("20 SMA is below 50 SMA (bearish)")

    # Slope
    if slope > 0:
        bullish_signals += 1
        reasons.append("Price slope is upward")
    elif slope < 0:
        bearish_signals += 1
        reasons.append("Price slope is downward")

    # MACD
    if macd_value > macd_signal:
        bullish_signals += 1
        reasons.append("MACD shows bullish crossover")
    elif macd_value < macd_signal:
        bearish_signals += 1
        reasons.append("MACD shows bearish crossover")

    # Structure adds bonus
    if is_hh and is_hl:
        bullish_signals += 1
        reasons.append("Higher Highs and Higher Lows")
    elif is_lh and is_ll:
        bearish_signals += 1
        reasons.append("Lower Highs and Lower Lows")

    # Final trend decision
    if bullish_signals >= 2:
        trend = "Uptrend"
        confidence = 0.6 + 0.1 * (bullish_signals - 2)
    elif bearish_signals >= 2:
        trend = "Downtrend"
        confidence = 0.6 + 0.1 * (bearish_signals - 2)
    else:
        trend = "Sideways"
        confidence = 0.5

    return {
        "trend": trend,
        "confidence": round(min(confidence, 0.95), 2),
        "justification": "; ".join(reasons)
    }
