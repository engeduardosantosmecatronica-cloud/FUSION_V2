from __future__ import annotations

from pathlib import Path

import pandas as pd


MODEL_EXTENSIONS = {".pkl", ".joblib", ".h5", ".onnx", ".pt", ".pth"}
SKIP_PARTS = {"venv", ".venv", "__pycache__", "site-packages", "node_modules", "qlib-main", "qlib-git"}


def classify_model_path(path: Path) -> str:
    upper = str(path).upper()
    if "BUILD_MODELS" in upper and "MODELS_PKL" in upper:
        return "build_models_shard"
    if "NEXUS_BACKUP" in upper and "BY_SYMBOL" in upper:
        return "nexus_by_symbol"
    if "NEXUS_BACKUP" in upper and "GLOBAL" in upper:
        return "nexus_global_strategy"
    if "DATA_HUB" in upper and "MODELOS" in upper:
        return "data_hub_symbol"
    if "QLIB" in upper:
        return "qlib_baseline"
    if "GENESIS" in upper:
        return "genesis_global"
    return "unknown"


def build_legacy_model_inventory(backup_root: str | Path, output_csv: str | Path | None = None) -> pd.DataFrame:
    backup_root = Path(backup_root)
    rows = []
    for path in backup_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in MODEL_EXTENSIONS:
            continue
        parts = {part.lower() for part in path.parts}
        if SKIP_PARTS.intersection(parts):
            continue
        stat = path.stat()
        rows.append(
            {
                "path": str(path),
                "name": path.name,
                "extension": path.suffix.lower(),
                "size_mb": round(stat.st_size / 1024 / 1024, 3),
                "modified_at": pd.Timestamp(stat.st_mtime, unit="s").isoformat(),
                "category": classify_model_path(path),
            }
        )
    inventory = pd.DataFrame(rows)
    if not inventory.empty:
        inventory = inventory.sort_values(["category", "size_mb"], ascending=[True, False])
    if output_csv is not None:
        output_path = Path(output_csv)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        inventory.to_csv(output_path, index=False)
    return inventory
