from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


META_FEATURES = (
    "trend_target",
    "sr_target",
    "orderflow_target",
    "volatility_regime",
    "risk_target",
)


@dataclass(frozen=True)
class MetaDecisionRule:
    high_volatility_cutoff: int = 2


def create_meta_target(df: pd.DataFrame, rule: MetaDecisionRule | None = None) -> pd.Series:
    cfg = rule or MetaDecisionRule()
    target = pd.Series(1, index=df.index, name="meta_target", dtype=int)
    if "risk_target" in df.columns:
        target.loc[df["risk_target"] == 0] = 0
    if "volatility_regime" in df.columns:
        target.loc[df["volatility_regime"] >= cfg.high_volatility_cutoff] = 0
    if "orderflow_target" in df.columns:
        target.loc[df["orderflow_target"] == 0] = 0
    return target


def build_meta_dataset(df: pd.DataFrame, feature_cols: tuple[str, ...] = META_FEATURES) -> pd.DataFrame:
    dataset = df.copy()
    for col in feature_cols:
        if col not in dataset.columns:
            dataset[col] = 0
    dataset["meta_target"] = create_meta_target(dataset)
    return dataset[list(feature_cols) + ["meta_target"]].replace([np.inf, -np.inf], np.nan).dropna()


def train_meta_decision_model(dataset: pd.DataFrame) -> dict[str, Any]:
    import lightgbm as lgb
    from sklearn.metrics import accuracy_score, f1_score
    from sklearn.model_selection import train_test_split

    X = dataset.drop(columns=["meta_target"])
    y = dataset["meta_target"].astype(int)
    stratify = y if y.nunique() > 1 and y.value_counts().min() >= 2 else None
    X_train, X_val, y_train, y_val = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=stratify,
    )
    model = lgb.LGBMClassifier(
        objective="binary",
        n_estimators=400,
        learning_rate=0.05,
        max_depth=4,
        subsample=0.9,
        colsample_bytree=0.9,
        class_weight="balanced",
        random_state=42,
        verbose=-1,
    )
    model.fit(X_train, y_train)
    pred = model.predict(X_val)
    return {
        "model": model,
        "feature_columns": X.columns.tolist(),
        "metrics": {
            "accuracy": float(accuracy_score(y_val, pred)),
            "f1_macro": float(f1_score(y_val, pred, average="macro")),
            "train_samples": int(len(X_train)),
            "test_samples": int(len(X_val)),
        },
    }

