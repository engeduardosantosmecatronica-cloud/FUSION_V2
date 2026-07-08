from __future__ import annotations

from fusion.decision.audit import DecisionAuditLogger
from fusion.decision.policy import DecisionPolicy
from fusion.decision.schema import DecisionEvent, DecisionResult, EngineOutput, SignalCandidate


class DecisionOrchestrator:
    def __init__(
        self,
        policy: DecisionPolicy | None = None,
        audit_logger: DecisionAuditLogger | None = None,
    ):
        self.policy = policy or DecisionPolicy()
        self.audit_logger = audit_logger or DecisionAuditLogger()

    def decide(
        self,
        candidate: SignalCandidate,
        engines: list[EngineOutput] | None = None,
        account: dict | None = None,
        portfolio: dict | None = None,
        audit: bool = True,
    ) -> DecisionEvent:
        engine_outputs = engines or []
        result: DecisionResult = self.policy.combine(candidate, engine_outputs)
        event = DecisionEvent(
            candidate=candidate,
            engines=engine_outputs,
            result=result,
            account=account or {},
            portfolio=portfolio or {},
        )
        if audit:
            self.audit_logger.write(event)
        return event
