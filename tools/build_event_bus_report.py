from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Relatorio dos eventos estruturados do FUSION.")
    parser.add_argument("--date", default="", help="Data YYYYMMDD. Se vazio, usa todos os arquivos.")
    parser.add_argument("--log-dir", default="logs/events")
    parser.add_argument("--output-dir", default="reports/event_bus")
    return parser.parse_args()


def iter_events(log_dir: Path, date: str):
    pattern = f"events_{date}.jsonl" if date else "events_*.jsonl"
    for path in sorted(log_dir.glob(pattern)):
        for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            event["_source_file"] = path.name
            event["_source_line"] = line_no
            yield event


def iter_events_with_optional_backfill(log_dir: Path, date: str):
    if log_dir.name == "events":
        backfill_dir = log_dir.parent / "events_backfill"
        yield from iter_events(backfill_dir, date)
    yield from iter_events(log_dir, date)


def flatten(events: list[dict]) -> pd.DataFrame:
    rows = []
    for event in events:
        data = event.get("data") or {}
        candidate = data.get("candidate") or {}
        result = data.get("result") or {}
        engine = data.get("engine") or {}
        rows.append(
            {
                "timestamp": event.get("timestamp", ""),
                "event_id": event.get("event_id", ""),
                "correlation_id": event.get("correlation_id", ""),
                "type": event.get("type", ""),
                "source": event.get("source", ""),
                "symbol": data.get("symbol") or candidate.get("symbol") or "",
                "broker_symbol": data.get("broker_symbol") or candidate.get("broker_symbol") or "",
                "timeframe": data.get("timeframe") or candidate.get("timeframe") or "",
                "strategy": data.get("strategy") or candidate.get("strategy") or "",
                "direction": data.get("direction") or candidate.get("side") or "",
                "status": data.get("status") or result.get("decision") or "",
                "reason": data.get("reason") or result.get("reason") or "",
                "engine": engine.get("engine", ""),
                "engine_state": engine.get("state", ""),
                "engine_score": engine.get("score", ""),
                "engine_confidence": engine.get("confidence", ""),
                "source_file": event.get("_source_file", ""),
                "source_line": event.get("_source_line", 0),
            }
        )
    return pd.DataFrame(rows)


def lifecycle_table(events_df: pd.DataFrame) -> pd.DataFrame:
    if events_df.empty:
        return pd.DataFrame()
    rows = []
    for correlation_id, group in events_df.groupby("correlation_id", dropna=False):
        types = set(group["type"].astype(str))
        decisions = group[group["type"] == "DECISION"]
        requests = group[group["type"] == "ORDER_REQUEST"]
        results = group[group["type"] == "ORDER_RESULT"]
        first = group.sort_values("timestamp").iloc[0]
        last = group.sort_values("timestamp").iloc[-1]
        rows.append(
            {
                "correlation_id": correlation_id,
                "symbol": first.get("symbol", ""),
                "timeframe": first.get("timeframe", ""),
                "strategy": first.get("strategy", ""),
                "types": ",".join(sorted(types)),
                "has_decision": "DECISION" in types,
                "has_order_request": "ORDER_REQUEST" in types,
                "has_order_result": "ORDER_RESULT" in types,
                "decision": decisions.iloc[-1].get("status", "") if not decisions.empty else "",
                "order_status": results.iloc[-1].get("status", "") if not results.empty else "",
                "reason": last.get("reason", ""),
                "events": len(group),
                "first_timestamp": first.get("timestamp", ""),
                "last_timestamp": last.get("timestamp", ""),
            }
        )
    return pd.DataFrame(rows)


def write_markdown(path: Path, events_df: pd.DataFrame, lifecycle_df: pd.DataFrame) -> None:
    lines = ["# Event Bus Report", ""]
    if events_df.empty:
        lines.append("Nenhum evento encontrado.")
        path.write_text("\n".join(lines), encoding="utf-8")
        return

    lines.extend(
        [
            f"- Eventos: {len(events_df)}",
            f"- Correlation IDs: {events_df['correlation_id'].nunique()}",
            f"- Ativos: {events_df['symbol'].replace('', pd.NA).dropna().nunique()}",
            "",
            "## Eventos Por Tipo",
            "",
        ]
    )
    for key, value in Counter(events_df["type"]).most_common():
        lines.append(f"- {key}: {value}")

    if not lifecycle_df.empty:
        lines.extend(["", "## Ciclo De Ordem", ""])
        order_cycles = lifecycle_df[lifecycle_df["has_order_request"] == True]
        lines.append(f"- Ciclos com ORDER_REQUEST: {len(order_cycles)}")
        lines.append(f"- Ciclos com ORDER_RESULT: {int(order_cycles['has_order_result'].sum()) if not order_cycles.empty else 0}")
        missing = order_cycles[order_cycles["has_order_result"] == False]
        lines.append(f"- Ciclos sem ORDER_RESULT: {len(missing)}")
        if not missing.empty:
            lines.extend(["", "### Ciclos Sem ORDER_RESULT", ""])
            for row in missing.tail(30).itertuples(index=False):
                lines.append(f"- {row.correlation_id} | {row.symbol} {row.timeframe} {row.strategy} | {row.reason}")

        lines.extend(["", "## Ultimos Ciclos", ""])
        for row in lifecycle_df.sort_values("last_timestamp", ascending=False).head(30).itertuples(index=False):
            lines.append(
                f"- {row.last_timestamp} | {row.symbol} {row.timeframe} {row.strategy} | "
                f"{row.decision}/{row.order_status} | {row.reason}"
            )

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    events = list(iter_events_with_optional_backfill(Path(args.log_dir), args.date))
    events_df = flatten(events)
    lifecycle_df = lifecycle_table(events_df)
    suffix = args.date if args.date else "all"
    events_df.to_csv(output_dir / f"event_bus_events_{suffix}.csv", index=False)
    lifecycle_df.to_csv(output_dir / f"event_bus_lifecycle_{suffix}.csv", index=False)
    write_markdown(output_dir / f"event_bus_report_{suffix}.md", events_df, lifecycle_df)
    print(f"Eventos: {len(events_df)}")
    print(f"Ciclos: {len(lifecycle_df)}")
    print(f"Saida: {output_dir}")


if __name__ == "__main__":
    main()
