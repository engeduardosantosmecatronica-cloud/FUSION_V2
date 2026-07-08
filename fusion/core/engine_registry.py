from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class BaseFusionEngine:
    name = "base"

    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None

    def on_event(self, event: Any) -> None:
        return None


@dataclass
class RegisteredEngine:
    name: str
    engine: Any
    enabled: bool = True


class FusionEngineRegistry:
    """Registro simples para engines internas do FUSION."""

    def __init__(self) -> None:
        self._engines: dict[str, RegisteredEngine] = {}

    def register(self, name: str, engine: Any, enabled: bool = True) -> None:
        self._engines[str(name)] = RegisteredEngine(str(name), engine, bool(enabled))

    def get(self, name: str) -> Any | None:
        item = self._engines.get(str(name))
        return item.engine if item else None

    def enabled(self) -> list[Any]:
        return [item.engine for item in self._engines.values() if item.enabled]

    def items(self) -> list[RegisteredEngine]:
        return list(self._engines.values())

    def snapshot(self) -> list[dict]:
        return [
            {
                "name": item.name,
                "class": item.engine.__name__ if isinstance(item.engine, type) else item.engine.__class__.__name__,
                "enabled": item.enabled,
            }
            for item in self._engines.values()
        ]

    @property
    def engines(self) -> dict[str, RegisteredEngine]:
        return self._engines
