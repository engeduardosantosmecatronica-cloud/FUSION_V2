from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd


def _safe_div(a: pd.Series, b: pd.Series | float) -> pd.Series:
    return (a / (b + 1e-12)).replace([np.inf, -np.inf], np.nan)


def _volume(df: pd.DataFrame) -> pd.Series:
    if "volume" in df.columns:
        return df["volume"]
    if "tick_volume" in df.columns:
        return df["tick_volume"]
    return pd.Series(1.0, index=df.index)


def _true_range(df: pd.DataFrame) -> pd.Series:
    return pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - df["close"].shift(1)).abs(),
            (df["low"] - df["close"].shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)


def _atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    return _true_range(df).rolling(window).mean()


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window).mean()
    loss = (-delta.clip(upper=0)).rolling(window).mean()
    rs = gain / (loss + 1e-12)
    return 100 - (100 / (1 + rs))


def _macd(close: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    line = _ema(close, 12) - _ema(close, 26)
    signal = _ema(line, 9)
    return line, signal, line - signal


def _rolling_percentile(series: pd.Series, window: int) -> pd.Series:
    def rank_last(values: np.ndarray) -> float:
        finite = values[np.isfinite(values)]
        if finite.size == 0:
            return np.nan
        return float((finite <= finite[-1]).mean())

    return series.rolling(window).apply(rank_last, raw=True)


@dataclass
class TrendMasterExpert:
    name: str = "omnis_trend"

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        close = df["close"]
        high = df["high"]
        low = df["low"]
        result = pd.DataFrame(index=df.index)
        for span in (9, 21, 50, 100, 200):
            result[f"omnis_ema_{span}"] = _ema(close, span)
            result[f"omnis_dist_ema_{span}"] = _safe_div(close - result[f"omnis_ema_{span}"], close)

        result["omnis_ema_stack_bull"] = (
            (result["omnis_ema_9"] > result["omnis_ema_21"])
            & (result["omnis_ema_21"] > result["omnis_ema_50"])
            & (result["omnis_ema_50"] > result["omnis_ema_100"])
        ).astype(int)
        result["omnis_ema_stack_bear"] = (
            (result["omnis_ema_9"] < result["omnis_ema_21"])
            & (result["omnis_ema_21"] < result["omnis_ema_50"])
            & (result["omnis_ema_50"] < result["omnis_ema_100"])
        ).astype(int)
        result["omnis_trend_slope_21"] = result["omnis_ema_21"].diff(5)
        result["omnis_trend_slope_50"] = result["omnis_ema_50"].diff(10)

        up_move = high.diff()
        down_move = -low.diff()
        plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=df.index)
        minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=df.index)
        atr = _atr(df, 14)
        plus_di = 100 * plus_dm.rolling(14).sum() / (atr.rolling(14).sum() + 1e-12)
        minus_di = 100 * minus_dm.rolling(14).sum() / (atr.rolling(14).sum() + 1e-12)
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-12)
        result["omnis_plus_di"] = plus_di
        result["omnis_minus_di"] = minus_di
        result["omnis_adx"] = dx.rolling(14).mean()
        result["omnis_rsi"] = _rsi(close)
        macd, macd_signal, macd_hist = _macd(close)
        result["omnis_macd"] = macd
        result["omnis_macd_signal"] = macd_signal
        result["omnis_macd_hist"] = macd_hist
        result["omnis_trend_signal"] = (
            result["omnis_ema_stack_bull"]
            - result["omnis_ema_stack_bear"]
            + np.sign(result["omnis_macd_hist"]).fillna(0) * 0.4
            + np.sign(result["omnis_plus_di"] - result["omnis_minus_di"]).fillna(0) * 0.4
        ).clip(-1, 1)
        result["omnis_trend_confidence"] = (
            result["omnis_adx"].clip(0, 50) / 50 * 0.6
            + result["omnis_trend_signal"].abs() * 0.4
        ).clip(0, 1)
        return result


@dataclass
class VolatilityGaugeExpert:
    name: str = "omnis_volatility"

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        atr = _atr(df, 14)
        close = df["close"]
        mid = close.rolling(20).mean()
        std = close.rolling(20).std()
        upper_bb = mid + 2 * std
        lower_bb = mid - 2 * std
        ema20 = _ema(close, 20)
        upper_kc = ema20 + 1.5 * atr
        lower_kc = ema20 - 1.5 * atr
        atr_mean = atr.rolling(50).mean()
        atr_std = atr.rolling(50).std()
        zscore = (atr - atr_mean) / (atr_std + 1e-12)
        result = pd.DataFrame(index=df.index)
        result["omnis_atr_14"] = atr
        result["omnis_atr_pct"] = _safe_div(atr, close)
        result["omnis_bb_width"] = _safe_div(upper_bb - lower_bb, mid)
        result["omnis_kc_width"] = _safe_div(upper_kc - lower_kc, ema20)
        result["omnis_squeeze_on"] = ((upper_bb < upper_kc) & (lower_bb > lower_kc)).astype(int)
        result["omnis_vol_zscore"] = zscore
        result["omnis_vol_regime_low"] = (zscore < -1).astype(int)
        result["omnis_vol_regime_high"] = (zscore > 1).astype(int)
        result["omnis_vol_expansion"] = atr.diff().gt(0).astype(int)
        result["omnis_vol_signal"] = (zscore.clip(-2, 2) / 2).fillna(0)
        result["omnis_vol_confidence"] = (zscore.abs().clip(0, 2) / 2).fillna(0)
        return result


@dataclass
class StatsQuantExpert:
    window: int = 20
    name: str = "omnis_stats_quant"

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        close = df["close"]
        ret = close.pct_change()
        mean = close.rolling(self.window).mean()
        std = close.rolling(self.window).std()
        zscore = (close - mean) / (std + 1e-12)
        result = pd.DataFrame(index=df.index)
        result["omnis_stat_mean"] = mean
        result["omnis_stat_std"] = std
        result["omnis_stat_zscore"] = zscore
        result["omnis_stat_percentile"] = _rolling_percentile(close, self.window)
        result["omnis_return_zscore"] = (ret - ret.rolling(self.window).mean()) / (ret.rolling(self.window).std() + 1e-12)
        result["omnis_trend_probability"] = (ret.gt(0).rolling(self.window).mean() - 0.5) * 2
        if isinstance(df.index, pd.DatetimeIndex):
            hourly = close.groupby(df.index.hour).transform("mean")
            hourly_std = close.groupby(df.index.hour).transform("std")
            result["omnis_hourly_mean_bias"] = _safe_div(close - hourly, close)
            result["omnis_hourly_std"] = hourly_std
        result["omnis_stats_signal"] = (
            -np.sign(zscore).fillna(0) * (zscore.abs() > 1).astype(int) * 0.5
            + result["omnis_trend_probability"].fillna(0) * 0.5
        ).clip(-1, 1)
        result["omnis_stats_confidence"] = (zscore.abs().clip(0, 3) / 3).fillna(0)
        return result


@dataclass
class ZoneMapperExpert:
    window: int = 50
    name: str = "omnis_zone_mapper"

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = _volume(df)
        support = low.rolling(self.window).min()
        resistance = high.rolling(self.window).max()
        range_size = resistance - support
        pivot = (high + low + close) / 3
        result = pd.DataFrame(index=df.index)
        result["omnis_pivot"] = pivot
        result["omnis_support_20"] = low.rolling(20).min()
        result["omnis_resistance_20"] = high.rolling(20).max()
        result["omnis_support_50"] = support
        result["omnis_resistance_50"] = resistance
        result["omnis_support_100"] = low.rolling(100).min()
        result["omnis_resistance_100"] = high.rolling(100).max()
        result["omnis_dist_support"] = _safe_div(close - support, close)
        result["omnis_dist_resistance"] = _safe_div(resistance - close, close)
        result["omnis_price_position"] = ((close - support) / (range_size + 1e-12)).clip(0, 1)
        result["omnis_at_support"] = (result["omnis_price_position"] < 0.15).astype(int)
        result["omnis_at_resistance"] = (result["omnis_price_position"] > 0.85).astype(int)
        result["omnis_volume_weighted_price"] = (close * volume).rolling(self.window).sum() / (volume.rolling(self.window).sum() + 1e-12)
        result["omnis_dist_vwap_zone"] = _safe_div(close - result["omnis_volume_weighted_price"], close)
        result["omnis_zone_signal"] = (
            result["omnis_at_support"] - result["omnis_at_resistance"]
        ).astype(float)
        result["omnis_zone_confidence"] = (
            (0.5 - (result["omnis_price_position"] - 0.5).abs()).rsub(0.5) * 2
        ).clip(0, 1)
        return result


@dataclass
class PullbackHunterExpert:
    name: str = "omnis_pullback"

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        close = df["close"]
        high = df["high"]
        low = df["low"]
        ema_fast = _ema(close, 9)
        ema_slow = _ema(close, 21)
        atr = _atr(df, 14)
        trend = np.sign(ema_fast - ema_slow)
        rolling_high = high.rolling(50).max()
        rolling_low = low.rolling(50).min()
        swing = rolling_high - rolling_low
        retracement = (rolling_high - close) / (swing + 1e-12)
        result = pd.DataFrame(index=df.index)
        result["omnis_pb_ema_fast"] = ema_fast
        result["omnis_pb_ema_slow"] = ema_slow
        result["omnis_pb_trend"] = trend
        result["omnis_keltner_upper"] = ema_slow + 1.5 * atr
        result["omnis_keltner_lower"] = ema_slow - 1.5 * atr
        result["omnis_pullback_depth"] = retracement
        result["omnis_fib_382"] = rolling_high - swing * 0.382
        result["omnis_fib_500"] = rolling_high - swing * 0.500
        result["omnis_fib_618"] = rolling_high - swing * 0.618
        result["omnis_pullback_buy"] = ((trend > 0) & (close <= ema_fast) & (close >= result["omnis_keltner_lower"])).astype(int)
        result["omnis_pullback_sell"] = ((trend < 0) & (close >= ema_fast) & (close <= result["omnis_keltner_upper"])).astype(int)
        result["omnis_pullback_strength"] = (
            (retracement.between(0.382, 0.618)).astype(int) * 0.6
            + (close.sub(ema_slow).abs() <= atr).astype(int) * 0.4
        )
        result["omnis_pullback_signal"] = (result["omnis_pullback_buy"] - result["omnis_pullback_sell"]) * result["omnis_pullback_strength"]
        result["omnis_pullback_confidence"] = result["omnis_pullback_strength"].clip(0, 1)
        return result


@dataclass
class ExhaustionDetectorExpert:
    name: str = "omnis_exhaustion"

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        close = df["close"]
        high = df["high"]
        low = df["low"]
        rsi = _rsi(close)
        lowest = low.rolling(14).min()
        highest = high.rolling(14).max()
        stoch_k = 100 * (close - lowest) / (highest - lowest + 1e-12)
        stoch_d = stoch_k.rolling(3).mean()
        macd, macd_signal, macd_hist = _macd(close)
        price_higher_high = high > high.shift(5).rolling(10).max()
        price_lower_low = low < low.shift(5).rolling(10).min()
        result = pd.DataFrame(index=df.index)
        result["omnis_exh_rsi"] = rsi
        result["omnis_exh_stoch_k"] = stoch_k
        result["omnis_exh_stoch_d"] = stoch_d
        result["omnis_exh_macd"] = macd
        result["omnis_exh_macd_signal"] = macd_signal
        result["omnis_exh_macd_hist"] = macd_hist
        result["omnis_overbought"] = ((rsi > 70) | (stoch_k > 80)).astype(int)
        result["omnis_oversold"] = ((rsi < 30) | (stoch_k < 20)).astype(int)
        result["omnis_bearish_divergence"] = (price_higher_high & (rsi < rsi.shift(5))).astype(int)
        result["omnis_bullish_divergence"] = (price_lower_low & (rsi > rsi.shift(5))).astype(int)
        result["omnis_gap_up"] = (low > high.shift(1)).astype(int)
        result["omnis_gap_down"] = (high < low.shift(1)).astype(int)
        result["omnis_extreme_candle"] = ((_true_range(df) > _true_range(df).rolling(20).mean() * 2)).astype(int)
        result["omnis_exhaustion_score"] = (
            result["omnis_oversold"] + result["omnis_bullish_divergence"]
            - result["omnis_overbought"] - result["omnis_bearish_divergence"]
        ).clip(-2, 2)
        result["omnis_exhaustion_signal"] = (result["omnis_exhaustion_score"] / 2).clip(-1, 1)
        result["omnis_exhaustion_confidence"] = (result["omnis_exhaustion_score"].abs() / 2).clip(0, 1)
        return result


@dataclass
class FlowAggressorExpert:
    name: str = "omnis_flow"

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        volume = _volume(df)
        close = df["close"]
        open_ = df["open"]
        high = df["high"]
        low = df["low"]
        body = close - open_
        candle_range = (high - low).replace(0, np.nan)
        raw_delta = np.sign(body).fillna(0) * volume
        vwap = (close * volume).rolling(20).sum() / (volume.rolling(20).sum() + 1e-12)
        buy_pressure = volume.where(close > open_, 0).rolling(20).sum()
        sell_pressure = volume.where(close < open_, 0).rolling(20).sum()
        result = pd.DataFrame(index=df.index)
        result["omnis_candle_delta"] = raw_delta
        result["omnis_cumulative_delta"] = raw_delta.cumsum()
        result["omnis_delta_zscore"] = (raw_delta - raw_delta.rolling(20).mean()) / (raw_delta.rolling(20).std() + 1e-12)
        result["omnis_volume_ratio"] = volume / (volume.rolling(20).mean() + 1e-12)
        result["omnis_volume_imbalance"] = (buy_pressure - sell_pressure) / (buy_pressure + sell_pressure + 1e-12)
        result["omnis_vwap"] = vwap
        result["omnis_dist_vwap"] = _safe_div(close - vwap, close)
        result["omnis_aggression_ratio"] = body.abs() / (candle_range + 1e-12)
        result["omnis_buy_aggression"] = ((body > 0) * result["omnis_aggression_ratio"] * result["omnis_volume_ratio"]).astype(float)
        result["omnis_sell_aggression"] = ((body < 0) * result["omnis_aggression_ratio"] * result["omnis_volume_ratio"]).astype(float)
        result["omnis_flow_strength"] = (
            result["omnis_buy_aggression"] - result["omnis_sell_aggression"]
            + result["omnis_volume_imbalance"]
            + result["omnis_delta_zscore"].clip(-2, 2) / 2
        ) / 3
        result["omnis_flow_signal"] = result["omnis_flow_strength"].clip(-1, 1)
        result["omnis_flow_confidence"] = result["omnis_flow_strength"].abs().clip(0, 1)
        return result


@dataclass
class PatternTriggerExpert:
    doji_threshold: float = 0.1
    name: str = "omnis_pattern"

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        open_ = df["open"]
        high = df["high"]
        low = df["low"]
        close = df["close"]
        body = (close - open_).abs()
        candle_range = (high - low).replace(0, np.nan)
        upper_shadow = high - pd.concat([open_, close], axis=1).max(axis=1)
        lower_shadow = pd.concat([open_, close], axis=1).min(axis=1) - low
        body_ratio = body / (candle_range + 1e-12)
        upper_ratio = upper_shadow / (candle_range + 1e-12)
        lower_ratio = lower_shadow / (candle_range + 1e-12)
        bullish = close > open_
        bearish = close < open_
        result = pd.DataFrame(index=df.index)
        result["omnis_body_ratio"] = body_ratio
        result["omnis_upper_shadow_ratio"] = upper_ratio
        result["omnis_lower_shadow_ratio"] = lower_ratio
        result["omnis_hammer"] = (bullish & (lower_ratio > 0.6) & (upper_ratio < 0.1) & (body_ratio < 0.3)).astype(int)
        result["omnis_shooting_star"] = (bearish & (upper_ratio > 0.6) & (lower_ratio < 0.1) & (body_ratio < 0.3)).astype(int)
        result["omnis_bullish_engulfing"] = (
            bullish & bearish.shift(1, fill_value=False) & (open_ < close.shift(1)) & (close > open_.shift(1))
        ).astype(int)
        result["omnis_bearish_engulfing"] = (
            bearish & bullish.shift(1, fill_value=False) & (open_ > close.shift(1)) & (close < open_.shift(1))
        ).astype(int)
        result["omnis_morning_star"] = (
            bullish & bearish.shift(2, fill_value=False) & (body_ratio.shift(1) < self.doji_threshold)
            & (close > (high.shift(2) + low.shift(2)) / 2)
        ).astype(int)
        result["omnis_evening_star"] = (
            bearish & bullish.shift(2, fill_value=False) & (body_ratio.shift(1) < self.doji_threshold)
            & (close < (high.shift(2) + low.shift(2)) / 2)
        ).astype(int)
        result["omnis_piercing_line"] = (
            bullish & bearish.shift(1, fill_value=False) & (open_ < low.shift(1))
            & (close > (open_.shift(1) + close.shift(1)) / 2)
        ).astype(int)
        result["omnis_dark_cloud"] = (
            bearish & bullish.shift(1, fill_value=False) & (open_ > high.shift(1))
            & (close < (open_.shift(1) + close.shift(1)) / 2)
        ).astype(int)
        result["omnis_inside_bar"] = ((high < high.shift(1)) & (low > low.shift(1))).astype(int)
        result["omnis_outside_bar"] = ((high > high.shift(1)) & (low < low.shift(1))).astype(int)
        result["omnis_doji"] = (body_ratio < self.doji_threshold).astype(int)
        result["omnis_spinning_top"] = ((body_ratio < 0.3) & (upper_ratio > 0.2) & (lower_ratio > 0.2)).astype(int)
        bullish_cols = [
            "omnis_hammer",
            "omnis_bullish_engulfing",
            "omnis_morning_star",
            "omnis_piercing_line",
        ]
        bearish_cols = [
            "omnis_shooting_star",
            "omnis_bearish_engulfing",
            "omnis_evening_star",
            "omnis_dark_cloud",
        ]
        bull_score = result[bullish_cols].sum(axis=1)
        bear_score = result[bearish_cols].sum(axis=1)
        total = bull_score + bear_score
        result["omnis_pattern_score"] = np.where(total > 0, (bull_score - bear_score) / total, 0.0)
        result["omnis_pattern_strength"] = (
            bull_score + bear_score + result["omnis_inside_bar"] * 0.4 + result["omnis_outside_bar"] * 0.6
        ).clip(0, 2)
        result["omnis_pattern_confidence"] = (result["omnis_pattern_strength"] / 2).clip(0, 1)
        return result


@dataclass
class RiskGuardianExpert:
    max_risk_per_trade: float = 0.02
    max_daily_risk: float = 0.05
    min_rr_ratio: float = 1.5
    max_open_positions: int = 3
    max_positions_same_dir: int = 2
    name: str = "omnis_risk_guardian"

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        returns = df["close"].pct_change()
        volatility = returns.rolling(20).std() * np.sqrt(252)
        cumulative = (1 + returns.fillna(0)).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / (running_max + 1e-12)
        downside = returns.where(returns < 0, 0)
        mae = (df["low"] - df["close"].shift(1)) / (df["close"].shift(1) + 1e-12)
        mfe = (df["high"] - df["close"].shift(1)) / (df["close"].shift(1) + 1e-12)
        result = pd.DataFrame(index=df.index)
        result["omnis_returns"] = returns
        result["omnis_volatility"] = volatility
        result["omnis_var_95"] = returns.rolling(20).quantile(0.05)
        result["omnis_var_99"] = returns.rolling(20).quantile(0.01)
        result["omnis_cvar_95"] = returns.rolling(20).apply(
            lambda x: x[x <= np.nanquantile(x, 0.05)].mean() if np.isfinite(x).any() else np.nan,
            raw=False,
        )
        result["omnis_drawdown"] = drawdown
        result["omnis_max_drawdown"] = drawdown.rolling(20).min()
        result["omnis_sharpe_20"] = returns.rolling(20).mean() / (returns.rolling(20).std() + 1e-12) * np.sqrt(252)
        result["omnis_sharpe_50"] = returns.rolling(50).mean() / (returns.rolling(50).std() + 1e-12) * np.sqrt(252)
        result["omnis_sortino_20"] = returns.rolling(20).mean() / (downside.rolling(20).std() + 1e-12) * np.sqrt(252)
        result["omnis_calmar_20"] = returns.rolling(20).mean() / (result["omnis_max_drawdown"].abs() + 1e-12)
        result["omnis_mae"] = mae
        result["omnis_mfe"] = mfe
        result["omnis_mae_ma"] = mae.rolling(20).mean()
        result["omnis_mfe_ma"] = mfe.rolling(20).mean()
        result["omnis_efficiency"] = (result["omnis_mfe_ma"].abs() / (result["omnis_mae_ma"].abs() + 1e-12)).clip(0, 10)
        result["omnis_win_rate"] = returns.gt(0).rolling(50).mean()
        result["omnis_expectancy"] = returns.rolling(50).mean()
        result["omnis_kelly"] = (
            result["omnis_win_rate"] - ((1 - result["omnis_win_rate"]) / (result["omnis_efficiency"] + 1e-3))
        ).clip(0, 0.25)
        vol_pct = volatility.rank(pct=True)
        sharpe_score = result["omnis_sharpe_20"].clip(0, 2) / 2
        position = 0.01 * (1 - vol_pct * 0.5) * (0.5 + sharpe_score * 0.5) * (1 + result["omnis_kelly"])
        result["omnis_suggested_position"] = position.clip(0.005, 0.05)
        result["omnis_risk_signal"] = (
            -(drawdown < -0.05).astype(int) * 0.2
            -(drawdown < -0.10).astype(int) * 0.2
            -(result["omnis_sharpe_20"] < 0.5).astype(int) * 0.2
            -(volatility > 0.5).astype(int) * 0.2
        ).clip(-1, 0)
        result["omnis_risk_confidence"] = (
            0.7
            + (result["omnis_sharpe_20"] > 0.5).astype(int) * 0.1
            + (result["omnis_sharpe_20"] > 1.0).astype(int) * 0.1
            - (drawdown < -0.05).astype(int) * 0.1
            - (drawdown < -0.10).astype(int) * 0.2
            - (volatility > 0.4).astype(int) * 0.1
        ).clip(0, 1)
        return result

    def evaluate_trade(
        self,
        symbol: str,
        direction: int,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        current_positions: list[dict[str, Any]],
        account_balance: float,
        daily_pnl: float,
    ) -> dict[str, Any]:
        risk_points = abs(entry_price - stop_loss)
        reward_points = abs(take_profit - entry_price)
        risk_amount = risk_points / entry_price if entry_price else 0.0
        reward_amount = reward_points / entry_price if entry_price else 0.0
        rr_ratio = reward_amount / risk_amount if risk_amount > 0 else 0.0
        position_size = min(self.max_risk_per_trade / risk_amount, 1.0) if risk_amount > 0 else 0.0
        if rr_ratio < self.min_rr_ratio:
            return {"approved": False, "reason": "rr_below_minimum", "position_size": 0.0, "risk_amount": risk_amount, "rr_ratio": rr_ratio}
        if daily_pnl + risk_amount * position_size * account_balance < -self.max_daily_risk * account_balance:
            return {"approved": False, "reason": "daily_risk_exceeded", "position_size": 0.0, "risk_amount": risk_amount, "rr_ratio": rr_ratio}
        if len(current_positions) >= self.max_open_positions:
            return {"approved": False, "reason": "max_open_positions", "position_size": 0.0, "risk_amount": risk_amount, "rr_ratio": rr_ratio}
        same_dir = sum(1 for pos in current_positions if pos.get("direction") == direction)
        if same_dir >= self.max_positions_same_dir:
            return {"approved": False, "reason": "max_same_direction", "position_size": 0.0, "risk_amount": risk_amount, "rr_ratio": rr_ratio}
        if any(pos.get("symbol") == symbol for pos in current_positions):
            return {"approved": False, "reason": "same_symbol_position", "position_size": 0.0, "risk_amount": risk_amount, "rr_ratio": rr_ratio}
        return {
            "approved": True,
            "reason": "approved",
            "position_size": position_size,
            "risk_amount": risk_amount,
            "rr_ratio": rr_ratio,
            "risk_points": risk_points,
            "reward_points": reward_points,
            "timestamp": datetime.utcnow().isoformat(),
        }


DEFAULT_OMNIS_EXPERTS = (
    TrendMasterExpert(),
    VolatilityGaugeExpert(),
    StatsQuantExpert(),
    ZoneMapperExpert(),
    PullbackHunterExpert(),
    ExhaustionDetectorExpert(),
    FlowAggressorExpert(),
    PatternTriggerExpert(),
    RiskGuardianExpert(),
)


def build_omnis_expert_features(
    df: pd.DataFrame,
    experts: tuple[Any, ...] = DEFAULT_OMNIS_EXPERTS,
) -> pd.DataFrame:
    parts = [expert.transform(df) for expert in experts]
    result = pd.concat(parts, axis=1)
    return result.loc[:, ~result.columns.duplicated()].replace([np.inf, -np.inf], np.nan).dropna()
