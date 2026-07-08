from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd


DIRECTION_LABELS = {0: "DOWN", 1: "FLAT", 2: "UP"}
DEFAULT_EXPERT_WEIGHTS = {
    "smc": 0.30,
    "momentum": 0.20,
    "ichimoku": 0.20,
    "hvn": 0.15,
    "pullback": 0.15,
}
REGIME_EXPERT_WEIGHTS = {
    "trending": {
        "smc": 0.35,
        "momentum": 0.25,
        "ichimoku": 0.20,
        "hvn": 0.10,
        "pullback": 0.10,
        "correlation": 0.15,
        "divergence": 0.08,
        "flow": 0.10,
        "pattern": 0.05,
        "trend_master": 0.12,
    },
    "ranging": {
        "smc": 0.15,
        "momentum": 0.10,
        "ichimoku": 0.30,
        "hvn": 0.25,
        "pullback": 0.20,
        "correlation": 0.10,
        "divergence": 0.12,
        "flow": 0.08,
        "pattern": 0.10,
        "trend_master": 0.10,
    },
    "volatile": {
        "smc": 0.25,
        "momentum": 0.15,
        "ichimoku": 0.25,
        "hvn": 0.15,
        "pullback": 0.20,
        "correlation": 0.12,
        "divergence": 0.10,
        "flow": 0.08,
        "pattern": 0.05,
        "trend_master": 0.10,
    },
    "calm": {
        "smc": 0.20,
        "momentum": 0.25,
        "ichimoku": 0.20,
        "hvn": 0.20,
        "pullback": 0.15,
        "correlation": 0.18,
        "divergence": 0.10,
        "flow": 0.12,
        "pattern": 0.08,
        "trend_master": 0.12,
    },
}


@dataclass
class ExpertVote:
    expert: str
    direction: int
    confidence: float
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConsensusResult:
    direction: int
    probability: float
    confidence: float
    votes: list[ExpertVote]
    consensus_layer: str
    weights_by_regime: dict[str, float] = field(default_factory=dict)


@dataclass
class HybridSignal:
    expert: str
    direction: int
    confidence: float
    source: str
    rule_based_weight: float = 1.0
    ml_weight: float = 1.0
    combined: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class HybridConsensusResult:
    direction: int
    probability: float
    confidence: float
    signals: list[HybridSignal]
    regime: str
    weights_used: dict[str, float]
    ml_adjustment: float


def consensus_layer(probability: float, confidence: float) -> str:
    combined = probability * confidence
    if combined >= 0.70:
        return "C1"
    if combined >= 0.50:
        return "C2"
    if combined >= 0.30:
        return "C3"
    return "C0"


class ExpertConsensus:
    def __init__(self, weights: dict[str, float] | None = None, default_regime: str = "trending"):
        self.default_weights = weights or DEFAULT_EXPERT_WEIGHTS
        self.default_regime = default_regime

    def evaluate(self, votes: list[ExpertVote], regime: str | None = None) -> ConsensusResult:
        regime_name = regime or self.default_regime
        regime_weights = REGIME_EXPERT_WEIGHTS.get(regime_name, REGIME_EXPERT_WEIGHTS["trending"])
        total_weight = 0.0
        weighted_direction = 0.0
        weighted_confidence = 0.0
        normalized: list[ExpertVote] = []
        for vote in votes:
            weight = float(regime_weights.get(vote.expert, self.default_weights.get(vote.expert, vote.weight)))
            total_weight += weight
            weighted_direction += float(vote.direction) * float(vote.confidence) * weight
            weighted_confidence += float(vote.confidence) * weight
            normalized.append(ExpertVote(vote.expert, int(vote.direction), float(vote.confidence), weight, vote.metadata))
        if total_weight <= 0:
            return ConsensusResult(0, 0.0, 0.0, normalized, "C0", regime_weights)
        probability = abs(weighted_direction) / total_weight
        confidence = weighted_confidence / total_weight
        direction = 1 if weighted_direction > 0 else -1 if weighted_direction < 0 else 0
        return ConsensusResult(direction, probability, confidence, normalized, consensus_layer(probability, confidence), regime_weights)

    def blind_spots(self, votes: list[ExpertVote]) -> list[str]:
        covered = {vote.expert for vote in votes}
        return sorted(set(self.default_weights) - covered)


class HybridConsensus:
    def __init__(self, ml_weight_factor: float = 0.30):
        self.ml_weight_factor = float(np.clip(ml_weight_factor, 0.0, 1.0))
        self.ml_performance: dict[str, float] = {}

    def evaluate(
        self,
        rule_signals: list[HybridSignal],
        ml_predictions: dict[str, np.ndarray],
        regime: str = "trending",
    ) -> HybridConsensusResult:
        base_weights = REGIME_EXPERT_WEIGHTS.get(regime, REGIME_EXPERT_WEIGHTS["trending"])
        total_direction = 0.0
        total_weight = 0.0
        merged: list[HybridSignal] = []
        for signal in rule_signals:
            rule_weight = float(base_weights.get(signal.expert, 0.2))
            ml_confidence = self._ml_confidence(signal.expert, ml_predictions)
            perf_bonus = self.ml_performance.get(signal.expert, 0.0)
            ml_adjustment = min(1.0, ml_confidence + perf_bonus) * self.ml_weight_factor
            final_weight = rule_weight * (1.0 + ml_adjustment)
            total_direction += int(signal.direction) * float(signal.confidence) * final_weight
            total_weight += final_weight
            merged.append(
                HybridSignal(
                    expert=signal.expert,
                    direction=int(signal.direction),
                    confidence=min(1.0, float(signal.confidence) * (1.0 + ml_adjustment)),
                    source="hybrid",
                    rule_based_weight=rule_weight,
                    ml_weight=ml_adjustment,
                    combined=True,
                    metadata={**signal.metadata, "ml_confidence": ml_confidence},
                )
            )
        if total_weight <= 0:
            return HybridConsensusResult(0, 0.0, 0.0, merged, regime, base_weights, self.ml_weight_factor)
        probability = abs(total_direction) / total_weight
        direction = 1 if total_direction > 0 else -1 if total_direction < 0 else 0
        return HybridConsensusResult(direction, probability, min(1.0, probability), merged, regime, base_weights, self.ml_weight_factor)

    def update_performance(self, expert: str, accuracy: float) -> None:
        self.ml_performance[expert] = float(np.clip(accuracy, 0.0, 1.0)) * 0.10

    @staticmethod
    def _ml_confidence(expert: str, ml_predictions: dict[str, np.ndarray]) -> float:
        pred = ml_predictions.get(expert)
        if pred is None:
            return 0.5
        arr = np.asarray(pred, dtype=float)
        if arr.size == 0:
            return 0.5
        probs = arr.mean(axis=0) if arr.ndim > 1 else arr
        return float(np.nanmax(probs)) if probs.size else 0.5


class HierarchicalConfidence:
    def __init__(self, weights: dict[str, float] | None = None):
        self.weights = weights or {"C1": 0.20, "C2": 0.30, "C3": 0.50}

    def score(self, signals: dict[str, float]) -> float:
        values = [(float(value), self.weights[layer]) for layer, value in signals.items() if layer in self.weights]
        total = sum(weight for _, weight in values)
        if total <= 0:
            return 0.0
        return sum(value * weight for value, weight in values) / total

    def recalibrate_by_volatility(self, market_condition: str) -> dict[str, float]:
        if market_condition == "high_volatility":
            self.weights = {"C1": 0.10, "C2": 0.20, "C3": 0.50}
        elif market_condition == "low_volatility":
            self.weights = {"C1": 0.25, "C2": 0.35, "C3": 0.40}
        else:
            self.weights = {"C1": 0.20, "C2": 0.30, "C3": 0.50}
        return self.weights.copy()


def load_expected_features(model_name: str, model_dir: str | Path) -> list[str]:
    path = Path(model_dir) / f"{model_name}_features.json"
    if not path.exists():
        path = Path(model_dir) / "features.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("features", data if isinstance(data, list) else []))


def prepare_features_with_fallback(df: pd.DataFrame, expected_features: list[str]) -> pd.DataFrame:
    prepared = pd.DataFrame(index=df.index)
    for feature in expected_features:
        if feature in df.columns:
            prepared[feature] = df[feature]
        elif "norm" in feature or "ratio" in feature:
            prepared[feature] = 1.0
        elif "regime" in feature or "score" in feature:
            prepared[feature] = 1.0
        elif "volatility" in feature or "atr" in feature:
            prepared[feature] = 0.005
        elif "dist" in feature:
            prepared[feature] = 0.01
        elif "rsi" in feature:
            prepared[feature] = 50.0
        else:
            prepared[feature] = 0.0
    return prepared.reindex(columns=expected_features).replace([np.inf, -np.inf], np.nan).fillna(0.0)


def safe_model_predict(model: Any, X: pd.DataFrame | np.ndarray, model_name: str = "model") -> np.ndarray:
    if model is None:
        return np.array([0])
    frame = X.copy() if isinstance(X, pd.DataFrame) else pd.DataFrame(np.asarray(X).reshape(1, -1))
    if hasattr(model, "n_features_in_"):
        expected = int(model.n_features_in_)
        if frame.shape[1] < expected:
            for idx in range(expected - frame.shape[1]):
                frame[f"missing_{idx}"] = 0.0
        elif frame.shape[1] > expected:
            frame = frame.iloc[:, :expected]
    try:
        return np.asarray(model.predict(frame.to_numpy()))
    except Exception as exc:
        return np.array([0], dtype=object)


class NexusModelStore:
    def __init__(self, model_dir: str | Path):
        self.model_dir = Path(model_dir)
        self.models: dict[str, Any] = {}

    def load(self, name: str) -> Any | None:
        if name in self.models:
            return self.models[name]
        path = self.model_dir / f"{name}.pkl"
        if not path.exists():
            return None
        model = joblib.load(path)
        self.models[name] = model
        return model

    def list_models(self, pattern: str = "*.pkl") -> list[str]:
        if not self.model_dir.exists():
            return []
        return sorted(path.stem for path in self.model_dir.glob(pattern))


class NexusFusionPredictor:
    def __init__(self, model_dir: str | Path):
        self.model_dir = Path(model_dir)
        self.models: dict[str, dict[str, Any]] = {}
        self.feature_columns: list[str] = []

    def load_model(self, name: str) -> bool:
        path = self.model_dir / f"{name}.pkl"
        if not path.exists():
            return False
        data = joblib.load(path)
        if not isinstance(data, dict):
            data = {"model": data, "scaler": None, "feature_names": []}
        self.models[name] = data
        if not self.feature_columns and data.get("feature_names"):
            self.feature_columns = list(data["feature_names"])
        return True

    def load_all(self, pattern: str = "symbol_*.pkl", include_global: bool = True) -> int:
        loaded = 0
        if include_global and self.load_model("global_all"):
            loaded += 1
        for path in self.model_dir.glob(pattern):
            loaded += int(self.load_model(path.stem))
        return loaded

    def predict(self, features: pd.DataFrame | np.ndarray, symbol: str | None = None) -> dict[str, Any]:
        model_name = f"symbol_{symbol}" if symbol else "global_all"
        if model_name not in self.models:
            model_name = "global_all"
        data = self.models.get(model_name)
        if not data:
            return empty_nexus_prediction()
        X = self._coerce_features(features, data.get("feature_names") or self.feature_columns)
        scaler = data.get("scaler")
        if scaler is not None:
            X = scaler.transform(X)
        model = data["model"]
        try:
            proba = model.predict_proba(X)[0] if hasattr(model, "predict_proba") else np.array([0.0, 1.0, 0.0])
            pred = int(model.predict(X)[0])
        except Exception:
            return empty_nexus_prediction(model_name)
        return {
            "direction": DIRECTION_LABELS.get(pred, str(pred)),
            "probability": float(np.nanmax(proba)),
            "confidence": float(np.nanstd(proba)),
            "proba": {DIRECTION_LABELS.get(i, str(i)): float(value) for i, value in enumerate(proba)},
            "model": model_name,
        }

    def _coerce_features(self, features: pd.DataFrame | np.ndarray, expected: list[str]) -> np.ndarray:
        if isinstance(features, pd.DataFrame):
            frame = prepare_features_with_fallback(features, expected) if expected else features.select_dtypes(include=[np.number])
            return frame.tail(1).to_numpy(dtype=float)
        arr = np.nan_to_num(np.asarray(features, dtype=float), nan=0.0, posinf=0.0, neginf=0.0)
        return arr.reshape(1, -1) if arr.ndim == 1 else arr


class RegimeModelBlender:
    DEFAULT_MODELS = {
        "mtf": {"file": "direction_mtf.pkl", "weight": 0.25},
        "forex": {"file": "direction_forex.pkl", "weight": 0.15},
        "momentum": {"file": "momentum_ml.pkl", "weight": 0.15},
        "ichimoku": {"file": "ichimoku_ml.pkl", "weight": 0.15},
        "hvn": {"file": "hvn_ml.pkl", "weight": 0.15},
        "pullback": {"file": "pullback_ml.pkl", "weight": 0.10},
        "regime": {"file": "regime_forex.pkl", "weight": 0.05},
    }

    REGIME_MODEL_WEIGHTS = {
        "trending": {"mtf": 0.35, "forex": 0.15, "momentum": 0.20, "ichimoku": 0.15, "hvn": 0.10, "pullback": 0.05},
        "ranging": {"mtf": 0.20, "forex": 0.15, "momentum": 0.10, "ichimoku": 0.25, "hvn": 0.20, "pullback": 0.10},
        "volatile": {"mtf": 0.25, "forex": 0.20, "momentum": 0.15, "ichimoku": 0.15, "hvn": 0.15, "pullback": 0.10},
        "calm": {"mtf": 0.30, "forex": 0.15, "momentum": 0.15, "ichimoku": 0.15, "hvn": 0.15, "pullback": 0.10},
    }

    def __init__(self, model_dir: str | Path, models_config: dict[str, dict[str, Any]] | None = None):
        self.model_dir = Path(model_dir)
        self.models_config = models_config or self.DEFAULT_MODELS
        self.models = {
            name: joblib.load(self.model_dir / cfg["file"])
            for name, cfg in self.models_config.items()
            if (self.model_dir / cfg["file"]).exists()
        }

    def predict(self, features: pd.DataFrame | np.ndarray, regime: str = "calm") -> dict[str, Any]:
        X = features.tail(1).to_numpy(dtype=float) if isinstance(features, pd.DataFrame) else np.asarray(features, dtype=float)
        X = np.nan_to_num(X.reshape(1, -1) if X.ndim == 1 else X, nan=0.0, posinf=0.0, neginf=0.0)
        weights = self.REGIME_MODEL_WEIGHTS.get(regime, self.REGIME_MODEL_WEIGHTS["calm"])
        scores: dict[str, float] = {}
        total_weight = 0.0
        for name, model in self.models.items():
            if name == "regime" or not hasattr(model, "predict_proba"):
                continue
            if hasattr(model, "n_features_in_") and int(model.n_features_in_) != X.shape[1]:
                continue
            proba = model.predict_proba(X)[0]
            weight = float(weights.get(name, self.models_config[name].get("weight", 0.1)))
            if len(proba) >= 3:
                scores["DOWN"] = scores.get("DOWN", 0.0) + float(proba[0]) * weight
                scores["FLAT"] = scores.get("FLAT", 0.0) + float(proba[1]) * weight
                scores["UP"] = scores.get("UP", 0.0) + float(proba[2]) * weight
            elif len(proba) == 2:
                scores["DOWN"] = scores.get("DOWN", 0.0) + float(1.0 - proba[1]) * weight
                scores["UP"] = scores.get("UP", 0.0) + float(proba[1]) * weight
            total_weight += weight
        if total_weight <= 0:
            scores = {"DOWN": 0.33, "FLAT": 0.34, "UP": 0.33}
        else:
            scores = {key: value / total_weight for key, value in scores.items()}
        direction = max(("DOWN", "FLAT", "UP"), key=lambda key: scores.get(key, 0.0))
        return {"direction": direction, "probability": float(scores.get(direction, 0.0)), "proba": scores, "regime": regime}


def empty_nexus_prediction(model: str = "none") -> dict[str, Any]:
    return {
        "direction": "FLAT",
        "probability": 0.0,
        "confidence": 0.0,
        "proba": {"DOWN": 0.0, "FLAT": 0.0, "UP": 0.0},
        "model": model,
    }
