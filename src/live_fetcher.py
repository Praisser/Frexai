from twelvedata import TDClient
import os

TD_API_KEY = os.getenv("TD_API_KEY") or "2e4977cb99c34d1188b62619ed07d89a"

def fetch_live_forex(symbol: str, interval: str = "1min", outputsize: int = 100):
    td = TDClient(apikey=TD_API_KEY)

    try:
        ts = td.time_series(
            symbol=symbol,
            interval=interval,
            outputsize=outputsize,
            timezone="UTC"
        )
        df = ts.as_pandas()

        if df.empty or len(df) < 2:
            raise ValueError("No data returned or insufficient candles.")
        
        df.rename(columns={
            'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'
        }, inplace=True)
        df.index.name = "Datetime"
        return df, interval.upper()

    except Exception as e:
        raise RuntimeError(f"Twelve Data API fetch failed for {symbol} @ {interval}: {e}")
