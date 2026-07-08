from __future__ import annotations

from .base import ExpertOutput, clamp, direction_from_score


BULLISH_SIGNALS = {"bullish_rejection", "bullish_engulfing", "bullish_pinbar", "demand_retest"}
BEARISH_SIGNALS = {"bearish_rejection", "bearish_engulfing", "bearish_pinbar", "supply_retest"}


def analyze(data: dict) -> dict:
    signal_type = str(data.get("signal_type", "none")).lower()
    zone_type = str(data.get("zone_type", "none")).lower()
    zone_strength = float(data.get("zone_strength", 0.0))
    signal_quality = float(data.get("signal_quality", 0.0))
    confluence_count = int(data.get("confluence_count", 0))

    signal_score = 0.0
    if signal_type in BULLISH_SIGNALS:
        signal_score = 1.0
    elif signal_type in BEARISH_SIGNALS:
        signal_score = -1.0

    zone_factor = clamp((zone_strength + signal_quality) / 2.0, 0.0, 1.0)
    confluence_bonus = min(confluence_count, 5) * 0.04

    score = signal_score * clamp(zone_factor + confluence_bonus, 0.0, 1.0)
    if zone_type in {"resistance", "supply"} and score > 0:
        score *= 0.55
    if zone_type in {"support", "demand"} and score < 0:
        score *= 0.55

    score = clamp(score, -1.0, 1.0)

    return ExpertOutput(
        bias=direction_from_score(score),
        score=score,
        confidence=clamp(0.35 + abs(score) * 0.45 + zone_strength * 0.15, 0.0, 1.0),
        reason="Sinal comprador em regiao relevante." if score > 0.2 else "Sinal vendedor em regiao relevante." if score < -0.2 else "Sinal fraco ou em regiao pouco relevante.",
        features={
            "signal_type": signal_type,
            "zone_type": zone_type,
            "zone_strength": zone_strength,
            "signal_quality": signal_quality,
            "confluence_count": confluence_count,
            "entry_timing": "valid" if abs(score) > 0.2 else "weak",
        },
    ).to_dict()
