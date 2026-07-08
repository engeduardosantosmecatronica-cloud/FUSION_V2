from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

from .features import build_feature_matrix
from .market_context import extract_orderflow_context, extract_sr_context, extract_volatility_context
from .omnis_experts import build_omnis_expert_features


CANDLE_FEATURES = (
    "candle_range",
    "candle_body",
    "body_ratio",
    "upper_wick_ratio",
    "lower_wick_ratio",
    "candle_direction",
    "candle_strength",
    "close_position",
    "close_pos_signed",
    "range_norm",
    "body_norm",
    "impulse_3",
    "doji_score",
    "pinbar_score",
    "is_engulfing",
    "is_inside_bar",
    "vol_adj_impulse",
)


def _volume(df: pd.DataFrame) -> pd.Series:
    if "volume" in df.columns:
        return df["volume"]
    if "tick_volume" in df.columns:
        return df["tick_volume"]
    if "real_volume" in df.columns:
        return df["real_volume"]
    return pd.Series(1000.0, index=df.index)


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / (loss + 1e-12)
    return 100 - (100 / (1 + rs))


def extract_candle_execution_features(df: pd.DataFrame, lookback: int = 20) -> pd.DataFrame:
    result = df.copy()
    volume = _volume(result)
    candle_range = result["high"] - result["low"]
    safe_range = candle_range.replace(0, np.nan)
    body = (result["close"] - result["open"]).abs()
    upper_wick = result["high"] - pd.concat([result["open"], result["close"]], axis=1).max(axis=1)
    lower_wick = pd.concat([result["open"], result["close"]], axis=1).min(axis=1) - result["low"]
    result["candle_range"] = candle_range
    result["candle_body"] = body
    result["body_ratio"] = body / (safe_range + 1e-12)
    result["upper_wick_ratio"] = upper_wick / (safe_range + 1e-12)
    result["lower_wick_ratio"] = lower_wick / (safe_range + 1e-12)
    result["candle_direction"] = np.sign(result["close"] - result["open"])
    range_mean = candle_range.rolling(lookback, min_periods=1).mean().replace(0, np.nan)
    range_std = candle_range.rolling(lookback, min_periods=1).std().replace(0, np.nan)
    body_mean = body.rolling(lookback, min_periods=1).mean()
    body_std = body.rolling(lookback, min_periods=1).std().replace(0, np.nan)
    result["candle_strength"] = candle_range / (range_mean + 1e-12)
    result["close_position"] = (result["close"] - result["low"]) / (safe_range + 1e-12)
    result["close_pos_signed"] = result["close_position"] * result["candle_direction"]
    result["range_norm"] = (candle_range - range_mean) / (range_std + 1e-12)
    result["body_norm"] = (body - body_mean) / (body_std + 1e-12)
    result["impulse_3"] = (result["close"] - result["close"].shift(3)) / (result["close"].shift(3) + 1e-12)
    result["doji_score"] = 1 - result["body_ratio"]
    result["pinbar_score"] = np.where(
        result["candle_direction"] == 1,
        result["lower_wick_ratio"] - result["upper_wick_ratio"],
        result["upper_wick_ratio"] - result["lower_wick_ratio"],
    )
    prev_body = (result["close"].shift(1) - result["open"].shift(1)).abs()
    result["is_engulfing"] = (body > prev_body * 1.5).astype(int)
    result["is_inside_bar"] = ((result["high"] <= result["high"].shift(1)) & (result["low"] >= result["low"].shift(1))).astype(int)
    volume_factor = volume / (volume.rolling(lookback, min_periods=1).mean() + 1e-12)
    result["vol_adj_impulse"] = result["impulse_3"] * volume_factor
    return result.replace([np.inf, -np.inf], np.nan)


def calculate_rsi_divergence(df: pd.DataFrame, rsi_period: int = 14, lookback: int = 5) -> pd.Series:
    rsi = _rsi(df["close"], rsi_period)
    lookback_high = df["high"].rolling(lookback).max()
    lookback_low = df["low"].rolling(lookback).min()
    rsi_high = rsi.rolling(lookback).max()
    rsi_low = rsi.rolling(lookback).min()
    sell = (df["high"] > lookback_high.shift(1)) & (rsi < rsi_high.shift(1))
    buy = (df["low"] < lookback_low.shift(1)) & (rsi > rsi_low.shift(1))
    return pd.Series(np.select([sell, buy], [-1.0, 1.0], default=0.0), index=df.index, name="rsi_divergence")


def extract_reversal_execution_features(df: pd.DataFrame, lookback: int = 5) -> pd.DataFrame:
    result = df.copy()
    volume = _volume(result)
    result["rsi_divergence"] = calculate_rsi_divergence(result, lookback=lookback)
    vol_ma20 = volume.rolling(20).mean()
    vol_recent = volume.rolling(lookback).mean()
    volume_ratio = vol_recent / (vol_ma20 + 1e-12)
    price_direction = np.sign(result["close"].diff())
    result["volume_declining"] = np.select(
        [(price_direction > 0) & (volume_ratio < 0.8), (price_direction < 0) & (volume_ratio > 1.2)],
        [-1.0, 1.0],
        default=0.0,
    )
    if "ema_21_slope_norm" in result.columns:
        slope_change = result["ema_21_slope_norm"].diff()
        result["ema_velocity"] = -(slope_change / (slope_change.std() + 1e-12)).clip(-1, 1)
    else:
        result["ema_velocity"] = 0.0
    candle_size = result["high"] - result["low"]
    size_ratio = candle_size / (candle_size.rolling(3).mean() + 1e-12)
    result["candle_size_trend"] = np.select(
        [(price_direction > 0) & (size_ratio < 0.7), (price_direction < 0) & (size_ratio > 1.3)],
        [-1.0, 1.0],
        default=0.0,
    )
    range_ = result["high"] - result["low"]
    result["close_position_range"] = -(2 * ((result["close"] - result["low"]) / (range_ + 1e-12)) - 1)
    if "ema_21" in result.columns:
        above = (result["close"] > result["ema_21"]).astype(int)
        result["sequential_closes"] = -((2 * above.rolling(3).sum() / 3) - 1)
    else:
        result["sequential_closes"] = 0.0
    return result.replace([np.inf, -np.inf], np.nan)


def extract_operational_risk_features(df: pd.DataFrame, atr_col: str = "atr_short", spread_col: str = "spread") -> pd.DataFrame:
    result = df.copy()
    result["risk_support"] = result["dist_to_support"] / (result[atr_col] + 1e-12) if "dist_to_support" in result.columns and atr_col in result.columns else np.nan
    result["risk_resistance"] = result["dist_to_resistance"] / (result[atr_col] + 1e-12) if "dist_to_resistance" in result.columns and atr_col in result.columns else np.nan
    result["risk_sr_min"] = result[["risk_support", "risk_resistance"]].min(axis=1)
    result["risk_volatility"] = result[atr_col] / (result["atr_long"] + 1e-12) if atr_col in result.columns and "atr_long" in result.columns else 1.0
    result["risk_spread"] = result[spread_col] / (result[atr_col] + 1e-12) if spread_col in result.columns and atr_col in result.columns else 0.0
    result["risk_candle"] = result["candle_range"] / (result[atr_col] + 1e-12) if "candle_range" in result.columns and atr_col in result.columns else 1.0
    result["operational_risk_score"] = (
        0.35 * pd.Series(result["risk_sr_min"]).fillna(1).clip(0, 3)
        + 0.25 * pd.Series(result["risk_volatility"]).fillna(1).clip(0, 3)
        + 0.20 * pd.Series(result["risk_candle"]).fillna(1).clip(0, 3)
        + 0.20 * pd.Series(result["risk_spread"]).fillna(0).clip(0, 3)
    ).clip(0, 3) / 3
    result["operational_risk_regime"] = pd.cut(
        result["operational_risk_score"],
        bins=[-np.inf, 0.33, 0.66, np.inf],
        labels=[0, 1, 2],
    ).astype(int)
    return result


def run_execution_feature_pipeline(
    df: pd.DataFrame,
    include_alpha: bool = True,
    include_omnis: bool = True,
) -> pd.DataFrame:
    result = df.copy()
    if include_alpha:
        alpha = build_feature_matrix(result, include_raw_ohlcv=False)
        result = pd.concat([result, alpha], axis=1)
        result = result.loc[:, ~result.columns.duplicated()]
    if include_omnis:
        omnis = build_omnis_expert_features(result)
        result = pd.concat([result, omnis], axis=1)
        result = result.loc[:, ~result.columns.duplicated()]
    result = extract_volatility_context(result)
    result = extract_sr_context(result)
    result = extract_orderflow_context(result)
    result = extract_candle_execution_features(result)
    result = extract_reversal_execution_features(result)
    result = extract_operational_risk_features(result)
    numeric = result.select_dtypes(include=[np.number]).columns
    result[numeric] = result[numeric].replace([np.inf, -np.inf], np.nan).fillna(0.0).astype(np.float32)
    return result.dropna()


def _scalar(frame_or_dict: Any, key: str, default: float = 0.0) -> float:
    if isinstance(frame_or_dict, pd.DataFrame):
        if frame_or_dict.empty or key not in frame_or_dict.columns:
            return default
        value = frame_or_dict[key].iloc[-1]
    elif isinstance(frame_or_dict, dict):
        value = frame_or_dict.get(key, default)
        if isinstance(value, pd.Series):
            value = value.iloc[-1]
    else:
        return default
    return float(value) if value is not None and not pd.isna(value) else default


def m15_entry_filter(features_m15: dict[str, Any], action: str) -> dict[str, Any]:
    score = 0
    reasons: list[str] = []
    trend = features_m15.get("trend", features_m15)
    candles = features_m15.get("candles", features_m15)
    ema9 = _scalar(trend, "ema_9", _scalar(trend, "omnis_ema_9"))
    ema21 = _scalar(trend, "ema_21", _scalar(trend, "omnis_ema_21"))
    price_dist = _scalar(trend, "price_ema21_dist", _scalar(trend, "omnis_dist_ema_21"))
    slope_ema21 = _scalar(trend, "ema_21_slope_norm", _scalar(trend, "omnis_trend_slope_21"))
    trend_regime = _scalar(trend, "trend_regime", _scalar(trend, "omnis_trend_signal"))
    candle_strength = _scalar(candles, "candle_strength", _scalar(candles, "omnis_pattern_score"))

    if action == "BUY":
        checks = [
            (slope_ema21 > 0, 3, "EMA21 slope positivo"),
            (candle_strength > 0.5, 2, "Candle comprador forte"),
            (price_dist > 0, 2, "Preco acima da EMA21"),
            (ema9 > ema21, 1, "EMA9 acima da EMA21"),
            (trend_regime >= 0, 2, "Regime nao baixista"),
        ]
    elif action == "SELL":
        checks = [
            (slope_ema21 < 0, 3, "EMA21 slope negativo"),
            (candle_strength < -0.5, 2, "Candle vendedor forte"),
            (price_dist < 0, 2, "Preco abaixo da EMA21"),
            (ema9 < ema21, 1, "EMA9 abaixo da EMA21"),
            (trend_regime <= 0, 2, "Regime nao altista"),
        ]
    else:
        checks = []

    for ok, points, reason in checks:
        if ok:
            score += points
            reasons.append(reason)
    return {"allowed": score >= 7, "score": score, "reasons": reasons}


@dataclass
class FeatureCache:
    ttl_seconds: int = 60

    def __post_init__(self) -> None:
        self.cache: dict[str, dict[str, Any]] = {}
        self.hits = 0
        self.misses = 0

    def _key(self, symbol: str, timeframe: str) -> str:
        return f"{symbol}_{timeframe}"

    def get(self, symbol: str, timeframe: str) -> pd.DataFrame | None:
        key = self._key(symbol, timeframe)
        entry = self.cache.get(key)
        if entry and datetime.now() - entry["timestamp"] < timedelta(seconds=self.ttl_seconds):
            self.hits += 1
            return entry["data"].copy()
        self.misses += 1
        return None

    def set(self, symbol: str, timeframe: str, df: pd.DataFrame) -> None:
        self.cache[self._key(symbol, timeframe)] = {"data": df.copy(), "timestamp": datetime.now()}


feature_cache = FeatureCache()

