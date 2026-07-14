from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from fusion.strategies.base import BaseStrategy, StrategyContext, StrategyDecision


class Estrategia7(BaseStrategy):
    name = "strategy7"
    tag = "S7"

    def _cfg(self) -> dict:
        return self.app._strategy_config(self.name)

    def _cfg_list(self, key: str, default: list[str]) -> list[str]:
        value = self._cfg().get(key, default)
        if value in (None, "all"):
            return list(default)
        if isinstance(value, str):
            return [item.strip().upper() for item in value.split(",") if item.strip()]
        return [str(item).upper() for item in value]

    @staticmethod
    def _adx(frame: pd.DataFrame, period: int = 14) -> pd.Series:
        high = frame["high"].astype(float)
        low = frame["low"].astype(float)
        close = frame["close"].astype(float)
        tr = pd.concat(
            [
                high - low,
                (high - close.shift(1)).abs(),
                (low - close.shift(1)).abs(),
            ],
            axis=1,
        ).max(axis=1)
        up_move = high.diff()
        down_move = -low.diff()
        plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=frame.index)
        minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=frame.index)
        atr = tr.rolling(period).mean()
        plus_di = 100 * plus_dm.rolling(period).mean() / (atr + 1e-12)
        minus_di = 100 * minus_dm.rolling(period).mean() / (atr + 1e-12)
        dx = ((plus_di - minus_di).abs() / ((plus_di + minus_di) + 1e-12)) * 100
        return dx.rolling(period).mean()

    @staticmethod
    def _stochastic(frame: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> tuple[pd.Series, pd.Series]:
        high = frame["high"].astype(float)
        low = frame["low"].astype(float)
        close = frame["close"].astype(float)
        lowest = low.rolling(k_period).min()
        highest = high.rolling(k_period).max()
        k = 100 * (close - lowest) / ((highest - lowest) + 1e-12)
        d = k.rolling(d_period).mean()
        return k, d

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
        bars = int(self._cfg().get("bars", 260) or 260)
        rates = self.app.mt5.copy_rates_from_pos(broker_symbol, tf_code, 0, bars)
        if rates is None or len(rates) < 220:
            return pd.DataFrame()
        frame = pd.DataFrame(rates).sort_values("time").reset_index(drop=True)
        frame["time"] = pd.to_datetime(frame["time"], unit="s")
        return frame

    @staticmethod
    def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
        delta = close.astype(float).diff()
        gain = delta.where(delta > 0, 0.0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
        rs = gain / (loss + 1e-12)
        return 100 - (100 / (1 + rs))

    def _setup(self, context: StrategyContext) -> tuple[int, dict[str, Any]]:
        cfg = self._cfg()
        allowed_symbols = set(self._cfg_list("symbols", ["EURUSD", "GOLD", "XAUUSD", "BTCUSD"]))
        symbol = context.symbol.upper()
        broker_symbol = context.broker_symbol.upper()
        if allowed_symbols and symbol not in allowed_symbols and broker_symbol not in allowed_symbols:
            return 0, {"reason": "symbol_not_allowed"}
        allowed_timeframes = set(self._cfg_list("timeframes", ["M15", "M30", "H1", "H4"]))
        if context.timeframe.upper() not in allowed_timeframes:
            return 0, {"reason": "timeframe_not_allowed"}

        frame = self._market_frame(context.broker_symbol, context.timeframe)
        if frame.empty:
            return 0, {"reason": "sem_rates"}

        close = frame["close"].astype(float)
        high = frame["high"].astype(float)
        low = frame["low"].astype(float)
        ema50 = close.ewm(span=int(cfg.get("ma_fast", 50) or 50), adjust=False).mean()
        ema200 = close.ewm(span=int(cfg.get("ma_slow", 200) or 200), adjust=False).mean()
        adx = self._adx(frame, int(cfg.get("adx_period", 14) or 14))
        rsi = self._rsi(close, int(cfg.get("rsi_period", 14) or 14))
        stoch_k, stoch_d = self._stochastic(
            frame,
            int(cfg.get("stoch_k_period", 14) or 14),
            int(cfg.get("stoch_d_period", 3) or 3),
        )

        row = frame.iloc[-2] if bool(cfg.get("use_closed_candle", True)) and len(frame) >= 2 else frame.iloc[-1]
        idx = row.name
        prev_idx = max(int(idx) - 1, 0)
        adx_value = float(adx.iloc[idx]) if np.isfinite(adx.iloc[idx]) else 0.0
        min_adx = float(cfg.get("min_adx", 25.0) or 25.0)
        if adx_value < min_adx:
            return 0, {"reason": "adx_fraco", "adx": adx_value}

        price = float(close.iloc[idx])
        ema50_value = float(ema50.iloc[idx])
        ema200_value = float(ema200.iloc[idx])
        rsi_now = float(rsi.iloc[idx]) if np.isfinite(rsi.iloc[idx]) else 50.0
        rsi_prev = float(rsi.iloc[prev_idx]) if np.isfinite(rsi.iloc[prev_idx]) else rsi_now
        k_now = float(stoch_k.iloc[idx]) if np.isfinite(stoch_k.iloc[idx]) else 50.0
        k_prev = float(stoch_k.iloc[prev_idx]) if np.isfinite(stoch_k.iloc[prev_idx]) else k_now
        d_now = float(stoch_d.iloc[idx]) if np.isfinite(stoch_d.iloc[idx]) else 50.0

        pullback_tolerance = float(cfg.get("pullback_tolerance_pct", 0.004) or 0.004)
        rsi_buy_level = float(cfg.get("rsi_buy_reclaim", 50.0) or 50.0)
        rsi_sell_level = float(cfg.get("rsi_sell_reject", 50.0) or 50.0)
        stoch_buy_level = float(cfg.get("stoch_oversold", 25.0) or 25.0)
        stoch_sell_level = float(cfg.get("stoch_overbought", 75.0) or 75.0)
        min_model_prob = float(cfg.get("min_model_probability", 0.60) or 0.60)
        require_model_alignment = bool(cfg.get("require_model_alignment", True))

        near_ema50 = abs(price - ema50_value) / max(abs(price), 1e-12) <= pullback_tolerance
        bullish_trend = price > ema200_value and ema50_value > ema200_value
        bearish_trend = price < ema200_value and ema50_value < ema200_value
        rsi_buy_reclaim = rsi_prev <= rsi_buy_level and rsi_now > rsi_buy_level
        rsi_sell_reject = rsi_prev >= rsi_sell_level and rsi_now < rsi_sell_level
        stoch_buy_reclaim = k_prev <= stoch_buy_level and k_now > stoch_buy_level and k_now >= d_now
        stoch_sell_reject = k_prev >= stoch_sell_level and k_now < stoch_sell_level and k_now <= d_now

        metadata = {
            "setup": "trend_pullback_ma50_200_adx_rsi_stoch",
            "close": price,
            "ema50": ema50_value,
            "ema200": ema200_value,
            "adx14": adx_value,
            "rsi14": rsi_now,
            "rsi14_prev": rsi_prev,
            "stoch_k": k_now,
            "stoch_d": d_now,
            "near_ema50": near_ema50,
            "signal_time": str(row.get("time", "")),
        }

        buy_ok = bullish_trend and near_ema50 and (rsi_buy_reclaim or stoch_buy_reclaim)
        sell_ok = bearish_trend and near_ema50 and (rsi_sell_reject or stoch_sell_reject)
        pred = 1 if buy_ok else 2 if sell_ok else 0
        if pred == 0:
            metadata["reason"] = "sem_pullback_confirmado"
            metadata.update({
                "bullish_trend": bullish_trend,
                "bearish_trend": bearish_trend,
                "rsi_buy_reclaim": rsi_buy_reclaim,
                "rsi_sell_reject": rsi_sell_reject,
                "stoch_buy_reclaim": stoch_buy_reclaim,
                "stoch_sell_reject": stoch_sell_reject,
            })
            return 0, metadata

        if require_model_alignment:
            model_prob = context.p_buy if pred == 1 else context.p_sell
            if context.prediction not in (0, pred) or model_prob < min_model_prob:
                metadata["reason"] = "modelo_nao_confirma"
                metadata["model_prediction"] = context.prediction
                metadata["model_probability"] = model_prob
                metadata["min_model_probability"] = min_model_prob
                return 0, metadata

        metadata["reason"] = "trend_pullback_confirmado"
        metadata["trigger"] = "rsi" if (rsi_buy_reclaim or rsi_sell_reject) else "stochastic"
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
