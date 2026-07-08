from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import pandas as pd


@dataclass
class ModelMetadata:
    name: str
    model_type: str
    symbols: list[str]
    timeframes: list[str]
    feature_columns: list[str]
    target: str = "target"
    buy_threshold: float = 0.55
    sell_threshold: float = 0.55
    metrics: dict[str, Any] = field(default_factory=dict)
    source: str = "fusion_refatorado"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


class ModelRegistry:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, model: Any, scaler: Any, metadata: ModelMetadata, folder: str | Path) -> Path:
        model_dir = self.root / folder
        model_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, model_dir / "model.pkl")
        joblib.dump(scaler, model_dir / "scaler.pkl")
        (model_dir / "meta.json").write_text(
            json.dumps(asdict(metadata), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self.update_index()
        return model_dir

    def load(self, folder: str | Path) -> tuple[Any, Any, ModelMetadata]:
        model_dir = self.root / folder
        model = joblib.load(model_dir / "model.pkl")
        scaler = joblib.load(model_dir / "scaler.pkl")
        meta_data = json.loads((model_dir / "meta.json").read_text(encoding="utf-8"))
        return model, scaler, ModelMetadata(**meta_data)

    def update_index(self) -> pd.DataFrame:
        rows = []
        for meta_file in self.root.glob("**/meta.json"):
            data = json.loads(meta_file.read_text(encoding="utf-8"))
            rows.append({
                "folder": str(meta_file.parent.relative_to(self.root)),
                "name": data.get("name"),
                "model_type": data.get("model_type"),
                "symbols": ",".join(data.get("symbols", [])),
                "timeframes": ",".join(data.get("timeframes", [])),
                "accuracy": data.get("metrics", {}).get("accuracy"),
                "f1_macro": data.get("metrics", {}).get("f1_macro"),
                "buy_threshold": data.get("buy_threshold"),
                "sell_threshold": data.get("sell_threshold"),
                "created_at": data.get("created_at"),
            })
        index = pd.DataFrame(rows)
        if not index.empty:
            index = index.sort_values(["model_type", "name", "created_at"])
        index.to_csv(self.root / "models_index.csv", index=False)
        return index
