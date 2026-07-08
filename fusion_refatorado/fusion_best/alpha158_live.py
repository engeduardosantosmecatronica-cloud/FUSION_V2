# nexus/features/alpha158_live.py
"""
Feature calculation engine — pure Alpha158 features from MT5 live data.

No model loading here. Features are returned as a DataFrame ready for
any model in the registry to consume.

Usage:
    from nexus.features.alpha158_live import get_alpha158_live_features, get_alpha158_live_unscaled
    df = get_alpha158_live_unscaled("EURUSD")       # raw DataFrame
    scaled = registry.scale_features(df, "EURUSD")  # scaled for a specific model
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict

_CACHE = {}


def _init_mt5():
    import MetaTrader5 as mt5

    if not mt5.initialize():
        raise RuntimeError("Falha ao inicializar MT5")
    return mt5


def fetch_mt5_data(instrument: str, lookback_bars: int = 700) -> pd.DataFrame:
    """Fetch raw OHLCV data from MT5 (M5 timeframe)."""
    mt5 = _init_mt5()
    rates = mt5.copy_rates_from_pos(instrument, mt5.TIMEFRAME_M5, 0, lookback_bars)
    if rates is None or len(rates) < 100:
        raise ValueError(f"Dados insuficientes do MT5 para {instrument}")

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df = df.sort_values("time").reset_index(drop=True)

    tick = mt5.symbol_info_tick(instrument)
    if tick is not None and tick.last > 0:
        idx = df.index[-1]
        df.loc[idx, "close"] = tick.last
        if tick.last > df.loc[idx, "high"]:
            df.loc[idx, "high"] = tick.last
        if tick.last < df.loc[idx, "low"]:
            df.loc[idx, "low"] = tick.last

    return df


def calculate_alpha158_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate 144 Alpha158 features from OHLCV DataFrame.
    Columns expected: open, high, low, close, (tick_volume or volume)
    """
    df = df.copy()
    for col in ["open", "high", "low", "close"]:
        if col not in df.columns and col.upper() in df.columns:
            df[col] = df[col.upper()]

    vol_col = "tick_volume" if "tick_volume" in df.columns else "volume"
    if vol_col not in df.columns:
        df["volume"] = 1
        vol_col = "volume"

    ret = df["close"].pct_change()
    vol_ret = df[vol_col].pct_change()

    f = {}

    # KBAR (12)
    f["KMID"] = (df["close"] - df["open"]) / df["open"]
    f["KLEN"] = (df["high"] - df["low"]) / df["open"]
    f["KMID2"] = ((df["close"] - df["open"]) / df["open"]) ** 2
    f["KUP"] = (df["high"] - df[["open", "close"]].max(axis=1)) / df["open"]
    f["KUP2"] = f["KUP"] ** 2
    f["KLOW"] = (df[["open", "close"]].min(axis=1) - df["low"]) / df["open"]
    f["KLOW2"] = f["KLOW"] ** 2
    f["KSFT"] = np.sign(df["close"] - df["open"]) * f["KLEN"]
    f["KSFT2"] = f["KSFT"] ** 2
    f["OPEN0"] = df["open"] / df["open"] - 1
    f["HIGH0"] = (df["high"] / df["open"]) - 1
    f["LOW0"] = (df["low"] / df["open"]) - 1

    # ROC (5)
    for n in [5, 10, 20, 30, 60]:
        f[f"ROC{n}"] = df["close"].pct_change(n)

    # MA (5)
    for n in [5, 10, 20, 30, 60]:
        f[f"MA{n}"] = df["close"].rolling(n).mean()

    # STD (5)
    for n in [5, 10, 20, 30, 60]:
        f[f"STD{n}"] = df["close"].rolling(n).std()

    # BETA (5)
    for n in [5, 10, 20, 30, 60]:
        ma = df["close"].rolling(n).mean()
        market_ret = ma.pct_change()
        f[f"BETA{n}"] = ret.rolling(n).cov(market_ret) / market_ret.rolling(n).var()

    # RSQR (1)
    def _rsqr(series, window):
        result = np.full(len(series), np.nan, dtype=float)
        for i in range(window - 1, len(series)):
            x = np.arange(window)
            y = series.iloc[i - window + 1 : i + 1].values
            if len(y) >= 2:
                corr = np.corrcoef(x, y)[0, 1]
                result[i] = corr ** 2 if not np.isnan(corr) else np.nan
        return pd.Series(result, index=series.index)

    f["RSQR60"] = _rsqr(df["close"], 60)

    # RESI (5)
    for n in [5, 10, 20, 30, 60]:
        ma = df["close"].rolling(n).mean()
        f[f"RESI{n}"] = (df["close"] - ma) / ma

    # MAX / MIN (10)
    for n in [5, 10, 20, 30, 60]:
        f[f"MAX{n}"] = df["close"].rolling(n).max() / df["close"] - 1
        f[f"MIN{n}"] = df["close"].rolling(n).min() / df["close"] - 1

    # QTLU / QTLD (10)
    for n in [5, 10, 20, 30, 60]:
        f[f"QTLU{n}"] = (df["close"].rolling(n).quantile(0.8) - df["close"]) / df["close"]
        f[f"QTLD{n}"] = (df["close"].rolling(n).quantile(0.2) - df["close"]) / df["close"]

    # RANK (5)
    for n in [5, 10, 20, 30, 60]:
        f[f"RANK{n}"] = df["close"].rolling(n).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False
        )

    # RSV (5)
    for n in [5, 10, 20, 30, 60]:
        low_n = df["low"].rolling(n).min()
        high_n = df["high"].rolling(n).max()
        f[f"RSV{n}"] = (df["close"] - low_n) / (high_n - low_n + 1e-8)

    # IMAX / IMIN (10)
    for n in [5, 10, 20, 30, 60]:
        f[f"IMAX{n}"] = df["close"].rolling(n).apply(lambda x: np.argmax(x), raw=False) / n
        f[f"IMIN{n}"] = df["close"].rolling(n).apply(lambda x: np.argmin(x), raw=False) / n

    # IMXD (5)
    for n in [5, 10, 20, 30, 60]:
        f[f"IMXD{n}"] = f[f"IMAX{n}"] - f[f"IMIN{n}"]

    # CORR (1)
    f["CORR60"] = df["close"].rolling(60).corr(df["close"].shift(1))

    # CNT (15)
    for n in [5, 10, 20, 30, 60]:
        f[f"CNTP{n}"] = (ret.rolling(n).apply(lambda x: (x > 0).sum(), raw=False)) / n
        f[f"CNTN{n}"] = (ret.rolling(n).apply(lambda x: (x < 0).sum(), raw=False)) / n
        f[f"CNTD{n}"] = f[f"CNTP{n}"] - f[f"CNTN{n}"]

    # SUM (15)
    for n in [5, 10, 20, 30, 60]:
        f[f"SUMP{n}"] = ret.rolling(n).apply(lambda x: x[x > 0].sum(), raw=False)
        f[f"SUMN{n}"] = ret.rolling(n).apply(lambda x: x[x < 0].sum(), raw=False)
        f[f"SUMD{n}"] = f[f"SUMP{n}"] + f[f"SUMN{n}"]

    # Volume MA (5)
    for n in [5, 10, 20, 30, 60]:
        f[f"VMA{n}"] = df[vol_col].rolling(n).mean()

    # Volume STD (5)
    for n in [5, 10, 20, 30, 60]:
        f[f"VSTD{n}"] = df[vol_col].rolling(n).std()

    # WVMA (5)
    for n in [5, 10, 20, 30, 60]:
        f[f"WVMA{n}"] = (df["close"] * df[vol_col]).rolling(n).sum() / df[vol_col].rolling(n).sum()

    # Volume SUM (15)
    for n in [5, 10, 20, 30, 60]:
        f[f"VSUMP{n}"] = vol_ret.rolling(n).apply(lambda x: x[x > 0].sum(), raw=False)
        f[f"VSUMN{n}"] = vol_ret.rolling(n).apply(lambda x: x[x < 0].sum(), raw=False)
        f[f"VSUMD{n}"] = f[f"VSUMP{n}"] + f[f"VSUMN{n}"]

    features = pd.DataFrame(f, index=df.index)
    features = features.replace([np.inf, -np.inf], np.nan)

    return features


def get_alpha158_live_features(
    instrument: str = "EURUSD",
    lookback_bars: int = 700,
) -> Optional[Dict]:
    """Return Alpha158 features for last candle as a dict."""
    df = fetch_mt5_data(instrument, lookback_bars)
    features_df = calculate_alpha158_features(df)

    last_row = features_df.iloc[-1]
    return {col: float(last_row[col]) if not pd.isna(last_row[col]) else 0.0 for col in last_row.index}


def get_alpha158_live_unscaled(
    instrument: str = "EURUSD",
    lookback_bars: int = 700,
) -> Optional[pd.DataFrame]:
    """Return full Alpha158 DataFrame (last bar only) — ready to be scaled by any model's scaler."""
    df = fetch_mt5_data(instrument, lookback_bars)
    features_df = calculate_alpha158_features(df)

    last_row = features_df.iloc[-1]
    last_time = df["time"].iloc[-1]

    _CACHE["last_candle_time"] = last_time
    _CACHE["last_price"] = df["close"].iloc[-1]

    return pd.DataFrame([last_row])
