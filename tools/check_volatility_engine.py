from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fusion.engines import VolatilityEngine


def main() -> int:
    rng = np.random.default_rng(42)
    close = 1.10 + np.cumsum(rng.normal(0, 0.0004, 220))
    high = close + rng.uniform(0.0001, 0.0005, 220)
    low = close - rng.uniform(0.0001, 0.0005, 220)
    df = pd.DataFrame(
        {
            "time": pd.date_range("2026-01-01", periods=220, freq="15min"),
            "open": close,
            "high": high,
            "low": low,
            "close": close,
        }
    )
    output = VolatilityEngine().evaluate(df)
    print(json.dumps(output.__dict__, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
