from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd


@dataclass
class LoadedModelBundle:
    model: Any
    features: list[str]
    metadata: Any = None
    model_path: Path | None = None


@dataclass
class LegacyModelPackage:
    model: Any
    scaler: Any | None
    features: list[str]
    metrics: dict[str, Any]
    model_path: Path


class QlibModelWrapper:
    def __init__(self, pipeline: Any, feature_cols: list[str]):
        self.pipeline = pipeline
        self.feature_cols = feature_cols

    def predict(self, X: pd.DataFrame | np.ndarray):
        if isinstance(X, pd.DataFrame):
            available = [col for col in self.feature_cols if col in X.columns]
            return self.pipeline.predict(X[available])
        return self.pipeline.predict(X)


def load_model_bundle(model_name: str, model_dir: str | Path = "models_refatorado") -> LoadedModelBundle | None:
    root = Path(model_dir)
    candidates = [
        root / f"{model_name}_model.pkl",
        root / f"{model_name}.pkl",
        root / model_name / "model.pkl",
    ]
    model_path = next((path for path in candidates if path.exists()), None)
    if model_path is None:
        return None
    model = joblib.load(model_path)
    features_path = model_path.with_name(f"{model_name}_features.json")
    if not features_path.exists():
        features_path = model_path.parent / "features.json"
    metadata_path = model_path.with_name(f"{model_name}_metadata.pkl")
    if not metadata_path.exists():
        metadata_path = model_path.parent / "metadata.pkl"
    features: list[str] = []
    if features_path.exists():
        with features_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        features = list(data.get("features", data if isinstance(data, list) else []))
    metadata = joblib.load(metadata_path) if metadata_path.exists() else None
    return LoadedModelBundle(model=model, features=features, metadata=metadata, model_path=model_path)


def _feature_names_from_legacy(features_list: Any) -> list[str]:
    features: list[str] = []
    if isinstance(features_list, list):
        for item in features_list:
            if isinstance(item, str):
                features.append(item)
            elif isinstance(item, dict) and "feature" in item:
                features.append(str(item["feature"]))
    return features


def load_legacy_model_package(path: str | Path) -> LegacyModelPackage:
    model_path = Path(path)
    data = joblib.load(model_path)
    if isinstance(data, dict) and "model" in data:
        return LegacyModelPackage(
            model=data["model"],
            scaler=data.get("scaler"),
            features=_feature_names_from_legacy(data.get("features_list") or data.get("features") or []),
            metrics=dict(data.get("metrics") or {}),
            model_path=model_path,
        )
    return LegacyModelPackage(model=data, scaler=None, features=[], metrics={}, model_path=model_path)


def prepare_features_for_model(df: pd.DataFrame, features: list[str], fill_value: float = 0.0) -> pd.DataFrame:
    if not features:
        return df.select_dtypes(include=[np.number]).copy()
    prepared = pd.DataFrame(index=df.index)
    for feature in features:
        prepared[feature] = df[feature] if feature in df.columns else fill_value
    return prepared.reindex(columns=features)


def check_feature_compatibility(df: pd.DataFrame, features: list[str]) -> tuple[bool, list[str]]:
    missing = [feature for feature in features if feature not in df.columns]
    return len(missing) == 0, missing


def predict_with_bundle(bundle: LoadedModelBundle, df: pd.DataFrame) -> np.ndarray | None:
    X = prepare_features_for_model(df, bundle.features)
    try:
        return bundle.model.predict(X)
    except Exception:
        return None


def predict_with_legacy_package(package: LegacyModelPackage, features_frame: pd.DataFrame) -> dict[str, Any]:
    X = prepare_features_for_model(features_frame, package.features)
    last = X.tail(1).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    values = last.to_numpy()
    if package.scaler is not None:
        values = package.scaler.transform(values)
    prediction = int(package.model.predict(values)[0])
    probability = 0.5
    if hasattr(package.model, "predict_proba"):
        proba = package.model.predict_proba(values)[0]
        probability = float(proba[1] if len(proba) > 1 else proba[0])
    signal = 1 if prediction == 1 else -1
    confidence = probability if prediction == 1 else 1 - probability
    return {
        "prediction": prediction,
        "probability": probability,
        "signal": signal,
        "confidence": confidence,
        "metrics": package.metrics,
        "model_path": str(package.model_path),
    }


class WeightedModelEnsemble:
    def __init__(self, weights: dict[str, float] | None = None):
        self.models: dict[str, Any] = {}
        self.weights = weights or {
            "trend": 0.30,
            "pattern": 0.20,
            "flow": 0.20,
            "volatility": 0.15,
            "sr": 0.15,
        }

    def add_model(self, name: str, model: Any) -> None:
        self.models[name] = model

    def predict(self, X: pd.DataFrame | np.ndarray) -> np.ndarray:
        if not self.models:
            return np.zeros(len(X) if hasattr(X, "__len__") else 1)
        votes = []
        total_weight = 0.0
        for name, model in self.models.items():
            weight = self.weights.get(name, 1.0)
            try:
                if hasattr(model, "votar"):
                    pred = model.votar(X)
                else:
                    pred = model.predict(X)
                votes.append(np.asarray(pred) * weight)
                total_weight += weight
            except Exception:
                continue
        if not votes or total_weight == 0:
            return np.zeros(len(X) if hasattr(X, "__len__") else 1)
        return np.sum(votes, axis=0) / total_weight

    def predict_proba(self, X: pd.DataFrame | np.ndarray) -> np.ndarray:
        probas = []
        total_weight = 0.0
        for name, model in self.models.items():
            if not hasattr(model, "predict_proba"):
                continue
            weight = self.weights.get(name, 1.0)
            try:
                probas.append(model.predict_proba(X) * weight)
                total_weight += weight
            except Exception:
                continue
        if not probas or total_weight == 0:
            return np.array([])
        return np.sum(probas, axis=0) / total_weight


class MultiAssetModelLoader:
    def __init__(self, best_models: dict[str, Any] | None = None, config_path: str | Path | None = None):
        self.best_models = best_models or {}
        self.config_path = Path(config_path) if config_path else None
        self.loaded_models: dict[str, Any] = {}
        if self.config_path is not None:
            with self.config_path.open("r", encoding="utf-8") as fh:
                self.best_models = json.load(fh)

    def list_assets(self) -> list[str]:
        return sorted(self.best_models)

    def get_asset_config(self, asset: str) -> dict[str, Any] | None:
        return self.best_models.get(asset)

    def _model_path_for_asset(self, asset: str) -> Path | None:
        config = self.get_asset_config(asset)
        if not config:
            return None
        for key in ("path", "model_path", "file"):
            if key in config:
                return Path(config[key])
        return None

    def load_model(self, asset: str) -> Any | None:
        if asset in self.loaded_models:
            return self.loaded_models[asset]
        path = self._model_path_for_asset(asset)
        if path is None or not path.exists():
            return None
        model = joblib.load(path)
        self.loaded_models[asset] = model
        return model

    def predict(self, asset: str, features: pd.DataFrame, return_proba: bool = False) -> np.ndarray | None:
        model = self.load_model(asset)
        if model is None or features is None or features.empty:
            return None
        numeric = features.select_dtypes(include=[np.number])
        if numeric.empty:
            return None
        if return_proba and hasattr(model, "predict_proba"):
            return model.predict_proba(numeric)
        prediction = model.predict(numeric)
        return np.asarray(prediction)

    def predict_batch(self, features_by_asset: dict[str, pd.DataFrame], return_proba: bool = False) -> dict[str, np.ndarray | None]:
        return {asset: self.predict(asset, features, return_proba=return_proba) for asset, features in features_by_asset.items()}

    def get_model_info(self) -> pd.DataFrame:
        rows = []
        for asset, config in self.best_models.items():
            row = {"asset": asset}
            if isinstance(config, dict):
                row.update(config)
            rows.append(row)
        return pd.DataFrame(rows)
