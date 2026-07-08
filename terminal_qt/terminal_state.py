from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fusion_terminal_qt import normalize_symbol

from runtime_utils import latest_file, safe_float


def latest_oms_snapshot(root: Path) -> dict[str, Any]:
    path = latest_file(root / "logs" / "oms", "oms_snapshot_*.json")
    if not path:
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return {}
    return normalize_oms(payload)


def normalize_oms(snapshot: dict[str, Any]) -> dict[str, Any]:
    if "oms" in snapshot and isinstance(snapshot["oms"], dict):
        return snapshot["oms"]
    return snapshot if isinstance(snapshot, dict) else {}


def positions(oms: dict[str, Any]) -> list[dict[str, Any]]:
    items = oms.get("positions") or oms.get("open_positions") or []
    return items if isinstance(items, list) else []


def trades(oms: dict[str, Any]) -> list[dict[str, Any]]:
    items = oms.get("trades") or []
    return items if isinstance(items, list) else []


def account(oms: dict[str, Any]) -> dict[str, Any]:
    item = oms.get("account") or {}
    return item if isinstance(item, dict) else {}


def symbol_watchlist(events: list[dict[str, Any]], oms: dict[str, Any], limit: int = 80) -> list[dict[str, Any]]:
    model: dict[str, dict[str, Any]] = {}
    for event in reversed(events):
        event_type = str(event.get("type") or "")
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        candidate = data.get("candidate") if isinstance(data.get("candidate"), dict) else {}
        symbol = normalize_symbol(data.get("symbol") or candidate.get("symbol") or data.get("broker_symbol") or candidate.get("broker_symbol"))
        if not symbol:
            continue
        row = model.setdefault(
            symbol,
            {
                "symbol": symbol,
                "signals": 0,
                "alerts": 0,
                "last_side": "-",
                "last_tf": "-",
                "p_buy": None,
                "p_sell": None,
                "pnl": 0.0,
                "positions": 0,
            },
        )
        if event_type == "SIGNAL":
            row["signals"] += 1
            row["last_side"] = data.get("direction") or data.get("side") or candidate.get("side") or row["last_side"]
            row["last_tf"] = data.get("timeframe") or candidate.get("timeframe") or row["last_tf"]
            row["p_buy"] = data.get("p_buy", candidate.get("p_buy", row["p_buy"]))
            row["p_sell"] = data.get("p_sell", candidate.get("p_sell", row["p_sell"]))
        elif event_type in {"RISK_ALERT", "TRAILING_UPDATE", "ORDER_RESULT", "DECISION"}:
            row["alerts"] += 1
    for position in positions(oms):
        symbol = normalize_symbol(position.get("symbol") or position.get("broker_symbol"))
        if not symbol:
            continue
        row = model.setdefault(
            symbol,
            {"symbol": symbol, "signals": 0, "alerts": 0, "last_side": "-", "last_tf": "-", "p_buy": None, "p_sell": None, "pnl": 0.0, "positions": 0},
        )
        row["positions"] += 1
        row["pnl"] += safe_float(position.get("profit"))
    return sorted(model.values(), key=lambda item: (safe_float(item.get("pnl")), item.get("signals", 0)), reverse=True)[:limit]


def recent_alerts(events: list[dict[str, Any]], limit: int = 60) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    alert_types = {"SIGNAL", "RISK_ALERT", "TRAILING_UPDATE", "ORDER_REQUEST", "ORDER_RESULT", "DECISION"}
    for event in reversed(events):
        event_type = str(event.get("type") or "")
        if event_type not in alert_types:
            continue
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        candidate = data.get("candidate") if isinstance(data.get("candidate"), dict) else {}
        result = data.get("result") if isinstance(data.get("result"), dict) else {}
        rows.append(
            {
                "time": data.get("timestamp") or event.get("timestamp") or "",
                "type": event_type,
                "symbol": normalize_symbol(data.get("symbol") or candidate.get("symbol") or data.get("broker_symbol") or candidate.get("broker_symbol")) or "-",
                "tf": data.get("timeframe") or candidate.get("timeframe") or "-",
                "side": data.get("direction") or data.get("side") or candidate.get("side") or "-",
                "status": result.get("status") or result.get("state") or data.get("status") or "-",
                "reason": result.get("reason") or data.get("reason") or data.get("explanation") or "-",
            }
        )
        if len(rows) >= limit:
            break
    return rows


def account_metrics(oms: dict[str, Any]) -> dict[str, Any]:
    acc = account(oms)
    pos = positions(oms)
    return {
        "balance": safe_float(acc.get("balance")),
        "equity": safe_float(acc.get("equity")),
        "margin": safe_float(acc.get("margin")),
        "free_margin": safe_float(acc.get("free_margin")),
        "currency": acc.get("currency") or "-",
        "positions": len(pos),
        "pnl": sum(safe_float(item.get("profit")) for item in pos),
        "trades": len(trades(oms)),
    }
