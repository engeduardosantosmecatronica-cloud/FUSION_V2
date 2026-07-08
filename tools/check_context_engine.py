from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fusion.decision import EngineOutput, SignalCandidate
from fusion.engines import ContextEngine


def main() -> int:
    candidate = SignalCandidate(
        symbol="EURUSD",
        broker_symbol="EURUSD",
        timeframe="M15",
        side="BUY",
        strategy="strategy1",
        raw_prediction=1,
        p_buy=0.68,
        p_sell=0.12,
    )
    engines = [
        EngineOutput(engine="macro_flow", direction="BUY", score=0.80, confidence=0.80, state="BUY"),
        EngineOutput(engine="market_regime", direction="BUY", score=0.70, confidence=0.75, state="TREND"),
        EngineOutput(engine="portfolio_exposure", direction="NEUTRAL", score=0.90, confidence=0.70, state="ok"),
        EngineOutput(engine="ema_alignment", direction="BUY", score=0.85, confidence=0.85, state="ok"),
    ]
    output = ContextEngine().evaluate(candidate, engines)
    print(json.dumps(output.__dict__, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
