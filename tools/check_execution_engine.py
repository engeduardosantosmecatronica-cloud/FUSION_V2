from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fusion.engines.execution import ExecutionConfig, ExecutionEngine


def main() -> None:
    rows = []
    price = 1.1000
    for index in range(140):
        open_ = price
        close = price + 0.0002
        high = close + 0.0001
        low = open_ - 0.0001
        volume = 100 + (index % 15)
        if index == 139:
            open_ = price
            close = price + 0.0018
            high = close + 0.0001
            low = open_ - 0.0001
            volume = 220
        rows.append(
            {
                "time": pd.Timestamp("2026-01-01") + pd.Timedelta(minutes=5 * index),
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "tick_volume": volume,
            }
        )
        price = close

    frame = pd.DataFrame(rows)
    output = ExecutionEngine(ExecutionConfig()).evaluate(frame, "BUY")
    print(
        {
            "state": output.state,
            "direction": output.direction,
            "entry_quality_score": round(output.features["entry_quality_score"], 4),
            "breakout_quality": round(output.features["breakout_quality"], 4),
            "positive": output.positive_factors,
            "negative": output.negative_factors,
            "warnings": output.warnings,
        }
    )


if __name__ == "__main__":
    main()
