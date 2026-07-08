from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from fusion.strategies.base import BaseStrategy, StrategyContext, StrategyDecision

try:
    from fusion_refatorado.fusion_best.expert_training import build_expert_feature_frame
except Exception:
    build_expert_feature_frame = None


class Estrategia6(BaseStrategy):
    name = "strategy6"
    tag = "S6"

    def _cfg_list(self, key: str, default: list[str]) -> list[str]:
        value = self.app._strategy_config(self.name).get(key, default)
        if value in (None, "all"):
            return list(default)
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return list(value)

    def _selected_features(self) -> list[str]:
        return self._cfg_list(
            "enabled_features",
            [
                "ret",
                "ret_5",
                "ret_10",
                "ret_20",
                "rsi14",
                "rsi28",
                "rsi_diff",
                "rsi_ma5",
                "rsi_gap",
                "dist_ema8",
                "dist_ema21",
                "dist_ema50",
                "dist_ema200",
                "range_pct",
                "range_ma10",
                "position_in_range",
                "vol5",
                "vol20",
                "vol_ratio",
                "macd",
                "macd_signal",
                "macd_hist",
                "alpha_vam",
                "alpha_effort",
                "alpha_mrs",
                "alpha_rsi_gap",
                "trend_alignment",
            ],
        )

    def _selected_omnis_features(self) -> list[str]:
        return self._cfg_list(
            "enabled_omnis_features",
            [
                "omnis_trend_signal",
                "omnis_trend_confidence",
                "omnis_trend_probability",
                "omnis_rsi",
                "omnis_adx",
                "omnis_plus_di",
                "omnis_minus_di",
                "omnis_macd",
                "omnis_macd_hist",
                "omnis_pullback_buy",
                "omnis_pullback_sell",
                "omnis_at_support",
                "omnis_at_resistance",
                "omnis_exhaustion_signal",
                "omnis_bullish_divergence",
                "omnis_bearish_divergence",
                "omnis_stat_zscore",
                "omnis_trend_slope_21",
                "omnis_trend_slope_50",
            ],
        )

    def _selected_experts(self) -> list[str]:
        return self._cfg_list(
            "enabled_experts",
            ["trend", "orderflow", "sr", "reversal", "pullback", "quant", "candles", "risk", "volatility"],
        )

    @staticmethod
    def _clean(value: Any) -> Any:
        if isinstance(value, (np.integer,)):
            return int(value)
        if isinstance(value, (np.floating,)):
            if not np.isfinite(value):
                return None
            return float(value)
        if isinstance(value, float) and not np.isfinite(value):
            return None
        if isinstance(value, pd.Timestamp):
            return value.isoformat()
        return value

    def _row_values(self, frame: pd.DataFrame, columns: list[str]) -> dict:
        if frame is None or frame.empty:
            return {}
        row = frame.tail(1).iloc[0]
        result = {}
        for col in columns:
            if col in row.index:
                result[col] = self._clean(row[col])
        return result

    def _market_frame(self, broker_symbol: str, timeframe: str) -> pd.DataFrame:
        tf_code = {
            "M5": self.app.mt5.TIMEFRAME_M5,
            "M15": self.app.mt5.TIMEFRAME_M15,
            "M30": self.app.mt5.TIMEFRAME_M30,
            "H1": self.app.mt5.TIMEFRAME_H1,
            "H4": self.app.mt5.TIMEFRAME_H4,
            "D1": self.app.mt5.TIMEFRAME_D1,
        }.get(timeframe)
        if not tf_code:
            return pd.DataFrame()
        bars = int(self.app._strategy_config(self.name).get("bars", 1200))
        rates = self.app.mt5.copy_rates_from_pos(broker_symbol, tf_code, 0, bars)
        if rates is None or len(rates) < 100:
            return pd.DataFrame()
        frame = pd.DataFrame(rates)
        frame["time"] = pd.to_datetime(frame["time"], unit="s")
        return frame.set_index("time").sort_index()

    def _omnis_snapshot(self, broker_symbol: str, timeframe: str) -> tuple[pd.DataFrame, dict]:
        if build_expert_feature_frame is None:
            return pd.DataFrame(), {}
        market = self._market_frame(broker_symbol, timeframe)
        if market.empty:
            return pd.DataFrame(), {}
        try:
            omnis = build_expert_feature_frame(market)
        except Exception as exc:
            return pd.DataFrame(), {"error": str(exc)}
        return omnis, self._row_values(omnis, self._selected_omnis_features())

    def _expert_votes(self, context: StrategyContext, omnis_frame: pd.DataFrame) -> dict:
        approved = self.app.approved_models.get((context.symbol.upper(), context.timeframe.upper()))
        if not approved or omnis_frame.empty:
            return {}
        selected = set(self._selected_experts())
        votes = {}
        for member in approved.members:
            if member.expert not in selected:
                continue
            missing = [col for col in member.feature_columns if col not in omnis_frame.columns]
            if missing:
                votes[member.expert] = {"enabled": True, "error": f"missing_features:{len(missing)}"}
                continue
            row = omnis_frame[member.feature_columns].tail(1).replace([np.inf, -np.inf], np.nan)
            if row.isna().any(axis=None):
                votes[member.expert] = {"enabled": True, "error": "nan_features"}
                continue
            try:
                raw_pred = int(member.model.predict(row)[0])
                direction = approved._direction(member, raw_pred, omnis_frame)
                confidence = approved._confidence(member.model, row, raw_pred)
                votes[member.expert] = {
                    "enabled": True,
                    "raw_prediction": raw_pred,
                    "direction": direction,
                    "confidence": float(confidence),
                    "weight": float(member.weight),
                    "mode": member.mode,
                    "role": member.role,
                }
            except Exception as exc:
                votes[member.expert] = {"enabled": True, "error": str(exc)}
        return votes

    def _expert_signal(self, votes: dict) -> dict:
        cfg = self.app._strategy_config(self.name)
        min_confidence = float(cfg.get("expert_min_confidence", 0.55))
        min_votes = int(cfg.get("min_expert_votes", 1))
        min_score = float(cfg.get("expert_min_score", 0.25))
        buy_score = 0.0
        sell_score = 0.0
        valid_votes = 0
        used = {}
        for expert, vote in votes.items():
            if vote.get("error") or not vote.get("enabled", False):
                continue
            direction = int(vote.get("direction", 0) or 0)
            confidence = float(vote.get("confidence", 0.0) or 0.0)
            weight = float(vote.get("weight", 0.0) or 0.0)
            if direction == 0 or confidence < min_confidence:
                continue
            score = weight * confidence
            if direction > 0:
                buy_score += score
            else:
                sell_score += score
            valid_votes += 1
            used[expert] = vote

        net_score = buy_score - sell_score
        prediction = 0
        if valid_votes >= min_votes and abs(net_score) >= min_score:
            prediction = 1 if net_score > 0 else 2
        return {
            "prediction": prediction,
            "buy_score": buy_score,
            "sell_score": sell_score,
            "net_score": net_score,
            "valid_votes": valid_votes,
            "used_votes": used,
        }

    def _feature_candidate(self, context: StrategyContext, required_pred: int = 0) -> dict:
        candidates = []
        sides = [(1, "compra"), (2, "venda")]
        if required_pred in (1, 2):
            sides = [(required_pred, "compra" if required_pred == 1 else "venda")]
        for pred, direction in sides:
            row = self.app._strategy_feature_candidate(self.name, context.symbol, context.timeframe, pred, context.broker_symbol)
            if row:
                row = dict(row)
                row["pred"] = pred
                row["direcao"] = row.get("direcao", direction)
                candidates.append(row)
        if not candidates:
            return {}
        frame = pd.DataFrame(candidates)
        sort_cols = [col for col in ["score", "win_rate", "entradas"] if col in frame.columns]
        if sort_cols:
            frame = frame.sort_values(sort_cols, ascending=[False] * len(sort_cols))
        return frame.iloc[0].to_dict()

    def _log_loop(self, payload: dict) -> None:
        cfg = self.app._strategy_config(self.name)
        if not bool(cfg.get("log_each_loop", True)):
            return
        log_dir = Path(cfg.get("log_dir", "logs/strategy6"))
        if not log_dir.is_absolute():
            log_dir = Path.cwd() / log_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        path = log_dir / f"strategy6_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")

    def diagnostic_snapshot(self, context: StrategyContext) -> dict:
        system_features = {}
        try:
            frame = self.app._calculate_features(context.broker_symbol, context.timeframe)
            system_features = self._row_values(frame, self._selected_features())
        except Exception as exc:
            system_features = {"error": str(exc)}
        omnis_frame, omnis_features = self._omnis_snapshot(context.broker_symbol, context.timeframe)
        expert_votes = self._expert_votes(context, omnis_frame)
        expert_signal = self._expert_signal(expert_votes)
        required_pred = int(expert_signal.get("prediction", 0) or 0)
        feature_candidate = self._feature_candidate(context, required_pred=required_pred) if self.enabled() else {}
        payload = {
            "timestamp": context.now.isoformat(),
            "symbol": context.symbol,
            "broker_symbol": context.broker_symbol,
            "timeframe": context.timeframe,
            "enabled": self.enabled(),
            "selectors": {
                "features": self._selected_features(),
                "omnis_features": self._selected_omnis_features(),
                "experts": self._selected_experts(),
            },
            "system_features": system_features,
            "omnis_features": omnis_features,
            "expert_votes": expert_votes,
            "expert_signal": expert_signal,
            "feature_rule_candidate": feature_candidate,
        }
        self._log_loop(payload)
        return payload

    def evaluate(self, context: StrategyContext, last_trade_time: dict) -> StrategyDecision:
        if not self.enabled() or self.app._is_gold_symbol(context.symbol):
            return StrategyDecision(tag=self.tag)
        snapshot = self.diagnostic_snapshot(context)
        cfg = self.app._strategy_config(self.name)
        expert_signal = snapshot.get("expert_signal", {}) or {}
        expert_pred = int(expert_signal.get("prediction", 0) or 0)
        if bool(cfg.get("require_expert_confirmation", True)) and expert_pred not in (1, 2):
            return StrategyDecision(tag=self.tag, message="sem_confirmacao_expert")

        feature_row = snapshot.get("feature_rule_candidate", {}) or {}
        if bool(cfg.get("require_feature_rule", True)) and not feature_row:
            return StrategyDecision(tag=self.tag, message="sem_feature")
        pred = expert_pred if expert_pred in (1, 2) else int(feature_row.get("pred", 0) or 0)
        if feature_row and int(feature_row.get("pred", pred) or pred) != pred:
            return StrategyDecision(tag=self.tag, feature_row=feature_row, message="feature_conflita_com_expert")
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
