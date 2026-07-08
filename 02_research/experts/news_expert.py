from __future__ import annotations

from .base import ExpertOutput


def analyze(data: dict) -> dict:
    has_news = bool(data.get("has_high_impact_news", False))
    minutes_to_event = data.get("minutes_to_event")
    minutes_since_event = data.get("minutes_since_event")
    block_before = int(data.get("block_minutes_before", 30))
    block_after = int(data.get("block_minutes_after", 15))

    blocked_before = has_news and minutes_to_event is not None and 0 <= int(minutes_to_event) <= block_before
    blocked_after = has_news and minutes_since_event is not None and 0 <= int(minutes_since_event) <= block_after
    trade_allowed = not (blocked_before or blocked_after)

    score = -0.9 if not trade_allowed else 0.2

    return ExpertOutput(
        bias="neutral" if trade_allowed else "avoid",
        score=score,
        confidence=0.95 if has_news else 0.75,
        reason="Noticia de alto impacto perto do horario." if not trade_allowed else "Sem bloqueio de noticia no momento.",
        features={
            "has_high_impact_news": has_news,
            "currency": data.get("currency"),
            "event": data.get("event"),
            "minutes_to_event": minutes_to_event,
            "minutes_since_event": minutes_since_event,
            "news_risk": "high" if not trade_allowed else "normal",
            "trade_allowed": trade_allowed,
        },
    ).to_dict()
