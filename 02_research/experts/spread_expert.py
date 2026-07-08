from __future__ import annotations

from .base import ExpertOutput, clamp, required


def analyze(data: dict) -> dict:
    missing = required(data, ["spread_points", "max_allowed_spread_points"])
    if missing:
        return ExpertOutput(
            status="insufficient_data",
            reason=f"Campos ausentes: {', '.join(missing)}.",
        ).to_dict()

    spread = float(data["spread_points"])
    max_allowed = max(float(data["max_allowed_spread_points"]), 0.000001)
    avg_spread = float(data.get("avg_spread_points", max_allowed * 0.5))

    spread_ratio = spread / max_allowed
    avg_ratio = spread / max(avg_spread, 0.000001)

    trade_allowed = spread <= max_allowed
    score = 1.0 - spread_ratio
    if avg_ratio > 2.0:
        score -= 0.2
    score = clamp(score, -1.0, 1.0)

    if spread_ratio <= 0.6:
        spread_state = "normal"
    elif spread_ratio <= 1.0:
        spread_state = "elevated"
    else:
        spread_state = "high"

    return ExpertOutput(
        bias="neutral" if trade_allowed else "avoid",
        score=score,
        confidence=0.96,
        reason="Spread aceitavel." if trade_allowed else "Spread acima do limite.",
        features={
            "spread_points": spread,
            "avg_spread_points": avg_spread,
            "max_allowed_spread_points": max_allowed,
            "spread_ratio": round(spread_ratio, 4),
            "spread_state": spread_state,
            "trade_allowed": trade_allowed,
        },
    ).to_dict()
