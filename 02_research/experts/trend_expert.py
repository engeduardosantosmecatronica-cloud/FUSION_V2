from __future__ import annotations

from .base import ExpertOutput, clamp, direction_from_score, required


def analyze(data: dict) -> dict:
    missing = required(data, ["h1_trend", "h4_trend"])
    if missing:
        return ExpertOutput(
            status="insufficient_data",
            reason=f"Campos ausentes: {', '.join(missing)}.",
        ).to_dict()

    h1 = str(data["h1_trend"]).lower()
    h4 = str(data["h4_trend"]).lower()
    structure = str(data.get("structure", "")).lower()
    ema_alignment = str(data.get("ema_alignment", "")).lower()

    score = 0.0
    if h4 == "up":
        score += 0.45
    elif h4 == "down":
        score -= 0.45

    if h1 == "up":
        score += 0.35
    elif h1 == "down":
        score -= 0.35

    if structure in {"higher_highs_higher_lows", "bullish"}:
        score += 0.15
    elif structure in {"lower_highs_lower_lows", "bearish"}:
        score -= 0.15

    if ema_alignment == "bullish":
        score += 0.05
    elif ema_alignment == "bearish":
        score -= 0.05

    score = clamp(score, -1.0, 1.0)
    confidence = 0.55 + 0.35 * abs(score)

    return ExpertOutput(
        bias=direction_from_score(score),
        score=score,
        confidence=confidence,
        reason="Tendencia alinhada para compra." if score > 0.2 else "Tendencia alinhada para venda." if score < -0.2 else "Tendencia sem alinhamento forte.",
        features={
            "h1_trend": h1,
            "h4_trend": h4,
            "structure": structure,
            "ema_alignment": ema_alignment,
            "trend_strength": round(abs(score), 4),
        },
    ).to_dict()
