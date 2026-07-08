from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd


DEFAULT_CONFIDENCE_WEIGHTS = {
    "model_trend": 0.15,
    "model_orderflow": 0.15,
    "model_candles": 0.10,
    "model_sr": 0.10,
    "regime_de_mercado": 0.15,
    "alinhamento_mtf": 0.12,
    "pontuacao_confluencia": 0.08,
    "alignment_strength": 0.10,
    "model_risk": -0.05,
}


def _true_range(df: pd.DataFrame) -> pd.Series:
    return pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - df["close"].shift(1)).abs(),
            (df["low"] - df["close"].shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / (loss + 1e-12)
    return 100 - (100 / (1 + rs))


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _macd(close: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    line = _ema(close, 12) - _ema(close, 26)
    signal = _ema(line, 9)
    return line, signal, line - signal


def _adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"]
    low = df["low"]
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=df.index)
    atr = _true_range(df).rolling(period).mean()
    plus_di = 100 * plus_dm.rolling(period).sum() / (atr.rolling(period).sum() + 1e-12)
    minus_di = 100 * minus_dm.rolling(period).sum() / (atr.rolling(period).sum() + 1e-12)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-12)
    return dx.rolling(period).mean()


@dataclass
class ConfidenceEngine:
    weights: dict[str, float] | None = None
    threshold: float = 0.20

    def calculate_score(self, signals: dict[str, Any]) -> dict[str, Any]:
        weights = self.weights or DEFAULT_CONFIDENCE_WEIGHTS
        total_score = 0.0
        total_weight = 0.0
        components: dict[str, dict[str, float]] = {}
        for factor, weight in weights.items():
            raw = float(signals.get(factor, 0.0) or 0.0)
            score = abs(raw) if factor == "alignment_strength" else float(np.clip(raw, -1, 1))
            contribution = score * weight
            total_score += contribution
            if score != 0:
                total_weight += abs(weight)
            components[factor] = {"score": score, "weight": weight, "contribution": contribution}
        final_score = total_score / total_weight if total_weight else 0.0
        action = "BUY" if final_score > self.threshold else "SELL" if final_score < -self.threshold else "HOLD"
        return {
            "action": action,
            "confidence": round(abs(final_score), 4),
            "final_score": round(final_score, 4),
            "components": components,
        }


def calculate_mtf_alignment_score(features_by_tf: dict[str, dict[str, Any]]) -> float:
    weights = {"M5": 0.5, "M15": 0.3, "H1": 0.2}
    score = 0.0
    total = 0.0
    for tf, weight in weights.items():
        trend = features_by_tf.get(tf, {}).get("trend")
        if isinstance(trend, pd.DataFrame) and not trend.empty:
            signal = trend.iloc[-1].get("ema_alignment", trend.iloc[-1].get("omnis_trend_signal", 0))
            score += float(np.clip(signal, -1, 1)) * weight
            total += weight
        elif isinstance(trend, dict):
            score += float(np.clip(trend.get("ema_alignment", trend.get("omnis_trend_signal", 0)), -1, 1)) * weight
            total += weight
    return score / total if total else 0.0


def calculate_alignment_strength_score(alignment_scores: dict[str, float]) -> float:
    weights = {"M5": 0.5, "M15": 0.3, "H1": 0.2, "M30": 0.15, "H4": 0.1}
    total = sum(weights[tf] for tf in alignment_scores if tf in weights)
    if total == 0:
        return 0.0
    return sum(abs(alignment_scores[tf]) * weights[tf] for tf in alignment_scores if tf in weights) / total


def check_strong_alignment(
    ema9: float,
    ema21: float,
    ema50: float,
    point: float = 0.0001,
    min_distance_points: float = 30,
) -> tuple[bool, str, float]:
    min_distance = min_distance_points * point
    dist_9_21 = abs(ema9 - ema21)
    dist_21_50 = abs(ema21 - ema50)
    strength = min(1.0, (dist_9_21 + dist_21_50) / (2 * min_distance + 1e-12))
    if ema9 > ema21 > ema50:
        return dist_9_21 >= min_distance and dist_21_50 >= min_distance, "BULLISH", strength
    if ema9 < ema21 < ema50:
        return dist_9_21 >= min_distance and dist_21_50 >= min_distance, "BEARISH", strength
    return False, "MIXED", 0.0


def ema_alignment_score(
    ema9: float,
    ema21: float,
    ema50: float,
    point: float = 0.0001,
    min_distance_points: float = 30,
) -> float:
    _, direction, strength = check_strong_alignment(ema9, ema21, ema50, point, min_distance_points)
    return strength if direction == "BULLISH" else -strength if direction == "BEARISH" else 0.0


def fibonacci_levels(high: float, low: float, trend_is_up: bool, levels: tuple[float, ...] = (0.236, 0.382, 0.5, 0.618, 0.786)) -> dict[str, float]:
    swing = high - low
    if trend_is_up:
        return {f"{level:.3f}": high - swing * level for level in levels}
    return {f"{level:.3f}": low + swing * level for level in levels}


def fibonacci_score(
    current_price: float,
    df: pd.DataFrame,
    tolerance: float = 0.001,
    swing_len: int = 50,
    weights: dict[str, float] | None = None,
) -> float:
    if df is None or df.empty or len(df) < max(5, swing_len // 2):
        return 0.0
    recent = df.tail(swing_len)
    high = float(recent["high"].max())
    low = float(recent["low"].min())
    high_idx = recent["high"].idxmax()
    low_idx = recent["low"].idxmin()
    trend_is_up = recent.index.get_loc(low_idx) > recent.index.get_loc(high_idx)
    levels = fibonacci_levels(high, low, trend_is_up)
    score_weights = weights or {"0.236": 0.4, "0.382": 0.7, "0.500": 0.8, "0.618": 1.0, "0.786": 0.6}
    for name, level_price in levels.items():
        if level_price and abs(current_price - level_price) / level_price <= tolerance:
            score = score_weights.get(name, 0.5)
            return score if trend_is_up else -score
    return 0.0


def consistency_check(
    order_type: str,
    decision: dict[str, Any],
    current_positions: list[Any],
    max_positions_per_direction: int = 3,
    min_confidence: float = 0.45,
) -> dict[str, Any]:
    score = 100
    reasons: list[str] = []
    same_dir = 0
    for pos in current_positions:
        pos_type = getattr(pos, "type", None) or getattr(pos, "side", None) or (pos.get("type") if isinstance(pos, dict) else None)
        if str(pos_type).upper() == order_type.upper():
            same_dir += 1
    if same_dir >= max_positions_per_direction:
        return {"approved": False, "score": 0, "reasons": [f"Maximo de {max_positions_per_direction} posicoes"], "lot_multiplier": 0.0}
    if float(decision.get("confidence", 0.0)) < min_confidence:
        score -= 30
        reasons.append(f"Confianca baixa: {decision.get('confidence', 0.0):.2f}")
    return {"approved": score >= 60, "score": score, "reasons": reasons, "lot_multiplier": max(0.3, min(1.0, score / 100))}


@dataclass
class MarketRegimeAnalyzer:
    adx_threshold: float = 25.0
    last_regime: dict[str, Any] | None = None

    def analyze(self, df: pd.DataFrame | None) -> dict[str, Any]:
        if df is not None and len(df) >= 30:
            adx = float(_adx(df).iloc[-1])
            if adx < 20:
                result = {"regime": "CHOPPY", "score": 0.2, "is_tradable": False, "adx": adx}
            elif adx > self.adx_threshold:
                result = {"regime": "TRENDING", "score": 1.0, "is_tradable": True, "adx": adx}
            else:
                result = {"regime": "RANGING", "score": 0.7, "is_tradable": True, "adx": adx}
            self.last_regime = result
            return result
        return (self.last_regime or {"regime": "NORMAL", "score": 0.5, "is_tradable": True, "adx": 25.0}).copy()


def extract_orderflow_context(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    result = df.copy()
    volume = result["tick_volume"] if "tick_volume" in result.columns else result.get("volume", pd.Series(1.0, index=result.index))
    result["log_return"] = np.log(result["close"] / result["close"].shift(1))
    vol_mean = volume.rolling(window).mean()
    vol_std = volume.rolling(window).std()
    result["tick_volume_zscore"] = (volume - vol_mean) / (vol_std + 1e-12)
    result["tick_volume_change"] = volume.pct_change()
    result["directional_pressure"] = volume * np.sign(result["log_return"])
    result["orderflow_delta"] = result["directional_pressure"].rolling(window).sum()
    result["orderflow_delta_norm"] = result["orderflow_delta"] / (volume.rolling(window).sum() + 1e-12)
    result["orderflow_intensity"] = result["orderflow_delta_norm"].abs()
    result["orderflow_regime"] = np.sign(result["orderflow_delta_norm"])
    result["delta_momentum"] = result["orderflow_delta_norm"].diff()
    result["pressure_change"] = result["orderflow_intensity"].diff()
    result["volume_trend"] = volume.rolling(10).mean().pct_change()
    result["flow_acceleration"] = result["delta_momentum"].diff()
    typical_price = (result["high"] + result["low"] + result["close"]) / 3
    result["vwap"] = (typical_price * volume).cumsum() / (volume.cumsum() + 1e-12)
    result["VWAP_D"] = (result["close"] - result["vwap"]) / (result["vwap"] + 1e-12) * 100
    result["vwap_position"] = np.sign(result["close"] - result["vwap"])
    return result.replace([np.inf, -np.inf], np.nan).fillna(0.0)


def extract_volatility_context(df: pd.DataFrame, atr_short: int = 5, atr_long: int = 14, vol_window: int = 10) -> pd.DataFrame:
    result = df.copy()
    tr = _true_range(result)
    result["atr_short"] = tr.rolling(atr_short).mean()
    result["atr_long"] = tr.rolling(atr_long).mean()
    result["log_return"] = np.log(result["close"] / result["close"].shift(1))
    result["volatility_std"] = result["log_return"].rolling(vol_window).std()
    result["candle_range"] = result["high"] - result["low"]
    result["range_norm"] = result["candle_range"] / (result["atr_long"] + 1e-12)
    result["atr_ratio"] = result["atr_short"] / (result["atr_long"] + 1e-12)
    conditions = [result["atr_ratio"] < 0.8, result["atr_ratio"].between(0.8, 1.2), result["atr_ratio"].between(1.2, 1.8), result["atr_ratio"] >= 1.8]
    result["context_volatility_regime"] = np.select(conditions, [0, 1, 2, 3], default=1)
    return result.replace([np.inf, -np.inf], np.nan).dropna()


def detect_pivots(df: pd.DataFrame, window: int = 3) -> pd.DataFrame:
    result = df.copy()
    result["pivot_high"] = (result["high"].shift(window) == result["high"].rolling(window * 2 + 1).max()).astype(int)
    result["pivot_low"] = (result["low"].shift(window) == result["low"].rolling(window * 2 + 1).min()).astype(int)
    return result


def extract_sr_context(df: pd.DataFrame, pivot_window: int = 3, atr_col: str = "atr_short") -> pd.DataFrame:
    result = detect_pivots(df, pivot_window).copy()
    if atr_col not in result.columns:
        result[atr_col] = _true_range(result).rolling(14).mean()
    for col in ("dist_to_resistance", "dist_to_support", "sr_position"):
        result[col] = np.nan
    result["sr_strength"] = 0.0
    result["sr_recency"] = 0.0
    resistance: list[tuple[float, int, int]] = []
    support: list[tuple[float, int, int]] = []

    def update(zones: list[tuple[float, int, int]], price: float, tolerance: float, idx: int) -> list[tuple[float, int, int]]:
        for pos, (level, strength, last_idx) in enumerate(zones):
            if abs(price - level) <= tolerance:
                zones[pos] = ((level * strength + price) / (strength + 1), strength + 1, idx)
                return zones
        zones.append((price, 1, idx))
        return zones

    for i in range(len(result)):
        price = result["close"].iloc[i]
        atr = result[atr_col].iloc[i]
        if pd.isna(atr) or atr == 0:
            continue
        tolerance = atr * 0.5
        if result["pivot_high"].iloc[i] == 1:
            resistance = update(resistance, result["high"].iloc[i], tolerance, i)
        if result["pivot_low"].iloc[i] == 1:
            support = update(support, result["low"].iloc[i], tolerance, i)
        res_candidates = [z for z in resistance if z[0] >= price]
        sup_candidates = [z for z in support if z[0] <= price]
        res_lvl = sup_lvl = np.nan
        res_strength = sup_strength = 0
        res_recency = sup_recency = 999
        if res_candidates:
            res_lvl, res_strength, last = min(res_candidates, key=lambda z: abs(z[0] - price))
            res_recency = i - last
            result.at[result.index[i], "dist_to_resistance"] = res_lvl - price
        if sup_candidates:
            sup_lvl, sup_strength, last = min(sup_candidates, key=lambda z: abs(z[0] - price))
            sup_recency = i - last
            result.at[result.index[i], "dist_to_support"] = price - sup_lvl
        if not pd.isna(res_lvl) and not pd.isna(sup_lvl) and res_lvl > sup_lvl:
            result.at[result.index[i], "sr_position"] = (price - sup_lvl) / (res_lvl - sup_lvl)
        result.at[result.index[i], "sr_strength"] = max(res_strength, sup_strength)
        result.at[result.index[i], "sr_recency"] = np.exp(-min(res_recency, sup_recency) / 50)
    return result.replace([np.inf, -np.inf], np.nan).fillna(0.0)


def detect_insidebar(df: pd.DataFrame) -> dict[str, Any]:
    if df is None or len(df) < 2:
        return {"is_insidebar": False, "strength": 0.0}
    mother = df.iloc[-2]
    inside = df.iloc[-1]
    is_inside = inside["high"] < mother["high"] and inside["low"] > mother["low"]
    mother_range = mother["high"] - mother["low"]
    inside_range = inside["high"] - inside["low"]
    compression = 1 - inside_range / (mother_range + 1e-12)
    return {
        "is_insidebar": bool(is_inside),
        "mother_high": float(mother["high"]),
        "mother_low": float(mother["low"]),
        "inside_high": float(inside["high"]),
        "inside_low": float(inside["low"]),
        "strength": float(np.clip(compression, 0, 1)),
    }


def check_insidebar_breakout(insidebar: dict[str, Any], current_price: float) -> tuple[bool, str]:
    if not insidebar.get("is_insidebar"):
        return False, "HOLD"
    if current_price > insidebar["mother_high"]:
        return True, "BUY"
    if current_price < insidebar["mother_low"]:
        return True, "SELL"
    return False, "HOLD"


def apply_insidebar_filter(
    order_type: str,
    decision: dict[str, Any],
    df: pd.DataFrame,
    current_price: float,
    level: int = 2,
    min_strength: float = 0.5,
    confidence_boost: float = 0.3,
    trigger_strength: float = 0.8,
) -> tuple[bool, str, dict[str, Any]]:
    insidebar = detect_insidebar(df)
    if not insidebar["is_insidebar"]:
        return False, "Sem insidebar detectado", decision
    broke, direction = check_insidebar_breakout(insidebar, current_price)
    if level == 1:
        if broke and direction != order_type and order_type != "HOLD":
            return True, f"Insidebar contrario: {direction}", decision
        return False, "Insidebar nivel 1 OK", decision
    if level == 3 and broke and insidebar["strength"] >= trigger_strength:
        updated = dict(decision)
        updated["action"] = direction
        updated["confidence"] = max(float(updated.get("confidence", 0.0)), 0.8)
        return False, f"Insidebar gatilho {direction}", updated
    if level == 2 and broke:
        updated = dict(decision)
        if direction == order_type:
            updated["confidence"] = min(1.0, float(updated.get("confidence", 0.0)) * (1 + confidence_boost))
            return False, "Insidebar confirmando", updated
        if order_type != "HOLD" and insidebar["strength"] > min_strength:
            updated["confidence"] = float(updated.get("confidence", 0.0)) * 0.6
            return updated["confidence"] < 0.3, "Insidebar contrario", updated
    return False, "Insidebar OK", decision


def _tf_value(features: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = features.get(key, default)
    if isinstance(value, pd.Series):
        value = value.iloc[-1]
    return float(value) if value is not None and not pd.isna(value) else default


def detect_pullback(features_by_tf: dict[str, dict[str, Any]]) -> bool:
    macro_count = 0
    for tf in ("D1", "H4", "H1"):
        features = features_by_tf.get(tf, {})
        if _tf_value(features, "candle_direction") > 0 or _tf_value(features, "ema_9_slope_norm") > 0:
            macro_count += 1
    micro_count = 0
    for tf in ("M5", "M15"):
        features = features_by_tf.get(tf, {})
        if _tf_value(features, "candle_direction") < 0 or _tf_value(features, "ema_9_slope_norm") < 0:
            micro_count += 1
    m15 = features_by_tf.get("M15", {})
    price_declining = (
        _tf_value(m15, "volume_declining_pattern") > 0
        or _tf_value(m15, "ema_velocity") < -0.001
        or (_tf_value(m15, "close") > 0 and _tf_value(m15, "close") < _tf_value(m15, "ema_21") * 0.995)
    )
    return macro_count >= 2 and micro_count >= 1 and price_declining


def get_pullback_details(features_by_tf: dict[str, dict[str, Any]]) -> dict[str, bool]:
    return {
        "is_pullback": detect_pullback(features_by_tf),
        "macro_uptrend": sum(
            1
            for tf in ("D1", "H4", "H1")
            if _tf_value(features_by_tf.get(tf, {}), "candle_direction") > 0
            or _tf_value(features_by_tf.get(tf, {}), "ema_9_slope_norm") > 0
        ) >= 2,
        "micro_downtrend": sum(
            1
            for tf in ("M5", "M15")
            if _tf_value(features_by_tf.get(tf, {}), "candle_direction") < 0
            or _tf_value(features_by_tf.get(tf, {}), "ema_9_slope_norm") < 0
        ) >= 1,
    }


class DivergenceType(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"


@dataclass
class DivergencePoint:
    oscillator: str
    type: DivergenceType
    strength: float
    price_idx: int
    previous_idx: int


@dataclass
class DivergenceDetector:
    lookback: int = 100
    pivot_window: int = 5
    min_separation: int = 3

    def oscillators(self, df: pd.DataFrame) -> pd.DataFrame:
        result = pd.DataFrame(index=df.index)
        result["rsi"] = _rsi(df["close"], 14)
        macd, signal, hist = _macd(df["close"])
        result["macd"] = macd
        result["macd_hist"] = hist
        result["momentum"] = df["close"] - df["close"].shift(10)
        typical = (df["high"] + df["low"] + df["close"]) / 3
        result["cci"] = (typical - typical.rolling(20).mean()) / (0.015 * typical.rolling(20).std() + 1e-12)
        volume = df["tick_volume"] if "tick_volume" in df.columns else df.get("volume", pd.Series(1.0, index=df.index))
        direction = np.sign(df["close"].diff()).fillna(0)
        result["obv"] = (direction * volume).cumsum()
        stoch_low = df["low"].rolling(14).min()
        stoch_high = df["high"].rolling(14).max()
        result["stoch"] = 100 * (df["close"] - stoch_low) / (stoch_high - stoch_low + 1e-12)
        mf_multiplier = ((df["close"] - df["low"]) - (df["high"] - df["close"])) / (df["high"] - df["low"] + 1e-12)
        result["cmf"] = (mf_multiplier * volume).rolling(20).sum() / (volume.rolling(20).sum() + 1e-12)
        return result.replace([np.inf, -np.inf], np.nan)

    def pivots(self, series: pd.Series) -> tuple[list[int], list[int]]:
        values = series.to_numpy()
        highs: list[int] = []
        lows: list[int] = []
        for i in range(self.pivot_window, len(values) - self.pivot_window):
            window = values[i - self.pivot_window : i + self.pivot_window + 1]
            if np.isfinite(values[i]) and values[i] == np.nanmax(window):
                highs.append(i)
            if np.isfinite(values[i]) and values[i] == np.nanmin(window):
                lows.append(i)
        return highs, lows

    def detect_pair(self, price: pd.Series, indicator: pd.Series, oscillator: str) -> list[DivergencePoint]:
        price = price.tail(self.lookback).reset_index(drop=True)
        indicator = indicator.tail(self.lookback).reset_index(drop=True)
        price_highs, price_lows = self.pivots(price)
        ind_highs, ind_lows = self.pivots(indicator)
        divergences: list[DivergencePoint] = []
        for prev, curr in zip(price_lows[-4:-1], price_lows[-3:]):
            if curr - prev < self.min_separation:
                continue
            ind_prev = max([i for i in ind_lows if i <= prev], default=None)
            ind_curr = max([i for i in ind_lows if i <= curr], default=None)
            if ind_prev is not None and ind_curr is not None and price.iloc[curr] < price.iloc[prev] and indicator.iloc[ind_curr] > indicator.iloc[ind_prev]:
                strength = float(abs((indicator.iloc[ind_curr] - indicator.iloc[ind_prev]) / (abs(indicator.iloc[ind_prev]) + 1e-12)))
                divergences.append(DivergencePoint(oscillator, DivergenceType.BULLISH, strength, curr, prev))
        for prev, curr in zip(price_highs[-4:-1], price_highs[-3:]):
            if curr - prev < self.min_separation:
                continue
            ind_prev = max([i for i in ind_highs if i <= prev], default=None)
            ind_curr = max([i for i in ind_highs if i <= curr], default=None)
            if ind_prev is not None and ind_curr is not None and price.iloc[curr] > price.iloc[prev] and indicator.iloc[ind_curr] < indicator.iloc[ind_prev]:
                strength = float(abs((indicator.iloc[ind_curr] - indicator.iloc[ind_prev]) / (abs(indicator.iloc[ind_prev]) + 1e-12)))
                divergences.append(DivergencePoint(oscillator, DivergenceType.BEARISH, strength, curr, prev))
        return divergences

    def analyze(self, df: pd.DataFrame, timeframe: str = "H1") -> dict[str, Any]:
        osc = self.oscillators(df)
        divergences: list[DivergencePoint] = []
        for name in osc.columns:
            divergences.extend(self.detect_pair(df["close"], osc[name], name))
        bullish = sum(1 for div in divergences if div.type == DivergenceType.BULLISH)
        bearish = sum(1 for div in divergences if div.type == DivergenceType.BEARISH)
        signal, confidence = self.signal(divergences)
        return {
            "timeframe": timeframe,
            "divergences": divergences,
            "summary": {"bullish": bullish, "bearish": bearish, "total": len(divergences)},
            "signal": signal,
            "confidence": confidence,
        }

    def signal(self, divergences: list[DivergencePoint]) -> tuple[int, float]:
        bullish = sum(0.5 if div.strength < 0.05 else 2.0 if div.strength > 0.1 else 1.0 for div in divergences if div.type == DivergenceType.BULLISH)
        bearish = sum(0.5 if div.strength < 0.05 else 2.0 if div.strength > 0.1 else 1.0 for div in divergences if div.type == DivergenceType.BEARISH)
        total = bullish + bearish
        if total == 0:
            return 0, 0.0
        score = (bullish - bearish) / total
        confidence = min(total / 5, 1.0)
        return (1 if score > 0.3 else -1 if score < -0.3 else 0), float(confidence)


def check_divergences(df: pd.DataFrame, timeframe: str = "H1") -> dict[str, Any]:
    detector = DivergenceDetector()
    return detector.analyze(df, timeframe)
