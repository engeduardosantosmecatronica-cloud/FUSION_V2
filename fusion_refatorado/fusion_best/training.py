from __future__ import annotations

from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score
from sklearn.preprocessing import StandardScaler

from .dataset_builder import normalize_ohlcv_columns
from .features import build_feature_matrix, create_multiclass_target, select_numeric_features
from .model_registry import ModelMetadata, ModelRegistry
from .specialists import build_specialist_features


def _temporal_train_test(X: pd.DataFrame, y: pd.Series, test_size: float = 0.2):
    split = int(len(X) * (1 - test_size))
    return X.iloc[:split], X.iloc[split:], y.iloc[:split], y.iloc[split:]


def _probability_thresholds(model: Any, X_scaled: np.ndarray, y: pd.Series) -> tuple[float, float]:
    probs = model.predict_proba(X_scaled)
    buy_probs: list[float] = []
    sell_probs: list[float] = []
    for i, cls in enumerate(model.classes_):
        if cls == 1:
            buy_probs = probs[y.values == cls, i].tolist()
        elif cls == 2:
            sell_probs = probs[y.values == cls, i].tolist()
    buy = float(np.percentile(buy_probs, 75)) if buy_probs else 0.55
    sell = float(np.percentile(sell_probs, 75)) if sell_probs else 0.55
    return buy, sell


def train_single_symbol_timeframe(
    parquet_path: str | Path,
    symbol: str,
    timeframe: str,
    output_root: str | Path = "models_refatorado",
    horizon: int = 12,
    threshold: float = 0.0008,
    min_rows: int = 500,
    include_specialists: bool = True,
) -> dict[str, Any]:
    """Train one LightGBM model for a single symbol/timeframe parquet."""
    parquet_path = Path(parquet_path)
    if parquet_path.suffix.lower() == ".parquet":
        df = pd.read_parquet(parquet_path)
    else:
        df = pd.read_csv(parquet_path, sep=None, engine="python")
    df = normalize_ohlcv_columns(df)

    features = build_feature_matrix(df)
    if include_specialists:
        specialist_features = build_specialist_features(df)
        features = pd.concat([features, specialist_features], axis=1)
        features = features.loc[:, ~features.columns.duplicated()]
    target = create_multiclass_target(df, horizon=horizon, threshold=threshold)
    common_idx = features.index.intersection(target.dropna().index)
    X = features.loc[common_idx]
    y = target.loc[common_idx]

    feature_cols = select_numeric_features(X)
    X = X[feature_cols].dropna()
    y = y.loc[X.index]
    if len(X) < min_rows:
        raise ValueError(f"Dados insuficientes para treino: {len(X)} linhas.")

    X_train, X_test, y_train, y_test = _temporal_train_test(X, y)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = lgb.LGBMClassifier(
        objective="multiclass",
        class_weight="balanced",
        n_estimators=500,
        learning_rate=0.05,
        max_depth=6,
        num_leaves=31,
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
        callbacks=[lgb.early_stopping(50, verbose=False)],
    )

    pred = model.predict(X_test_scaled)
    metrics = {
        "accuracy": float(accuracy_score(y_test, pred)),
        "f1_macro": float(f1_score(y_test, pred, average="macro")),
        "train_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "features": int(len(feature_cols)),
    }
    buy_threshold, sell_threshold = _probability_thresholds(model, X_train_scaled, y_train)

    registry = ModelRegistry(output_root)
    metadata = ModelMetadata(
        name=f"{symbol}_{timeframe}",
        model_type="single_symbol_timeframe",
        symbols=[symbol],
        timeframes=[timeframe],
        feature_columns=feature_cols,
        buy_threshold=buy_threshold,
        sell_threshold=sell_threshold,
        metrics=metrics,
        source=str(parquet_path),
    )
    model_dir = registry.save(model, scaler, metadata, Path(symbol) / timeframe)
    return {"model_dir": str(model_dir), "metrics": metrics}


def create_genesis_labels_auto(y_reg: pd.Series, lower_pct: float = 33, upper_pct: float = 66) -> pd.Series:
    y_clean = y_reg.replace([np.inf, -np.inf], np.nan).dropna()
    lower_threshold = np.percentile(y_clean, lower_pct)
    upper_threshold = np.percentile(y_clean, upper_pct)
    labels = np.where(y_reg > upper_threshold, 1, np.where(y_reg < lower_threshold, 2, 0))
    return pd.Series(labels, index=y_reg.index, name="genesis_label")


def prepare_genesis_mtf_dataset(
    frame: pd.DataFrame,
    label_col: str = "target_label",
    shift_safety: int = 4,
    keep_price_rsi: bool = True,
) -> tuple[pd.DataFrame, pd.Series]:
    df = frame.copy()
    if "date" in df.columns and "symbol" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index(["date", "symbol"]).sort_index()
    if label_col not in df.columns:
        raise ValueError(f"Coluna alvo ausente: {label_col}")
    y_reg = df[label_col].copy()
    X = df.drop(columns=[label_col])
    if isinstance(X.index, pd.MultiIndex) and "symbol" in X.index.names:
        X = X.groupby(level="symbol").shift(shift_safety)
    else:
        X = X.shift(shift_safety)
    valid_idx = X.dropna().index.intersection(y_reg.dropna().index)
    X = X.loc[valid_idx]
    y_reg = y_reg.loc[valid_idx]
    if keep_price_rsi:
        columns = [
            col
            for col in X.columns
            if not any(token in str(col).lower() for token in ("open", "high", "low", "close")) or "rsi" in str(col).lower()
        ]
        X = X[columns]
    return X.select_dtypes(include=[np.number]), y_reg


def genesis_signals_from_probabilities(
    probs: np.ndarray,
    buy_threshold: float = 0.60,
    sell_threshold: float = 0.60,
) -> np.ndarray:
    signals = np.zeros(len(probs), dtype=int)
    if probs.shape[1] < 3:
        return signals
    p_buy = probs[:, 1]
    p_sell = probs[:, 2]
    signals[p_buy > buy_threshold] = 1
    signals[(signals == 0) & (p_sell > sell_threshold)] = 2
    return signals


def summarize_genesis_returns(active_index: pd.Index, realized_returns: np.ndarray) -> dict[str, float | int]:
    eval_df = pd.DataFrame({"realized": realized_returns}, index=active_index)
    if isinstance(eval_df.index, pd.MultiIndex) and "date" in eval_df.index.names:
        bar_returns = eval_df.groupby(level="date")["realized"].mean()
    else:
        bar_returns = eval_df["realized"]
    equity_curve = (1 + bar_returns).cumprod()
    return {
        "signals": int(len(eval_df)),
        "bars": int(len(bar_returns)),
        "win_rate": float((eval_df["realized"] > 0).mean()) if len(eval_df) else 0.0,
        "avg_trade": float(eval_df["realized"].mean()) if len(eval_df) else 0.0,
        "gross_profit_pct": float((equity_curve.iloc[-1] - 1) * 100) if len(equity_curve) else 0.0,
    }


def robust_scale_features(frame: pd.DataFrame, exclude: tuple[str, ...] = ("date", "symbol", "target_label")) -> tuple[pd.DataFrame, Any]:
    from sklearn.preprocessing import RobustScaler

    df = frame.copy()
    feature_cols = [col for col in df.columns if col not in exclude and pd.api.types.is_numeric_dtype(df[col])]
    scaler = RobustScaler()
    df[feature_cols] = scaler.fit_transform(df[feature_cols])
    constant_cols = [col for col in feature_cols if df[col].nunique(dropna=False) <= 1]
    if constant_cols:
        df = df.drop(columns=constant_cols)
    return df, scaler


def clean_fusion_regression_frame(df: pd.DataFrame, target_col: str = "target_ret", max_nan_fraction: float = 0.30) -> tuple[pd.DataFrame, pd.Series, list[str]]:
    data = df.replace([np.inf, -np.inf], np.nan).copy()
    if "date" in data.columns:
        data["date"] = pd.to_datetime(data["date"])
        data = data.sort_values("date").reset_index(drop=True)
    if target_col not in data.columns:
        raise ValueError(f"Coluna alvo ausente: {target_col}")
    feature_cols = [col for col in data.columns if col not in ("date", "symbol", target_col) and pd.api.types.is_numeric_dtype(data[col])]
    feature_cols = [col for col in feature_cols if data[col].notna().mean() >= (1 - max_nan_fraction)]
    feature_cols = [col for col in feature_cols if data[col].std(skipna=True) > 0]
    y = data[target_col].fillna(0)
    X = data[feature_cols].fillna(data[feature_cols].median())
    return X, y, feature_cols


def train_regression_model_zoo(X: pd.DataFrame, y: pd.Series, train_ratio: float = 0.70, val_ratio: float = 0.15) -> dict[str, Any]:
    from scipy.stats import spearmanr
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
    from sklearn.linear_model import Ridge
    from sklearn.metrics import mean_squared_error, r2_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    n = len(X)
    train_size = int(n * train_ratio)
    val_size = int(n * val_ratio)
    X_train, y_train = X.iloc[:train_size], y.iloc[:train_size]
    X_test, y_test = X.iloc[train_size + val_size :], y.iloc[train_size + val_size :]
    models = {
        "ridge": Pipeline([("scaler", StandardScaler()), ("reg", Ridge(alpha=10.0))]),
        "gbr": Pipeline([("scaler", StandardScaler()), ("reg", GradientBoostingRegressor(n_estimators=150, max_depth=5, learning_rate=0.05, subsample=0.8, random_state=42))]),
        "rf": Pipeline([("scaler", StandardScaler()), ("reg", RandomForestRegressor(n_estimators=100, max_depth=8, n_jobs=-1, random_state=42))]),
    }
    results = {}
    best_name = ""
    best_ic = -float("inf")
    best_model = None
    for name, model in models.items():
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        ic, _ = spearmanr(y_test, pred)
        results[name] = {"r2": float(r2_score(y_test, pred)), "ic": float(ic), "rmse": float(np.sqrt(mean_squared_error(y_test, pred)))}
        if ic > best_ic:
            best_name, best_ic, best_model = name, float(ic), model
    return {"best_name": best_name, "best_ic": best_ic, "best_model": best_model, "metrics": results}


def train_omnis_elite_random_forest(
    df: pd.DataFrame,
    test_size: float = 0.15,
    confidence_threshold: float = 0.55,
    random_state: int = 42,
) -> dict[str, Any]:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

    from .qlib_integration import build_omnis_elite_alphas

    data = build_omnis_elite_alphas(df, horizon=1)
    data["target"] = (data["close"].shift(-1) > data["close"]).astype(int)
    features = ["roc_5", "rsv_20", "j_indicator", "persistence"]
    data = data.dropna(subset=features + ["target"])
    split_idx = int(len(data) * (1 - test_size))
    X_train = data[features].iloc[:split_idx]
    y_train = data["target"].iloc[:split_idx]
    X_test = data[features].iloc[split_idx:]
    y_test = data["target"].iloc[split_idx:]

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=6,
        min_samples_leaf=50,
        random_state=random_state,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    probabilities = model.predict_proba(X_test)
    max_prob = probabilities.max(axis=1) if len(probabilities) else np.array([])
    strong_mask = max_prob >= confidence_threshold
    strong_accuracy = float(accuracy_score(y_test.iloc[strong_mask], y_pred[strong_mask])) if strong_mask.any() else 0.0
    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)) if len(y_test) else 0.0,
        "strong_signal_accuracy": strong_accuracy,
        "strong_signal_count": int(strong_mask.sum()),
        "train_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "features": features,
        "feature_importance": dict(zip(features, model.feature_importances_.astype(float))),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist() if len(y_test) else [],
        "classification_report": classification_report(y_test, y_pred, output_dict=True, zero_division=0) if len(y_test) else {},
    }
    return {"model": model, "metrics": metrics, "feature_columns": features, "confidence_threshold": confidence_threshold}


def create_atr_direction_target(
    df: pd.DataFrame,
    target_col: str = "direction_target",
    horizon: int = 6,
    atr_col: str = "atr",
    threshold_atr: float = 0.30,
    max_hold_fraction: float | None = 0.70,
) -> pd.Series:
    data = df.copy()
    if atr_col not in data.columns:
        high = data["high"]
        low = data["low"]
        close = data["close"]
        true_range = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
        data[atr_col] = true_range.rolling(14).mean()
    future_move = data["close"].shift(-horizon) - data["close"]
    target = pd.Series(0, index=data.index, name=target_col)
    target[future_move > data[atr_col] * threshold_atr] = 1
    target[future_move < -data[atr_col] * threshold_atr] = -1
    if max_hold_fraction is not None and len(target) > 0:
        hold_mask = target == 0
        max_holds = int(len(target) * max_hold_fraction)
        if int(hold_mask.sum()) > max_holds:
            excess = int(hold_mask.sum()) - max_holds
            ranked = future_move.abs().loc[hold_mask].sort_values(ascending=False).head(excess).index
            target.loc[ranked] = np.sign(future_move.loc[ranked]).replace(0, 1).astype(int)
    return target


def create_meta_decision_target(df: pd.DataFrame) -> pd.Series:
    target = pd.Series(1, index=df.index, name="meta_target")
    if "risk_target" in df.columns:
        target[df["risk_target"] == 0] = 0
    if "volatility_regime" in df.columns:
        target[df["volatility_regime"] >= 2] = 0
    if "orderflow_target" in df.columns:
        target[df["orderflow_target"] == 0] = 0
    return target.astype(int)


def train_meta_decision_model(
    df: pd.DataFrame,
    feature_cols: list[str] | None = None,
    test_size: float = 0.20,
    random_state: int = 42,
) -> dict[str, Any]:
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, classification_report

    feature_cols = feature_cols or ["trend_target", "sr_target", "orderflow_target", "volatility_regime", "risk_target"]
    data = df.copy()
    for col in feature_cols:
        if col not in data.columns:
            data[col] = 0
    data["meta_target"] = create_meta_decision_target(data)
    data = data.dropna(subset=feature_cols + ["meta_target"])
    X = data[feature_cols]
    y = data["meta_target"].astype(int)
    stratify = y if y.nunique() > 1 and y.value_counts().min() >= 2 else None
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=test_size, stratify=stratify, random_state=random_state)
    model = lgb.LGBMClassifier(
        objective="binary",
        n_estimators=400,
        learning_rate=0.05,
        max_depth=4,
        subsample=0.9,
        colsample_bytree=0.9,
        class_weight="balanced",
        random_state=random_state,
        verbose=-1,
    )
    model.fit(X_train, y_train)
    pred = np.asarray(model.predict(X_val)).ravel()
    metrics = {
        "accuracy": float(accuracy_score(y_val, pred)),
        "train_samples": int(len(X_train)),
        "test_samples": int(len(X_val)),
        "classification_report": classification_report(y_val, pred, output_dict=True, zero_division=0),
        "feature_columns": feature_cols,
    }
    return {"model": model, "metrics": metrics, "feature_columns": feature_cols}


def prepare_required_feature_frame(df: pd.DataFrame, required_features: list[str]) -> pd.DataFrame:
    prepared = pd.DataFrame(index=df.index)
    for feature in dict.fromkeys(required_features):
        if feature in df.columns:
            prepared[feature] = df[feature]
        elif any(token in feature for token in ("range", "norm", "ratio")):
            prepared[feature] = 1.0
        elif any(token in feature for token in ("volatility", "atr", "std")):
            prepared[feature] = 0.005
        elif "rsi" in feature:
            prepared[feature] = 50.0
        else:
            prepared[feature] = 0.0
    return prepared.reindex(columns=list(dict.fromkeys(required_features))).replace([np.inf, -np.inf], np.nan).fillna(0.0)
