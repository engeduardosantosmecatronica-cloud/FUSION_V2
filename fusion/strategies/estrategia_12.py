from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from fusion.strategies.base import BaseStrategy, StrategyContext, StrategyDecision


class Estrategia12(BaseStrategy):
    name = "strategy12"
    tag = "S12"

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
        bars = int(self._cfg().get("bars", 320) or 320)
        rates = self.app.mt5.copy_rates_from_pos(broker_symbol, tf_code, 0, bars)
        if rates is None or len(rates) < 140:
            return pd.DataFrame()
        frame = pd.DataFrame(rates).sort_values("time").reset_index(drop=True)
        frame["time"] = pd.to_datetime(frame["time"], unit="s")
        return frame

    @staticmethod
    def _true_range(frame: pd.DataFrame) -> pd.Series:
        high = frame["high"].astype(float)
        low = frame["low"].astype(float)
        close = frame["close"].astype(float)
        return pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)

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
    def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
        delta = close.astype(float).diff()
        gain = delta.where(delta > 0, 0.0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
        rs = gain / (loss + 1e-12)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def _macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[pd.Series, pd.Series, pd.Series]:
        ema_fast = close.astype(float).ewm(span=fast, adjust=False).mean()
        ema_slow = close.astype(float).ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal, adjust=False).mean()
        return macd, macd_signal, macd - macd_signal

    @staticmethod
    def _obv(frame: pd.DataFrame) -> pd.Series:
        close = frame["close"].astype(float)
        volume_col = "tick_volume" if "tick_volume" in frame.columns else "real_volume" if "real_volume" in frame.columns else "volume"
        volume = frame[volume_col].astype(float) if volume_col in frame.columns else pd.Series(0.0, index=frame.index)
        return (np.sign(close.diff()).fillna(0.0) * volume).cumsum()

    def _allowed(self, context: StrategyContext, symbols: list[str], timeframes: list[str]) -> tuple[bool, dict[str, Any]]:
        cfg = self._cfg()
        allowed_symbols = set(self._cfg_list("symbols", symbols))
        symbol = context.symbol.upper()
        broker_symbol = context.broker_symbol.upper()
        if allowed_symbols and symbol not in allowed_symbols and broker_symbol not in allowed_symbols:
            return False, {"reason": "symbol_not_allowed"}
        allowed_timeframes = set(self._cfg_list("timeframes", timeframes))
        if context.timeframe.upper() not in allowed_timeframes:
            return False, {"reason": "timeframe_not_allowed"}
        return True, {}

    def _model_confirms(self, pred: int, context: StrategyContext, metadata: dict[str, Any]) -> bool:
        cfg = self._cfg()
        if not bool(cfg.get("require_model_alignment", True)):
            return True
        min_model_prob = float(cfg.get("min_model_probability", 0.58) or 0.58)
        model_prob = context.p_buy if pred == 1 else context.p_sell
        if context.prediction not in (0, pred) or model_prob < min_model_prob:
            metadata.update({
                "reason": "modelo_nao_confirma",
                "model_prediction": context.prediction,
                "model_probability": model_prob,
                "min_model_probability": min_model_prob,
            })
            return False
        return True

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


    def _setup(self, context: StrategyContext) -> tuple[int, dict[str, Any]]:
        ok, reason = self._allowed(context, ["EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "GOLD", "XAUUSD"], ["M30", "H1", "H4"])
        if not ok:
            return 0, reason
        cfg = self._cfg()
        frame = self._market_frame(context.broker_symbol, context.timeframe)
        if frame.empty:
            return 0, {"reason": "sem_rates"}
        close = frame["close"].astype(float)
        high = frame["high"].astype(float)
        low = frame["low"].astype(float)
        idx = len(frame) - 2 if bool(cfg.get("use_closed_candle", True)) and len(frame) >= 2 else len(frame) - 1
        if idx < 120:
            return 0, {"reason": "dados_insuficientes"}
        tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2
        kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2
        span_a = ((tenkan + kijun) / 2).shift(26)
        span_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)
        future_a = ((tenkan + kijun) / 2)
        future_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2)
        adx = self._adx(frame, int(cfg.get("adx_period", 14) or 14))
        atr = self._true_range(frame).rolling(int(cfg.get("atr_period", 14) or 14)).mean()
        price = float(close.iloc[idx])
        cloud_top = max(float(span_a.iloc[idx]), float(span_b.iloc[idx]))
        cloud_bottom = min(float(span_a.iloc[idx]), float(span_b.iloc[idx]))
        tenkan_now = float(tenkan.iloc[idx])
        kijun_now = float(kijun.iloc[idx])
        adx_now = float(adx.iloc[idx]) if np.isfinite(adx.iloc[idx]) else 0.0
        atr_now = float(atr.iloc[idx]) if np.isfinite(atr.iloc[idx]) else 0.0
        atr_ma = float(atr.iloc[max(0, idx - 30):idx].mean())
        atr_ok = atr_now >= atr_ma * float(cfg.get("min_atr_vs_ma", 0.80) or 0.80)
        buy_ok = price > cloud_top and tenkan_now > kijun_now and float(future_a.iloc[idx]) > float(future_b.iloc[idx]) and adx_now >= float(cfg.get("min_adx", 22.0) or 22.0) and atr_ok
        sell_ok = price < cloud_bottom and tenkan_now < kijun_now and float(future_a.iloc[idx]) < float(future_b.iloc[idx]) and adx_now >= float(cfg.get("min_adx", 22.0) or 22.0) and atr_ok
        pred = 1 if buy_ok else 2 if sell_ok else 0
        metadata = {"setup": "tendencia_visual_ichimoku_adx_atr", "close": price, "cloud_top": cloud_top, "cloud_bottom": cloud_bottom, "tenkan": tenkan_now, "kijun": kijun_now, "adx": adx_now, "atr": atr_now, "atr_ok": atr_ok, "signal_time": str(frame.iloc[idx].get("time", ""))}
        if pred == 0:
            metadata.update({"reason": "ichimoku_sem_tendencia_confirmada", "buy_ok": buy_ok, "sell_ok": sell_ok})
            return 0, metadata
        if not self._model_confirms(pred, context, metadata):
            return 0, metadata
        metadata["reason"] = "tendencia_ichimoku_confirmada"
        return pred, metadata
