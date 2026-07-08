from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from queue import Empty, Queue
from threading import RLock
import threading
from typing import Any, Callable
from uuid import uuid4

from fusion.core.enums import FusionEventType
from fusion.core.objects import to_plain_dict


EventHandler = Callable[["FusionEvent"], None]


@dataclass
class FusionEvent:
    type: FusionEventType | str
    source: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    event_id: str = field(default_factory=lambda: uuid4().hex)
    correlation_id: str = ""
    version: str = "fusion_event_v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "event_id": self.event_id,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
            "type": self.type.value if hasattr(self.type, "value") else str(self.type),
            "source": self.source,
            "data": to_plain_dict(self.data),
        }


class FusionEventBus:
    """Barramento síncrono leve para desacoplar módulos do FUSION."""

    ALL_EVENTS = "*"

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._lock = RLock()
        self._queue: Queue[FusionEvent] = Queue()
        self._worker: threading.Thread | None = None
        self._stop_event = threading.Event()

    def subscribe(self, event_type: FusionEventType | str, handler: EventHandler) -> None:
        key = self._normalize_type(event_type)
        with self._lock:
            if handler not in self._handlers[key]:
                self._handlers[key].append(handler)

    def unsubscribe(self, event_type: FusionEventType | str, handler: EventHandler) -> None:
        key = self._normalize_type(event_type)
        with self._lock:
            if handler in self._handlers.get(key, []):
                self._handlers[key].remove(handler)

    def publish(self, event: FusionEvent) -> None:
        key = self._normalize_type(event.type)
        with self._lock:
            handlers = list(self._handlers.get(key, []))
            handlers.extend(self._handlers.get(self.ALL_EVENTS, []))
        for handler in handlers:
            handler(event)

    def publish_async(self, event: FusionEvent) -> None:
        if not self._worker or not self._worker.is_alive():
            self.start_async()
        self._queue.put(event)

    def start_async(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self._stop_event.clear()
        self._worker = threading.Thread(target=self._run_async_loop, name="FusionEventBus", daemon=True)
        self._worker.start()

    def stop_async(self, timeout: float = 3.0) -> None:
        if self._worker and self._worker.is_alive():
            self._queue.join()
        self._stop_event.set()
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=timeout)
        self._worker = None

    def pending_async_events(self) -> int:
        return int(self._queue.qsize())

    def _run_async_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                event = self._queue.get(timeout=0.25)
            except Empty:
                continue
            try:
                self.publish(event)
            finally:
                self._queue.task_done()

    @staticmethod
    def _normalize_type(event_type: FusionEventType | str) -> str:
        return event_type.value if hasattr(event_type, "value") else str(event_type)
