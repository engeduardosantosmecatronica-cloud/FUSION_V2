from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fusion.core.enums import FusionEventType
from fusion.core.event_logger import FusionEventLogger
from fusion.core.events import FusionEvent, FusionEventBus


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke test do FusionEventBus em modo assíncrono.")
    parser.add_argument("--events", type=int, default=1000, help="Quantidade de eventos synthetic.")
    parser.add_argument("--output-dir", default="", help="Diretorio opcional para gravar eventos de teste.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_root = Path(args.output_dir) if args.output_dir else Path(tempfile.mkdtemp(prefix="fusion_event_bus_async_"))
    logger = FusionEventLogger(log_dir=output_root, enabled=True)
    bus = FusionEventBus()
    captured = []

    def capture(event: FusionEvent) -> None:
        captured.append(event.event_id)

    bus.subscribe(FusionEventBus.ALL_EVENTS, logger.handle)
    bus.subscribe(FusionEventBus.ALL_EVENTS, capture)
    bus.start_async()

    for index in range(max(1, int(args.events))):
        bus.publish_async(
            FusionEvent(
                type=FusionEventType.DASHBOARD_UPDATE,
                source="check_event_bus_async",
                correlation_id=f"ASYNC_TEST:{index}",
                data={"index": index, "kind": "async_smoke"},
            )
        )
    bus.stop_async(timeout=10.0)

    files = sorted(output_root.glob("events_*.jsonl"))
    logged = 0
    event_ids = set()
    for path in files:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            logged += 1
            event_ids.add(payload.get("event_id", ""))

    expected = max(1, int(args.events))
    captured_count = len(captured)
    missing_capture = expected - captured_count
    missing_log = expected - logged
    ok = captured_count == expected and logged == expected and len(event_ids) == expected and bus.pending_async_events() == 0

    print(f"Output: {output_root}")
    print(f"Expected: {expected}")
    print(f"Captured: {captured_count}")
    print(f"Logged: {logged}")
    print(f"Unique logged ids: {len(event_ids)}")
    print(f"Pending: {bus.pending_async_events()}")
    print(f"Missing capture: {missing_capture}")
    print(f"Missing log: {missing_log}")
    print(f"Status: {'OK' if ok else 'FAIL'}")
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
