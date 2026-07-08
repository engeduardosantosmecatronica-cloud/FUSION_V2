from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspeciona ORDER_REQUEST/ORDER_RESULT/POSITION_UPDATE do FUSION.")
    parser.add_argument("--date", required=True, help="Data no formato YYYYMMDD.")
    parser.add_argument("--symbol", default="", help="Filtra por ativo.")
    args = parser.parse_args()

    path = ROOT / "logs" / "order_lifecycle" / f"order_lifecycle_{args.date}.jsonl"
    if not path.exists():
        raise SystemExit(f"Arquivo nao encontrado: {path}")

    events = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        data = event.get("data") or {}
        symbol = str(data.get("symbol", "") or "").upper()
        if args.symbol and args.symbol.upper() not in symbol:
            continue
        events.append(event)

    grouped = defaultdict(list)
    for event in events:
        grouped[event.get("correlation_id") or event.get("event_id")].append(event)

    print(f"Eventos lifecycle: {len(events)}")
    print(f"Ciclos: {len(grouped)}")
    for correlation_id, items in list(grouped.items())[-50:]:
        print(f"\n{correlation_id}")
        for event in items:
            data = event.get("data") or {}
            print(
                f"  {event.get('timestamp')} | {event.get('type')} | "
                f"{data.get('symbol', '-')} {data.get('timeframe', '-')} | "
                f"{data.get('direction', '-')} | {data.get('status', '-')} | {data.get('reason', '-')}"
            )


if __name__ == "__main__":
    main()
