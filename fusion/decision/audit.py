from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from fusion.decision.schema import DecisionEvent


class DecisionAuditLogger:
    def __init__(self, log_dir: str | Path = "logs/decision_audit", enabled: bool = True):
        self.log_dir = Path(log_dir)
        self.enabled = enabled

    def write(self, event: DecisionEvent) -> Path | None:
        if not self.enabled:
            return None
        self.log_dir.mkdir(parents=True, exist_ok=True)
        path = self.log_dir / f"decision_audit_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_dict(), ensure_ascii=False, default=str) + "\n")
        return path
