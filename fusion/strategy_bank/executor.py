from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np
import pandas as pd


BUY = 1
SELL = 2


@dataclass(frozen=True)
class StrategySignal:
    asset: str
    strategy_id: str
    setup: str
    timeframe: str
    timestamp: Any
    side: str
    prediction: int
    entry_price: float
    tp_price: float
    sl_price: float
    confidence_hint: float
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)


def normalize_ohlcv(frame: pd.DataFrame) -> pd.DataFrame:
    df = frame.copy()
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
    elif "time" in df.columns:
        df["date"] = pd.to_datetime(df["time"])
        df = df.sort_values("date").reset_index(drop=True)
    else:
        df = df.reset_index().rename(columns={"index": "date"})
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

    for col in ("open", "high", "low", "close"):
        if col not in df.columns:
            raise ValueError(f"OHLCV frame missing required column: {col}")
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if "tick_volume" not in df.columns:
        df["tick_volume"] = 0.0
    if "spread" not in df.columns:
        df["spread"] = 0.0
    if "point_value" not in df.columns:
        df["point_value"] = infer_point_value(df["close"])
    df["point_value"] = pd.to_numeric(df["point_value"], errors="coerce").ffill().bfill()
    return df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)


def infer_point_value(close: pd.Series) -> float:
    median = float(close.dropna().median()) if not close.dropna().empty else 1.0
    if median > 500:
        return 0.01
    if median > 20:
        return 0.001
    if median > 3:
        return 0.0001
    return 0.00001


def enrich_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    df = normalize_ohlcv(frame)
    close = df["close"]
    high = df["high"]
    low = df["low"]
    open_ = df["open"]

    for period in (8, 21, 50, 200):
        df[f"ema{period}"] = close.ewm(span=period, adjust=False).mean()
        df[f"ema{period}_slope"] = df[f"ema{period}"].diff(5)

    tr_parts = pd.concat(
        [
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    )
    df["tr"] = tr_parts.max(axis=1)
    df["atr14"] = df["tr"].rolling(14).mean()
    df["atr_ratio"] = df["atr14"] / (df["atr14"].rolling(80).mean() + 1e-12)

    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
    rs = gain / (loss + 1e-12)
    df["rsi14"] = 100 - (100 / (1 + rs))

    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    atr = df["tr"].rolling(14).mean()
    plus_di = 100 * pd.Series(plus_dm, index=df.index).rolling(14).mean() / (atr + 1e-12)
    minus_di = 100 * pd.Series(minus_dm, index=df.index).rolling(14).mean() / (atr + 1e-12)
    dx = ((plus_di - minus_di).abs() / ((plus_di + minus_di) + 1e-12)) * 100
    df["adx14"] = dx.rolling(14).mean()

    df["range_high20"] = high.shift(1).rolling(20).max()
    df["range_low20"] = low.shift(1).rolling(20).min()
    df["range_mid20"] = (df["range_high20"] + df["range_low20"]) / 2
    df["range_high50"] = high.shift(1).rolling(50).max()
    df["range_low50"] = low.shift(1).rolling(50).min()
    df["body"] = (close - open_).abs()
    df["body_ratio"] = df["body"] / (df["atr14"] + 1e-12)
    df["upper_wick"] = high - np.maximum(open_, close)
    df["lower_wick"] = np.minimum(open_, close) - low
    df["bullish"] = close > open_
    df["bearish"] = close < open_
    df["hour_utc"] = df["date"].dt.hour
    return df


def point_value(df: pd.DataFrame, idx: int) -> float:
    value = float(df.iloc[idx].get("point_value", 0.0) or 0.0)
    return value if value > 0 else infer_point_value(df["close"])


def build_signal(
    strategy: dict,
    df: pd.DataFrame,
    idx: int,
    prediction: int,
    reason: str,
    confidence_hint: float,
    metadata: dict[str, Any] | None = None,
) -> StrategySignal:
    row = df.iloc[idx]
    pv = point_value(df, idx)
    risk = strategy.get("risk", {})
    tp_points = float(risk.get("tp_points", 0) or 0)
    sl_points = float(risk.get("sl_points", 0) or 0)
    entry = float(row["close"])
    side = "BUY" if prediction == BUY else "SELL"
    if prediction == BUY:
        tp = entry + tp_points * pv
        sl = entry - sl_points * pv
    else:
        tp = entry - tp_points * pv
        sl = entry + sl_points * pv
    return StrategySignal(
        asset=strategy["asset"],
        strategy_id=strategy["id"],
        setup=strategy["setup"],
        timeframe=str(row.get("timeframe", "")) or str(strategy.get("timeframe", "")),
        timestamp=row["date"],
        side=side,
        prediction=prediction,
        entry_price=entry,
        tp_price=tp,
        sl_price=sl,
        confidence_hint=float(confidence_hint),
        reason=reason,
        metadata={**(metadata or {}), "row_index": int(idx)},
    )


def _append_if_model_allows(
    signals: list[StrategySignal],
    strategy: dict,
    df: pd.DataFrame,
    idx: int,
    prediction: int,
    reason: str,
    confidence_hint: float,
    model_predictions: pd.DataFrame | None,
    metadata: dict[str, Any] | None = None,
) -> None:
    if model_predictions is not None and not model_predictions.empty:
        row = model_predictions.loc[df.index[idx]] if df.index[idx] in model_predictions.index else None
        if row is not None:
            model_pred = int(row.get("prediction", 0) or 0)
            p_buy = float(row.get("p_buy", 0.0) or 0.0)
            p_sell = float(row.get("p_sell", 0.0) or 0.0)
            min_prob = float(strategy.get("signal_policy", {}).get("min_probability", 0.0) or 0.0)
            min_edge = float(strategy.get("signal_policy", {}).get("min_edge", 0.0) or 0.0)
            model_prob = p_buy if prediction == BUY else p_sell
            opposite = p_sell if prediction == BUY else p_buy
            if model_pred not in (0, prediction):
                return
            if model_prob < min_prob or (model_prob - opposite) < min_edge:
                return
            confidence_hint = max(confidence_hint, model_prob)
            metadata = {**(metadata or {}), "model_prediction": model_pred, "p_buy": p_buy, "p_sell": p_sell}

    signals.append(build_signal(strategy, df, idx, prediction, reason, confidence_hint, metadata))


def detect_ema_cross_continuation(strategy: dict, df: pd.DataFrame, model_predictions: pd.DataFrame | None = None) -> list[StrategySignal]:
    signals: list[StrategySignal] = []
    for idx in range(55, len(df)):
        prev = df.iloc[idx - 1]
        row = df.iloc[idx]
        buy = prev["ema8"] <= prev["ema21"] and row["ema8"] > row["ema21"] and row["close"] > row["ema50"]
        sell = prev["ema8"] >= prev["ema21"] and row["ema8"] < row["ema21"] and row["close"] < row["ema50"]
        if buy and row["adx14"] >= 16:
            _append_if_model_allows(signals, strategy, df, idx, BUY, "ema8_cross_above_ema21_close_above_ema50", 0.56, model_predictions)
        elif sell and row["adx14"] >= 16:
            _append_if_model_allows(signals, strategy, df, idx, SELL, "ema8_cross_below_ema21_close_below_ema50", 0.56, model_predictions)
    return signals


def detect_trend_pullback_ema21(strategy: dict, df: pd.DataFrame, model_predictions: pd.DataFrame | None = None) -> list[StrategySignal]:
    signals: list[StrategySignal] = []
    for idx in range(60, len(df)):
        row = df.iloc[idx]
        trend_up = row["ema21"] > row["ema50"] and row["ema21_slope"] > 0
        trend_down = row["ema21"] < row["ema50"] and row["ema21_slope"] < 0
        touched_ema21 = row["low"] <= row["ema21"] <= row["high"]
        if trend_up and touched_ema21 and row["bullish"] and row["close"] > row["ema21"]:
            _append_if_model_allows(signals, strategy, df, idx, BUY, "trend_up_pullback_reclaimed_ema21", 0.58, model_predictions)
        elif trend_down and touched_ema21 and row["bearish"] and row["close"] < row["ema21"]:
            _append_if_model_allows(signals, strategy, df, idx, SELL, "trend_down_pullback_rejected_ema21", 0.58, model_predictions)
    return signals


def detect_inside_bar_breakout(strategy: dict, df: pd.DataFrame, model_predictions: pd.DataFrame | None = None) -> list[StrategySignal]:
    signals: list[StrategySignal] = []
    for idx in range(3, len(df)):
        mother = df.iloc[idx - 2]
        inside = df.iloc[idx - 1]
        row = df.iloc[idx]
        is_inside = inside["high"] <= mother["high"] and inside["low"] >= mother["low"]
        if not is_inside:
            continue
        if row["close"] > mother["high"]:
            _append_if_model_allows(signals, strategy, df, idx, BUY, "inside_bar_mother_high_breakout", 0.57, model_predictions)
        elif row["close"] < mother["low"]:
            _append_if_model_allows(signals, strategy, df, idx, SELL, "inside_bar_mother_low_breakout", 0.57, model_predictions)
    return signals


def detect_range_mean_reversion(strategy: dict, df: pd.DataFrame, model_predictions: pd.DataFrame | None = None) -> list[StrategySignal]:
    signals: list[StrategySignal] = []
    for idx in range(55, len(df)):
        row = df.iloc[idx]
        range_size = row["range_high20"] - row["range_low20"]
        if not np.isfinite(range_size) or range_size <= 0 or row["adx14"] > 18:
            continue
        near_low = row["low"] <= row["range_low20"] + 0.15 * range_size
        near_high = row["high"] >= row["range_high20"] - 0.15 * range_size
        if near_low and row["bullish"] and row["rsi14"] < 45:
            _append_if_model_allows(signals, strategy, df, idx, BUY, "range_low_bullish_rejection", 0.55, model_predictions)
        elif near_high and row["bearish"] and row["rsi14"] > 55:
            _append_if_model_allows(signals, strategy, df, idx, SELL, "range_high_bearish_rejection", 0.55, model_predictions)
    return signals


def detect_volatility_expansion_breakout(strategy: dict, df: pd.DataFrame, model_predictions: pd.DataFrame | None = None) -> list[StrategySignal]:
    signals: list[StrategySignal] = []
    for idx in range(90, len(df)):
        row = df.iloc[idx]
        was_compressed = float(df["atr_ratio"].iloc[idx - 5:idx].mean()) < 0.90
        expanding = row["atr_ratio"] > 1.02 and row["body_ratio"] > 0.65
        if not was_compressed or not expanding:
            continue
        if row["close"] > row["range_high20"]:
            _append_if_model_allows(signals, strategy, df, idx, BUY, "volatility_expansion_breakout_high20", 0.58, model_predictions)
        elif row["close"] < row["range_low20"]:
            _append_if_model_allows(signals, strategy, df, idx, SELL, "volatility_expansion_breakout_low20", 0.58, model_predictions)
    return signals


def detect_session_momentum_open(strategy: dict, df: pd.DataFrame, model_predictions: pd.DataFrame | None = None) -> list[StrategySignal]:
    signals: list[StrategySignal] = []
    liquid_hours = {7, 8, 9, 12, 13, 14, 15}
    for idx in range(30, len(df)):
        row = df.iloc[idx]
        if int(row["hour_utc"]) not in liquid_hours or row["body_ratio"] < 0.75:
            continue
        extension = abs(row["close"] - row["ema21"]) / (row["atr14"] + 1e-12)
        if extension > 1.2:
            continue
        if row["bullish"] and row["close"] > row["ema21"]:
            _append_if_model_allows(signals, strategy, df, idx, BUY, "liquid_session_bullish_momentum", 0.56, model_predictions)
        elif row["bearish"] and row["close"] < row["ema21"]:
            _append_if_model_allows(signals, strategy, df, idx, SELL, "liquid_session_bearish_momentum", 0.56, model_predictions)
    return signals


def detect_liquidity_sweep_reversal(strategy: dict, df: pd.DataFrame, model_predictions: pd.DataFrame | None = None) -> list[StrategySignal]:
    signals: list[StrategySignal] = []
    for idx in range(45, len(df)):
        row = df.iloc[idx]
        swept_low = row["low"] < row["range_low20"] and row["close"] > row["range_low20"] and row["bullish"]
        swept_high = row["high"] > row["range_high20"] and row["close"] < row["range_high20"] and row["bearish"]
        if swept_low:
            _append_if_model_allows(signals, strategy, df, idx, BUY, "sell_side_sweep_reclaim", 0.58, model_predictions)
        elif swept_high:
            _append_if_model_allows(signals, strategy, df, idx, SELL, "buy_side_sweep_reclaim", 0.58, model_predictions)
    return signals


def detect_daily_bias_intraday(strategy: dict, df: pd.DataFrame, model_predictions: pd.DataFrame | None = None) -> list[StrategySignal]:
    signals: list[StrategySignal] = []
    for idx in range(80, len(df)):
        row = df.iloc[idx]
        bias_buy = row["ema21"] > row["ema50"] > row["ema200"] and row["ema50_slope"] > 0
        bias_sell = row["ema21"] < row["ema50"] < row["ema200"] and row["ema50_slope"] < 0
        continuation_buy = row["low"] <= row["ema21"] and row["close"] > row["ema8"] and row["bullish"]
        continuation_sell = row["high"] >= row["ema21"] and row["close"] < row["ema8"] and row["bearish"]
        if bias_buy and continuation_buy:
            _append_if_model_allows(signals, strategy, df, idx, BUY, "daily_bias_buy_intraday_continuation", 0.59, model_predictions)
        elif bias_sell and continuation_sell:
            _append_if_model_allows(signals, strategy, df, idx, SELL, "daily_bias_sell_intraday_continuation", 0.59, model_predictions)
    return signals


def detect_support_resistance_bounce(strategy: dict, df: pd.DataFrame, model_predictions: pd.DataFrame | None = None) -> list[StrategySignal]:
    signals: list[StrategySignal] = []
    for idx in range(65, len(df)):
        row = df.iloc[idx]
        span50 = row["range_high50"] - row["range_low50"]
        if not np.isfinite(span50) or span50 <= 0:
            continue
        near_support = row["low"] <= row["range_low50"] + 0.12 * span50
        near_resistance = row["high"] >= row["range_high50"] - 0.12 * span50
        rejection_buy = near_support and row["lower_wick"] > row["body"] * 0.8 and row["bullish"]
        rejection_sell = near_resistance and row["upper_wick"] > row["body"] * 0.8 and row["bearish"]
        if rejection_buy:
            _append_if_model_allows(signals, strategy, df, idx, BUY, "support_rejection_bounce", 0.56, model_predictions)
        elif rejection_sell:
            _append_if_model_allows(signals, strategy, df, idx, SELL, "resistance_rejection_bounce", 0.56, model_predictions)
    return signals


def detect_gold_impulse_pullback(strategy: dict, df: pd.DataFrame, model_predictions: pd.DataFrame | None = None) -> list[StrategySignal]:
    signals: list[StrategySignal] = []
    for idx in range(35, len(df)):
        impulse = df.iloc[idx - 1]
        row = df.iloc[idx]
        if impulse["body_ratio"] < 1.15:
            continue
        impulse_mid = (impulse["open"] + impulse["close"]) / 2
        if impulse["bullish"]:
            pullback = row["low"] <= max(impulse_mid, row["ema21"]) and row["close"] > row["ema21"] and row["bullish"]
            if pullback:
                _append_if_model_allows(signals, strategy, df, idx, BUY, "gold_bullish_impulse_pullback", 0.60, model_predictions)
        elif impulse["bearish"]:
            pullback = row["high"] >= min(impulse_mid, row["ema21"]) and row["close"] < row["ema21"] and row["bearish"]
            if pullback:
                _append_if_model_allows(signals, strategy, df, idx, SELL, "gold_bearish_impulse_pullback", 0.60, model_predictions)
    return signals


DETECTORS: dict[str, Callable[[dict, pd.DataFrame, pd.DataFrame | None], list[StrategySignal]]] = {
    "ema_cross_continuation": detect_ema_cross_continuation,
    "trend_pullback_ema21": detect_trend_pullback_ema21,
    "inside_bar_breakout": detect_inside_bar_breakout,
    "range_mean_reversion": detect_range_mean_reversion,
    "volatility_expansion_breakout": detect_volatility_expansion_breakout,
    "session_momentum_open": detect_session_momentum_open,
    "liquidity_sweep_reversal": detect_liquidity_sweep_reversal,
    "daily_bias_intraday": detect_daily_bias_intraday,
    "support_resistance_bounce": detect_support_resistance_bounce,
    "gold_impulse_pullback": detect_gold_impulse_pullback,
}


def evaluate_strategy(strategy: dict, frame: pd.DataFrame, model_predictions: pd.DataFrame | None = None) -> list[StrategySignal]:
    detector = DETECTORS.get(strategy["id"])
    if detector is None:
        raise ValueError(f"No detector registered for strategy: {strategy['id']}")
    df = enrich_indicators(frame)
    if "timeframe" not in df.columns:
        df["timeframe"] = ",".join(strategy.get("timeframes", ()))
    return detector(strategy, df, model_predictions)


def evaluate_asset_bank(asset_bank: dict, frames_by_timeframe: dict[str, pd.DataFrame]) -> list[StrategySignal]:
    signals: list[StrategySignal] = []
    for strategy in asset_bank.get("strategies", []):
        for timeframe in strategy.get("timeframes", ()):
            frame = frames_by_timeframe.get(str(timeframe).upper())
            if frame is None or frame.empty:
                continue
            strategy_for_tf = dict(strategy)
            strategy_for_tf["timeframe"] = str(timeframe).upper()
            frame_for_tf = frame.copy()
            frame_for_tf["timeframe"] = str(timeframe).upper()
            signals.extend(evaluate_strategy(strategy_for_tf, frame_for_tf))
    return signals
