from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator
from uuid import uuid4

from fusion.backtest.context import BacktestContext, BacktestRunConfig
from fusion.backtest.market_data import HistoricalMarketDataProvider
from fusion.core.objects import FusionBar


@dataclass
class ReplayFrame:
    context: BacktestContext
    primary_bar: FusionBar
    bars_by_timeframe: dict[str, list[FusionBar]] = field(default_factory=dict)


class MultiTimeframeReplayCursor:
    def __init__(
        self,
        provider: HistoricalMarketDataProvider,
        config: BacktestRunConfig,
        primary_timeframe: str = "M5",
        lookback: int = 300,
        run_id: str | None = None,
    ) -> None:
        self.provider = provider
        self.config = config
        self.primary_timeframe = primary_timeframe.upper()
        self.lookback = lookback
        self.run_id = run_id or uuid4().hex

    def frames(self, symbol: str) -> Iterator[ReplayFrame]:
        total = self.provider.bar_count(symbol, self.primary_timeframe)
        start_index = self._start_index(symbol, total)
        end_index = self._end_index(symbol, total)
        for index in range(start_index, end_index + 1):
            primary_bar = self.provider.get_bar(symbol, self.primary_timeframe, index)
            if primary_bar is None:
                continue
            bars_by_tf = self.provider.get_aligned_bars(
                symbol,
                self.primary_timeframe,
                index,
                self.config.timeframes,
                self.lookback,
            )
            yield ReplayFrame(
                context=BacktestContext(
                    run_id=self.run_id,
                    config=self.config,
                    symbol=symbol,
                    timeframe=self.primary_timeframe,
                    candle_index=index,
                    timestamp=primary_bar.timestamp,
                ),
                primary_bar=primary_bar,
                bars_by_timeframe=bars_by_tf,
            )

    def _start_index(self, symbol: str, total: int) -> int:
        if not self.config.start:
            return 0
        for index in range(total):
            ts = self.provider.timestamp_at(symbol, self.primary_timeframe, index)
            if ts is not None and str(ts) >= self.config.start:
                return index
        return 0

    def _end_index(self, symbol: str, total: int) -> int:
        if total <= 0:
            return -1
        if not self.config.end:
            return total - 1
        last = total - 1
        for index in range(total):
            ts = self.provider.timestamp_at(symbol, self.primary_timeframe, index)
            if ts is not None and str(ts) > self.config.end:
                return max(0, index - 1)
        return last

