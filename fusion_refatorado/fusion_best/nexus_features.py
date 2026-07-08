from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

EPSILON = 1e-10


@dataclass
class CandlePatternSignal:
    name: str
    direction: int
    confidence: float
    strength: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VolumeProfileNode:
    price: float
    volume: float
    volume_buy: float = 0.0
    volume_sell: float = 0.0
    trades: int = 0


@dataclass
class TickData:
    timestamp: datetime
    bid: float
    ask: float
    volume: float
    volume_sell: float = 0.0
    volume_buy: float = 0.0


def nexus_sma(series: pd.Series, period: int = 20) -> pd.Series:
    return series.rolling(window=period).mean()


def nexus_ema(series: pd.Series, period: int = 20) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def nexus_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs = gain / (loss + EPSILON)
    return 100 - (100 / (1 + rs))


def nexus_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[pd.Series, pd.Series, pd.Series]:
    macd_line = nexus_ema(series, fast) - nexus_ema(series, slow)
    signal_line = nexus_ema(macd_line, signal)
    return macd_line, signal_line, macd_line - signal_line


def nexus_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def bollinger_bands(series: pd.Series, period: int = 20, std_dev: float = 2.0) -> tuple[pd.Series, pd.Series, pd.Series]:
    middle = nexus_sma(series, period)
    std = series.rolling(window=period).std()
    return middle + std * std_dev, middle, middle - std * std_dev


def stochastic_oscillator(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k_period: int = 14,
    d_period: int = 3,
) -> tuple[pd.Series, pd.Series]:
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()
    k = 100 * (close - lowest_low) / (highest_high - lowest_low + EPSILON)
    return k, k.rolling(window=d_period).mean()


def ichimoku_components(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.DataFrame:
    tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2
    kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2
    cloud_a = ((tenkan + kijun) / 2).shift(26)
    cloud_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)
    return pd.DataFrame(
        {
            "ichimoku_tenkan": tenkan,
            "ichimoku_kijun": kijun,
            "ichimoku_cloud_a": cloud_a,
            "ichimoku_cloud_b": cloud_b,
            "ichimoku_chikou": close.shift(-26),
        },
        index=close.index,
    )


def build_nexus_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    frame = frame.rename(columns={"timestamp": "time", "tickvol": "volume", "vol": "volume"})
    required = {"open", "high", "low", "close"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"missing required OHLC columns: {sorted(missing)}")
    if "volume" not in frame.columns:
        frame["volume"] = 0.0

    for period in [5, 10, 20, 50, 100, 200]:
        frame[f"nexus_sma_{period}"] = nexus_sma(frame["close"], period)
    for period in [5, 10, 20, 50]:
        frame[f"nexus_ema_{period}"] = nexus_ema(frame["close"], period)

    frame["nexus_sma_alignment"] = np.select(
        [
            (frame["close"] > frame["nexus_sma_20"]) & (frame["nexus_sma_20"] > frame["nexus_sma_50"]) & (frame["nexus_sma_50"] > frame["nexus_sma_200"]),
            (frame["close"] < frame["nexus_sma_20"]) & (frame["nexus_sma_20"] < frame["nexus_sma_50"]) & (frame["nexus_sma_50"] < frame["nexus_sma_200"]),
        ],
        [1, -1],
        default=0,
    )
    frame["nexus_sma_cross"] = np.sign(frame["nexus_sma_20"] - frame["nexus_sma_50"])
    frame["nexus_rsi_14"] = nexus_rsi(frame["close"], 14)
    frame["nexus_rsi_28"] = nexus_rsi(frame["close"], 28)
    macd_line, signal_line, histogram = nexus_macd(frame["close"])
    frame["nexus_macd"] = macd_line
    frame["nexus_macd_signal"] = signal_line
    frame["nexus_macd_hist"] = histogram
    frame["nexus_stoch_k"], frame["nexus_stoch_d"] = stochastic_oscillator(frame["high"], frame["low"], frame["close"])
    for period in [5, 10, 20]:
        frame[f"nexus_roc_{period}"] = frame["close"].pct_change(period)
    frame["nexus_momentum_score"] = ((frame["nexus_rsi_14"] - 50) / 50 + frame["nexus_macd_hist"] * 10 + (frame["nexus_stoch_k"] - 50) / 50) / 3
    frame["nexus_atr_14"] = nexus_atr(frame["high"], frame["low"], frame["close"], 14)
    frame["nexus_atr_pct"] = frame["nexus_atr_14"] / frame["close"].replace(0, np.nan)
    bb_upper, bb_mid, bb_lower = bollinger_bands(frame["close"])
    frame["nexus_bb_upper"] = bb_upper
    frame["nexus_bb_mid"] = bb_mid
    frame["nexus_bb_lower"] = bb_lower
    frame["nexus_bb_width"] = (bb_upper - bb_lower) / (bb_mid + EPSILON)
    frame["nexus_bb_position"] = (frame["close"] - bb_lower) / (bb_upper - bb_lower + EPSILON)
    for period in [10, 20, 50]:
        frame[f"nexus_volatility_{period}"] = frame["close"].pct_change().rolling(period).std()
    frame = pd.concat([frame, ichimoku_components(frame["high"], frame["low"], frame["close"])], axis=1)
    return add_candle_micro_features(frame)


def add_candle_micro_features(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    body = frame["close"] - frame["open"]
    total_range = (frame["high"] - frame["low"]).replace(0, np.nan)
    frame["nexus_body"] = body
    frame["nexus_body_pct"] = body / frame["close"].replace(0, np.nan)
    frame["nexus_upper_shadow"] = frame["high"] - frame[["close", "open"]].max(axis=1)
    frame["nexus_lower_shadow"] = frame[["close", "open"]].min(axis=1) - frame["low"]
    frame["nexus_candle_direction"] = np.sign(body).replace(0, 0)
    frame["nexus_doji"] = (body.abs() / total_range < 0.10).astype(int)
    frame["nexus_hammer"] = ((frame["nexus_lower_shadow"] > body.abs() * 2) & (frame["nexus_upper_shadow"] < body.abs() * 0.25)).astype(int)
    frame["nexus_shooting_star"] = ((frame["nexus_upper_shadow"] > body.abs() * 2) & (frame["nexus_lower_shadow"] < body.abs() * 0.25)).astype(int)
    frame["nexus_engulf_bullish"] = (
        (frame["close"].shift(1) < frame["open"].shift(1))
        & (frame["close"] > frame["open"])
        & (frame["open"] < frame["close"].shift(1))
        & (frame["close"] > frame["open"].shift(1))
    ).astype(int)
    frame["nexus_engulf_bearish"] = (
        (frame["close"].shift(1) > frame["open"].shift(1))
        & (frame["close"] < frame["open"])
        & (frame["open"] > frame["close"].shift(1))
        & (frame["close"] < frame["open"].shift(1))
    ).astype(int)
    return frame


def detect_latest_candle_patterns(df: pd.DataFrame) -> list[CandlePatternSignal]:
    if len(df) < 2:
        return []
    frame = add_candle_micro_features(df.tail(3))
    last = frame.iloc[-1]
    signals: list[CandlePatternSignal] = []
    mapping = {
        "nexus_doji": ("doji", 0, 0.50),
        "nexus_hammer": ("hammer", 1, 0.70),
        "nexus_shooting_star": ("shooting_star", -1, 0.70),
        "nexus_engulf_bullish": ("engulf_bullish", 1, 0.75),
        "nexus_engulf_bearish": ("engulf_bearish", -1, 0.75),
    }
    for column, (name, direction, confidence) in mapping.items():
        if int(last.get(column, 0)) == 1:
            signals.append(CandlePatternSignal(name=name, direction=direction, confidence=confidence, strength=confidence))
    return signals


def volume_profile_from_ticks(ticks: pd.DataFrame, price_col: str = "price", bins: int = 50) -> pd.DataFrame:
    if ticks.empty or price_col not in ticks.columns:
        return pd.DataFrame(columns=["price", "volume", "volume_buy", "volume_sell", "trades"])
    data = ticks.copy()
    if "volume" not in data.columns:
        data["volume"] = 1.0
    data["bin"] = pd.cut(data[price_col], bins=bins, duplicates="drop")
    grouped = data.groupby("bin", observed=True)
    rows = []
    for interval, group in grouped:
        midpoint = float(interval.mid)
        volume = float(group["volume"].sum())
        if "is_buy" in group.columns:
            buy = float(group.loc[group["is_buy"].astype(bool), "volume"].sum())
            sell = float(group.loc[~group["is_buy"].astype(bool), "volume"].sum())
        else:
            buy = sell = 0.0
        rows.append({"price": midpoint, "volume": volume, "volume_buy": buy, "volume_sell": sell, "trades": int(len(group))})
    return pd.DataFrame(rows).sort_values("price").reset_index(drop=True)


def summarize_order_book(bids: list[tuple[float, float]], asks: list[tuple[float, float]], levels: int = 10) -> dict[str, float]:
    bid_slice = bids[:levels]
    ask_slice = asks[:levels]
    if not bid_slice or not ask_slice:
        return {"spread": 0.0, "spread_pips": 0.0, "mid_price": 0.0, "volume_imbalance": 0.0}
    bid_volume = sum(volume for _, volume in bid_slice)
    ask_volume = sum(volume for _, volume in ask_slice)
    total = bid_volume + ask_volume
    spread = ask_slice[0][0] - bid_slice[0][0]
    return {
        "spread": float(spread),
        "spread_pips": float(spread * 10000),
        "mid_price": float((ask_slice[0][0] + bid_slice[0][0]) / 2),
        "bid_volume": float(bid_volume),
        "ask_volume": float(ask_volume),
        "volume_imbalance": float((bid_volume - ask_volume) / total) if total else 0.0,
        "depth_1m_bid": float(sum(volume for _, volume in bid_slice[:3])),
        "depth_1m_ask": float(sum(volume for _, volume in ask_slice[:3])),
    }
