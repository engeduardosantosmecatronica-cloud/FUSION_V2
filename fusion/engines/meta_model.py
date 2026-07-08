from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fusion.decision.schema import EngineOutput, SignalCandidate


@dataclass
class MetaModelConfig:
    min_active_members: int = 2
    max_conflict_ratio: float = 0.35
    max_vote_concentration: float = 0.70
    min_avg_confidence: float = 0.45
    single_model_score: float = 0.45


class MetaModelEnsembleEngine:
    name = "meta_model_ensemble"

    def __init__(self, config: MetaModelConfig | None = None):
        self.config = config or MetaModelConfig()

    @staticmethod
    def _parse_active_votes(approved_status: str) -> list[dict[str, Any]]:
        votes: list[dict[str, Any]] = []
        status = str(approved_status or "").strip()
        if not status or status.upper() in {"NEUTRO", "SEM_DADOS", "SEM_FEATURES", "ERRO_FEATURES"}:
            return votes
        for token in status.split(";"):
            parts = token.split(":")
            if len(parts) < 4:
                continue
            try:
                direction_raw = int(float(parts[1]))
                confidence = float(parts[2])
                weight = float(str(parts[3]).replace("w", ""))
            except (TypeError, ValueError):
                continue
            direction = "BUY" if direction_raw > 0 else "SELL" if direction_raw < 0 else "NEUTRAL"
            if direction == "NEUTRAL":
                continue
            votes.append(
                {
                    "expert": parts[0],
                    "direction": direction,
                    "confidence": max(0.0, min(1.0, confidence)),
                    "weight": max(0.0, weight),
                    "contribution": max(0.0, weight) * max(0.0, min(1.0, confidence)),
                }
            )
        return votes

    @staticmethod
    def _member_count(approved_model: Any) -> int:
        members = getattr(approved_model, "members", None)
        if members is None:
            return 0
        try:
            return len(members)
        except TypeError:
            return 0

    @staticmethod
    def _single_model_feature_count(model: Any) -> int:
        meta = getattr(model, "meta", {}) or {}
        features = meta.get("features") or meta.get("feature_columns") or meta.get("columns") or []
        try:
            return len(features)
        except TypeError:
            return 0

    def evaluate(
        self,
        candidate: SignalCandidate,
        model: Any = None,
        approved_model: Any = None,
        approved_status: str = "",
    ) -> EngineOutput:
        side = candidate.side.upper()
        positive: list[str] = []
        negative: list[str] = []
        warnings: list[str] = []

        if approved_model is not None:
            votes = self._parse_active_votes(approved_status)
            member_count = self._member_count(approved_model)
            buy_weight = sum(float(vote["contribution"]) for vote in votes if vote["direction"] == "BUY")
            sell_weight = sum(float(vote["contribution"]) for vote in votes if vote["direction"] == "SELL")
            side_weight = buy_weight if side == "BUY" else sell_weight if side == "SELL" else 0.0
            opposite_weight = sell_weight if side == "BUY" else buy_weight if side == "SELL" else 0.0
            total_weight = buy_weight + sell_weight
            active_members = len(votes)
            avg_confidence = (
                sum(float(vote["confidence"]) for vote in votes) / active_members if active_members else 0.0
            )
            max_contribution = max((float(vote["contribution"]) for vote in votes), default=0.0)
            vote_concentration = max_contribution / total_weight if total_weight > 0 else 0.0
            conflict_ratio = opposite_weight / total_weight if total_weight > 0 else 1.0
            agreement = side_weight / total_weight if total_weight > 0 else 0.0

            score = agreement
            if active_members < self.config.min_active_members:
                warnings.append(f"poucos_experts_ativos:{active_members}")
                score *= 0.75
            if conflict_ratio > self.config.max_conflict_ratio:
                negative.append(f"conflito_entre_experts:{conflict_ratio:.2f}")
                score *= 0.65
            if vote_concentration > self.config.max_vote_concentration and active_members > 1:
                warnings.append(f"concentracao_em_um_expert:{vote_concentration:.2f}")
                score *= 0.85
            if avg_confidence < self.config.min_avg_confidence:
                warnings.append(f"confianca_media_baixa:{avg_confidence:.2f}")
                score *= 0.85
            if agreement >= 0.65 and not negative:
                positive.append("ensemble_alinhado")
            if member_count and active_members < member_count:
                warnings.append(f"experts_inativos:{member_count - active_members}")

            score = max(0.0, min(1.0, score))
            state = "ensemble_ok"
            direction = side
            if not votes:
                state = "no_active_votes"
                direction = "NEUTRAL"
                score = 0.0
                warnings.append("sem_votos_ativos")
            elif negative:
                state = "conflicted_ensemble"
                direction = "SELL" if side == "BUY" else "BUY" if side == "SELL" else "NEUTRAL"
            elif active_members < self.config.min_active_members or score < 0.50:
                state = "weak_ensemble"
                direction = "NEUTRAL"

            return EngineOutput(
                engine=self.name,
                direction=direction,
                score=score,
                confidence=max(0.10, min(0.95, avg_confidence if votes else 0.10)),
                state=state,
                positive_factors=positive,
                negative_factors=negative,
                warnings=warnings[:8],
                features={
                    "model_type": "approved_ensemble",
                    "member_count": member_count,
                    "active_members": active_members,
                    "buy_vote_weight": buy_weight,
                    "sell_vote_weight": sell_weight,
                    "side_vote_weight": side_weight,
                    "opposite_vote_weight": opposite_weight,
                    "net_vote_weight": buy_weight - sell_weight,
                    "ensemble_agreement": agreement,
                    "conflict_ratio": conflict_ratio,
                    "vote_concentration": vote_concentration,
                    "avg_confidence": avg_confidence,
                    "approved_status": approved_status,
                    "votes": votes,
                },
            )

        if model is not None:
            feature_count = self._single_model_feature_count(model)
            warnings.append("modelo_unico_sem_meta_ensemble")
            if feature_count <= 0:
                warnings.append("sem_metadados_features_modelo")
            return EngineOutput(
                engine=self.name,
                direction="NEUTRAL",
                score=max(0.0, min(1.0, self.config.single_model_score)),
                confidence=0.35,
                state="single_model",
                warnings=warnings,
                features={
                    "model_type": "single_model",
                    "feature_count": feature_count,
                    "raw_probability": candidate.direction_score,
                },
            )

        return EngineOutput(
            engine=self.name,
            direction="NEUTRAL",
            score=0.0,
            confidence=0.0,
            state="no_model_context",
            warnings=["sem_modelo_para_meta_ensemble"],
            features={"model_type": "none"},
        )
