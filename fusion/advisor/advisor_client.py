from __future__ import annotations

from fusion.engines.ai_advisor import AIAdvisorConfig, AIAdvisorEngine


def create_advisor_client(config: AIAdvisorConfig | None = None) -> AIAdvisorEngine:
    return AIAdvisorEngine(config)
