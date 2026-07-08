from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Valida cruzamento financeiro por ordem/ticket no Event Bus.")
    parser.add_argument("--date", required=True, help="Data YYYYMMDD.")
    parser.add_argument("--events-dir", default="logs/events")
    parser.add_argument("--output-dir", default="reports/order_financial_cross")
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def load_events(date: str, events_dir: str) -> list[dict[str, Any]]:
    events = load_jsonl(ROOT / "logs" / "events_backfill" / f"events_{date}.jsonl")
    events.extend(load_jsonl(ROOT / events_dir / f"events_{date}.jsonl"))
    seen = set()
    unique = []
    for event in events:
        key = event.get("event_id") or json.dumps(event, sort_keys=True, default=str)
        if key in seen:
            continue
        seen.add(key)
        unique.append(event)
    return unique


def _data(event: dict[str, Any]) -> dict[str, Any]:
    data = event.get("data") or {}
    return data if isinstance(data, dict) else {}


def _ticket_from_order(data: dict[str, Any]) -> str:
    metadata = data.get("metadata") or {}
    return str(metadata.get("ticket") or data.get("ticket") or data.get("order_id") or "")


def main() -> None:
    args = parse_args()
    events = load_events(args.date, args.events_dir)
    orders = [event for event in events if event.get("type") == "ORDER_RESULT"]
    requests = [event for event in events if event.get("type") == "ORDER_REQUEST"]
    trades = [event for event in events if event.get("type") == "TRADE_UPDATE"]
    positions = [event for event in events if event.get("type") == "POSITION_UPDATE"]

    trades_by_order: dict[str, list[dict[str, Any]]] = {}
    for event in trades:
        data = _data(event)
        order_id = str(data.get("order_id") or data.get("ticket") or "")
        if order_id:
            trades_by_order.setdefault(order_id, []).append(event)

    positions_by_ticket: dict[str, list[dict[str, Any]]] = {}
    for event in positions:
        data = _data(event)
        position_id = str(data.get("position_id") or data.get("ticket") or "")
        if position_id:
            positions_by_ticket.setdefault(position_id, []).append(event)

    rows = []
    for event in orders:
        data = _data(event)
        ticket = _ticket_from_order(data)
        related_trades = trades_by_order.get(ticket, [])
        related_positions = positions_by_ticket.get(ticket, [])
        trade_profit = sum(float(_data(item).get("profit", 0.0) or 0.0) for item in related_trades)
        last_position = _data(sorted(related_positions, key=lambda item: item.get("timestamp", ""))[-1]) if related_positions else {}
        rows.append(
            {
                "timestamp": event.get("timestamp", ""),
                "correlation_id": event.get("correlation_id", ""),
                "symbol": data.get("symbol", ""),
                "broker_symbol": data.get("broker_symbol", ""),
                "timeframe": data.get("timeframe", ""),
                "strategy": data.get("strategy", ""),
                "direction": data.get("direction", ""),
                "status": data.get("status", ""),
                "reason": data.get("reason", ""),
                "ticket": ticket,
                "has_ticket": bool(ticket and ticket != "0"),
                "trade_updates": len(related_trades),
                "position_updates": len(related_positions),
                "trade_profit": trade_profit if related_trades else "",
                "last_position_profit": last_position.get("profit", ""),
                "last_position_volume": last_position.get("volume", ""),
            }
        )

    output_dir = ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(output_dir / f"order_financial_cross_{args.date}.csv", index=False)

    lines = [
        "# Order Financial Cross",
        "",
        f"- Data: {args.date}",
        f"- Eventos: {len(events)}",
        f"- ORDER_REQUEST: {len(requests)}",
        f"- ORDER_RESULT: {len(orders)}",
        f"- TRADE_UPDATE: {len(trades)}",
        f"- POSITION_UPDATE: {len(positions)}",
    ]
    if df.empty:
        lines.extend(
            [
                "",
                "## Resultado",
                "",
                "Nenhum ORDER_RESULT encontrado. Ainda nao ha ordem executada/rejeitada no Event Bus para validar por ticket/order_id.",
            ]
        )
    else:
        with_ticket = int(df["has_ticket"].sum())
        with_trade = int((df["trade_updates"] > 0).sum())
        with_position = int((df["position_updates"] > 0).sum())
        missing_financial = df[(df["status"].astype(str) == "FILLED") & (df["trade_updates"] == 0) & (df["position_updates"] == 0)]
        lines.extend(
            [
                "",
                "## Resultado",
                "",
                f"- ORDER_RESULT com ticket: {with_ticket}",
                f"- ORDER_RESULT com TRADE_UPDATE relacionado: {with_trade}",
                f"- ORDER_RESULT com POSITION_UPDATE relacionado: {with_position}",
                f"- FILLED sem trade/position relacionado: {len(missing_financial)}",
                "",
                "## Ultimas Ordens",
                "",
            ]
        )
        for row in df.sort_values("timestamp", ascending=False).head(40).itertuples(index=False):
            lines.append(
                f"- {row.timestamp} | {row.symbol} {row.timeframe} {row.strategy} {row.direction} "
                f"| status={row.status} ticket={row.ticket or '-'} trades={row.trade_updates} "
                f"positions={row.position_updates} profit={row.trade_profit}"
            )

    (output_dir / f"order_financial_cross_{args.date}.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Eventos: {len(events)}")
    print(f"ORDER_RESULT: {len(orders)}")
    print(f"Saida: {output_dir}")


if __name__ == "__main__":
    main()
