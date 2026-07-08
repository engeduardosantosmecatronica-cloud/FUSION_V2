from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fusion.decision import DecisionResult, EngineOutput, SignalCandidate, build_xai_explanation


def main() -> None:
    candidate = SignalCandidate(
        symbol="EURUSD",
        broker_symbol="EURUSD",
        timeframe="H1",
        side="BUY",
        strategy="S1",
        raw_prediction=1,
        p_buy=0.68,
        p_sell=0.22,
    )
    result = DecisionResult(
        decision="ALLOW",
        reason="ok",
        consensus_score=0.72,
        conflict_score=0.12,
        tradeability_score=0.69,
        position_multiplier=1.0,
    )
    engines = [
        EngineOutput(
            engine="macro_flow",
            direction="BUY",
            score=0.82,
            confidence=0.80,
            state="macro_alinhado",
            positive_factors=["macro_alinhado:BUY"],
        ),
        EngineOutput(
            engine="risk_engine",
            direction="NEUTRAL",
            score=0.74,
            confidence=0.75,
            state="normal_risk",
            positive_factors=["risco_operacional_normal"],
        ),
        EngineOutput(
            engine="entry_timing",
            direction="SELL",
            score=0.35,
            confidence=0.70,
            state="conflict",
            negative_factors=["comprar_topo_sem_rompimento_validado"],
        ),
    ]
    explanation = build_xai_explanation(candidate, result, engines)
    if explanation["final_score"] <= 0:
        raise SystemExit("xai final_score invalido")
    if not explanation["aligned_engines"]:
        raise SystemExit("xai nao registrou engines alinhadas")
    if not explanation["conflicting_engines"]:
        raise SystemExit("xai nao registrou engines conflitantes")
    if not explanation["top_negative_factors"]:
        raise SystemExit("xai nao registrou fatores negativos")
    print(
        "xai_ok "
        f"score={explanation['final_score']:.3f} "
        f"band={explanation['confidence_band']} "
        f"aligned={len(explanation['aligned_engines'])} "
        f"conflicts={len(explanation['conflicting_engines'])}"
    )


if __name__ == "__main__":
    main()
