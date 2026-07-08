from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from threading import RLock

from fusion.core.events import FusionEvent


class FusionEventLogger:
    """Grava eventos estruturados em JSONL para auditoria e replay."""

    def __init__(self, log_dir: str | Path = "logs/events", enabled: bool = True) -> None:
        self.log_dir = Path(log_dir)
        self.enabled = enabled
        self._lock = RLock()

    def handle(self, event: FusionEvent) -> Path | None:
        return self.write(event)

    def write(self, event: FusionEvent) -> Path | None:
        if not self.enabled:
            return None
        self.log_dir.mkdir(parents=True, exist_ok=True)
        path = self.log_dir / f"events_{datetime.now().strftime('%Y%m%d')}.jsonl"
        payload = event.to_dict()
        with self._lock:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
            self._write_specialized_stream(payload)
        return path

    def _write_specialized_stream(self, payload: dict) -> None:
        event_type = str(payload.get("type", "") or "")
        if event_type not in {"ORDER_REQUEST", "ORDER_RESULT", "POSITION_UPDATE", "ACCOUNT_UPDATE"}:
            return
        folder = self.log_dir.parent / "order_lifecycle"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"order_lifecycle_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
