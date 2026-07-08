from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

from .dataset_builder import normalize_ohlcv_columns
from .extended_experts import build_extended_expert_features
from .omnis_experts import build_omnis_expert_features


TargetBuilder = Callable[[pd.DataFrame, int, float], pd.Series]


@dataclass(frozen=True)
class ExpertTrainingSpec:
    name: str
    target_column: str
    feature_prefixes: tuple[str, ...]
    horizon: int = 10
    threshold: float = 0.001
    objective: str = "multiclass"
    classes: tuple[int, ...] = (-1, 0, 1)
    target_builder: TargetBuilder | None = None
    model_params: dict[str, Any] | None = None


def future_return(df: pd.DataFrame, horizon: int) -> pd.Series:
    return (df["close"].shift(-horizon) - df["close"]) / (df["close"] + 1e-12)


def trend_target(df: pd.DataFrame, horizon: int = 10, threshold: float = 0.001) -> pd.Series:
    ret = future_return(df, horizon)
    target = np.where(ret > threshold, 1, np.where(ret < -threshold, -1, 0))
    return pd.Series(target, index=df.index, name="trend_target", dtype=int)


def volatility_target(
    df: pd.DataFrame,
    horizon: int = 10,
    threshold: float = 0.001,
    low: float = 0.003,
    high: float = 0.01,
) -> pd.Series:
    move = future_return(df, horizon).abs()
    target = pd.Series(1, index=df.index, name="volatility_target", dtype=int)
    target.loc[move < low] = 0
    target.loc[move > high] = 2
    return target


def candle_pattern_target(df: pd.DataFrame, horizon: int = 5, threshold: float = 0.001) -> pd.Series:
    ret = future_return(df, horizon)
    target = pd.Series(0, index=df.index, name="candles_target", dtype=int)
    bullish = [
        "omnis_hammer",
        "omnis_bullish_engulfing",
        "omnis_morning_star",
        "omnis_piercing_line",
    ]
    bearish = [
        "omnis_shooting_star",
        "omnis_bearish_engulfing",
        "omnis_evening_star",
        "omnis_dark_cloud",
    ]
    for col in bullish:
        if col in df.columns:
            target.loc[(df[col] == 1) & (ret > threshold)] = 1
    for col in bearish:
        if col in df.columns:
            target.loc[(df[col] == 1) & (ret < -threshold)] = -1
    return target


def orderflow_target(df: pd.DataFrame, horizon: int = 10, threshold: float = 0.001) -> pd.Series:
    if "omnis_cumulative_delta" in df.columns:
        delta = df["omnis_cumulative_delta"].diff(horizon)
    elif "omnis_candle_delta" in df.columns:
        delta = df["omnis_candle_delta"].rolling(horizon).sum()
    else:
        delta = df["close"].diff(horizon)
    delta_std = delta.rolling(50).std()
    target = np.where(delta > delta_std, 1, np.where(delta < -delta_std, -1, 0))
    return pd.Series(target, index=df.index, name="orderflow_target", dtype=int)


def pullback_target(df: pd.DataFrame, horizon: int = 5, threshold: float = 0.001) -> pd.Series:
    ret = future_return(df, horizon)
    target = pd.Series(0, index=df.index, name="pullback_target", dtype=int)
    if "omnis_pullback_buy" in df.columns:
        target.loc[(df["omnis_pullback_buy"] == 1) & (ret > threshold)] = 1
    if "omnis_pullback_sell" in df.columns:
        target.loc[(df["omnis_pullback_sell"] == 1) & (ret < -threshold)] = -1
    return target


def quant_target(df: pd.DataFrame, horizon: int = 10, threshold: float = 0.001) -> pd.Series:
    ret = future_return(df, horizon)
    target = pd.Series(0, index=df.index, name="quant_target", dtype=int)
    zscore = df.get("omnis_stat_zscore")
    percentile = df.get("omnis_stat_percentile")
    hourly_bias = df.get("omnis_hourly_mean_bias")
    if zscore is not None:
        target.loc[(zscore > 1) & (ret < -threshold)] = -1
        target.loc[(zscore < -1) & (ret > threshold)] = 1
    if percentile is not None:
        target.loc[(percentile > 0.9) & (ret < -threshold)] = -1
        target.loc[(percentile < 0.1) & (ret > threshold)] = 1
    if hourly_bias is not None:
        target.loc[(hourly_bias > threshold) & (ret < -threshold)] = -1
        target.loc[(hourly_bias < -threshold) & (ret > threshold)] = 1
    return target


def reversal_target(df: pd.DataFrame, horizon: int = 10, threshold: float = 0.001) -> pd.Series:
    ret = future_return(df, horizon)
    exhaustion = df.get("omnis_exhaustion_signal", pd.Series(0, index=df.index))
    divergence = df.get("omnis_bullish_divergence", 0) - df.get("omnis_bearish_divergence", 0)
    setup = (exhaustion.abs() > 0.5) | (pd.Series(divergence, index=df.index).abs() > 0)
    target = (setup & (np.sign(exhaustion + divergence) == np.sign(ret)) & (ret.abs() > threshold)).astype(int)
    return pd.Series(target, index=df.index, name="reversal_target", dtype=int)


def risk_target(df: pd.DataFrame, horizon: int = 10, threshold: float = 0.001) -> pd.Series:
    ret = future_return(df, horizon)
    drawdown = df.get("omnis_drawdown", pd.Series(0, index=df.index))
    volatility = df.get("omnis_volatility", pd.Series(0, index=df.index))
    sharpe = df.get("omnis_sharpe_20", pd.Series(1, index=df.index))
    high_risk = (drawdown < -0.05) | (volatility > volatility.rolling(100).quantile(0.8)) | (sharpe < 0)
    failed_forward = ret.abs() < threshold
    return pd.Series((high_risk | failed_forward).astype(int), index=df.index, name="risk_target", dtype=int)


def support_resistance_target(df: pd.DataFrame, horizon: int = 10, threshold: float = 0.001) -> pd.Series:
    ret = future_return(df, horizon)
    at_support = df.get("omnis_at_support", pd.Series(0, index=df.index))
    at_resistance = df.get("omnis_at_resistance", pd.Series(0, index=df.index))
    target = pd.Series(0, index=df.index, name="sr_target", dtype=int)
    target.loc[(at_support == 1) & (ret > threshold)] = 1
    target.loc[(at_resistance == 1) & (ret < -threshold)] = -1
    return target


def _safe_div(numerator: pd.Series, denominator: pd.Series | float, eps: float = 1e-12) -> pd.Series:
    return numerator / (denominator + eps)


def _true_range(data: pd.DataFrame) -> pd.Series:
    prev_close = data["close"].shift(1)
    return pd.concat(
        [
            data["high"] - data["low"],
            (data["high"] - prev_close).abs(),
            (data["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)


def _rolling_atr(data: pd.DataFrame, window: int = 14) -> pd.Series:
    return _true_range(data).rolling(window, min_periods=1).mean()


def _volume_series(data: pd.DataFrame) -> pd.Series:
    for col in ("tick_volume", "real_volume", "volume"):
        if col in data.columns:
            return pd.to_numeric(data[col], errors="coerce").fillna(0.0)
    return pd.Series(0.0, index=data.index)


def build_fusion_layer_features(
    data: pd.DataFrame,
    omnis: pd.DataFrame,
    extended: pd.DataFrame,
) -> pd.DataFrame:
    """Feature layers inspired by the new root experts, adapted to historical bars."""
    open_ = data["open"].astype(float)
    high = data["high"].astype(float)
    low = data["low"].astype(float)
    close = data["close"].astype(float)
    volume = _volume_series(data)
    atr = _rolling_atr(data, 14)
    candle_range = (high - low).replace(0, np.nan).ffill().fillna(0.0)
    body = close - open_
    abs_body = body.abs()
    upper_shadow = high - pd.concat([open_, close], axis=1).max(axis=1)
    lower_shadow = pd.concat([open_, close], axis=1).min(axis=1) - low
    ema_fast = close.ewm(span=21, adjust=False).mean()
    ema_slow = close.ewm(span=50, adjust=False).mean()
    ema_long = close.ewm(span=200, adjust=False).mean()
    rolling_high = high.rolling(20, min_periods=2).max().shift(1)
    rolling_low = low.rolling(20, min_periods=2).min().shift(1)
    rolling_mid = (rolling_high + rolling_low) / 2
    range_20 = high.rolling(20, min_periods=2).max() - low.rolling(20, min_periods=2).min()
    range_100 = high.rolling(100, min_periods=10).max() - low.rolling(100, min_periods=10).min()
    dist_support = _safe_div(close - rolling_low, atr)
    dist_resistance = _safe_div(rolling_high - close, atr)
    breakout_up = (close > rolling_high).astype(int)
    breakout_down = (close < rolling_low).astype(int)
    trend_direction = np.sign(ema_fast - ema_slow)
    trend_strength = _safe_div((ema_fast - ema_slow).abs(), atr).clip(0, 5) / 5
    compression = _safe_div(range_20, range_100).clip(0, 3)
    rejection_buy = ((lower_shadow > abs_body * 1.5) & (close > open_)).astype(int)
    rejection_sell = ((upper_shadow > abs_body * 1.5) & (close < open_)).astype(int)
    volume_z = _safe_div(volume - volume.rolling(50, min_periods=5).mean(), volume.rolling(50, min_periods=5).std()).fillna(0.0)
    spread_source = pd.to_numeric(data["spread"], errors="coerce") if "spread" in data.columns else pd.Series(0.0, index=data.index)
    spread_proxy = np.where(spread_source > 0, spread_source, _safe_div(candle_range, atr).clip(0, 5))

    out = pd.DataFrame(index=data.index)
    out["fusion_phase_trend_direction"] = trend_direction
    out["fusion_phase_trend_strength"] = trend_strength
    out["fusion_phase_breakout_up"] = breakout_up
    out["fusion_phase_breakout_down"] = breakout_down
    out["fusion_phase_range_compression"] = compression
    out["fusion_phase_pullback_buy"] = ((trend_direction > 0) & (close <= ema_fast) & (close > ema_slow)).astype(int)
    out["fusion_phase_pullback_sell"] = ((trend_direction < 0) & (close >= ema_fast) & (close < ema_slow)).astype(int)
    out["fusion_phase_above_long_ema"] = (close > ema_long).astype(int)
    out["fusion_session_hour"] = data.index.hour if isinstance(data.index, pd.DatetimeIndex) else 0
    out["fusion_session_asia"] = out["fusion_session_hour"].between(0, 6).astype(int)
    out["fusion_session_london"] = out["fusion_session_hour"].between(7, 12).astype(int)
    out["fusion_session_ny"] = out["fusion_session_hour"].between(13, 20).astype(int)
    out["fusion_session_overlap"] = out["fusion_session_hour"].between(12, 16).astype(int)
    out["fusion_session_activity"] = (_safe_div(atr, close).rolling(20, min_periods=3).mean() * 10000).fillna(0.0)
    out["fusion_spread_value"] = pd.Series(spread_proxy, index=data.index).fillna(0.0)
    out["fusion_spread_range_ratio"] = _safe_div(pd.Series(spread_proxy, index=data.index), candle_range).clip(0, 5).fillna(0.0)
    out["fusion_spread_volatility_ratio"] = _safe_div(pd.Series(spread_proxy, index=data.index), atr).clip(0, 5).fillna(0.0)
    out["fusion_signal_zone_buy_rejection"] = rejection_buy
    out["fusion_signal_zone_sell_rejection"] = rejection_sell
    out["fusion_signal_zone_breakout_buy"] = breakout_up
    out["fusion_signal_zone_breakout_sell"] = breakout_down
    out["fusion_signal_zone_body_ratio"] = _safe_div(abs_body, candle_range).clip(0, 1).fillna(0.0)
    out["fusion_signal_zone_confluence_buy"] = (
        rejection_buy + breakout_up + out["fusion_phase_pullback_buy"] + (dist_support <= 1.5).astype(int)
    )
    out["fusion_signal_zone_confluence_sell"] = (
        rejection_sell + breakout_down + out["fusion_phase_pullback_sell"] + (dist_resistance <= 1.5).astype(int)
    )
    out["fusion_sr_support"] = rolling_low
    out["fusion_sr_resistance"] = rolling_high
    out["fusion_sr_mid"] = rolling_mid
    out["fusion_sr_dist_support_atr"] = dist_support
    out["fusion_sr_dist_resistance_atr"] = dist_resistance
    out["fusion_sr_at_support"] = (dist_support <= 1.0).astype(int)
    out["fusion_sr_at_resistance"] = (dist_resistance <= 1.0).astype(int)
    out["fusion_liquidity_sweep_low"] = ((low < rolling_low) & (close > rolling_low)).astype(int)
    out["fusion_liquidity_sweep_high"] = ((high > rolling_high) & (close < rolling_high)).astype(int)
    out["fusion_liquidity_volume_z"] = volume_z
    out["fusion_target_room_buy_atr"] = dist_resistance.clip(lower=0, upper=20)
    out["fusion_target_room_sell_atr"] = dist_support.clip(lower=0, upper=20)
    out["fusion_target_room_buy_clear"] = (out["fusion_target_room_buy_atr"] >= 2.0).astype(int)
    out["fusion_target_room_sell_clear"] = (out["fusion_target_room_sell_atr"] >= 2.0).astype(int)
    out["fusion_target_room_balance"] = out["fusion_target_room_buy_atr"] - out["fusion_target_room_sell_atr"]

    for source in (omnis, extended):
        numeric = source.select_dtypes(include=[np.number])
        if not numeric.empty:
            out = out.join(numeric, how="left", rsuffix="_dup")
    return out.replace([np.inf, -np.inf], np.nan).fillna(0.0)


def market_phase_target(df: pd.DataFrame, horizon: int = 10, threshold: float = 0.001) -> pd.Series:
    ret = future_return(df, horizon)
    buy_setup = (
        (df.get("fusion_phase_trend_direction", 0) > 0)
        & ((df.get("fusion_phase_breakout_up", 0) == 1) | (df.get("fusion_phase_pullback_buy", 0) == 1))
    )
    sell_setup = (
        (df.get("fusion_phase_trend_direction", 0) < 0)
        & ((df.get("fusion_phase_breakout_down", 0) == 1) | (df.get("fusion_phase_pullback_sell", 0) == 1))
    )
    target = pd.Series(0, index=df.index, name="market_phase_target", dtype=int)
    target.loc[buy_setup & (ret > threshold)] = 1
    target.loc[sell_setup & (ret < -threshold)] = -1
    return target


def session_target(df: pd.DataFrame, horizon: int = 10, threshold: float = 0.001) -> pd.Series:
    move = future_return(df, horizon).abs()
    activity = df.get("fusion_session_activity", pd.Series(0, index=df.index))
    poor_session = (df.get("fusion_session_asia", 0) == 1) & (activity < activity.rolling(100).quantile(0.4))
    high_opportunity = (df.get("fusion_session_overlap", 0) == 1) & (move > threshold)
    target = pd.Series(1, index=df.index, name="session_target", dtype=int)
    target.loc[poor_session | (move < threshold * 0.5)] = 0
    target.loc[high_opportunity | (move > threshold * 2)] = 2
    return target


def spread_target(df: pd.DataFrame, horizon: int = 5, threshold: float = 0.001) -> pd.Series:
    move = future_return(df, horizon).abs()
    spread_ratio = df.get("fusion_spread_volatility_ratio", pd.Series(0, index=df.index))
    bad_cost = (spread_ratio > spread_ratio.rolling(100).quantile(0.8)) | (move < threshold * 0.5)
    return pd.Series(bad_cost.astype(int), index=df.index, name="spread_target", dtype=int)


def signal_zone_target(df: pd.DataFrame, horizon: int = 5, threshold: float = 0.001) -> pd.Series:
    ret = future_return(df, horizon)
    buy_score = df.get("fusion_signal_zone_confluence_buy", pd.Series(0, index=df.index))
    sell_score = df.get("fusion_signal_zone_confluence_sell", pd.Series(0, index=df.index))
    target = pd.Series(0, index=df.index, name="signal_zone_target", dtype=int)
    target.loc[(buy_score >= 2) & (ret > threshold)] = 1
    target.loc[(sell_score >= 2) & (ret < -threshold)] = -1
    return target


def sr_liquidity_target(df: pd.DataFrame, horizon: int = 10, threshold: float = 0.001) -> pd.Series:
    ret = future_return(df, horizon)
    support_bounce = (df.get("fusion_sr_at_support", 0) == 1) | (df.get("fusion_liquidity_sweep_low", 0) == 1)
    resistance_reject = (df.get("fusion_sr_at_resistance", 0) == 1) | (df.get("fusion_liquidity_sweep_high", 0) == 1)
    target = pd.Series(0, index=df.index, name="sr_liquidity_target", dtype=int)
    target.loc[support_bounce & (ret > threshold)] = 1
    target.loc[resistance_reject & (ret < -threshold)] = -1
    return target


def target_room_target(df: pd.DataFrame, horizon: int = 10, threshold: float = 0.001) -> pd.Series:
    ret = future_return(df, horizon)
    target = pd.Series(0, index=df.index, name="target_room_target", dtype=int)
    buy_room = df.get("fusion_target_room_buy_atr", pd.Series(0, index=df.index))
    sell_room = df.get("fusion_target_room_sell_atr", pd.Series(0, index=df.index))
    target.loc[(buy_room >= 2) & (ret > threshold)] = 1
    target.loc[(sell_room >= 2) & (ret < -threshold)] = -1
    return target


LIGHTGBM_EXPERT_PARAMS: dict[str, Any] = {
    "n_estimators": 500,
    "learning_rate": 0.05,
    "max_depth": 6,
    "num_leaves": 31,
    "min_child_samples": 20,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "class_weight": "balanced",
    "random_state": 42,
    "n_jobs": -1,
    "verbose": -1,
}


EXPERT_SPECS: dict[str, ExpertTrainingSpec] = {
    "trend": ExpertTrainingSpec(
        name="trend",
        target_column="trend_target",
        feature_prefixes=("omnis_ema_", "omnis_dist_ema_", "omnis_plus_di", "omnis_minus_di", "omnis_adx", "omnis_rsi", "omnis_macd", "omnis_trend_"),
        horizon=10,
        target_builder=trend_target,
        model_params={**LIGHTGBM_EXPERT_PARAMS, "max_depth": 7, "class_weight": {-1: 1.5, 0: 1.5, 1: 1.0}},
    ),
    "volatility": ExpertTrainingSpec(
        name="volatility",
        target_column="volatility_target",
        feature_prefixes=("omnis_atr_", "omnis_bb_", "omnis_kc_", "omnis_squeeze", "omnis_vol_"),
        horizon=10,
        classes=(0, 1, 2),
        target_builder=volatility_target,
        model_params=LIGHTGBM_EXPERT_PARAMS,
    ),
    "candles": ExpertTrainingSpec(
        name="candles",
        target_column="candles_target",
        feature_prefixes=("omnis_body", "omnis_upper_shadow", "omnis_lower_shadow", "omnis_hammer", "omnis_shooting", "omnis_bullish", "omnis_bearish", "omnis_morning", "omnis_evening", "omnis_piercing", "omnis_dark", "omnis_inside", "omnis_outside", "omnis_doji", "omnis_spinning", "omnis_pattern"),
        horizon=5,
        target_builder=candle_pattern_target,
        model_params=LIGHTGBM_EXPERT_PARAMS,
    ),
    "orderflow": ExpertTrainingSpec(
        name="orderflow",
        target_column="orderflow_target",
        feature_prefixes=("omnis_candle_delta", "omnis_cumulative_delta", "omnis_delta", "omnis_volume", "omnis_vwap", "omnis_dist_vwap", "omnis_aggression", "omnis_buy_aggression", "omnis_sell_aggression", "omnis_flow"),
        horizon=10,
        target_builder=orderflow_target,
        model_params=LIGHTGBM_EXPERT_PARAMS,
    ),
    "pullback": ExpertTrainingSpec(
        name="pullback",
        target_column="pullback_target",
        feature_prefixes=("omnis_pb_", "omnis_keltner", "omnis_pullback", "omnis_fib_"),
        horizon=5,
        target_builder=pullback_target,
        model_params=LIGHTGBM_EXPERT_PARAMS,
    ),
    "quant": ExpertTrainingSpec(
        name="quant",
        target_column="quant_target",
        feature_prefixes=("omnis_stat_", "omnis_return_zscore", "omnis_trend_probability", "omnis_hourly_"),
        horizon=10,
        target_builder=quant_target,
        model_params=LIGHTGBM_EXPERT_PARAMS,
    ),
    "reversal": ExpertTrainingSpec(
        name="reversal",
        target_column="reversal_target",
        feature_prefixes=("omnis_exh_", "omnis_over", "omnis_bullish_divergence", "omnis_bearish_divergence", "omnis_gap", "omnis_extreme", "omnis_exhaustion"),
        horizon=10,
        objective="binary",
        classes=(0, 1),
        target_builder=reversal_target,
        model_params=LIGHTGBM_EXPERT_PARAMS,
    ),
    "risk": ExpertTrainingSpec(
        name="risk",
        target_column="risk_target",
        feature_prefixes=("omnis_returns", "omnis_volatility", "omnis_var_", "omnis_cvar", "omnis_drawdown", "omnis_max_drawdown", "omnis_sharpe", "omnis_sortino", "omnis_calmar", "omnis_mae", "omnis_mfe", "omnis_efficiency", "omnis_win_rate", "omnis_expectancy", "omnis_kelly", "omnis_suggested_position", "omnis_risk"),
        horizon=10,
        objective="binary",
        classes=(0, 1),
        target_builder=risk_target,
        model_params=LIGHTGBM_EXPERT_PARAMS,
    ),
    "sr": ExpertTrainingSpec(
        name="sr",
        target_column="sr_target",
        feature_prefixes=("omnis_pivot", "omnis_support", "omnis_resistance", "omnis_dist_support", "omnis_dist_resistance", "omnis_price_position", "omnis_at_support", "omnis_at_resistance", "omnis_volume_weighted_price", "omnis_dist_vwap_zone", "omnis_zone"),
        horizon=10,
        target_builder=support_resistance_target,
        model_params=LIGHTGBM_EXPERT_PARAMS,
    ),
    "market_phase": ExpertTrainingSpec(
        name="market_phase",
        target_column="market_phase_target",
        feature_prefixes=("fusion_phase_", "omnis_trend_", "omnis_adx", "omnis_plus_di", "omnis_minus_di", "ext_mom_", "ext_qnt_momentum"),
        horizon=10,
        target_builder=market_phase_target,
        model_params={**LIGHTGBM_EXPERT_PARAMS, "max_depth": 7},
    ),
    "session": ExpertTrainingSpec(
        name="session",
        target_column="session_target",
        feature_prefixes=("fusion_session_", "fusion_spread_", "ext_season_", "ext_qnt_volatility"),
        horizon=10,
        classes=(0, 1, 2),
        target_builder=session_target,
        model_params=LIGHTGBM_EXPERT_PARAMS,
    ),
    "spread": ExpertTrainingSpec(
        name="spread",
        target_column="spread_target",
        feature_prefixes=("fusion_spread_", "fusion_session_activity", "omnis_atr_", "omnis_vol_", "ext_vol_"),
        horizon=5,
        objective="binary",
        classes=(0, 1),
        target_builder=spread_target,
        model_params=LIGHTGBM_EXPERT_PARAMS,
    ),
    "signal_zone": ExpertTrainingSpec(
        name="signal_zone",
        target_column="signal_zone_target",
        feature_prefixes=("fusion_signal_zone_", "fusion_phase_", "fusion_sr_", "omnis_body", "omnis_upper_shadow", "omnis_lower_shadow", "omnis_hammer", "omnis_shooting", "omnis_bullish", "omnis_bearish", "ext_candle_", "ext_swing_"),
        horizon=5,
        target_builder=signal_zone_target,
        model_params=LIGHTGBM_EXPERT_PARAMS,
    ),
    "sr_liquidity": ExpertTrainingSpec(
        name="sr_liquidity",
        target_column="sr_liquidity_target",
        feature_prefixes=("fusion_sr_", "fusion_liquidity_", "omnis_support", "omnis_resistance", "omnis_dist_support", "omnis_dist_resistance", "omnis_at_support", "omnis_at_resistance", "ext_swing_", "ext_volume_node_", "ext_micro_"),
        horizon=10,
        target_builder=sr_liquidity_target,
        model_params=LIGHTGBM_EXPERT_PARAMS,
    ),
    "target_room": ExpertTrainingSpec(
        name="target_room",
        target_column="target_room_target",
        feature_prefixes=("fusion_target_room_", "fusion_sr_", "omnis_dist_support", "omnis_dist_resistance", "ext_fib_", "ext_ichi_"),
        horizon=10,
        target_builder=target_room_target,
        model_params=LIGHTGBM_EXPERT_PARAMS,
    ),
    "fibonacci": ExpertTrainingSpec(
        name="fibonacci",
        target_column="trend_target",
        feature_prefixes=("ext_fib_", "fusion_sr_", "fusion_target_room_"),
        horizon=10,
        target_builder=trend_target,
        model_params=LIGHTGBM_EXPERT_PARAMS,
    ),
    "ichimoku": ExpertTrainingSpec(
        name="ichimoku",
        target_column="trend_target",
        feature_prefixes=("ext_ichi_", "fusion_phase_", "omnis_trend_"),
        horizon=10,
        target_builder=trend_target,
        model_params=LIGHTGBM_EXPERT_PARAMS,
    ),
    "volume_structure": ExpertTrainingSpec(
        name="volume_structure",
        target_column="orderflow_target",
        feature_prefixes=("ext_volume_", "ext_obv", "ext_hvn", "ext_lvn", "omnis_volume", "omnis_flow"),
        horizon=10,
        target_builder=orderflow_target,
        model_params=LIGHTGBM_EXPERT_PARAMS,
    ),
    "gap_structure": ExpertTrainingSpec(
        name="gap_structure",
        target_column="reversal_target",
        feature_prefixes=("ext_gap_", "omnis_gap", "fusion_phase_", "fusion_signal_zone_"),
        horizon=10,
        target_builder=reversal_target,
        objective="binary",
        classes=(0, 1),
        model_params=LIGHTGBM_EXPERT_PARAMS,
    ),
    "stochastic": ExpertTrainingSpec(
        name="stochastic",
        target_column="reversal_target",
        feature_prefixes=("ext_stoch_", "omnis_over", "omnis_exh_"),
        horizon=10,
        target_builder=reversal_target,
        objective="binary",
        classes=(0, 1),
        model_params=LIGHTGBM_EXPERT_PARAMS,
    ),
    "momentum_accel": ExpertTrainingSpec(
        name="momentum_accel",
        target_column="trend_target",
        feature_prefixes=("ext_momentum", "ext_acceleration", "fusion_phase_", "omnis_macd"),
        horizon=10,
        target_builder=trend_target,
        model_params=LIGHTGBM_EXPERT_PARAMS,
    ),
    "microstructure": ExpertTrainingSpec(
        name="microstructure",
        target_column="orderflow_target",
        feature_prefixes=("ext_ms_", "ext_micro_", "ext_spread", "ext_tick_volume", "fusion_spread_", "omnis_candle_delta", "omnis_volume"),
        horizon=10,
        target_builder=orderflow_target,
        model_params=LIGHTGBM_EXPERT_PARAMS,
    ),
    "advanced_volatility": ExpertTrainingSpec(
        name="advanced_volatility",
        target_column="volatility_target",
        feature_prefixes=("ext_adv_", "omnis_atr_", "omnis_bb_", "omnis_kc_", "fusion_session_activity"),
        horizon=10,
        classes=(0, 1, 2),
        target_builder=volatility_target,
        model_params=LIGHTGBM_EXPERT_PARAMS,
    ),
    "anomaly_regime": ExpertTrainingSpec(
        name="anomaly_regime",
        target_column="risk_target",
        feature_prefixes=("ext_ml_", "ext_qnt_", "fusion_phase_", "omnis_volatility", "omnis_drawdown"),
        horizon=10,
        target_builder=risk_target,
        objective="binary",
        classes=(0, 1),
        model_params=LIGHTGBM_EXPERT_PARAMS,
    ),
    "exhaustion": ExpertTrainingSpec(
        name="exhaustion",
        target_column="reversal_target",
        feature_prefixes=("ext_exh_", "omnis_exh_", "omnis_over", "omnis_bullish_divergence", "omnis_bearish_divergence"),
        horizon=10,
        target_builder=reversal_target,
        objective="binary",
        classes=(0, 1),
        model_params=LIGHTGBM_EXPERT_PARAMS,
    ),
    "quant_regime": ExpertTrainingSpec(
        name="quant_regime",
        target_column="quant_target",
        feature_prefixes=("ext_qnt_", "omnis_stat_", "omnis_return_zscore", "omnis_hourly_"),
        horizon=10,
        target_builder=quant_target,
        model_params=LIGHTGBM_EXPERT_PARAMS,
    ),
}


DEFAULT_EXPERT_ORDER: tuple[str, ...] = (
    "volatility",
    "trend",
    "market_phase",
    "session",
    "spread",
    "orderflow",
    "sr",
    "sr_liquidity",
    "signal_zone",
    "target_room",
    "fibonacci",
    "ichimoku",
    "volume_structure",
    "gap_structure",
    "stochastic",
    "momentum_accel",
    "microstructure",
    "advanced_volatility",
    "anomaly_regime",
    "exhaustion",
    "quant_regime",
    "risk",
    "reversal",
    "candles",
    "pullback",
    "quant",
)


def select_expert_feature_columns(df: pd.DataFrame, spec: ExpertTrainingSpec) -> list[str]:
    columns = [
        col
        for col in df.columns
        if any(str(col).startswith(prefix) for prefix in spec.feature_prefixes)
        and pd.api.types.is_numeric_dtype(df[col])
    ]
    return list(dict.fromkeys(columns))


def build_expert_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    data = normalize_ohlcv_columns(df)
    omnis = build_omnis_expert_features(data)
    extended = build_extended_expert_features(data)
    fusion_layers = build_fusion_layer_features(data, omnis, extended)
    merged = pd.concat([data[["open", "high", "low", "close"]], fusion_layers], axis=1)
    return merged.loc[:, ~merged.columns.duplicated()]


def build_expert_dataset_from_feature_frame(
    merged: pd.DataFrame,
    expert_name: str,
    min_features: int = 5,
) -> pd.DataFrame:
    if expert_name not in EXPERT_SPECS:
        raise KeyError(f"Expert desconhecido: {expert_name}")
    spec = EXPERT_SPECS[expert_name]
    target = spec.target_builder(merged, spec.horizon, spec.threshold) if spec.target_builder else trend_target(merged)
    feature_cols = select_expert_feature_columns(merged, spec)
    if len(feature_cols) < min_features:
        raise ValueError(f"Features insuficientes para {expert_name}: {len(feature_cols)}")
    dataset = pd.concat([merged[feature_cols], target.rename(spec.target_column)], axis=1)
    return dataset.replace([np.inf, -np.inf], np.nan).dropna()


def build_expert_dataset(
    df: pd.DataFrame,
    expert_name: str,
    min_features: int = 5,
) -> pd.DataFrame:
    merged = build_expert_feature_frame(df)
    return build_expert_dataset_from_feature_frame(merged, expert_name, min_features=min_features)


def build_all_expert_datasets(
    df: pd.DataFrame,
    expert_names: tuple[str, ...] = DEFAULT_EXPERT_ORDER,
) -> dict[str, pd.DataFrame]:
    merged = build_expert_feature_frame(df)
    return {name: build_expert_dataset_from_feature_frame(merged, name) for name in expert_names}


def train_lightgbm_expert(
    dataset: pd.DataFrame,
    expert_name: str,
    test_size: float = 0.2,
) -> dict[str, Any]:
    """Train one specialist model. Imports ML dependencies only when called."""
    import lightgbm as lgb
    from sklearn.metrics import accuracy_score, f1_score
    from sklearn.model_selection import train_test_split

    spec = EXPERT_SPECS[expert_name]
    X = dataset.drop(columns=[spec.target_column])
    y = dataset[spec.target_column].astype(int)
    stratify = y if y.nunique() > 1 and y.value_counts().min() >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=42,
        stratify=stratify,
    )
    params = dict(spec.model_params or LIGHTGBM_EXPERT_PARAMS)
    if spec.objective == "binary":
        params["objective"] = "binary"
    else:
        params["objective"] = "multiclass"
        params["num_class"] = len(spec.classes)
    model = lgb.LGBMClassifier(**params)
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    return {
        "model": model,
        "expert": expert_name,
        "feature_columns": X.columns.tolist(),
        "metrics": {
            "accuracy": float(accuracy_score(y_test, pred)),
            "f1_macro": float(f1_score(y_test, pred, average="macro")),
            "train_samples": int(len(X_train)),
            "test_samples": int(len(X_test)),
            "features": int(X.shape[1]),
        },
    }


def create_binary_future_target(df: pd.DataFrame, forward_periods: int = 5, threshold: float = 0.001) -> pd.Series:
    future = df["close"].shift(-forward_periods) / (df["close"] + 1e-12) - 1
    return pd.Series((future > threshold).astype(int), index=df.index, name="target").fillna(0)


def legacy_candidate_model_factories(random_state: int = 42) -> dict[str, Any]:
    """Candidate classifiers preserved from OMNIS_Copia trainer."""
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
    from sklearn.linear_model import LogisticRegression

    factories: dict[str, Any] = {
        "random_forest": lambda: RandomForestClassifier(n_estimators=100, max_depth=10, random_state=random_state, n_jobs=-1),
        "gradient_boosting": lambda: GradientBoostingClassifier(n_estimators=100, max_depth=5, random_state=random_state),
        "logistic": lambda: LogisticRegression(max_iter=1000, random_state=random_state, n_jobs=-1),
    }
    try:
        import xgboost as xgb

        factories["xgboost"] = lambda: xgb.XGBClassifier(n_estimators=100, max_depth=5, learning_rate=0.1, random_state=random_state, n_jobs=-1)
    except Exception:
        pass
    try:
        import lightgbm as lgb

        factories["lightgbm"] = lambda: lgb.LGBMClassifier(n_estimators=100, max_depth=5, learning_rate=0.1, random_state=random_state, n_jobs=-1, verbose=-1)
    except Exception:
        pass
    return factories


def save_expert_training_metadata(result: dict[str, Any], output_dir: str | Path) -> Path:
    import json

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    metadata_path = output / f"{result['expert']}_metadata.json"
    payload = {
        "expert": result["expert"],
        "feature_columns": result["feature_columns"],
        "metrics": result["metrics"],
        "spec": EXPERT_SPECS[result["expert"]].__dict__,
    }
    metadata_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return metadata_path
