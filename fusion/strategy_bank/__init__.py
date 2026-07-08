from __future__ import annotations

from fusion.strategy_bank._factory import ASSETS, build_asset_strategy_bank, build_strategy_bank
from fusion.strategy_bank.executor import StrategySignal, evaluate_asset_bank, evaluate_strategy


STRATEGY_BANK = build_strategy_bank()

__all__ = [
    "ASSETS",
    "STRATEGY_BANK",
    "StrategySignal",
    "build_asset_strategy_bank",
    "build_strategy_bank",
    "evaluate_asset_bank",
    "evaluate_strategy",
]
