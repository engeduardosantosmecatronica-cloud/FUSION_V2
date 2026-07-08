from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Checa saude recente do Event Bus em runtime.")
    parser.add_argument("--date", required=True, help="Data YYYYMMDD.")
    parser.add_argument("--minutes", type=int, default=30, help="Janela recente em minutos.")
    parser.add_argument("--max-stale-minutes", type=int, default=15, help="Idade maxima aceitavel do ultimo evento.")
    parser.add_argument("--events-dir", default="logs/events")
    return parser.parse_args()


def load_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def parse_ts(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def main() -> None:
    args = parse_args()
    path = ROOT / args.events_dir / f"events_{args.date}.jsonl"
    events = load_events(path)
    if not events:
        raise SystemExit(f"Nenhum evento encontrado em {path}")

    timestamps = [ts for ts in (parse_ts(event.get("timestamp", "")) for event in events) if ts]
    if not timestamps:
        raise SystemExit("Eventos sem timestamps validos.")
    latest_ts = max(timestamps)
    now = datetime.now()
    stale_minutes = max(0.0, (now - latest_ts).total_seconds() / 60.0)
    stale_status = "OK" if stale_minutes <= max(1, int(args.max_stale_minutes)) else "STALE"
    cutoff = latest_ts - timedelta(minutes=max(1, int(args.minutes)))
    recent = [event for event in events if (parse_ts(event.get("timestamp", "")) or datetime.min) >= cutoff]

    by_type = Counter(str(event.get("type", "") or "") for event in recent)
    by_corr: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in recent:
        by_corr[str(event.get("correlation_id") or event.get("event_id"))].append(event)

    order_request_without_result = 0
    order_result_without_request = 0
    decision_without_engine = 0
    decision_without_signal = 0
    for group in by_corr.values():
        types = Counter(str(event.get("type", "") or "") for event in group)
        if types["ORDER_REQUEST"] and not types["ORDER_RESULT"]:
            order_request_without_result += 1
        if types["ORDER_RESULT"] and not types["ORDER_REQUEST"]:
            order_result_without_request += 1
        if types["DECISION"] and not types["ENGINE_RESULT"]:
            decision_without_engine += 1
        if types["DECISION"] and not types["SIGNAL"]:
            decision_without_signal += 1

    print(f"Arquivo: {path}")
    print(f"Eventos totais: {len(events)}")
    print(f"Agora local: {now.isoformat(timespec='seconds')}")
    print(f"Ultimo evento: {latest_ts.isoformat()} | idade_min={stale_minutes:.1f} | status={stale_status}")
    print(f"Janela: ultimos {args.minutes} min ate {latest_ts.isoformat()}")
    print(f"Eventos recentes: {len(recent)}")
    print("Tipos:")
    for event_type, count in by_type.most_common():
        print(f"  {event_type}: {count}")
    print("Alertas recentes:")
    print(f"  order_request_sem_order_result: {order_request_without_result}")
    print(f"  order_result_sem_order_request: {order_result_without_request}")
    print(f"  decision_sem_engine_result: {decision_without_engine}")
    print(f"  decision_sem_signal: {decision_without_signal}")


if __name__ == "__main__":
    main()
