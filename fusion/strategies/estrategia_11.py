from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from fusion.strategies.base import BaseStrategy, StrategyContext, StrategyDecision


class Estrategia11(BaseStrategy):
    name = "strategy11"
    tag = "S11"

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


    @staticmethod
    def _ad_line(frame: pd.DataFrame) -> pd.Series:
        high = frame["high"].astype(float)
        low = frame["low"].astype(float)
        close = frame["close"].astype(float)
        volume_col = "tick_volume" if "tick_volume" in frame.columns else "real_volume" if "real_volume" in frame.columns else "volume"
        volume = frame[volume_col].astype(float) if volume_col in frame.columns else pd.Series(0.0, index=frame.index)
        clv = ((close - low) - (high - close)) / ((high - low) + 1e-12)
        return (clv * volume).cumsum()

    @staticmethod
    def _mfi(frame: pd.DataFrame, period: int = 14) -> pd.Series:
        typical = (frame["high"].astype(float) + frame["low"].astype(float) + frame["close"].astype(float)) / 3
        volume_col = "tick_volume" if "tick_volume" in frame.columns else "real_volume" if "real_volume" in frame.columns else "volume"
        volume = frame[volume_col].astype(float) if volume_col in frame.columns else pd.Series(0.0, index=frame.index)
        flow = typical * volume
        pos = flow.where(typical.diff() > 0, 0.0).rolling(period).sum()
        neg = flow.where(typical.diff() < 0, 0.0).abs().rolling(period).sum()
        return 100 - (100 / (1 + pos / (neg + 1e-12)))

    def _setup(self, context: StrategyContext) -> tuple[int, dict[str, Any]]:
        ok, reason = self._allowed(context, ["BTCUSD", "ETHUSD", "GOLD", "XAUUSD", "EURUSD", "GBPUSD"], ["M15", "M30", "H1", "H4"])
        if not ok:
            return 0, reason
        cfg = self._cfg()
        frame = self._market_frame(context.broker_symbol, context.timeframe)
        if frame.empty:
            return 0, {"reason": "sem_rates"}
        close = frame["close"].astype(float)
        idx = len(frame) - 2 if bool(cfg.get("use_closed_candle", True)) and len(frame) >= 2 else len(frame) - 1
        if idx < 80:
            return 0, {"reason": "dados_insuficientes"}
        lookback = int(cfg.get("slope_bars", 8) or 8)
        obv = self._obv(frame)
        ad = self._ad_line(frame)
        mfi = self._mfi(frame, int(cfg.get("mfi_period", 14) or 14))
        _, _, hist = self._macd(close)
        price_slope = float(close.iloc[idx] - close.iloc[idx - lookback])
        obv_slope = float(obv.iloc[idx] - obv.iloc[idx - lookback])
        ad_slope = float(ad.iloc[idx] - ad.iloc[idx - lookback])
        hist_now = float(hist.iloc[idx]) if np.isfinite(hist.iloc[idx]) else 0.0
        hist_prev = float(hist.iloc[idx - 1]) if np.isfinite(hist.iloc[idx - 1]) else hist_now
        mfi_now = float(mfi.iloc[idx]) if np.isfinite(mfi.iloc[idx]) else 50.0
        buy_ok = price_slope > 0 and obv_slope > 0 and ad_slope > 0 and float(cfg.get("mfi_buy_min", 45.0) or 45.0) <= mfi_now <= float(cfg.get("mfi_buy_max", 82.0) or 82.0) and hist_now > hist_prev
        sell_ok = price_slope < 0 and obv_slope < 0 and ad_slope < 0 and float(cfg.get("mfi_sell_min", 18.0) or 18.0) <= mfi_now <= float(cfg.get("mfi_sell_max", 55.0) or 55.0) and hist_now < hist_prev
        pred = 1 if buy_ok else 2 if sell_ok else 0
        metadata = {"setup": "fluxo_volume_obv_ad_mfi_macd", "price_slope": price_slope, "obv_slope": obv_slope, "ad_slope": ad_slope, "mfi": mfi_now, "macd_hist": hist_now, "signal_time": str(frame.iloc[idx].get("time", ""))}
        if pred == 0:
            metadata.update({"reason": "fluxo_nao_confirma", "buy_ok": buy_ok, "sell_ok": sell_ok})
            return 0, metadata
        if not self._model_confirms(pred, context, metadata):
            return 0, metadata
        metadata["reason"] = "fluxo_volume_confirma_preco"
        return pred, metadata
