"""
Verificar distribuição de probabilidades do modelo
"""

import pandas as pd
import numpy as np
from pathlib import Path
import joblib

# Carregar dados
data = pd.read_parquet("data/parquet/M5/EURUSD.parquet")
if 'date' in data.columns:
    data['date'] = pd.to_datetime(data['date'])
    data.set_index('date', inplace=True)

cutoff_date = pd.Timestamp.now() - pd.Timedelta(days=365)
data = data[data.index >= cutoff_date].copy()

# Carregar modelo
model = joblib.load("models_expr/EURUSD/M5/model.pkl")
scaler = joblib.load("models_expr/EURUSD/M5/scaler.pkl")
meta = joblib.load("models_expr/EURUSD/M5/meta.pkl")
feature_cols = meta.get('feature_columns', [])

print("Analisando probabilidades...")
buy_probs = []
sell_probs = []
neutral_probs = []

for idx in range(100, min(5000, len(data))):
    try:
        row = data.iloc[idx]
        
        features_available = []
        skip = False
        for col in feature_cols:
            if col not in data.columns:
                skip = True
                break
            val = row[col]
            if pd.isna(val):
                skip = True
                break
            features_available.append(val)
        
        if skip or len(features_available) != len(feature_cols):
            continue
        
        X = np.array(features_available).reshape(1, -1)
        X_scaled = scaler.transform(X)
        probs = model.predict_proba(X_scaled)
        
        for i, cls in enumerate(model.classes_):
            if cls == 1:
                buy_probs.append(float(probs[0, i]))
            elif cls == 2:
                sell_probs.append(float(probs[0, i]))
            elif cls == 0:
                neutral_probs.append(float(probs[0, i]))
    except:
        pass

print(f"\nTotal de candles analisados: {len(buy_probs)}")
print(f"\nClasses do modelo: {model.classes_}")

print(f"\nDistribuição de BUY (classe 1):")
print(f"  Min:  {np.min(buy_probs):.4f}")
print(f"  Max:  {np.max(buy_probs):.4f}")
print(f"  Mean: {np.mean(buy_probs):.4f}")
print(f"  Std:  {np.std(buy_probs):.4f}")
print(f"  > 0.50: {sum(1 for p in buy_probs if p > 0.50)}")
print(f"  > 0.55: {sum(1 for p in buy_probs if p > 0.55)}")
print(f"  > 0.60: {sum(1 for p in buy_probs if p > 0.60)}")
print(f"  > 0.70: {sum(1 for p in buy_probs if p > 0.70)}")

print(f"\nDistribuição de SELL (classe 2):")
print(f"  Min:  {np.min(sell_probs):.4f}")
print(f"  Max:  {np.max(sell_probs):.4f}")
print(f"  Mean: {np.mean(sell_probs):.4f}")
print(f"  > 0.50: {sum(1 for p in sell_probs if p > 0.50)}")
print(f"  > 0.55: {sum(1 for p in sell_probs if p > 0.55)}")

print(f"\nDistribuição de NEUTRO (classe 0):")
print(f"  Min:  {np.min(neutral_probs) if neutral_probs else 'N/A':.4f}")
print(f"  Max:  {np.max(neutral_probs) if neutral_probs else 'N/A':.4f}")
print(f"  Mean: {np.mean(neutral_probs) if neutral_probs else 'N/A':.4f}")

# Percentis
print(f"\nPercentis de BUY:")
for p in [50, 75, 90, 95, 99]:
    print(f"  {p}º: {np.percentile(buy_probs, p):.4f}")
