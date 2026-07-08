from __future__ import annotations

from fusion.strategies.base import BaseStrategy, StrategyContext, StrategyDecision


class Estrategia5(BaseStrategy):
    name = "strategy5"
    tag = "S5"

    def evaluate(self, context: StrategyContext, last_trade_time: dict) -> StrategyDecision:
        if not self.enabled() or not context.approved_model:
            return StrategyDecision(tag=self.tag)
        if self.app._is_gold_symbol(context.symbol) or context.prediction not in (1, 2):
            return StrategyDecision(tag=self.tag)
        if not self._cooldown_ready(context, last_trade_time):
            return StrategyDecision(tag=self.tag, message="cooldown")

        pred = self._strategy_pred(context.prediction)
        feature_row = self.app._approved_feature_row(context.symbol, context.timeframe)
        result = self._execute(pred, context, feature_row)
        decision = StrategyDecision(tag=self.tag, attempted=True, prediction=pred, feature_row=feature_row)
        if result and result.success:
            self._mark_trade_time(context, last_trade_time)
            decision.executed = True
        elif result:
            decision.message = result.message
        else:
            decision.message = self.app._last_execution_block_reason
        return decision
