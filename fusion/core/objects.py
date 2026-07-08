from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from fusion.core.enums import AssetType, DecisionAction, OrderStatus, TradeDirection


def _now_iso() -> str:
    return datetime.now().isoformat()


def to_plain_dict(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, list):
        return [to_plain_dict(item) for item in value]
    if isinstance(value, tuple):
        return [to_plain_dict(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_plain_dict(item) for key, item in value.items()}
    if hasattr(value, "__dataclass_fields__"):
        return {key: to_plain_dict(item) for key, item in asdict(value).items()}
    return value


@dataclass
class FusionTick:
    symbol: str
    broker_symbol: str
    bid: float = 0.0
    ask: float = 0.0
    last: float = 0.0
    volume: float = 0.0
    spread: float = 0.0
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return to_plain_dict(self)


@dataclass
class FusionBar:
    symbol: str
    broker_symbol: str
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return to_plain_dict(self)


@dataclass
class FusionContract:
    symbol: str
    broker_symbol: str
    asset_type: AssetType | str = AssetType.UNKNOWN
    digits: int = 0
    point: float = 0.0
    tick_size: float = 0.0
    tick_value: float = 0.0
    point_value: float = 0.0
    min_lot: float = 0.0
    lot_step: float = 0.0
    max_lot: float = 0.0
    spread: float = 0.0
    currency_profit: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return to_plain_dict(self)


@dataclass
class FusionOrder:
    order_id: str
    symbol: str
    broker_symbol: str
    strategy: str
    timeframe: str
    direction: TradeDirection | str
    volume: float = 0.0
    price: float = 0.0
    sl: float = 0.0
    tp: float = 0.0
    magic: int = 0
    status: OrderStatus | str = OrderStatus.PENDING
    reason: str = ""
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_active(self) -> bool:
        return str(self.status) in {
            OrderStatus.PENDING.value,
            OrderStatus.SENT.value,
            OrderStatus.PART_FILLED.value,
        }

    def to_dict(self) -> dict[str, Any]:
        return to_plain_dict(self)


@dataclass
class FusionTrade:
    trade_id: str
    order_id: str
    symbol: str
    broker_symbol: str
    direction: TradeDirection | str
    volume: float
    price: float
    profit: float = 0.0
    strategy: str = ""
    timeframe: str = ""
    timestamp: str = field(default_factory=_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_plain_dict(self)


@dataclass
class FusionPosition:
    position_id: str
    symbol: str
    broker_symbol: str
    direction: TradeDirection | str
    volume: float
    price_open: float = 0.0
    price_current: float = 0.0
    profit: float = 0.0
    magic: int = 0
    updated_at: str = field(default_factory=_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_plain_dict(self)


@dataclass
class FusionAccount:
    account_id: str
    balance: float = 0.0
    equity: float = 0.0
    margin: float = 0.0
    free_margin: float = 0.0
    currency: str = ""
    updated_at: str = field(default_factory=_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_plain_dict(self)


@dataclass
class FusionSignal:
    symbol: str
    broker_symbol: str
    timeframe: str
    strategy: str
    direction: TradeDirection | str
    p_buy: float = 0.0
    p_sell: float = 0.0
    raw_prediction: int = 0
    timestamp: str = field(default_factory=_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_plain_dict(self)


@dataclass
class FusionDecision:
    symbol: str
    broker_symbol: str
    timeframe: str
    strategy: str
    direction: TradeDirection | str
    decision: DecisionAction | str
    final_action: str = ""
    p_buy: float = 0.0
    p_sell: float = 0.0
    confidence: float = 0.0
    reasons: list[str] = field(default_factory=list)
    positive_factors: list[str] = field(default_factory=list)
    negative_factors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    engine_states: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_plain_dict(self)
