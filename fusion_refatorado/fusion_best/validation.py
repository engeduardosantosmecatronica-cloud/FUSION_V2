from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, log_loss


@dataclass(frozen=True)
class ValidationConfig:
    target_col: str = "target"
    train_ratio: float = 0.8
    drop_cols: tuple[str, ...] = ("date", "time", "symbol", "future_close")
    random_state: int = 42


DEFAULT_GROUP_PREFIXES: dict[str, tuple[str, ...]] = {
    "structure": ("pivot_", "structure_"),
    "volatility": ("vol_", "atr", "bb_", "kc_"),
    "momentum": ("mom_", "momentum_", "roc_", "acc_"),
    "liquidity": ("liq_",),
    "microstructure": ("micro_", "spread_", "tick_", "imbalance"),
    "regime": ("regime_", "market_regime"),
}


def prepare_xy(
    df: pd.DataFrame,
    config: ValidationConfig | None = None,
    feature_cols: Iterable[str] | None = None,
) -> tuple[pd.DataFrame, pd.Series]:
    cfg = config or ValidationConfig()
    if cfg.target_col not in df.columns:
        raise KeyError(f"Target ausente: {cfg.target_col}")
    drop_existing = [c for c in cfg.drop_cols if c in df.columns]
    if feature_cols is None:
        X = df.drop(columns=drop_existing + [cfg.target_col], errors="ignore")
    else:
        X = df[[c for c in feature_cols if c in df.columns]].copy()
    y = df[cfg.target_col].copy()
    X = X.apply(pd.to_numeric, errors="coerce")
    X = X.dropna(axis=1, how="all").replace([np.inf, -np.inf], np.nan)
    valid_idx = X.dropna().index.intersection(y.dropna().index)
    return X.loc[valid_idx].reset_index(drop=True), y.loc[valid_idx].reset_index(drop=True)


def train_lgbm_binary(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    random_state: int = 42,
) -> object:
    import lightgbm as lgb

    model = lgb.LGBMClassifier(
        n_estimators=300,
        learning_rate=0.03,
        num_leaves=31,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=random_state,
        verbose=-1,
    )
    model.fit(X_train, y_train)
    return model


def temporal_binary_evaluate(
    df: pd.DataFrame,
    name: str = "dataset",
    config: ValidationConfig | None = None,
    feature_cols: Iterable[str] | None = None,
) -> dict[str, float | int | str]:
    cfg = config or ValidationConfig()
    X, y = prepare_xy(df, cfg, feature_cols=feature_cols)
    split = int(len(X) * cfg.train_ratio)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]
    model = train_lgbm_binary(X_train, y_train, cfg.random_state)
    proba = model.predict_proba(X_test)[:, 1]
    pred = (proba > 0.5).astype(int)
    return {
        "dataset": name,
        "features": int(X.shape[1]),
        "rows": int(X.shape[0]),
        "accuracy": float(accuracy_score(y_test, pred)),
        "logloss": float(log_loss(y_test, proba)),
    }


def feature_importance(
    df: pd.DataFrame,
    config: ValidationConfig | None = None,
) -> pd.DataFrame:
    cfg = config or ValidationConfig()
    X, y = prepare_xy(df, cfg)
    split = int(len(X) * cfg.train_ratio)
    model = train_lgbm_binary(X.iloc[:split], y.iloc[:split], cfg.random_state)
    return (
        pd.DataFrame({"feature": X.columns, "importance": model.feature_importances_})
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )


def compare_top_feature_sets(
    df: pd.DataFrame,
    importance: pd.DataFrame,
    top_ns: tuple[int, ...] = (30, 20, 10),
    config: ValidationConfig | None = None,
) -> pd.DataFrame:
    cfg = config or ValidationConfig()
    results = [temporal_binary_evaluate(df, "full", cfg)]
    for n in top_ns:
        top_features = importance["feature"].head(n).tolist()
        results.append(temporal_binary_evaluate(df, f"top_{n}", cfg, feature_cols=top_features))
    return pd.DataFrame(results).sort_values(["logloss", "accuracy"], ascending=[True, False])


def select_top_feature_dataset(
    df: pd.DataFrame,
    importance: pd.DataFrame,
    top_n: int = 30,
    config: ValidationConfig | None = None,
) -> pd.DataFrame:
    cfg = config or ValidationConfig()
    base_cols = [c for c in (*cfg.drop_cols, cfg.target_col, "close", "future_close") if c in df.columns]
    top_features = [c for c in importance["feature"].head(top_n).tolist() if c in df.columns]
    keep_cols = list(dict.fromkeys(base_cols + top_features))
    return df[keep_cols].copy()


def group_ablation(
    df: pd.DataFrame,
    group_prefixes: dict[str, tuple[str, ...]] | None = None,
    config: ValidationConfig | None = None,
) -> pd.DataFrame:
    cfg = config or ValidationConfig()
    groups = group_prefixes or DEFAULT_GROUP_PREFIXES
    X, y = prepare_xy(df, cfg)
    all_features = X.columns.tolist()
    full = pd.concat([X, y.rename(cfg.target_col)], axis=1)
    results = [temporal_binary_evaluate(full, "baseline_all", cfg)]

    for group_name, prefixes in groups.items():
        group_features = [c for c in all_features if any(c.startswith(p) for p in prefixes)]
        if group_features:
            results.append(temporal_binary_evaluate(full, f"{group_name}_only", cfg, group_features))

    for group_name, prefixes in groups.items():
        reduced = [c for c in all_features if not any(c.startswith(p) for p in prefixes)]
        if reduced:
            results.append(temporal_binary_evaluate(full, f"without_{group_name}", cfg, reduced))

    return pd.DataFrame(results).sort_values(["logloss", "accuracy"], ascending=[True, False])


def specialist_incremental_ablation(
    df: pd.DataFrame,
    specialist_groups: dict[str, list[str]],
    config: ValidationConfig | None = None,
) -> pd.DataFrame:
    cfg = config or ValidationConfig()
    X, y = prepare_xy(df, cfg)
    specialist_cols = {col for cols in specialist_groups.values() for col in cols}
    alpha_features = [c for c in X.columns if c not in specialist_cols]
    base_df = pd.concat([X, y.rename(cfg.target_col)], axis=1)
    baseline = temporal_binary_evaluate(base_df, "alpha_only", cfg, alpha_features)
    results = []
    for group_name, features in specialist_groups.items():
        use_features = alpha_features + [f for f in features if f in X.columns]
        metrics = temporal_binary_evaluate(base_df, group_name, cfg, use_features)
        metrics["delta_acc"] = metrics["accuracy"] - baseline["accuracy"]
        metrics["delta_logloss"] = metrics["logloss"] - baseline["logloss"]
        results.append(metrics)
    return pd.DataFrame(results).sort_values(["delta_logloss", "delta_acc"], ascending=[True, False])


def compare_alpha_vs_specialists(
    df: pd.DataFrame,
    specialist_prefixes: tuple[str, ...] = (
        "pivot_",
        "structure_",
        "vol_",
        "liq_",
        "micro_",
        "regime_",
        "mom_",
        "momentum_",
    ),
    config: ValidationConfig | None = None,
) -> pd.DataFrame:
    cfg = config or ValidationConfig()
    X, y = prepare_xy(df, cfg)
    specialist_features = [
        col for col in X.columns
        if any(col.startswith(prefix) for prefix in specialist_prefixes)
    ]
    alpha_features = [col for col in X.columns if col not in specialist_features]
    full = pd.concat([X, y.rename(cfg.target_col)], axis=1)
    rows = [
        temporal_binary_evaluate(full, "alpha_only", cfg, alpha_features),
        temporal_binary_evaluate(full, "alpha_plus_specialists", cfg, X.columns.tolist()),
    ]
    if specialist_features:
        rows.append(temporal_binary_evaluate(full, "specialists_only", cfg, specialist_features))
    return pd.DataFrame(rows).sort_values(["logloss", "accuracy"], ascending=[True, False])


def topn_probability_backtest(
    df: pd.DataFrame,
    importance: pd.DataFrame,
    top_n: int = 30,
    confidence: float = 0.55,
    config: ValidationConfig | None = None,
) -> tuple[pd.DataFrame, dict[str, float]]:
    cfg = config or ValidationConfig()
    required = {"close", "future_close"}
    missing = required.difference(df.columns)
    if missing:
        raise KeyError(f"Colunas obrigatorias ausentes para backtest: {sorted(missing)}")
    top_features = importance["feature"].head(top_n).tolist()
    X, y = prepare_xy(df, cfg, top_features)
    aligned = df.loc[X.index].reset_index(drop=True)
    split = int(len(X) * cfg.train_ratio)
    model = train_lgbm_binary(X.iloc[:split], y.iloc[:split], cfg.random_state)
    test_df = aligned.iloc[split:].copy().reset_index(drop=True)
    proba = model.predict_proba(X.iloc[split:])[:, 1]
    test_df["proba"] = proba
    test_df["signal"] = 0
    test_df.loc[test_df["proba"] > confidence, "signal"] = 1
    test_df.loc[test_df["proba"] < (1 - confidence), "signal"] = -1
    test_df["return"] = (test_df["future_close"] - test_df["close"]) / test_df["close"]
    if {"spread", "point_value"}.issubset(test_df.columns):
        test_df["spread_cost"] = (test_df["spread"] * test_df["point_value"]) / test_df["close"]
    else:
        test_df["spread_cost"] = 0.0
    test_df["strategy_return"] = test_df["signal"] * test_df["return"]
    test_df.loc[test_df["signal"] != 0, "strategy_return"] -= test_df["spread_cost"]
    test_df["equity_curve"] = (1 + test_df["strategy_return"]).cumprod()
    executed = test_df[test_df["signal"] != 0]
    summary = {
        "trades": int(len(executed)),
        "hit_rate": float((executed["strategy_return"] > 0).mean()) if len(executed) else 0.0,
        "total_return": float(test_df["equity_curve"].iloc[-1] - 1) if len(test_df) else 0.0,
        "avg_trade_return": float(executed["strategy_return"].mean()) if len(executed) else 0.0,
    }
    return test_df, summary


def target_horizon_scan(
    df: pd.DataFrame,
    importance: pd.DataFrame,
    horizons: tuple[int, ...] = (5, 10, 20, 30),
    top_n: int = 30,
    confidence: float = 0.55,
    train_ratio: float = 0.8,
) -> pd.DataFrame:
    if "close" not in df.columns:
        raise KeyError("target_horizon_scan precisa de coluna 'close'.")
    rows = []
    top_features = [c for c in importance["feature"].head(top_n).tolist() if c in df.columns]
    for horizon in horizons:
        tmp = df.copy()
        tmp["future_close"] = tmp["close"].shift(-horizon)
        tmp["target"] = (tmp["future_close"] > tmp["close"]).astype(int)
        tmp = tmp.dropna().reset_index(drop=True)
        cfg = ValidationConfig(target_col="target", train_ratio=train_ratio)
        backtest, summary = topn_probability_backtest(tmp, importance, top_n, confidence, cfg)
        rows.append({"horizon": horizon, **summary})
    return pd.DataFrame(rows).sort_values("total_return", ascending=False)


def candidate_windows(feature_name: str) -> list[int]:
    nums = re.findall(r"\d+", feature_name)
    if not nums:
        return [5, 12, 30, 60, 120]
    base = int(nums[-1])
    return sorted({max(2, int(base * factor)) for factor in (0.5, 0.75, 1.0, 1.25, 1.5)})


def feature_family(name: str) -> str | None:
    if "corr" in name:
        return "corr"
    if "std" in name:
        return "std"
    if "atr" in name:
        return "atr"
    if "lag_volume" in name:
        return "lag_volume"
    if "lag_" in name:
        return "lag"
    if "close_low_ratio" in name:
        return "close_low_ratio"
    if "close_high_ratio" in name:
        return "close_high_ratio"
    if "close_ma" in name:
        return "close_ma_ratio"
    if "mom" in name:
        return "mom"
    if "vol" in name:
        return "vol"
    return None


def build_window_candidate(df: pd.DataFrame, family: str, window: int) -> pd.Series | None:
    close = df["close"]
    volume = df["volume"] if "volume" in df.columns else df.get("tick_volume")
    if family == "corr" and volume is not None:
        return close.pct_change().rolling(window).corr(volume)
    if family == "std":
        return close.pct_change().rolling(window).std()
    if family == "atr":
        tr = pd.concat(
            [
                df["high"] - df["low"],
                (df["high"] - close.shift(1)).abs(),
                (df["low"] - close.shift(1)).abs(),
            ],
            axis=1,
        ).max(axis=1)
        return tr.rolling(window).mean()
    if family == "lag_volume" and volume is not None:
        return volume.shift(window)
    if family == "lag":
        return close.shift(window)
    if family == "close_low_ratio":
        return close / (df["low"].rolling(window).min() + 1e-12)
    if family == "close_high_ratio":
        return close / (df["high"].rolling(window).max() + 1e-12)
    if family == "close_ma_ratio":
        return close / (close.rolling(window).mean() + 1e-12)
    if family == "mom":
        return close.pct_change(window)
    if family == "vol" and volume is not None:
        mean = volume.rolling(window).mean()
        std = volume.rolling(window).std()
        return (volume - mean) / (std + 1e-12)
    return None


def scan_feature_parameter_windows(
    df: pd.DataFrame,
    top_features: list[str],
    config: ValidationConfig | None = None,
) -> pd.DataFrame:
    """Reusable, dataframe-based version of ALPHAEDU 06_feature_parameter_scan.py."""
    cfg = config or ValidationConfig()
    X_base, y_base = prepare_xy(df, cfg)
    rows = []
    base_df = pd.concat([X_base, y_base.rename(cfg.target_col)], axis=1)
    for feature in top_features:
        family = feature_family(feature)
        if family is None:
            continue
        for window in candidate_windows(feature):
            candidate = build_window_candidate(df.reset_index(drop=True), family, window)
            if candidate is None:
                continue
            work = base_df.copy()
            work["candidate"] = candidate.reset_index(drop=True)
            try:
                metrics = temporal_binary_evaluate(work, f"{feature}_{window}", cfg)
            except Exception:
                continue
            rows.append(
                {
                    "feature": feature,
                    "family": family,
                    "window": window,
                    "accuracy": metrics["accuracy"],
                    "logloss": metrics["logloss"],
                }
            )
    return pd.DataFrame(rows).sort_values(["logloss", "accuracy"], ascending=[True, False])
