from pathlib import Path
from datetime import datetime

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


PROJECT_DIR = Path(__file__).resolve().parent
SYMBOL = "XAUUSD"
TIMEFRAMES = ["M5", "M15", "M30", "H1", "H4", "D1"]
OUTPUT_DIR = PROJECT_DIR / "models_principal"


def rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))


def ema(df: pd.DataFrame, period: int) -> pd.Series:
    return df["close"].ewm(span=period, adjust=False).mean()


def alpha_vam(df: pd.DataFrame, period: int = 20) -> pd.Series:
    ret = np.log(df["close"] / df["close"].shift(1))
    range_pct = (df["high"] - df["low"]) / df["close"]
    return ret.rolling(period).mean() / (range_pct.rolling(period).std() + 1e-9)


def alpha_effort(df: pd.DataFrame, period: int = 50) -> pd.Series:
    range_pct = (df["high"] - df["low"]) / df["close"]
    return range_pct / (range_pct.rolling(period).mean() + 1e-9)


def alpha_mrs(df: pd.DataFrame, period: int = 20) -> pd.Series:
    ema21 = df["close"].ewm(span=21).mean()
    dist_ema = (df["close"] / ema21) - 1
    range_pct = (df["high"] - df["low"]) / df["close"]
    return dist_ema / (range_pct.rolling(period).mean() + 1e-9)


def alpha_rsi_gap(df: pd.DataFrame, period: int = 14) -> pd.Series:
    rsi_value = rsi(df, period)
    return rsi_value - rsi_value.rolling(10).mean()


def load_local_csv(tf: str) -> pd.DataFrame:
    files = sorted((PROJECT_DIR / "data" / "csv" / tf).glob(f"*/*/{SYMBOL}.csv"))
    if not files:
        return pd.DataFrame()

    parts = []
    for file_path in files:
        df = pd.read_csv(file_path)
        parts.append(df)

    df = pd.concat(parts, ignore_index=True).drop_duplicates("date")
    df["time"] = pd.to_datetime(df["date"])
    df = df.sort_values("time").set_index("time")
    keep_cols = ["open", "high", "low", "close", "tick_volume"]
    for col in keep_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df[keep_cols].dropna()


def calculate_features(df: pd.DataFrame) -> pd.DataFrame:
    if len(df) < 250:
        return pd.DataFrame()

    features = pd.DataFrame(index=df.index)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    ret = np.log(close / close.shift(1))
    features["ret"] = ret
    features["ret_5"] = ret.rolling(5).sum()
    features["ret_10"] = ret.rolling(10).sum()
    features["ret_20"] = ret.rolling(20).sum()

    rsi14 = rsi(df, 14)
    rsi28 = rsi(df, 28)
    features["rsi14"] = rsi14
    features["rsi28"] = rsi28
    features["rsi_diff"] = rsi14 - rsi28
    features["rsi_ma5"] = rsi14.rolling(5).mean()
    features["rsi_gap"] = rsi14 - rsi14.rolling(10).mean()

    ema8 = ema(df, 8)
    ema21 = ema(df, 21)
    ema50 = ema(df, 50)
    ema200 = ema(df, 200)
    features["ema8"] = ema8
    features["ema21"] = ema21
    features["ema50"] = ema50
    features["ema200"] = ema200
    features["dist_ema8"] = (close / ema8) - 1
    features["dist_ema21"] = (close / ema21) - 1
    features["dist_ema50"] = (close / ema50) - 1
    features["dist_ema200"] = (close / ema200) - 1

    range_pct = (high - low) / close
    features["range_pct"] = range_pct
    features["range_ma10"] = range_pct.rolling(10).mean()
    features["high_20"] = high.rolling(20).max()
    features["low_20"] = low.rolling(20).min()
    features["position_in_range"] = (close - features["low_20"]) / (features["high_20"] - features["low_20"] + 1e-9)

    vol5 = ret.rolling(5).std()
    vol20 = ret.rolling(20).std()
    features["vol5"] = vol5
    features["vol20"] = vol20
    features["vol_ratio"] = vol5 / (vol20 + 1e-9)

    ema_fast = close.ewm(span=12).mean()
    ema_slow = close.ewm(span=26).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=9).mean()
    features["macd"] = macd_line
    features["macd_signal"] = signal_line
    features["macd_hist"] = macd_line - signal_line

    features["upper_bb"] = ema21 + (ret.rolling(20).std() * 2)
    features["lower_bb"] = ema21 - (ret.rolling(20).std() * 2)
    features["bb_width"] = features["upper_bb"] - features["lower_bb"]
    features["alpha_vam"] = alpha_vam(df, 20)
    features["alpha_effort"] = alpha_effort(df, 50)
    features["alpha_mrs"] = alpha_mrs(df, 20)
    features["alpha_rsi_gap"] = alpha_rsi_gap(df, 14)

    trend_alignment = (rsi14 > 50).astype(int)
    for period in [5, 10, 20]:
        trend_alignment = trend_alignment + (close > ema(df, period)).astype(int)
    features["trend_alignment"] = trend_alignment

    return features.replace([np.inf, -np.inf], np.nan).dropna()


def create_target(df: pd.DataFrame, horizon: int = 12, threshold: float = 0.0008) -> pd.Series:
    future_ret = np.log(df["close"].shift(-horizon) / df["close"])
    target = pd.Series(0, index=df.index)
    target[future_ret > threshold] = 1
    target[future_ret < -threshold] = 2
    return target


def train_single_model(X: pd.DataFrame, y: pd.Series):
    if len(X) < 500:
        return None

    train_size = int(len(X) * 0.8)
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
        X_train_scaled,
        y_train,
        eval_set=[(X_test_scaled, y_test)],
        callbacks=[lgb.early_stopping(30, verbose=False)],
    )

    y_pred = model.predict(X_test_scaled)
    accuracy = float((y_pred == y_test.values).mean())
    probs = model.predict_proba(X_train_scaled)

    buy_probs = []
    sell_probs = []
    for idx, cls in enumerate(model.classes_):
        if cls == 1:
            buy_probs = probs[y_train.values == cls, idx].tolist()
        elif cls == 2:
            sell_probs = probs[y_train.values == cls, idx].tolist()

    buy_thresh = float(np.percentile(buy_probs, 75)) if buy_probs else 0.55
    sell_thresh = float(np.percentile(sell_probs, 75)) if sell_probs else 0.55
    return model, scaler, accuracy, buy_thresh, sell_thresh


def save_model(tf: str, model, scaler, meta: dict):
    model_dir = OUTPUT_DIR / SYMBOL / tf
    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_dir / "model.pkl")
    joblib.dump(scaler, model_dir / "scaler.pkl")
    joblib.dump(meta, model_dir / "meta.pkl")


def main():
    trained = []
    for tf in TIMEFRAMES:
        print(f"Treinando {SYMBOL} {tf}...")
        df = load_local_csv(tf)
        if df.empty or len(df) < 500:
            print(f"  Sem dados suficientes: {len(df)}")
            continue

        features = calculate_features(df)
        target = create_target(df, horizon=12)
        common_idx = features.index.intersection(target.dropna().index)
        X = features.loc[common_idx]
        y = target.loc[common_idx]
        if len(X) < 500:
            print(f"  Features insuficientes: {len(X)}")
            continue

        result = train_single_model(X, y)
        if result is None:
            print("  Falha no treino")
            continue

        model, scaler, accuracy, buy_thresh, sell_thresh = result
        meta = {
            "symbol": SYMBOL,
            "timeframe": tf,
            "accuracy": accuracy,
            "buy_threshold": buy_thresh,
            "sell_threshold": sell_thresh,
            "feature_columns": X.columns.tolist(),
            "training_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "train_samples": int(len(X) * 0.8),
            "test_samples": int(len(X) * 0.2),
            "source": "local_csv",
        }
        save_model(tf, model, scaler, meta)
        trained.append(meta)
        print(f"  OK | acc={accuracy:.3f} buy={buy_thresh:.3f} sell={sell_thresh:.3f} samples={len(X)}")

    if trained:
        index_path = OUTPUT_DIR / SYMBOL / "models_index.csv"
        pd.DataFrame(trained).drop(columns=["feature_columns"]).to_csv(index_path, index=False)
    print(f"Concluido. Modelos treinados: {len(trained)}")


if __name__ == "__main__":
    main()
