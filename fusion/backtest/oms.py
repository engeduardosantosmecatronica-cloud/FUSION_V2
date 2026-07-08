from __future__ import annotations

from uuid import uuid4

from fusion.core.enums import OrderStatus, TradeDirection
from fusion.core.objects import FusionOrder, FusionPosition, FusionTrade
from fusion.execution.oms import FusionOMS


class BacktestOMS(FusionOMS):
    def fill_order(self, order_id: str, fill_price: float) -> FusionPosition | None:
        order = self.orders.get(str(order_id))
        if order is None:
            return None
        order.status = OrderStatus.FILLED
        order.price = float(fill_price)
        self.update_order(order)
        position = FusionPosition(
            position_id=str(order.order_id),
            symbol=order.symbol,
            broker_symbol=order.broker_symbol,
            direction=order.direction,
            volume=order.volume,
            price_open=float(fill_price),
            price_current=float(fill_price),
            magic=order.magic,
            metadata={"strategy": order.strategy, "timeframe": order.timeframe},
        )
        self.update_position(position)
        return position

    def close_position(self, position_id: str, price: float, reason: str = "") -> FusionTrade | None:
        position = self.positions.pop(str(position_id), None)
        if position is None:
            return None
        direction = str(position.direction)
        pnl = (float(price) - position.price_open) if direction == TradeDirection.BUY.value else (position.price_open - float(price))
        trade = FusionTrade(
            trade_id=uuid4().hex,
            order_id=str(position.position_id),
            symbol=position.symbol,
            broker_symbol=position.broker_symbol,
            direction=position.direction,
            volume=position.volume,
            price=float(price),
            profit=pnl,
            strategy=str(position.metadata.get("strategy", "")),
            timeframe=str(position.metadata.get("timeframe", "")),
            metadata={"reason": reason},
        )
        self.update_trade(trade)
        return trade

