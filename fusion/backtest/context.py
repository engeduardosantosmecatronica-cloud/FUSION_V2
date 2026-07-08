from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BacktestRunConfig:
    symbols: list[str]
    timeframes: list[str]
    start: str = ""
    end: str = ""
    initial_balance: float = 10000.0
    currency: str = "USD"
    spread_mode: str = "historical"
    slippage_points: float = 0.0
    commission_per_lot: float = 0.0
    max_bars: int = 5000
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BacktestContext:
    run_id: str
    config: BacktestRunConfig
    symbol: str
    timeframe: str
    candle_index: int = 0
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

