from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class MacroFlowConfig:
    timeframes: list[str]
    bars: int = 260
    ema_fast: int = 21
    ema_slow: int = 50
    atr_period: int = 14
    momentum_bars: int = 20
    min_score: float = 0.20
    weights: dict[str, float] | None = None
    aggregation: str = "weighted_majority"
    currency_strength_enabled: bool = True
    currency_strength_weight: float = 0.35


TIMEFRAME_MINUTES = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "M30": 30,
    "H1": 60,
    "H4": 240,
    "D1": 1440,
}


def split_forex_symbol(symbol: str) -> tuple[str, str] | None:
    symbol = symbol.upper()
    if len(symbol) != 6:
        return None
    known = {"USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD", "SGD"}
    base = symbol[:3]
    quote = symbol[3:]
    if base in known and quote in known:
        return base, quote
    return None


def true_range(df: pd.DataFrame) -> pd.Series:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    prev_close = close.shift(1)
    return pd.concat([(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)


def timeframe_flow(df: pd.DataFrame, cfg: MacroFlowConfig) -> dict[str, Any]:
    if df.empty or len(df) < max(cfg.ema_slow + 5, cfg.momentum_bars + 5, cfg.atr_period + 5):
        return {"score": 0.0, "direction": "NEUTRO", "reason": "dados_insuficientes"}

    frame = df.sort_values("time").reset_index(drop=True).copy()
    close = frame["close"].astype(float)
    ema_fast = close.ewm(span=cfg.ema_fast, adjust=False).mean()
    ema_slow = close.ewm(span=cfg.ema_slow, adjust=False).mean()
    atr = true_range(frame).rolling(cfg.atr_period).mean()
    last_atr = float(atr.iloc[-1])
    if not np.isfinite(last_atr) or last_atr <= 0:
        return {"score": 0.0, "direction": "NEUTRO", "reason": "atr_indisponivel"}

    fast = float(ema_fast.iloc[-1])
    slow = float(ema_slow.iloc[-1])
    price = float(close.iloc[-1])
    fast_slope = float(ema_fast.iloc[-1] - ema_fast.iloc[-1 - min(cfg.momentum_bars, len(ema_fast) - 2)])
    slow_slope = float(ema_slow.iloc[-1] - ema_slow.iloc[-1 - min(cfg.momentum_bars, len(ema_slow) - 2)])
    momentum = float(close.iloc[-1] - close.iloc[-1 - cfg.momentum_bars])

    trend_component = np.tanh(((fast - slow) / last_atr) / 2.0)
    price_component = np.tanh(((price - slow) / last_atr) / 2.0)
    slope_component = np.tanh(((fast_slope + slow_slope) / last_atr) / 2.0)
    momentum_component = np.tanh((momentum / last_atr) / 2.0)
    score = float(np.mean([trend_component, price_component, slope_component, momentum_component]))
    if score > 0.05:
        direction = "BUY"
    elif score < -0.05:
        direction = "SELL"
    else:
        direction = "NEUTRO"

    return {
        "score": score,
        "direction": direction,
        "price": price,
        "ema_fast": fast,
        "ema_slow": slow,
        "atr": last_atr,
        "trend_component": float(trend_component),
        "price_component": float(price_component),
        "slope_component": float(slope_component),
        "momentum_component": float(momentum_component),
        "reason": "ok",
    }


def aggregate_symbol_flow(tf_results: dict[str, dict[str, Any]], cfg: MacroFlowConfig) -> dict[str, Any]:
    weights = cfg.weights or {}
    total_weight = 0.0
    weighted_score = 0.0
    bullish_weight = 0.0
    bearish_weight = 0.0
    reasons = []
    for tf, result in tf_results.items():
        weight = float(weights.get(tf, TIMEFRAME_MINUTES.get(tf, 60)) or 1.0)
        if result.get("reason") != "ok":
            reasons.append(f"{tf}:{result.get('reason')}")
            continue
        total_weight += weight
        score = float(result.get("score", 0.0))
        weighted_score += score * weight
        if score > 0:
            bullish_weight += weight
        elif score < 0:
            bearish_weight += weight
    if total_weight <= 0:
        return {"score": 0.0, "direction": "NEUTRO", "reason": ";".join(reasons or ["sem_fluxo"])}
    score = weighted_score / total_weight
    if cfg.aggregation == "weighted_majority":
        vote_score = (bullish_weight - bearish_weight) / total_weight
        direction = "BUY" if vote_score > cfg.min_score else "SELL" if vote_score < -cfg.min_score else "NEUTRO"
        return {
            "score": float(vote_score),
            "raw_score": float(score),
            "direction": direction,
            "bullish_weight": float(bullish_weight),
            "bearish_weight": float(bearish_weight),
            "total_weight": float(total_weight),
            "reason": "ok" if direction != "NEUTRO" else "macro_neutro",
        }
    direction = "BUY" if score > cfg.min_score else "SELL" if score < -cfg.min_score else "NEUTRO"
    return {
        "score": float(score),
        "raw_score": float(score),
        "direction": direction,
        "bullish_weight": float(bullish_weight),
        "bearish_weight": float(bearish_weight),
        "total_weight": float(total_weight),
        "reason": "ok" if direction != "NEUTRO" else "macro_neutro",
    }


def currency_strength_from_flows(symbol_flows: dict[str, float]) -> dict[str, float]:
    totals: dict[str, float] = {}
    counts: dict[str, int] = {}
    for symbol, score in symbol_flows.items():
        parsed = split_forex_symbol(symbol)
        if not parsed:
            continue
        base, quote = parsed
        totals[base] = totals.get(base, 0.0) + score
        counts[base] = counts.get(base, 0) + 1
        totals[quote] = totals.get(quote, 0.0) - score
        counts[quote] = counts.get(quote, 0) + 1
    return {currency: totals[currency] / counts[currency] for currency in totals if counts.get(currency, 0) > 0}


def direction_to_prediction(direction: str) -> int:
    direction = direction.upper()
    if direction == "BUY":
        return 1
    if direction == "SELL":
        return 2
    return 0
