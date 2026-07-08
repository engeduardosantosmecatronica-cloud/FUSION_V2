from __future__ import annotations

from dataclasses import dataclass, field

from fusion.decision.schema import EngineOutput, SignalCandidate


@dataclass
class ConsensusConfig:
    weights: dict[str, float] = field(
        default_factory=lambda: {
            "market_briefing": 0.12,
            "market_regime": 0.14,
            "volatility_engine": 0.10,
            "session_context": 0.08,
            "macro_flow": 0.16,
            "portfolio_exposure": 0.10,
            "portfolio_correlation": 0.12,
            "market_structure": 0.08,
            "entry_timing": 0.12,
            "candle_price": 0.08,
            "ema_alignment": 0.08,
            "context_engine": 0.16,
            "confidence_calibration": 0.10,
            "meta_model_ensemble": 0.12,
            "feature_engineering": 0.08,
        }
    )
    min_consensus_score: float = 0.55
    max_conflict_score: float = 0.35
    weak_score_floor: float = 0.40


class ConsensusEngine:
    name = "consensus_engine"

    def __init__(self, config: ConsensusConfig | None = None):
        self.config = config or ConsensusConfig()

    def evaluate(self, candidate: SignalCandidate, engines: list[EngineOutput]) -> EngineOutput:
        side = candidate.side.upper()
        total_weight = 0.0
        support_weight = 0.0
        conflict_weight = 0.0
        warning_weight = 0.0
        aligned: list[str] = []
        conflicts: list[str] = []
        warnings: list[str] = []
        snapshots: dict[str, dict] = {}

        for engine in engines:
            if engine.engine == self.name:
                continue
            weight = float(self.config.weights.get(engine.engine, 0.05) or 0.05)
            confidence = max(0.0, min(1.0, float(engine.confidence or engine.score or 0.0)))
            effective_weight = weight * (confidence if confidence > 0 else 0.35)
            score = max(0.0, min(1.0, float(engine.score or 0.0)))
            total_weight += effective_weight
            snapshots[engine.engine] = {
                "direction": engine.direction,
                "score": engine.score,
                "confidence": engine.confidence,
                "state": engine.state,
                "negative_factors": engine.negative_factors[:4],
                "warnings": engine.warnings[:4],
            }

            if engine.aligned_with(side):
                aligned.append(engine.engine)
                support_weight += effective_weight * max(score, 0.50)
            elif engine.conflicts_with(side):
                conflicts.append(engine.engine)
                conflict_weight += effective_weight * max(score, 0.50)
            elif engine.negative_factors:
                warnings.append(engine.engine)
                warning_weight += effective_weight * 0.50
            elif engine.warnings:
                warnings.append(engine.engine)
                warning_weight += effective_weight * 0.25
                support_weight += effective_weight * min(score, 0.50)
            else:
                support_weight += effective_weight * min(score, 0.50)

        if total_weight <= 0:
            return EngineOutput(
                engine=self.name,
                direction="NEUTRAL",
                score=0.0,
                confidence=0.0,
                state="insufficient_engines",
                warnings=["sem_engines_para_consenso"],
            )

        consensus_score = max(0.0, min(1.0, support_weight / total_weight))
        conflict_score = max(0.0, min(1.0, (conflict_weight + warning_weight) / total_weight))
        confidence = max(0.0, min(1.0, consensus_score * (1.0 - min(conflict_score, 0.95))))

        state = "strong_consensus"
        direction = side
        positive_factors = []
        negative_factors = []
        engine_warnings = []

        if aligned:
            positive_factors.append(f"aligned:{'+'.join(aligned)}")
        if conflicts:
            negative_factors.append(f"conflicts:{'+'.join(conflicts)}")
        if warnings:
            engine_warnings.append(f"warnings:{'+'.join(warnings)}")

        if conflict_score > self.config.max_conflict_score:
            state = "conflicted"
            direction = "NEUTRAL"
            negative_factors.append(f"conflict_score:{conflict_score:.2f}")
        elif consensus_score < self.config.weak_score_floor:
            state = "weak"
            direction = "NEUTRAL"
            negative_factors.append(f"consensus_score:{consensus_score:.2f}")
        elif consensus_score < self.config.min_consensus_score:
            state = "moderate"
            engine_warnings.append(f"consensus_moderado:{consensus_score:.2f}")

        return EngineOutput(
            engine=self.name,
            direction=direction,
            score=consensus_score,
            confidence=confidence,
            state=state,
            positive_factors=positive_factors,
            negative_factors=negative_factors,
            warnings=engine_warnings[:8],
            features={
                "consensus_score": consensus_score,
                "conflict_score": conflict_score,
                "support_weight": support_weight,
                "conflict_weight": conflict_weight,
                "warning_weight": warning_weight,
                "total_weight": total_weight,
                "aligned_engines": aligned,
                "conflicting_engines": conflicts,
                "warning_engines": warnings,
                "engine_snapshots": snapshots,
            },
        )
