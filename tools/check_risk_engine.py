from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fusion.decision.schema import EngineOutput, SignalCandidate
from fusion.engines.risk import RiskConfig, RiskEngine


def main() -> None:
    candidate = SignalCandidate(
        symbol="AUDUSD",
        broker_symbol="AUDUSD",
        timeframe="H1",
        side="SELL",
        strategy="strategy1",
        raw_prediction=2,
        p_buy=0.22,
        p_sell=0.61,
    )
    engines = [
        EngineOutput(
            engine="portfolio_exposure",
            direction="BUY",
            score=0.20,
            confidence=0.75,
            state="currency_overexposure",
            negative_factors=["exposicao_excessiva:AUD:-7.00"],
        ),
        EngineOutput(
            engine="consensus_engine",
            direction="NEUTRAL",
            score=0.42,
            confidence=0.55,
            state="conflicted",
            features={"conflict_score": 0.38},
        ),
        EngineOutput(
            engine="feature_engineering",
            direction="NEUTRAL",
            score=0.48,
            confidence=0.70,
            state="feature_quality_weak",
            warnings=["feature_coverage_baixa"],
        ),
        EngineOutput(
            engine="volatility_engine",
            direction="NEUTRAL",
            score=0.82,
            confidence=0.80,
            state="EXPANSION",
            positive_factors=["expansao_volatilidade"],
        ),
    ]
    account = {
        "balance": 1000.0,
        "equity": 955.0,
        "profit": -45.0,
        "margin": 310.0,
        "margin_free": 645.0,
        "margin_level": 308.0,
    }
    positions = [
        {"symbol": "AUDJPY", "direction": "SELL", "volume": 0.01, "profit": -8.0},
        {"symbol": "AUDUSD", "direction": "SELL", "volume": 0.01, "profit": -6.0},
        {"symbol": "EURAUD", "direction": "BUY", "volume": 0.01, "profit": -10.0},
        {"symbol": "EURUSD", "direction": "BUY", "volume": 0.01, "profit": 2.0},
    ]
    output = RiskEngine(
        RiskConfig(
            max_losing_positions=3,
            max_currency_risk_units=4.0,
            warning_currency_risk_units=2.0,
            max_same_direction_positions=2,
        )
    ).evaluate(candidate, engines, account, positions)
    print(
        {
            "state": output.state,
            "direction": output.direction,
            "risk_score": round(output.features["risk_score"], 4),
            "multiplier": output.features["position_multiplier_suggested"],
            "negative": output.negative_factors,
            "warnings": output.warnings,
            "margin_usage_pct": round(output.features["margin_usage_pct"], 4),
            "max_projected_currency_risk": output.features["max_projected_currency_risk"],
        }
    )
    if output.state not in {"critical_risk", "high_risk", "reduced_risk"}:
        raise SystemExit("expected risk state")
    if output.features["position_multiplier_suggested"] > 0.75:
        raise SystemExit("expected reduced multiplier")


if __name__ == "__main__":
    main()
