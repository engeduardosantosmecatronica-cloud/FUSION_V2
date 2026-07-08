from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from urllib import request as urlrequest
import json


logger = logging.getLogger("fusion_best.trading")


@dataclass(frozen=True)
class SymbolSpec:
    point: float = 0.0001
    digits: int = 5
    stop_level_points: int = 0
    spread: float = 0.0
    trade_mode: str = "FULL"


@dataclass(frozen=True)
class Tick:
    bid: float
    ask: float


@dataclass(frozen=True)
class OrderPayload:
    symbol: str
    action: str
    lot: float
    sl: float = 0.0
    tp: float = 0.0
    comment: str = "Fusion_AI"
    magic: int = 777777
    deviation: int = 30


@dataclass(frozen=True)
class TradeFilterConfig:
    single_position: bool = True
    min_confidence: float = 0.15
    max_spread_pips: float = 3.6
    max_price_extension_atr: float = 2.5
    cooldown_seconds: int = 60


def pip_value_from_spec(spec: SymbolSpec) -> float:
    return spec.point * 10 if spec.digits >= 2 else spec.point


def trailing_params_for_symbol(symbol: str, spec: SymbolSpec, config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = config or {}
    upper = symbol.upper()
    is_crypto = any(token in upper for token in ("BTC", "ETH", "BCH"))
    is_gold = upper in {"GOLD", "XAUUSD"}
    pip_value = pip_value_from_spec(spec)
    if is_crypto:
        activation_pips = float(cfg.get("trailing_crypto_activation", 1000))
        distance_pips = float(cfg.get("trailing_crypto_distance", 500))
    elif is_gold:
        activation_pips = float(cfg.get("trailing_gold_activation", 40))
        distance_pips = float(cfg.get("trailing_gold_distance", 20))
    else:
        activation_pips = float(cfg.get("trailing_activation", 10))
        distance_pips = float(cfg.get("trailing_distance", 5))
    return {
        "activation": activation_pips * pip_value,
        "distance": distance_pips * pip_value,
        "activation_pips": activation_pips,
        "distance_pips": distance_pips,
        "pip_value": pip_value,
        "is_crypto": is_crypto,
        "is_gold": is_gold,
    }


def calculate_spread_aware_sl_tp(symbol: str, action: str, spec: SymbolSpec, tick: Tick) -> tuple[float, float]:
    spread_pips = abs(tick.ask - tick.bid) / max(spec.point, 1e-12)
    upper = symbol.upper()
    if "BTC" in upper or "ETH" in upper:
        sl_points = max(300, int(spread_pips * 2.5))
        tp_points = max(600, int(spread_pips * 5))
    elif "XAU" in upper or "GOLD" in upper:
        sl_points = max(1500, int(spread_pips * 5))
        tp_points = max(3000, int(spread_pips * 10))
    else:
        sl_points = max(500, int(spread_pips * 3))
        tp_points = max(1000, int(spread_pips * 6))
    price = tick.ask if action.upper() == "BUY" else tick.bid
    return calculate_points_sl_tp(action, price, spec, sl_points=sl_points, tp_points=tp_points)


def evaluate_trade_filter_funnel(
    symbol: str,
    decision_packet: dict[str, Any],
    market_row: dict[str, Any],
    open_positions: list[dict[str, Any]] | None = None,
    last_trade_age_seconds: float | None = None,
    config: TradeFilterConfig | None = None,
) -> dict[str, Any]:
    cfg = config or TradeFilterConfig()
    positions = open_positions or []
    action = str(decision_packet.get("decision", "NEUTRAL")).upper()
    score = float(decision_packet.get("score", 0.0))
    alignment = float(decision_packet.get("alignment", 0.0))
    blocks: list[str] = []
    if action == "NEUTRAL":
        blocks.append("decision_neutral")
    if cfg.single_position and positions:
        blocks.append("single_position")
    if last_trade_age_seconds is not None and last_trade_age_seconds < cfg.cooldown_seconds:
        blocks.append("cooldown")
    if abs(score) < cfg.min_confidence:
        blocks.append("min_confidence")
    ema = market_row.get("ema_9", market_row.get("omnis_ema_9"))
    atr = market_row.get("atr", market_row.get("omnis_atr"))
    close = market_row.get("close")
    if close is not None and ema is not None and atr not in (None, 0) and abs(float(close) - float(ema)) > float(atr) * cfg.max_price_extension_atr:
        blocks.append("price_extension_atr")
    if (action == "BUY" and alignment < 0) or (action == "SELL" and alignment > 0):
        blocks.append("trend_alignment")
    spread_pips = float(market_row.get("spread_pips", 0.0) or 0.0)
    if spread_pips > cfg.max_spread_pips:
        blocks.append("spread_limit")
    return {"passed": not blocks, "blocks": blocks, "symbol": symbol.upper(), "decision": action, "score": score}


def validate_symbol_for_order(symbol: str, order_type: str, spec: SymbolSpec | None, tick: Tick | None) -> dict[str, Any]:
    if spec is None:
        return {"ok": False, "message": f"Sem informacoes para {symbol}"}
    if spec.trade_mode == "DISABLED":
        return {"ok": False, "message": f"{symbol} com trading desabilitado"}
    if spec.trade_mode == "LONGONLY" and order_type == "SELL":
        return {"ok": False, "message": f"{symbol} so permite compras"}
    if spec.trade_mode == "SHORTONLY" and order_type == "BUY":
        return {"ok": False, "message": f"{symbol} so permite vendas"}
    if tick is None or tick.ask <= 0 or tick.bid <= 0:
        return {"ok": False, "message": f"Tick invalido para {symbol}"}
    return {"ok": True, "message": f"{symbol} OK"}


def build_order_request(payload: OrderPayload, spec: SymbolSpec, tick: Tick) -> dict[str, Any]:
    action = payload.action.upper()
    if action not in {"BUY", "SELL"}:
        raise ValueError(f"Tipo de ordem invalido: {payload.action}")
    price = tick.ask if action == "BUY" else tick.bid
    request = {
        "symbol": payload.symbol,
        "action": action,
        "volume": float(payload.lot),
        "price": round(price, spec.digits),
        "deviation": payload.deviation,
        "magic": payload.magic,
        "comment": payload.comment,
    }
    if payload.sl > 0:
        request["sl"] = round(payload.sl, spec.digits)
    if payload.tp > 0:
        request["tp"] = round(payload.tp, spec.digits)
    return request


def calculate_points_sl_tp(
    order_type: str,
    price: float,
    spec: SymbolSpec,
    sl_points: int = 0,
    tp_points: int = 0,
) -> tuple[float, float]:
    action = order_type.upper()
    sl = 0.0
    tp = 0.0
    if sl_points > 0:
        distance = max(sl_points, spec.stop_level_points) * spec.point
        sl = price - distance if action == "BUY" else price + distance
    if tp_points > 0:
        distance = tp_points * spec.point
        tp = price + distance if action == "BUY" else price - distance
    return (round(sl, spec.digits) if sl > 0 else 0.0, round(tp, spec.digits) if tp > 0 else 0.0)


def block_trade_by_trend(order_type: str, trend: Any, slope_threshold: float = 0.0) -> bool:
    def val(name: str, default: float = 0.0) -> float:
        if hasattr(trend, "columns"):
            if name not in trend.columns or trend.empty:
                return default
            return float(trend[name].iloc[-1])
        if isinstance(trend, dict):
            return float(trend.get(name, default) or default)
        return default

    ema9 = val("ema_9", val("omnis_ema_9"))
    ema21 = val("ema_21", val("omnis_ema_21"))
    ema50 = val("ema_50", val("omnis_ema_50"))
    slope = val("ema_21_slope_norm", val("omnis_trend_slope_21"))
    if order_type.upper() == "BUY":
        return ema9 < ema21 < ema50 and slope < -slope_threshold
    return ema9 > ema21 > ema50 and slope > slope_threshold


def calculate_trailing_sl(
    order_type: str,
    entry: float,
    current_price: float,
    current_sl: float,
    spec: SymbolSpec,
    mode: str = "ATR",
    atr: float | None = None,
    fixed_activation_points: int = 100,
    fixed_distance_points: int = 50,
    atr_start_mult: float = 2.0,
    atr_step_mult: float = 1.2,
    atr_lock_mult: float = 0.8,
    anti_spam_percent: float = 0.2,
) -> float | None:
    action = order_type.upper()
    if mode.upper() == "FIXO":
        profit = current_price - entry if action == "BUY" else entry - current_price
        if profit / spec.point < fixed_activation_points:
            return None
        distance = fixed_distance_points * spec.point
        proposed = current_price - distance if action == "BUY" else current_price + distance + spec.spread
        floor_or_ceiling = entry if action == "BUY" else entry - spec.spread
        new_sl = max(floor_or_ceiling, proposed, current_sl or 0.0) if action == "BUY" else min(floor_or_ceiling, proposed, current_sl or proposed)
        min_move = distance * anti_spam_percent
    else:
        if atr is None or atr <= 0:
            return None
        profit = current_price - entry if action == "BUY" else entry - current_price
        if profit < atr * atr_start_mult:
            return None
        lock = entry + atr * atr_lock_mult if action == "BUY" else entry - atr * atr_lock_mult
        proposed = current_price - atr * atr_step_mult if action == "BUY" else current_price + atr * atr_step_mult
        new_sl = max(lock, proposed, current_sl or 0.0) if action == "BUY" else min(lock, proposed, current_sl or proposed)
        min_move = atr * anti_spam_percent
    if current_sl and abs(new_sl - current_sl) < min_move:
        return None
    return round(new_sl, spec.digits)


class TradeAdapter:
    """Dependency-injected executor. Pass an order_sender for MT5, broker API or simulator."""

    def __init__(self, order_sender: Callable[[dict[str, Any]], Any]):
        self.order_sender = order_sender

    def execute(self, payload: OrderPayload, spec: SymbolSpec, tick: Tick) -> dict[str, Any]:
        validation = validate_symbol_for_order(payload.symbol, payload.action, spec, tick)
        if not validation["ok"]:
            return {"success": False, "ticket": None, "price": None, "error": validation["message"]}
        request = build_order_request(payload, spec, tick)
        result = self.order_sender(request)
        if isinstance(result, dict):
            return result
        return {"success": True, "ticket": getattr(result, "order", None), "price": request["price"], "error": None}


TRADE_HEADERS = [
    "timestamp_open",
    "timestamp_close",
    "symbol",
    "side",
    "confidence",
    "entry_price",
    "stop_loss",
    "take_profit",
    "exit_price",
    "profit",
    "ticket",
]


class TradeCsvLogger:
    def __init__(self, csv_path: str | Path = "logs/trades_Fusion.csv"):
        self.csv_path = Path(csv_path)
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.csv_path.exists():
            with self.csv_path.open("w", newline="", encoding="utf-8") as fh:
                csv.writer(fh).writerow(TRADE_HEADERS)

    def log_open(
        self,
        symbol: str,
        side: str,
        confidence: float,
        entry_price: float,
        ticket: int | str,
        stop_loss: float = 0.0,
        take_profit: float = 0.0,
    ) -> None:
        with self.csv_path.open("a", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow(
                [
                    datetime.now().isoformat(),
                    "",
                    symbol,
                    side,
                    confidence,
                    entry_price,
                    stop_loss,
                    take_profit,
                    "",
                    "",
                    ticket,
                ]
            )

    def log_close(self, ticket: int | str, exit_price: float, profit: float) -> bool:
        rows = list(csv.reader(self.csv_path.open("r", newline="", encoding="utf-8")))
        found = False
        for row in rows[1:]:
            if len(row) >= len(TRADE_HEADERS) and row[-1] == str(ticket) and row[1] == "":
                row[1] = datetime.now().isoformat()
                row[8] = str(exit_price)
                row[9] = str(profit)
                found = True
                break
        if found:
            with self.csv_path.open("w", newline="", encoding="utf-8") as fh:
                csv.writer(fh).writerows(rows)
        return found


def send_telegram_message(
    message: str,
    token: str | None,
    chat_id: str | None,
    enabled: bool = False,
    timeout: int = 5,
) -> bool:
    if not enabled or not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": message, "parse_mode": "HTML"}).encode("utf-8")
    req = urlrequest.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlrequest.urlopen(req, timeout=timeout) as response:
            return 200 <= response.status < 300
    except Exception:
        return False
