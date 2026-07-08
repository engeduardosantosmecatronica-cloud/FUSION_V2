from __future__ import annotations

from typing import Any

from fusion.decision.schema import EngineOutput, SignalCandidate
from fusion.engines.ai_advisor import AIAdvisorEngine


def build_advisor_payload(
    candidate: SignalCandidate,
    engines: list[EngineOutput],
    portfolio: dict[str, Any] | None = None,
    model_hint: str = "gpt-5.4-nano",
) -> dict[str, Any]:
    advisor = AIAdvisorEngine()
    advisor.config.model_hint = model_hint
    return advisor.build_payload(candidate, engines, portfolio=portfolio or {})
