from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from fusion.decision.schema import EngineOutput


@dataclass
class VolatilityConfig:
    atr_period: int = 14
    short_window: int = 20
    long_window: int = 100
    compression_threshold: float = 0.75
    expansion_threshold: float = 1.25
    panic_percentile: float = 0.95
    min_range_to_atr: float = 0.55


class VolatilityEngine:
    name = "volatility_engine"

    def __init__(self, config: VolatilityConfig | None = None):
        self.config = config or VolatilityConfig()

    @staticmethod
    def _true_range(df: pd.DataFrame) -> pd.Series:
        high = df["high"].astype(float)
        low = df["low"].astype(float)
        close = df["close"].astype(float)
        prev_close = close.shift(1)
        return pd.concat([(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)

    def evaluate(self, df: pd.DataFrame) -> EngineOutput:
        cfg = self.config
        min_bars = max(cfg.long_window + cfg.atr_period + 5, cfg.short_window + cfg.atr_period + 5)
        if df.empty or len(df) < min_bars:
            return EngineOutput(
                engine=self.name,
                direction="NEUTRAL",
                score=0.0,
                confidence=0.0,
                state="INSUFFICIENT_DATA",
                warnings=["dados_insuficientes"],
            )

        frame = df.sort_values("time").reset_index(drop=True)
        tr = self._true_range(frame)
        atr = tr.rolling(cfg.atr_period).mean()
        atr_short = atr.rolling(cfg.short_window).mean()
        atr_long = atr.rolling(cfg.long_window).mean()
        current_atr = float(atr.iloc[-1])
        current_range = float(frame["high"].iloc[-1] - frame["low"].iloc[-1])
        atr_ratio = float(atr_short.iloc[-1] / atr_long.iloc[-1]) if atr_long.iloc[-1] else np.nan
        atr_percentile = float((atr.tail(cfg.long_window) <= current_atr).mean())
        range_to_atr = float(current_range / current_atr) if current_atr else np.nan

        positive: list[str] = []
        negative: list[str] = []
        warnings: list[str] = []
        state = "NORMAL"
        score = 0.70
        confidence = 0.70

        if np.isfinite(atr_percentile) and atr_percentile >= cfg.panic_percentile:
            state = "PANIC_VOLATILITY"
            score = 0.25
            confidence = 0.90
            negative.append("volatilidade_panic")
        elif np.isfinite(atr_ratio) and atr_ratio < cfg.compression_threshold:
            state = "COMPRESSION"
            score = 0.45
            confidence = 0.80
            warnings.append("compressao_volatilidade")
        elif np.isfinite(atr_ratio) and atr_ratio > cfg.expansion_threshold:
            state = "EXPANSION"
            score = 0.82
            confidence = 0.80
            positive.append("expansao_volatilidade")

        if np.isfinite(range_to_atr) and range_to_atr < cfg.min_range_to_atr:
            if state == "NORMAL":
                state = "LOW_INTRABAR_RANGE"
            score = min(score, 0.50)
            warnings.append("range_atual_baixo_vs_atr")

        return EngineOutput(
            engine=self.name,
            direction="NEUTRAL",
            score=max(0.0, min(1.0, score)),
            confidence=max(0.0, min(1.0, confidence)),
            state=state,
            positive_factors=positive,
            negative_factors=negative,
            warnings=warnings,
            features={
                "atr": None if not np.isfinite(current_atr) else current_atr,
                "atr_ratio_short_long": None if not np.isfinite(atr_ratio) else atr_ratio,
                "atr_percentile": atr_percentile,
                "range_to_atr": None if not np.isfinite(range_to_atr) else range_to_atr,
                "current_range": current_range,
            },
        )
