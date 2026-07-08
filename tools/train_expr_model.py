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
from fusion.features.expressions.definitions import build_expression_features


SYMBOLS = [
    "EURUSD", "GBPUSD", "USDJPY", "GBPJPY", "AUDUSD", "USDCAD", "USDCHF", "EURGBP", "EURJPY", "NZDUSD",
                           "EURCHF", "AUDCAD", "AUDCHF", "EURCAD", "GBPCHF", "AUDJPY", "CADCHF", "EURAUD", "GBPAUD", "NZDCAD", "AUDNZD", "CADCHF", "CHFJPY", "EURNZD" ]

TIMEFRAMES = ["M5", "M15", "M30", "H1", "H4", "D1"]

TF_MAP = {
    "M5": 5, "M15": 15, "M30": 30,
    "H1": 60, "H4": 240, "D1": 1440
}


def get_mt5_rates(symbol: str, tf_minutes: int, count: int = 5000):
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


def create_target(df: pd.DataFrame, horizon: int = 12, threshold: float = 0.0008) -> pd.Series:
    future_ret = np.log(df['close'].shift(-horizon) / df['close'])
    target = pd.Series(0, index=df.index)
    target[future_ret > threshold] = 1
    target[future_ret < -threshold] = 2
    return target


def train_single_model(X: pd.DataFrame, y: pd.Series, symbol: str, tf: str) -> Tuple:
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
    output_dir.mkdir(parents=True, exist_ok=True)

    for key, data in models_dict.items():
        symbol, tf = key
        model_dir = output_dir / symbol / tf
        model_dir.mkdir(parents=True, exist_ok=True)

        joblib.dump(data['model'], model_dir / "model.pkl")
        joblib.dump(data['scaler'], model_dir / "scaler.pkl")
        joblib.dump(data['meta'], model_dir / "meta.pkl")

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
    logger = get_logger("TrainerExpr")
    logger.info("=" * 60)
    logger.info("FUSION_V2 - TREINAMENTO VIA EXPRESSOES (ALPHAEDU)")
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

    output_dir = project_dir / "models_expr"
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
            logger.warning(f"Simbolo nao encontrado no broker: {sym_ia}")
            continue

        mt5.symbol_select(real_name, True)
        logger.info(f"\n{'='*50}")
        logger.info(f"TREINANDO: {sym_ia} ({real_name})")
        logger.info(f"{'='*50}")

        for tf_name in TIMEFRAMES:
            tf_min = TF_MAP[tf_name]
            logger.info(f"  Processando {tf_name}...")

            df = get_mt5_rates(real_name, tf_min, count=5000)
            if df is None or len(df) < 500:
                logger.info(" SEM DADOS")
                continue

            features = build_expression_features(df)
            exclude_cols = {'open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume', 'time'}
            features = features.drop(columns=[c for c in exclude_cols if c in features.columns])

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
    logger.info(f"TREINAMENTO CONCLUIDO!")
    logger.info(f"Modelos salvos: {models_trained}")
    logger.info(f"Diretorio: {output_dir}")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    main()
