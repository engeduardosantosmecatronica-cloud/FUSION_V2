from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PatternStateConfig:
    atr_period: int = 14
    adx_period: int = 14
    bb_period: int = 20
    bb_std_mult: float = 2.0
    rsi_period: int = 14
    mfi_period: int = 14
    price_channel_period: int = 20
    fractal_left: int = 2
    fractal_right: int = 2
    squeeze_lookback: int = 80
    volume_lookback: int = 20
    adaptive_period: int = 20


def _safe_div(a: pd.Series | float, b: pd.Series | float) -> pd.Series | float:
    return a / (b + 1e-12)


def _volume(df: pd.DataFrame) -> pd.Series:
    for col in ("tick_volume", "real_volume", "volume"):
        if col in df.columns:
            return df[col].astype(float)
    return pd.Series(0.0, index=df.index)


def _true_range(df: pd.DataFrame) -> pd.Series:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    return pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs = gain / (loss + 1e-12)
    return 100 - (100 / (1 + rs))


def _adx(df: pd.DataFrame, period: int) -> tuple[pd.Series, pd.Series, pd.Series]:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    tr = _true_range(df)
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=df.index)
    atr = tr.rolling(period).mean()
    plus_di = 100 * plus_dm.rolling(period).mean() / (atr + 1e-12)
    minus_di = 100 * minus_dm.rolling(period).mean() / (atr + 1e-12)
    dx = ((plus_di - minus_di).abs() / ((plus_di + minus_di) + 1e-12)) * 100
    return dx.rolling(period).mean(), plus_di, minus_di


def _macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[pd.Series, pd.Series, pd.Series]:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=signal, adjust=False).mean()
    return macd, macd_signal, macd - macd_signal


def _obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    return (np.sign(close.diff()).fillna(0.0) * volume).cumsum()


def _mfi(df: pd.DataFrame, volume: pd.Series, period: int) -> pd.Series:
    typical = (df["high"].astype(float) + df["low"].astype(float) + df["close"].astype(float)) / 3
    flow = typical * volume
    pos = flow.where(typical.diff() > 0, 0.0).rolling(period).sum()
    neg = flow.where(typical.diff() < 0, 0.0).abs().rolling(period).sum()
    return 100 - (100 / (1 + pos / (neg + 1e-12)))


def _ad_line(df: pd.DataFrame, volume: pd.Series) -> pd.Series:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    clv = ((close - low) - (high - close)) / ((high - low) + 1e-12)
    return (clv * volume).cumsum()


def _cho(ad_line: pd.Series, fast: int = 3, slow: int = 10) -> pd.Series:
    return ad_line.ewm(span=fast, adjust=False).mean() - ad_line.ewm(span=slow, adjust=False).mean()


def _pvt(close: pd.Series, volume: pd.Series) -> pd.Series:
    return (close.pct_change().fillna(0.0) * volume).cumsum()


def _fractals(df: pd.DataFrame, left: int, right: int) -> tuple[pd.Series, pd.Series]:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    fh = pd.Series(0, index=df.index, dtype=int)
    fl = pd.Series(0, index=df.index, dtype=int)
    for i in range(left, len(df) - right):
        if high.iloc[i] >= high.iloc[i - left:i + right + 1].max():
            fh.iloc[i + right] = 1
        if low.iloc[i] <= low.iloc[i - left:i + right + 1].min():
            fl.iloc[i + right] = 1
    return fh, fl


def _cci(df: pd.DataFrame, period: int = 20) -> pd.Series:
    typical = (df["high"].astype(float) + df["low"].astype(float) + df["close"].astype(float)) / 3
    mean = typical.rolling(period).mean()
    mad = (typical - mean).abs().rolling(period).mean()
    return (typical - mean) / (0.015 * mad + 1e-12)


def _stochastic(df: pd.DataFrame, period: int = 14, d_period: int = 3) -> tuple[pd.Series, pd.Series]:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    k = 100 * (close - low.rolling(period).min()) / ((high.rolling(period).max() - low.rolling(period).min()) + 1e-12)
    return k, k.rolling(d_period).mean()


def _wpr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"].astype(float).rolling(period).max()
    low = df["low"].astype(float).rolling(period).min()
    close = df["close"].astype(float)
    return -100 * (high - close) / ((high - low) + 1e-12)


def _demarker(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    demax = (high - high.shift(1)).clip(lower=0)
    demin = (low.shift(1) - low).clip(lower=0)
    return demax.rolling(period).mean() / ((demax.rolling(period).mean() + demin.rolling(period).mean()) + 1e-12)


def _dpo(close: pd.Series, period: int = 20) -> pd.Series:
    shift = int(period / 2 + 1)
    return close.shift(shift) - close.rolling(period).mean()


def _kama(close: pd.Series, period: int = 10, fast: int = 2, slow: int = 30) -> pd.Series:
    change = (close - close.shift(period)).abs()
    volatility = close.diff().abs().rolling(period).sum()
    er = change / (volatility + 1e-12)
    sc = (er * (2 / (fast + 1) - 2 / (slow + 1)) + 2 / (slow + 1)) ** 2
    out = close.copy().astype(float)
    for i in range(1, len(close)):
        out.iloc[i] = out.iloc[i - 1] + float(sc.iloc[i] if np.isfinite(sc.iloc[i]) else 0.0) * (close.iloc[i] - out.iloc[i - 1])
    return out


def _vidya(close: pd.Series, period: int = 20) -> pd.Series:
    momentum = close.diff()
    up = momentum.clip(lower=0).rolling(period).sum()
    down = (-momentum.clip(upper=0)).rolling(period).sum()
    cmo = ((up - down).abs() / ((up + down) + 1e-12)).fillna(0.0)
    alpha = 2 / (period + 1)
    out = close.copy().astype(float)
    for i in range(1, len(close)):
        out.iloc[i] = out.iloc[i - 1] + alpha * float(cmo.iloc[i]) * (close.iloc[i] - out.iloc[i - 1])
    return out


def _frama_proxy(close: pd.Series, period: int = 20) -> pd.Series:
    er = (close - close.shift(period)).abs() / (close.diff().abs().rolling(period).sum() + 1e-12)
    alpha = er.clip(0.01, 1.0)
    out = close.copy().astype(float)
    for i in range(1, len(close)):
        out.iloc[i] = out.iloc[i - 1] + float(alpha.iloc[i] if np.isfinite(alpha.iloc[i]) else 0.01) * (close.iloc[i] - out.iloc[i - 1])
    return out



def _parabolic_sar(df: pd.DataFrame, step: float = 0.02, max_step: float = 0.2) -> pd.Series:
    high = df["high"].astype(float).reset_index(drop=True)
    low = df["low"].astype(float).reset_index(drop=True)
    close = df["close"].astype(float).reset_index(drop=True)
    if len(df) == 0:
        return pd.Series(dtype=float, index=df.index)
    sar = pd.Series(np.nan, index=df.index, dtype=float)
    uptrend = True
    af = step
    ep = high.iloc[0]
    sar.iloc[0] = low.iloc[0]
    if len(df) > 1:
        uptrend = close.iloc[1] >= close.iloc[0]
        ep = high.iloc[1] if uptrend else low.iloc[1]
        sar.iloc[1] = low.iloc[0] if uptrend else high.iloc[0]
    for i in range(2, len(df)):
        prev_sar = sar.iloc[i - 1]
        if uptrend:
            value = prev_sar + af * (ep - prev_sar)
            value = min(value, low.iloc[i - 1], low.iloc[i - 2])
            if low.iloc[i] < value:
                uptrend = False
                value = ep
                ep = low.iloc[i]
                af = step
            else:
                if high.iloc[i] > ep:
                    ep = high.iloc[i]
                    af = min(max_step, af + step)
        else:
            value = prev_sar + af * (ep - prev_sar)
            value = max(value, high.iloc[i - 1], high.iloc[i - 2])
            if high.iloc[i] > value:
                uptrend = True
                value = ep
                ep = high.iloc[i]
                af = step
            else:
                if low.iloc[i] < ep:
                    ep = low.iloc[i]
                    af = min(max_step, af + step)
        sar.iloc[i] = value
    return sar

def build_pattern_state_features(df: pd.DataFrame, config: PatternStateConfig | None = None) -> pd.DataFrame:
    config = config or PatternStateConfig()
    if df is None or df.empty:
        return pd.DataFrame()
    data = df.copy()
    if "date" in data.columns and "time" not in data.columns:
        data["time"] = data["date"]
    if "time" in data.columns:
        data["time"] = pd.to_datetime(data["time"])
    else:
        data["time"] = pd.RangeIndex(len(data))
    data = data.sort_values("time").reset_index(drop=True)
    for col in ("open", "high", "low", "close"):
        data[col] = data[col].astype(float)

    open_ = data["open"]
    high = data["high"]
    low = data["low"]
    close = data["close"]
    volume = _volume(data)
    tr = _true_range(data)
    atr = tr.rolling(config.atr_period).mean()
    atr_ma = atr.rolling(50).mean()
    adx, plus_di, minus_di = _adx(data, config.adx_period)
    rsi = _rsi(close, config.rsi_period)
    macd, macd_signal, osma = _macd(close)
    obv = _obv(close, volume)
    mfi = _mfi(data, volume, config.mfi_period)
    ad = _ad_line(data, volume)
    cho = _cho(ad)
    pvt = _pvt(close, volume)

    bb_mid = close.rolling(config.bb_period).mean()
    bb_std = close.rolling(config.bb_period).std()
    bb_upper = bb_mid + config.bb_std_mult * bb_std
    bb_lower = bb_mid - config.bb_std_mult * bb_std
    bb_width = (bb_upper - bb_lower) / (bb_mid.abs() + 1e-12)
    bb_percentile = bb_width.rolling(config.squeeze_lookback).rank(pct=True)
    price_channel_high = high.rolling(config.price_channel_period).max().shift(1)
    price_channel_low = low.rolling(config.price_channel_period).min().shift(1)
    stddev = close.pct_change().rolling(config.bb_period).std()
    stddev_percentile = stddev.rolling(config.squeeze_lookback).rank(pct=True)
    vroc = volume.pct_change(config.volume_lookback) * 100
    volume_ratio = volume / (volume.rolling(config.volume_lookback).mean() + 1e-12)

    fractal_high, fractal_low = _fractals(data, config.fractal_left, config.fractal_right)
    swing_high = high.where(fractal_high.astype(bool)).ffill()
    swing_low = low.where(fractal_low.astype(bool)).ffill()

    cci = _cci(data)
    stoch_k, stoch_d = _stochastic(data)
    wpr = _wpr(data)
    demarker = _demarker(data)
    dpo = _dpo(close)

    kama = _kama(close, config.adaptive_period)
    vidya = _vidya(close, config.adaptive_period)
    frama = _frama_proxy(close, config.adaptive_period)
    ema = close.ewm(span=config.adaptive_period, adjust=False).mean()
    dema = 2 * ema - ema.ewm(span=config.adaptive_period, adjust=False).mean()
    tema = 3 * ema - 3 * ema.ewm(span=config.adaptive_period, adjust=False).mean() + ema.ewm(span=config.adaptive_period, adjust=False).mean().ewm(span=config.adaptive_period, adjust=False).mean()

    tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2
    kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2
    span_a = ((tenkan + kijun) / 2).shift(26)
    span_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)

    median = (high + low) / 2
    jaw = median.ewm(alpha=1 / 13, adjust=False).mean().shift(8)
    teeth = median.ewm(alpha=1 / 8, adjust=False).mean().shift(5)
    lips = median.ewm(alpha=1 / 5, adjust=False).mean().shift(3)
    ao = median.rolling(5).mean() - median.rolling(34).mean()
    ac = ao - ao.rolling(5).mean()
    gator_upper = (jaw - teeth).abs()
    gator_lower = -(teeth - lips).abs()
    bw_zone = pd.Series(np.select([(ao > ao.shift(1)) & (ac > ac.shift(1)), (ao < ao.shift(1)) & (ac < ac.shift(1))], ["green", "red"], default="gray"), index=data.index)
    psar = _parabolic_sar(data)

    chv = ((high - low).ewm(span=10, adjust=False).mean().pct_change(10)) * 100
    mass_single = (high - low).ewm(span=9, adjust=False).mean()
    mass_double = mass_single.ewm(span=9, adjust=False).mean()
    mass_index = (mass_single / (mass_double + 1e-12)).rolling(25).sum()

    out = pd.DataFrame({
        "time": data["time"],
        "open": open_, "high": high, "low": low, "close": close,
        "volume": volume,
        "adx": adx, "plus_di": plus_di, "minus_di": minus_di,
        "atr": atr, "atr_ma50": atr_ma, "atr_ratio": atr / (atr_ma + 1e-12),
        "bb_mid": bb_mid, "bb_upper": bb_upper, "bb_lower": bb_lower, "bb_width": bb_width, "bb_width_percentile": bb_percentile,
        "stddev": stddev, "stddev_percentile": stddev_percentile,
        "rsi": rsi, "macd": macd, "macd_signal": macd_signal, "osma": osma,
        "obv": obv, "mfi": mfi, "ad": ad, "cho": cho, "pvt": pvt, "vroc": vroc, "volume_ratio": volume_ratio,
        "price_channel_high": price_channel_high, "price_channel_low": price_channel_low,
        "fractal_high_confirmed": fractal_high, "fractal_low_confirmed": fractal_low,
        "last_fractal_high": swing_high, "last_fractal_low": swing_low,
        "cci": cci, "stoch_k": stoch_k, "stoch_d": stoch_d, "wpr": wpr, "demarker": demarker, "dpo": dpo,
        "ama": kama, "frama": frama, "vidya": vidya, "dema": dema, "tema": tema,
        "tenkan": tenkan, "kijun": kijun, "ichimoku_span_a": span_a, "ichimoku_span_b": span_b,
        "alligator_jaw": jaw, "alligator_teeth": teeth, "alligator_lips": lips,
        "awesome_oscillator": ao, "accelerator_oscillator": ac, "gator_upper": gator_upper, "gator_lower": gator_lower, "bw_zone_trade": bw_zone,
        "parabolic_sar": psar,
        "chv": chv, "mass_index": mass_index,
    })

    compression = (out["bb_width_percentile"] <= 0.25) & (out["stddev_percentile"] <= 0.35) & (out["atr_ratio"] <= 0.90)
    expansion = (out["atr_ratio"] >= 1.15) | (out["bb_width"] > out["bb_width"].shift(3))
    trend_up = (out["adx"] >= 22) & (out["plus_di"] > out["minus_di"]) & (close > close.ewm(span=50, adjust=False).mean())
    trend_down = (out["adx"] >= 22) & (out["minus_di"] > out["plus_di"]) & (close < close.ewm(span=50, adjust=False).mean())
    lateral = (out["adx"] < 18) & ~compression
    out["regime"] = np.select([compression, trend_up | trend_down, expansion, lateral], ["compressao", "tendencia", "expansao", "lateral"], default="indefinido")

    breakout_up = close > out["price_channel_high"]
    breakout_down = close < out["price_channel_low"]
    pullback_up = trend_up & (out["rsi"].between(40, 55)) & (close > close.ewm(span=50, adjust=False).mean())
    pullback_down = trend_down & (out["rsi"].between(45, 60)) & (close < close.ewm(span=50, adjust=False).mean())
    out["estrutura"] = np.select(
        [breakout_up, breakout_down, out["fractal_high_confirmed"] == 1, out["fractal_low_confirmed"] == 1, pullback_up | pullback_down],
        ["rompimento_alta", "rompimento_baixa", "topo_confirmado", "fundo_confirmado", "pullback"],
        default="neutra",
    )

    osma_up = out["osma"] > out["osma"].shift(1)
    osma_down = out["osma"] < out["osma"].shift(1)
    out["momentum"] = np.select(
        [(out["osma"] > 0) & osma_up, (out["osma"] < 0) & osma_down, (close.diff() > 0) & osma_down, (close.diff() < 0) & osma_up],
        ["acelerando_alta", "acelerando_baixa", "perdendo_forca_alta", "perdendo_forca_baixa"],
        default="neutro",
    )

    obv_slope = out["obv"].diff(5)
    ad_slope = out["ad"].diff(5)
    price_slope = close.diff(5)
    out["volume_state"] = np.select(
        [(price_slope > 0) & (obv_slope > 0) & (ad_slope > 0), (price_slope < 0) & (obv_slope < 0) & (ad_slope < 0), (price_slope > 0) & ((obv_slope < 0) | (ad_slope < 0)), (price_slope < 0) & ((obv_slope > 0) | (ad_slope > 0))],
        ["confirma_alta", "confirma_baixa", "diverge_alta", "diverge_baixa"],
        default="neutro",
    )

    out["volatilidade"] = np.select(
        [compression, out["atr_ratio"] >= 1.35, out["atr_ratio"] >= 1.10, out["atr_ratio"] <= 0.85],
        ["baixa_compressao", "extrema", "subindo", "baixa"],
        default="normal",
    )

    out["pattern_key"] = out[["regime", "estrutura", "momentum", "volume_state", "volatilidade"]].astype(str).agg("|".join, axis=1)


    # Scores 3/3: contexto + gatilho + filtro. Esses campos servem para mineracao historica
    # e para entrada operacional conservadora via strategy14.
    cloud_top = pd.concat([out["ichimoku_span_a"], out["ichimoku_span_b"]], axis=1).max(axis=1)
    cloud_bottom = pd.concat([out["ichimoku_span_a"], out["ichimoku_span_b"]], axis=1).min(axis=1)
    osma_cross_up = (out["osma"] > 0) & (out["osma"].shift(1) <= 0)
    osma_cross_down = (out["osma"] < 0) & (out["osma"].shift(1) >= 0)
    adx_strong_rising = (out["adx"] >= 25) & (out["adx"] > out["adx"].shift(1))
    ichimoku_context_buy = close > cloud_top
    ichimoku_context_sell = close < cloud_bottom
    out["score_trend_ichimoku_buy"] = ichimoku_context_buy.astype(int) + osma_cross_up.astype(int) + adx_strong_rising.astype(int)
    out["score_trend_ichimoku_sell"] = ichimoku_context_sell.astype(int) + osma_cross_down.astype(int) + adx_strong_rising.astype(int)

    alligator_spread = (out["alligator_lips"] - out["alligator_jaw"]).abs() / (close.abs() + 1e-12)
    alligator_open = alligator_spread >= 0.0005
    alligator_buy = (out["alligator_lips"] > out["alligator_teeth"]) & (out["alligator_teeth"] > out["alligator_jaw"]) & alligator_open
    alligator_sell = (out["alligator_lips"] < out["alligator_teeth"]) & (out["alligator_teeth"] < out["alligator_jaw"]) & alligator_open
    bw_green = (out["awesome_oscillator"] > out["awesome_oscillator"].shift(1)) & (out["accelerator_oscillator"] > out["accelerator_oscillator"].shift(1)) & (out["bw_zone_trade"] == "green")
    bw_red = (out["awesome_oscillator"] < out["awesome_oscillator"].shift(1)) & (out["accelerator_oscillator"] < out["accelerator_oscillator"].shift(1)) & (out["bw_zone_trade"] == "red")
    fractal_break_buy = close > out["last_fractal_high"]
    fractal_break_sell = close < out["last_fractal_low"]
    out["score_trend_bill_williams_buy"] = alligator_buy.astype(int) + bw_green.astype(int) + fractal_break_buy.astype(int)
    out["score_trend_bill_williams_sell"] = alligator_sell.astype(int) + bw_red.astype(int) + fractal_break_sell.astype(int)

    adaptive_context_buy = (out["frama"] > out["frama"].shift(3)) | (out["vidya"] > out["vidya"].shift(3))
    adaptive_context_sell = (out["frama"] < out["frama"].shift(3)) | (out["vidya"] < out["vidya"].shift(3))
    fast_cross_buy = ((out["tema"] > out["frama"]) & (out["tema"].shift(1) <= out["frama"].shift(1))) | ((out["dema"] > out["vidya"]) & (out["dema"].shift(1) <= out["vidya"].shift(1)))
    fast_cross_sell = ((out["tema"] < out["frama"]) & (out["tema"].shift(1) >= out["frama"].shift(1))) | ((out["dema"] < out["vidya"]) & (out["dema"].shift(1) >= out["vidya"].shift(1)))
    psar_buy = close > out["parabolic_sar"]
    psar_sell = close < out["parabolic_sar"]
    out["score_trend_adaptive_buy"] = adaptive_context_buy.astype(int) + fast_cross_buy.astype(int) + psar_buy.astype(int)
    out["score_trend_adaptive_sell"] = adaptive_context_sell.astype(int) + fast_cross_sell.astype(int) + psar_sell.astype(int)

    outside_lower = close <= out["bb_lower"]
    outside_upper = close >= out["bb_upper"]
    osc_reclaim_buy = ((out["rsi"] > 30) & (out["rsi"].shift(1) <= 30)) | ((out["stoch_k"] > 20) & (out["stoch_k"].shift(1) <= 20)) | ((out["wpr"] > -80) & (out["wpr"].shift(1) <= -80))
    osc_reclaim_sell = ((out["rsi"] < 70) & (out["rsi"].shift(1) >= 70)) | ((out["stoch_k"] < 80) & (out["stoch_k"].shift(1) >= 80)) | ((out["wpr"] < -20) & (out["wpr"].shift(1) >= -20))
    flow_div_buy = (close < close.shift(5)) & ((out["mfi"] > out["mfi"].shift(5)) | (out["cho"] > out["cho"].shift(5)))
    flow_div_sell = (close > close.shift(5)) & ((out["mfi"] < out["mfi"].shift(5)) | (out["cho"] < out["cho"].shift(5)))
    out["score_mean_reversion_flow_buy"] = outside_lower.astype(int) + osc_reclaim_buy.astype(int) + flow_div_buy.astype(int)
    out["score_mean_reversion_flow_sell"] = outside_upper.astype(int) + osc_reclaim_sell.astype(int) + flow_div_sell.astype(int)

    dpo_extreme_buy = out["dpo"] <= out["dpo"].rolling(80).quantile(0.10)
    dpo_extreme_sell = out["dpo"] >= out["dpo"].rolling(80).quantile(0.90)
    cci_reclaim_buy = (out["cci"] > -200) & (out["cci"].shift(1) <= -200)
    cci_reclaim_sell = (out["cci"] < 200) & (out["cci"].shift(1) >= 200)
    demarker_buy = (out["demarker"] > 0.30) & (out["demarker"].shift(1) <= 0.30)
    demarker_sell = (out["demarker"] < 0.70) & (out["demarker"].shift(1) >= 0.70)
    out["score_mean_reversion_cycle_buy"] = dpo_extreme_buy.astype(int) + cci_reclaim_buy.astype(int) + demarker_buy.astype(int)
    out["score_mean_reversion_cycle_sell"] = dpo_extreme_sell.astype(int) + cci_reclaim_sell.astype(int) + demarker_sell.astype(int)

    squeeze_context = (out["bb_width_percentile"] <= 0.20) & (out["stddev_percentile"] <= 0.25)
    channel_break_buy = close > out["price_channel_high"]
    channel_break_sell = close < out["price_channel_low"]
    volume_burst = (out["volume_ratio"] >= 1.40) | (out["vroc"] >= 30)
    out["score_breakout_squeeze_buy"] = squeeze_context.shift(1, fill_value=False).astype(bool).astype(int) + channel_break_buy.astype(int) + volume_burst.astype(int)
    out["score_breakout_squeeze_sell"] = squeeze_context.shift(1, fill_value=False).astype(bool).astype(int) + channel_break_sell.astype(int) + volume_burst.astype(int)

    lateral_price = ((close - close.shift(10)).abs() / (out["atr"] + 1e-12)) <= 1.0
    accumulation_buy = lateral_price & (out["obv"] > out["obv"].shift(10)) & (out["ad"] > out["ad"].shift(10))
    distribution_sell = lateral_price & (out["obv"] < out["obv"].shift(10)) & (out["ad"] < out["ad"].shift(10))
    chv_expanding = out["chv"] > out["chv"].shift(3)
    out["score_breakout_pressure_buy"] = accumulation_buy.astype(int) + fractal_break_buy.astype(int) + chv_expanding.astype(int)
    out["score_breakout_pressure_sell"] = distribution_sell.astype(int) + fractal_break_sell.astype(int) + chv_expanding.astype(int)


    # Scores derivados do anexo de estrategias classicas: tendencia, breakout,
    # reversao a media, price action e sessao. Todos seguem 3/3.
    ema9 = close.ewm(span=9, adjust=False).mean()
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    ema200 = close.ewm(span=200, adjust=False).mean()
    body = (close - open_).abs()
    candle_range = (high - low).replace(0, np.nan)
    body_to_range = body / (candle_range + 1e-12)
    close_position = (close - low) / (candle_range + 1e-12)
    upper_wick = high - pd.concat([open_, close], axis=1).max(axis=1)
    lower_wick = pd.concat([open_, close], axis=1).min(axis=1) - low
    bullish_pin = (lower_wick / (candle_range + 1e-12) >= 0.45) & (close_position >= 0.55)
    bearish_pin = (upper_wick / (candle_range + 1e-12) >= 0.45) & (close_position <= 0.45)
    bullish_engulf = (close > open_) & (close.shift(1) < open_.shift(1)) & (close >= open_.shift(1)) & (open_ <= close.shift(1))
    bearish_engulf = (close < open_) & (close.shift(1) > open_.shift(1)) & (close <= open_.shift(1)) & (open_ >= close.shift(1))
    bullish_reversal_candle = bullish_pin | bullish_engulf
    bearish_reversal_candle = bearish_pin | bearish_engulf
    ema9_cross_up = (ema9 > ema21) & (ema9.shift(1) <= ema21.shift(1))
    ema9_cross_down = (ema9 < ema21) & (ema9.shift(1) >= ema21.shift(1))
    ema_fast_slope_up = (ema9 > ema9.shift(3)) & (ema21 > ema21.shift(3))
    ema_fast_slope_down = (ema9 < ema9.shift(3)) & (ema21 < ema21.shift(3))
    ema200_buy = close > ema200
    ema200_sell = close < ema200
    out["score_trend_ema_cross_buy"] = ema9_cross_up.astype(int) + ema_fast_slope_up.astype(int) + ema200_buy.astype(int)
    out["score_trend_ema_cross_sell"] = ema9_cross_down.astype(int) + ema_fast_slope_down.astype(int) + ema200_sell.astype(int)

    higher_highs = (out["last_fractal_high"] > out["last_fractal_high"].shift(10))
    higher_lows = (out["last_fractal_low"] > out["last_fractal_low"].shift(10))
    lower_highs = (out["last_fractal_high"] < out["last_fractal_high"].shift(10))
    lower_lows = (out["last_fractal_low"] < out["last_fractal_low"].shift(10))
    trend_structure_buy = higher_highs & higher_lows & ema200_buy
    trend_structure_sell = lower_highs & lower_lows & ema200_sell
    pullback_ema_buy = (low <= ema21) | (low <= ema50)
    pullback_ema_sell = (high >= ema21) | (high >= ema50)
    small_bos_buy = close > high.rolling(5).max().shift(1)
    small_bos_sell = close < low.rolling(5).min().shift(1)
    out["score_trend_pullback_price_action_buy"] = trend_structure_buy.astype(int) + pullback_ema_buy.astype(int) + (bullish_reversal_candle | small_bos_buy).astype(int)
    out["score_trend_pullback_price_action_sell"] = trend_structure_sell.astype(int) + pullback_ema_sell.astype(int) + (bearish_reversal_candle | small_bos_sell).astype(int)

    range_width_atr = (out["price_channel_high"] - out["price_channel_low"]) / (out["atr"] + 1e-12)
    range_context = ((out["adx"] < 20) | (out["bb_width_percentile"] <= 0.35)) & (range_width_atr <= 4.0)
    strong_breakout_candle = (body_to_range >= 0.55) & ((out["volume_ratio"] >= 1.15) | (out["vroc"] >= 20))
    out["score_breakout_range_buy"] = range_context.shift(1, fill_value=False).astype(bool).astype(int) + channel_break_buy.astype(int) + strong_breakout_candle.astype(int)
    out["score_breakout_range_sell"] = range_context.shift(1, fill_value=False).astype(bool).astype(int) + channel_break_sell.astype(int) + strong_breakout_candle.astype(int)

    day_key = pd.to_datetime(out["time"]).dt.date if np.issubdtype(pd.to_datetime(out["time"]).dtype, np.datetime64) else pd.Series(0, index=out.index)
    prior_day_high = high.groupby(day_key).cummax().shift(1)
    prior_day_low = low.groupby(day_key).cummin().shift(1)
    day_break_buy = close > prior_day_high
    day_break_sell = close < prior_day_low
    retest_day_high_buy = (low <= prior_day_high) & (close > prior_day_high)
    retest_day_low_sell = (high >= prior_day_low) & (close < prior_day_low)
    out["score_breakout_day_high_low_buy"] = ema200_buy.astype(int) + day_break_buy.astype(int) + (strong_breakout_candle | retest_day_high_buy).astype(int)
    out["score_breakout_day_high_low_sell"] = ema200_sell.astype(int) + day_break_sell.astype(int) + (strong_breakout_candle | retest_day_low_sell).astype(int)

    bb_reentry_buy = (close.shift(1) < out["bb_lower"].shift(1)) & (close > out["bb_lower"])
    bb_reentry_sell = (close.shift(1) > out["bb_upper"].shift(1)) & (close < out["bb_upper"])
    out["score_mean_reversion_bollinger_reentry_buy"] = outside_lower.shift(1, fill_value=False).astype(bool).astype(int) + bb_reentry_buy.astype(int) + (out["adx"] < 24).astype(int)
    out["score_mean_reversion_bollinger_reentry_sell"] = outside_upper.shift(1, fill_value=False).astype(bool).astype(int) + bb_reentry_sell.astype(int) + (out["adx"] < 24).astype(int)

    near_support = ((close - out["price_channel_low"]).abs() / (out["atr"] + 1e-12) <= 0.35) | (out["fractal_low_confirmed"] == 1)
    near_resistance = ((out["price_channel_high"] - close).abs() / (out["atr"] + 1e-12) <= 0.35) | (out["fractal_high_confirmed"] == 1)
    out["score_mean_reversion_rsi_sr_buy"] = near_support.astype(int) + (out["rsi"] <= 30).astype(int) + bullish_reversal_candle.astype(int)
    out["score_mean_reversion_rsi_sr_sell"] = near_resistance.astype(int) + (out["rsi"] >= 70).astype(int) + bearish_reversal_candle.astype(int)

    ema_flat = (ema20.diff(10).abs() / (out["atr"] + 1e-12) <= 0.35) | (out["adx"] < 18)
    far_below_ema = ((ema20 - close) / (out["atr"] + 1e-12) >= 2.0) | ((ema50 - close) / (out["atr"] + 1e-12) >= 2.0)
    far_above_ema = ((close - ema20) / (out["atr"] + 1e-12) >= 2.0) | ((close - ema50) / (out["atr"] + 1e-12) >= 2.0)
    out["score_mean_reversion_ema_extension_buy"] = ema_flat.astype(int) + far_below_ema.astype(int) + bullish_reversal_candle.astype(int)
    out["score_mean_reversion_ema_extension_sell"] = ema_flat.astype(int) + far_above_ema.astype(int) + bearish_reversal_candle.astype(int)

    range_support_buy = range_context & near_support
    range_resistance_sell = range_context & near_resistance
    stoch_reclaim_buy = (out["stoch_k"] > 20) & (out["stoch_k"].shift(1) <= 20)
    stoch_reject_sell = (out["stoch_k"] < 80) & (out["stoch_k"].shift(1) >= 80)
    out["score_range_oscillator_buy"] = range_support_buy.astype(int) + (out["rsi"] <= 35).astype(int) + stoch_reclaim_buy.astype(int)
    out["score_range_oscillator_sell"] = range_resistance_sell.astype(int) + (out["rsi"] >= 65).astype(int) + stoch_reject_sell.astype(int)

    false_break_up = (high > out["price_channel_high"]) & (close < out["price_channel_high"])
    false_break_down = (low < out["price_channel_low"]) & (close > out["price_channel_low"])
    out["score_price_action_false_break_buy"] = range_context.astype(int) + false_break_down.astype(int) + bullish_reversal_candle.astype(int)
    out["score_price_action_false_break_sell"] = range_context.astype(int) + false_break_up.astype(int) + bearish_reversal_candle.astype(int)

    hour = pd.to_datetime(out["time"], errors="coerce").dt.hour
    london_ny = hour.between(7, 20, inclusive="both")
    out["score_session_london_ny_breakout_buy"] = london_ny.astype(int) + ema200_buy.astype(int) + (channel_break_buy & strong_breakout_candle).astype(int)
    out["score_session_london_ny_breakout_sell"] = london_ny.astype(int) + ema200_sell.astype(int) + (channel_break_sell & strong_breakout_candle).astype(int)

    buy_score_cols = [col for col in out.columns if col.startswith("score_") and col.endswith("_buy")]
    sell_score_cols = [col for col in out.columns if col.startswith("score_") and col.endswith("_sell")]
    out["best_pattern_buy_score"] = out[buy_score_cols].max(axis=1)
    out["best_pattern_sell_score"] = out[sell_score_cols].max(axis=1)
    out["best_pattern_buy"] = out[buy_score_cols].idxmax(axis=1).str.replace("score_", "", regex=False).str.replace("_buy", "", regex=False)
    out["best_pattern_sell"] = out[sell_score_cols].idxmax(axis=1).str.replace("score_", "", regex=False).str.replace("_sell", "", regex=False)
    out["pattern_score_signal"] = np.select(
        [(out["best_pattern_buy_score"] >= 3) & (out["best_pattern_buy_score"] >= out["best_pattern_sell_score"]), (out["best_pattern_sell_score"] >= 3)],
        [1, 2],
        default=0,
    )
    out["pattern_score_name"] = np.select(
        [out["pattern_score_signal"] == 1, out["pattern_score_signal"] == 2],
        [out["best_pattern_buy"], out["best_pattern_sell"]],
        default="none",
    )

    out["setup_breakout_compressao"] = (compression.shift(1, fill_value=False).astype(bool) & (breakout_up | breakout_down) & (out["adx"] > out["adx"].shift(1)) & (out["atr"] > out["atr"].shift(1)) & ((out["volume_state"].str.startswith("confirma")) | (out["vroc"] > 20))).astype(int)
    out["setup_tendencia_pullback"] = ((pullback_up & (out["stoch_k"] > out["stoch_d"])) | (pullback_down & (out["stoch_k"] < out["stoch_d"]))).astype(int)
    out["setup_reversao_divergencia_proxy"] = (((close > close.shift(5)) & (out["rsi"] < out["rsi"].shift(5)) & (out["volume_state"] == "diverge_alta")) | ((close < close.shift(5)) & (out["rsi"] > out["rsi"].shift(5)) & (out["volume_state"] == "diverge_baixa"))).astype(int)
    out["setup_bill_williams_expansao"] = (((out["alligator_lips"] > out["alligator_teeth"]) & (out["alligator_teeth"] > out["alligator_jaw"]) & (out["awesome_oscillator"] > 0) & (out["accelerator_oscillator"] > 0)) | ((out["alligator_lips"] < out["alligator_teeth"]) & (out["alligator_teeth"] < out["alligator_jaw"]) & (out["awesome_oscillator"] < 0) & (out["accelerator_oscillator"] < 0))).astype(int)
    return out.replace([np.inf, -np.inf], np.nan)


def summarize_pattern_states(frame: pd.DataFrame, top: int = 20) -> dict[str, Any]:
    if frame.empty:
        return {"rows": 0}
    setup_cols = [col for col in frame.columns if col.startswith("setup_")]
    return {
        "rows": int(len(frame)),
        "from": str(frame["time"].min()) if "time" in frame.columns else "",
        "to": str(frame["time"].max()) if "time" in frame.columns else "",
        "regime_counts": frame["regime"].value_counts(dropna=False).to_dict() if "regime" in frame.columns else {},
        "top_patterns": frame["pattern_key"].value_counts(dropna=False).head(top).to_dict() if "pattern_key" in frame.columns else {},
        "setup_counts": {col: int(frame[col].fillna(0).sum()) for col in setup_cols},
    }
