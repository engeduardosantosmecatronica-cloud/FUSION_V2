from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fusion.decision.schema import SignalCandidate
from fusion.engines.meta_model import MetaModelConfig, MetaModelEnsembleEngine


def candidate(side: str = "BUY") -> SignalCandidate:
    return SignalCandidate(
        symbol="EURUSD",
        broker_symbol="EURUSD",
        timeframe="M30",
        side=side,
        strategy="strategy5",
        raw_prediction=1 if side == "BUY" else 2,
        p_buy=0.62 if side == "BUY" else 0.31,
        p_sell=0.31 if side == "BUY" else 0.62,
    )


def main() -> int:
    engine = MetaModelEnsembleEngine(MetaModelConfig())
    approved_model = SimpleNamespace(members=[object(), object(), object()])

    aligned = engine.evaluate(
        candidate("BUY"),
        approved_model=approved_model,
        approved_status="trend:1:0.720:w0.600;momentum:1:0.650:w0.500;reversal:-1:0.480:w0.250",
    )
    conflicted = engine.evaluate(
        candidate("BUY"),
        approved_model=approved_model,
        approved_status="trend:1:0.620:w0.300;mean_reversion:-1:0.800:w0.600;volatility:-1:0.690:w0.400",
    )
    single = engine.evaluate(candidate("SELL"), model=SimpleNamespace(meta={"features": ["a", "b", "c"]}))

    print(f"aligned state={aligned.state} score={aligned.score:.3f} agreement={aligned.features['ensemble_agreement']:.3f}")
    print(f"conflicted state={conflicted.state} score={conflicted.score:.3f} conflict={conflicted.features['conflict_ratio']:.3f}")
    print(f"single state={single.state} score={single.score:.3f} features={single.features['feature_count']}")

    if aligned.state != "ensemble_ok":
        raise SystemExit("aligned scenario should be ensemble_ok")
    if conflicted.state != "conflicted_ensemble":
        raise SystemExit("conflicted scenario should be conflicted_ensemble")
    if single.state != "single_model":
        raise SystemExit("single model scenario should be single_model")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
