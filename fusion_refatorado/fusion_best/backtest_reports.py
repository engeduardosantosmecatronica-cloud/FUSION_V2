from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def _read_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def flatten_expert_backtest_report(path: str | Path) -> pd.DataFrame:
    data = _read_json(path)
    rows: list[dict[str, Any]] = []
    expert = data.get("expert") or Path(path).stem.replace("backtest_", "")
    for market_key, result in (data.get("results") or {}).items():
        symbol = result.get("symbol")
        timeframe = result.get("timeframe")
        for feature, stats in (result.get("features") or {}).items():
            rows.append(
                {
                    "source_file": Path(path).name,
                    "expert": expert,
                    "market_key": market_key,
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "feature": feature,
                    "sharpe": stats.get("sharpe"),
                    "win_rate": stats.get("win_rate"),
                    "threshold": stats.get("threshold"),
                    "samples": stats.get("samples"),
                }
            )
    return pd.DataFrame(rows)


def flatten_expert_backtest_dir(path: str | Path) -> pd.DataFrame:
    root = Path(path)
    frames = []
    for report_path in sorted(root.glob("backtest_*.json")):
        if report_path.name == "backtest_all_experts_all_assets.json":
            continue
        frame = flatten_expert_backtest_report(report_path)
        if not frame.empty:
            frames.append(frame)
    if not frames:
        return pd.DataFrame(
            columns=[
                "source_file",
                "expert",
                "market_key",
                "symbol",
                "timeframe",
                "feature",
                "sharpe",
                "win_rate",
                "threshold",
                "samples",
            ]
        )
    return pd.concat(frames, ignore_index=True)


def rank_expert_features(frame: pd.DataFrame, min_samples: int = 30) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    ranked = frame.copy()
    ranked["abs_sharpe"] = ranked["sharpe"].abs()
    ranked = ranked[ranked["samples"].fillna(0) >= min_samples]
    return ranked.sort_values(["abs_sharpe", "win_rate"], ascending=[False, False]).reset_index(drop=True)


def flatten_model_backtest_results(path: str | Path) -> pd.DataFrame:
    data = _read_json(path)
    rows: list[dict[str, Any]] = []
    for expert, expert_results in data.items():
        if not isinstance(expert_results, dict):
            continue
        for key, result in expert_results.items():
            if not isinstance(result, dict):
                continue
            metrics = result.get("metrics") or {}
            strategy_returns = result.get("strategy_returns") or {}
            rows.append(
                {
                    "expert": result.get("expert", expert),
                    "key": key,
                    "symbol": result.get("symbol"),
                    "timeframe": result.get("timeframe"),
                    "model": result.get("model"),
                    "accuracy": metrics.get("accuracy"),
                    "precision": metrics.get("precision"),
                    "recall": metrics.get("recall"),
                    "f1": metrics.get("f1"),
                    "auc": metrics.get("auc"),
                    "n_samples": metrics.get("n_samples"),
                    "sharpe": strategy_returns.get("sharpe_ratio"),
                    "max_drawdown": strategy_returns.get("max_drawdown"),
                    "win_rate": strategy_returns.get("win_rate"),
                    "total_return": strategy_returns.get("total_return"),
                    "n_predictions": result.get("n_predictions"),
                    "n_windows": result.get("n_windows"),
                }
            )
    return pd.DataFrame(rows)


def rank_model_backtests(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    ranked = frame.copy()
    ranked["auc"] = ranked["auc"].fillna(0.0)
    ranked["sharpe"] = ranked["sharpe"].fillna(0.0)
    ranked["win_rate"] = ranked["win_rate"].fillna(0.0)
    ranked["score"] = ranked["auc"] + ranked["sharpe"].clip(-1.0, 1.0) * 0.20 + (ranked["win_rate"] - 0.5) * 0.30
    return ranked.sort_values(["score", "auc", "sharpe"], ascending=[False, False, False]).reset_index(drop=True)


def top_strategy_models_from_report(path: str | Path, top_n: int = 10) -> pd.DataFrame:
    data = _read_json(path)
    return pd.DataFrame(data.get("top_models") or []).head(top_n)


def flatten_feature_analysis_report(path: str | Path) -> pd.DataFrame:
    data = _read_json(path)
    features: list[dict[str, Any]] = []
    features.extend(data.get("top_features") or [])
    for feature_name, feature_data in (data.get("feature_details") or {}).items():
        row = dict(feature_data)
        row["feature"] = feature_name
        features.append(row)
    if not features:
        return pd.DataFrame()
    frame = pd.DataFrame(features)
    parts = Path(path).stem.split("_")
    frame["symbol"] = parts[2] if len(parts) > 2 else data.get("symbol")
    frame["timeframe"] = parts[3] if len(parts) > 3 else data.get("timeframe")
    frame["source_file"] = Path(path).name
    return frame


def summarize_feature_analysis(frame: pd.DataFrame, metric: str = "predictive_power") -> dict[str, pd.DataFrame]:
    if frame.empty or metric not in frame.columns:
        return {"global": frame.copy(), "by_symbol": pd.DataFrame(), "by_timeframe": pd.DataFrame()}
    ranked = frame.sort_values(metric, ascending=False).reset_index(drop=True)
    by_symbol = ranked.groupby("symbol", dropna=False).head(5).reset_index(drop=True) if "symbol" in ranked else pd.DataFrame()
    by_timeframe = ranked.groupby("timeframe", dropna=False).head(5).reset_index(drop=True) if "timeframe" in ranked else pd.DataFrame()
    return {"global": ranked.head(20), "by_symbol": by_symbol, "by_timeframe": by_timeframe}
