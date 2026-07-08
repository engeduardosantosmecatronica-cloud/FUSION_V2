from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any


class RuntimeControl:
    """Leitura leve de controles operacionais que podem mudar sem reiniciar o Fusion."""

    def __init__(self, path: str | Path = "config/fusion_runtime_control.json", ttl_seconds: float = 1.0):
        self.path = Path(path)
        if not self.path.is_absolute():
            project_root = Path(__file__).resolve().parents[1]
            cwd_path = Path.cwd() / self.path
            root_path = project_root / self.path
            self.path = cwd_path if cwd_path.exists() else root_path
        self.ttl_seconds = max(float(ttl_seconds or 1.0), 0.1)
        self._last_check = 0.0
        self._last_mtime = 0.0
        self._payload: dict[str, Any] = {}

    def payload(self) -> dict[str, Any]:
        now = time.time()
        if now - self._last_check < self.ttl_seconds:
            return self._payload
        self._last_check = now

        if not self.path.exists():
            self._payload = {}
            self._last_mtime = 0.0
            return self._payload

        mtime = self.path.stat().st_mtime
        if mtime == self._last_mtime:
            return self._payload

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8-sig"))
        except Exception:
            return self._payload

        self._last_mtime = mtime
        self._payload = payload if isinstance(payload, dict) else {}
        return self._payload

    def enabled(self) -> bool:
        payload = self.payload()
        if not bool(payload.get("enabled", False)):
            return False
        valid_until = str(payload.get("valid_until", "") or "").strip()
        if valid_until:
            try:
                if datetime.now() > datetime.fromisoformat(valid_until[:19]):
                    return False
            except ValueError:
                pass
        return True

    def section(self, name: str) -> dict[str, Any]:
        if not self.enabled():
            return {}
        value = self.payload().get(name, {}) or {}
        return value if isinstance(value, dict) else {}

    def get(self, dotted_key: str, default: Any = None) -> Any:
        if not self.enabled():
            return default
        value: Any = self.payload()
        for key in dotted_key.split("."):
            if not isinstance(value, dict):
                return default
            value = value.get(key)
        return default if value is None else value

