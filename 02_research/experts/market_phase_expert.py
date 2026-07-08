from __future__ import annotations

from .base import ExpertOutput, clamp, direction_from_score


def analyze(data: dict) -> dict:
    phase = str(data.get("market_phase", "unknown")).lower()
    breakout_direction = str(data.get("breakout_direction", "none")).lower()
    pullback_quality = float(data.get("pullback_quality", 0.0))
    range_strength = float(data.get("range_strength", 0.0))
    reversal_risk = float(data.get("reversal_risk", 0.0))

    score = 0.0
    if phase in {"breakout", "pullback_after_breakout", "trend_pullback"}:
        if breakout_direction == "up":
            score = 0.45 + 0.35 * pullback_quality
        elif breakout_direction == "down":
            score = -0.45 - 0.35 * pullback_quality
    elif phase in {"range", "lateral"}:
        score = 0.0
    elif phase == "reversal":
        direction = str(data.get("reversal_direction", "none")).lower()
        score = 0.35 if direction == "up" else -0.35 if direction == "down" else 0.0

    score -= clamp(reversal_risk, 0.0, 1.0) * 0.15 if score > 0 else 0.0
    score += clamp(reversal_risk, 0.0, 1.0) * 0.15 if score < 0 else 0.0
    score *= 1.0 - clamp(range_strength, 0.0, 1.0) * 0.35
    score = clamp(score, -1.0, 1.0)

    return ExpertOutput(
        bias=direction_from_score(score),
        score=score,
        confidence=clamp(0.45 + abs(score) * 0.4, 0.0, 1.0),
        reason="Fase favorece compra." if score > 0.2 else "Fase favorece venda." if score < -0.2 else "Fase lateral ou sem vantagem direcional.",
        features={
            "market_phase": phase,
            "breakout_direction": breakout_direction,
            "pullback_quality": pullback_quality,
            "range_state": "ranging" if range_strength > 0.55 else "not_ranging",
            "reversal_risk": reversal_risk,
        },
    ).to_dict()
