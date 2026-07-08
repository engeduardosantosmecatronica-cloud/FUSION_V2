from __future__ import annotations

from .base import ExpertOutput, clamp, required


def analyze(data: dict) -> dict:
    missing = required(data, ["atr_points", "planned_sl_points", "planned_tp_points"])
    if missing:
        return ExpertOutput(
            status="insufficient_data",
            reason=f"Campos ausentes: {', '.join(missing)}.",
        ).to_dict()

    atr = max(float(data["atr_points"]), 1.0)
    sl = float(data["planned_sl_points"])
    tp = float(data["planned_tp_points"])
    spread = float(data.get("spread_points", 0.0))

    sl_atr_ratio = sl / atr
    tp_atr_ratio = tp / atr
    spread_atr_ratio = spread / atr

    score = 0.5
    if sl_atr_ratio < 0.25:
        score -= 0.45
    elif sl_atr_ratio > 2.5:
        score -= 0.2

    if tp_atr_ratio < 0.4:
        score -= 0.25
    elif 0.8 <= tp_atr_ratio <= 2.5:
        score += 0.2

    if spread_atr_ratio > 0.08:
        score -= 0.3

    score = clamp(score, -1.0, 1.0)
    trade_allowed = score >= 0.1

    return ExpertOutput(
        bias="neutral" if trade_allowed else "avoid",
        score=score,
        confidence=0.78,
        reason="Volatilidade comporta stop e alvo." if trade_allowed else "Volatilidade nao favorece o plano de stop/alvo.",
        features={
            "atr_points": atr,
            "planned_sl_points": sl,
            "planned_tp_points": tp,
            "sl_atr_ratio": round(sl_atr_ratio, 4),
            "tp_atr_ratio": round(tp_atr_ratio, 4),
            "spread_atr_ratio": round(spread_atr_ratio, 4),
            "volatility_state": "normal" if trade_allowed else "unfavorable",
            "trade_allowed": trade_allowed,
        },
    ).to_dict()
