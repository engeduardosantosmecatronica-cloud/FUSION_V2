from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def flatten_training_summary(summary_path: str | Path, models_dir: str | Path | None = None) -> pd.DataFrame:
    summary_path = Path(summary_path)
    data = json.loads(summary_path.read_text(encoding="utf-8"))
    root = Path(models_dir) if models_dir is not None else summary_path.parent
    rows: list[dict[str, Any]] = []
    for expert, models in (data.get("results") or {}).items():
        for model_type, payload in (models or {}).items():
            metrics = payload.get("metrics") or {}
            file_name = f"{expert}_{model_type}.pkl"
            model_path = root / file_name
            rows.append(
                {
                    "expert": expert,
                    "model_type": model_type,
                    "file_name": file_name,
                    "path": str(model_path),
                    "exists": model_path.exists(),
                    "size_mb": round(model_path.stat().st_size / (1024 * 1024), 6) if model_path.exists() else None,
                    "accuracy": metrics.get("accuracy"),
                    "precision": metrics.get("precision"),
                    "recall": metrics.get("recall"),
                    "f1": metrics.get("f1"),
                    "auc": metrics.get("auc"),
                    "training_time": payload.get("training_time"),
                    "n_samples": payload.get("n_samples"),
                    "source_timestamp": data.get("timestamp"),
                }
            )
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.sort_values(["auc", "f1", "accuracy"], ascending=False, na_position="last")
    return frame


def best_models_by_expert(inventory: pd.DataFrame, metric: str = "auc") -> pd.DataFrame:
    if inventory.empty or metric not in inventory.columns:
        return pd.DataFrame()
    ordered = inventory.sort_values([metric, "f1", "accuracy"], ascending=False, na_position="last")
    return ordered.groupby("expert", as_index=False).head(1).reset_index(drop=True)

