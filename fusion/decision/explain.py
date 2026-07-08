from __future__ import annotations

from collections import Counter
from typing import Any

from fusion.decision.schema import DecisionResult, EngineOutput, SignalCandidate


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return low
    if number < low:
        return low
    if number > high:
        return high
    return number


def _engine_weight(engine: EngineOutput) -> float:
    confidence = _clamp(engine.confidence)
    score = _clamp(engine.score)
    return max(0.10, 0.65 * confidence + 0.35 * score)


def _ranked_factors(items: list[tuple[str, float]], top_n: int) -> list[dict[str, Any]]:
    scores: Counter[str] = Counter()
    for factor, weight in items:
        if not factor:
            continue
        scores[str(factor)] += float(weight)
    return [
        {"factor": factor, "weight": round(weight, 4)}
        for factor, weight in scores.most_common(max(1, int(top_n)))
    ]


def _confidence_band(score: float, conflict_score: float) -> str:
    if score >= 0.72 and conflict_score <= 0.20:
        return "alta"
    if score >= 0.55 and conflict_score <= 0.35:
        return "media"
    if score >= 0.40:
        return "baixa"
    return "fraca"


def _decision_summary(
    candidate: SignalCandidate,
    result: DecisionResult,
    aligned_engines: list[str],
    conflicting_engines: list[str],
    negative_factors: list[dict[str, Any]],
) -> str:
    side = candidate.side.upper()
    base = (
        f"{result.decision} {candidate.symbol} {candidate.timeframe} {side}: "
        f"tradeability={result.tradeability_score:.3f}, "
        f"consensus={result.consensus_score:.3f}, conflito={result.conflict_score:.3f}."
    )
    if result.decision.upper() == "BLOCK":
        blocker = negative_factors[0]["factor"] if negative_factors else result.reason
        return f"{base} Bloqueio dominante: {blocker}."
    if conflicting_engines:
        return f"{base} Entrada permitida com conflito moderado em {', '.join(conflicting_engines[:3])}."
    if aligned_engines:
        return f"{base} Motores alinhados: {', '.join(aligned_engines[:4])}."
    return base


def build_xai_explanation(
    candidate: SignalCandidate,
    result: DecisionResult,
    engines: list[EngineOutput],
    top_n: int = 8,
) -> dict[str, Any]:
    """Consolidates engine outputs into an auditable XAI explanation.

    The explainer is intentionally deterministic and side-effect free. It does not
    approve/block trades; it only summarizes why the existing decision happened.
    """
    aligned_engines: list[str] = []
    conflicting_engines: list[str] = []
    neutral_engines: list[str] = []
    warning_engines: list[str] = []
    positive_items: list[tuple[str, float]] = []
    negative_items: list[tuple[str, float]] = []
    warning_items: list[tuple[str, float]] = []
    engine_contributions: list[dict[str, Any]] = []

    for engine in engines:
        weight = _engine_weight(engine)
        direction = str(engine.direction or "NEUTRAL").upper()
        aligned = engine.aligned_with(candidate.side)
        conflicts = engine.conflicts_with(candidate.side)
        if aligned:
            aligned_engines.append(engine.engine)
        elif conflicts:
            conflicting_engines.append(engine.engine)
        else:
            neutral_engines.append(engine.engine)

        if engine.warnings:
            warning_engines.append(engine.engine)

        for factor in engine.positive_factors:
            positive_items.append((f"{engine.engine}:{factor}", weight))
        for factor in engine.negative_factors:
            negative_items.append((f"{engine.engine}:{factor}", weight))
        for factor in engine.warnings:
            warning_items.append((f"{engine.engine}:{factor}", weight))
        if conflicts:
            negative_items.append((f"{engine.engine}:direcao_conflitante:{direction}", weight))
        if aligned and direction in {"BUY", "SELL"}:
            positive_items.append((f"{engine.engine}:direcao_alinhada:{direction}", weight))

        impact = "neutral"
        if conflicts or engine.negative_factors:
            impact = "negative"
        elif aligned or engine.positive_factors:
            impact = "positive"

        engine_contributions.append(
            {
                "engine": engine.engine,
                "direction": direction,
                "state": engine.state,
                "score": round(_clamp(engine.score), 4),
                "confidence": round(_clamp(engine.confidence), 4),
                "weight": round(weight, 4),
                "impact": impact,
                "positive_count": len(engine.positive_factors),
                "negative_count": len(engine.negative_factors),
                "warning_count": len(engine.warnings),
            }
        )

    final_score = _clamp(
        0.45 * result.tradeability_score
        + 0.25 * result.consensus_score
        + 0.20 * (1.0 - result.conflict_score)
        + 0.10 * candidate.direction_score
    )
    top_positive = _ranked_factors(positive_items, top_n)
    top_negative = _ranked_factors(negative_items, top_n)
    top_warnings = _ranked_factors(warning_items, top_n)
    engine_contributions = sorted(
        engine_contributions,
        key=lambda item: (item["impact"] != "negative", -float(item["weight"])),
    )

    explanation = {
        "version": "xai_v1",
        "final_score": round(final_score, 4),
        "confidence_band": _confidence_band(final_score, result.conflict_score),
        "decision": result.decision,
        "reason": result.reason,
        "direction_score": round(candidate.direction_score, 4),
        "tradeability_score": round(_clamp(result.tradeability_score), 4),
        "consensus_score": round(_clamp(result.consensus_score), 4),
        "conflict_score": round(_clamp(result.conflict_score), 4),
        "position_multiplier": round(float(result.position_multiplier or 1.0), 4),
        "aligned_engines": aligned_engines,
        "conflicting_engines": conflicting_engines,
        "neutral_engines": neutral_engines,
        "warning_engines": sorted(set(warning_engines)),
        "top_positive_factors": top_positive,
        "top_negative_factors": top_negative,
        "top_warnings": top_warnings,
        "engine_contributions": engine_contributions,
    }
    explanation["summary"] = _decision_summary(
        candidate,
        result,
        aligned_engines,
        conflicting_engines,
        top_negative,
    )
    return explanation
