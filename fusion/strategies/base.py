from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class StrategyContext:
    broker_symbol: str
    symbol: str
    timeframe: str
    prediction: int
    p_buy: float
    p_sell: float
    now: datetime
    model: Any = None
    approved_model: Any = None
    approved_status: str = ""
    feature_row: dict = field(default_factory=dict)


@dataclass
class StrategyDecision:
    tag: str
    executed: bool = False
    attempted: bool = False
    message: str = ""
    prediction: int = 0
    feature_row: dict = field(default_factory=dict)


class BaseStrategy:
    name = ""
    tag = ""

    def __init__(self, app: Any):
        self.app = app

    def enabled(self) -> bool:
        return self.app._strategy_enabled(self.name)

    def evaluate(self, context: StrategyContext, last_trade_time: dict) -> StrategyDecision:
        raise NotImplementedError

    def _cooldown_ready(self, context: StrategyContext, last_trade_time: dict) -> bool:
        key = (self.name, context.symbol, context.timeframe)
        elapsed = (context.now - last_trade_time.get(key, context.now)).total_seconds()
        memory_ready = key not in last_trade_time or elapsed >= self.app._strategy_cooldown(self.name)
        if not memory_ready:
            return False
        remaining = self.app._recent_close_cooldown_remaining(
            self.name,
            context.broker_symbol,
            context.symbol,
            context.timeframe,
        )
        if remaining > 0:
            self.app._last_execution_block_reason = f"cooldown_pos_fechamento:{remaining}s"
            return False
        return True

    def _mark_trade_time(self, context: StrategyContext, last_trade_time: dict) -> None:
        last_trade_time[(self.name, context.symbol, context.timeframe)] = context.now

    def _strategy_pred(self, pred: int) -> int:
        return self.app._strategy_prediction(self.name, pred)

    def _execute(self, pred: int, context: StrategyContext, feature_row: dict | None = None):
        result = self.app._execute_strategy_order(
            self.name,
            pred,
            context.broker_symbol,
            context.symbol,
            context.timeframe,
            feature_row or {},
            context.p_buy,
            context.p_sell,
            model=context.model,
            approved_model=context.approved_model,
            approved_status=context.approved_status,
        )
        if result is None:
            reason = self.app._last_execution_block_reason or "sem_motivo_registrado"
            direction = "BUY" if pred == 1 else "SELL" if pred == 2 else "WAIT"
            self.app.logger.info(
                f"{self.tag} {context.symbol} {context.timeframe} {direction} tentativa_sem_ordem: {reason}"
            )
        return result

