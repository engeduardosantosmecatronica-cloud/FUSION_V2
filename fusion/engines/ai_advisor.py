from __future__ import annotations

from dataclasses import dataclass
import json
import urllib.error
import urllib.request
from typing import Any

from fusion.decision.schema import EngineOutput, SignalCandidate


@dataclass
class AIAdvisorConfig:
    endpoint_url: str = "http://127.0.0.1:8765/advice"
    timeout_seconds: float = 8.0
    min_confidence_to_block: float = 0.65
    fail_open: bool = True
    model_hint: str = "gpt-5.4-nano"


class AIAdvisorEngine:
    name = "ai_advisor"

    def __init__(self, config: AIAdvisorConfig | None = None):
        self.config = config or AIAdvisorConfig()

    @staticmethod
    def _engine_to_dict(engine: EngineOutput) -> dict[str, Any]:
        return {
            "engine": engine.engine,
            "direction": engine.direction,
            "score": engine.score,
            "confidence": engine.confidence,
            "state": engine.state,
            "positive_factors": engine.positive_factors,
            "negative_factors": engine.negative_factors,
            "warnings": engine.warnings,
            "features": engine.features,
        }

    @staticmethod
    def _candidate_to_dict(candidate: SignalCandidate) -> dict[str, Any]:
        return {
            "symbol": candidate.symbol,
            "broker_symbol": candidate.broker_symbol,
            "timeframe": candidate.timeframe,
            "side": candidate.side,
            "strategy": candidate.strategy,
            "raw_prediction": candidate.raw_prediction,
            "p_buy": candidate.p_buy,
            "p_sell": candidate.p_sell,
            "direction_score": candidate.direction_score,
            "timestamp": candidate.timestamp,
        }

    def build_payload(
        self,
        candidate: SignalCandidate,
        engines: list[EngineOutput],
        portfolio: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "task": "Confirmar se a ordem candidata deve ser evitada por contexto macro, risco, sessao ou conflito.",
            "required_response_schema": {
                "recommendation": "ALLOW | AVOID | NEUTRAL",
                "confidence": "0.0-1.0",
                "primary_reason": "string curta",
                "risk_notes": ["lista curta"],
            },
            "rules": [
                "Nao envie ordem.",
                "Nao altere parametros do robo.",
                "Responda apenas JSON valido.",
                "Use AVOID apenas quando houver conflito contextual forte.",
            ],
            "model_hint": self.config.model_hint,
            "candidate": self._candidate_to_dict(candidate),
            "engines": [self._engine_to_dict(engine) for engine in engines],
            "portfolio": portfolio or {},
        }

    def evaluate(
        self,
        candidate: SignalCandidate,
        engines: list[EngineOutput],
        portfolio: dict[str, Any] | None = None,
    ) -> EngineOutput:
        payload = self.build_payload(candidate, engines, portfolio)
        data = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        request = urllib.request.Request(
            self.config.endpoint_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                raw = response.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return EngineOutput(
                engine=self.name,
                direction="NEUTRAL",
                score=0.50 if self.config.fail_open else 0.0,
                confidence=0.0,
                state="unavailable",
                warnings=[f"advisor_indisponivel:{type(exc).__name__}"],
                features={"endpoint_url": self.config.endpoint_url, "fail_open": self.config.fail_open},
            )

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            start = raw.find("{")
            end = raw.rfind("}")
            if start >= 0 and end > start:
                try:
                    parsed = json.loads(raw[start : end + 1])
                except json.JSONDecodeError:
                    parsed = {}
            else:
                parsed = {}

        recommendation = str(parsed.get("recommendation", "NEUTRAL") or "NEUTRAL").upper()
        if recommendation not in {"ALLOW", "AVOID", "NEUTRAL"}:
            recommendation = "NEUTRAL"
        try:
            confidence = float(parsed.get("confidence", 0.0) or 0.0)
        except (TypeError, ValueError):
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))
        reason = str(parsed.get("primary_reason", "") or "")
        notes = parsed.get("risk_notes", [])
        if not isinstance(notes, list):
            notes = [str(notes)]

        if recommendation == "AVOID":
            direction = "SELL" if candidate.side.upper() == "BUY" else "BUY" if candidate.side.upper() == "SELL" else "NEUTRAL"
            return EngineOutput(
                engine=self.name,
                direction=direction,
                score=1.0,
                confidence=confidence,
                state="avoid",
                negative_factors=[reason or "advisor_evitar"],
                warnings=[str(item) for item in notes[:5]],
                features={"raw_response": parsed},
            )
        if recommendation == "ALLOW":
            return EngineOutput(
                engine=self.name,
                direction=candidate.side.upper(),
                score=confidence,
                confidence=confidence,
                state="allow",
                positive_factors=[reason or "advisor_aprova"],
                warnings=[str(item) for item in notes[:5]],
                features={"raw_response": parsed},
            )
        return EngineOutput(
            engine=self.name,
            direction="NEUTRAL",
            score=0.50,
            confidence=confidence,
            state="neutral",
            warnings=[reason or "advisor_neutro"] + [str(item) for item in notes[:4]],
            features={"raw_response": parsed},
        )
