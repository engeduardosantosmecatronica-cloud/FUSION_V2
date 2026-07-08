from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

from fusion.backtest.features import BacktestFeatureReplay, FeatureSnapshot
from fusion.backtest.replay import MultiTimeframeReplayCursor, ReplayFrame


@dataclass
class FeatureReplayFrame:
    replay: ReplayFrame
    snapshots: dict[str, FeatureSnapshot] = field(default_factory=dict)
    flattened: dict[str, object] = field(default_factory=dict)


class FeatureReplayRunner:
    def __init__(
        self,
        cursor: MultiTimeframeReplayCursor,
        feature_replay: BacktestFeatureReplay | None = None,
    ) -> None:
        self.cursor = cursor
        self.feature_replay = feature_replay or BacktestFeatureReplay()

    def frames(self, symbol: str) -> Iterator[FeatureReplayFrame]:
        for replay_frame in self.cursor.frames(symbol):
            snapshots = self.feature_replay.multi_timeframe_snapshot(
                symbol,
                replay_frame.bars_by_timeframe,
            )
            flattened = self.feature_replay.flattened_features(
                symbol,
                replay_frame.bars_by_timeframe,
                suffix_timeframe=True,
            )
            yield FeatureReplayFrame(
                replay=replay_frame,
                snapshots=snapshots,
                flattened=flattened,
            )

