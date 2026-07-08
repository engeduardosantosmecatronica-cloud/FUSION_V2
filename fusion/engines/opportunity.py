from __future__ import annotations

from dataclasses import dataclass, field

from fusion.decision.schema import EngineOutput, SignalCandidate


@dataclass
class OpportunityConfig:
    weights: dict[str, float] = field(
        default_factory=lambda: {
            "direction_probability": 0.22,
            "consensus_engine": 0.20,
            "entry_timing": 0.16,
            "context_engine": 0.14,
            "confidence_calibration": 0.12,
            "meta_model_ensemble": 0.12,
            "market_structure": 0.08,
            "volatility_engine": 0.05,
            "session_context": 0.03,
        }
    )
    min_tradeability_score: float = 0.55
    marginal_tradeability_score: float = 0.45
    high_quality_score: float = 0.70
    max_conflict_score: float = 0.35
    severe_conflict_penalty: float = 0.18
    warning_penalty: float = 0.03
    negative_penalty: float = 0.06


class OpportunityEngine:
    name = "opportunity_engine"

    def __init__(self, config: OpportunityConfig | None = None):
        self.config = config or OpportunityConfig()

    @staticmethod
    def _engine_by_name(engines: list[EngineOutput]) -> dict[str, EngineOutput]:
        result: dict[str, EngineOutput] = {}
        for engine in engines:
            result[engine.engine] = engine
        return result

    @staticmethod
    def _bounded(value: float, default: float = 0.0) -> float:
        try:
            value = float(value)
        except (TypeError, ValueError):
            return default
        return max(0.0, min(1.0, value))

    @staticmethod
    def _engine_score(engine: EngineOutput | None, default: float = 0.50) -> float:
        if engine is None:
            return default
        return OpportunityEngine._bounded(engine.score, default)

    @staticmethod
    def _engine_confidence(engine: EngineOutput | None, default: float = 0.35) -> float:
        if engine is None:
            return default
        return OpportunityEngine._bounded(engine.confidence or engine.score, default)

    @staticmethod
    def _collect_factors(engine_name: str, engine: EngineOutput | None) -> tuple[list[str], list[str], list[str]]:
        if engine is None:
            return [], [], []
        positives = [f"{engine_name}:{item}" for item in engine.positive_factors[:2]]
        negatives = [f"{engine_name}:{item}" for item in engine.negative_factors[:2]]
        warnings = [f"{engine_name}:{item}" for item in engine.warnings[:2]]
        return positives, negatives, warnings

    def evaluate(self, candidate: SignalCandidate, engines: list[EngineOutput]) -> EngineOutput:
        by_name = self._engine_by_name(engines)
        negative_factors: list[str] = []
        warnings: list[str] = []
        positive_factors: list[str] = []
        components: dict[str, float] = {}

        direction_score = max(0.0, min(1.0, float(candidate.direction_score or 0.0)))
        consensus = by_name.get("consensus_engine")
        context = by_name.get("context_engine")
        entry = by_name.get("entry_timing")
        execution = by_name.get("execution_engine")
        risk = by_name.get("risk_engine")
        calibration = by_name.get("confidence_calibration")
        meta_model = by_name.get("meta_model_ensemble")
        market_structure = by_name.get("market_structure")
        feature_engineering = by_name.get("feature_engineering")
        volatility = by_name.get("volatility_engine")
        session = by_name.get("session_context")
        portfolio = by_name.get("portfolio_exposure")
        correlation = by_name.get("portfolio_correlation")

        execution_score = (
            0.55 * self._engine_score(entry)
            + 0.35 * self._engine_score(execution)
            + 0.10 * self._engine_score(market_structure)
        )
        context_score = (
            0.45 * self._engine_score(context)
            + 0.20 * self._engine_score(volatility)
            + 0.15 * self._engine_score(session)
            + 0.12 * self._engine_score(market_structure)
            + 0.08 * self._engine_score(feature_engineering)
        )
        model_quality_score = (
            0.50 * self._engine_score(meta_model)
            + 0.35 * self._engine_score(calibration)
            + 0.15 * direction_score
        )
        risk_score = (
            0.40 * self._engine_score(risk)
            + 0.35 * self._engine_score(portfolio)
            + 0.25 * self._engine_score(correlation)
        )
        consensus_score = self._engine_score(consensus, default=direction_score)

        components.update(
            {
                "direction_probability": direction_score,
                "execution_score": self._bounded(execution_score),
                "context_score": self._bounded(context_score),
                "model_quality_score": self._bounded(model_quality_score),
                "risk_score": self._bounded(risk_score),
                "consensus_score": self._bounded(consensus_score),
                "entry_timing": self._engine_score(entry),
                "execution_engine": self._engine_score(execution),
                "context_engine": self._engine_score(context),
                "risk_engine": self._engine_score(risk),
                "portfolio_exposure": self._engine_score(portfolio),
                "portfolio_correlation": self._engine_score(correlation),
                "confidence_calibration": self._engine_score(calibration),
                "meta_model_ensemble": self._engine_score(meta_model),
                "market_structure": self._engine_score(market_structure),
                "feature_engineering": self._engine_score(feature_engineering),
                "volatility_engine": self._engine_score(volatility),
                "session_context": self._engine_score(session),
            }
        )

        weighted_total = 0.0
        weighted_score = 0.0

        for name, weight in self.config.weights.items():
            weight = float(weight or 0.0)
            if name == "direction_probability":
                score = direction_score
                confidence = 1.0
            elif name == "execution_score":
                score = components["execution_score"]
                confidence = max(self._engine_confidence(entry), self._engine_confidence(execution))
            elif name == "context_score":
                score = components["context_score"]
                confidence = self._engine_confidence(context)
            elif name == "model_quality_score":
                score = components["model_quality_score"]
                confidence = max(self._engine_confidence(meta_model), self._engine_confidence(calibration))
            elif name == "risk_score":
                score = components["risk_score"]
                confidence = max(self._engine_confidence(risk), self._engine_confidence(portfolio), self._engine_confidence(correlation))
            else:
                engine = by_name.get(name)
                if engine is None:
                    continue
                score = max(0.0, min(1.0, float(engine.score or 0.0)))
                confidence = max(0.0, min(1.0, float(engine.confidence or score or 0.0)))
            effective_weight = weight * (confidence if confidence > 0 else 0.35)
            weighted_total += effective_weight
            weighted_score += score * effective_weight

        for name in (
            "consensus_engine",
            "entry_timing",
            "execution_engine",
            "context_engine",
            "risk_engine",
            "portfolio_exposure",
            "portfolio_correlation",
            "confidence_calibration",
            "meta_model_ensemble",
            "feature_engineering",
            "market_structure",
            "volatility_engine",
            "session_context",
        ):
            pos, neg, warn = self._collect_factors(name, by_name.get(name))
            positive_factors.extend(pos)
            negative_factors.extend(neg)
            warnings.extend(warn)

        if weighted_total <= 0:
            return EngineOutput(
                engine=self.name,
                direction="NEUTRAL",
                score=0.0,
                confidence=0.0,
                state="insufficient_context",
                warnings=["sem_componentes_para_oportunidade"],
            )

        tradeability_score = max(0.0, min(1.0, weighted_score / weighted_total))
        conflict_score = 0.0
        if consensus is not None:
            conflict_score = float(consensus.features.get("conflict_score", 0.0) or 0.0)
        severe_conflict_count = sum(
            1
            for engine in (risk, portfolio, correlation, context, consensus)
            if engine is not None and (engine.conflicts_with(candidate.side) or engine.negative_factors)
        )
        quality_floor = min(
            components["execution_score"],
            components["context_score"],
            components["risk_score"],
            components["model_quality_score"],
        )
        penalty = 0.0
        if severe_conflict_count:
            penalty += min(0.35, severe_conflict_count * self.config.severe_conflict_penalty)
        penalty += min(0.18, len(negative_factors) * self.config.negative_penalty)
        penalty += min(0.09, len(warnings) * self.config.warning_penalty)
        if quality_floor < 0.35:
            penalty += 0.10
            negative_factors.append(f"quality_floor_baixo:{quality_floor:.2f}")
        tradeability_score = max(0.0, min(1.0, tradeability_score - penalty))

        state = "tradable"
        direction = candidate.side.upper()
        confidence = tradeability_score * (1.0 - min(conflict_score, 0.95))

        if conflict_score > self.config.max_conflict_score:
            state = "conflicted"
            direction = "NEUTRAL"
            negative_factors.append(f"conflict_score:{conflict_score:.2f}")
        elif tradeability_score < self.config.marginal_tradeability_score:
            state = "poor"
            direction = "NEUTRAL"
            negative_factors.append(f"tradeability_score:{tradeability_score:.2f}")
        elif tradeability_score < self.config.min_tradeability_score:
            state = "marginal"
            warnings.append(f"tradeability_marginal:{tradeability_score:.2f}")
        elif tradeability_score >= self.config.high_quality_score and severe_conflict_count == 0:
            state = "high_quality"
            positive_factors.append(f"tradeability_alto:{tradeability_score:.2f}")

        return EngineOutput(
            engine=self.name,
            direction=direction,
            score=tradeability_score,
            confidence=max(0.0, min(1.0, confidence)),
            state=state,
            positive_factors=positive_factors[:8],
            negative_factors=negative_factors[:8],
            warnings=warnings[:8],
            features={
                "tradeability_score": tradeability_score,
                "direction_score": direction_score,
                "conflict_score": conflict_score,
                "severe_conflict_count": severe_conflict_count,
                "quality_floor": quality_floor,
                "penalty": penalty,
                "components": components,
            },
        )
