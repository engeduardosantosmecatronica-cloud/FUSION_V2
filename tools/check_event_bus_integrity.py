from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
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


def load_events(date: str, include_backfill: bool) -> list[dict]:
    events = []
    if include_backfill:
        events.extend(read_jsonl(ROOT / "logs" / "events_backfill" / f"events_{date}.jsonl"))
    events.extend(read_jsonl(ROOT / "logs" / "events" / f"events_{date}.jsonl"))
    seen = set()
    unique = []
    for event in events:
        key = event.get("event_id") or json.dumps(event, sort_keys=True, default=str)
        if key in seen:
            continue
        seen.add(key)
        unique.append(event)
    return sorted(unique, key=lambda item: item.get("timestamp", ""))


def event_symbol(event: dict) -> str:
    data = event.get("data") or {}
    candidate = data.get("candidate") or {}
    return str(data.get("symbol") or candidate.get("symbol") or "").upper()


def event_timeframe(event: dict) -> str:
    data = event.get("data") or {}
    candidate = data.get("candidate") or {}
    return str(data.get("timeframe") or candidate.get("timeframe") or "").upper()


def main() -> None:
    parser = argparse.ArgumentParser(description="Valida integridade do Event Bus do FUSION.")
    parser.add_argument("--date", required=True, help="Data YYYYMMDD.")
    parser.add_argument("--include-backfill", action="store_true", help="Inclui eventos reconstruidos do decision_audit.")
    parser.add_argument("--output-dir", default="reports/event_bus")
    args = parser.parse_args()

    events = load_events(args.date, include_backfill=args.include_backfill)
    by_corr: dict[str, list[dict]] = defaultdict(list)
    for event in events:
        by_corr[str(event.get("correlation_id") or event.get("event_id"))].append(event)

    rows = []
    for corr, group in by_corr.items():
        types = Counter(str(item.get("type", "") or "") for item in group)
        ordered = sorted(group, key=lambda item: item.get("timestamp", ""))
        decisions = [item for item in group if item.get("type") == "DECISION"]
        order_requests = [item for item in group if item.get("type") == "ORDER_REQUEST"]
        order_results = [item for item in group if item.get("type") == "ORDER_RESULT"]
        engine_results = [item for item in group if item.get("type") == "ENGINE_RESULT"]
        signals = [item for item in group if item.get("type") == "SIGNAL"]
        issues = []

        if decisions and not engine_results and not args.include_backfill:
            issues.append("decision_sem_engine_result")
        if order_requests and not decisions:
            issues.append("order_request_sem_decision")
        if order_requests and not order_results:
            issues.append("order_request_sem_order_result")
        if order_results and not order_requests:
            issues.append("order_result_sem_order_request")
        if decisions and not signals:
            # S4/setup blocks and strategy-level blocks can exist without SIGNAL in older paths, so warning only.
            issues.append("decision_sem_signal")
        if len(order_results) > 1:
            issues.append("multiplos_order_result")

        first = ordered[0] if ordered else {}
        last = ordered[-1] if ordered else {}
        data_last = last.get("data") or {}
        result_last = data_last.get("result") or {}
        rows.append(
            {
                "correlation_id": corr,
                "symbol": event_symbol(first) or event_symbol(last),
                "timeframe": event_timeframe(first) or event_timeframe(last),
                "events": len(group),
                "types": ",".join(sorted(types)),
                "signal": len(signals),
                "engine_result": len(engine_results),
                "decision": len(decisions),
                "order_request": len(order_requests),
                "order_result": len(order_results),
                "last_type": last.get("type", ""),
                "last_status": data_last.get("status") or result_last.get("decision") or "",
                "last_reason": data_last.get("reason") or result_last.get("reason") or "",
                "issues": ";".join(issues),
                "issue_count": len(issues),
                "first_timestamp": first.get("timestamp", ""),
                "last_timestamp": last.get("timestamp", ""),
            }
        )

    df = pd.DataFrame(rows)
    output_dir = ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"{args.date}_with_backfill" if args.include_backfill else args.date
    df.to_csv(output_dir / f"event_bus_integrity_{suffix}.csv", index=False)

    lines = ["# Event Bus Integrity", "", f"- Data: {args.date}", f"- Eventos: {len(events)}", f"- Ciclos: {len(df)}"]
    if not df.empty:
        issue_df = df[df["issue_count"].astype(int) > 0]
        lines.append(f"- Ciclos com alerta: {len(issue_df)}")
        lines.extend(["", "## Alertas", ""])
        if issue_df.empty:
            lines.append("_Nenhum alerta._")
        else:
            exploded = []
            for value in issue_df["issues"].fillna("").astype(str):
                exploded.extend([item for item in value.split(";") if item])
            for key, value in Counter(exploded).most_common():
                lines.append(f"- {key}: {value}")
            lines.extend(["", "## Amostras", ""])
            for row in issue_df.sort_values("last_timestamp", ascending=False).head(40).itertuples(index=False):
                lines.append(f"- {row.last_timestamp} | {row.symbol} {row.timeframe} | {row.issues} | {row.last_reason}")
    (output_dir / f"event_bus_integrity_{suffix}.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"Eventos: {len(events)}")
    print(f"Ciclos: {len(df)}")
    print(f"Alertas: {int((df['issue_count'].astype(int) > 0).sum()) if not df.empty else 0}")
    print(f"Saida: {output_dir}")


if __name__ == "__main__":
    main()
