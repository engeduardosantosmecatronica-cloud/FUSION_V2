from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path

import pandas as pd

from fusion.decision.schema import EngineOutput, SignalCandidate


@dataclass
class CalibrationConfig:
    candidates_path: str = "reports/market_structure_calibration/market_structure_calibration_candidates_atr1.5_slatr1_lh100.csv"
    profiles_path: str = "reports/confidence_calibration/confidence_calibration_profiles.json"
    min_samples: int = 300
    min_rules: int = 2
    raw_weight: float = 0.50
    history_weight: float = 0.50
    prior_samples: int = 200
    min_reliability: float = 0.45
    use_profiles: bool = True


class ConfidenceCalibrationEngine:
    name = "confidence_calibration"

    def __init__(self, config: CalibrationConfig | None = None):
        self.config = config or CalibrationConfig()
        self._profiles: dict[tuple[str, str, str], dict] | None = None
        self._fallback_profiles: dict[tuple[str, str, str], dict] | None = None

    def _load_profile_json(self) -> tuple[dict[tuple[str, str, str], dict], dict[tuple[str, str, str], dict]]:
        path = Path(self.config.profiles_path)
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists():
            return {}, {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}, {}
        exact: dict[tuple[str, str, str], dict] = {}
        fallback: dict[tuple[str, str, str], dict] = {}
        for item in payload.get("profiles", []):
            key = (
                str(item.get("symbol", "") or "").upper(),
                str(item.get("timeframe", "") or "").upper(),
                str(item.get("side", "") or "").lower(),
            )
            exact[key] = dict(item)
        for item in payload.get("fallback_profiles", []):
            key = (
                str(item.get("symbol", "") or "*").upper(),
                str(item.get("timeframe", "") or "*").upper(),
                str(item.get("side", "") or "").lower(),
            )
            fallback[key] = dict(item)
        return exact, fallback

    def _load_profiles(self) -> dict[tuple[str, str, str], dict]:
        if self._profiles is not None:
            return self._profiles
        if self.config.use_profiles:
            exact, fallback = self._load_profile_json()
            if exact:
                self._profiles = exact
                self._fallback_profiles = fallback
                return self._profiles
        path = Path(self.config.candidates_path)
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists():
            self._profiles = {}
            return self._profiles
        frame = pd.read_csv(path)
        if frame.empty:
            self._profiles = {}
            return self._profiles
        frame["symbol"] = frame["symbol"].astype(str).str.upper()
        frame["timeframe"] = frame["timeframe"].astype(str).str.upper()
        frame["side"] = frame["side"].astype(str).str.lower()
        grouped = (
            frame.groupby(["symbol", "timeframe", "side"])
            .agg(
                rules=("feature", "count"),
                total_samples=("samples", "sum"),
                avg_win_rate=("win_rate", "mean"),
                max_win_rate=("win_rate", "max"),
                avg_edge=("edge_score", "mean"),
                max_edge=("edge_score", "max"),
            )
            .reset_index()
        )
        self._profiles = {
            (row.symbol, row.timeframe, row.side): {
                "rules": int(row.rules),
                "total_samples": int(row.total_samples),
                "avg_win_rate": float(row.avg_win_rate),
                "max_win_rate": float(row.max_win_rate),
                "avg_edge": float(row.avg_edge),
                "max_edge": float(row.max_edge),
            }
            for row in grouped.itertuples(index=False)
        }
        return self._profiles

    def _fallback_profile(self, symbol: str, timeframe: str, side_key: str) -> dict | None:
        if self._fallback_profiles is None:
            self._fallback_profiles = {}
        keys = [
            (symbol.upper(), "*", side_key),
            ("*", timeframe.upper(), side_key),
            ("*", "*", side_key),
        ]
        for key in keys:
            profile = self._fallback_profiles.get(key)
            if profile:
                return profile
        return None

    @staticmethod
    def _profile_value(profile: dict, *keys: str, default: float = 0.0) -> float:
        for key in keys:
            if key in profile:
                try:
                    return float(profile.get(key))
                except (TypeError, ValueError):
                    return default
        return default

    def evaluate(self, candidate: SignalCandidate) -> EngineOutput:
        side = candidate.side.upper()
        side_key = "buy" if side == "BUY" else "sell" if side == "SELL" else "neutral"
        raw_probability = candidate.direction_score
        profiles = self._load_profiles()
        exact_key = (candidate.symbol.upper(), candidate.timeframe.upper(), side_key)
        profile = profiles.get(exact_key)
        profile_source = "exact"
        if not profile:
            profile = self._fallback_profile(candidate.symbol.upper(), candidate.timeframe.upper(), side_key)
            profile_source = "fallback" if profile else "none"
        if not profile:
            return EngineOutput(
                engine=self.name,
                direction="NEUTRAL",
                score=raw_probability,
                confidence=0.25,
                state="no_profile",
                warnings=["sem_perfil_calibracao"],
                features={"raw_probability": raw_probability},
            )

        total_samples = int(self._profile_value(profile, "total_samples", "samples", default=0.0))
        rules = int(self._profile_value(profile, "rules", "feature_count", default=0.0))
        enough = total_samples >= self.config.min_samples and rules >= self.config.min_rules
        historical = max(
            0.0,
            min(
                1.0,
                self._profile_value(profile, "posterior_probability", "avg_win_rate", "weighted_win_rate", default=raw_probability),
            ),
        )
        reliability = max(
            0.0,
            min(1.0, self._profile_value(profile, "reliability_score", "wilson_lower", default=0.45 if enough else 0.25)),
        )
        total_weight = max(1e-9, self.config.raw_weight + self.config.history_weight)
        calibrated = ((self.config.raw_weight * raw_probability) + (self.config.history_weight * historical)) / total_weight
        calibrated = max(0.0, min(1.0, calibrated))
        conservative = min(calibrated, max(historical, reliability + 0.10))
        if reliability < self.config.min_reliability:
            calibrated = (calibrated + conservative) / 2.0
        negative = ["probabilidade_calibrada_menor"] if calibrated < raw_probability else []
        positive = ["probabilidade_calibrada_melhor_ou_igual"] if calibrated >= raw_probability else []
        direction = side if calibrated >= raw_probability else "SELL" if side == "BUY" else "BUY" if side == "SELL" else "NEUTRAL"
        state = "calibrated" if enough and profile_source == "exact" else "weak_profile"
        if profile_source == "fallback":
            state = "fallback_profile"
        if reliability < self.config.min_reliability:
            state = "low_reliability"
            negative.append("perfil_baixa_confiabilidade")
        return EngineOutput(
            engine=self.name,
            direction=direction,
            score=calibrated,
            confidence=max(0.25, min(0.90, reliability if enough else reliability * 0.75)),
            state=state,
            positive_factors=positive,
            negative_factors=negative,
            warnings=[] if enough and reliability >= self.config.min_reliability else ["perfil_calibracao_fraco"],
            features={
                "raw_probability": raw_probability,
                "historical_probability": historical,
                "calibrated_probability": calibrated,
                "reliability_score": reliability,
                "profile_source": profile_source,
                "profile": profile,
            },
        )
