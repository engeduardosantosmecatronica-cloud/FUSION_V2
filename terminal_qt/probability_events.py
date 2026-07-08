from __future__ import annotations

import math
from typing import Any

from fusion_terminal_qt import TIMEFRAMES, normalize_symbol

from runtime_utils import safe_float


def probability_model(
    events: list[dict[str, Any]],
    symbol: str,
    broker_symbol: str,
) -> dict[str, dict[str, Any]]:
    symbol_aliases = {normalize_symbol(symbol), normalize_symbol(broker_symbol)}
    if normalize_symbol(symbol) in {"GOLD", "XAUUSD"} or normalize_symbol(broker_symbol) == "GOLD":
        symbol_aliases.update({"GOLD", "XAUUSD"})
    model: dict[str, dict[str, Any]] = {}
    for event in reversed(events):
        event_type = str(event.get("type", ""))
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        candidate = data.get("candidate") if isinstance(data.get("candidate"), dict) else {}
        event_symbol = normalize_symbol(
            data.get("symbol")
            or candidate.get("symbol")
            or data.get("broker_symbol")
            or candidate.get("broker_symbol")
        )
        if event_symbol not in symbol_aliases:
            continue
        timeframe = str(data.get("timeframe") or candidate.get("timeframe") or "").upper()
        if timeframe not in TIMEFRAMES or timeframe in model:
            continue
        p_buy = safe_float(data.get("p_buy", candidate.get("p_buy")), math.nan)
        p_sell = safe_float(data.get("p_sell", candidate.get("p_sell")), math.nan)
        if not math.isfinite(p_buy) and not math.isfinite(p_sell):
            continue
        model[timeframe] = {
            "p_buy": p_buy if math.isfinite(p_buy) else None,
            "p_sell": p_sell if math.isfinite(p_sell) else None,
            "side": str(data.get("direction") or data.get("side") or candidate.get("side") or "").upper(),
            "source": event_type,
        }
        if len(model) == len(TIMEFRAMES):
            break
    return model


def side_from_probs(p_buy: Any, p_sell: Any) -> str:
    if not isinstance(p_buy, float) or not isinstance(p_sell, float):
        return ""
    if p_buy > p_sell:
        return "BUY"
    if p_sell > p_buy:
        return "SELL"
    return "NEUTRAL"
