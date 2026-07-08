"""
Debug com features calculadas
"""

import pandas as pd
import numpy as np
import joblib

# Carregar e calcular features
data = pd.read_parquet("data/parquet/M5/EURUSD.parquet")
if 'date' in data.columns:
    data['date'] = pd.to_datetime(data['date'])
    data.set_index('date', inplace=True)

cutoff = pd.Timestamp.now() - pd.Timedelta(days=365)
data = data[data.index >= cutoff].copy()

# Calcular features simples
close = data['close']
data['ret'] = np.log(close / close.shift(1))
data['ret_5'] = data['ret'].rolling(5).sum()
data['ret_10'] = data['ret'].rolling(10).sum()
data['ret_20'] = data['ret'].rolling(20).sum()

data['ema8'] = close.ewm(span=8).mean()
data['ema21'] = close.ewm(span=21).mean()
data['ema50'] = close.ewm(span=50).mean()
data['ema200'] = close.ewm(span=200).mean()

# Carregar modelo
model = joblib.load("models_expr/EURUSD/M5/model.pkl")
scaler = joblib.load("models_expr/EURUSD/M5/scaler.pkl")
meta = joblib.load("models_expr/EURUSD/M5/meta.pkl")
feature_cols = meta.get('feature_columns', [])

print(f"Testando primeiros 1000 candles após índice 200...")
buy_probs = []

for idx in range(200, min(1200, len(data))):
    try:
        row = data.iloc[idx]
        features = []
        skip = False
        
        for col in feature_cols:
            if col not in data.columns:
                skip = True
                break
            val = row[col]
            if pd.isna(val):
                skip = True
                break
            features.append(val)
        
        if skip:
            continue
        
        X = np.array(features).reshape(1, -1)
        X_scaled = scaler.transform(X)
        probs = model.predict_proba(X_scaled)
        
        for i, cls in enumerate(model.classes_):
            if cls == 1:
                p_buy = float(probs[0, i])
                buy_probs.append(p_buy)
                if p_buy > 0.50:
                    print(f"Candle {idx}: p_buy={p_buy:.4f}")
    except Exception as e:
        pass

print(f"\nTotal analisado: {len(buy_probs)}")
if buy_probs:
    print(f"Min: {np.min(buy_probs):.4f}")
    print(f"Max: {np.max(buy_probs):.4f}")
    print(f"Mean: {np.mean(buy_probs):.4f}")
    print(f"\n> 0.50: {sum(1 for p in buy_probs if p > 0.50)}")
    print(f"> 0.55: {sum(1 for p in buy_probs if p > 0.55)}")
    print(f"> 0.40: {sum(1 for p in buy_probs if p > 0.40)}")
else:
    print("Nenhum candle analisado!")
