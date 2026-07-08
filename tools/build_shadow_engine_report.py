from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


SHADOW_ENGINES = {
    "market_regime",
    "volatility_engine",
    "session_context",
    "portfolio_exposure",
    "risk_engine",
    "market_structure",
    "entry_timing",
    "execution_engine",
    "market_briefing",
    "context_engine",
    "confidence_calibration",
    "meta_model_ensemble",
    "feature_engineering",
    "consensus_engine",
    "opportunity_engine",
    "ai_advisor",
}

RISK_STATES = {
    "avoid_buying_top",
    "avoid_selling_bottom",
    "block",
    "conflicted",
    "weak",
    "PANIC_VOLATILITY",
    "currency_overexposure",
    "gross_overexposure",
    "cluster_overexposure",
    "losing_currency_overexposure",
    "symbol_concentration",
    "gross_warning",
    "cluster_warning",
    "risk_accumulation",
    "avoid",
    "moderate",
    "marginal",
    "poor",
    "high_quality",
    "insufficient_context",
    "insufficient_engines",
    "avoid_execution",
    "weak_execution",
    "high_risk",
    "critical_risk",
    "reduced_risk",
    "weak_ensemble",
    "conflicted_ensemble",
    "single_model",
    "no_active_votes",
    "no_model_context",
    "feature_quality_weak",
    "insufficient_features",
    "insufficient_data",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Relatorio consolidado dos engines em shadow.")
    parser.add_argument("--log-dir", default="logs/decision_audit")
    parser.add_argument("--output-dir", default="reports/shadow_engine_report")
    parser.add_argument("--date", default="", help="YYYYMMDD. Se vazio, usa todos os audits.")
    parser.add_argument("--tail", type=int, default=0, help="Limita aos ultimos N eventos.")
    return parser.parse_args()


def iter_events(log_dir: Path, date: str):
    pattern = f"decision_audit_{date}.jsonl" if date else "decision_audit_*.jsonl"
    for path in sorted(log_dir.glob(pattern)):
        with path.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                event["_source_file"] = path.name
                event["_source_line"] = line_no
                yield event


def engine_risk_flag(engine: dict[str, Any], side: str) -> bool:
    state = str(engine.get("state", "") or "")
    direction = str(engine.get("direction", "") or "").upper()
    negatives = engine.get("negative_factors", []) or []
    warnings = engine.get("warnings", []) or []
    if state in RISK_STATES:
        return True
    if negatives:
        return True
    if direction in {"BUY", "SELL"} and side.upper() in {"BUY", "SELL"} and direction != side.upper():
        return True
    if engine.get("engine") == "market_briefing" and warnings:
        return True
    if engine.get("engine") == "confidence_calibration" and "probabilidade_calibrada_menor" in negatives:
        return True
    return False


def flatten(events: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    event_rows = []
    engine_rows = []
    for event in events:
        candidate = event.get("candidate", {}) or {}
        result = event.get("result", {}) or {}
        side = str(candidate.get("side", "") or "")
        engines = event.get("engines", []) or []
        risky = [engine for engine in engines if engine.get("engine") in SHADOW_ENGINES and engine_risk_flag(engine, side)]
        event_rows.append(
            {
                "timestamp": event.get("timestamp", ""),
                "symbol": candidate.get("symbol", ""),
                "timeframe": candidate.get("timeframe", ""),
                "side": side,
                "strategy": candidate.get("strategy", ""),
                "p_buy": candidate.get("p_buy", 0.0),
                "p_sell": candidate.get("p_sell", 0.0),
                "decision": result.get("decision", ""),
                "reason": result.get("reason", ""),
                "tradeability_score": result.get("tradeability_score", 0.0),
                "conflict_score": result.get("conflict_score", 0.0),
                "shadow_risk_count": len(risky),
                "shadow_risk_engines": ",".join(str(engine.get("engine", "")) for engine in risky),
                "source_file": event.get("_source_file", ""),
                "source_line": event.get("_source_line", 0),
            }
        )
        for engine in engines:
            if engine.get("engine") not in SHADOW_ENGINES:
                continue
            features = engine.get("features", {}) or {}
            engine_rows.append(
                {
                    "timestamp": event.get("timestamp", ""),
                    "symbol": candidate.get("symbol", ""),
                    "timeframe": candidate.get("timeframe", ""),
                    "side": side,
                    "strategy": candidate.get("strategy", ""),
                    "decision": result.get("decision", ""),
                    "reason": result.get("reason", ""),
                    "engine": engine.get("engine", ""),
                    "engine_direction": engine.get("direction", ""),
                    "engine_state": engine.get("state", ""),
                    "engine_score": engine.get("score", 0.0),
                    "engine_confidence": engine.get("confidence", 0.0),
                    "risk_flag": engine_risk_flag(engine, side),
                    "negative_factors": ";".join(str(item) for item in engine.get("negative_factors", []) or []),
                    "warnings": ";".join(str(item) for item in engine.get("warnings", []) or []),
                    "context_score": features.get("context_score"),
                    "context_conflict_score": features.get("context_conflict_score"),
                    "calibrated_probability": features.get("calibrated_probability"),
                    "raw_probability": features.get("raw_probability"),
                }
            )
    return pd.DataFrame(event_rows), pd.DataFrame(engine_rows)


def write_markdown(path: Path, events: pd.DataFrame, engines: pd.DataFrame) -> None:
    lines = ["# Shadow Engine Report", ""]
    if events.empty:
        lines.append("Nenhum evento encontrado.")
        path.write_text("\n".join(lines), encoding="utf-8")
        return
    lines.extend(
        [
            f"- Eventos: {len(events)}",
            f"- Ativos: {events['symbol'].nunique()}",
            f"- Eventos com alerta shadow: {int((events['shadow_risk_count'].astype(float) > 0).sum())}",
            f"- Tradeability medio: {events['tradeability_score'].astype(float).mean():.3f}",
            "",
            "## Decisoes",
            "",
        ]
    )
    for decision, count in Counter(events["decision"]).most_common():
        lines.append(f"- {decision}: {count}")

    if not engines.empty:
        lines.extend(["", "## Alertas Por Engine", ""])
        risk = engines[engines["risk_flag"] == True]
        if risk.empty:
            lines.append("_Nenhum alerta shadow encontrado._")
        else:
            grouped = risk.groupby(["engine", "engine_state"]).size().reset_index(name="count")
            for row in grouped.sort_values("count", ascending=False).head(40).itertuples(index=False):
                lines.append(f"- {row.engine} / {row.engine_state}: {int(row.count)}")

    blocked_high = events[(events["decision"] == "BLOCK") & (events["tradeability_score"].astype(float) >= 0.55)]
    lines.extend(["", "## Bloqueios Com Tradeability Alto", ""])
    if blocked_high.empty:
        lines.append("_Nenhum bloqueio com tradeability alto._")
    else:
        for row in blocked_high.sort_values("tradeability_score", ascending=False).head(30).itertuples(index=False):
            lines.append(
                f"- {row.timestamp} {row.strategy} {row.symbol} {row.timeframe} {row.side}: "
                f"{row.reason} tradeability={float(row.tradeability_score):.3f} shadow={row.shadow_risk_engines}"
            )

    allowed_risky = events[(events["decision"] == "ALLOW") & (events["shadow_risk_count"].astype(float) > 0)]
    lines.extend(["", "## Entradas Permitidas Com Alerta Shadow", ""])
    if allowed_risky.empty:
        lines.append("_Nenhuma entrada permitida com alerta shadow._")
    else:
        for row in allowed_risky.sort_values("shadow_risk_count", ascending=False).head(30).itertuples(index=False):
            lines.append(
                f"- {row.timestamp} {row.strategy} {row.symbol} {row.timeframe} {row.side}: "
                f"shadow={row.shadow_risk_engines} tradeability={float(row.tradeability_score):.3f}"
            )

    if not engines.empty and "confidence_calibration" in set(engines["engine"]):
        cal = engines[(engines["engine"] == "confidence_calibration") & engines["calibrated_probability"].notna()]
        lines.extend(["", "## Calibracao", ""])
        if cal.empty:
            lines.append("_Sem eventos calibrados._")
        else:
            delta = cal["calibrated_probability"].astype(float) - cal["raw_probability"].astype(float)
            lines.append(f"- Eventos calibrados: {len(cal)}")
            lines.append(f"- Delta medio calibrado-bruto: {delta.mean():.4f}")
            lines.append(f"- Calibracao reduziu probabilidade em: {int((delta < 0).sum())} eventos")

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    events = list(iter_events(Path(args.log_dir), args.date))
    if args.tail and args.tail > 0:
        events = events[-args.tail :]
    events_df, engines_df = flatten(events)
    suffix = args.date if args.date else "all"
    if args.tail:
        suffix += f"_tail{args.tail}"
    events_df.to_csv(output_dir / f"shadow_engine_events_{suffix}.csv", index=False)
    engines_df.to_csv(output_dir / f"shadow_engine_engines_{suffix}.csv", index=False)
    write_markdown(output_dir / f"shadow_engine_report_{suffix}.md", events_df, engines_df)
    print(f"Eventos: {len(events_df)}")
    print(f"Engines: {len(engines_df)}")
    print(f"Saida: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
