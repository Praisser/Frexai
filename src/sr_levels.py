# src/sr_levels.py

import pandas as pd
import numpy as np
from scipy.signal import find_peaks
from collections import defaultdict

def identify_sr_levels(df: pd.DataFrame, distance=5, threshold=0.0015, round_to=0.0005) -> dict:
    """
    Identify support and resistance levels based on local extrema clustering.
    Returns a dictionary with level, type, and strength.
    """

    highs = df['High'].values
    lows = df['Low'].values

    # Find local peaks (resistance)
    res_idx, _ = find_peaks(highs, distance=distance)
    sup_idx, _ = find_peaks(-lows, distance=distance)

    levels = defaultdict(int)

    for idx in res_idx:
        level = round(highs[idx] / round_to) * round_to
        levels[level] += 1

    for idx in sup_idx:
        level = round(lows[idx] / round_to) * round_to
        levels[level] += 1

    # Filter and sort
    sr_levels = []
    for level, touches in sorted(levels.items(), key=lambda x: x[0]):
        strength = (
            "strong" if touches >= 4 else
            "moderate" if touches == 3 else
            "weak"
        )
        sr_levels.append({
            "price": round(level, 5),
            "strength": strength,
            "touches": touches
        })

    # Separate support/resistance based on current price
    current_price = df['Close'].iloc[-1]
    supports = [lvl for lvl in sr_levels if lvl["price"] < current_price]
    resistances = [lvl for lvl in sr_levels if lvl["price"] > current_price]

    supports = sorted(supports, key=lambda x: -x["price"])[:3]
    resistances = sorted(resistances, key=lambda x: x["price"])[:3]

    return {
        "support": supports,
        "resistance": resistances
    }
    