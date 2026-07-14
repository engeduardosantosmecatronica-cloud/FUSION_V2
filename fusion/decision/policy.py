from __future__ import annotations

from dataclasses import dataclass

from fusion.decision.schema import DecisionResult, EngineOutput, SignalCandidate


@dataclass
class DecisionPolicy:
    min_tradeability_score: float = 0.55
    max_conflict_score: float = 0.40
    reduce_size_conflict_score: float = 0.25
    neutral_engine_penalty: float = 0.10
    min_direction_score: float = 0.60
    macro_alignment_guard_enabled: bool = True
    macro_alignment_min_tradeability: float = 0.60
    macro_alignment_min_consensus: float = 0.45
    losing_positions_guard_enabled: bool = True
    losing_positions_min_tradeability: float = 0.68
    extreme_breakout_guard_enabled: bool = True
    extreme_breakout_min_tradeability: float = 0.68
    extreme_breakout_min_consensus: float = 0.55
    stale_data_guard_enabled: bool = True
    fragile_structure_guard_enabled: bool = True
    fragile_structure_min_tradeability: float = 0.70
    fragile_structure_min_consensus: float = 0.50

    @staticmethod
    def _has_factor(factors: list[str], *needles: str) -> bool:
        return any(all(needle in factor for needle in needles) for factor in factors)

    def _quality_block_reason(
        self,
        candidate: SignalCandidate,
        consensus_score: float,
        tradeability_score: float,
        positives: list[str],
        negatives: list[str],
        warnings: list[str],
    ) -> str:
        if candidate.direction_score < self.min_direction_score:
            return "probabilidade_direcional_baixa"

        if self.macro_alignment_guard_enabled:
            macro_against = self._has_factor(negatives, "macro_flow:", "contra") or self._has_factor(
                negatives, "macro_flow:", "direcao_conflitante"
            )
            alignment_against = self._has_factor(negatives, "market_alignment:", "contra") or self._has_factor(
                negatives, "market_alignment:", "direcao_conflitante"
            )
            if macro_against and alignment_against:
                if (
                    tradeability_score < self.macro_alignment_min_tradeability
                    or consensus_score < self.macro_alignment_min_consensus
                ):
                    return "macro_e_estrutura_contra_sem_score_forte"

        if self.losing_positions_guard_enabled:
            losing_risk = (
                self._has_factor(negatives, "risk_engine:muitas_posicoes_negativas")
                or self._has_factor(negatives, "opportunity_engine:risk_engine:muitas_posicoes_negativas")
                or self._has_factor(warnings, "portfolio_exposure:posicoes_negativas")
                or self._has_factor(warnings, "context_engine:portfolio_exposure:posicoes_negativas")
            )
            if losing_risk and tradeability_score < self.losing_positions_min_tradeability:
                return "muitas_posicoes_negativas_exige_oportunidade_forte"

        all_factors = positives + negatives + warnings
        if self.stale_data_guard_enabled:
            stale_data = (
                self._has_factor(all_factors, "stale")
                or self._has_factor(all_factors, "feed_stale")
                or self._has_factor(all_factors, "candle_antigo")
                or self._has_factor(all_factors, "dados_desatualizados")
            )
            if stale_data:
                return "dados_de_mercado_desatualizados"

        if self.fragile_structure_guard_enabled:
            fragile_structure = (
                self._has_factor(all_factors, "market_structure:shadow", "consolidacao")
                or self._has_factor(all_factors, "market_structure:shadow", "compressao")
                or self._has_factor(all_factors, "market_structure:shadow", "estrutura_fraca")
                or self._has_factor(all_factors, "market_structure:shadow", "vol_baixa")
            )
            weak_execution = (
                self._has_factor(all_factors, "execution_engine:volume_execucao_baixo")
                or self._has_factor(all_factors, "execution_engine:range_intrabar_fraco")
                or self._has_factor(all_factors, "execution_engine:corpo_fraco")
            )
            if fragile_structure and (
                weak_execution
                or tradeability_score < self.fragile_structure_min_tradeability
                or consensus_score < self.fragile_structure_min_consensus
            ):
                return "estrutura_shadow_fraca_sem_confirmacao"

        if self.extreme_breakout_guard_enabled:
            extreme_breakout = self._has_factor(positives, "entry_timing:", "fundo_permitida_por_bos_ou_breakout") or self._has_factor(
                positives, "entry_timing:", "topo_permitida_por_bos_ou_breakout"
            )
            if extreme_breakout:
                if (
                    tradeability_score < self.extreme_breakout_min_tradeability
                    or consensus_score < self.extreme_breakout_min_consensus
                ):
                    return "rompimento_em_extremo_sem_confirmacao_forte"

        return ""

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
        quality_block = self._quality_block_reason(
            candidate,
            consensus_score,
            tradeability_score,
            positives,
            negatives,
            warnings,
        )
        if quality_block:
            decision = "BLOCK"
            reason = quality_block
        elif conflict_score > self.max_conflict_score:
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
