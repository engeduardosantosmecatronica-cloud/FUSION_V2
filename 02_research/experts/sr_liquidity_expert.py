from __future__ import annotations

from .base import ExpertOutput, clamp, direction_from_score, required


def analyze(data: dict) -> dict:
    missing = required(data, ["price", "nearest_support", "nearest_resistance"])
    if missing:
        return ExpertOutput(
            status="insufficient_data",
            reason=f"Campos ausentes: {', '.join(missing)}.",
        ).to_dict()

    price = float(data["price"])
    support = float(data["nearest_support"])
    resistance = float(data["nearest_resistance"])
    point = float(data.get("point", 0.0001))
    zone_quality = float(data.get("zone_quality", 0.5))
    liquidity_above = bool(data.get("liquidity_above", False))
    liquidity_below = bool(data.get("liquidity_below", False))

    distance_to_support = max(0.0, (price - support) / point)
    distance_to_resistance = max(0.0, (resistance - price) / point)
    total_room = max(distance_to_support + distance_to_resistance, 1.0)

    support_pressure = 1.0 - min(distance_to_support / total_room, 1.0)
    resistance_pressure = 1.0 - min(distance_to_resistance / total_room, 1.0)

    score = (support_pressure - resistance_pressure) * zone_quality
    if liquidity_above:
        score += 0.15
    if liquidity_below:
        score -= 0.15

    score = clamp(score, -1.0, 1.0)

    return ExpertOutput(
        bias=direction_from_score(score),
        score=score,
        confidence=clamp(0.45 + zone_quality * 0.4 + abs(score) * 0.15, 0.0, 1.0),
        reason="Preco mais favoravel para compra pela regiao." if score > 0.2 else "Preco mais favoravel para venda pela regiao." if score < -0.2 else "Preco no meio da faixa ou sem vantagem clara.",
        features={
            "nearest_support": support,
            "nearest_resistance": resistance,
            "distance_to_support_points": round(distance_to_support, 2),
            "distance_to_resistance_points": round(distance_to_resistance, 2),
            "liquidity_above": liquidity_above,
            "liquidity_below": liquidity_below,
            "zone_quality": zone_quality,
        },
    ).to_dict()
