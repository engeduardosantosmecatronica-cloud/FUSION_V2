from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from fusion.decision.schema import EngineOutput
from fusion.features.market_structure import MarketStructureConfig, build_market_structure_features


@dataclass
class ExecutionConfig:
    bars: int = 180
    min_entry_quality_score: float = 0.55
    min_breakout_quality_score: float = 0.60
    min_volume_ratio: float = 0.80
    exhaustion_streak: int = 5
    fake_breakout_max_bars: int = 3


class ExecutionEngine:
    name = "execution_engine"

    def __init__(self, config: ExecutionConfig | None = None):
        self.config = config or ExecutionConfig()

    @staticmethod
    def _float(row: pd.Series, key: str, default: float = 0.0) -> float:
        try:
            value = float(row.get(key, default))
        except (TypeError, ValueError):
            return default
        return value if np.isfinite(value) else default

    @staticmethod
    def _int(row: pd.Series, key: str, default: int = 0) -> int:
        try:
            return int(float(row.get(key, default)))
        except (TypeError, ValueError):
            return default

    def evaluate(self, df: pd.DataFrame, side: str) -> EngineOutput:
        side = str(side or "").upper()
        if side not in {"BUY", "SELL"}:
            return EngineOutput(
                engine=self.name,
                direction="NEUTRAL",
                score=0.0,
                confidence=0.0,
                state="invalid_side",
                warnings=["lado_invalido"],
            )
        if df.empty or len(df) < 80:
            return EngineOutput(
                engine=self.name,
                direction="NEUTRAL",
                score=0.0,
                confidence=0.0,
                state="INSUFFICIENT_DATA",
                warnings=["dados_insuficientes"],
            )

        features = build_market_structure_features(
            df.tail(max(90, self.config.bars)),
            MarketStructureConfig(),
            include_raw_ohlcv=False,
        )
        if features.empty:
            return EngineOutput(
                engine=self.name,
                direction="NEUTRAL",
                score=0.0,
                confidence=0.0,
                state="INSUFFICIENT_DATA",
                warnings=["sem_features"],
            )

        row = features.tail(1).iloc[0]
        volume_ratio = self._float(row, "volume_ratio", 0.0)
        range_to_atr = self._float(row, "range_to_atr", 0.0)
        body_to_range = self._float(row, "body_to_range", 0.0)
        close_position = self._float(row, "close_position", 0.5)
        absorption = self._int(row, "absorption", 0)
        volume_climax = self._int(row, "volume_climax", 0)
        rejection_upper = self._int(row, "rejection_upper", 0)
        rejection_lower = self._int(row, "rejection_lower", 0)
        stop_hunt_up = self._int(row, "stop_hunt_up", 0)
        stop_hunt_down = self._int(row, "stop_hunt_down", 0)
        displacement_up = self._int(row, "displacement_up", 0)
        displacement_down = self._int(row, "displacement_down", 0)
        breakout_up = self._int(row, "breakout_up", 0)
        breakout_down = self._int(row, "breakout_down", 0)
        bos_up = self._int(row, "break_of_structure_up", 0)
        bos_down = self._int(row, "break_of_structure_down", 0)
        liquidity_grab_up = self._int(row, "liquidity_grab_up", 0)
        liquidity_grab_down = self._int(row, "liquidity_grab_down", 0)
        bullish_imbalance = self._int(row, "bullish_imbalance", 0)
        bearish_imbalance = self._int(row, "bearish_imbalance", 0)
        consecutive_up = self._float(row, "consecutive_up", 0.0)
        consecutive_down = self._float(row, "consecutive_down", 0.0)
        velocity_atr_3 = self._float(row, "velocity_atr_3", 0.0)
        velocity_atr_5 = self._float(row, "velocity_atr_5", 0.0)

        buy_breakout_quality = (
            0.25 * breakout_up
            + 0.25 * bos_up
            + 0.20 * displacement_up
            + 0.15 * bullish_imbalance
            + 0.15 * min(max(volume_ratio / 1.5, 0.0), 1.0)
        )
        sell_breakout_quality = (
            0.25 * breakout_down
            + 0.25 * bos_down
            + 0.20 * displacement_down
            + 0.15 * bearish_imbalance
            + 0.15 * min(max(volume_ratio / 1.5, 0.0), 1.0)
        )
        breakout_quality = buy_breakout_quality if side == "BUY" else sell_breakout_quality

        momentum_ignition_buy = (
            displacement_up == 1
            and volume_ratio >= 1.05
            and velocity_atr_3 > 0
            and close_position >= 0.65
        )
        momentum_ignition_sell = (
            displacement_down == 1
            and volume_ratio >= 1.05
            and velocity_atr_3 < 0
            and close_position <= 0.35
        )
        rejection_support = side == "BUY" and rejection_lower == 1 and close_position >= 0.50
        rejection_resistance = side == "SELL" and rejection_upper == 1 and close_position <= 0.50
        absorption_support = side == "BUY" and absorption == 1 and rejection_lower == 1
        absorption_resistance = side == "SELL" and absorption == 1 and rejection_upper == 1
        fake_breakout_buy = side == "BUY" and (liquidity_grab_up == 1 or stop_hunt_up == 1)
        fake_breakout_sell = side == "SELL" and (liquidity_grab_down == 1 or stop_hunt_down == 1)
        exhaustion_buy = side == "BUY" and consecutive_up >= self.config.exhaustion_streak and rejection_upper == 1
        exhaustion_sell = side == "SELL" and consecutive_down >= self.config.exhaustion_streak and rejection_lower == 1
        low_execution_volume = volume_ratio < self.config.min_volume_ratio

        score = 0.50
        positive: list[str] = []
        negative: list[str] = []
        warnings: list[str] = []

        if breakout_quality >= self.config.min_breakout_quality_score:
            score += 0.18
            positive.append("breakout_quality_ok")
        if (side == "BUY" and momentum_ignition_buy) or (side == "SELL" and momentum_ignition_sell):
            score += 0.14
            positive.append("momentum_ignition")
        if rejection_support or rejection_resistance:
            score += 0.10
            positive.append("candle_rejection_aligned")
        if absorption_support or absorption_resistance:
            score += 0.10
            positive.append("liquidity_absorption_aligned")

        if fake_breakout_buy or fake_breakout_sell:
            score -= 0.22
            negative.append("fake_breakout_or_stop_hunt")
        if exhaustion_buy or exhaustion_sell:
            score -= 0.18
            negative.append("exhaustion_candle")
        if low_execution_volume:
            score -= 0.08
            warnings.append("volume_execucao_baixo")
        if range_to_atr < 0.35:
            score -= 0.08
            warnings.append("range_intrabar_fraco")
        if body_to_range < 0.25 and not (absorption_support or absorption_resistance):
            score -= 0.05
            warnings.append("corpo_fraco")

        score = max(0.0, min(1.0, score))
        state = "good_execution"
        direction = side
        if negative:
            state = "avoid_execution"
            direction = "SELL" if side == "BUY" else "BUY"
        elif score < self.config.min_entry_quality_score:
            state = "weak_execution"
            direction = "NEUTRAL"
        elif warnings:
            state = "acceptable_with_warnings"

        if not positive and not negative:
            positive.append("execution_context_neutral")

        return EngineOutput(
            engine=self.name,
            direction=direction,
            score=score,
            confidence=max(0.35, min(0.90, 0.45 + abs(score - 0.50))),
            state=state,
            positive_factors=positive,
            negative_factors=negative,
            warnings=warnings,
            features={
                "entry_quality_score": score,
                "breakout_quality": breakout_quality,
                "buy_breakout_quality": buy_breakout_quality,
                "sell_breakout_quality": sell_breakout_quality,
                "volume_ratio": volume_ratio,
                "range_to_atr": range_to_atr,
                "body_to_range": body_to_range,
                "close_position": close_position,
                "absorption": absorption,
                "volume_climax": volume_climax,
                "momentum_ignition_buy": momentum_ignition_buy,
                "momentum_ignition_sell": momentum_ignition_sell,
                "fake_breakout_buy": fake_breakout_buy,
                "fake_breakout_sell": fake_breakout_sell,
                "exhaustion_buy": exhaustion_buy,
                "exhaustion_sell": exhaustion_sell,
                "velocity_atr_3": velocity_atr_3,
                "velocity_atr_5": velocity_atr_5,
            },
        )
