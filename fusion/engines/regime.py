from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from fusion.decision.schema import EngineOutput


@dataclass
class RegimeConfig:
    atr_period: int = 14
    long_window: int = 100
    adx_period: int = 14
    efficiency_window: int = 20
    entropy_window: int = 30
    compression_threshold: float = 0.75
    expansion_threshold: float = 1.25
    trend_adx_threshold: float = 22.0
    range_adx_threshold: float = 16.0
    panic_atr_percentile: float = 0.95
    min_confidence: float = 0.35


class MarketRegimeEngine:
    name = "market_regime"

    def __init__(self, config: RegimeConfig | None = None):
        self.config = config or RegimeConfig()

    @staticmethod
    def _true_range(df: pd.DataFrame) -> pd.Series:
        high = df["high"].astype(float)
        low = df["low"].astype(float)
        close = df["close"].astype(float)
        prev_close = close.shift(1)
        return pd.concat([(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)

    @staticmethod
    def _adx(df: pd.DataFrame, period: int) -> pd.Series:
        high = df["high"].astype(float)
        low = df["low"].astype(float)
        close = df["close"].astype(float)
        up_move = high.diff()
        down_move = -low.diff()
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
        tr = MarketRegimeEngine._true_range(df)
        atr = tr.rolling(period).mean()
        plus_di = 100 * pd.Series(plus_dm, index=df.index).rolling(period).mean() / atr
        minus_di = 100 * pd.Series(minus_dm, index=df.index).rolling(period).mean() / atr
        dx = ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)) * 100
        return dx.rolling(period).mean()

    @staticmethod
    def _efficiency(close: pd.Series, window: int) -> pd.Series:
        direction = (close - close.shift(window)).abs()
        path = close.diff().abs().rolling(window).sum()
        return direction / path.replace(0, np.nan)

    @staticmethod
    def _binary_entropy(returns: pd.Series, window: int) -> pd.Series:
        signs = (returns > 0).astype(float)
        p = signs.rolling(window).mean().clip(1e-6, 1 - 1e-6)
        return -(p * np.log2(p) + (1 - p) * np.log2(1 - p))

    def evaluate(self, df: pd.DataFrame, side: str = "NEUTRAL") -> EngineOutput:
        cfg = self.config
        min_bars = max(cfg.long_window + 5, cfg.adx_period * 3, cfg.entropy_window + 5)
        if df.empty or len(df) < min_bars:
            return EngineOutput(
                engine=self.name,
                direction="NEUTRAL",
                score=0.0,
                confidence=0.0,
                state="INSUFFICIENT_DATA",
                warnings=["dados_insuficientes"],
            )

        frame = df.sort_values("time").reset_index(drop=True).copy()
        close = frame["close"].astype(float)
        returns = np.log(close / close.shift(1)).replace([np.inf, -np.inf], np.nan)
        tr = self._true_range(frame)
        atr = tr.rolling(cfg.atr_period).mean()
        atr_long = atr.rolling(cfg.long_window).mean()
        atr_ratio = float((atr.iloc[-1] / atr_long.iloc[-1]) if atr_long.iloc[-1] else np.nan)
        atr_percentile = float((atr.tail(cfg.long_window) <= atr.iloc[-1]).mean())
        adx = float(self._adx(frame, cfg.adx_period).iloc[-1])
        efficiency = float(self._efficiency(close, cfg.efficiency_window).iloc[-1])
        entropy = float(self._binary_entropy(returns, cfg.entropy_window).iloc[-1])
        rolling_vol = float(returns.rolling(cfg.entropy_window).std().iloc[-1] or 0.0)
        momentum = float(close.iloc[-1] - close.iloc[-1 - cfg.efficiency_window])

        positive: list[str] = []
        negative: list[str] = []
        warnings: list[str] = []
        state = "TRANSITIONAL"
        confidence = 0.40

        if atr_percentile >= cfg.panic_atr_percentile and atr_ratio > cfg.expansion_threshold:
            state = "PANIC_VOLATILITY"
            confidence = min(1.0, 0.65 + (atr_percentile - cfg.panic_atr_percentile))
            warnings.append("volatilidade_panic")
        elif atr_ratio < cfg.compression_threshold and adx < cfg.range_adx_threshold:
            state = "COMPRESSION"
            confidence = min(1.0, 0.55 + (cfg.compression_threshold - atr_ratio))
            positive.append("compressao_volatilidade")
        elif atr_ratio > cfg.expansion_threshold and adx >= cfg.trend_adx_threshold:
            state = "EXPANSION"
            confidence = min(1.0, 0.55 + min(0.35, (atr_ratio - cfg.expansion_threshold) / 2))
            positive.append("expansao_direcional")
        elif adx >= cfg.trend_adx_threshold and efficiency >= 0.35:
            state = "TREND"
            confidence = min(1.0, 0.50 + min(0.35, efficiency))
            positive.append("tendencia_eficiente")
        elif adx <= cfg.range_adx_threshold and efficiency < 0.25 and entropy > 0.85:
            state = "RANGE"
            confidence = min(1.0, 0.55 + min(0.25, entropy - 0.75))
            negative.append("mercado_lateral")
        else:
            state = "TRANSITIONAL"
            confidence = 0.45
            warnings.append("regime_transicional")

        direction = "NEUTRAL"
        if state in {"TREND", "EXPANSION"}:
            direction = "BUY" if momentum > 0 else "SELL" if momentum < 0 else "NEUTRAL"
        score = confidence
        if state in {"RANGE", "PANIC_VOLATILITY", "TRANSITIONAL"}:
            score *= 0.55

        if side.upper() in {"BUY", "SELL"} and direction in {"BUY", "SELL"}:
            if direction == side.upper():
                positive.append(f"regime_alinhado:{state}")
            else:
                negative.append(f"regime_contra:{state}:{direction}")

        features: dict[str, Any] = {
            "atr_ratio": None if not np.isfinite(atr_ratio) else atr_ratio,
            "atr_percentile": atr_percentile,
            "adx": None if not np.isfinite(adx) else adx,
            "efficiency": None if not np.isfinite(efficiency) else efficiency,
            "entropy": None if not np.isfinite(entropy) else entropy,
            "rolling_volatility": rolling_vol,
            "momentum": momentum,
        }
        return EngineOutput(
            engine=self.name,
            direction=direction,
            score=max(0.0, min(1.0, float(score))),
            confidence=max(0.0, min(1.0, float(confidence))),
            state=state,
            positive_factors=positive,
            negative_factors=negative,
            warnings=warnings,
            features=features,
        )
