from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fusion.decision.schema import EngineOutput, SignalCandidate
from fusion.engines.opportunity import OpportunityConfig, OpportunityEngine


def candidate() -> SignalCandidate:
    return SignalCandidate(
        symbol="EURUSD",
        broker_symbol="EURUSD",
        timeframe="M30",
        side="BUY",
        strategy="strategy1",
        raw_prediction=1,
        p_buy=0.68,
        p_sell=0.22,
    )


def ok_engines() -> list[EngineOutput]:
    return [
        EngineOutput("consensus_engine", "BUY", 0.78, 0.80, "strong_consensus", positive_factors=["aligned"]),
        EngineOutput("entry_timing", "BUY", 0.82, 0.82, "ok", positive_factors=["entrada_limpa"]),
        EngineOutput("execution_engine", "BUY", 0.76, 0.78, "good_execution", positive_factors=["qualidade_execucao"]),
        EngineOutput("context_engine", "BUY", 0.74, 0.76, "favorable", positive_factors=["contexto_favoravel"]),
        EngineOutput("risk_engine", "NEUTRAL", 0.84, 0.80, "normal_risk", positive_factors=["risco_ok"]),
        EngineOutput("portfolio_exposure", "NEUTRAL", 0.82, 0.75, "ok"),
        EngineOutput("portfolio_correlation", "NEUTRAL", 0.85, 0.75, "ok"),
        EngineOutput("confidence_calibration", "BUY", 0.70, 0.70, "calibrated"),
        EngineOutput("meta_model_ensemble", "BUY", 0.78, 0.72, "ensemble_ok"),
        EngineOutput("market_structure", "NEUTRAL", 0.72, 0.70, "shadow", positive_factors=["estrutura_ok"]),
        EngineOutput("volatility_engine", "NEUTRAL", 0.70, 0.70, "NORMAL"),
        EngineOutput("session_context", "NEUTRAL", 0.80, 0.70, "new_york"),
    ]


def risky_engines() -> list[EngineOutput]:
    return [
        EngineOutput("consensus_engine", "SELL", 0.32, 0.70, "conflicted", negative_factors=["conflicts:risk"]),
        EngineOutput("entry_timing", "NEUTRAL", 0.35, 0.65, "weak_execution", negative_factors=["entrada_fraca"]),
        EngineOutput("execution_engine", "NEUTRAL", 0.30, 0.65, "avoid_execution", negative_factors=["fake_breakout"]),
        EngineOutput("context_engine", "SELL", 0.28, 0.76, "conflicted", negative_factors=["contexto_conflitante"]),
        EngineOutput("risk_engine", "SELL", 0.20, 0.80, "high_risk", negative_factors=["drawdown_risco"]),
        EngineOutput("portfolio_exposure", "SELL", 0.15, 0.75, "currency_overexposure", negative_factors=["exposicao_excessiva"]),
        EngineOutput("portfolio_correlation", "SELL", 0.20, 0.75, "risk_accumulation", negative_factors=["correlacao_prejuizo"]),
        EngineOutput("confidence_calibration", "NEUTRAL", 0.40, 0.35, "low_reliability", warnings=["perfil_fraco"]),
        EngineOutput("meta_model_ensemble", "NEUTRAL", 0.35, 0.50, "weak_ensemble", warnings=["poucos_experts"]),
        EngineOutput("market_structure", "NEUTRAL", 0.30, 0.70, "shadow", negative_factors=["consolidacao"]),
        EngineOutput("volatility_engine", "NEUTRAL", 0.45, 0.70, "NORMAL"),
        EngineOutput("session_context", "NEUTRAL", 0.35, 0.70, "rollover_low_liquidity", negative_factors=["baixa_liquidez"]),
    ]


def main() -> int:
    engine = OpportunityEngine(OpportunityConfig())
    good = engine.evaluate(candidate(), ok_engines())
    bad = engine.evaluate(candidate(), risky_engines())
    print(f"good state={good.state} score={good.score:.3f} penalty={good.features['penalty']:.3f}")
    print(f"bad state={bad.state} score={bad.score:.3f} penalty={bad.features['penalty']:.3f}")
    if good.state not in {"high_quality", "tradable"}:
        raise SystemExit("good opportunity should be tradable")
    if bad.state not in {"poor", "conflicted"}:
        raise SystemExit("risky opportunity should be poor/conflicted")
    if bad.score >= good.score:
        raise SystemExit("risky score should be lower than good score")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
