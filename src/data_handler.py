import pandas as pd
from src.live_fetcher import fetch_live_forex

def load_forex_data(filepath):
    df = pd.read_csv(filepath)

    if 'Date' in df.columns and 'Time' in df.columns:
        df['Datetime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'])
        df.drop(columns=['Date', 'Time'], inplace=True)
    elif 'Datetime' in df.columns:
        df['Datetime'] = pd.to_datetime(df['Datetime'])
    else:
        raise ValueError("CSV must have 'Date'+'Time' or 'Datetime' columns.")

    df.set_index('Datetime', inplace=True)
    df[['Open', 'High', 'Low', 'Close', 'Volume']] = df[['Open', 'High', 'Low', 'Close', 'Volume']].apply(pd.to_numeric, errors='coerce')
    df.dropna(inplace=True)

    inferred_tf = "Unknown"
    if len(df) > 1:
        delta = (df.index[1] - df.index[0]).total_seconds()
        if delta <= 60: inferred_tf = "M1"
        elif delta <= 300: inferred_tf = "M5"
        elif delta <= 900: inferred_tf = "M15"
        elif delta <= 1800: inferred_tf = "M30"
        elif delta <= 3600: inferred_tf = "H1"
        elif delta <= 14400: inferred_tf = "H4"
        elif delta <= 86400: inferred_tf = "D1"

    return df, inferred_tf
