from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resume logs JSONL do Decision Audit.")
    parser.add_argument("--log-dir", default="logs/decision_audit")
    parser.add_argument("--output-dir", default="reports/decision_audit")
    parser.add_argument("--date", default="", help="Data YYYYMMDD. Se vazio, le todos os arquivos.")
    return parser.parse_args()


def iter_events(log_dir: Path, date: str):
    pattern = f"decision_audit_{date}.jsonl" if date else "decision_audit_*.jsonl"
    for path in sorted(log_dir.glob(pattern)):
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                event["_source_file"] = path.name
                yield event


def flatten(events: list[dict]) -> pd.DataFrame:
    rows = []
    for event in events:
        candidate = event.get("candidate", {}) or {}
        result = event.get("result", {}) or {}
        explanation = event.get("explanation", {}) or {}
        engines = event.get("engines", []) or []
        rows.append(
            {
                "timestamp": event.get("timestamp", ""),
                "correlation_id": event.get("correlation_id", ""),
                "symbol": candidate.get("symbol", ""),
                "timeframe": candidate.get("timeframe", ""),
                "side": candidate.get("side", ""),
                "strategy": candidate.get("strategy", ""),
                "p_buy": candidate.get("p_buy", 0.0),
                "p_sell": candidate.get("p_sell", 0.0),
                "decision": result.get("decision", ""),
                "reason": result.get("reason", ""),
                "consensus_score": result.get("consensus_score", 0.0),
                "conflict_score": result.get("conflict_score", 0.0),
                "tradeability_score": result.get("tradeability_score", 0.0),
                "position_multiplier": result.get("position_multiplier", 1.0),
                "xai_final_score": explanation.get("final_score", 0.0),
                "xai_confidence_band": explanation.get("confidence_band", ""),
                "xai_summary": explanation.get("summary", ""),
                "xai_positive": ";".join(str(item.get("factor", "")) for item in explanation.get("top_positive_factors", []) or []),
                "xai_negative": ";".join(str(item.get("factor", "")) for item in explanation.get("top_negative_factors", []) or []),
                "engines": ",".join(str(engine.get("engine", "")) for engine in engines),
                "source_file": event.get("_source_file", ""),
            }
        )
    return pd.DataFrame(rows)


def engine_rows(events: list[dict]) -> pd.DataFrame:
    rows = []
    for event in events:
        candidate = event.get("candidate", {}) or {}
        result = event.get("result", {}) or {}
        for engine in event.get("engines", []) or []:
            rows.append(
                {
                    "timestamp": event.get("timestamp", ""),
                    "correlation_id": event.get("correlation_id", ""),
                    "symbol": candidate.get("symbol", ""),
                    "timeframe": candidate.get("timeframe", ""),
                    "side": candidate.get("side", ""),
                    "strategy": candidate.get("strategy", ""),
                    "decision": result.get("decision", ""),
                    "reason": result.get("reason", ""),
                    "engine": engine.get("engine", ""),
                    "engine_direction": engine.get("direction", ""),
                    "engine_score": engine.get("score", 0.0),
                    "engine_confidence": engine.get("confidence", 0.0),
                    "engine_state": engine.get("state", ""),
                    "positive_factors": ";".join(str(item) for item in engine.get("positive_factors", []) or []),
                    "negative_factors": ";".join(str(item) for item in engine.get("negative_factors", []) or []),
                    "warnings": ";".join(str(item) for item in engine.get("warnings", []) or []),
                }
            )
    return pd.DataFrame(rows)


def write_markdown(path: Path, events_df: pd.DataFrame, engines_df: pd.DataFrame) -> None:
    lines = ["# Decision Audit Summary", ""]
    if events_df.empty:
        lines.append("Nenhum evento encontrado.")
        path.write_text("\n".join(lines), encoding="utf-8")
        return

    lines.extend(
        [
            f"- Eventos: {len(events_df)}",
            f"- Ativos: {events_df['symbol'].nunique()}",
            f"- Estrategias: {events_df['strategy'].nunique()}",
            f"- Tradeability medio: {events_df['tradeability_score'].astype(float).mean():.3f}",
            "",
            "## Decisoes",
            "",
        ]
    )
    for decision, count in Counter(events_df["decision"]).most_common():
        lines.append(f"- {decision}: {count}")

    lines.extend(["", "## Motivos", ""])
    for reason, count in Counter(events_df["reason"]).most_common(30):
        lines.append(f"- {reason}: {count}")

    if "xai_confidence_band" in events_df.columns:
        bands = events_df["xai_confidence_band"].fillna("").astype(str)
        bands = bands[bands != ""]
        if not bands.empty:
            lines.extend(["", "## XAI - Faixa de Confianca", ""])
            for band, count in Counter(bands).most_common():
                lines.append(f"- {band}: {count}")

    if not engines_df.empty:
        lines.extend(["", "## Engines", ""])
        grouped = engines_df.groupby(["engine", "engine_direction"]).size().reset_index(name="count")
        for row in grouped.sort_values(["engine", "count"], ascending=[True, False]).itertuples(index=False):
            lines.append(f"- {row.engine} {row.engine_direction}: {int(row.count)}")

    output = events_df.sort_values("timestamp", ascending=False).head(30)
    lines.extend(["", "## Ultimos eventos", ""])
    for row in output.itertuples(index=False):
        lines.append(
            f"- {row.timestamp} {row.strategy} {row.symbol} {row.timeframe} {row.side}: "
            f"{row.decision} {row.reason} tradeability={float(row.tradeability_score):.3f}"
        )
        summary = getattr(row, "xai_summary", "")
        if summary:
            lines.append(f"  - XAI: {summary}")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    events = list(iter_events(Path(args.log_dir), args.date))
    events_df = flatten(events)
    engines_df = engine_rows(events)
    suffix = args.date if args.date else "all"
    events_df.to_csv(output_dir / f"decision_audit_events_{suffix}.csv", index=False)
    engines_df.to_csv(output_dir / f"decision_audit_engines_{suffix}.csv", index=False)
    write_markdown(output_dir / f"decision_audit_summary_{suffix}.md", events_df, engines_df)
    print(f"Eventos: {len(events_df)}")
    print(f"Saida: {output_dir}")


if __name__ == "__main__":
    main()
