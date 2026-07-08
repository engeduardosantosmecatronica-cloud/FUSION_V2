from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def read_events_with_backfill(date: str) -> list[dict]:
    events = read_jsonl(ROOT / "logs" / "events_backfill" / f"events_{date}.jsonl")
    events.extend(read_jsonl(ROOT / "logs" / "events" / f"events_{date}.jsonl"))
    seen = set()
    unique = []
    for event in events:
        key = event.get("event_id") or json.dumps(event, sort_keys=True, default=str)
        if key in seen:
            continue
        seen.add(key)
        unique.append(event)
    return unique


def flatten_decision_audit(events: list[dict]) -> pd.DataFrame:
    rows = []
    for event in events:
        candidate = event.get("candidate") or {}
        result = event.get("result") or {}
        rows.append(
            {
                "timestamp": event.get("timestamp", ""),
                "correlation_id": event.get("correlation_id", ""),
                "symbol": candidate.get("symbol", ""),
                "timeframe": candidate.get("timeframe", ""),
                "strategy": candidate.get("strategy", ""),
                "side": candidate.get("side", ""),
                "p_buy": candidate.get("p_buy", 0.0),
                "p_sell": candidate.get("p_sell", 0.0),
                "decision": result.get("decision", ""),
                "reason": result.get("reason", ""),
                "tradeability_score": result.get("tradeability_score", 0.0),
                "conflict_score": result.get("conflict_score", 0.0),
            }
        )
    return pd.DataFrame(rows)


def flatten_event_bus(events: list[dict]) -> pd.DataFrame:
    rows = []
    for event in events:
        data = event.get("data") or {}
        candidate = data.get("candidate") or {}
        result = data.get("result") or {}
        engine = data.get("engine") or {}
        rows.append(
            {
                "timestamp": event.get("timestamp", ""),
                "correlation_id": event.get("correlation_id", ""),
                "type": event.get("type", ""),
                "source": event.get("source", ""),
                "symbol": data.get("symbol") or candidate.get("symbol") or "",
                "timeframe": data.get("timeframe") or candidate.get("timeframe") or "",
                "strategy": data.get("strategy") or candidate.get("strategy") or "",
                "direction": data.get("direction") or candidate.get("side") or "",
                "status": data.get("status") or result.get("decision") or "",
                "reason": data.get("reason") or result.get("reason") or "",
                "engine": engine.get("engine", ""),
                "engine_state": engine.get("state", ""),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Relatorio operacional diario consolidado.")
    parser.add_argument("--date", required=True, help="Data YYYYMMDD.")
    parser.add_argument("--output-dir", default="reports/operational_day")
    args = parser.parse_args()

    audit_df = flatten_decision_audit(read_jsonl(ROOT / "logs" / "decision_audit" / f"decision_audit_{args.date}.jsonl"))
    event_df = flatten_event_bus(read_events_with_backfill(args.date))
    lifecycle_df = flatten_event_bus(read_jsonl(ROOT / "logs" / "order_lifecycle" / f"order_lifecycle_{args.date}.jsonl"))

    output_dir = ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    audit_df.to_csv(output_dir / f"operational_decisions_{args.date}.csv", index=False)
    event_df.to_csv(output_dir / f"operational_events_{args.date}.csv", index=False)
    lifecycle_df.to_csv(output_dir / f"operational_lifecycle_{args.date}.csv", index=False)

    lines = ["# Operational Day Report", "", f"- Data: {args.date}"]
    lines.append(f"- Decision audit: {len(audit_df)}")
    lines.append(f"- Event Bus: {len(event_df)}")
    lines.append(f"- Order lifecycle: {len(lifecycle_df)}")

    if not audit_df.empty:
        lines.extend(["", "## Decisoes", ""])
        for key, value in Counter(audit_df["decision"]).most_common():
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Motivos De Bloqueio", ""])
        blocked = audit_df[audit_df["decision"] == "BLOCK"]
        for key, value in Counter(blocked["reason"]).most_common(30):
            lines.append(f"- {key}: {value}")

    if not event_df.empty:
        lines.extend(["", "## Event Bus Por Tipo", ""])
        for key, value in Counter(event_df["type"]).most_common():
            lines.append(f"- {key}: {value}")
        signal_count = int((event_df["type"] == "SIGNAL").sum())
        decision_count = int((event_df["type"] == "DECISION").sum())
        engine_count = int((event_df["type"] == "ENGINE_RESULT").sum())
        lines.extend(
            [
                "",
                "## Cobertura Do Barramento",
                "",
                f"- SIGNAL: {signal_count}",
                f"- DECISION: {decision_count}",
                f"- ENGINE_RESULT: {engine_count}",
            ]
        )

    if not lifecycle_df.empty:
        lines.extend(["", "## Ciclo De Ordem", ""])
        for key, value in Counter(lifecycle_df["type"]).most_common():
            lines.append(f"- {key}: {value}")

    if not audit_df.empty and not event_df.empty and "correlation_id" in audit_df.columns:
        audit_corr = set(audit_df["correlation_id"].dropna().astype(str))
        event_corr = set(event_df["correlation_id"].dropna().astype(str))
        audit_corr.discard("")
        event_corr.discard("")
        missing_in_events = sorted(audit_corr - event_corr)
        lines.extend(["", "## Integridade Correlation ID", ""])
        lines.append(f"- Audit corr IDs: {len(audit_corr)}")
        lines.append(f"- Event corr IDs: {len(event_corr)}")
        lines.append(f"- Audit sem evento correspondente: {len(missing_in_events)}")
        for item in missing_in_events[:30]:
            lines.append(f"  - {item}")

    (output_dir / f"operational_day_report_{args.date}.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Decision audit: {len(audit_df)}")
    print(f"Event Bus: {len(event_df)}")
    print(f"Lifecycle: {len(lifecycle_df)}")
    print(f"Saida: {output_dir}")


if __name__ == "__main__":
    main()
