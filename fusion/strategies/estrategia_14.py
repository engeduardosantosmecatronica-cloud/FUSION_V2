from __future__ import annotations

from typing import Any

import pandas as pd

from fusion.features.pattern_state import PatternStateConfig, build_pattern_state_features
from fusion.strategies.base import BaseStrategy, StrategyContext, StrategyDecision


class Estrategia14(BaseStrategy):
    name = "strategy14"
    tag = "S14"

    def _cfg(self) -> dict:
        return self.app._strategy_config(self.name)

    def _cfg_list(self, key: str, default: list[str]) -> list[str]:
        value = self._cfg().get(key, default)
        if value in (None, "all"):
            return list(default)
        if isinstance(value, str):
            return [item.strip().upper() for item in value.split(",") if item.strip()]
        return [str(item).upper() for item in value]

    def _market_frame(self, broker_symbol: str, timeframe: str) -> pd.DataFrame:
        if self.app.mt5 is None:
            return pd.DataFrame()
        tf_code = {
            "M5": self.app.mt5.TIMEFRAME_M5,
            "M15": self.app.mt5.TIMEFRAME_M15,
            "M30": self.app.mt5.TIMEFRAME_M30,
            "H1": self.app.mt5.TIMEFRAME_H1,
            "H4": self.app.mt5.TIMEFRAME_H4,
            "D1": self.app.mt5.TIMEFRAME_D1,
        }.get(timeframe.upper())
        if not tf_code:
            return pd.DataFrame()
        bars = int(self._cfg().get("bars", 360) or 360)
        rates = self.app.mt5.copy_rates_from_pos(broker_symbol, tf_code, 0, bars)
        if rates is None or len(rates) < 160:
            return pd.DataFrame()
        frame = pd.DataFrame(rates).sort_values("time").reset_index(drop=True)
        frame["time"] = pd.to_datetime(frame["time"], unit="s")
        return frame

    def _setup(self, context: StrategyContext) -> tuple[int, dict[str, Any]]:
        cfg = self._cfg()
        symbols = set(self._cfg_list("symbols", ["EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "GOLD", "XAUUSD"]))
        symbol = context.symbol.upper()
        broker_symbol = context.broker_symbol.upper()
        if symbols and symbol not in symbols and broker_symbol not in symbols:
            return 0, {"reason": "symbol_not_allowed"}
        timeframes = set(self._cfg_list("timeframes", ["M15", "M30", "H1", "H4"]))
        if context.timeframe.upper() not in timeframes:
            return 0, {"reason": "timeframe_not_allowed"}

        frame = self._market_frame(context.broker_symbol, context.timeframe)
        if frame.empty:
            return 0, {"reason": "sem_rates"}
        features = build_pattern_state_features(frame, PatternStateConfig())
        if features.empty:
            return 0, {"reason": "sem_pattern_state"}
        idx = -2 if bool(cfg.get("use_closed_candle", True)) and len(features) >= 2 else -1
        row = features.iloc[idx]
        min_score = int(cfg.get("min_score", 3) or 3)
        buy_score = int(row.get("best_pattern_buy_score", 0) or 0)
        sell_score = int(row.get("best_pattern_sell_score", 0) or 0)
        pred = int(row.get("pattern_score_signal", 0) or 0)
        if pred == 1 and buy_score < min_score:
            pred = 0
        if pred == 2 and sell_score < min_score:
            pred = 0

        metadata = {
            "setup": "pattern_score_3of3",
            "pattern_score_name": str(row.get("pattern_score_name", "none")),
            "best_pattern_buy": str(row.get("best_pattern_buy", "")),
            "best_pattern_sell": str(row.get("best_pattern_sell", "")),
            "best_pattern_buy_score": buy_score,
            "best_pattern_sell_score": sell_score,
            "regime": str(row.get("regime", "")),
            "estrutura": str(row.get("estrutura", "")),
            "momentum": str(row.get("momentum", "")),
            "volume_state": str(row.get("volume_state", "")),
            "volatilidade": str(row.get("volatilidade", "")),
            "pattern_key": str(row.get("pattern_key", "")),
            "signal_time": str(row.get("time", "")),
        }
        score_cols = [col for col in features.columns if col.startswith("score_")]
        for col in score_cols:
            value = row.get(col, 0)
            try:
                if int(value) >= min_score:
                    metadata[col] = int(value)
            except (TypeError, ValueError):
                continue

        if pred not in (1, 2):
            metadata["reason"] = "sem_score_3de3"
            return 0, metadata

        if bool(cfg.get("require_model_alignment", True)):
            min_model_prob = float(cfg.get("min_model_probability", 0.58) or 0.58)
            model_prob = context.p_buy if pred == 1 else context.p_sell
            if context.prediction not in (0, pred) or model_prob < min_model_prob:
                metadata.update({
                    "reason": "modelo_nao_confirma",
                    "model_prediction": context.prediction,
                    "model_probability": model_prob,
                    "min_model_probability": min_model_prob,
                })
                return 0, metadata
        metadata["reason"] = "pattern_score_3de3_confirmado"
        return pred, metadata

    def evaluate(self, context: StrategyContext, last_trade_time: dict) -> StrategyDecision:
        if not self.enabled():
            return StrategyDecision(tag=self.tag)
        pred, feature_row = self._setup(context)
        if pred not in (1, 2):
            return StrategyDecision(tag=self.tag, feature_row=feature_row, message=str(feature_row.get("reason", "sem_setup")))
        pred = self._strategy_pred(pred)
        if pred not in (1, 2):
            return StrategyDecision(tag=self.tag, feature_row=feature_row, message="sem_direcao")
        if not self._cooldown_ready(context, last_trade_time):
            return StrategyDecision(tag=self.tag, prediction=pred, feature_row=feature_row, message="cooldown")
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
