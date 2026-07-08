from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def load_events(date: str) -> list[dict]:
    path = ROOT / "logs" / "events" / f"events_{date}.jsonl"
    if not path.exists():
        raise SystemExit(f"Arquivo nao encontrado: {path}")
    events = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay/resumo dos eventos estruturados do FUSION.")
    parser.add_argument("--date", required=True, help="Data no formato YYYYMMDD.")
    parser.add_argument("--symbol", default="", help="Filtra por ativo/simbolo.")
    parser.add_argument("--limit", type=int, default=50, help="Quantidade de eventos recentes na timeline.")
    parser.add_argument("--output-dir", default="reports/event_replay", help="Diretorio de saida para CSV/MD.")
    args = parser.parse_args()

    events = load_events(args.date)
    symbol_filter = args.symbol.upper().strip()
    if symbol_filter:
        events = [
            event for event in events
            if symbol_filter in str(event.get("correlation_id", "")).upper()
            or symbol_filter in str((event.get("data") or {}).get("symbol", "")).upper()
            or symbol_filter in str(((event.get("data") or {}).get("candidate") or {}).get("symbol", "")).upper()
        ]

    counts = Counter(str(event.get("type", "") or "") for event in events)
    by_symbol = Counter()
    lifecycle = defaultdict(list)
    for event in events:
        data = event.get("data") or {}
        candidate = data.get("candidate") or {}
        symbol = data.get("symbol") or candidate.get("symbol") or str(event.get("correlation_id", "")).split(":")[0]
        if symbol:
            by_symbol[str(symbol).upper()] += 1
        corr = event.get("correlation_id") or event.get("event_id")
        lifecycle[corr].append(event)

    print(f"Eventos: {len(events)}")
    print("Por tipo:")
    for key, value in counts.most_common():
        print(f"  {key}: {value}")
    print("Por ativo:")
    for key, value in by_symbol.most_common(30):
        print(f"  {key}: {value}")

    print("Timeline recente:")
    for event in events[-max(1, args.limit):]:
        data = event.get("data") or {}
        candidate = data.get("candidate") or {}
        result = data.get("result") or {}
        symbol = data.get("symbol") or candidate.get("symbol") or "-"
        tf = data.get("timeframe") or candidate.get("timeframe") or "-"
        status = data.get("status") or result.get("decision") or "-"
        reason = data.get("reason") or result.get("reason") or "-"
        print(f"  {event.get('timestamp')} | {event.get('type')} | {symbol} {tf} | {status} | {reason}")

    output_dir = ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = args.date if not symbol_filter else f"{args.date}_{symbol_filter}"
    rows = []
    cycle_rows = []
    for event in events:
        data = event.get("data") or {}
        candidate = data.get("candidate") or {}
        result = data.get("result") or {}
        engine = data.get("engine") or {}
        rows.append(
            {
                "timestamp": event.get("timestamp", ""),
                "type": event.get("type", ""),
                "source": event.get("source", ""),
                "correlation_id": event.get("correlation_id", ""),
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
    for correlation_id, items in lifecycle.items():
        ordered = sorted(items, key=lambda item: item.get("timestamp", ""))
        types = {str(item.get("type", "")) for item in ordered}
        first_data = ordered[0].get("data") or {}
        first_candidate = first_data.get("candidate") or {}
        last_data = ordered[-1].get("data") or {}
        last_result = last_data.get("result") or {}
        cycle_rows.append(
            {
                "correlation_id": correlation_id,
                "symbol": first_data.get("symbol") or first_candidate.get("symbol") or "",
                "timeframe": first_data.get("timeframe") or first_candidate.get("timeframe") or "",
                "strategy": first_data.get("strategy") or first_candidate.get("strategy") or "",
                "has_decision": "DECISION" in types,
                "has_engine_result": "ENGINE_RESULT" in types,
                "has_order_request": "ORDER_REQUEST" in types,
                "has_order_result": "ORDER_RESULT" in types,
                "events": len(ordered),
                "first_timestamp": ordered[0].get("timestamp", ""),
                "last_timestamp": ordered[-1].get("timestamp", ""),
                "last_type": ordered[-1].get("type", ""),
                "last_status": last_data.get("status") or last_result.get("decision") or "",
                "last_reason": last_data.get("reason") or last_result.get("reason") or "",
            }
        )

    events_df = pd.DataFrame(rows)
    cycles_df = pd.DataFrame(cycle_rows)
    events_df.to_csv(output_dir / f"event_replay_events_{suffix}.csv", index=False)
    cycles_df.to_csv(output_dir / f"event_replay_cycles_{suffix}.csv", index=False)
    md_lines = ["# Event Replay", "", f"- Eventos: {len(events_df)}", f"- Ciclos: {len(cycles_df)}", ""]
    if not cycles_df.empty:
        order_cycles = cycles_df[cycles_df["has_order_request"] == True]
        md_lines.extend(
            [
                "## Ciclos",
                "",
                f"- Com ORDER_REQUEST: {len(order_cycles)}",
                f"- Sem ORDER_RESULT: {int((order_cycles['has_order_result'] == False).sum()) if not order_cycles.empty else 0}",
                "",
                "## Recentes",
                "",
            ]
        )
        for row in cycles_df.sort_values("last_timestamp", ascending=False).head(30).itertuples(index=False):
            md_lines.append(
                f"- {row.last_timestamp} | {row.symbol} {row.timeframe} {row.strategy} | "
                f"{row.last_type} {row.last_status} | {row.last_reason}"
            )
    (output_dir / f"event_replay_{suffix}.md").write_text("\n".join(md_lines), encoding="utf-8")
    print(f"Saida: {output_dir}")


if __name__ == "__main__":
    main()
