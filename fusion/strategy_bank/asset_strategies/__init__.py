from __future__ import annotations

from fusion.strategy_bank._factory import ASSETS, build_asset_strategy_bank


def get_asset_strategies(symbol: str) -> dict:
    return build_asset_strategy_bank(symbol)


__all__ = ["ASSETS", "get_asset_strategies"]
