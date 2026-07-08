from __future__ import annotations

from fusion.strategies.base import BaseStrategy, StrategyContext, StrategyDecision


class Estrategia3(BaseStrategy):
    name = "strategy3"
    tag = "S3"

    def evaluate(self, context: StrategyContext, last_trade_time: dict) -> StrategyDecision:
        if not self.enabled() or context.approved_model or not context.model:
            return StrategyDecision(tag=self.tag)
        if self.app._is_gold_symbol(context.symbol) or context.prediction not in (1, 2):
            return StrategyDecision(tag=self.tag)

        pred = self._strategy_pred(context.prediction)
        feature_row = self.app._strategy_feature_candidate(self.name, context.symbol, context.timeframe, pred, context.broker_symbol)
        if not feature_row:
            self.app.logger.info(f"S3 sem feature aprovada: {context.symbol} {context.timeframe}")
            return StrategyDecision(tag=self.tag, prediction=pred, message="sem_feature")
        if not self._cooldown_ready(context, last_trade_time):
            return StrategyDecision(tag=self.tag, prediction=pred, feature_row=feature_row, message="cooldown")
        if not self.app._strategy_group_exposure_allowed(self.name, context.symbol, pred):
            return StrategyDecision(tag=self.tag, prediction=pred, feature_row=feature_row, message="exposure_block")

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
