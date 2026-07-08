from __future__ import annotations

from fusion.strategies.base import BaseStrategy, StrategyContext, StrategyDecision


class Estrategia4(BaseStrategy):
    name = "strategy4"
    tag = "S4"

    def evaluate(self, context: StrategyContext, last_trade_time: dict) -> StrategyDecision:
        if not self.enabled() or context.approved_model or not context.model:
            return StrategyDecision(tag=self.tag)
        if not self.app._is_gold_symbol(context.symbol) or context.prediction not in (1, 2):
            return StrategyDecision(tag=self.tag)

        pred = self._strategy_pred(context.prediction)
        if pred != 1:
            self.app.logger.info(f"S4 GOLD {context.timeframe} ignora sinal SELL")
            reason = "sell_ignored:gold_s4_buy_only"
            self.app._audit_strategy_block_with_shadow(
                self.name,
                pred,
                context.broker_symbol,
                context.symbol,
                context.timeframe,
                reason,
                context.p_buy,
                context.p_sell,
                model=context.model,
                approved_model=context.approved_model,
                approved_status=context.approved_status,
                extra={"strategy4_reason": reason},
            )
            return StrategyDecision(tag=self.tag, prediction=pred, message=reason)
        if not self._cooldown_ready(context, last_trade_time):
            reason = self.app._last_execution_block_reason or "cooldown"
            self.app._audit_strategy_block_with_shadow(
                self.name,
                pred,
                context.broker_symbol,
                context.symbol,
                context.timeframe,
                reason,
                context.p_buy,
                context.p_sell,
                model=context.model,
                approved_model=context.approved_model,
                approved_status=context.approved_status,
                extra={"strategy4_reason": reason},
            )
            return StrategyDecision(tag=self.tag, prediction=pred, message=reason)
        if not self.app._strategy4_insidebar_buy_allowed(context.broker_symbol, context.symbol, context.timeframe):
            reason = self.app._last_strategy4_setup_reason or "setup_block"
            self.app._audit_strategy_block_with_shadow(
                self.name,
                pred,
                context.broker_symbol,
                context.symbol,
                context.timeframe,
                reason,
                context.p_buy,
                context.p_sell,
                model=context.model,
                approved_model=context.approved_model,
                approved_status=context.approved_status,
                extra={
                    "strategy4_reason": reason,
                    "strategy4_setup": self.app._last_strategy4_setup_details,
                },
            )
            return StrategyDecision(tag=self.tag, prediction=pred, message=reason)

        result = self._execute(pred, context)
        decision = StrategyDecision(tag=self.tag, attempted=True, prediction=pred)
        if result and result.success:
            self._mark_trade_time(context, last_trade_time)
            decision.executed = True
        elif result:
            decision.message = result.message
        else:
            decision.message = self.app._last_execution_block_reason
        return decision
