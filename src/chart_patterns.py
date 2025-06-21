import pandas as pd
import numpy as np
from scipy.signal import find_peaks

def detect_double_top_bottom(df: pd.DataFrame, threshold=0.005, min_distance=10) -> list:
    patterns = []

    prices = df['Close'].values
    dates = df.index

    # Detect peaks and troughs
    peaks, _ = find_peaks(prices, distance=min_distance)
    troughs, _ = find_peaks(-prices, distance=min_distance)

    # Track last used peak/trough to avoid overlap
    last_top_index = -50
    last_bottom_index = -50

    # --- Double Top Detection ---
    for i in range(len(peaks) - 1):
        p1, p2 = peaks[i], peaks[i + 1]

        # Skip if too close to last detected pattern
        if p1 - last_top_index < 30:
            continue

        # Price similarity check
        if abs(prices[p1] - prices[p2]) / prices[p1] < threshold:
            # Check for valley in between
            middle = prices[p1+1:p2]
            if len(middle) > 0 and middle.min() < min(prices[p1], prices[p2]):
                neckline = middle.min()
                projected_target = neckline - (prices[p1] - neckline)

                pattern = {
                    "name": "Double Top",
                    "status": "forming" if p2 >= len(prices) - 2 else "completed",
                    "validation_confidence": 0.8,
                    "peak1": round(prices[p1], 5),
                    "peak2": round(prices[p2], 5),
                    "neckline": round(neckline, 5),
                    "projected_target": round(projected_target, 5)
                }
                patterns.append(pattern)
                last_top_index = p2  # prevent overlapping

    # --- Double Bottom Detection ---
    for i in range(len(troughs) - 1):
        t1, t2 = troughs[i], troughs[i + 1]

        # Skip if too close to last detected pattern
        if t1 - last_bottom_index < 30:
            continue

        # Price similarity check
        if abs(prices[t1] - prices[t2]) / prices[t1] < threshold:
            # Check for peak in between
            middle = prices[t1+1:t2]
            if len(middle) > 0 and middle.max() > max(prices[t1], prices[t2]):
                neckline = middle.max()
                projected_target = neckline + (neckline - prices[t1])

                pattern = {
                    "name": "Double Bottom",
                    "status": "forming" if t2 >= len(prices) - 2 else "completed",
                    "validation_confidence": 0.8,
                    "trough1": round(prices[t1], 5),
                    "trough2": round(prices[t2], 5),
                    "neckline": round(neckline, 5),
                    "projected_target": round(projected_target, 5)
                }
                patterns.append(pattern)
                last_bottom_index = t2

    latest_top = next((p for p in reversed(patterns) if p['name'] == 'Double Top'), None)
    latest_bottom = next((p for p in reversed(patterns) if p['name'] == 'Double Bottom'), None)
    return [p for p in [latest_top, latest_bottom] if p]

