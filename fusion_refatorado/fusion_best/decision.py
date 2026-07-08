from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict
from typing import Any
import warnings

import numpy as np
import pandas as pd

from .signals import SignalSide, TradingSignal


@dataclass
class SLTPConfig:
    fixed_sl_points: int = 250
    fixed_tp_points: int = 500
    point: float = 0.0001
    digits: int = 5
    stop_level_points: int = 0
    atr_sl_mult: float = 1.5
    atr_tp_mult: float = 3.0


@dataclass
class DecisionConfig:
    timeframe_weights: dict[str, float] = field(
        default_factory=lambda: {"M5": 0.15, "M15": 0.25, "M30": 0.25, "H1": 0.25, "H4": 0.10}
    )
    confidence_min: float = 0.55
    risk_veto_threshold: float = 70.0
    spread: float = 0.0
    min_distance: float = 0.0
    price_filter_min_orders: int = 3


class AdaptiveThreshold:
    """Rolling z-score threshold used to avoid static signal gates."""

    def __init__(
        self,
        n_bars: int = 100,
        z_factor: float = 1.0,
        history_size: int = 40,
        min_sigma: float = 0.02,
        sensitivity_k: float = 1.0,
        base_buy_threshold: float = 0.30,
        base_sell_threshold: float = -0.10,
    ):
        self.n_bars = n_bars
        self.z_factor = z_factor
        self.history_size = history_size
        self.min_sigma = min_sigma
        self.sensitivity_k = sensitivity_k
        self.base_buy_threshold = base_buy_threshold
        self.base_sell_threshold = base_sell_threshold
        self.all_scores: dict[str, list[float]] = defaultdict(list)
        self.loop_history: dict[str, list[dict[str, float]]] = defaultdict(list)
        self.sigma_history: dict[str, list[float]] = defaultdict(list)

    def calculate_threshold(self, scores: list[float], is_buy: bool = True, current_score: float | None = None) -> tuple[float, float, float]:
        history = list(scores)
        if current_score is not None and history:
            history = history[:-1]
        if len(history) < 2:
            sigma = self.min_sigma
            mu = 0.0
        else:
            arr = np.asarray(history, dtype=float)
            mu = float(np.nanmean(arr))
            sigma = max(float(np.nanstd(arr)), self.min_sigma)
        threshold = mu + self.sensitivity_k * self.z_factor * sigma if is_buy else mu - self.sensitivity_k * self.z_factor * sigma
        return float(threshold), mu, sigma

    def record_score(self, symbol: str, score: float, decision: str | None = None) -> None:
        key = symbol.upper()
        self.all_scores[key].append(float(score))
        self.all_scores[key] = self.all_scores[key][-self.n_bars :]

    def record_loop_result(self, symbol: str, score: float, decision: str, thresholds: dict[str, float]) -> None:
        key = symbol.upper()
        self.record_score(key, score, decision)
        row = {"score": float(score), "buy_threshold": float(thresholds["buy_threshold"]), "sell_threshold": float(thresholds["sell_threshold"])}
        self.loop_history[key].append(row)
        self.loop_history[key] = self.loop_history[key][-self.history_size :]

    def get_thresholds(self, symbol: str, current_score: float | None = None) -> dict[str, float]:
        key = symbol.upper()
        scores = self.all_scores.get(key, [])
        buy, mu_buy, sigma_buy = self.calculate_threshold(scores, True, current_score)
        sell, mu_sell, sigma_sell = self.calculate_threshold(scores, False, current_score)
        self.sigma_history[key].append(max(sigma_buy, sigma_sell))
        self.sigma_history[key] = self.sigma_history[key][-self.n_bars :]
        return {
            "buy_threshold": buy if scores else self.base_buy_threshold,
            "sell_threshold": sell if scores else self.base_sell_threshold,
            "mu_buy": mu_buy,
            "sigma_buy": sigma_buy,
            "mu_sell": mu_sell,
            "sigma_sell": sigma_sell,
        }

    def get_avg_thresholds(self, symbol: str) -> dict[str, float | int]:
        rows = self.loop_history.get(symbol.upper(), [])
        if not rows:
            return {"avg_buy_threshold": self.base_buy_threshold, "avg_sell_threshold": self.base_sell_threshold, "loops_used": 0}
        return {
            "avg_buy_threshold": float(np.mean([row["buy_threshold"] for row in rows])),
            "avg_sell_threshold": float(np.mean([row["sell_threshold"] for row in rows])),
            "loops_used": len(rows),
        }

    def volatility_alert(self, symbol: str, multiplier: float = 1.75) -> bool:
        sigmas = self.sigma_history.get(symbol.upper(), [])
        return len(sigmas) >= 3 and sigmas[0] > 0 and sigmas[-1] > sigmas[0] * multiplier


def hierarchical_model_decision(
    scores: dict[str, float],
    weights: dict[str, float] | None = None,
    buy_threshold: float = 0.01,
    sell_threshold: float = -0.01,
) -> dict[str, Any]:
    layer_weights = weights or {"C1": 0.20, "C2": 0.30, "C3": 0.50}
    total_weight = sum(layer_weights.get(layer, 0.0) for layer in scores)
    if total_weight <= 0:
        final_score = 0.0
    else:
        final_score = sum(float(scores[layer]) * layer_weights.get(layer, 0.0) for layer in scores) / total_weight
    if final_score >= buy_threshold:
        decision = "BUY"
    elif final_score <= sell_threshold:
        decision = "SELL"
    else:
        decision = "NEUTRAL"
    return {
        "decision": decision,
        "score": float(final_score),
        "prob_buy": float(np.clip(0.2 + final_score, 0, 1)),
        "prob_sell": float(np.clip(0.2 - final_score, 0, 1)),
        "prob_hold": float(np.clip(1 - abs(final_score), 0, 1)),
        "layers": scores,
    }


def align_model_features(
    frame: pd.DataFrame,
    expected_features: list[str] | None = None,
    n_features: int | None = None,
) -> pd.DataFrame:
    """Prepare model input without depending on the legacy training package."""
    data = frame.copy()
    data.columns = data.columns.astype(str)
    if expected_features:
        aligned = pd.DataFrame(index=data.index)
        for feature in expected_features:
            if feature in data.columns:
                aligned[feature] = data[feature]
            elif "norm" in feature or "ratio" in feature:
                aligned[feature] = 1.0
            elif "regime" in feature or "score" in feature:
                aligned[feature] = 1.0
            elif "volatility" in feature or "atr" in feature:
                aligned[feature] = 0.005
            elif "dist" in feature:
                aligned[feature] = 0.01
            elif "rsi" in feature:
                aligned[feature] = 50.0
            else:
                aligned[feature] = 0.0
        return aligned.reindex(columns=expected_features)
    if n_features is not None:
        if data.shape[1] < n_features:
            for i in range(n_features - data.shape[1]):
                data[f"missing_{i}"] = 0.0
        elif data.shape[1] > n_features:
            data = data.iloc[:, :n_features]
    return data


def safe_predict(model: Any, frame: pd.DataFrame, model_name: str = "model") -> np.ndarray:
    """Prediction wrapper reused from OMNIS, but package-agnostic."""
    if model is None or frame is None or frame.empty:
        return np.array([0])
    n_features = getattr(model, "n_features_in_", None)
    prepared = align_model_features(frame, n_features=n_features)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)
        warnings.filterwarnings("ignore", message="X does not have valid feature names")
        try:
            return model.predict(prepared.values)
        except Exception:
            return np.array([0])


def calculate_sl_tp(
    order_type: str,
    price: float,
    config: SLTPConfig | None = None,
    atr: float | None = None,
) -> tuple[float, float]:
    """Calculate fixed or ATR-based stop loss and take profit without MT5."""
    cfg = config or SLTPConfig()
    if atr is not None and atr > 0:
        sl_distance = atr * cfg.atr_sl_mult
        tp_distance = atr * cfg.atr_tp_mult
    else:
        sl_points = max(cfg.fixed_sl_points, cfg.stop_level_points + 10)
        tp_points = cfg.fixed_tp_points if cfg.fixed_sl_points >= cfg.stop_level_points else sl_points * 2
        sl_distance = sl_points * cfg.point
        tp_distance = tp_points * cfg.point

    if order_type.upper() == "BUY":
        sl = price - sl_distance
        tp = price + tp_distance
    else:
        sl = price + sl_distance
        tp = price - tp_distance
    return round(sl, cfg.digits), round(tp, cfg.digits)


def price_improvement_filter(
    action: str,
    current_price: float,
    open_positions: list[dict[str, Any]],
    spread: float = 0.0,
    min_distance: float = 0.0,
    min_orders: int = 3,
) -> bool:
    """Avoid stacking entries unless price improved relative to existing orders."""
    if not open_positions:
        return True
    if action.upper() == "BUY":
        buy_prices = [float(p["price_open"]) for p in open_positions if str(p.get("type", "")).upper() == "BUY"]
        if len(buy_prices) < min_orders:
            return True
        best_price = min(buy_prices)
        return (current_price + spread) < best_price and abs(best_price - current_price) >= min_distance
    if action.upper() == "SELL":
        sell_prices = [float(p["price_open"]) for p in open_positions if str(p.get("type", "")).upper() == "SELL"]
        if len(sell_prices) < min_orders:
            return True
        best_price = max(sell_prices)
        return (current_price - spread) > best_price and abs(current_price - best_price) >= min_distance
    return True


def proximity_score(current_price: float, level: float | None, tolerance: float = 0.001, direction: int = 1) -> float:
    if level is None or current_price <= 0 or level <= 0:
        return 0.0
    if abs(current_price - level) / current_price > tolerance:
        return 0.0
    return float(direction if current_price >= level else -direction)


def calculate_confluence_score(
    current_price: float,
    features: dict[str, Any],
    fibonacci_score: float = 0.0,
) -> float:
    """Weighted confluence from Fibonacci, support/resistance, EMA200 and VWAP."""
    if not isinstance(features, dict) or current_price <= 0:
        return 0.0

    trend = features.get("trend")
    orderflow = features.get("orderflow")
    sr_score = 0.0
    ema_score = 0.0
    vwap_score = 0.0

    if isinstance(trend, pd.DataFrame) and not trend.empty:
        row = trend.iloc[-1]
        dist_sup = row.get("dist_to_support", row.get("omnis_dist_support", np.nan))
        dist_res = row.get("dist_to_resistance", row.get("omnis_dist_resistance", np.nan))
        if pd.notna(dist_sup) and pd.notna(dist_res) and dist_sup > 0 and dist_res > 0:
            if dist_res / dist_sup > 5:
                sr_score = 0.75
            elif dist_sup / dist_res > 5:
                sr_score = -0.75
        ema_score = proximity_score(current_price, row.get("ema_200", row.get("omnis_ema_200")), direction=1)

    if isinstance(orderflow, pd.DataFrame) and not orderflow.empty:
        row = orderflow.iloc[-1]
        vwap_score = proximity_score(current_price, row.get("VWAP_D", row.get("omnis_vwap")), direction=1) * 0.5

    scores = {"fibonacci": fibonacci_score, "sr": sr_score, "ema200": ema_score, "vwap": vwap_score}
    weights = {"fibonacci": 0.4, "sr": 0.3, "ema200": 0.2, "vwap": 0.1}
    active_weight = sum(weights[name] for name, value in scores.items() if value != 0)
    if active_weight == 0:
        return 0.0
    total = sum(scores[name] * weights[name] for name in scores)
    return float(np.clip(total / active_weight, -1, 1))


def weighted_timeframe_vote(
    signals_by_tf: dict[str, TradingSignal],
    config: DecisionConfig | None = None,
    confluence: float = 0.0,
    risk_score: float = 0.0,
) -> TradingSignal:
    """Meta-vote inspired by OMNIS, expressed with reusable TradingSignal objects."""
    cfg = config or DecisionConfig()
    if risk_score >= cfg.risk_veto_threshold:
        last = next(iter(signals_by_tf.values()), None)
        return TradingSignal(
            symbol=last.symbol if last else "",
            timeframe="META",
            timestamp=last.timestamp if last else None,
            side=SignalSide.HOLD,
            confidence=0.0,
            price=last.price if last else 0.0,
            source="weighted_timeframe_vote",
            components={"reason": "risk_veto", "risk_score": risk_score},
        )

    weighted_score = 0.0
    total_weight = 0.0
    valid: list[TradingSignal] = []
    for tf, signal in signals_by_tf.items():
        weight = cfg.timeframe_weights.get(tf, 0.0)
        if weight <= 0:
            continue
        valid.append(signal)
        weighted_score += int(signal.side) * signal.confidence * weight
        total_weight += weight

    if not valid or total_weight <= 0:
        return TradingSignal("", "META", None, SignalSide.HOLD, 0.0, 0.0, "weighted_timeframe_vote")

    score = weighted_score / total_weight
    score = float(np.clip(score + confluence * 0.25, -2, 2))
    confidence = min(abs(score), 1.0)
    if confidence < cfg.confidence_min:
        side = SignalSide.HOLD
    elif score > 1.25:
        side = SignalSide.STRONG_BUY
    elif score > 0:
        side = SignalSide.BUY
    elif score < -1.25:
        side = SignalSide.STRONG_SELL
    else:
        side = SignalSide.SELL

    last = valid[-1]
    return TradingSignal(
        symbol=last.symbol,
        timeframe="META",
        timestamp=last.timestamp,
        side=side,
        confidence=float(confidence),
        price=last.price,
        source="weighted_timeframe_vote",
        components={
            "score": score,
            "confluence": confluence,
            "risk_score": risk_score,
            "votes": [signal.to_dict() for signal in valid],
        },
    )
