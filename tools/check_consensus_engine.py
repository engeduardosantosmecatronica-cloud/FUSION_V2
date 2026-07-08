from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fusion.decision.schema import EngineOutput, SignalCandidate
from fusion.engines.consensus import ConsensusConfig, ConsensusEngine


def main() -> None:
    candidate = SignalCandidate(
        symbol="EURUSD",
        broker_symbol="EURUSD",
        timeframe="H1",
        side="BUY",
        strategy="strategy1",
        raw_prediction=1,
        p_buy=0.62,
        p_sell=0.21,
    )
    engines = [
        EngineOutput(engine="market_regime", direction="BUY", score=0.72, confidence=0.80, state="TREND"),
        EngineOutput(engine="macro_flow", direction="BUY", score=0.70, confidence=0.75, state="aligned"),
        EngineOutput(engine="entry_timing", direction="NEUTRAL", score=0.62, confidence=0.65, state="ok"),
        EngineOutput(engine="portfolio_exposure", direction="NEUTRAL", score=0.50, confidence=0.60, state="warning", warnings=["currency_warning"]),
        EngineOutput(engine="market_structure", direction="SELL", score=0.55, confidence=0.60, state="shadow", warnings=["consolidacao"]),
    ]
    output = ConsensusEngine(ConsensusConfig()).evaluate(candidate, engines)
    print(
        {
            "state": output.state,
            "direction": output.direction,
            "consensus_score": round(output.features["consensus_score"], 4),
            "conflict_score": round(output.features["conflict_score"], 4),
            "aligned": output.features["aligned_engines"],
            "conflicts": output.features["conflicting_engines"],
        }
    )


if __name__ == "__main__":
    main()
