from __future__ import annotations

from .base import ExpertOutput, clamp


SESSION_SCORE = {
    "london": 0.35,
    "new_york": 0.3,
    "london_new_york_overlap": 0.45,
    "asia": 0.05,
    "rollover": -0.8,
    "closed": -1.0,
}


def analyze(data: dict) -> dict:
    session = str(data.get("session", "unknown")).lower()
    spread_state = str(data.get("spread_state", "normal")).lower()
    expected_liquidity = str(data.get("expected_liquidity", "normal")).lower()

    score = SESSION_SCORE.get(session, 0.0)
    if spread_state in {"high", "extreme"}:
        score -= 0.35
    if expected_liquidity == "low":
        score -= 0.2
    elif expected_liquidity == "high":
        score += 0.1

    score = clamp(score, -1.0, 1.0)
    trade_allowed = score > -0.4

    return ExpertOutput(
        bias="neutral" if trade_allowed else "avoid",
        score=score,
        confidence=0.85,
        reason="Sessao operacional aceitavel." if trade_allowed else "Sessao ruim para operar.",
        features={
            "session": session,
            "expected_liquidity": expected_liquidity,
            "spread_state": spread_state,
            "session_risk": "normal" if trade_allowed else "high",
            "trade_allowed": trade_allowed,
        },
    ).to_dict()
