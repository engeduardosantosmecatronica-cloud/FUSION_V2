from __future__ import annotations

from typing import Any

from fusion.core.enums import AssetType
from fusion.core.objects import FusionContract


def infer_asset_type(symbol: str) -> AssetType:
    text = str(symbol or "").upper()
    if text in {"GOLD", "XAUUSD", "XAUUSD."} or "XAU" in text:
        return AssetType.METAL
    if len(text) >= 6 and text[:3].isalpha() and text[3:6].isalpha():
        return AssetType.FOREX
    return AssetType.UNKNOWN


def contract_from_mt5_info(symbol: str, broker_symbol: str, info: Any) -> FusionContract:
    return FusionContract(
        symbol=symbol,
        broker_symbol=broker_symbol,
        asset_type=infer_asset_type(symbol),
        digits=int(getattr(info, "digits", 0) or 0),
        point=float(getattr(info, "point", 0.0) or 0.0),
        tick_size=float(getattr(info, "trade_tick_size", 0.0) or 0.0),
        tick_value=float(getattr(info, "trade_tick_value", 0.0) or 0.0),
        point_value=float(getattr(info, "trade_tick_value", 0.0) or 0.0),
        min_lot=float(getattr(info, "volume_min", 0.0) or 0.0),
        lot_step=float(getattr(info, "volume_step", 0.0) or 0.0),
        max_lot=float(getattr(info, "volume_max", 0.0) or 0.0),
        spread=float(getattr(info, "spread", 0.0) or 0.0),
        currency_profit=str(getattr(info, "currency_profit", "") or ""),
    )


def apply_contract_override(contract: FusionContract, override: dict | None) -> FusionContract:
    if not override:
        return contract
    for key, value in override.items():
        if hasattr(contract, key):
            setattr(contract, key, value)
    return contract
