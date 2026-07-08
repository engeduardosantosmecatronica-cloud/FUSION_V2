from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_events(date: str) -> list[dict]:
    events = []
    for folder in ["events_backfill", "events"]:
        path = ROOT / "logs" / folder / f"events_{date}.jsonl"
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return sorted(events, key=lambda item: item.get("timestamp", ""))


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconstrói estado OMS a partir do Event Bus.")
    parser.add_argument("--date", required=True, help="Data YYYYMMDD.")
    parser.add_argument("--output-dir", default="reports/oms_replay")
    args = parser.parse_args()

    state = {
        "account": {},
        "orders": {},
        "positions": {},
        "ticks": {},
        "trades": {},
        "contracts": {},
        "decisions": {},
        "signals": {},
    }
    events = load_events(args.date)
    for event in events:
        event_type = event.get("type")
        data = event.get("data") or {}
        corr = event.get("correlation_id") or event.get("event_id")
        if event_type == "ACCOUNT_UPDATE":
            state["account"] = data
        elif event_type in {"ORDER_REQUEST", "ORDER_RESULT"}:
            order_id = str(data.get("order_id") or corr)
            state["orders"][order_id] = data
        elif event_type == "POSITION_UPDATE":
            position_id = str(data.get("position_id") or corr)
            state["positions"][position_id] = data
        elif event_type == "TICK_UPDATE":
            symbol = str(data.get("symbol") or "")
            if symbol:
                state["ticks"][symbol] = data
        elif event_type == "TRADE_UPDATE":
            trade_id = str(data.get("trade_id") or corr)
            state["trades"][trade_id] = data
        elif event_type == "DASHBOARD_UPDATE" and isinstance(data.get("contract"), dict):
            contract = data.get("contract") or {}
            symbol = str(contract.get("symbol") or "")
            if symbol:
                state["contracts"][symbol] = contract
        elif event_type == "DECISION":
            state["decisions"][corr] = data
        elif event_type == "SIGNAL":
            state["signals"][corr] = data

    summary = {
        "date": args.date,
        "events": len(events),
        "orders": len(state["orders"]),
        "positions": len(state["positions"]),
        "trades": len(state["trades"]),
        "ticks": len(state["ticks"]),
        "contracts": len(state["contracts"]),
        "decisions": len(state["decisions"]),
        "signals": len(state["signals"]),
        "account": state["account"],
    }

    output_dir = ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"oms_replay_state_{args.date}.json").write_text(
        json.dumps({"summary": summary, "state": state}, ensure_ascii=False, default=str, indent=2),
        encoding="utf-8",
    )
    lines = ["# OMS Replay State", ""]
    for key, value in summary.items():
        if key == "account":
            continue
        lines.append(f"- {key}: {value}")
    if summary["account"]:
        lines.extend(["", "## Account", ""])
        for key, value in summary["account"].items():
            lines.append(f"- {key}: {value}")
    (output_dir / f"oms_replay_state_{args.date}.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Eventos: {len(events)}")
    print(f"Saida: {output_dir}")


if __name__ == "__main__":
    main()
