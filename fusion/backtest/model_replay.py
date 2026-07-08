from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from fusion.backtest.feature_replay_runner import FeatureReplayFrame
from fusion.core.objects import to_plain_dict


@dataclass
class ModelPredictionSnapshot:
    symbol: str
    timeframe: str
    timestamp: str = ""
    prediction: int = 0
    p_buy: float = 0.0
    p_sell: float = 0.0
    status: str = "NO_MODEL"
    model_type: str = "single_model"
    feature_count: int = 0
    missing_features: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_plain_dict(self)


class BacktestSingleModel:
    def __init__(self, model_path: Path, scaler_path: Path, meta_path: Path) -> None:
        import joblib

        self.model_path = Path(model_path)
        self.scaler_path = Path(scaler_path)
        self.meta_path = Path(meta_path)
        self.model = joblib.load(self.model_path)
        self.scaler = joblib.load(self.scaler_path)
        self.meta = joblib.load(self.meta_path)
        self.feature_cols = list(self.meta.get("feature_columns", []))
        self.buy_thresh = float(self.meta.get("buy_threshold", 0.55))
        self.sell_thresh = float(self.meta.get("sell_threshold", 0.55))

    def predict(self, features: dict[str, Any]) -> ModelPredictionSnapshot:
        symbol = str(self.meta.get("symbol", ""))
        timeframe = str(self.meta.get("timeframe", ""))
        missing = [col for col in self.feature_cols if col not in features]
        snapshot = ModelPredictionSnapshot(
            symbol=symbol,
            timeframe=timeframe,
            feature_count=len(self.feature_cols),
            missing_features=missing,
            metadata={
                "model_path": str(self.model_path),
                "training_date": self.meta.get("training_date", ""),
                "accuracy": self.meta.get("accuracy", 0.0),
                "buy_threshold": self.buy_thresh,
                "sell_threshold": self.sell_thresh,
            },
        )
        if missing:
            snapshot.status = "MISSING_FEATURES"
            return snapshot

        row = pd.DataFrame([{col: features[col] for col in self.feature_cols}], columns=self.feature_cols)
        try:
            scaled = self.scaler.transform(row.values)
            scaled_df = pd.DataFrame(scaled, columns=self.feature_cols)
            probs = self.model.predict_proba(scaled_df)
        except Exception as exc:
            snapshot.status = "PREDICT_ERROR"
            snapshot.metadata["error"] = str(exc)
            return snapshot

        classes = list(getattr(self.model, "classes_", []))
        p_buy = 0.0
        p_sell = 0.0
        for idx, cls in enumerate(classes):
            if int(cls) == 1:
                p_buy = float(probs[0, idx])
            elif int(cls) == 2:
                p_sell = float(probs[0, idx])
        prediction = 0
        if p_buy > self.buy_thresh:
            prediction = 1
        elif p_sell > self.sell_thresh:
            prediction = 2
        snapshot.prediction = prediction
        snapshot.p_buy = p_buy
        snapshot.p_sell = p_sell
        snapshot.status = "OK"
        return snapshot


class BacktestModelRegistry:
    def __init__(self, model_dir: Path | str = "models") -> None:
        self.model_dir = Path(model_dir)
        self.models: dict[tuple[str, str], BacktestSingleModel] = {}

    def load(self) -> dict[tuple[str, str], BacktestSingleModel]:
        self.models.clear()
        if not self.model_dir.exists():
            return self.models
        for sym_dir in self.model_dir.iterdir():
            if not sym_dir.is_dir():
                continue
            for tf_dir in sym_dir.iterdir():
                if not tf_dir.is_dir():
                    continue
                model_path = tf_dir / "model.pkl"
                scaler_path = tf_dir / "scaler.pkl"
                meta_path = tf_dir / "meta.pkl"
                if not (model_path.exists() and scaler_path.exists() and meta_path.exists()):
                    continue
                try:
                    model = BacktestSingleModel(model_path, scaler_path, meta_path)
                except Exception:
                    continue
                self.models[(sym_dir.name.upper(), tf_dir.name.upper())] = model
        return self.models

    def get(self, symbol: str, timeframe: str) -> BacktestSingleModel | None:
        if not self.models:
            self.load()
        return self.models.get((symbol.upper(), timeframe.upper()))


class ModelReplayRunner:
    def __init__(self, registry: BacktestModelRegistry) -> None:
        self.registry = registry

    def predict_frame(self, frame: FeatureReplayFrame) -> dict[str, ModelPredictionSnapshot]:
        symbol = frame.replay.context.symbol
        predictions: dict[str, ModelPredictionSnapshot] = {}
        for timeframe, snapshot in frame.snapshots.items():
            model = self.registry.get(symbol, timeframe)
            if model is None:
                predictions[timeframe] = ModelPredictionSnapshot(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=snapshot.timestamp,
                    status="NO_MODEL",
                )
                continue
            if snapshot.status != "OK":
                predictions[timeframe] = ModelPredictionSnapshot(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=snapshot.timestamp,
                    status=snapshot.status,
                    metadata={"feature_reason": snapshot.reason},
                )
                continue
            prediction = model.predict(snapshot.features)
            prediction.timestamp = snapshot.timestamp
            predictions[timeframe] = prediction
        return predictions

