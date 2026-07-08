from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fusion.engines import PortfolioExposureConfig, PortfolioExposureEngine


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test do Portfolio Exposure Engine.")
    parser.add_argument("--symbol", default="EURNZD")
    parser.add_argument("--side", default="BUY", choices=["BUY", "SELL"])
    args = parser.parse_args()

    positions = [
        {"symbol": "EURUSD", "direction": "BUY", "volume": 0.01, "profit": -2.4},
        {"symbol": "AUDJPY", "direction": "SELL", "volume": 0.01, "profit": 1.1},
        {"symbol": "EURAUD", "direction": "BUY", "volume": 0.01, "profit": -1.7},
        {"symbol": "AUDUSD", "direction": "SELL", "volume": 0.01, "profit": -0.9},
    ]
    matrix = {
        "EURNZD": {"EURAUD": 0.74, "AUDUSD": -0.71},
        "EURAUD": {"EURNZD": 0.74},
        "AUDUSD": {"EURNZD": -0.71},
    }
    engine = PortfolioExposureEngine(PortfolioExposureConfig(max_cluster_exposure=2.5, max_losing_currency_exposure=2.0))
    output = engine.evaluate(args.symbol, args.side, positions, correlation_matrix=matrix)
    print(json.dumps(output.__dict__, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
