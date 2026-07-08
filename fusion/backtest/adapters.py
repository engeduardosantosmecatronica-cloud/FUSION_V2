from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import uuid4

from fusion.core.enums import OrderStatus
from fusion.core.objects import FusionAccount, FusionContract, FusionOrder, FusionPosition, FusionTick
from fusion.execution.oms import FusionOMS


class BrokerAdapter(ABC):
    @abstractmethod
    def account(self) -> FusionAccount:
        raise NotImplementedError

    @abstractmethod
    def positions(self, symbol: str | None = None) -> list[FusionPosition]:
        raise NotImplementedError

    @abstractmethod
    def contract(self, symbol: str) -> FusionContract | None:
        raise NotImplementedError

    @abstractmethod
    def last_tick(self, symbol: str) -> FusionTick | None:
        raise NotImplementedError

    @abstractmethod
    def send_order(self, order: FusionOrder) -> FusionOrder:
        raise NotImplementedError


class BacktestBrokerAdapter(BrokerAdapter):
    def __init__(self, oms: FusionOMS, account: FusionAccount | None = None) -> None:
        self.oms = oms
        self._account = account or FusionAccount(account_id="BACKTEST", balance=10000.0, equity=10000.0, currency="USD")
        self.oms.update_account(self._account)

    def account(self) -> FusionAccount:
        return self._account

    def positions(self, symbol: str | None = None) -> list[FusionPosition]:
        return self.oms.get_positions(symbol)

    def contract(self, symbol: str) -> FusionContract | None:
        return self.oms.get_contract(symbol)

    def last_tick(self, symbol: str) -> FusionTick | None:
        return self.oms.get_last_tick(symbol)

    def send_order(self, order: FusionOrder) -> FusionOrder:
        if not order.order_id:
            order.order_id = uuid4().hex
        order.status = OrderStatus.SENT
        order.metadata.setdefault("adapter", "backtest")
        self.oms.update_order(order)
        return order

    def update_tick(self, tick: FusionTick) -> None:
        self.oms.update_tick(tick)

    def update_contract(self, contract: FusionContract) -> None:
        self.oms.update_contract(contract)

    def snapshot(self) -> dict[str, Any]:
        return self.oms.snapshot()

