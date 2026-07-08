from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from .model_io import LegacyModelPackage, load_legacy_model_package, predict_with_legacy_package


@dataclass
class ModelVote:
    name: str
    signal: int
    confidence: float
    probability: float
    weight: float
    metrics: dict[str, Any]


class LegacyAucEnsemble:
    def __init__(self, packages: Iterable[LegacyModelPackage], min_confidence: float = 0.52):
        self.packages = list(packages)
        self.min_confidence = min_confidence

    @classmethod
    def from_paths(cls, paths: Iterable[str | Path], min_confidence: float = 0.52) -> "LegacyAucEnsemble":
        return cls([load_legacy_model_package(path) for path in paths], min_confidence=min_confidence)

    def predict(self, features_frame: pd.DataFrame) -> dict[str, Any]:
        votes: list[ModelVote] = []
        for package in self.packages:
            result = predict_with_legacy_package(package, features_frame)
            confidence = float(result["confidence"])
            if confidence < self.min_confidence:
                continue
            auc = float(package.metrics.get("auc") or package.metrics.get("AUC") or 0.5)
            weight = max(auc, 0.01)
            votes.append(
                ModelVote(
                    name=Path(package.model_path).stem,
                    signal=int(result["signal"]),
                    confidence=confidence,
                    probability=float(result["probability"]),
                    weight=weight,
                    metrics=package.metrics,
                )
            )
        if not votes:
            return {
                "signal": 0,
                "confidence": 0.0,
                "weighted_signal": 0.0,
                "votes": [],
                "error": "no_votes",
            }
        total_weight = sum(vote.weight for vote in votes)
        weighted_signal = sum(vote.signal * vote.confidence * vote.weight for vote in votes) / total_weight
        avg_confidence = float(np.average([vote.confidence for vote in votes], weights=[vote.weight for vote in votes]))
        if weighted_signal > 0.60:
            signal = 2
        elif weighted_signal > 0.20:
            signal = 1
        elif weighted_signal < -0.60:
            signal = -2
        elif weighted_signal < -0.20:
            signal = -1
        else:
            signal = 0
        return {
            "signal": signal,
            "confidence": avg_confidence,
            "weighted_signal": float(weighted_signal),
            "votes": [vote.__dict__ for vote in votes],
            "error": None,
        }


def top_model_paths_from_manifest(manifest_path: str | Path, models_dir: str | Path, top_n: int = 5) -> list[Path]:
    manifest = pd.read_csv(manifest_path)
    ranked = manifest.sort_values(["auc", "f1", "accuracy"], ascending=[False, False, False]).head(top_n)
    root = Path(models_dir)
    return [root / str(row["file_name"]) for _, row in ranked.iterrows()]
