from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analisa performance operacional por correlation_id.")
    parser.add_argument("--date", required=True, help="Data YYYYMMDD.")
    parser.add_argument("--events-dir", default="logs/events")
    parser.add_argument("--output-dir", default="reports/event_performance")
    return parser.parse_args()


def load_events(path: Path) -> list[dict]:
    events = []
    if not path.exists():
        return events
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def load_events_with_backfill(date: str, events_dir: str) -> list[dict]:
    events = load_events(ROOT / "logs" / "events_backfill" / f"events_{date}.jsonl")
    events.extend(load_events(ROOT / events_dir / f"events_{date}.jsonl"))
    seen = set()
    unique = []
    for event in events:
        key = event.get("event_id") or json.dumps(event, sort_keys=True, default=str)
        if key in seen:
            continue
        seen.add(key)
        unique.append(event)
    return unique


def main() -> None:
    args = parse_args()
    events = load_events_with_backfill(args.date, args.events_dir)
    trade_profit_by_order: dict[str, float] = {}
    trade_count_by_order: dict[str, int] = {}
    for event in events:
        if event.get("type") != "TRADE_UPDATE":
            continue
        data = event.get("data") or {}
        order_id = str(data.get("order_id", "") or "")
        if not order_id:
            continue
        trade_profit_by_order[order_id] = trade_profit_by_order.get(order_id, 0.0) + float(data.get("profit", 0.0) or 0.0)
        trade_count_by_order[order_id] = trade_count_by_order.get(order_id, 0) + 1

    grouped = defaultdict(list)
    for event in events:
        grouped[event.get("correlation_id") or event.get("event_id")].append(event)

    rows = []
    for correlation_id, items in grouped.items():
        ordered = sorted(items, key=lambda item: item.get("timestamp", ""))
        decisions = [item for item in ordered if item.get("type") == "DECISION"]
        order_results = [item for item in ordered if item.get("type") == "ORDER_RESULT"]
        position_updates = [item for item in ordered if item.get("type") == "POSITION_UPDATE"]
        trade_updates = [item for item in ordered if item.get("type") == "TRADE_UPDATE"]
        engine_results = [item for item in ordered if item.get("type") == "ENGINE_RESULT"]

        first_data = (ordered[0].get("data") or {}) if ordered else {}
        candidate = first_data.get("candidate") or {}
        result_data = (order_results[-1].get("data") or {}) if order_results else {}
        last_position = (position_updates[-1].get("data") or {}) if position_updates else {}
        trade_profit = sum(float((item.get("data") or {}).get("profit", 0.0) or 0.0) for item in trade_updates)
        ticket = str((result_data.get("metadata") or {}).get("ticket", "") or "")
        if ticket and ticket in trade_profit_by_order:
            trade_profit = trade_profit_by_order[ticket]
            trade_updates = trade_updates or [{"data": {"order_id": ticket}}] * trade_count_by_order.get(ticket, 1)
        decision_result = ((decisions[-1].get("data") or {}).get("result") or {}) if decisions else {}

        rows.append(
            {
                "correlation_id": correlation_id,
                "symbol": first_data.get("symbol") or candidate.get("symbol") or result_data.get("symbol") or "",
                "timeframe": first_data.get("timeframe") or candidate.get("timeframe") or result_data.get("timeframe") or "",
                "strategy": first_data.get("strategy") or candidate.get("strategy") or result_data.get("strategy") or "",
                "side": candidate.get("side") or result_data.get("direction") or "",
                "decision": decision_result.get("decision", ""),
                "decision_reason": decision_result.get("reason", ""),
                "tradeability_score": decision_result.get("tradeability_score", ""),
                "conflict_score": decision_result.get("conflict_score", ""),
                "order_status": result_data.get("status", ""),
                "order_reason": result_data.get("reason", ""),
                "ticket": ticket,
                "last_position_profit": last_position.get("profit", ""),
                "trade_profit": trade_profit if trade_updates else "",
                "trade_count": len(trade_updates),
                "engine_count": len(engine_results),
                "event_count": len(ordered),
                "first_timestamp": ordered[0].get("timestamp", "") if ordered else "",
                "last_timestamp": ordered[-1].get("timestamp", "") if ordered else "",
            }
        )

    output_dir = ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(output_dir / f"event_performance_{args.date}.csv", index=False)

    lines = ["# Event Performance", "", f"- Correlation IDs: {len(df)}"]
    if not df.empty:
        sent = df[df["order_status"].astype(str).str.len() > 0]
        lines.append(f"- Ciclos com resultado de ordem: {len(sent)}")
        filled = df[df["order_status"].astype(str) == "FILLED"]
        lines.append(f"- FILLED: {len(filled)}")
        rejected = df[df["order_status"].astype(str).isin(["FAILED", "REJECTED"])]
        lines.append(f"- FAILED/REJECTED: {len(rejected)}")
        lines.extend(["", "## Ultimos Ciclos", ""])
        for row in df.sort_values("last_timestamp", ascending=False).head(40).itertuples(index=False):
            lines.append(
                f"- {row.last_timestamp} | {row.symbol} {row.timeframe} {row.strategy} {row.side} | "
                f"decision={row.decision}:{row.decision_reason} order={row.order_status}:{row.order_reason} "
                f"position_profit={row.last_position_profit} trade_profit={row.trade_profit}"
            )
    (output_dir / f"event_performance_{args.date}.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Eventos: {len(events)}")
    print(f"Ciclos: {len(df)}")
    print(f"Saida: {output_dir}")


if __name__ == "__main__":
    main()
