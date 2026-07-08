from __future__ import annotations

from dataclasses import dataclass

from fusion.decision.schema import DecisionResult, EngineOutput, SignalCandidate


@dataclass
class DecisionPolicy:
    min_tradeability_score: float = 0.55
    max_conflict_score: float = 0.40
    reduce_size_conflict_score: float = 0.25
    neutral_engine_penalty: float = 0.10

    def combine(self, candidate: SignalCandidate, engines: list[EngineOutput]) -> DecisionResult:
        if not engines:
            base = candidate.direction_score
            decision = "ALLOW" if base >= self.min_tradeability_score else "BLOCK"
            reason = "sem_engines" if decision == "ALLOW" else "probabilidade_baixa"
            return DecisionResult(
                decision=decision,
                reason=reason,
                consensus_score=base,
                conflict_score=0.0,
                tradeability_score=base,
            )

        total_weight = 0.0
        aligned_weight = 0.0
        conflict_weight = 0.0
        weighted_score = 0.0
        positives: list[str] = []
        negatives: list[str] = []
        warnings: list[str] = []

        for engine in engines:
            confidence = max(0.0, min(1.0, float(engine.confidence or abs(engine.score) or 0.0)))
            weight = confidence if confidence > 0 else 0.25
            total_weight += weight
            weighted_score += max(0.0, min(1.0, float(engine.score))) * weight
            positives.extend(f"{engine.engine}:{item}" for item in engine.positive_factors)
            negatives.extend(f"{engine.engine}:{item}" for item in engine.negative_factors)
            warnings.extend(f"{engine.engine}:{item}" for item in engine.warnings)
            if engine.conflicts_with(candidate.side):
                conflict_weight += weight
                negatives.append(f"{engine.engine}:direcao_conflitante:{engine.direction}")
            elif engine.aligned_with(candidate.side):
                aligned_weight += weight
                if engine.direction.upper() == candidate.side.upper():
                    positives.append(f"{engine.engine}:alinhado:{engine.direction}")

        if total_weight <= 0:
            total_weight = 1.0
        engine_score = weighted_score / total_weight
        consensus_score = aligned_weight / total_weight
        conflict_score = conflict_weight / total_weight
        tradeability_score = (
            0.45 * candidate.direction_score
            + 0.35 * engine_score
            + 0.20 * consensus_score
            - 0.30 * conflict_score
        )
        tradeability_score = max(0.0, min(1.0, tradeability_score))

        decision = "ALLOW"
        reason = "ok"
        position_multiplier = 1.0
        if conflict_score > self.max_conflict_score:
            decision = "BLOCK"
            reason = "conflito_alto"
        elif tradeability_score < self.min_tradeability_score:
            decision = "BLOCK"
            reason = "tradeability_baixo"
        elif conflict_score > self.reduce_size_conflict_score:
            position_multiplier = 0.5
            reason = "conflito_moderado"

        return DecisionResult(
            decision=decision,
            reason=reason,
            consensus_score=consensus_score,
            conflict_score=conflict_score,
            tradeability_score=tradeability_score,
            position_multiplier=position_multiplier,
            positive_factors=positives,
            negative_factors=negatives,
            warnings=warnings,
        )
