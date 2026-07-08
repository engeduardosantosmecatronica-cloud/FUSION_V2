from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from fusion.core.objects import FusionBar


class MarketDataProvider(ABC):
    @abstractmethod
    def get_bars(self, symbol: str, timeframe: str, end_index: int, lookback: int) -> list[FusionBar]:
        raise NotImplementedError

    @abstractmethod
    def bar_count(self, symbol: str, timeframe: str) -> int:
        raise NotImplementedError


@dataclass
class HistoricalMarketDataProvider(MarketDataProvider):
    data_root: Path
    max_cache_items: int = 64

    def __post_init__(self) -> None:
        self.data_root = Path(self.data_root)
        self._cache: dict[tuple[str, str], pd.DataFrame] = {}

    def get_bars(self, symbol: str, timeframe: str, end_index: int, lookback: int) -> list[FusionBar]:
        frame = self._frame(symbol, timeframe)
        if frame.empty:
            return []
        end = min(max(end_index, 0), len(frame) - 1)
        start = max(0, end - max(lookback, 1) + 1)
        rows = frame.iloc[start : end + 1]
        return [self._row_to_bar(symbol, timeframe, row) for _, row in rows.iterrows()]

    def bar_count(self, symbol: str, timeframe: str) -> int:
        return int(len(self._frame(symbol, timeframe)))

    def get_bar(self, symbol: str, timeframe: str, index: int) -> FusionBar | None:
        frame = self._frame(symbol, timeframe)
        if frame.empty or index < 0 or index >= len(frame):
            return None
        return self._row_to_bar(symbol, timeframe, frame.iloc[index])

    def timestamp_at(self, symbol: str, timeframe: str, index: int) -> pd.Timestamp | None:
        frame = self._frame(symbol, timeframe)
        if frame.empty or index < 0 or index >= len(frame):
            return None
        return self._row_timestamp(frame.iloc[index])

    def get_bars_until(
        self,
        symbol: str,
        timeframe: str,
        timestamp: pd.Timestamp | str,
        lookback: int,
    ) -> list[FusionBar]:
        frame = self._frame(symbol, timeframe)
        if frame.empty:
            return []
        ts = pd.Timestamp(timestamp)
        time_series = self._time_series(frame)
        eligible = frame.loc[time_series <= ts]
        if eligible.empty:
            return []
        rows = eligible.tail(max(lookback, 1))
        return [self._row_to_bar(symbol, timeframe, row) for _, row in rows.iterrows()]

    def get_aligned_bars(
        self,
        symbol: str,
        primary_timeframe: str,
        primary_index: int,
        timeframes: list[str],
        lookback: int,
    ) -> dict[str, list[FusionBar]]:
        timestamp = self.timestamp_at(symbol, primary_timeframe, primary_index)
        if timestamp is None:
            return {timeframe: [] for timeframe in timeframes}
        return {
            timeframe: self.get_bars_until(symbol, timeframe, timestamp, lookback)
            for timeframe in timeframes
        }

    def _frame(self, symbol: str, timeframe: str) -> pd.DataFrame:
        key = (symbol.upper(), timeframe.upper())
        if key in self._cache:
            return self._cache[key]
        path = self._resolve_path(symbol, timeframe)
        if path is None:
            frame = pd.DataFrame()
        else:
            frame = pd.read_csv(path)
            frame = self._normalize_frame(frame)
        if len(self._cache) >= self.max_cache_items:
            self._cache.pop(next(iter(self._cache)))
        self._cache[key] = frame
        return frame

    def _resolve_path(self, symbol: str, timeframe: str) -> Path | None:
        symbol = symbol.upper()
        timeframe = timeframe.upper()
        candidates = [
            self.data_root / f"{symbol}_{timeframe}.csv",
            self.data_root / f"{symbol}_{timeframe}.csv",
            self.data_root / symbol / f"{timeframe}.csv",
            self.data_root / symbol / f"{timeframe}.csv",
            self.data_root / timeframe / f"{symbol}.csv",
        ]
        direct = next((path for path in candidates if path.exists()), None)
        if direct:
            return direct
        glob_roots = [
            self.data_root / timeframe,
            self.data_root / "csv" / timeframe,
            self.data_root / "data" / "csv" / timeframe,
        ]
        for root in glob_roots:
            if not root.exists():
                continue
            matches = sorted(root.glob(f"**/{symbol}.csv"))
            if matches:
                return matches[0]
        return None

    @staticmethod
    def _normalize_frame(frame: pd.DataFrame) -> pd.DataFrame:
        renamed = {col: str(col).strip().lower() for col in frame.columns}
        frame = frame.rename(columns=renamed)
        time_col = "time" if "time" in frame.columns else "timestamp" if "timestamp" in frame.columns else None
        if time_col is None and "date" in frame.columns:
            time_col = "date"
        if time_col:
            frame[time_col] = pd.to_datetime(frame[time_col], errors="coerce")
            frame = frame.sort_values(time_col)
        return frame.reset_index(drop=True)

    @staticmethod
    def _row_to_bar(symbol: str, timeframe: str, row: Any) -> FusionBar:
        timestamp = str(row.get("time", row.get("timestamp", row.get("date", ""))))
        return FusionBar(
            symbol=symbol,
            broker_symbol=symbol,
            timeframe=timeframe,
            open=float(row.get("open", 0.0) or 0.0),
            high=float(row.get("high", 0.0) or 0.0),
            low=float(row.get("low", 0.0) or 0.0),
            close=float(row.get("close", 0.0) or 0.0),
            volume=float(row.get("volume", row.get("tick_volume", 0.0)) or 0.0),
            timestamp=timestamp,
        )

    @staticmethod
    def _row_timestamp(row: Any) -> pd.Timestamp:
        return pd.Timestamp(row.get("time", row.get("timestamp", row.get("date", ""))))

    @staticmethod
    def _time_series(frame: pd.DataFrame) -> pd.Series:
        if "time" in frame.columns:
            return pd.to_datetime(frame["time"], errors="coerce")
        if "timestamp" in frame.columns:
            return pd.to_datetime(frame["timestamp"], errors="coerce")
        if "date" in frame.columns:
            return pd.to_datetime(frame["date"], errors="coerce")
        return pd.Series(pd.NaT, index=frame.index)
