from __future__ import annotations

from dataclasses import dataclass, field

from fusion.decision.schema import EngineOutput, SignalCandidate


@dataclass
class ContextEngineConfig:
    weights: dict[str, float] = field(
        default_factory=lambda: {
            "market_regime": 0.18,
            "volatility_engine": 0.10,
            "session_context": 0.10,
            "macro_flow": 0.20,
            "portfolio_exposure": 0.14,
            "portfolio_correlation": 0.14,
            "meta_model_ensemble": 0.10,
            "feature_engineering": 0.08,
            "market_structure": 0.08,
            "candle_price": 0.06,
            "ema_alignment": 0.06,
        }
    )
    min_context_score: float = 0.55
    max_context_conflict: float = 0.35


class ContextEngine:
    name = "context_engine"

    def __init__(self, config: ContextEngineConfig | None = None):
        self.config = config or ContextEngineConfig()

    def evaluate(self, candidate: SignalCandidate, engines: list[EngineOutput]) -> EngineOutput:
        side = candidate.side.upper()
        weighted_total = 0.0
        weighted_score = 0.0
        conflict_total = 0.0
        aligned: list[str] = []
        conflicts: list[str] = []
        warnings: list[str] = []
        features: dict[str, dict] = {}

        for engine in engines:
            if engine.engine == self.name:
                continue
            weight = float(self.config.weights.get(engine.engine, 0.05) or 0.05)
            confidence = max(0.0, min(1.0, float(engine.confidence or engine.score or 0.0)))
            effective_weight = weight * (confidence if confidence > 0 else 0.35)
            score = max(0.0, min(1.0, float(engine.score or 0.0)))
            weighted_total += effective_weight
            weighted_score += score * effective_weight
            features[engine.engine] = {
                "direction": engine.direction,
                "score": engine.score,
                "confidence": engine.confidence,
                "state": engine.state,
            }
            if engine.aligned_with(side):
                aligned.append(engine.engine)
            elif engine.conflicts_with(side):
                conflicts.append(engine.engine)
                conflict_total += effective_weight
            warnings.extend(f"{engine.engine}:{item}" for item in engine.warnings[:3])

        if weighted_total <= 0:
            return EngineOutput(
                engine=self.name,
                direction="NEUTRAL",
                score=0.0,
                confidence=0.0,
                state="insufficient_context",
                warnings=["sem_engines_para_contexto"],
            )

        context_score = max(0.0, min(1.0, weighted_score / weighted_total))
        conflict_score = max(0.0, min(1.0, conflict_total / weighted_total))
        state = "favorable"
        direction = side
        positive = [f"alinhados:{'+'.join(aligned)}"] if aligned else []
        negative = []

        if conflict_score > self.config.max_context_conflict:
            state = "conflicted"
            direction = "SELL" if side == "BUY" else "BUY" if side == "SELL" else "NEUTRAL"
            negative.append(f"contexto_conflitante:{'+'.join(conflicts)}")
        elif context_score < self.config.min_context_score:
            state = "weak"
            direction = "NEUTRAL"
            negative.append(f"contexto_fraco:{context_score:.2f}")
        elif conflicts:
            state = "mixed"
            warnings.append(f"conflitos_moderados:{'+'.join(conflicts)}")

        return EngineOutput(
            engine=self.name,
            direction=direction,
            score=context_score,
            confidence=max(0.0, min(1.0, 1.0 - conflict_score)),
            state=state,
            positive_factors=positive,
            negative_factors=negative,
            warnings=warnings[:12],
            features={
                "context_score": context_score,
                "context_conflict_score": conflict_score,
                "aligned_engines": aligned,
                "conflicting_engines": conflicts,
                "engine_snapshots": features,
            },
        )
