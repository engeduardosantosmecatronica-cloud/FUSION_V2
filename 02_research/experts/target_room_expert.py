from __future__ import annotations

from .base import ExpertOutput, clamp, required


def analyze(data: dict) -> dict:
    missing = required(data, ["direction", "entry_price", "tp_price", "nearest_barrier", "point"])
    if missing:
        return ExpertOutput(
            status="insufficient_data",
            reason=f"Campos ausentes: {', '.join(missing)}.",
        ).to_dict()

    direction = str(data["direction"]).lower()
    entry = float(data["entry_price"])
    tp = float(data["tp_price"])
    barrier = float(data["nearest_barrier"])
    point = float(data["point"])

    planned_tp_points = abs(tp - entry) / point
    if direction == "buy":
        distance_to_barrier = max(0.0, (barrier - entry) / point)
    else:
        distance_to_barrier = max(0.0, (entry - barrier) / point)

    room_to_target_ratio = distance_to_barrier / max(planned_tp_points, 1.0)
    score = clamp(room_to_target_ratio - 0.5, -1.0, 1.0)
    if room_to_target_ratio >= 1.0:
        score = 0.8
        target_quality = "clear"
    elif room_to_target_ratio >= 0.7:
        target_quality = "partial_obstruction"
    else:
        target_quality = "blocked"

    bias = "buy" if direction == "buy" and score > 0.1 else "sell" if direction == "sell" and score > 0.1 else "avoid"

    return ExpertOutput(
        bias=bias,
        score=score,
        confidence=clamp(0.45 + abs(score) * 0.45, 0.0, 1.0),
        reason="Alvo tem espaco livre." if score > 0.1 else "Barreira proxima demais para o alvo planejado.",
        features={
            "direction": direction,
            "entry_price": entry,
            "tp_price": tp,
            "nearest_barrier": barrier,
            "distance_to_barrier_points": round(distance_to_barrier, 2),
            "planned_tp_points": round(planned_tp_points, 2),
            "room_to_target_ratio": round(room_to_target_ratio, 4),
            "target_quality": target_quality,
        },
    ).to_dict()
