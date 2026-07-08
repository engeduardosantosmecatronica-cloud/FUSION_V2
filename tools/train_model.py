"""
FUSION_V2 - Training Script
============================
Treina modelos específicos por ATIVO e TIMEFRAME
Timeframes: M5, M15, M30, H1, H4, D1
Inspirado em BUILD_MODELS + ALPHAEDU
"""

import sys
from pathlib import Path
project_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(project_dir))

import numpy as np
import pandas as pd
import joblib
import lightgbm as lgb
from sklearn.preprocessing import StandardScaler
from datetime import datetime
from typing import Dict, Tuple

from fusion.core.logger import get_logger
from fusion.features.engine import AlphaMiner, RSI, EMA


SYMBOLS = [
    #"EURUSD", "GBPUSD", "USDJPY", "GBPJPY", "AUDUSD", "USDCAD", "USDCHF",
    #"XAUUSD", "XAGUSD", "EURGBP", "EURJPY", "NZDUSD"
    "EURCHF", "AUDCAD", "AUDCHF", "EURCAD", "GBPCHF", "AUDJPY", "CADCHF", 
    "EURAUD", "GBPAUD", "NZDCAD", "AUDNZD", "CADCHF", "CHFJPY", "EURNZD"
]

TIMEFRAMES = ["M5", "M15", "M30", "H1", "H4", "D1"]

TF_MAP = {
    "M5": 5, "M15": 15, "M30": 30,
    "H1": 60, "H4": 240, "D1": 1440
}


def get_mt5_rates(symbol: str, tf_minutes: int, count: int = 5000):
    """Busca dados do MT5."""
    try:
        import MetaTrader5 as mt5
        tf_map = {
            5: mt5.TIMEFRAME_M5, 15: mt5.TIMEFRAME_M15, 30: mt5.TIMEFRAME_M30,
            60: mt5.TIMEFRAME_H1, 240: mt5.TIMEFRAME_H4, 1440: mt5.TIMEFRAME_D1
        }
        tf_code = tf_map.get(tf_minutes, mt5.TIMEFRAME_M5)
        rates = mt5.copy_rates_from_pos(symbol, tf_code, 0, count)
        if rates is None:
            return None
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        return df
    except Exception as e:
        return None


def calculate_features(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula features para um dataframe."""
    if len(df) < 100:
        return pd.DataFrame()
    
    features = pd.DataFrame(index=df.index)
    
    close = df['close']
    high = df['high']
    low = df['low']
    open_col = df['open']
    
    ret = np.log(close / close.shift(1))
    features['ret'] = ret
    features['ret_5'] = ret.rolling(5).sum()
    features['ret_10'] = ret.rolling(10).sum()
    features['ret_20'] = ret.rolling(20).sum()
    
    rsi14 = RSI.calculate(df, 14)
    rsi28 = RSI.calculate(df, 28)
    features['rsi14'] = rsi14
    features['rsi28'] = rsi28
    features['rsi_diff'] = rsi14 - rsi28
    features['rsi_ma5'] = rsi14.rolling(5).mean()
    features['rsi_gap'] = rsi14 - rsi14.rolling(10).mean()
    
    ema8 = EMA.calculate(df, 8)
    ema21 = EMA.calculate(df, 21)
    ema50 = EMA.calculate(df, 50)
    ema200 = EMA.calculate(df, 200)
    
    features['ema8'] = ema8
    features['ema21'] = ema21
    features['ema50'] = ema50
    features['ema200'] = ema200
    
    features['dist_ema8'] = (close / ema8) - 1
    features['dist_ema21'] = (close / ema21) - 1
    features['dist_ema50'] = (close / ema50) - 1
    features['dist_ema200'] = (close / ema200) - 1
    
    range_pct = (high - low) / close
    features['range_pct'] = range_pct
    features['range_ma10'] = range_pct.rolling(10).mean()
    
    features['high_20'] = high.rolling(20).max()
    features['low_20'] = low.rolling(20).min()
    features['position_in_range'] = (close - features['low_20']) / (features['high_20'] - features['low_20'] + 1e-9)
    
    vol5 = ret.rolling(5).std()
    vol20 = ret.rolling(20).std()
    features['vol5'] = vol5
    features['vol20'] = vol20
    features['vol_ratio'] = vol5 / (vol20 + 1e-9)
    
    ema_fast = close.ewm(span=12).mean()
    ema_slow = close.ewm(span=26).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=9).mean()
    features['macd'] = macd_line
    features['macd_signal'] = signal_line
    features['macd_hist'] = macd_line - signal_line
    
    features['upper_bb'] = ema21 + (ret.rolling(20).std() * 2)
    features['lower_bb'] = ema21 - (ret.rolling(20).std() * 2)
    features['bb_width'] = features['upper_bb'] - features['lower_bb']
    
    features['alpha_vam'] = AlphaMiner.vam(df, 20)
    features['alpha_effort'] = AlphaMiner.effort(df, 50)
    features['alpha_mrs'] = AlphaMiner.mrs(df, 20)
    features['alpha_rsi_gap'] = AlphaMiner.rsi_gap(df, 14)
    
    trend_alignment = (rsi14 > 50).astype(int)
    for period in [5, 10, 20]:
        ma_trend = (close > EMA.calculate(df, period)).astype(int)
        trend_alignment = trend_alignment + ma_trend
    features['trend_alignment'] = trend_alignment
    
    return features.dropna()


def create_target(df: pd.DataFrame, horizon: int = 12, threshold: float = 0.0008) -> pd.Series:
    """Cria target: 1=buy, 2=sell, 0=hold."""
    future_ret = np.log(df['close'].shift(-horizon) / df['close'])
    
    target = pd.Series(0, index=df.index)
    target[future_ret > threshold] = 1
    target[future_ret < -threshold] = 2
    
    return target


def train_single_model(X: pd.DataFrame, y: pd.Series, symbol: str, tf: str) -> Tuple:
    """Treina modelo para um símbolo/timeframe."""
    if len(X) < 500:
        return None, None, None, 0
    
    n = len(X)
    train_size = int(n * 0.8)
    
    X_train, X_test = X.iloc[:train_size], X.iloc[train_size:]
    y_train, y_test = y.iloc[:train_size], y.iloc[train_size:]
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train.values)
    X_test_scaled = scaler.transform(X_test.values)
    
    model = lgb.LGBMClassifier(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=5,
        num_leaves=20,
        min_child_samples=30,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.2,
        reg_lambda=0.2,
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )
    
    model.fit(
        X_train_scaled, y_train,
        eval_set=[(X_test_scaled, y_test)],
        callbacks=[lgb.early_stopping(30, verbose=False)]
    )
    
    y_pred = model.predict(X_test_scaled)
    accuracy = float((y_pred == y_test.values).mean())
    
    probs = model.predict_proba(X_train_scaled)
    
    buy_probs = []
    sell_probs = []
    for i, cls in enumerate(model.classes_):
        if cls == 1:
            buy_probs = probs[y_train.values == cls, i].tolist()
        elif cls == 2:
            sell_probs = probs[y_train.values == cls, i].tolist()
    
    buy_thresh = float(np.percentile(buy_probs, 75)) if buy_probs else 0.55
    sell_thresh = float(np.percentile(sell_probs, 75)) if sell_probs else 0.55
    
    return model, scaler, accuracy, buy_thresh, sell_thresh


def save_models(models_dict: Dict, output_dir: Path):
    """Salva todos os modelos."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for key, data in models_dict.items():
        symbol, tf = key
        model_dir = output_dir / symbol / tf
        model_dir.mkdir(parents=True, exist_ok=True)
        
        model_path = model_dir / "model.pkl"
        scaler_path = model_dir / "scaler.pkl"
        meta_path = model_dir / "meta.pkl"
        
        joblib.dump(data['model'], model_path)
        joblib.dump(data['scaler'], scaler_path)
        joblib.dump(data['meta'], meta_path)
    
    master_index = []
    for key, data in models_dict.items():
        master_index.append({
            'symbol': key[0],
            'timeframe': key[1],
            'accuracy': data['meta']['accuracy'],
            'buy_threshold': data['meta']['buy_threshold'],
            'sell_threshold': data['meta']['sell_threshold'],
            'train_samples': data['meta']['train_samples'],
        })
    
    pd.DataFrame(master_index).to_csv(output_dir / "models_index.csv", index=False)


def main():
    logger = get_logger("Trainer")
    logger.info("=" * 60)
    logger.info("FUSION_V2 - TREINAMENTO POR ATIVO/TIMEFRAME")
    logger.info("=" * 60)
    
    try:
        import MetaTrader5 as mt5
        if not mt5.initialize():
            logger.error("Falha ao inicializar MT5")
            return
        
        acc = mt5.account_info()
        logger.info(f"MT5 Conectado | Conta: {acc.login}")
    except Exception as e:
        logger.error(f"Erro MT5: {e}")
        return
    
    output_dir = project_dir / "models"
    
    broker_symbols = {s.name.upper(): s.name for s in mt5.symbols_get()}
    
    models_trained = 0
    models_dict = {}
    
    for sym_ia in SYMBOLS:
        sym_upper = sym_ia.upper()
        
        real_name = None
        if sym_upper in broker_symbols:
            real_name = broker_symbols[sym_upper]
        elif sym_upper == "XAUUSD":
            for name in broker_symbols:
                if "XAUUSD" in name or ("GOLD" in name.upper()):
                    real_name = broker_symbols[name]
                    break
        
        if not real_name:
            logger.warning(f"Símbolo não encontrado no broker: {sym_ia}")
            continue
        
        mt5.symbol_select(real_name, True)
        logger.info(f"\n{'='*50}")
        logger.info(f"TREINANDO: {sym_ia} ({real_name})")
        logger.info(f"{'='*50}")
        
        for tf_name in TIMEFRAMES:
            tf_min = TF_MAP[tf_name]
            logger.info(f"  Processando {tf_name}...", )
            
            df = get_mt5_rates(real_name, tf_min, count=5000)
            if df is None or len(df) < 500:
                logger.info(" SEM DADOS")
                continue
            
            features = calculate_features(df)
            target = create_target(df, horizon=tf_min)
            
            common_idx = features.dropna().index.intersection(target.dropna().index)
            X = features.loc[common_idx]
            y = target.loc[common_idx]
            
            if len(X) < 500:
                logger.info(f" DADOS INSUFICIENTES ({len(X)})")
                continue
            
            model, scaler, accuracy, buy_thresh, sell_thresh = train_single_model(X, y, sym_ia, tf_name)
            
            if model is None:
                logger.info(" FALHA NO TREINO")
                continue
            
            logger.info(f" OK | Acc: {accuracy:.3f} | BUY: {buy_thresh:.2f} | SELL: {sell_thresh:.2f}")
            
            meta = {
                'symbol': sym_ia,
                'timeframe': tf_name,
                'accuracy': accuracy,
                'buy_threshold': buy_thresh,
                'sell_threshold': sell_thresh,
                'feature_columns': X.columns.tolist(),
                'training_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'train_samples': int(len(X) * 0.8),
                'test_samples': int(len(X) * 0.2),
            }
            
            models_dict[(sym_ia, tf_name)] = {
                'model': model,
                'scaler': scaler,
                'meta': meta
            }
            models_trained += 1
    
    mt5.shutdown()
    
    if models_dict:
        save_models(models_dict, output_dir)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"TREINAMENTO CONCLUÍDO!")
    logger.info(f"Modelos salvos: {models_trained}")
    logger.info(f"Diretório: {output_dir}")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    main()