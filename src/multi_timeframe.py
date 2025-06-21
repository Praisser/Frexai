from src.mt5_fetcher import fetch_mt5_data
from src.trend_analyzer import detect_trend
from src.risk_manager import suggest_trade_levels
from src.sr_levels import identify_sr_levels

def analyze_confluence(symbol, tf1="M15", tf2="H1", capital=10000):
    df1 = fetch_mt5_data(symbol, tf1)
    df2 = fetch_mt5_data(symbol, tf2)

    trend1 = detect_trend(df1)
    trend2 = detect_trend(df2)

    sr1 = identify_sr_levels(df1)
    sr2 = identify_sr_levels(df2)

    risk1 = suggest_trade_levels(df1, trend1['trend'], sr1['support'], sr1['resistance'], capital=capital)
    risk2 = suggest_trade_levels(df2, trend2['trend'], sr2['support'], sr2['resistance'], capital=capital)

    trend_agree = trend1['trend'] == trend2['trend'] and trend1['trend'] != "Sideways"

    return {
        "timeframes": [tf1, tf2],
        "trend_1": trend1,
        "trend_2": trend2,
        "agreement": trend_agree,
        "verdict": "✅ Strong Confluence" if trend_agree else "⚠️ Trend Mismatch",
        "risk_1": risk1,
        "risk_2": risk2
    }
