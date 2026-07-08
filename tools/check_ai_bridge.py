from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fusion.ai.bridge import mock_advice, mock_review


def main() -> int:
    advice_payload = {
        "candidate": {"symbol": "EURUSD", "timeframe": "M5", "side": "BUY"},
        "engines": [
            {"engine": "macro_flow", "direction": "SELL", "score": 0.82, "confidence": 0.82},
            {
                "engine": "context_engine",
                "direction": "SELL",
                "score": 0.45,
                "confidence": 0.55,
                "features": {"context_score": 0.45, "context_conflict_score": 0.50},
            },
        ],
    }
    review_payload = {
        "candidate": {"symbol": "EURUSD", "timeframe": "M5", "side": "BUY"},
        "result": {"decision": "ALLOW", "reason": "pre_order_checks_ok", "tradeability_score": 0.58, "conflict_score": 0.45},
        "engines": [{"engine": "macro_flow", "direction": "SELL"}],
    }
    print(json.dumps({"advice": mock_advice(advice_payload), "review": mock_review(review_payload)}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
