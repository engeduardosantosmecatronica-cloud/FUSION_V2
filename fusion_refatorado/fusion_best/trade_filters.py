from __future__ import annotations

from typing import Any

import pandas as pd


DEFAULT_FIB_LEVELS = (0.236, 0.382, 0.5, 0.618, 0.786)
DEFAULT_FIB_WEIGHTS = {"0.236": 0.35, "0.382": 0.65, "0.5": 0.75, "0.618": 1.0, "0.786": 0.55}


def score_m15_entry(features_m15: dict[str, Any], action: str, min_score: int = 7) -> dict[str, Any]:
    score = 0
    reasons: list[str] = []
    trend = features_m15.get("trend", {})
    candles = features_m15.get("candles", {})

    def value(container: Any, key: str, default: float = 0.0) -> float:
        item = container.get(key, default) if isinstance(container, dict) else default
        if hasattr(item, "values"):
            return float(item.values[0])
        return float(item)

    ema9 = value(trend, "ema_9")
    ema21 = value(trend, "ema_21")
    price_dist = value(trend, "price_ema21_dist")
    slope_ema21 = value(trend, "ema_21_slope_norm")
    trend_regime = int(value(trend, "trend_regime"))
    candle_strength = value(candles, "candle_strength")

    if action.upper() == "BUY":
        checks = [
            (slope_ema21 > 0, 3, "EMA21 slope positivo"),
            (candle_strength > 0.5, 2, "Candle comprador forte"),
            (price_dist > 0, 2, "Preco acima da EMA21"),
            (ema9 > ema21, 1, "EMA9 acima da EMA21"),
            (trend_regime >= 0, 2, "Regime nao baixista"),
        ]
    elif action.upper() == "SELL":
        checks = [
            (slope_ema21 < 0, 3, "EMA21 slope negativo"),
            (candle_strength < -0.5, 2, "Candle vendedor forte"),
            (price_dist < 0, 2, "Preco abaixo da EMA21"),
            (ema9 < ema21, 1, "EMA9 abaixo da EMA21"),
            (trend_regime <= 0, 2, "Regime nao altista"),
        ]
    else:
        checks = []

    for passed, points, reason in checks:
        if passed:
            score += points
            reasons.append(reason)
    return {"allowed": score >= min_score, "score": score, "reasons": reasons}


def fibonacci_levels(high: float, low: float, trend_is_up: bool, levels: tuple[float, ...] = DEFAULT_FIB_LEVELS) -> dict[str, float]:
    swing_range = high - low
    if trend_is_up:
        return {f"{level:.3f}": high - swing_range * level for level in levels}
    return {f"{level:.3f}": low + swing_range * level for level in levels}


def fibonacci_entry_score(
    current_price: float,
    df: pd.DataFrame,
    tolerance: float = 0.0015,
    swing_len: int = 20,
    weights: dict[str, float] | None = None,
) -> float:
    if df is None or df.empty or len(df) < swing_len:
        return 0.0
    recent = df.tail(swing_len)
    high = float(recent["high"].max())
    low = float(recent["low"].min())
    high_idx = recent["high"].idxmax()
    low_idx = recent["low"].idxmin()
    trend_is_up = recent.index.get_loc(low_idx) > recent.index.get_loc(high_idx)
    levels = fibonacci_levels(high, low, trend_is_up)
    weights = weights or DEFAULT_FIB_WEIGHTS
    for level_name, level_price in levels.items():
        if level_price and abs(current_price - level_price) / level_price <= tolerance:
            score = weights.get(level_name, 0.5)
            return float(score if trend_is_up else -score)
    return 0.0


def validate_fibonacci_entry(action: str, price: float, df: pd.DataFrame, tolerance: float = 0.0015) -> tuple[bool, str]:
    if df is None or df.empty or len(df) < 20:
        return True, "Dados insuficientes para Fibonacci"
    recent_high = float(df["high"].tail(20).max())
    recent_low = float(df["low"].tail(20).min())
    diff = recent_high - recent_low
    for level in DEFAULT_FIB_LEVELS:
        fib_price = recent_low + level * diff
        if fib_price and abs(price - fib_price) / fib_price < tolerance:
            return True, f"{action.upper()} proximo de Fibonacci {level:.3f}"
    return False, f"{action.upper()} fora de nivel Fibonacci"


def check_strong_alignment(
    ema9: float,
    ema21: float,
    ema50: float,
    point: float,
    min_distance_points: float = 10.0,
) -> tuple[bool, str, float]:
    min_dist = min_distance_points * point
    dist_9_21 = abs(ema9 - ema21)
    dist_21_50 = abs(ema21 - ema50)
    strength = min(1.0, (dist_9_21 + dist_21_50) / (2 * min_dist)) if min_dist else 0.0
    if ema9 > ema21 > ema50:
        return dist_9_21 >= min_dist and dist_21_50 >= min_dist, "BULLISH", strength
    if ema9 < ema21 < ema50:
        return dist_9_21 >= min_dist and dist_21_50 >= min_dist, "BEARISH", strength
    return False, "MIXED", 0.0


def alignment_score(ema9: float, ema21: float, ema50: float, point: float, min_distance_points: float = 10.0) -> float:
    _, direction, strength = check_strong_alignment(ema9, ema21, ema50, point, min_distance_points)
    if direction == "BULLISH":
        return strength
    if direction == "BEARISH":
        return -strength
    return 0.0


def detect_insidebar(df: pd.DataFrame) -> dict[str, Any]:
    if df is None or len(df) < 2:
        return {"is_insidebar": False, "strength": 0.0, "breakout_confirmed": False, "breakout_direction": None}
    mother = df.iloc[-2]
    child = df.iloc[-1]
    child_inside = child["high"] <= mother["high"] and child["low"] >= mother["low"]
    mother_range = float(mother["high"] - mother["low"])
    child_range = float(child["high"] - child["low"])
    strength = 1 - (child_range / mother_range) if mother_range > 0 else 0.0
    breakout_direction = "BUY" if child["close"] > mother["high"] else "SELL" if child["close"] < mother["low"] else None
    return {
        "is_insidebar": bool(child_inside),
        "mother_high": float(mother["high"]),
        "mother_low": float(mother["low"]),
        "child_high": float(child["high"]),
        "child_low": float(child["low"]),
        "strength": float(max(0.0, strength)),
        "breakout_confirmed": breakout_direction is not None,
        "breakout_direction": breakout_direction,
    }


def check_insidebar_breakout(insidebar_info: dict[str, Any], current_price: float, point: float, buffer_points: float = 2.0) -> tuple[bool, str]:
    if not insidebar_info.get("is_insidebar"):
        return False, "NONE"
    buffer = buffer_points * point
    if current_price > float(insidebar_info["mother_high"]) + buffer:
        return True, "BUY"
    if current_price < float(insidebar_info["mother_low"]) - buffer:
        return True, "SELL"
    return False, "NONE"
