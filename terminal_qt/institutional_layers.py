from __future__ import annotations

import json
from typing import Any

from fusion_terminal_qt import TIMEFRAMES, normalize_symbol

from runtime_utils import safe_float


LAYER_DEFINITIONS: dict[str, dict[str, Any]] = {
    "Market Regime": {"engines": ["market_regime"]},
    "Market Structure": {"engines": ["market_structure"]},
    "Execution": {"engines": ["execution_engine", "entry_timing"]},
    "Context": {"engines": ["context_engine", "macro_flow", "market_briefing"]},
    "Risk": {"engines": ["portfolio_exposure"], "decision": True},
    "Portfolio Exposure": {"engines": ["portfolio_exposure"], "decision": True},
    "Confidence Calibration": {"engines": ["confidence_calibration"]},
    "Consensus": {"engines": ["consensus_engine"]},
    "Volatility": {"engines": ["volatility_engine"]},
    "Session": {"engines": ["session_context"]},
    "Opportunity": {"engines": ["entry_timing", "execution_engine", "context_engine", "consensus_engine"]},
    "Meta-Model Ensemble": {"engines": ["meta_model_ensemble"]},
    "Feature Engineering": {"engines": ["feature_engineering"]},
    "Advisor / Briefing": {"engines": ["market_briefing"]},
    "Audit / Event Bus": {"events": True, "decision": True},
}


def layer_names() -> list[str]:
    return list(LAYER_DEFINITIONS)


def layer_snapshot(
    events: list[dict[str, Any]],
    layer_name: str,
    symbol: str,
    broker_symbol: str,
) -> dict[str, Any]:
    definition = LAYER_DEFINITIONS.get(layer_name, {})
    engines = definition.get("engines", [])
    engine_rows = latest_engine_rows(events, engines, symbol, broker_symbol)
    decisions = latest_decisions(events, symbol, broker_symbol, limit=5) if definition.get("decision") else []
    event_counts = event_type_counts(events) if definition.get("events") else {}
    return {
        "layer": layer_name,
        "engines": engine_rows,
        "decisions": decisions,
        "event_counts": event_counts,
    }


def latest_engine_rows(
    events: list[dict[str, Any]],
    engine_names: list[str],
    symbol: str,
    broker_symbol: str,
) -> list[dict[str, Any]]:
    aliases = _symbol_aliases(symbol, broker_symbol)
    seen: set[tuple[str, str]] = set()
    rows: list[dict[str, Any]] = []
    wanted = set(engine_names)
    for event in reversed(events):
        if event.get("type") != "ENGINE_RESULT":
            continue
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        engine = data.get("engine") if isinstance(data.get("engine"), dict) else {}
        name = str(engine.get("engine") or "")
        if name not in wanted:
            continue
        candidate = data.get("candidate") if isinstance(data.get("candidate"), dict) else {}
        event_symbol = normalize_symbol(candidate.get("symbol") or candidate.get("broker_symbol") or "")
        if event_symbol and event_symbol not in aliases:
            continue
        timeframe = str(candidate.get("timeframe") or engine.get("features", {}).get("signal_timeframe") or "").upper()
        if timeframe and timeframe not in TIMEFRAMES:
            timeframe = ""
        key = (name, timeframe)
        if key in seen:
            continue
        seen.add(key)
        rows.append(_engine_row(event, candidate, engine, timeframe))
        if len(rows) >= max(8, len(wanted) * len(TIMEFRAMES)):
            break
    return rows


def latest_decisions(
    events: list[dict[str, Any]],
    symbol: str,
    broker_symbol: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    aliases = _symbol_aliases(symbol, broker_symbol)
    rows: list[dict[str, Any]] = []
    for event in reversed(events):
        if event.get("type") != "DECISION":
            continue
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        candidate = data.get("candidate") if isinstance(data.get("candidate"), dict) else {}
        event_symbol = normalize_symbol(candidate.get("symbol") or candidate.get("broker_symbol") or "")
        if event_symbol and event_symbol not in aliases:
            continue
        result = data.get("result") if isinstance(data.get("result"), dict) else {}
        rows.append(
            {
                "time": data.get("timestamp") or event.get("timestamp") or "",
                "symbol": event_symbol or "-",
                "timeframe": candidate.get("timeframe") or "-",
                "side": candidate.get("side") or candidate.get("direction") or "-",
                "state": result.get("status") or result.get("state") or result.get("decision") or "-",
                "score": result.get("score"),
                "reason": result.get("reason") or data.get("explanation") or "-",
                "raw": data,
            }
        )
        if len(rows) >= limit:
            break
    return rows


def event_type_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        event_type = str(event.get("type") or "-")
        counts[event_type] = counts.get(event_type, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: item[1], reverse=True))


def compact_json(value: Any, limit: int = 2500) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, indent=2, default=str)
    except TypeError:
        text = str(value)
    if len(text) > limit:
        return text[:limit] + "\n..."
    return text


def _engine_row(
    event: dict[str, Any],
    candidate: dict[str, Any],
    engine: dict[str, Any],
    timeframe: str,
) -> dict[str, Any]:
    positives = engine.get("positive_factors") if isinstance(engine.get("positive_factors"), list) else []
    negatives = engine.get("negative_factors") if isinstance(engine.get("negative_factors"), list) else []
    warnings = engine.get("warnings") if isinstance(engine.get("warnings"), list) else []
    return {
        "time": event.get("timestamp") or "",
        "engine": engine.get("engine") or "-",
        "symbol": normalize_symbol(candidate.get("symbol") or candidate.get("broker_symbol") or "") or "-",
        "timeframe": timeframe or candidate.get("timeframe") or "-",
        "side": candidate.get("side") or candidate.get("direction") or engine.get("direction") or "-",
        "direction": engine.get("direction") or "-",
        "state": engine.get("state") or "-",
        "score": safe_float(engine.get("score"), 0.0),
        "confidence": safe_float(engine.get("confidence"), 0.0),
        "positive_count": len(positives),
        "negative_count": len(negatives),
        "warning_count": len(warnings),
        "positive_factors": positives,
        "negative_factors": negatives,
        "warnings": warnings,
        "features": engine.get("features") if isinstance(engine.get("features"), dict) else {},
        "raw": engine,
    }


def _symbol_aliases(symbol: str, broker_symbol: str) -> set[str]:
    aliases = {normalize_symbol(symbol), normalize_symbol(broker_symbol)}
    if "GOLD" in aliases or "XAUUSD" in aliases:
        aliases.update({"GOLD", "XAUUSD"})
    aliases.discard("")
    aliases.discard("-")
    return aliases
