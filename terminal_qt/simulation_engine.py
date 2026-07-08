from __future__ import annotations

from typing import Any

from fusion_terminal_qt import normalize_symbol

from runtime_utils import CONFIG, safe_float


def pip_value(symbol: str) -> float:
    normalized = normalize_symbol(symbol)
    if normalized in {"GOLD", "XAUUSD"}:
        return 0.1
    if "JPY" in normalized:
        return 0.01
    return 0.0001


def signal_key(symbol: str, timeframe: str, signal: dict[str, Any]) -> str:
    return f"{symbol}:{timeframe}:{int(signal['index'])}:{str(signal['side'])}"


def simulated_order(
    symbol: str,
    timeframe: str,
    signal: dict[str, Any],
    overrides: dict[str, dict[str, Any]],
    stop_loss_pips: float,
    take_profit_pips: float,
    trailing_activation_pips: float,
    trailing_distance_pips: float,
) -> dict[str, Any]:
    side = str(signal["side"])
    entry = float(signal["price"])
    key = signal_key(symbol, timeframe, signal)
    override = overrides.get(key, {})
    point_value = pip_value(symbol)
    sl_pips = override.get("stop_loss", stop_loss_pips)
    tp_pips = override.get("take_profit", take_profit_pips)
    trailing_activation = override.get("trailing_activation", trailing_activation_pips)
    trailing_distance = override.get("trailing_distance", trailing_distance_pips)
    sl_points = sl_pips * point_value
    tp_points = tp_pips * point_value
    if side == "BUY":
        stop_loss = entry - sl_points if sl_points else None
        take_profit = entry + tp_points if tp_points else None
    else:
        stop_loss = entry + sl_points if sl_points else None
        take_profit = entry - tp_points if tp_points else None
    return {
        "key": key,
        "index": signal["index"],
        "side": side,
        "entry": entry,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "stop_loss_pips": sl_pips,
        "take_profit_pips": tp_pips,
        "trailing_activation": trailing_activation,
        "trailing_distance": trailing_distance,
    }


def simulate_trade_results(
    symbol: str,
    timeframe: str,
    signals: list[dict[str, Any]],
    highs: list[float],
    lows: list[float],
    closes: list[float],
    candles: list[dict[str, Any]],
    stop_loss_pips: float,
    take_profit_pips: float,
) -> list[dict[str, Any]]:
    if not signals:
        return []

    point_value = pip_value(symbol)
    sl_distance = stop_loss_pips * point_value
    tp_distance = take_profit_pips * point_value
    trades: list[dict[str, Any]] = []

    for pos, signal in enumerate(signals[:-1]):
        entry_index = int(signal["index"])
        side = str(signal["side"])
        entry = float(signal["price"])
        next_signal_index = int(signals[pos + 1]["index"])
        exit_index = next_signal_index
        exit_price = closes[next_signal_index]
        exit_reason = "sinal_oposto"

        stop_loss = entry - sl_distance if side == "BUY" and sl_distance else entry + sl_distance if sl_distance else None
        take_profit = entry + tp_distance if side == "BUY" and tp_distance else entry - tp_distance if tp_distance else None

        for idx in range(entry_index + 1, min(next_signal_index + 1, len(closes))):
            if side == "BUY":
                if stop_loss is not None and lows[idx] <= stop_loss:
                    exit_index, exit_price, exit_reason = idx, stop_loss, "stop_loss"
                    break
                if take_profit is not None and highs[idx] >= take_profit:
                    exit_index, exit_price, exit_reason = idx, take_profit, "take_profit"
                    break
            else:
                if stop_loss is not None and highs[idx] >= stop_loss:
                    exit_index, exit_price, exit_reason = idx, stop_loss, "stop_loss"
                    break
                if take_profit is not None and lows[idx] <= take_profit:
                    exit_index, exit_price, exit_reason = idx, take_profit, "take_profit"
                    break

        pnl = (exit_price - entry) if side == "BUY" else (entry - exit_price)
        trades.append(
            {
                "key": signal_key(symbol, timeframe, signal),
                "entry_index": entry_index,
                "exit_index": exit_index,
                "side": side,
                "entry": entry,
                "exit": exit_price,
                "pnl": pnl,
                "pnl_pips": pnl / point_value if point_value else 0.0,
                "reason": exit_reason,
                "entry_time": candles[entry_index].get("time", "") if entry_index < len(candles) else "",
                "exit_time": candles[exit_index].get("time", "") if exit_index < len(candles) else "",
            }
        )
    return trades


def max_drawdown_pips(trades: list[dict[str, Any]]) -> float:
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for trade in trades:
        equity += safe_float(trade.get("pnl_pips"))
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    return max_dd


def strategy_names() -> list[str]:
    names: list[str] = []
    strategies = CONFIG.get("strategies", {}) if isinstance(CONFIG, dict) else {}
    if isinstance(strategies, dict):
        names.extend(str(key) for key in strategies)
    for key in CONFIG if isinstance(CONFIG, dict) else []:
        if str(key).lower().startswith("strategy"):
            names.append(str(key))
    names.insert(0, "Cruzamento EMA 9/21")
    if not names:
        names = ["Strategy1", "Strategy2", "Strategy3", "Strategy4", "Manual"]
    return sorted(dict.fromkeys(names))
