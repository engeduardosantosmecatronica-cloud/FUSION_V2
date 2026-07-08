from __future__ import annotations

from dataclasses import dataclass, field

from fusion.decision.schema import EngineOutput, SignalCandidate


@dataclass
class ContextBrainConfig:
    weights: dict[str, float] = field(
        default_factory=lambda: {
            "market_alignment": 0.18,
            "timeframe_consensus": 0.18,
            "macro_flow": 0.16,
            "market_structure": 0.12,
            "market_regime": 0.10,
            "volatility_engine": 0.08,
            "entry_timing": 0.08,
            "execution_engine": 0.08,
            "context_engine": 0.12,
            "consensus_engine": 0.12,
            "opportunity_engine": 0.12,
            "risk_engine": 0.10,
            "portfolio_exposure": 0.08,
            "portfolio_correlation": 0.08,
            "confidence_calibration": 0.08,
            "meta_model_ensemble": 0.08,
            "feature_engineering": 0.06,
        }
    )
    min_brain_score: float = 0.55
    strong_score: float = 0.72
    max_conflict_score: float = 0.35
    structural_engines: tuple[str, ...] = (
        "market_alignment",
        "timeframe_consensus",
        "macro_flow",
        "market_structure",
    )


class ContextBrainEngine:
    name = "context_brain"

    def __init__(self, config: ContextBrainConfig | None = None):
        self.config = config or ContextBrainConfig()

    @staticmethod
    def _bounded(value: float, low: float = 0.0, high: float = 1.0) -> float:
        return max(low, min(high, float(value or 0.0)))

    def evaluate(self, candidate: SignalCandidate, engines: list[EngineOutput]) -> EngineOutput:
        side = candidate.side.upper()
        weighted_total = 0.0
        support_total = 0.0
        conflict_total = 0.0
        structural_conflicts: list[str] = []
        aligned: list[str] = []
        conflicts: list[str] = []
        warnings: list[str] = []
        snapshots: dict[str, dict] = {}

        for engine in engines:
            if engine.engine == self.name:
                continue
            weight = float(self.config.weights.get(engine.engine, 0.04) or 0.04)
            confidence = self._bounded(engine.confidence if engine.confidence else engine.score, 0.0, 1.0)
            effective_weight = weight * max(confidence, 0.25)
            score = self._bounded(engine.score, 0.0, 1.0)
            weighted_total += effective_weight
            support_total += score * effective_weight
            snapshots[engine.engine] = {
                "direction": engine.direction,
                "score": engine.score,
                "confidence": engine.confidence,
                "state": engine.state,
                "positive": engine.positive_factors[:5],
                "negative": engine.negative_factors[:5],
                "warnings": engine.warnings[:5],
            }

            if engine.aligned_with(side):
                aligned.append(engine.engine)
            elif engine.conflicts_with(side):
                conflicts.append(engine.engine)
                conflict_total += effective_weight
                if engine.engine in self.config.structural_engines:
                    structural_conflicts.append(engine.engine)
            warnings.extend(f"{engine.engine}:{item}" for item in engine.warnings[:2])

        model_edge = 0.0
        if side == "BUY":
            model_edge = float(candidate.p_buy or 0.0) - float(candidate.p_sell or 0.0)
        elif side == "SELL":
            model_edge = float(candidate.p_sell or 0.0) - float(candidate.p_buy or 0.0)
        model_support = self._bounded((model_edge + 1.0) / 2.0, 0.0, 1.0)
        model_weight = float(self.config.weights.get("model_probability", 0.10) or 0.10)
        weighted_total += model_weight
        support_total += model_support * model_weight

        if weighted_total <= 0:
            return EngineOutput(
                engine=self.name,
                direction="NEUTRAL",
                score=0.0,
                confidence=0.0,
                state="insufficient_context",
                warnings=["sem_camadas_para_context_brain"],
            )

        brain_score = self._bounded(support_total / weighted_total, 0.0, 1.0)
        conflict_score = self._bounded(conflict_total / weighted_total, 0.0, 1.0)
        confidence = self._bounded(brain_score * (1.0 - min(conflict_score, 0.95)), 0.0, 1.0)
        state = "institutional_aligned"
        direction = side
        negative: list[str] = []
        positive: list[str] = []

        if structural_conflicts:
            state = "structural_conflict"
            direction = "SELL" if side == "BUY" else "BUY" if side == "SELL" else "NEUTRAL"
            negative.append(f"conflito_estrutural:{'+'.join(structural_conflicts)}")
        elif conflict_score > self.config.max_conflict_score:
            state = "mixed_context"
            direction = "SELL" if side == "BUY" else "BUY" if side == "SELL" else "NEUTRAL"
            negative.append(f"contexto_muito_conflitante:{conflict_score:.2f}")
        elif brain_score < self.config.min_brain_score:
            state = "weak_context"
            direction = "NEUTRAL"
            negative.append(f"contexto_fraco:{brain_score:.2f}")
        elif brain_score >= self.config.strong_score and conflict_score <= 0.18:
            state = "strong_institutional_alignment"
            positive.append(f"alinhamento_forte:{side}")
        elif conflicts:
            state = "moderate_alignment"
            warnings.append(f"conflitos_moderados:{'+'.join(conflicts)}")

        if aligned:
            positive.append(f"camadas_alinhadas:{'+'.join(aligned[:8])}")

        final_label = "NEUTRO"
        if direction in {"BUY", "SELL"}:
            if state == "strong_institutional_alignment":
                final_label = f"FORTE {direction}"
            elif state in {"institutional_aligned", "moderate_alignment"}:
                final_label = direction
            else:
                final_label = f"CONTRA_{direction}"

        return EngineOutput(
            engine=self.name,
            direction=direction,
            score=brain_score,
            confidence=confidence,
            state=state,
            positive_factors=positive,
            negative_factors=negative,
            warnings=warnings[:12],
            features={
                "final_label": final_label,
                "brain_score": brain_score,
                "conflict_score": conflict_score,
                "model_edge": model_edge,
                "model_support": model_support,
                "aligned_engines": aligned,
                "conflicting_engines": conflicts,
                "structural_conflicts": structural_conflicts,
                "engine_snapshots": snapshots,
            },
        )
