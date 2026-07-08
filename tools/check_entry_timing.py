from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fusion.engines import EntryTimingEngine


def sample_frame(kind: str) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    close = 1.10 + np.cumsum(rng.normal(0.00005, 0.00025, 260))
    if kind == "buy_top":
        close[-25:] = np.linspace(close[-26], close[-26] + 0.006, 25)
    elif kind == "sell_bottom":
        close[-25:] = np.linspace(close[-26], close[-26] - 0.006, 25)
    elif kind == "buy_top_no_break":
        close[-40:] = np.linspace(close[-41] - 0.001, close[-41] + 0.001, 40)
    elif kind == "sell_bottom_no_break":
        close[-40:] = np.linspace(close[-41] + 0.001, close[-41] - 0.001, 40)
    high = close + rng.uniform(0.00005, 0.00025, len(close))
    low = close - rng.uniform(0.00005, 0.00025, len(close))
    return pd.DataFrame(
        {
            "time": pd.date_range("2026-01-01", periods=len(close), freq="15min"),
            "open": np.r_[close[0], close[:-1]],
            "high": high,
            "low": low,
            "close": close,
            "tick_volume": rng.integers(80, 180, len(close)),
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Testa Entry Timing Engine.")
    parser.add_argument("--kind", default="buy_top", choices=["buy_top", "sell_bottom", "buy_top_no_break", "sell_bottom_no_break", "normal"])
    parser.add_argument("--side", default="BUY", choices=["BUY", "SELL"])
    args = parser.parse_args()
    output = EntryTimingEngine().evaluate(sample_frame(args.kind), args.side)
    print(json.dumps(output.__dict__, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
