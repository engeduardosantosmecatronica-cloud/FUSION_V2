from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from runtime_utils import safe_float


STRATEGY_LABELS = [
    ("strategy1", "S1 - sinal base / EMA cross"),
    ("strategy2", "S2 - feature filter / candle confirmado"),
    ("strategy3", "S3 - feature + exposicao / tendencia forte"),
    ("strategy4", "S4 - GOLD inside bar breakout"),
    ("strategy5", "S5 - approved ensemble / continuacao"),
    ("strategy6", "S6 - experts/features / RSI + tendencia"),
]


@dataclass
class BacktestOrder:
    order_id: int
    symbol: str
    timeframe: str
    side: str
    entry_index: int
    entry: float
    stop_loss: float | None
    take_profit: float | None
    trailing_activation_pips: float
    trailing_distance_pips: float
    pip_value: float
    lot: float
    best_price: float
    trailing_active: bool = False
    trailing_stop: float | None = None


@dataclass
class BacktestTrade:
    order_id: int
    side: str
    entry_index: int
    exit_index: int
    entry: float
    exit: float
    reason: str
    pnl_pips: float
    lot: float


@dataclass
class PeriodBacktestState:
    index: int = 0
    phase: int = 0
    price: float = 0.0
    next_order_id: int = 1
    open_orders: list[BacktestOrder] = field(default_factory=list)
    closed_trades: list[BacktestTrade] = field(default_factory=list)
    signals: list[dict[str, Any]] = field(default_factory=list)
    finished: bool = False


def candle_sequence(candle: dict[str, Any]) -> list[float]:
    open_price = safe_float(candle.get("open"))
    high_price = safe_float(candle.get("high"))
    low_price = safe_float(candle.get("low"))
    close_price = safe_float(candle.get("close"))
    if close_price >= open_price:
        return [open_price, low_price, high_price, close_price]
    return [open_price, high_price, low_price, close_price]


def ema_cross_signal(index: int, closes: list[float], fast: list[float | None], slow: list[float | None]) -> str | None:
    if index <= 0 or index >= len(closes):
        return None
    prev_fast = fast[index - 1]
    prev_slow = slow[index - 1]
    curr_fast = fast[index]
    curr_slow = slow[index]
    if prev_fast is None or prev_slow is None or curr_fast is None or curr_slow is None:
        return None
    if prev_fast <= prev_slow and curr_fast > curr_slow:
        return "BUY"
    if prev_fast >= prev_slow and curr_fast < curr_slow:
        return "SELL"
    return None


def strategy_options() -> list[str]:
    return [f"{key} | {label}" for key, label in STRATEGY_LABELS]


def strategy_key(option: str) -> str:
    key = str(option).split("|", 1)[0].strip().lower()
    if key in {item[0] for item in STRATEGY_LABELS}:
        return key
    return "strategy1"


def signal_for_strategy(
    strategy: str,
    index: int,
    candles: list[dict[str, Any]],
    fast: list[float | None],
    slow: list[float | None],
    trend: list[float | None],
) -> str | None:
    key = strategy_key(strategy)
    closes = [safe_float(row.get("close")) for row in candles]
    if key == "strategy1":
        return ema_cross_signal(index, closes, fast, slow)
    if key == "strategy2":
        return _strategy2_signal(index, candles, fast, slow)
    if key == "strategy3":
        return _strategy3_signal(index, candles, fast, slow, trend)
    if key == "strategy4":
        return _strategy4_signal(index, candles)
    if key == "strategy5":
        return _strategy5_signal(index, candles, fast, slow)
    if key == "strategy6":
        return _strategy6_signal(index, candles, fast, slow)
    return ema_cross_signal(index, closes, fast, slow)


def _strategy2_signal(index: int, candles: list[dict[str, Any]], fast: list[float | None], slow: list[float | None]) -> str | None:
    closes = [safe_float(row.get("close")) for row in candles]
    side = ema_cross_signal(index, closes, fast, slow)
    if not side:
        return None
    candle = candles[index]
    is_bull = safe_float(candle.get("close")) > safe_float(candle.get("open"))
    is_bear = safe_float(candle.get("close")) < safe_float(candle.get("open"))
    if side == "BUY" and is_bull:
        return "BUY"
    if side == "SELL" and is_bear:
        return "SELL"
    return None


def _strategy3_signal(
    index: int,
    candles: list[dict[str, Any]],
    fast: list[float | None],
    slow: list[float | None],
    trend: list[float | None],
) -> str | None:
    closes = [safe_float(row.get("close")) for row in candles]
    side = ema_cross_signal(index, closes, fast, slow)
    if not side or index >= len(trend) or trend[index] is None:
        return None
    close = closes[index]
    if side == "BUY" and close > safe_float(trend[index]):
        return "BUY"
    if side == "SELL" and close < safe_float(trend[index]):
        return "SELL"
    return None


def _strategy4_signal(index: int, candles: list[dict[str, Any]]) -> str | None:
    if index < 2:
        return None
    mother = candles[index - 2]
    inside = candles[index - 1]
    current = candles[index]
    inside_ok = safe_float(inside.get("high")) < safe_float(mother.get("high")) and safe_float(inside.get("low")) > safe_float(mother.get("low"))
    if inside_ok and safe_float(current.get("close")) > safe_float(mother.get("high")):
        return "BUY"
    return None


def _strategy5_signal(index: int, candles: list[dict[str, Any]], fast: list[float | None], slow: list[float | None]) -> str | None:
    if index <= 1 or fast[index] is None or slow[index] is None:
        return None
    close = safe_float(candles[index].get("close"))
    previous_high = safe_float(candles[index - 1].get("high"))
    previous_low = safe_float(candles[index - 1].get("low"))
    if safe_float(fast[index]) > safe_float(slow[index]) and close > previous_high:
        return "BUY"
    if safe_float(fast[index]) < safe_float(slow[index]) and close < previous_low:
        return "SELL"
    return None


def _strategy6_signal(index: int, candles: list[dict[str, Any]], fast: list[float | None], slow: list[float | None]) -> str | None:
    if index < 15 or fast[index] is None or slow[index] is None:
        return None
    rsi_values = _rsi([safe_float(row.get("close")) for row in candles], 14)
    prev_rsi = rsi_values[index - 1]
    curr_rsi = rsi_values[index]
    if prev_rsi is None or curr_rsi is None:
        return None
    if safe_float(fast[index]) > safe_float(slow[index]) and prev_rsi <= 50.0 < curr_rsi:
        return "BUY"
    if safe_float(fast[index]) < safe_float(slow[index]) and prev_rsi >= 50.0 > curr_rsi:
        return "SELL"
    return None


def _rsi(values: list[float], period: int) -> list[float | None]:
    result: list[float | None] = [None] * len(values)
    if len(values) <= period:
        return result
    gains: list[float] = []
    losses: list[float] = []
    for idx in range(1, len(values)):
        change = values[idx] - values[idx - 1]
        gains.append(max(change, 0.0))
        losses.append(abs(min(change, 0.0)))
        if idx < period:
            continue
        window_gains = gains[idx - period : idx]
        window_losses = losses[idx - period : idx]
        avg_gain = sum(window_gains) / period
        avg_loss = sum(window_losses) / period
        if avg_loss == 0:
            result[idx] = 100.0
        else:
            rs = avg_gain / avg_loss
            result[idx] = 100.0 - (100.0 / (1.0 + rs))
    return result


def create_order(
    state: PeriodBacktestState,
    symbol: str,
    timeframe: str,
    side: str,
    index: int,
    price: float,
    pip_value: float,
    lot: float,
    stop_loss_pips: float,
    take_profit_pips: float,
    trailing_activation_pips: float,
    trailing_distance_pips: float,
) -> BacktestOrder:
    sl_points = stop_loss_pips * pip_value
    tp_points = take_profit_pips * pip_value
    if side == "BUY":
        stop_loss = price - sl_points if sl_points > 0 else None
        take_profit = price + tp_points if tp_points > 0 else None
    else:
        stop_loss = price + sl_points if sl_points > 0 else None
        take_profit = price - tp_points if tp_points > 0 else None
    order = BacktestOrder(
        order_id=state.next_order_id,
        symbol=symbol,
        timeframe=timeframe,
        side=side,
        entry_index=index,
        entry=price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        trailing_activation_pips=trailing_activation_pips,
        trailing_distance_pips=trailing_distance_pips,
        pip_value=pip_value,
        lot=lot,
        best_price=price,
    )
    state.next_order_id += 1
    state.open_orders.append(order)
    state.signals.append({"index": index, "side": side, "price": price, "order_id": order.order_id})
    return order


def update_orders(state: PeriodBacktestState, price: float, index: int) -> list[BacktestTrade]:
    closed: list[BacktestTrade] = []
    remaining: list[BacktestOrder] = []
    for order in state.open_orders:
        exit_reason, exit_price = _exit_hit(order, price)
        if exit_reason:
            trade = _close_order(order, index, exit_price, exit_reason)
            state.closed_trades.append(trade)
            closed.append(trade)
        else:
            remaining.append(order)
    state.open_orders = remaining
    return closed


def _exit_hit(order: BacktestOrder, price: float) -> tuple[str | None, float]:
    if order.side == "BUY":
        _update_trailing(order, price)
        if order.stop_loss is not None and price <= order.stop_loss:
            return "stop_loss", order.stop_loss
        if order.take_profit is not None and price >= order.take_profit:
            return "take_profit", order.take_profit
        if order.trailing_active and order.trailing_stop is not None and price <= order.trailing_stop:
            return "trailing_stop", order.trailing_stop
    else:
        _update_trailing(order, price)
        if order.stop_loss is not None and price >= order.stop_loss:
            return "stop_loss", order.stop_loss
        if order.take_profit is not None and price <= order.take_profit:
            return "take_profit", order.take_profit
        if order.trailing_active and order.trailing_stop is not None and price >= order.trailing_stop:
            return "trailing_stop", order.trailing_stop
    return None, price


def _update_trailing(order: BacktestOrder, price: float) -> None:
    activation = order.trailing_activation_pips * order.pip_value
    distance = order.trailing_distance_pips * order.pip_value
    if activation <= 0 or distance <= 0:
        return
    if order.side == "BUY":
        if price >= order.entry + activation:
            order.trailing_active = True
        if order.trailing_active:
            order.best_price = max(order.best_price, price)
            order.trailing_stop = order.best_price - distance
    else:
        if price <= order.entry - activation:
            order.trailing_active = True
        if order.trailing_active:
            order.best_price = min(order.best_price, price)
            order.trailing_stop = order.best_price + distance


def _close_order(order: BacktestOrder, index: int, exit_price: float, reason: str) -> BacktestTrade:
    pnl = (exit_price - order.entry) if order.side == "BUY" else (order.entry - exit_price)
    pnl_pips = pnl / order.pip_value if order.pip_value else 0.0
    return BacktestTrade(
        order_id=order.order_id,
        side=order.side,
        entry_index=order.entry_index,
        exit_index=index,
        entry=order.entry,
        exit=exit_price,
        reason=reason,
        pnl_pips=pnl_pips,
        lot=order.lot,
    )


def metrics(state: PeriodBacktestState) -> dict[str, float]:
    total = len(state.closed_trades)
    wins = [trade for trade in state.closed_trades if trade.pnl_pips > 0]
    losses = [trade for trade in state.closed_trades if trade.pnl_pips < 0]
    net = sum(trade.pnl_pips for trade in state.closed_trades)
    gross_profit = sum(trade.pnl_pips for trade in wins)
    gross_loss = sum(trade.pnl_pips for trade in losses)
    return {
        "open": float(len(state.open_orders)),
        "closed": float(total),
        "wins": float(len(wins)),
        "losses": float(len(losses)),
        "win_rate": (len(wins) / total * 100.0) if total else 0.0,
        "net_pips": net,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
    }
