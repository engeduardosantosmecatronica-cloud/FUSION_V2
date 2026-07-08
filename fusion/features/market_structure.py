from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable
import warnings

import numpy as np
import pandas as pd
from pandas.errors import PerformanceWarning

warnings.filterwarnings("ignore", category=PerformanceWarning)


@dataclass(frozen=True)
class MarketStructureConfig:
    windows: tuple[int, ...] = (3, 5, 10, 20)
    atr_period: int = 14
    volume_window: int = 20
    compression_window: int = 10
    support_resistance_window: int = 20
    entropy_bins: int = 10


def _safe_div(a: pd.Series | float, b: pd.Series | float) -> pd.Series | float:
    return a / (b + 1e-12)


def _true_range(df: pd.DataFrame) -> pd.Series:
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift(1)).abs()
    low_close = (df["low"] - df["close"].shift(1)).abs()
    return pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)


def _rolling_entropy(series: pd.Series, window: int, bins: int) -> pd.Series:
    def calc(values: np.ndarray) -> float:
        clean = values[np.isfinite(values)]
        if len(clean) < 3:
            return np.nan
        hist, _ = np.histogram(clean, bins=bins)
        probs = hist[hist > 0] / hist.sum()
        return float(-(probs * np.log(probs)).sum())

    return series.rolling(window).apply(calc, raw=True)


def _bars_since(condition: pd.Series) -> pd.Series:
    condition = condition.fillna(False).astype(bool)
    seen = condition.cumsum()
    index = pd.Series(np.arange(len(condition)), index=condition.index)
    last_seen = index.where(condition).groupby(seen).ffill()
    result = index - last_seen
    result[seen == 0] = np.nan
    return result


def _session(hour: pd.Series) -> pd.Series:
    conditions = [
        hour.between(0, 6, inclusive="left"),
        hour.between(6, 12, inclusive="left"),
        hour.between(12, 18, inclusive="left"),
    ]
    return np.select(conditions, ["asia", "london", "ny"], default="after_hours")


def build_market_structure_features(
    df: pd.DataFrame,
    config: MarketStructureConfig | None = None,
    include_raw_ohlcv: bool = False,
) -> pd.DataFrame:
    """Calcula features observacionais de estrutura, volatilidade, volume e regime.

    A funcao e intencionalmente independente do runtime de ordens. Ela aceita um
    dataframe OHLCV historico e retorna features para pesquisa, logs e treinamento.
    """
    config = config or MarketStructureConfig()
    if df is None or df.empty:
        return pd.DataFrame()

    data = df.copy()
    if "date" in data.columns:
        data["time"] = pd.to_datetime(data["date"])
        data = data.drop(columns=["date"])
    elif "time" in data.columns:
        data["time"] = pd.to_datetime(data["time"])
    elif isinstance(data.index, pd.DatetimeIndex):
        data["time"] = data.index
    else:
        data["time"] = pd.RangeIndex(len(data))

    data = data.sort_values("time").reset_index(drop=True)
    volume_col = "tick_volume" if "tick_volume" in data.columns else "volume"
    if volume_col not in data.columns:
        data[volume_col] = 0.0
    if "real_volume" not in data.columns:
        data["real_volume"] = 0.0

    open_ = data["open"].astype(float)
    high = data["high"].astype(float)
    low = data["low"].astype(float)
    close = data["close"].astype(float)
    volume = data[volume_col].astype(float)
    candle_range = (high - low).replace(0, np.nan)
    body = (close - open_).abs()
    signed_body = close - open_
    upper_wick = high - pd.concat([open_, close], axis=1).max(axis=1)
    lower_wick = pd.concat([open_, close], axis=1).min(axis=1) - low
    tr = _true_range(data)
    atr = tr.rolling(config.atr_period).mean()
    atr_5 = tr.rolling(5).mean()
    atr_50 = tr.rolling(50).mean()
    ret = np.log(close / close.shift(1))

    features = pd.DataFrame(index=data.index)
    if include_raw_ohlcv:
        for col in ["time", "open", "high", "low", "close", volume_col, "spread", "real_volume"]:
            if col in data.columns:
                features[col] = data[col]
    else:
        features["time"] = data["time"]

    features["body"] = body
    features["signed_body"] = signed_body
    features["body_points"] = _safe_div(body, data.get("point_value", pd.Series(1.0, index=data.index)).astype(float))
    features["range"] = candle_range
    features["upper_wick"] = upper_wick.clip(lower=0)
    features["lower_wick"] = lower_wick.clip(lower=0)
    features["body_to_range"] = _safe_div(body, candle_range)
    features["upper_wick_to_range"] = _safe_div(features["upper_wick"], candle_range)
    features["lower_wick_to_range"] = _safe_div(features["lower_wick"], candle_range)
    features["wick_imbalance"] = _safe_div(features["lower_wick"] - features["upper_wick"], candle_range)
    features["close_position"] = _safe_div(close - low, candle_range)
    features["movement_efficiency"] = _safe_div(body, candle_range)
    features["inefficiency"] = _safe_div(candle_range, body.replace(0, np.nan))
    features["is_bullish"] = (close > open_).astype(int)
    features["is_bearish"] = (close < open_).astype(int)
    features["is_doji"] = (body <= candle_range * 0.1).astype(int)
    features["rejection_upper"] = ((features["upper_wick_to_range"] >= 0.45) & (features["close_position"] <= 0.6)).astype(int)
    features["rejection_lower"] = ((features["lower_wick_to_range"] >= 0.45) & (features["close_position"] >= 0.4)).astype(int)

    direction = np.sign(signed_body).replace(0, np.nan)
    features["consecutive_up"] = features["is_bullish"].groupby((features["is_bullish"] == 0).cumsum()).cumcount() + 1
    features.loc[features["is_bullish"] == 0, "consecutive_up"] = 0
    features["consecutive_down"] = features["is_bearish"].groupby((features["is_bearish"] == 0).cumsum()).cumcount() + 1
    features.loc[features["is_bearish"] == 0, "consecutive_down"] = 0
    features["body_change"] = body.diff()
    features["body_momentum_loss"] = ((body < body.shift(1)) & (body.shift(1) < body.shift(2))).astype(int)

    features["true_range"] = tr
    features["atr"] = atr
    features["atr_5"] = atr_5
    features["atr_50"] = atr_50
    features["atr_ratio_5_50"] = _safe_div(atr_5, atr_50)
    features["range_to_atr"] = _safe_div(candle_range, atr)
    range_mean_20 = candle_range.rolling(20).mean()
    range_std_20 = candle_range.rolling(20).std()
    features["range_zscore_20"] = _safe_div(candle_range - range_mean_20, range_std_20)
    features["range_contraction"] = (_safe_div(atr_5, atr_50) <= 0.70).astype(int)
    features["range_expansion"] = (_safe_div(atr_5, atr_50) >= 1.30).astype(int)
    features["volatility_expansion"] = (features["range_to_atr"] >= 1.5).astype(int)
    rolling_range = candle_range.rolling(config.compression_window).mean()
    features["volatility_compression"] = (
        rolling_range <= rolling_range.rolling(config.compression_window * 2).quantile(0.25)
    ).astype(int)
    features["compression_breakout"] = (
        (features["volatility_compression"].shift(1) == 1) & (features["range_to_atr"] >= 1.5)
    ).astype(int)

    volume_mean = volume.rolling(config.volume_window).mean()
    volume_std = volume.rolling(config.volume_window).std()
    features["volume"] = volume
    features["volume_ratio"] = _safe_div(volume, volume_mean)
    features["volume_zscore"] = _safe_div(volume - volume_mean, volume_std)
    features["volume_climax"] = (features["volume_zscore"] >= 2.0).astype(int)
    features["delta_proxy"] = signed_body * volume
    features["pressure"] = _safe_div(signed_body, volume.replace(0, np.nan))
    features["buy_pressure_proxy"] = _safe_div((close - low), candle_range) * volume
    features["sell_pressure_proxy"] = _safe_div((high - close), candle_range) * volume
    features["pressure_imbalance"] = _safe_div(
        features["buy_pressure_proxy"] - features["sell_pressure_proxy"],
        volume.replace(0, np.nan),
    )
    features["effort_result"] = _safe_div(features["volume_ratio"], features["movement_efficiency"].replace(0, np.nan))
    features["absorption"] = (
        (features["volume_ratio"] >= 1.5)
        & (features["body_to_range"] <= 0.35)
        & ((features["upper_wick_to_range"] >= 0.35) | (features["lower_wick_to_range"] >= 0.35))
    ).astype(int)
    features["empty_market_move"] = ((features["volume_ratio"] <= 0.8) & (features["range_to_atr"] >= 1.2)).astype(int)

    for period in (9, 21, 50, 200):
        ema = close.ewm(span=period, adjust=False).mean()
        features[f"ema{period}"] = ema
        features[f"dist_ema{period}"] = _safe_div(close, ema) - 1
        features[f"ema{period}_slope"] = ema.diff(5)
        features[f"ema{period}_slope_atr"] = _safe_div(features[f"ema{period}_slope"], atr)

    features["ema_alignment_buy"] = ((features["ema9"] > features["ema21"]) & (features["ema21"] > features["ema50"])).astype(int)
    features["ema_alignment_sell"] = ((features["ema9"] < features["ema21"]) & (features["ema21"] < features["ema50"])).astype(int)
    features["price_extension_atr"] = _safe_div(close - features["ema21"], atr)

    features["log_ret"] = ret
    for window in config.windows:
        features[f"ret_sum_{window}"] = ret.rolling(window).sum()
        features[f"velocity_{window}"] = close - close.shift(window)
        features[f"velocity_atr_{window}"] = _safe_div(features[f"velocity_{window}"], atr)
        features[f"acceleration_{window}"] = features[f"velocity_{window}"].diff()
        features[f"range_mean_{window}"] = candle_range.rolling(window).mean()
        features[f"volume_sum_{window}"] = volume.rolling(window).sum()
        features[f"volatility_{window}"] = ret.rolling(window).std()
        features[f"skew_{window}"] = ret.rolling(window).skew()
        features[f"kurtosis_{window}"] = ret.rolling(window).kurt()
        features[f"entropy_{window}"] = _rolling_entropy(ret, window, config.entropy_bins)
        path_distance = (close - close.shift(window)).abs()
        path_noise = close.diff().abs().rolling(window).sum()
        features[f"kaufman_er_{window}"] = _safe_div(path_distance, path_noise)
        features[f"overlap_ratio_{window}"] = (
            (pd.concat([high, high.shift(1)], axis=1).min(axis=1) - pd.concat([low, low.shift(1)], axis=1).max(axis=1)).clip(lower=0)
            .rolling(window)
            .mean()
            .pipe(lambda s: _safe_div(s, candle_range.rolling(window).mean()))
        )

    local_window = config.support_resistance_window
    rolling_high = high.rolling(local_window).max()
    rolling_low = low.rolling(local_window).min()
    tolerance = atr * 0.2
    features["near_resistance"] = ((rolling_high - close).abs() <= tolerance).astype(int)
    features["near_support"] = ((close - rolling_low).abs() <= tolerance).astype(int)
    features["resistance_touches"] = ((rolling_high - high).abs() <= tolerance).rolling(local_window).sum()
    features["support_touches"] = ((low - rolling_low).abs() <= tolerance).rolling(local_window).sum()
    features["breakout_up"] = (close > rolling_high.shift(1)).astype(int)
    features["breakout_down"] = (close < rolling_low.shift(1)).astype(int)
    features["breakout_up_with_volume"] = ((features["breakout_up"] == 1) & (features["volume_ratio"] >= 1.2)).astype(int)
    features["breakout_down_with_volume"] = ((features["breakout_down"] == 1) & (features["volume_ratio"] >= 1.2)).astype(int)
    features["swing_high"] = (high >= rolling_high).astype(int)
    features["swing_low"] = (low <= rolling_low).astype(int)
    prior_swing_high = high.where(features["swing_high"].astype(bool)).ffill().shift(1)
    prior_swing_low = low.where(features["swing_low"].astype(bool)).ffill().shift(1)
    prior_swing_high_2 = high.where(features["swing_high"].astype(bool)).ffill().shift(2)
    prior_swing_low_2 = low.where(features["swing_low"].astype(bool)).ffill().shift(2)
    features["distance_to_swing_high_atr"] = _safe_div(prior_swing_high - close, atr)
    features["distance_to_swing_low_atr"] = _safe_div(close - prior_swing_low, atr)
    features["break_of_structure_up"] = (close > prior_swing_high).astype(int)
    features["break_of_structure_down"] = (close < prior_swing_low).astype(int)
    features["liquidity_grab_up"] = ((high > prior_swing_high) & (close < prior_swing_high)).astype(int)
    features["liquidity_grab_down"] = ((low < prior_swing_low) & (close > prior_swing_low)).astype(int)
    features["higher_high"] = ((features["swing_high"] == 1) & (high > prior_swing_high)).astype(int)
    features["lower_high"] = ((features["swing_high"] == 1) & (high < prior_swing_high)).astype(int)
    features["higher_low"] = ((features["swing_low"] == 1) & (low > prior_swing_low)).astype(int)
    features["lower_low"] = ((features["swing_low"] == 1) & (low < prior_swing_low)).astype(int)
    features["swing_high_expansion_atr"] = _safe_div(high - prior_swing_high_2, atr)
    features["swing_low_expansion_atr"] = _safe_div(prior_swing_low_2 - low, atr)
    structure_event = pd.Series(
        np.select(
            [features["break_of_structure_up"] == 1, features["break_of_structure_down"] == 1],
            [1, -1],
            default=np.nan,
        ),
        index=features.index,
    )
    structure_bias = structure_event.ffill().fillna(0)
    features["structure_bias"] = structure_bias
    features["change_of_character_up"] = ((features["break_of_structure_up"] == 1) & (structure_bias.shift(1) < 0)).astype(int)
    features["change_of_character_down"] = ((features["break_of_structure_down"] == 1) & (structure_bias.shift(1) > 0)).astype(int)
    features["bullish_structure_sequence"] = (
        (features["higher_high"].rolling(12).sum() >= 1)
        & (features["higher_low"].rolling(12).sum() >= 1)
    ).astype(int)
    features["bearish_structure_sequence"] = (
        (features["lower_low"].rolling(12).sum() >= 1)
        & (features["lower_high"].rolling(12).sum() >= 1)
    ).astype(int)
    features["structure_transition"] = (
        ((features["change_of_character_up"] == 1) | (features["change_of_character_down"] == 1))
        & (features["volatility_expansion"] == 1)
    ).astype(int)
    features["displacement_up"] = (
        (close > open_)
        & (features["range_to_atr"] >= 1.2)
        & (features["body_to_range"] >= 0.60)
        & (features["close_position"] >= 0.70)
        & (features["volume_ratio"] >= 1.05)
    ).astype(int)
    features["displacement_down"] = (
        (close < open_)
        & (features["range_to_atr"] >= 1.2)
        & (features["body_to_range"] >= 0.60)
        & (features["close_position"] <= 0.30)
        & (features["volume_ratio"] >= 1.05)
    ).astype(int)
    features["bullish_fvg"] = (low > high.shift(2)).astype(int)
    features["bearish_fvg"] = (high < low.shift(2)).astype(int)
    bullish_fvg_top = low.where(features["bullish_fvg"].astype(bool))
    bullish_fvg_bottom = high.shift(2).where(features["bullish_fvg"].astype(bool))
    bearish_fvg_top = low.shift(2).where(features["bearish_fvg"].astype(bool))
    bearish_fvg_bottom = high.where(features["bearish_fvg"].astype(bool))
    prior_bullish_fvg_top = bullish_fvg_top.ffill().shift(1)
    prior_bullish_fvg_bottom = bullish_fvg_bottom.ffill().shift(1)
    prior_bearish_fvg_top = bearish_fvg_top.ffill().shift(1)
    prior_bearish_fvg_bottom = bearish_fvg_bottom.ffill().shift(1)
    features["bullish_fvg_size_atr"] = _safe_div(bullish_fvg_top - bullish_fvg_bottom, atr)
    features["bearish_fvg_size_atr"] = _safe_div(bearish_fvg_top - bearish_fvg_bottom, atr)
    features["bullish_fvg_mitigated"] = (
        (low <= prior_bullish_fvg_top)
        & (high >= prior_bullish_fvg_bottom)
    ).astype(int)
    features["bearish_fvg_mitigated"] = (
        (high >= prior_bearish_fvg_bottom)
        & (low <= prior_bearish_fvg_top)
    ).astype(int)
    features["bullish_imbalance"] = ((features["bullish_fvg"] == 1) & (features["displacement_up"] == 1)).astype(int)
    features["bearish_imbalance"] = ((features["bearish_fvg"] == 1) & (features["displacement_down"] == 1)).astype(int)
    features["bullish_order_block_proxy"] = (
        (features["displacement_up"] == 1)
        & (close.shift(1) < open_.shift(1))
    ).astype(int)
    features["bearish_order_block_proxy"] = (
        (features["displacement_down"] == 1)
        & (close.shift(1) > open_.shift(1))
    ).astype(int)
    features["stop_hunt_up"] = (
        (features["liquidity_grab_up"] == 1)
        & ((features["volume_ratio"] >= 1.1) | (features["rejection_upper"] == 1))
    ).astype(int)
    features["stop_hunt_down"] = (
        (features["liquidity_grab_down"] == 1)
        & ((features["volume_ratio"] >= 1.1) | (features["rejection_lower"] == 1))
    ).astype(int)
    features["institutional_structure_score"] = (
        0.50
        + (features["bullish_structure_sequence"] + features["bearish_structure_sequence"]) * 0.10
        + (features["displacement_up"] + features["displacement_down"]) * 0.08
        + (features["bullish_imbalance"] + features["bearish_imbalance"]) * 0.06
        + (features["break_of_structure_up"] + features["break_of_structure_down"]) * 0.08
        - (features["stop_hunt_up"] + features["stop_hunt_down"]) * 0.12
        - features["volatility_compression"].fillna(0) * 0.08
        - (features["overlap_ratio_10"].fillna(0).clip(lower=0, upper=1) * 0.08)
    ).clip(lower=0.0, upper=1.0)
    features["bars_since_breakout_up"] = _bars_since(features["breakout_up"] == 1)
    features["bars_since_breakout_down"] = _bars_since(features["breakout_down"] == 1)
    features["bars_since_volume_climax"] = _bars_since(features["volume_climax"] == 1)
    features["bars_since_swing_high"] = _bars_since(features["swing_high"] == 1)
    features["bars_since_swing_low"] = _bars_since(features["swing_low"] == 1)
    features["bars_since_bos_up"] = _bars_since(features["break_of_structure_up"] == 1)
    features["bars_since_bos_down"] = _bars_since(features["break_of_structure_down"] == 1)
    features["bars_since_choch_up"] = _bars_since(features["change_of_character_up"] == 1)
    features["bars_since_choch_down"] = _bars_since(features["change_of_character_down"] == 1)
    features["bars_since_stop_hunt_up"] = _bars_since(features["stop_hunt_up"] == 1)
    features["bars_since_stop_hunt_down"] = _bars_since(features["stop_hunt_down"] == 1)

    trend_score = (
        features["ema_alignment_buy"]
        - features["ema_alignment_sell"]
        + np.sign(features["ema21_slope_atr"].fillna(0))
        + np.sign(features["velocity_atr_10"].fillna(0))
    )
    features["regime_trend"] = (trend_score.abs() >= 3).astype(int)
    features["regime_consolidation"] = (
        (features["volatility_compression"] == 1)
        | ((features["overlap_ratio_10"] >= 0.55) & (features["range_to_atr"] <= 1.0))
    ).astype(int)
    features["regime_expansion"] = ((features["range_to_atr"] >= 1.5) & (features["volume_ratio"] >= 1.1)).astype(int)
    features["regime_reversal_risk"] = (
        ((features["consecutive_up"] >= 5) & (features["rejection_upper"] == 1))
        | ((features["consecutive_down"] >= 5) & (features["rejection_lower"] == 1))
    ).astype(int)

    time_series = pd.to_datetime(data["time"], errors="coerce")
    if pd.api.types.is_datetime64_any_dtype(time_series):
        features["hour"] = time_series.dt.hour
        features["minute"] = time_series.dt.minute
        features["day_of_week"] = time_series.dt.dayofweek
        features["session"] = _session(features["hour"])
    else:
        features["hour"] = np.nan
        features["minute"] = np.nan
        features["day_of_week"] = np.nan
        features["session"] = "unknown"

    numeric_cols = features.select_dtypes(include=[np.number]).columns
    features[numeric_cols] = features[numeric_cols].replace([np.inf, -np.inf], np.nan)
    return features


def build_multi_timeframe_snapshot(frames: dict[str, pd.DataFrame], config: MarketStructureConfig | None = None) -> pd.DataFrame:
    rows = []
    for timeframe, frame in frames.items():
        features = build_market_structure_features(frame, config=config)
        if features.empty:
            continue
        row = features.tail(1).copy()
        row.insert(0, "timeframe", timeframe)
        rows.append(row)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def build_asset_profile(
    frames: dict[str, pd.DataFrame],
    symbol: str,
    correlation_symbols: dict[str, pd.Series] | None = None,
) -> dict:
    profile: dict[str, object] = {"symbol": symbol}
    base = frames.get("D1")
    if base is None or base.empty:
        base = frames.get("H1")
    if base is None or base.empty:
        base = next(iter(frames.values()), pd.DataFrame())
    if base is None or base.empty:
        return profile

    data = base.copy()
    if "date" in data.columns:
        data["time"] = pd.to_datetime(data["date"])
    elif "time" in data.columns:
        data["time"] = pd.to_datetime(data["time"])
    elif isinstance(data.index, pd.DatetimeIndex):
        data["time"] = data.index
    volume_col = "tick_volume" if "tick_volume" in data.columns else "volume"
    if volume_col not in data.columns:
        data[volume_col] = 0.0

    high = data["high"].astype(float)
    low = data["low"].astype(float)
    close = data["close"].astype(float)
    ret = np.log(close / close.shift(1))
    point_value = float(data["point_value"].dropna().iloc[0]) if "point_value" in data.columns and data["point_value"].notna().any() else 1.0
    daily_range_points = (high - low) / point_value

    profile["natural_volatility_ret_std"] = float(ret.std(skipna=True))
    profile["noise_level_range_to_body"] = float(_safe_div(high - low, (close - data["open"]).abs()).replace([np.inf, -np.inf], np.nan).median(skipna=True))
    profile["average_directional_bias"] = float(ret.mean(skipna=True))
    profile["average_daily_amplitude_points"] = float(daily_range_points.mean(skipna=True))
    profile["median_daily_amplitude_points"] = float(daily_range_points.median(skipna=True))

    m5 = frames.get("M5")
    if m5 is not None and not m5.empty:
        m5_data = m5.copy()
        if "date" in m5_data.columns:
            m5_data["time"] = pd.to_datetime(m5_data["date"])
        elif "time" in m5_data.columns:
            m5_data["time"] = pd.to_datetime(m5_data["time"])
        m5_data["day"] = m5_data["time"].dt.date
        profile["daily_m5_path_points"] = float(((m5_data["high"] - m5_data["low"]) / point_value).groupby(m5_data["day"]).sum().mean())

    if "time" in data.columns and pd.api.types.is_datetime64_any_dtype(data["time"]):
        data["hour"] = data["time"].dt.hour
        hourly_ret = ret.groupby(data["hour"]).mean()
        profile["best_bullish_hour"] = int(hourly_ret.idxmax()) if not hourly_ret.empty else None
        profile["best_bearish_hour"] = int(hourly_ret.idxmin()) if not hourly_ret.empty else None

    if correlation_symbols:
        correlations = {}
        for other, other_close in correlation_symbols.items():
            other_ret = np.log(other_close / other_close.shift(1))
            corr = ret.corr(other_ret)
            if pd.notna(corr):
                correlations[other] = float(corr)
        ordered = sorted(correlations.items(), key=lambda item: item[1])
        profile["strongest_negative_correlations"] = ordered[:5]
        profile["strongest_positive_correlations"] = ordered[-5:][::-1]

    vol = float(profile.get("natural_volatility_ret_std", 0.0) or 0.0)
    bias = float(profile.get("average_directional_bias", 0.0) or 0.0)
    if vol > 0.01:
        role = "volatility_driver"
    elif abs(bias) > vol * 0.05:
        role = "directional_bias"
    else:
        role = "diversifier"
    profile["probable_portfolio_role"] = role
    return profile
