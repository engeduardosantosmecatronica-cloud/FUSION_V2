# utils/indicators.py
from __future__ import annotations

from typing import Dict, Tuple

import numpy as np
import pandas as pd


EPSILON = 1e-10


# =========================
# Helpers
# =========================

def _validate_period(period: int, name: str = "period") -> None:
    if period <= 0:
        raise ValueError(f"{name} deve ser maior que zero.")


def _rolling_std(series: pd.Series, period: int, min_periods: int | None = None) -> pd.Series:
    return series.rolling(window=period, min_periods=min_periods or period).std()


# =========================
# Médias móveis
# =========================

def calculate_sma(prices: pd.Series, period: int = 20, min_periods: int | None = None) -> pd.Series:
    _validate_period(period)
    return prices.rolling(window=period, min_periods=min_periods or period).mean()


def calculate_ema(prices: pd.Series, period: int = 20) -> pd.Series:
    _validate_period(period)
    return prices.ewm(span=period, adjust=False).mean()


def calculate_wma(prices: pd.Series, period: int = 20) -> pd.Series:
    _validate_period(period)
    weights = np.arange(1, period + 1)

    return prices.rolling(window=period, min_periods=period).apply(
        lambda x: np.dot(x, weights) / weights.sum(),
        raw=True,
    )


def calculate_hma(prices: pd.Series, period: int = 20) -> pd.Series:
    _validate_period(period)
    half_length = max(1, period // 2)
    sqrt_length = max(1, int(np.sqrt(period)))

    wma_half = calculate_wma(prices, half_length)
    wma_full = calculate_wma(prices, period)

    hma_raw = 2 * wma_half - wma_full
    return calculate_wma(hma_raw, sqrt_length)


# =========================
# Osciladores
# =========================

def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    _validate_period(period)

    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    rsi = rsi.copy()
    rsi[(avg_loss == 0) & (avg_gain > 0)] = 100.0
    rsi[(avg_gain == 0) & (avg_loss > 0)] = 0.0
    rsi[(avg_gain == 0) & (avg_loss == 0)] = 50.0

    return rsi


def calculate_stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k_period: int = 14,
    d_period: int = 3,
) -> Tuple[pd.Series, pd.Series]:
    _validate_period(k_period, "k_period")
    _validate_period(d_period, "d_period")

    lowest_low = low.rolling(window=k_period, min_periods=k_period).min()
    highest_high = high.rolling(window=k_period, min_periods=k_period).max()

    stoch_k = 100 * ((close - lowest_low) / (highest_high - lowest_low + EPSILON))
    stoch_d = stoch_k.rolling(window=d_period, min_periods=d_period).mean()

    return stoch_k, stoch_d


def calculate_williams_r(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> pd.Series:
    _validate_period(period)

    highest_high = high.rolling(window=period, min_periods=period).max()
    lowest_low = low.rolling(window=period, min_periods=period).min()

    return -100 * ((highest_high - close) / (highest_high - lowest_low + EPSILON))


def calculate_cci(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 20,
) -> pd.Series:
    _validate_period(period)

    tp = (high + low + close) / 3
    sma_tp = tp.rolling(window=period, min_periods=period).mean()
    mad = tp.rolling(window=period, min_periods=period).apply(
        lambda x: np.abs(x - x.mean()).mean(),
        raw=True,
    )

    return (tp - sma_tp) / (0.015 * mad + EPSILON)


def calculate_roc(prices: pd.Series, period: int = 12) -> pd.Series:
    _validate_period(period)
    return ((prices - prices.shift(period)) / prices.shift(period)) * 100


def calculate_ultimate_oscillator(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period1: int = 7,
    period2: int = 14,
    period3: int = 28,
) -> pd.Series:
    _validate_period(period1, "period1")
    _validate_period(period2, "period2")
    _validate_period(period3, "period3")

    prev_close = close.shift(1)

    buying_pressure = close - pd.concat([low, prev_close], axis=1).min(axis=1)
    true_range = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    avg1 = buying_pressure.rolling(period1, min_periods=period1).sum() / (
        true_range.rolling(period1, min_periods=period1).sum() + EPSILON
    )
    avg2 = buying_pressure.rolling(period2, min_periods=period2).sum() / (
        true_range.rolling(period2, min_periods=period2).sum() + EPSILON
    )
    avg3 = buying_pressure.rolling(period3, min_periods=period3).sum() / (
        true_range.rolling(period3, min_periods=period3).sum() + EPSILON
    )

    return 100 * (4 * avg1 + 2 * avg2 + avg3) / 7


def calculate_macd(
    prices: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    _validate_period(fast, "fast")
    _validate_period(slow, "slow")
    _validate_period(signal, "signal")

    ema_fast = calculate_ema(prices, fast)
    ema_slow = calculate_ema(prices, slow)

    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


# =========================
# Volatilidade
# =========================

def calculate_true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)


def calculate_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> pd.Series:
    _validate_period(period)
    tr = calculate_true_range(high, low, close)
    return tr.rolling(window=period, min_periods=period).mean()


def calculate_bollinger_bands(
    prices: pd.Series,
    period: int = 20,
    num_std: float = 2.0,
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    _validate_period(period)

    middle = calculate_sma(prices, period=period, min_periods=period)
    std = prices.rolling(window=period, min_periods=period).std()

    upper = middle + (std * num_std)
    lower = middle - (std * num_std)

    return upper, middle, lower


def calculate_keltner_channels(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    ema_period: int = 20,
    atr_period: int = 10,
    multiplier: float = 2.0,
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    _validate_period(ema_period, "ema_period")
    _validate_period(atr_period, "atr_period")

    ema = calculate_ema(close, ema_period)
    atr = calculate_atr(high, low, close, atr_period)

    upper = ema + (atr * multiplier)
    lower = ema - (atr * multiplier)

    return upper, ema, lower


def calculate_historical_volatility(prices: pd.Series, period: int = 20) -> pd.Series:
    _validate_period(period)
    log_returns = np.log(prices / prices.shift(1))
    return log_returns.rolling(window=period, min_periods=period).std() * np.sqrt(252)


# =========================
# Tendência
# =========================

def calculate_adx(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    _validate_period(period)

    tr = calculate_true_range(high, low, close)
    atr = tr.rolling(window=period, min_periods=period).mean()

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(
        np.where((up_move > down_move) & (up_move > 0), up_move, 0.0),
        index=high.index,
        dtype=float,
    )
    minus_dm = pd.Series(
        np.where((down_move > up_move) & (down_move > 0), down_move, 0.0),
        index=high.index,
        dtype=float,
    )

    plus_di = 100 * (plus_dm.rolling(window=period, min_periods=period).mean() / (atr + EPSILON))
    minus_di = 100 * (minus_dm.rolling(window=period, min_periods=period).mean() / (atr + EPSILON))

    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di + EPSILON))
    adx = dx.rolling(window=period, min_periods=period).mean()

    return adx, plus_di, minus_di, atr


def calculate_ichimoku(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    tenkan_period: int = 9,
    kijun_period: int = 26,
    senkou_b_period: int = 52,
) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
    _validate_period(tenkan_period, "tenkan_period")
    _validate_period(kijun_period, "kijun_period")
    _validate_period(senkou_b_period, "senkou_b_period")

    tenkan_high = high.rolling(window=tenkan_period, min_periods=tenkan_period).max()
    tenkan_low = low.rolling(window=tenkan_period, min_periods=tenkan_period).min()
    tenkan_sen = (tenkan_high + tenkan_low) / 2

    kijun_high = high.rolling(window=kijun_period, min_periods=kijun_period).max()
    kijun_low = low.rolling(window=kijun_period, min_periods=kijun_period).min()
    kijun_sen = (kijun_high + kijun_low) / 2

    senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(kijun_period)
    senkou_span_b = (
        (high.rolling(window=senkou_b_period, min_periods=senkou_b_period).max() +
         low.rolling(window=senkou_b_period, min_periods=senkou_b_period).min()) / 2
    ).shift(kijun_period)

    chikou_span = close.shift(-kijun_period)

    return tenkan_sen, kijun_sen, senkou_span_a, senkou_span_b, chikou_span


def calculate_parabolic_sar(
    high: pd.Series,
    low: pd.Series,
    acceleration: float = 0.02,
    maximum: float = 0.2,
) -> pd.Series:
    length = len(high)
    if length == 0:
        return pd.Series(dtype=float)

    sar = pd.Series(index=high.index, dtype=float)
    sar.iloc[0] = low.iloc[0]

    ep = high.iloc[0]
    af = acceleration
    trend = 1

    for i in range(1, length):
        sar.iloc[i] = sar.iloc[i - 1] + af * (ep - sar.iloc[i - 1])

        if trend == 1:
            if sar.iloc[i] > low.iloc[i]:
                trend = -1
                sar.iloc[i] = ep
                ep = low.iloc[i]
                af = acceleration
            elif high.iloc[i] > ep:
                ep = high.iloc[i]
                af = min(af + acceleration, maximum)
        else:
            if sar.iloc[i] < high.iloc[i]:
                trend = 1
                sar.iloc[i] = ep
                ep = high.iloc[i]
                af = acceleration
            elif low.iloc[i] < ep:
                ep = low.iloc[i]
                af = min(af + acceleration, maximum)

    return sar


# =========================
# Volume
# =========================

def calculate_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = pd.Series(0.0, index=close.index)
    direction.loc[close.diff() > 0] = 1.0
    direction.loc[close.diff() < 0] = -1.0
    return (direction * volume).cumsum()


def calculate_mfi(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
    period: int = 14,
) -> pd.Series:
    _validate_period(period)

    typical_price = (high + low + close) / 3
    raw_money_flow = typical_price * volume

    positive_flow = raw_money_flow.where(typical_price > typical_price.shift(1), 0.0)
    negative_flow = raw_money_flow.where(typical_price < typical_price.shift(1), 0.0)

    positive_sum = positive_flow.rolling(window=period, min_periods=period).sum()
    negative_sum = negative_flow.rolling(window=period, min_periods=period).sum()

    money_ratio = positive_sum / (negative_sum + EPSILON)
    return 100 - (100 / (1 + money_ratio))


def calculate_vwap(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
) -> pd.Series:
    typical_price = (high + low + close) / 3
    cumulative_volume = volume.cumsum().replace(0, np.nan)
    return (typical_price * volume).cumsum() / cumulative_volume


def calculate_volume_profile(prices: pd.Series, volume: pd.Series, bins: int = 10) -> pd.Series:
    if bins <= 0:
        raise ValueError("bins deve ser maior que zero.")
    price_bins = pd.cut(prices, bins=bins)
    return volume.groupby(price_bins, observed=False).sum()


# =========================
# Suporte e resistência
# =========================

def calculate_pivot_points(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
    pivot = (high + low + close) / 3

    r1 = 2 * pivot - low
    r2 = pivot + (high - low)
    r3 = high + 2 * (pivot - low)

    s1 = 2 * pivot - high
    s2 = pivot - (high - low)
    s3 = low - 2 * (high - pivot)

    return pivot, r1, r2, r3, s1, s2, s3


def calculate_fibonacci_levels(high: pd.Series, low: pd.Series) -> Dict[str, float]:
    last_high = float(high.iloc[-1]) if not high.empty else 0.0
    last_low = float(low.iloc[-1]) if not low.empty else 0.0
    diff = last_high - last_low

    return {
        "0.0": last_low,
        "0.236": last_low + 0.236 * diff,
        "0.382": last_low + 0.382 * diff,
        "0.5": last_low + 0.5 * diff,
        "0.618": last_low + 0.618 * diff,
        "0.786": last_low + 0.786 * diff,
        "1.0": last_high,
    }


# =========================
# Utilitários
# =========================

def calculate_zscore(series: pd.Series, period: int = 20) -> pd.Series:
    _validate_period(period)
    mean = series.rolling(window=period, min_periods=period).mean()
    std = series.rolling(window=period, min_periods=period).std()
    return (series - mean) / (std + EPSILON)


def calculate_correlation(series1: pd.Series, series2: pd.Series, period: int = 20) -> pd.Series:
    _validate_period(period)
    return series1.rolling(window=period, min_periods=period).corr(series2)


def calculate_entropy(series: pd.Series, period: int = 20) -> pd.Series:
    _validate_period(period)

    def entropy_calc(x: np.ndarray) -> float:
        _, counts = np.unique(x, return_counts=True)
        probs = counts / len(x)
        return float(-np.sum(probs * np.log2(probs + EPSILON)))

    return series.rolling(window=period, min_periods=period).apply(entropy_calc, raw=True)
