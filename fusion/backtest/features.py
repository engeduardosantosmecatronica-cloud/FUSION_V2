from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from fusion.core.objects import FusionBar, to_plain_dict
from fusion.features.engine import AlphaMiner, EMA, RSI

try:
    from fusion.features.expressions.definitions import build_expression_features
except Exception:
    build_expression_features = None


@dataclass
class FeatureSnapshot:
    symbol: str
    timeframe: str
    timestamp: str
    features: dict[str, Any] = field(default_factory=dict)
    rows: int = 0
    status: str = "OK"
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return to_plain_dict(self)


class BacktestFeatureReplay:
    def __init__(self, min_bars: int = 100, prefer_expression_builder: bool = True) -> None:
        self.min_bars = min_bars
        self.prefer_expression_builder = prefer_expression_builder

    def snapshot(self, symbol: str, timeframe: str, bars: list[FusionBar]) -> FeatureSnapshot:
        if len(bars) < self.min_bars:
            timestamp = bars[-1].timestamp if bars else ""
            return FeatureSnapshot(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=timestamp,
                rows=len(bars),
                status="INSUFFICIENT_BARS",
                reason=f"min_bars:{self.min_bars}",
            )
        frame = self._bars_to_frame(bars)
        features = self._calculate(frame)
        if features.empty:
            return FeatureSnapshot(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=str(frame.index[-1]) if len(frame.index) else "",
                rows=len(bars),
                status="NO_FEATURES",
                reason="features_empty",
            )
        row = features.tail(1).iloc[0]
        return FeatureSnapshot(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=str(features.tail(1).index[0]),
            rows=len(bars),
            features=self._row_to_dict(row),
            status="OK",
        )

    def multi_timeframe_snapshot(
        self,
        symbol: str,
        bars_by_timeframe: dict[str, list[FusionBar]],
    ) -> dict[str, FeatureSnapshot]:
        return {
            timeframe: self.snapshot(symbol, timeframe, bars)
            for timeframe, bars in bars_by_timeframe.items()
        }

    def flattened_features(
        self,
        symbol: str,
        bars_by_timeframe: dict[str, list[FusionBar]],
        suffix_timeframe: bool = True,
    ) -> dict[str, Any]:
        snapshots = self.multi_timeframe_snapshot(symbol, bars_by_timeframe)
        flattened: dict[str, Any] = {}
        for timeframe, snapshot in snapshots.items():
            if snapshot.status != "OK":
                flattened[f"feature_status_{timeframe.lower()}"] = snapshot.status
                continue
            for key, value in snapshot.features.items():
                output_key = f"{key}_{timeframe.lower()}" if suffix_timeframe else key
                flattened[output_key] = value
        return flattened

    def _calculate(self, frame: pd.DataFrame) -> pd.DataFrame:
        if self.prefer_expression_builder and build_expression_features is not None:
            try:
                result = build_expression_features(frame.copy())
                if not result.empty:
                    return self._append_raw_columns(result, frame)
            except Exception:
                pass
        return self._calculate_legacy(frame)

    @staticmethod
    def _bars_to_frame(bars: list[FusionBar]) -> pd.DataFrame:
        rows = []
        for bar in bars:
            rows.append(
                {
                    "time": pd.to_datetime(bar.timestamp, errors="coerce"),
                    "open": float(bar.open),
                    "high": float(bar.high),
                    "low": float(bar.low),
                    "close": float(bar.close),
                    "tick_volume": float(bar.volume or 0.0),
                }
            )
        frame = pd.DataFrame(rows).dropna(subset=["time"]).sort_values("time")
        return frame.set_index("time")

    def _calculate_legacy(self, df: pd.DataFrame) -> pd.DataFrame:
        if len(df) < self.min_bars:
            return pd.DataFrame()

        features = pd.DataFrame(index=df.index)
        close = df["close"]
        high = df["high"]
        low = df["low"]

        ret = np.log(close / close.shift(1))
        features["ret"] = ret
        features["ret_5"] = ret.rolling(5).sum()
        features["ret_10"] = ret.rolling(10).sum()
        features["ret_20"] = ret.rolling(20).sum()

        rsi14 = RSI.calculate(df, 14)
        rsi28 = RSI.calculate(df, 28)
        features["rsi14"] = rsi14
        features["rsi28"] = rsi28
        features["rsi_diff"] = rsi14 - rsi28
        features["rsi_ma5"] = rsi14.rolling(5).mean()
        features["rsi_gap"] = rsi14 - rsi14.rolling(10).mean()

        ema8 = EMA.calculate(df, 8)
        ema21 = EMA.calculate(df, 21)
        ema50 = EMA.calculate(df, 50)
        ema200 = EMA.calculate(df, 200)
        features["ema8"] = ema8
        features["ema21"] = ema21
        features["ema50"] = ema50
        features["ema200"] = ema200
        features["dist_ema8"] = (close / ema8) - 1
        features["dist_ema21"] = (close / ema21) - 1
        features["dist_ema50"] = (close / ema50) - 1
        features["dist_ema200"] = (close / ema200) - 1

        range_pct = (high - low) / close
        features["range_pct"] = range_pct
        features["range_ma10"] = range_pct.rolling(10).mean()
        features["high_20"] = high.rolling(20).max()
        features["low_20"] = low.rolling(20).min()
        features["position_in_range"] = (close - features["low_20"]) / (features["high_20"] - features["low_20"] + 1e-9)

        vol5 = ret.rolling(5).std()
        vol20 = ret.rolling(20).std()
        features["vol5"] = vol5
        features["vol20"] = vol20
        features["vol_ratio"] = vol5 / (vol20 + 1e-9)

        ema_fast = close.ewm(span=12).mean()
        ema_slow = close.ewm(span=26).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=9).mean()
        features["macd"] = macd_line
        features["macd_signal"] = signal_line
        features["macd_hist"] = macd_line - signal_line

        features["upper_bb"] = ema21 + (ret.rolling(20).std() * 2)
        features["lower_bb"] = ema21 - (ret.rolling(20).std() * 2)
        features["bb_width"] = features["upper_bb"] - features["lower_bb"]
        features["alpha_vam"] = AlphaMiner.vam(df, 20)
        features["alpha_effort"] = AlphaMiner.effort(df, 50)
        features["alpha_mrs"] = AlphaMiner.mrs(df, 20)
        features["alpha_rsi_gap"] = AlphaMiner.rsi_gap(df, 14)

        trend_alignment = (rsi14 > 50).astype(int)
        for period in [5, 10, 20]:
            trend_alignment = trend_alignment + (close > EMA.calculate(df, period)).astype(int)
        features["trend_alignment"] = trend_alignment
        return self._append_raw_columns(features.dropna(), df)

    @staticmethod
    def _append_raw_columns(features: pd.DataFrame, frame: pd.DataFrame) -> pd.DataFrame:
        result = features.copy()
        raw_cols = ["open", "high", "low", "close", "tick_volume", "spread", "real_volume"]
        for col in raw_cols:
            if col in frame.columns and col not in result.columns:
                result[col] = frame[col]
        return result.replace([np.inf, -np.inf], np.nan).dropna()

    @staticmethod
    def _row_to_dict(row: pd.Series) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in row.items():
            if hasattr(value, "item"):
                value = value.item()
            if isinstance(value, float) and not np.isfinite(value):
                continue
            result[str(key)] = value
        return result

