from fusion.strategy_bank._factory import build_asset_strategy_bank


STRATEGY_BANK = build_asset_strategy_bank("USDJPY")
STRATEGIES = STRATEGY_BANK["strategies"]
