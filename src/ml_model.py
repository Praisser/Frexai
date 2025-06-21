import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from ta.momentum import RSIIndicator
from ta.trend import MACD
from ta.volatility import AverageTrueRange

MODEL_PATH = "models/forex_model.pkl"

def extract_features(df, support_levels, resistance_levels):
    df = df.copy()
    rsi = RSIIndicator(df['Close']).rsi()
    macd = MACD(df['Close'])
    df['rsi'] = rsi
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['ma_diff'] = df['Close'].rolling(5).mean() - df['Close'].rolling(20).mean()
    df['candle_body'] = abs(df['Close'] - df['Open'])
    df['upper_shadow'] = df['High'] - df[['Close', 'Open']].max(axis=1)
    df['lower_shadow'] = df[['Close', 'Open']].min(axis=1) - df['Low']
    df['atr'] = AverageTrueRange(df['High'], df['Low'], df['Close']).average_true_range()

    sr_prices = [s['price'] for s in support_levels + resistance_levels]
    df['dist_to_nearest_sr'] = df['Close'].apply(lambda x: min([abs(x - sr) for sr in sr_prices]) if sr_prices else 0)
    df = df.dropna()
    return df

def label_data(df):
    df = df.copy()
    future_return = df['Close'].shift(-3) - df['Close']
    df['label'] = np.select(
        [future_return > 0.001, future_return < -0.001],
        ['Buy', 'Sell'],
        default='Wait'
    )
    return df

def train_model(df, support_levels, resistance_levels):
    df = extract_features(df, support_levels, resistance_levels)
    df = label_data(df)

    feature_cols = ['rsi', 'macd', 'macd_signal', 'ma_diff', 'candle_body',
                    'upper_shadow', 'lower_shadow', 'atr', 'dist_to_nearest_sr']

    if len(df) < 100 or df['label'].nunique() < 2:
        raise ValueError("❌ Not enough data to train model or labels are not diverse.")

    X = df[feature_cols]
    y = df['label']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

    model = GradientBoostingClassifier()
    model.fit(X_train, y_train)

    # Save only if model has learned
    if hasattr(model, "feature_importances_"):
        os.makedirs("models", exist_ok=True)
        joblib.dump(model, MODEL_PATH)

    return model

def predict_signal(df, support_levels, resistance_levels):
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError("❌ Trained model not found. Train it first from the GUI.")

    model = joblib.load(MODEL_PATH)
    df = extract_features(df, support_levels, resistance_levels)

    if df.empty:
        raise ValueError("❌ No data to predict.")

    latest = df.iloc[-1:]
    features = ['rsi', 'macd', 'macd_signal', 'ma_diff', 'candle_body',
                'upper_shadow', 'lower_shadow', 'atr', 'dist_to_nearest_sr']
    
    pred = model.predict(latest[features])[0]
    prob = model.predict_proba(latest[features]).max()

    return pred, round(prob * 100, 2)
