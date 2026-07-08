from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from fusion.decision.schema import EngineOutput
from fusion.features.market_structure import MarketStructureConfig, build_market_structure_features


@dataclass
class EntryTimingConfig:
    bars: int = 260
    top_bottom_distance_atr: float = 0.35
    extension_atr: float = 1.20
    require_valid_breakout: bool = True
    breakout_max_bars: int = 2
    min_breakout_volume_ratio: float = 1.10


class EntryTimingEngine:
    name = "entry_timing"

    def __init__(self, config: EntryTimingConfig | None = None):
        self.config = config or EntryTimingConfig()

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
        distance_high = self._float(row, "distance_to_swing_high_atr", 999.0)
        distance_low = self._float(row, "distance_to_swing_low_atr", 999.0)
        extension = self._float(row, "price_extension_atr", 0.0)
        volume_ratio = self._float(row, "volume_ratio", 0.0)
        breakout_up = self._int(row, "breakout_up", 0)
        breakout_down = self._int(row, "breakout_down", 0)
        bos_up = self._int(row, "break_of_structure_up", 0)
        bos_down = self._int(row, "break_of_structure_down", 0)
        bars_since_breakout_up = self._float(row, "bars_since_breakout_up", 999.0)
        bars_since_breakout_down = self._float(row, "bars_since_breakout_down", 999.0)
        breakout_up_volume = self._int(row, "breakout_up_with_volume", 0)
        breakout_down_volume = self._int(row, "breakout_down_with_volume", 0)

        near_top = distance_high <= self.config.top_bottom_distance_atr
        near_bottom = distance_low <= self.config.top_bottom_distance_atr
        buy_extended = extension >= self.config.extension_atr
        sell_extended = extension <= -self.config.extension_atr
        valid_buy_break = (
            bos_up == 1
            or breakout_up_volume == 1
            or (breakout_up == 1 and volume_ratio >= self.config.min_breakout_volume_ratio)
            or bars_since_breakout_up <= self.config.breakout_max_bars
        )
        valid_sell_break = (
            bos_down == 1
            or breakout_down_volume == 1
            or (breakout_down == 1 and volume_ratio >= self.config.min_breakout_volume_ratio)
            or bars_since_breakout_down <= self.config.breakout_max_bars
        )

        negative: list[str] = []
        positive: list[str] = []
        warnings: list[str] = []
        state = "ok"
        score = 0.82
        direction = side if side in {"BUY", "SELL"} else "NEUTRAL"

        if side == "BUY" and (near_top or buy_extended):
            if self.config.require_valid_breakout and valid_buy_break:
                state = "validated_breakout_buy"
                positive.append("compra_topo_permitida_por_bos_ou_breakout")
                score = 0.76
            else:
                state = "avoid_buying_top"
                direction = "SELL"
                score = 0.25
                negative.append("comprar_topo_sem_rompimento_validado")
        elif side == "SELL" and (near_bottom or sell_extended):
            if self.config.require_valid_breakout and valid_sell_break:
                state = "validated_breakout_sell"
                positive.append("venda_fundo_permitida_por_bos_ou_breakout")
                score = 0.76
            else:
                state = "avoid_selling_bottom"
                direction = "BUY"
                score = 0.25
                negative.append("vender_fundo_sem_rompimento_validado")
        else:
            positive.append("entrada_sem_extremo_topo_fundo")

        if volume_ratio < 0.80 and state.startswith("validated_breakout"):
            warnings.append("rompimento_com_volume_fraco")

        return EngineOutput(
            engine=self.name,
            direction=direction,
            score=score,
            confidence=0.82,
            state=state,
            positive_factors=positive,
            negative_factors=negative,
            warnings=warnings,
            features={
                "distance_to_swing_high_atr": distance_high,
                "distance_to_swing_low_atr": distance_low,
                "price_extension_atr": extension,
                "volume_ratio": volume_ratio,
                "near_top": near_top,
                "near_bottom": near_bottom,
                "buy_extended": buy_extended,
                "sell_extended": sell_extended,
                "breakout_up": breakout_up,
                "breakout_down": breakout_down,
                "break_of_structure_up": bos_up,
                "break_of_structure_down": bos_down,
                "valid_buy_break": valid_buy_break,
                "valid_sell_break": valid_sell_break,
            },
        )
