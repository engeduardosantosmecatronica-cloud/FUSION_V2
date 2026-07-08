from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fusion.decision import EngineOutput, SignalCandidate
from fusion.engines import AIAdvisorEngine


def main() -> int:
    candidate = SignalCandidate(
        symbol="EURUSD",
        broker_symbol="EURUSD",
        timeframe="M5",
        side="BUY",
        strategy="strategy1",
        raw_prediction=1,
        p_buy=0.62,
        p_sell=0.18,
    )
    engines = [
        EngineOutput(engine="macro_flow", direction="SELL", score=0.82, confidence=0.82, state="SELL", negative_factors=["dolar_forte"]),
        EngineOutput(engine="ema_alignment", direction="BUY", score=0.85, confidence=0.85, state="ok", positive_factors=["emas_alinhadas"]),
    ]
    payload = AIAdvisorEngine().build_payload(candidate, engines, {"sl_points": 100, "tp_points": 0})
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
