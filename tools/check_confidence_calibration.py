from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fusion.decision import SignalCandidate
from fusion.engines import CalibrationConfig, ConfidenceCalibrationEngine


def main() -> int:
    parser = argparse.ArgumentParser(description="Testa Confidence Calibration Engine.")
    parser.add_argument("--symbol", default="AUDCHF")
    parser.add_argument("--timeframe", default="H1")
    parser.add_argument("--side", default="SELL", choices=["BUY", "SELL"])
    parser.add_argument("--p-buy", type=float, default=0.20)
    parser.add_argument("--p-sell", type=float, default=0.55)
    args = parser.parse_args()
    pred = 1 if args.side == "BUY" else 2
    candidate = SignalCandidate(
        symbol=args.symbol.upper(),
        broker_symbol=args.symbol.upper(),
        timeframe=args.timeframe.upper(),
        side=args.side,
        strategy="strategy1",
        raw_prediction=pred,
        p_buy=args.p_buy,
        p_sell=args.p_sell,
    )
    output = ConfidenceCalibrationEngine(
        CalibrationConfig(profiles_path="reports/confidence_calibration/confidence_calibration_profiles.json")
    ).evaluate(candidate)
    print(json.dumps(output.__dict__, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
