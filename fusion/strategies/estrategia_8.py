from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from fusion.strategies.base import BaseStrategy, StrategyContext, StrategyDecision


class Estrategia8(BaseStrategy):
    name = "strategy8"
    tag = "S8"

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
    def _true_range(frame: pd.DataFrame) -> pd.Series:
        high = frame["high"].astype(float)
        low = frame["low"].astype(float)
        close = frame["close"].astype(float)
        return pd.concat(
            [
                high - low,
                (high - close.shift(1)).abs(),
                (low - close.shift(1)).abs(),
            ],
            axis=1,
        ).max(axis=1)

    @classmethod
    def _adx(cls, frame: pd.DataFrame, period: int = 14) -> pd.Series:
        high = frame["high"].astype(float)
        low = frame["low"].astype(float)
        tr = cls._true_range(frame)
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
    def _obv(frame: pd.DataFrame) -> pd.Series:
        close = frame["close"].astype(float)
        volume_col = "tick_volume" if "tick_volume" in frame.columns else "real_volume" if "real_volume" in frame.columns else "volume"
        volume = frame[volume_col].astype(float) if volume_col in frame.columns else pd.Series(0.0, index=frame.index)
        direction = np.sign(close.diff()).fillna(0.0)
        return (direction * volume).cumsum()

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
        if rates is None or len(rates) < 120:
            return pd.DataFrame()
        frame = pd.DataFrame(rates).sort_values("time").reset_index(drop=True)
        frame["time"] = pd.to_datetime(frame["time"], unit="s")
        return frame

    def _setup(self, context: StrategyContext) -> tuple[int, dict[str, Any]]:
        cfg = self._cfg()
        allowed_symbols = set(self._cfg_list("symbols", ["EURUSD", "GBPUSD", "BTCUSD", "GOLD", "XAUUSD"]))
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
        bb_period = int(cfg.get("bb_period", 20) or 20)
        bb_std_mult = float(cfg.get("bb_std_mult", 2.0) or 2.0)
        atr_period = int(cfg.get("atr_period", 14) or 14)
        adx_period = int(cfg.get("adx_period", 14) or 14)
        compression_lookback = int(cfg.get("compression_lookback", 80) or 80)
        use_closed = bool(cfg.get("use_closed_candle", True))

        mid = close.rolling(bb_period).mean()
        std = close.rolling(bb_period).std()
        upper = mid + bb_std_mult * std
        lower = mid - bb_std_mult * std
        bandwidth = (upper - lower) / (mid.abs() + 1e-12)
        tr = self._true_range(frame)
        atr = tr.rolling(atr_period).mean()
        adx = self._adx(frame, adx_period)
        obv = self._obv(frame)

        row = frame.iloc[-2] if use_closed and len(frame) >= 2 else frame.iloc[-1]
        idx = int(row.name)
        prev_idx = max(idx - 1, 0)
        if idx < max(bb_period, atr_period * 2, adx_period * 2, compression_lookback // 2):
            return 0, {"reason": "dados_insuficientes"}

        bw_now = float(bandwidth.iloc[idx]) if np.isfinite(bandwidth.iloc[idx]) else 0.0
        bw_window = bandwidth.iloc[max(0, idx - compression_lookback):idx].dropna()
        if bw_window.empty:
            return 0, {"reason": "sem_bandwidth"}
        bw_percentile = float((bw_window <= bw_now).mean())
        max_bw_percentile = float(cfg.get("max_bandwidth_percentile", 0.35) or 0.35)
        compressed = bw_percentile <= max_bw_percentile

        atr_now = float(atr.iloc[idx]) if np.isfinite(atr.iloc[idx]) else 0.0
        atr_prev = float(atr.iloc[prev_idx]) if np.isfinite(atr.iloc[prev_idx]) else atr_now
        atr_ma = float(atr.iloc[max(0, idx - 20):idx].mean()) if idx > 20 else atr_prev
        atr_rising = atr_now > atr_prev and atr_now >= atr_ma * float(cfg.get("min_atr_vs_ma", 0.95) or 0.95)

        adx_now = float(adx.iloc[idx]) if np.isfinite(adx.iloc[idx]) else 0.0
        adx_prev = float(adx.iloc[prev_idx]) if np.isfinite(adx.iloc[prev_idx]) else adx_now
        min_adx = float(cfg.get("min_adx", 18.0) or 18.0)
        adx_rising = adx_now >= min_adx and adx_now > adx_prev

        obv_now = float(obv.iloc[idx]) if np.isfinite(obv.iloc[idx]) else 0.0
        obv_prev = float(obv.iloc[prev_idx]) if np.isfinite(obv.iloc[prev_idx]) else obv_now
        obv_slope = obv_now - float(obv.iloc[max(0, idx - int(cfg.get("obv_slope_bars", 5) or 5))])
        obv_buy_ok = obv_now > obv_prev and obv_slope > 0
        obv_sell_ok = obv_now < obv_prev and obv_slope < 0

        close_now = float(close.iloc[idx])
        upper_now = float(upper.iloc[idx]) if np.isfinite(upper.iloc[idx]) else close_now
        lower_now = float(lower.iloc[idx]) if np.isfinite(lower.iloc[idx]) else close_now
        body = abs(float(close.iloc[idx]) - float(row.get("open", close_now)))
        candle_range = max(float(high.iloc[idx]) - float(low.iloc[idx]), 1e-12)
        min_body_ratio = float(cfg.get("min_body_to_range", 0.45) or 0.45)
        body_ok = (body / candle_range) >= min_body_ratio

        buy_breakout = close_now > upper_now
        sell_breakout = close_now < lower_now
        pred = 0
        if compressed and atr_rising and adx_rising and body_ok and buy_breakout and obv_buy_ok:
            pred = 1
        elif compressed and atr_rising and adx_rising and body_ok and sell_breakout and obv_sell_ok:
            pred = 2

        metadata = {
            "setup": "volatility_breakout_bb_atr_adx_obv",
            "close": close_now,
            "bb_upper": upper_now,
            "bb_lower": lower_now,
            "bb_bandwidth": bw_now,
            "bb_bandwidth_percentile": bw_percentile,
            "compressed": compressed,
            "atr14": atr_now,
            "atr_prev": atr_prev,
            "atr_rising": atr_rising,
            "adx14": adx_now,
            "adx_prev": adx_prev,
            "adx_rising": adx_rising,
            "obv": obv_now,
            "obv_slope": obv_slope,
            "body_to_range": body / candle_range,
            "signal_time": str(row.get("time", "")),
        }
        if pred == 0:
            metadata.update({
                "reason": "sem_rompimento_volatilidade_confirmado",
                "buy_breakout": buy_breakout,
                "sell_breakout": sell_breakout,
                "obv_buy_ok": obv_buy_ok,
                "obv_sell_ok": obv_sell_ok,
                "body_ok": body_ok,
            })
            return 0, metadata

        min_model_prob = float(cfg.get("min_model_probability", 0.58) or 0.58)
        if bool(cfg.get("require_model_alignment", True)):
            model_prob = context.p_buy if pred == 1 else context.p_sell
            if context.prediction not in (0, pred) or model_prob < min_model_prob:
                metadata.update({
                    "reason": "modelo_nao_confirma",
                    "model_prediction": context.prediction,
                    "model_probability": model_prob,
                    "min_model_probability": min_model_prob,
                })
                return 0, metadata

        metadata["reason"] = "rompimento_volatilidade_confirmado"
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
