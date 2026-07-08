from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fusion.decision import DecisionAuditLogger, DecisionOrchestrator, DecisionPolicy, EngineOutput, SignalCandidate


def main() -> None:
    orchestrator = DecisionOrchestrator(
        policy=DecisionPolicy(),
        audit_logger=DecisionAuditLogger("logs/decision_audit_smoke", enabled=True),
    )
    candidate = SignalCandidate(
        symbol="EURUSD",
        broker_symbol="EURUSD",
        timeframe="M5",
        side="BUY",
        strategy="SMOKE",
        raw_prediction=1,
        p_buy=0.72,
        p_sell=0.18,
    )
    engines = [
        EngineOutput(
            engine="macro_flow",
            direction="BUY",
            score=0.80,
            confidence=0.80,
            positive_factors=["H1/H4/D1 alinhados"],
        ),
        EngineOutput(
            engine="portfolio",
            direction="NEUTRAL",
            score=0.75,
            confidence=0.70,
            positive_factors=["sem_excesso_exposicao"],
        ),
    ]
    event = orchestrator.decide(candidate, engines)
    print(event.result.decision, event.result.reason, f"{event.result.tradeability_score:.3f}")


if __name__ == "__main__":
    main()
