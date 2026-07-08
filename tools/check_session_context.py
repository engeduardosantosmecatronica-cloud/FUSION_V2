from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fusion.engines import SessionConfig, SessionEngine


def main() -> int:
    engine = SessionEngine(SessionConfig())
    samples = [
        ("EURUSD", "M5", "BUY", datetime(2026, 5, 21, 7, 5, tzinfo=timezone.utc)),
        ("GBPJPY", "M5", "SELL", datetime(2026, 5, 21, 12, 5, tzinfo=timezone.utc)),
        ("AUDJPY", "M15", "BUY", datetime(2026, 5, 21, 2, 0, tzinfo=timezone.utc)),
        ("EURUSD", "H1", "SELL", datetime(2026, 5, 22, 19, 0, tzinfo=timezone.utc)),
        ("XAUUSD", "M5", "BUY", datetime(2026, 5, 21, 21, 15, tzinfo=timezone.utc)),
    ]
    results = []
    for symbol, timeframe, side, now_utc in samples:
        output = engine.evaluate(now_utc, symbol=symbol, timeframe=timeframe, side=side)
        results.append(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "side": side,
                "state": output.state,
                "score": output.score,
                "warnings": output.warnings,
                "negative_factors": output.negative_factors,
                "features": output.features,
            }
        )
    print(json.dumps(results, indent=2, ensure_ascii=False, default=str))
    if results[0]["state"] != "london":
        raise SystemExit("expected london state")
    if results[3]["state"] != "friday_close_risk":
        raise SystemExit("expected friday close risk")
    if results[4]["state"] != "rollover_low_liquidity":
        raise SystemExit("expected rollover state")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
