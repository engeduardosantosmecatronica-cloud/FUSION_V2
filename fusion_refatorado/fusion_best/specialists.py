from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np
import pandas as pd


class Specialist(Protocol):
    name: str

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        ...


def _volume_col(df: pd.DataFrame) -> str:
    if "volume" in df.columns:
        return "volume"
    if "tick_volume" in df.columns:
        return "tick_volume"
    raise KeyError("DataFrame precisa ter coluna 'volume' ou 'tick_volume'.")


def _true_range(df: pd.DataFrame) -> pd.Series:
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift(1)).abs()
    low_close = (df["low"] - df["close"].shift(1)).abs()
    return pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)


@dataclass
class LiquiditySpecialist:
    name: str = "liquidity"

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        volume = df[_volume_col(df)]
        high_max = df["high"].rolling(20).max()
        low_min = df["low"].rolling(20).min()
        range_30 = df["high"].rolling(30).max() - df["low"].rolling(30).min()
        vol_up = volume.where(df["close"].diff() > 0, 0)
        vol_down = volume.where(df["close"].diff() < 0, 0)
        return pd.DataFrame(
            {
                "liq_range": high_max - low_min,
                "liq_sweep": (df["high"] > high_max.shift(1)).astype(int)
                - (df["low"] < low_min.shift(1)).astype(int),
                "liq_cluster": range_30 / (df["close"] + 1e-12),
                "liq_pressure": vol_up.rolling(20).sum() - vol_down.rolling(20).sum(),
            },
            index=df.index,
        )


@dataclass
class MicrostructureSpecialist:
    name: str = "microstructure"

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        direction = np.sign(df["close"].diff())
        spread = df["spread"] if "spread" in df.columns else pd.Series(0.0, index=df.index)
        up = df["close"].diff().clip(lower=0)
        down = -df["close"].diff().clip(upper=0)
        return pd.DataFrame(
            {
                "spread_norm": spread / (df["close"] + 1e-12),
                "tick_pressure": (direction > 0).rolling(10).sum() - (direction < 0).rolling(10).sum(),
                "micro_vol": df["close"].diff().rolling(10).std(),
                "imbalance": up.rolling(20).sum() - down.rolling(20).sum(),
            },
            index=df.index,
        )


@dataclass
class MomentumSpecialist:
    name: str = "momentum"

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        close = df["close"]
        ret = close.pct_change()
        result = pd.DataFrame(index=df.index)
        for window in (5, 10, 20, 50):
            result[f"mom_{window}"] = close - close.shift(window)
        result["mom_mean"] = result[[c for c in result.columns if c.startswith("mom_")]].mean(axis=1)
        result["mom_std"] = result[[c for c in result.columns if c.startswith("mom_")]].std(axis=1)
        result["mom_norm_10"] = result["mom_10"] / (close.rolling(10).std() + 1e-12)
        result["acc_10"] = result["mom_10"] - result["mom_10"].shift(1)
        result["roc_10"] = (close - close.shift(10)) / (close.shift(10) + 1e-12)
        result["trend_strength_mom"] = result["mom_10"] / (result["mom_50"].abs() + 1e-12)
        impulse = ret.where(ret > 0, 0).rolling(20).sum()
        correction = ret.where(ret < 0, 0).abs().rolling(20).sum()
        result["impulse_ratio"] = impulse / (correction + 1e-12)
        result["momentum_divergence"] = close.diff(5) - close.diff(10)
        return result


@dataclass
class RegimeSpecialist:
    name: str = "regime"

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        vol = df["close"].pct_change().rolling(20).std()
        trend = df["close"].diff(20)
        range_score = (df["high"].rolling(20).max() - df["low"].rolling(20).min()) / (df["close"] + 1e-12)
        vol_ma = vol.rolling(50).mean()
        regime = pd.Series(0, index=df.index, dtype=float)
        regime[(vol < vol_ma) & (trend.abs() < range_score)] = 0
        regime[(trend > 0) & (vol > vol_ma)] = 1
        regime[(trend < 0) & (vol > vol_ma)] = -1
        regime[vol > vol_ma * 2] = 2
        return pd.DataFrame(
            {
                "regime_volatility": vol,
                "regime_trend_score": trend,
                "regime_range_score": range_score,
                "market_regime": regime,
            },
            index=df.index,
        )


@dataclass
class StructureSpecialist:
    left: int = 3
    name: str = "structure"

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        highs = df["high"].to_numpy()
        lows = df["low"].to_numpy()
        pivot_high = np.zeros(len(df))
        pivot_low = np.zeros(len(df))
        for i in range(self.left, len(df)):
            if all(highs[i] > highs[i - j] for j in range(1, self.left + 1)):
                pivot_high[i] = highs[i]
            if all(lows[i] < lows[i - j] for j in range(1, self.left + 1)):
                pivot_low[i] = lows[i]

        last_high = None
        last_low = None
        structure = []
        for ph, pl in zip(pivot_high, pivot_low):
            label = 0
            if ph > 0:
                label = 0 if last_high is None else (1 if ph > last_high else -1)
                last_high = ph
            if pl > 0:
                label = 0 if last_low is None else (2 if pl > last_low else -2)
                last_low = pl
            structure.append(label)

        signal = pd.Series(structure, index=df.index)
        return pd.DataFrame(
            {
                "pivot_high": pivot_high,
                "pivot_low": pivot_low,
                "structure_signal": signal,
                "structure_trend": signal.rolling(10).mean(),
                "structure_strength": signal.rolling(20).apply(lambda x: np.sum(np.abs(x)), raw=True),
                "structure_break": signal.diff().abs().gt(1).astype(int),
            },
            index=df.index,
        )


@dataclass
class VolatilitySpecialist:
    atr_window: int = 14
    regime_window: int = 50
    name: str = "volatility"

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        atr = _true_range(df).rolling(self.atr_window).mean()
        vol_mean = atr.rolling(self.regime_window).mean()
        vol_std = atr.rolling(self.regime_window).std()
        zscore = (atr - vol_mean) / (vol_std + 1e-12)
        regime = pd.Series(0, index=df.index, dtype=int)
        regime[zscore < -1] = 1
        regime[(zscore >= -1) & (zscore < 0.5)] = 2
        regime[(zscore >= 0.5) & (zscore < 1.5)] = 3
        regime[zscore >= 1.5] = 4
        slope = atr.diff()
        squeeze = (zscore < -1).astype(int)
        return pd.DataFrame(
            {
                "atr": atr,
                "vol_mean": vol_mean,
                "vol_std": vol_std,
                "vol_zscore": zscore,
                "volatility_regime": regime,
                "vol_squeeze": squeeze,
                "vol_slope": slope,
                "vol_expanding": (slope > 0).astype(int),
                "vol_contracting": (slope < 0).astype(int),
                "volatility_score": zscore * 0.5 + squeeze * -1 + (slope > 0).astype(int) * 0.3,
            },
            index=df.index,
        )


DEFAULT_SPECIALISTS: tuple[Specialist, ...] = (
    LiquiditySpecialist(),
    MicrostructureSpecialist(),
    MomentumSpecialist(),
    RegimeSpecialist(),
    StructureSpecialist(),
    VolatilitySpecialist(),
)


def build_specialist_features(
    df: pd.DataFrame,
    specialists: tuple[Specialist, ...] = DEFAULT_SPECIALISTS,
) -> pd.DataFrame:
    parts = [specialist.transform(df) for specialist in specialists]
    result = pd.concat(parts, axis=1)
    return result.loc[:, ~result.columns.duplicated()].replace([np.inf, -np.inf], np.nan).dropna()
