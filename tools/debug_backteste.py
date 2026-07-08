"""
BACKTESTE DEBUG - Entender o que está acontecendo
"""

import pandas as pd
import numpy as np
from pathlib import Path
import joblib

# Carregar dados EURUSD M5
print("Carregando dados...")
data = pd.read_parquet("data/parquet/M5/EURUSD.parquet")
if 'date' in data.columns:
    data['date'] = pd.to_datetime(data['date'])
    data.set_index('date', inplace=True)

# Últimos 1 ano
cutoff_date = pd.Timestamp.now() - pd.Timedelta(days=365)
data = data[data.index >= cutoff_date].copy()

print(f"Total de candles: {len(data)}")
print(f"Colunas: {data.columns.tolist()}\n")

# Calcular EMAs
data['ema_9'] = data['close'].ewm(span=9).mean()
data['ema_21'] = data['close'].ewm(span=21).mean()
data['ema_50'] = data['close'].ewm(span=50).mean()

# Carregar modelo
print("Carregando modelo...")
model = joblib.load("models_expr/EURUSD/M5/model.pkl")
scaler = joblib.load("models_expr/EURUSD/M5/scaler.pkl")
meta = joblib.load("models_expr/EURUSD/M5/meta.pkl")
feature_cols = meta.get('feature_columns', [])
print(f"Features do modelo: {feature_cols[:5]}... (total: {len(feature_cols)})\n")

# Teste 1: Quantos sinais BUY o modelo gera?
print("="*80)
print("TESTE 1: Sinais BUY do modelo")
print("="*80)

buy_signals = []
for idx in range(100, min(1000, len(data))):  # Primeiros 900 candles
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
                p_buy = float(probs[0, i])
                if p_buy > 0.55:
                    buy_signals.append((idx, p_buy))
                    print(f"  Candle {idx}: BUY signal (p_buy={p_buy:.4f})")
    except:
        pass

print(f"\nTotal de sinais BUY: {len(buy_signals)}\n")

# Teste 2: Para esses sinais, quantos passam na verificação de alinhamento de médias?
print("="*80)
print("TESTE 2: Alinhamento de médias (9 > 21 > 50)")
print("="*80)

aligned_signals = []
for idx, p_buy in buy_signals:
    ema9 = data['ema_9'].iloc[idx]
    ema21 = data['ema_21'].iloc[idx]
    ema50 = data['ema_50'].iloc[idx]
    
    is_aligned = (ema9 > ema21) and (ema21 > ema50)
    
    print(f"  Candle {idx}: ema9={ema9:.5f}, ema21={ema21:.5f}, ema50={ema50:.5f} -> {'✓' if is_aligned else '✗'}")
    
    if is_aligned:
        aligned_signals.append(idx)

print(f"\nTotal com alinhamento: {len(aligned_signals)}\n")

# Teste 3: Candle anterior é de alta ou baixa?
print("="*80)
print("TESTE 3: Candle anterior de alta ou baixa")
print("="*80)

valid_candles = []
for idx in aligned_signals:
    is_high = data['close'].iloc[idx-1] > data['open'].iloc[idx-1]
    is_low = data['close'].iloc[idx-1] < data['open'].iloc[idx-1]
    
    print(f"  Candle {idx}: anterior {'HIGH' if is_high else 'LOW' if is_low else 'DOJI'} -> {'✓' if (is_high or is_low) else '✗'}")
    
    if is_high or is_low:
        valid_candles.append(idx)

print(f"\nTotal com candle anterior válido: {len(valid_candles)}\n")

# Teste 4: Preço entrou acima do candle anterior?
print("="*80)
print("TESTE 4: Entrada acima do candle anterior")
print("="*80)

final_entries = []
for idx in valid_candles:
    prev_high = data['high'].iloc[idx-1]
    prev_low = data['low'].iloc[idx-1]
    prev_open = data['open'].iloc[idx-1]
    prev_close = data['close'].iloc[idx-1]
    curr_high = data['high'].iloc[idx]
    
    max_prev = max(prev_high, prev_low, prev_open, prev_close)
    can_enter = curr_high > max_prev
    
    print(f"  Candle {idx}: curr_high={curr_high:.5f} > max_prev={max_prev:.5f} -> {'✓' if can_enter else '✗'}")
    
    if can_enter:
        final_entries.append(idx)

print(f"\nTotal de entradas válidas: {len(final_entries)}\n")
