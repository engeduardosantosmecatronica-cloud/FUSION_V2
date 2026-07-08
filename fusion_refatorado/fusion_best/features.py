from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class FeatureConfig:
    windows: tuple[int, ...] = (5, 10, 12, 14, 20, 30, 45, 60, 120)
    return_windows: tuple[int, ...] = (1, 3, 5, 10, 20)
    atr_windows: tuple[int, ...] = (5, 10, 14, 20, 30)
    lag_windows: tuple[int, ...] = (1, 2, 3, 5, 10, 20)


def _volume_col(df: pd.DataFrame) -> str:
    if "volume" in df.columns:
        return "volume"
    if "tick_volume" in df.columns:
        return "tick_volume"
    raise KeyError("DataFrame precisa ter coluna 'volume' ou 'tick_volume'.")


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs = gain / (loss + 1e-12)
    return 100 - (100 / (1 + rs))


def _true_range(df: pd.DataFrame) -> pd.Series:
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift(1)).abs()
    low_close = (df["low"] - df["close"].shift(1)).abs()
    return pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)


def build_feature_matrix(
    df: pd.DataFrame,
    config: FeatureConfig | None = None,
    include_raw_ohlcv: bool = False,
) -> pd.DataFrame:
    """Build a compact best-of feature matrix from ALPHAEDU, NEXUS and BUILD_MODELS ideas."""
    cfg = config or FeatureConfig()
    required = {"open", "high", "low", "close"}
    missing = required.difference(df.columns)
    if missing:
        raise KeyError(f"Colunas obrigatorias ausentes: {sorted(missing)}")

    data = df.copy()
    volume = data[_volume_col(data)]
    close = data["close"]
    high = data["high"]
    low = data["low"]
    open_ = data["open"]

    features: dict[str, pd.Series] = {}
    ret_1 = close.pct_change()
    log_ret = np.log(close / close.shift(1))

    for window in cfg.return_windows:
        features[f"ret_{window}"] = close.pct_change(window)
        features[f"log_ret_sum_{window}"] = log_ret.rolling(window).sum()

    for window in cfg.windows:
        ma = close.rolling(window).mean()
        std = ret_1.rolling(window).std()
        high_max = high.rolling(window).max()
        low_min = low.rolling(window).min()
        vol_ma = volume.rolling(window).mean()
        vol_std = volume.rolling(window).std()

        features[f"ma_{window}"] = ma
        features[f"close_ma_ratio_{window}"] = (close - ma) / (ma + 1e-12)
        features[f"std_{window}"] = std
        features[f"corr_ret_volume_{window}"] = ret_1.rolling(window).corr(volume)
        features[f"close_high_ratio_{window}"] = (high_max - close) / (high_max + 1e-12)
        features[f"close_low_ratio_{window}"] = (close - low_min) / (low_min + 1e-12)
        features[f"position_in_range_{window}"] = (close - low_min) / (high_max - low_min + 1e-12)
        features[f"volume_ratio_{window}"] = volume / (vol_ma + 1e-12)
        features[f"volume_zscore_{window}"] = (volume - vol_ma) / (vol_std + 1e-12)

    features["range"] = high - low
    features["range_pct"] = (high - low) / (close + 1e-12)
    features["body"] = (close - open_).abs()
    features["body_pct"] = features["body"] / (features["range"] + 1e-12)
    features["upper_wick"] = high - pd.concat([open_, close], axis=1).max(axis=1)
    features["lower_wick"] = pd.concat([open_, close], axis=1).min(axis=1) - low
    features["close_position"] = (close - low) / ((high - low) + 1e-12)

    tr = _true_range(data)
    features["true_range"] = tr
    for window in cfg.atr_windows:
        atr = tr.rolling(window).mean()
        features[f"atr_{window}"] = atr
        features[f"atr_close_ratio_{window}"] = atr / (close + 1e-12)

    for window in cfg.lag_windows:
        features[f"lag_close_{window}"] = close.shift(window)
        features[f"lag_volume_{window}"] = volume.shift(window)

    rsi14 = _rsi(close, 14)
    rsi28 = _rsi(close, 28)
    features["rsi14"] = rsi14
    features["rsi28"] = rsi28
    features["rsi_diff"] = rsi14 - rsi28
    features["rsi_gap"] = rsi14 - rsi14.rolling(10).mean()

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    features["macd"] = macd
    features["macd_signal"] = macd.ewm(span=9, adjust=False).mean()
    features["macd_hist"] = features["macd"] - features["macd_signal"]

    for span in (8, 21, 50, 200):
        ema = close.ewm(span=span, adjust=False).mean()
        features[f"ema_{span}"] = ema
        features[f"dist_ema_{span}"] = (close / (ema + 1e-12)) - 1

    trend_votes = (rsi14 > 50).astype(int)
    for span in (8, 21, 50):
        trend_votes = trend_votes + (close > close.ewm(span=span, adjust=False).mean()).astype(int)
    features["trend_alignment"] = trend_votes

    result = pd.DataFrame(features, index=data.index)
    if include_raw_ohlcv:
        raw_cols = ["open", "high", "low", "close", _volume_col(data)]
        result = pd.concat([data[raw_cols], result], axis=1)
    return result.replace([np.inf, -np.inf], np.nan).dropna()


def create_multiclass_target(
    df: pd.DataFrame,
    horizon: int = 12,
    threshold: float = 0.0008,
) -> pd.Series:
    """Return 0=hold, 1=buy, 2=sell using future log-return."""
    future_ret = np.log(df["close"].shift(-horizon) / df["close"])
    target = pd.Series(0, index=df.index, name="target")
    target[future_ret > threshold] = 1
    target[future_ret < -threshold] = 2
    return target


def select_numeric_features(df: pd.DataFrame, exclude: Iterable[str] = ()) -> list[str]:
    excluded = set(exclude)
    return [
        col for col in df.columns
        if col not in excluded and pd.api.types.is_numeric_dtype(df[col])
    ]
