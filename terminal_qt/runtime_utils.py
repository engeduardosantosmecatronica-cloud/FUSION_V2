from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

from fusion_terminal_qt import ROOT


def load_config() -> dict[str, Any]:
    try:
        import yaml
    except ImportError:
        return {}
    path = ROOT / "config" / "fusion_config.yaml"
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8", errors="replace")) or {}
    except Exception:
        return {}


CONFIG = load_config()
BROKER_SETTINGS = CONFIG.get("broker", {}) if isinstance(CONFIG, dict) else {}
SYMBOL_CONTRACTS = CONFIG.get("contracts", {}).get("symbols", {}) if isinstance(CONFIG, dict) else {}
TRAILING_SYMBOL_MAPPING = CONFIG.get("trailing", {}).get("symbol_mapping", {}) if isinstance(CONFIG, dict) else {}
TARGET_SYMBOLS = CONFIG.get("symbols", []) if isinstance(CONFIG, dict) else []


def latest_file(base: Path, pattern: str) -> Path | None:
    files = sorted(base.glob(pattern), key=lambda item: item.stat().st_mtime, reverse=True)
    return files[0] if files else None


def read_jsonl_tail(path: Path | None, tail_bytes: int = 3_000_000) -> list[dict[str, Any]]:
    if not path or not path.exists():
        return []
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            handle.seek(max(0, size - tail_bytes))
            if size > tail_bytes:
                handle.readline()
            text = handle.read().decode("utf-8", errors="replace")
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def sanitize_candles(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clean: list[dict[str, Any]] = []
    for row in rows:
        try:
            open_price = float(row["open"])
            high_price = float(row["high"])
            low_price = float(row["low"])
            close_price = float(row["close"])
        except (KeyError, TypeError, ValueError):
            continue
        values = [open_price, high_price, low_price, close_price]
        if not all(math.isfinite(value) and value > 0 for value in values):
            continue
        if "tick_volume" in row and safe_float(row.get("tick_volume"), 0.0) <= 0:
            continue
        if is_weekend_candle(row.get("time", "")):
            continue
        high_price = max(high_price, open_price, close_price)
        low_price = min(low_price, open_price, close_price)
        clean.append(
            {
                "time": row.get("time", ""),
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
            }
        )
    return clean


def is_weekend_candle(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[: len(fmt)], fmt).weekday() >= 5
        except ValueError:
            continue
    return False


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def is_color(value: str) -> bool:
    if not value.startswith("#") or len(value) not in {4, 7}:
        return False
    return all(ch in "0123456789abcdefABCDEF" for ch in value[1:])
