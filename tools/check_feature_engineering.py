from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fusion.engines.feature_engineering import FeatureEngineeringConfig, FeatureEngineeringEngine


def sample_frame(rows: int = 320) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    base = 1.1000 + np.cumsum(rng.normal(0, 0.00045, rows))
    open_ = base + rng.normal(0, 0.00012, rows)
    close = base + rng.normal(0, 0.00012, rows)
    high = np.maximum(open_, close) + np.abs(rng.normal(0.00035, 0.00008, rows))
    low = np.minimum(open_, close) - np.abs(rng.normal(0.00035, 0.00008, rows))
    volume = rng.integers(80, 180, rows)
    return pd.DataFrame(
        {
            "time": pd.date_range("2026-01-01", periods=rows, freq="5min"),
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "tick_volume": volume,
        }
    )


def main() -> int:
    engine = FeatureEngineeringEngine(FeatureEngineeringConfig())
    output = engine.evaluate(sample_frame())
    print(
        f"state={output.state} score={output.score:.3f} "
        f"coverage={output.features['feature_coverage']:.3f} "
        f"families={len(output.features['family_scores'])}"
    )
    if output.state not in {"feature_quality_ok", "feature_anomaly_context"}:
        raise SystemExit("unexpected feature quality state")
    if output.features["feature_coverage"] < 0.70:
        raise SystemExit("feature coverage too low")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
