from __future__ import annotations

from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score
from sklearn.preprocessing import StandardScaler

from .features import build_feature_matrix, create_multiclass_target, select_numeric_features
from .model_registry import ModelMetadata, ModelRegistry
from .specialists import build_specialist_features
from .training import _probability_thresholds, _temporal_train_test


def _infer_symbol_timeframe_from_shard(path: Path) -> tuple[list[str], list[str]]:
    name = path.stem.upper()
    timeframe = []
    for tf in ("M5", "M15", "M30", "H1", "H4", "D1"):
        if f"_{tf}" in name or name.endswith(tf):
            timeframe.append(tf)
    return [name], timeframe or ["UNKNOWN"]


def train_shard_experts(
    shards_dir: str | Path,
    output_root: str | Path = "models_refatorado/experts",
    pattern: str = "SHARD_*.parquet",
    min_rows: int = 1000,
    target_col: str | None = None,
    threshold: float = 0.0001,
    include_specialists: bool = True,
) -> pd.DataFrame:
    """Train one LightGBM expert per shard parquet, inspired by BUILD_MODELS."""
    shards_dir = Path(shards_dir)
    registry = ModelRegistry(output_root)
    results: list[dict[str, Any]] = []

    for shard_path in sorted(shards_dir.glob(pattern)):
        df = pd.read_parquet(shard_path)
        if len(df) < min_rows:
            results.append({"shard": shard_path.name, "status": "skipped_insufficient_rows", "rows": len(df)})
            continue

        source_cols = set(df.columns)
        if {"open", "high", "low", "close"}.issubset(source_cols):
            X = build_feature_matrix(df)
            if include_specialists:
                specialist_features = build_specialist_features(df)
                X = pd.concat([X, specialist_features], axis=1)
                X = X.loc[:, ~X.columns.duplicated()]
            if target_col and target_col in df.columns:
                target = df[target_col]
            else:
                target = create_multiclass_target(df, horizon=1, threshold=threshold)
            common_idx = X.index.intersection(target.dropna().index)
            X = X.loc[common_idx]
            y = target.loc[common_idx]
        else:
            label_source = target_col or ("target_label" if "target_label" in df.columns else None)
            if label_source is None or label_source not in df.columns:
                results.append({"shard": shard_path.name, "status": "skipped_no_ohlcv_or_target", "rows": len(df)})
                continue
            y = pd.Series(0, index=df.index, name="target")
            y[df[label_source] > threshold] = 1
            y[df[label_source] < -threshold] = 2
            X = df.drop(columns=[label_source], errors="ignore")

        feature_cols = select_numeric_features(X, exclude=["target", "target_label", "label"])
        X = X[feature_cols].replace([np.inf, -np.inf], np.nan).dropna()
        y = y.loc[X.index]
        if len(X) < min_rows:
            results.append({"shard": shard_path.name, "status": "skipped_after_cleaning", "rows": len(X)})
            continue

        X_train, X_test, y_train, y_test = _temporal_train_test(X, y)
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        model = lgb.LGBMClassifier(
            objective="multiclass",
            class_weight="balanced",
            n_estimators=1000,
            learning_rate=0.03,
            num_leaves=63,
            max_depth=10,
            min_child_samples=30,
            subsample=0.8,
            colsample_bytree=0.8,
            importance_type="gain",
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
        symbols, timeframes = _infer_symbol_timeframe_from_shard(shard_path)
        metadata = ModelMetadata(
            name=shard_path.stem,
            model_type="shard_expert",
            symbols=symbols,
            timeframes=timeframes,
            feature_columns=feature_cols,
            buy_threshold=buy_threshold,
            sell_threshold=sell_threshold,
            metrics=metrics,
            source=str(shard_path),
        )
        model_dir = registry.save(model, scaler, metadata, shard_path.stem)
        results.append({"shard": shard_path.name, "status": "trained", "model_dir": str(model_dir), **metrics})

    return pd.DataFrame(results)
