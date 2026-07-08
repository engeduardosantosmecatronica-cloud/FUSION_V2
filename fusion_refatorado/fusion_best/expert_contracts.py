from __future__ import annotations

import hashlib
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class ExpertRunResult:
    signal: float
    confidence: float
    expert: str
    version: str
    timestamp: Any = None
    features: dict[str, float] = field(default_factory=dict)
    computation_time: float = 0.0
    error: str | None = None


class ExpertContract(ABC):
    """Small, dependency-light contract distilled from OMNIS_Copia BaseExpert."""

    def __init__(
        self,
        name: str,
        version: str = "1.0.0",
        description: str = "",
        cache_size: int = 32,
        validate_inputs: bool = True,
    ):
        self.name = name
        self.version = version
        self.description = description
        self.validate_inputs = validate_inputs
        self._cache_size = max(0, cache_size)
        self._cache: dict[str, pd.DataFrame] = {}
        self._cache_order: list[str] = []
        self.stats: dict[str, Any] = {
            "calls": 0,
            "errors": 0,
            "last_call": None,
            "avg_computation_time": 0.0,
        }

    @abstractmethod
    def calculate_features(self, frame: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError

    @abstractmethod
    def get_signal(self, features: pd.DataFrame) -> float:
        raise NotImplementedError

    @abstractmethod
    def get_confidence(self, features: pd.DataFrame) -> float:
        raise NotImplementedError

    def get_features_list(self) -> list[str]:
        return []

    def validate_data(self, frame: pd.DataFrame, min_periods: int = 10) -> bool:
        if frame is None or len(frame) < min_periods:
            return False
        required = {"open", "high", "low", "close"}
        return required.issubset(frame.columns)

    def run(self, frame: pd.DataFrame) -> ExpertRunResult:
        start = time.time()
        self.stats["calls"] += 1
        self.stats["last_call"] = datetime.now(timezone.utc).isoformat()
        try:
            if self.validate_inputs and not self.validate_data(frame):
                return self._error_result("Dados insuficientes ou colunas OHLC ausentes")
            cache_key = self._cache_key(frame)
            if cache_key in self._cache:
                features = self._cache[cache_key].copy()
                self._touch_cache_key(cache_key)
            else:
                features = self.calculate_features(frame.copy())
                self._add_cache(cache_key, features)
            elapsed = time.time() - start
            self.stats["avg_computation_time"] = self.stats["avg_computation_time"] * 0.95 + elapsed * 0.05
            timestamp = frame.index[-1] if isinstance(frame.index, pd.DatetimeIndex) and len(frame) else None
            return ExpertRunResult(
                signal=float(np.clip(self.get_signal(features), -1, 1)),
                confidence=float(np.clip(self.get_confidence(features), 0, 1)),
                expert=self.name,
                version=self.version,
                timestamp=timestamp,
                features=self._last_features(features),
                computation_time=elapsed,
            )
        except Exception as exc:
            self.stats["errors"] += 1
            return self._error_result(str(exc))

    def __call__(self, frame: pd.DataFrame) -> ExpertRunResult:
        return self.run(frame)

    def _error_result(self, message: str) -> ExpertRunResult:
        return ExpertRunResult(
            signal=0.0,
            confidence=0.0,
            expert=self.name,
            version=self.version,
            error=message,
        )

    def _cache_key(self, frame: pd.DataFrame) -> str:
        if frame.empty:
            return f"{self.name}:{self.version}:empty"
        cols = [col for col in ("open", "high", "low", "close") if col in frame.columns]
        recent = frame[cols].tail(10).to_numpy(dtype=float, copy=True)
        digest = hashlib.md5(recent.tobytes()).hexdigest()
        return f"{self.name}:{self.version}:{digest}"

    def _add_cache(self, key: str, value: pd.DataFrame) -> None:
        if self._cache_size <= 0:
            return
        if len(self._cache_order) >= self._cache_size:
            oldest = self._cache_order.pop(0)
            self._cache.pop(oldest, None)
        self._cache[key] = value.copy()
        self._cache_order.append(key)

    def _touch_cache_key(self, key: str) -> None:
        if key in self._cache_order:
            self._cache_order.remove(key)
            self._cache_order.append(key)

    def _last_features(self, frame: pd.DataFrame) -> dict[str, float]:
        if frame.empty:
            return {}
        last = frame.iloc[-1]
        names = self.get_features_list() or list(frame.columns)
        output: dict[str, float] = {}
        for name in names:
            if name not in last:
                continue
            value = last[name]
            if pd.notna(value) and np.isfinite(value):
                output[name] = float(value)
        return output

