from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fusion.decision import SignalCandidate
from fusion.engines import MarketBriefingConfig, MarketBriefingEngine


def main() -> int:
    parser = argparse.ArgumentParser(description="Testa Market Briefing Engine.")
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--side", default="BUY")
    parser.add_argument("--strategy", default="strategy4")
    parser.add_argument("--briefing-path", default="config/market_briefing_today.json")
    args = parser.parse_args()
    candidate = SignalCandidate(
        symbol=args.symbol.upper(),
        broker_symbol=args.symbol.upper(),
        timeframe=args.timeframe.upper(),
        side=args.side.upper(),
        strategy=args.strategy,
        raw_prediction=1 if args.side.upper() == "BUY" else 2,
    )
    output = MarketBriefingEngine(MarketBriefingConfig(briefing_path=args.briefing_path)).evaluate(candidate)
    print(json.dumps(output.__dict__, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
