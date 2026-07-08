from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from fusion.decision.schema import EngineOutput
from fusion.features.market_structure import MarketStructureConfig, build_market_structure_features


@dataclass
class FeatureEngineeringConfig:
    bars: int = 260
    min_feature_coverage: float = 0.72
    min_family_coverage: float = 0.60
    max_nan_critical: int = 3
    critical_features: tuple[str, ...] = (
        "range_to_atr",
        "volume_ratio",
        "body_to_range",
        "close_position",
        "ema_alignment_buy",
        "ema_alignment_sell",
        "institutional_structure_score",
        "kaufman_er_10",
        "overlap_ratio_10",
    )
    feature_families: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: {
            "candle_anatomy": (
                "body_to_range",
                "upper_wick_to_range",
                "lower_wick_to_range",
                "close_position",
                "movement_efficiency",
            ),
            "volatility": (
                "atr",
                "range_to_atr",
                "atr_ratio_5_50",
                "range_zscore_20",
                "volatility_compression",
                "volatility_expansion",
            ),
            "volume_microstructure": (
                "volume_ratio",
                "volume_zscore",
                "delta_proxy",
                "pressure_imbalance",
                "effort_result",
                "absorption",
            ),
            "trend_momentum": (
                "ema_alignment_buy",
                "ema_alignment_sell",
                "ema21_slope_atr",
                "velocity_atr_5",
                "velocity_atr_10",
                "acceleration_5",
            ),
            "structure": (
                "break_of_structure_up",
                "break_of_structure_down",
                "change_of_character_up",
                "change_of_character_down",
                "liquidity_grab_up",
                "liquidity_grab_down",
                "institutional_structure_score",
            ),
            "statistical": (
                "log_ret",
                "skew_20",
                "kurtosis_20",
                "entropy_20",
                "kaufman_er_20",
                "overlap_ratio_20",
            ),
            "temporal": (
                "hour",
                "minute",
                "day_of_week",
                "bars_since_breakout_up",
                "bars_since_breakout_down",
                "bars_since_volume_climax",
            ),
        }
    )


class FeatureEngineeringEngine:
    name = "feature_engineering"

    def __init__(self, config: FeatureEngineeringConfig | None = None):
        self.config = config or FeatureEngineeringConfig()

    @staticmethod
    def _is_valid(value) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return value != ""
        try:
            return bool(np.isfinite(float(value)))
        except (TypeError, ValueError):
            return not pd.isna(value)

    def evaluate(self, df: pd.DataFrame) -> EngineOutput:
        if df is None or df.empty or len(df) < 80:
            return EngineOutput(
                engine=self.name,
                direction="NEUTRAL",
                score=0.0,
                confidence=0.0,
                state="insufficient_data",
                warnings=["dados_insuficientes"],
            )

        features = build_market_structure_features(
            df.tail(max(90, self.config.bars)),
            MarketStructureConfig(),
            include_raw_ohlcv=False,
        )
        if features.empty:
            return EngineOutput(
                engine=self.name,
                direction="NEUTRAL",
                score=0.0,
                confidence=0.0,
                state="insufficient_features",
                warnings=["features_vazias"],
            )

        row = features.tail(1).iloc[0]
        numeric_cols = list(features.select_dtypes(include=[np.number]).columns)
        valid_numeric = sum(self._is_valid(row.get(col)) for col in numeric_cols)
        feature_coverage = valid_numeric / max(1, len(numeric_cols))

        family_scores: dict[str, float] = {}
        missing_by_family: dict[str, list[str]] = {}
        for family, columns in self.config.feature_families.items():
            present = [col for col in columns if col in features.columns]
            valid = [col for col in present if self._is_valid(row.get(col))]
            family_scores[family] = len(valid) / max(1, len(columns))
            missing_by_family[family] = [col for col in columns if col not in valid]

        critical_missing = [
            col
            for col in self.config.critical_features
            if col not in features.columns or not self._is_valid(row.get(col))
        ]
        weak_families = [
            family
            for family, score in family_scores.items()
            if score < self.config.min_family_coverage
        ]
        warnings: list[str] = []
        negative: list[str] = []
        positive: list[str] = []

        anomaly_flags = []
        for col in (
            "volume_climax",
            "absorption",
            "empty_market_move",
            "stop_hunt_up",
            "stop_hunt_down",
            "volatility_compression",
            "volatility_expansion",
            "structure_transition",
            "regime_reversal_risk",
        ):
            try:
                if int(float(row.get(col, 0) or 0)) == 1:
                    anomaly_flags.append(col)
            except (TypeError, ValueError):
                continue
        if anomaly_flags:
            warnings.append("feature_anomalies:" + "+".join(anomaly_flags[:5]))

        if feature_coverage < self.config.min_feature_coverage:
            negative.append(f"feature_coverage_baixa:{feature_coverage:.2f}")
        if len(critical_missing) > self.config.max_nan_critical:
            negative.append(f"critical_features_missing:{len(critical_missing)}")
        if weak_families:
            warnings.append("familias_fracas:" + "+".join(weak_families[:4]))
        if not negative:
            positive.append("feature_quality_ok")

        family_floor = min(family_scores.values(), default=0.0)
        critical_score = 1.0 - (len(critical_missing) / max(1, len(self.config.critical_features)))
        score = (0.50 * feature_coverage) + (0.30 * family_floor) + (0.20 * critical_score)
        if anomaly_flags:
            score -= 0.03 * min(3, len(anomaly_flags))
        score = max(0.0, min(1.0, score))

        state = "feature_quality_ok"
        if negative:
            state = "feature_quality_weak"
        elif anomaly_flags:
            state = "feature_anomaly_context"

        return EngineOutput(
            engine=self.name,
            direction="NEUTRAL",
            score=score,
            confidence=max(0.20, min(0.90, feature_coverage)),
            state=state,
            positive_factors=positive,
            negative_factors=negative,
            warnings=warnings[:8],
            features={
                "feature_coverage": feature_coverage,
                "numeric_feature_count": len(numeric_cols),
                "valid_numeric_feature_count": valid_numeric,
                "family_scores": family_scores,
                "family_floor": family_floor,
                "weak_families": weak_families,
                "critical_missing": critical_missing,
                "critical_score": critical_score,
                "anomaly_flags": anomaly_flags,
                "latest_feature_time": str(row.get("time", "")),
            },
        )
