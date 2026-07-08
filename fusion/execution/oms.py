from __future__ import annotations

from collections import deque
from threading import RLock
from typing import Any

from fusion.core.objects import (
    FusionAccount,
    FusionContract,
    FusionOrder,
    FusionPosition,
    FusionTick,
    FusionTrade,
)


class FusionOMS:
    """OMS leve em memória para estado operacional do robô."""

    def __init__(self, max_history: int = 500) -> None:
        self.max_history = max_history
        self.orders: dict[str, FusionOrder] = {}
        self.trades: deque[FusionTrade] = deque(maxlen=max_history)
        self.positions: dict[str, FusionPosition] = {}
        self.ticks: dict[str, FusionTick] = {}
        self.contracts: dict[str, FusionContract] = {}
        self.account: FusionAccount | None = None
        self._lock = RLock()

    def update_tick(self, tick: FusionTick) -> None:
        with self._lock:
            self.ticks[tick.symbol.upper()] = tick

    def update_order(self, order: FusionOrder) -> None:
        with self._lock:
            self.orders[str(order.order_id)] = order

    def update_trade(self, trade: FusionTrade) -> None:
        with self._lock:
            self.trades.append(trade)

    def update_position(self, position: FusionPosition) -> None:
        with self._lock:
            self.positions[str(position.position_id)] = position

    def update_account(self, account: FusionAccount) -> None:
        with self._lock:
            self.account = account

    def update_contract(self, contract: FusionContract) -> None:
        with self._lock:
            self.contracts[contract.symbol.upper()] = contract

    def get_active_orders(self, symbol: str | None = None) -> list[FusionOrder]:
        with self._lock:
            orders = [order for order in self.orders.values() if order.is_active()]
            if symbol:
                orders = [order for order in orders if order.symbol.upper() == symbol.upper()]
            return list(orders)

    def get_positions(self, symbol: str | None = None) -> list[FusionPosition]:
        with self._lock:
            positions = list(self.positions.values())
            if symbol:
                positions = [pos for pos in positions if pos.symbol.upper() == symbol.upper()]
            return positions

    def get_last_tick(self, symbol: str) -> FusionTick | None:
        with self._lock:
            return self.ticks.get(symbol.upper())

    def get_contract(self, symbol: str) -> FusionContract | None:
        with self._lock:
            return self.contracts.get(symbol.upper())

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "account": self.account.to_dict() if self.account else {},
                "orders": [order.to_dict() for order in self.orders.values()],
                "active_orders": [order.to_dict() for order in self.orders.values() if order.is_active()],
                "trades": [trade.to_dict() for trade in self.trades],
                "positions": [position.to_dict() for position in self.positions.values()],
                "ticks": [tick.to_dict() for tick in self.ticks.values()],
                "contracts": [contract.to_dict() for contract in self.contracts.values()],
            }
