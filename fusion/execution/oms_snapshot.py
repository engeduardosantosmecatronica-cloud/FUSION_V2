from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from threading import RLock

from fusion.execution.oms import FusionOMS


class OMSSnapshotWriter:
    def __init__(self, output_dir: str | Path = "logs/oms", enabled: bool = True) -> None:
        self.output_dir = Path(output_dir)
        self.enabled = enabled
        self._lock = RLock()

    def write(self, oms: FusionOMS) -> Path | None:
        if not self.enabled:
            return None
        self.output_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "timestamp": datetime.now().isoformat(),
            "version": "oms_snapshot_v1",
            "oms": oms.snapshot(),
        }
        path = self.output_dir / f"oms_snapshot_{datetime.now().strftime('%Y%m%d')}.json"
        tmp_path = path.with_suffix(".tmp")
        with self._lock:
            tmp_path.write_text(json.dumps(payload, ensure_ascii=False, default=str, indent=2), encoding="utf-8")
            tmp_path.replace(path)
        return path
