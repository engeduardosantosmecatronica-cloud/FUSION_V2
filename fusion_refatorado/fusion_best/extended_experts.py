from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np
import pandas as pd


EPS = 1e-10


def _volume(frame: pd.DataFrame) -> pd.Series:
    if "tick_volume" in frame.columns:
        return frame["tick_volume"].astype(float)
    if "volume" in frame.columns:
        return frame["volume"].astype(float)
    return pd.Series(0.0, index=frame.index)


@dataclass
class FibonacciLevelExpert:
    period: int = 20
    levels: tuple[float, ...] = (0.236, 0.382, 0.5, 0.618, 0.786)

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        high = frame["high"].astype(float)
        low = frame["low"].astype(float)
        close = frame["close"].astype(float)
        recent_high = high.rolling(self.period).max()
        recent_low = low.rolling(self.period).min()
        span = recent_high - recent_low
        out = pd.DataFrame(index=frame.index)
        for level in self.levels:
            name = str(level).replace(".", "")
            fib_price = recent_high - span * level
            out[f"ext_fib_{name}_price"] = fib_price
            out[f"ext_fib_{name}_dist"] = (close - fib_price) / (close.abs() + EPS)
        return out


@dataclass
class IchimokuLiteExpert:
    tenkan_period: int = 9
    kijun_period: int = 26
    span_b_period: int = 52

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        high = frame["high"].astype(float)
        low = frame["low"].astype(float)
        close = frame["close"].astype(float)
        out = pd.DataFrame(index=frame.index)
        out["ext_ichi_tenkan"] = (high.rolling(self.tenkan_period).max() + low.rolling(self.tenkan_period).min()) / 2
        out["ext_ichi_kijun"] = (high.rolling(self.kijun_period).max() + low.rolling(self.kijun_period).min()) / 2
        out["ext_ichi_span_a_now"] = (out["ext_ichi_tenkan"] + out["ext_ichi_kijun"]) / 2
        out["ext_ichi_span_b_now"] = (high.rolling(self.span_b_period).max() + low.rolling(self.span_b_period).min()) / 2
        out["ext_ichi_tk_cross"] = np.sign(out["ext_ichi_tenkan"] - out["ext_ichi_kijun"]).fillna(0)
        cloud_top = pd.concat([out["ext_ichi_span_a_now"], out["ext_ichi_span_b_now"]], axis=1).max(axis=1)
        cloud_bottom = pd.concat([out["ext_ichi_span_a_now"], out["ext_ichi_span_b_now"]], axis=1).min(axis=1)
        out["ext_ichi_above_cloud"] = (close > cloud_top).astype(int)
        out["ext_ichi_below_cloud"] = (close < cloud_bottom).astype(int)
        out["ext_ichi_cloud_width"] = (cloud_top - cloud_bottom) / (close.abs() + EPS)
        return out


@dataclass
class VolumeStructureExpert:
    periods: tuple[int, ...] = (5, 20, 50)

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        volume = _volume(frame)
        close = frame["close"].astype(float)
        out = pd.DataFrame(index=frame.index)
        for period in self.periods:
            ma = volume.rolling(period).mean()
            out[f"ext_volume_ma_{period}"] = ma
            out[f"ext_volume_ratio_{period}"] = volume / (ma + EPS)
        out["ext_obv"] = (np.sign(close.diff()).fillna(0) * volume).cumsum()
        if 5 in self.periods and 20 in self.periods:
            out["ext_volume_osc"] = (volume.rolling(5).mean() - volume.rolling(20).mean()) / (
                volume.rolling(20).mean() + EPS
            )
        return out


@dataclass
class GapStructureExpert:
    atr_period: int = 14

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        high = frame["high"].astype(float)
        low = frame["low"].astype(float)
        close = frame["close"].astype(float)
        prev_high = high.shift(1)
        prev_low = low.shift(1)
        prev_close = close.shift(1)
        true_range = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
        atr = true_range.rolling(self.atr_period).mean()
        out = pd.DataFrame(index=frame.index)
        out["ext_gap_up"] = (low > prev_high).astype(int)
        out["ext_gap_down"] = (high < prev_low).astype(int)
        out["ext_gap_size"] = 0.0
        out.loc[out["ext_gap_up"] == 1, "ext_gap_size"] = low - prev_high
        out.loc[out["ext_gap_down"] == 1, "ext_gap_size"] = high - prev_low
        out["ext_gap_ratio"] = out["ext_gap_size"].abs() / (atr + EPS)
        day_high = high.rolling(24).max()
        day_low = low.rolling(24).min()
        out["ext_gap_position"] = 0.5
        out.loc[out["ext_gap_up"] == 1, "ext_gap_position"] = (low - day_low) / (day_high - day_low + EPS)
        out.loc[out["ext_gap_down"] == 1, "ext_gap_position"] = (high - day_low) / (day_high - day_low + EPS)
        return out


@dataclass
class VolumeNodeExpert:
    period: int = 20

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        volume = _volume(frame)
        ma = volume.rolling(self.period).mean()
        std = volume.rolling(self.period).std()
        out = pd.DataFrame(index=frame.index)
        out["ext_hvn"] = (volume > ma + std).astype(int)
        out["ext_lvn"] = (volume < ma - std).astype(int)
        out["ext_hvn_strength"] = volume / (ma + EPS) * out["ext_hvn"]
        out["ext_lvn_strength"] = ma / (volume + EPS) * out["ext_lvn"]
        return out


@dataclass
class StochasticExpert:
    k_period: int = 14
    d_period: int = 3
    slowing: int = 3

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        high = frame["high"].astype(float)
        low = frame["low"].astype(float)
        close = frame["close"].astype(float)
        lowest = low.rolling(self.k_period).min()
        highest = high.rolling(self.k_period).max()
        out = pd.DataFrame(index=frame.index)
        out["ext_stoch_k_fast"] = 100 * (close - lowest) / (highest - lowest + EPS)
        out["ext_stoch_k"] = out["ext_stoch_k_fast"].rolling(self.slowing).mean()
        out["ext_stoch_d"] = out["ext_stoch_k"].rolling(self.d_period).mean()
        out["ext_stoch_kd_diff"] = out["ext_stoch_k"] - out["ext_stoch_d"]
        out["ext_stoch_overbought"] = (out["ext_stoch_k"] > 80).astype(int)
        out["ext_stoch_oversold"] = (out["ext_stoch_k"] < 20).astype(int)
        out["ext_stoch_cross_up"] = (
            (out["ext_stoch_k"] > out["ext_stoch_d"]) & (out["ext_stoch_k"].shift(1) <= out["ext_stoch_d"].shift(1))
        ).astype(int)
        out["ext_stoch_cross_down"] = (
            (out["ext_stoch_k"] < out["ext_stoch_d"]) & (out["ext_stoch_k"].shift(1) >= out["ext_stoch_d"].shift(1))
        ).astype(int)
        return out


class SeasonalityExpert:
    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        out = pd.DataFrame(index=frame.index)
        if not isinstance(frame.index, pd.DatetimeIndex):
            return out
        hour = frame.index.hour
        dayofweek = frame.index.dayofweek
        day = frame.index.day
        out["ext_hour"] = hour
        out["ext_day_of_week"] = dayofweek
        out["ext_is_asia"] = ((hour >= 0) & (hour < 8)).astype(int)
        out["ext_is_london"] = ((hour >= 8) & (hour < 13)).astype(int)
        out["ext_is_ny"] = ((hour >= 13) & (hour < 22)).astype(int)
        out["ext_is_overlap"] = ((hour >= 13) & (hour < 17)).astype(int)
        out["ext_is_monday"] = (dayofweek == 0).astype(int)
        out["ext_is_friday"] = (dayofweek == 4).astype(int)
        out["ext_is_month_start"] = (day <= 5).astype(int)
        out["ext_is_month_end"] = (day >= 25).astype(int)
        return out


@dataclass
class CorrelationExpert:
    periods: tuple[int, ...] = (20, 50, 100)

    def transform(self, frame: pd.DataFrame, symbols: Mapping[str, pd.DataFrame] | None = None) -> pd.DataFrame:
        close = frame["close"].astype(float)
        out = pd.DataFrame(index=frame.index)
        for lag in (1, 5, 10):
            out[f"ext_autocorr_{lag}"] = close.rolling(50).apply(
                lambda values: pd.Series(values).autocorr(lag) if len(values) > lag else 0.0,
                raw=False,
            )
        if not symbols:
            return out
        for symbol, other in symbols.items():
            if "close" not in other.columns:
                continue
            aligned = pd.concat([close, other["close"].astype(float)], axis=1, join="inner")
            aligned.columns = ["base", "other"]
            for period in self.periods:
                out.loc[aligned.index, f"ext_corr_{symbol}_{period}"] = aligned["base"].rolling(period).corr(aligned["other"])
        return out


@dataclass
class MomentumAccelerationExpert:
    fast_period: int = 10
    slow_period: int = 30

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        close = frame["close"].astype(float)
        out = pd.DataFrame(index=frame.index)
        out["ext_momentum"] = close.pct_change(self.fast_period) * 100
        out["ext_momentum_slow"] = close.pct_change(self.slow_period) * 100
        out["ext_acceleration"] = out["ext_momentum"].diff()
        out["ext_momentum_ma_fast"] = out["ext_momentum"].rolling(self.fast_period).mean()
        out["ext_momentum_ma_slow"] = out["ext_momentum"].rolling(self.slow_period).mean()
        out["ext_momentum_cross"] = 0
        cross_up = (out["ext_momentum_ma_fast"].shift(1) <= out["ext_momentum_ma_slow"].shift(1)) & (
            out["ext_momentum_ma_fast"] > out["ext_momentum_ma_slow"]
        )
        cross_down = (out["ext_momentum_ma_fast"].shift(1) >= out["ext_momentum_ma_slow"].shift(1)) & (
            out["ext_momentum_ma_fast"] < out["ext_momentum_ma_slow"]
        )
        out.loc[cross_up, "ext_momentum_cross"] = 1
        out.loc[cross_down, "ext_momentum_cross"] = -1
        out["ext_momentum_regime"] = np.sign(out["ext_momentum"]).fillna(0)
        out["ext_momentum_strength"] = (
            out["ext_momentum"].abs() / (out["ext_momentum_ma_slow"].abs() + EPS)
        ).clip(0, 2)
        out["ext_momentum_score"] = (out["ext_momentum"] / (out["ext_momentum_ma_slow"].abs() + EPS)).clip(-1, 1)
        out["ext_momentum_signal"] = (out["ext_momentum_score"] * out["ext_momentum_strength"]).clip(-1, 1)
        return out


@dataclass
class SwingPointExpert:
    lookback: int = 5

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        high = frame["high"].astype(float)
        low = frame["low"].astype(float)
        close = frame["close"].astype(float)
        window = self.lookback + 1
        out = pd.DataFrame(index=frame.index)
        out["ext_swing_high"] = (high.shift(1) >= high.shift(1).rolling(window).max()).astype(int)
        out["ext_swing_low"] = (low.shift(1) <= low.shift(1).rolling(window).min()).astype(int)
        out["ext_last_swing_high"] = high.shift(1).where(out["ext_swing_high"] == 1).ffill()
        out["ext_last_swing_low"] = low.shift(1).where(out["ext_swing_low"] == 1).ffill()
        out["ext_dist_to_swing_high"] = (out["ext_last_swing_high"] - close) / (close.abs() + EPS)
        out["ext_dist_to_swing_low"] = (close - out["ext_last_swing_low"]) / (close.abs() + EPS)
        out["ext_swing_range"] = (out["ext_last_swing_high"] - out["ext_last_swing_low"]) / (close.abs() + EPS)
        return out


class MicrostructureLiteExpert:
    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        out = pd.DataFrame(index=frame.index)
        if "spread" in frame.columns:
            spread = frame["spread"].astype(float)
            out["ext_spread"] = spread
            out["ext_spread_ma"] = spread.rolling(20).mean()
            out["ext_spread_ratio"] = spread / (out["ext_spread_ma"] + EPS)
        volume = _volume(frame)
        out["ext_tick_volume"] = volume
        out["ext_tick_volume_ratio"] = volume / (volume.rolling(20).mean() + EPS)
        if "bid" in frame.columns and "ask" in frame.columns:
            bid = frame["bid"].astype(float)
            ask = frame["ask"].astype(float)
            out["ext_bid_ask_spread"] = ask - bid
            out["ext_mid_price"] = (bid + ask) / 2
        return out


@dataclass
class VolumeMicrostructureExpert:
    periods: tuple[int, ...] = (5, 10, 20, 50)

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        volume = _volume(frame)
        close = frame["close"].astype(float)
        high = frame["high"].astype(float)
        low = frame["low"].astype(float)
        open_ = frame["open"].astype(float)
        bar_range = (high - low).replace(0, np.nan)
        price_direction = np.sign(close.diff()).fillna(0)
        out = pd.DataFrame(index=frame.index)

        out["ext_ms_tick_volume"] = volume
        for period in self.periods:
            ma = volume.rolling(period).mean()
            out[f"ext_ms_volume_ma_{period}"] = ma
            out[f"ext_ms_volume_ratio_{period}"] = volume / (ma + EPS)
            out[f"ext_ms_volume_roc_{period}"] = volume.pct_change(period)

        vol_ma = volume.rolling(20).mean()
        vol_std = volume.rolling(20).std()
        out["ext_ms_volume_zscore"] = (volume - vol_ma) / (vol_std + EPS)
        out["ext_ms_volume_flow"] = volume * price_direction
        out["ext_ms_bull_volume"] = volume.where(price_direction > 0, 0.0)
        out["ext_ms_bear_volume"] = volume.where(price_direction < 0, 0.0)
        out["ext_ms_bull_bear_ratio"] = out["ext_ms_bull_volume"].rolling(20).sum() / (
            out["ext_ms_bear_volume"].rolling(20).sum() + EPS
        )
        out["ext_ms_volume_efficiency"] = bar_range / (volume + EPS)
        out["ext_ms_volume_per_pip"] = volume / ((bar_range / 0.0001) + EPS)
        out["ext_ms_volume_spike"] = (volume > vol_ma + 2 * vol_std).astype(int)
        out["ext_ms_volume_dry"] = (volume < vol_ma * 0.5).astype(int)
        out["ext_ms_volume_expanding"] = (volume > volume.shift(1)).fillna(False).astype(int)
        out["ext_ms_volume_contracting"] = (volume < volume.shift(1)).fillna(False).astype(int)
        out["ext_ms_volume_consecutive_expand"] = (
            (out["ext_ms_volume_expanding"] == 1) & (out["ext_ms_volume_expanding"].shift(1) == 1)
        ).astype(int)
        out["ext_ms_volume_consecutive_contract"] = (
            (out["ext_ms_volume_contracting"] == 1) & (out["ext_ms_volume_contracting"].shift(1) == 1)
        ).astype(int)
        out["ext_ms_volume_momentum"] = volume - volume.shift(5)
        out["ext_ms_volume_acceleration"] = out["ext_ms_volume_momentum"] - out["ext_ms_volume_momentum"].shift(5)

        bar_position = ((close - low) / (bar_range + EPS)).clip(0, 1)
        out["ext_ms_volume_at_close"] = volume * bar_position
        out["ext_ms_volume_upper_half"] = volume.where(bar_position > 0.5, 0.0)
        out["ext_ms_volume_lower_half"] = volume.where(bar_position <= 0.5, 0.0)
        typical = (high + low + close) / 3
        out["ext_ms_vwap_20"] = (volume * typical).rolling(20).sum() / (volume.rolling(20).sum() + EPS)
        out["ext_ms_vwap_dist"] = (close - out["ext_ms_vwap_20"]) / (close.abs() + EPS)
        out["ext_ms_obv_simple"] = (volume * price_direction).cumsum()
        out["ext_ms_vpt"] = (volume * close.pct_change().fillna(0)).cumsum()
        atr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1).rolling(14).mean()
        out["ext_ms_volume_per_atr"] = volume / (atr + EPS)

        if isinstance(frame.index, pd.DatetimeIndex):
            hour = frame.index.hour
            sessions = {
                "asia": (hour >= 0) & (hour < 8),
                "london": (hour >= 8) & (hour < 13),
                "ny": (hour >= 13) & (hour < 22),
                "overlap": (hour >= 13) & (hour < 17),
            }
            total_session_volume = volume.rolling(96).sum()
            for name, mask in sessions.items():
                session_volume = volume.where(mask, 0.0)
                out[f"ext_ms_volume_{name}_pct"] = session_volume.rolling(96).sum() / (total_session_volume + EPS)

        # Rolling price-volume concentration by decile, causal within each rolling window.
        rolling_low = low.rolling(50).min()
        rolling_high = high.rolling(50).max()
        price_zone = (((typical - rolling_low) / (rolling_high - rolling_low + EPS)) * 10).clip(0, 9).fillna(0).astype(int)
        zone_cols = []
        for zone in range(10):
            col = f"ext_ms_volume_zone_{zone}"
            zone_cols.append(col)
            out[col] = volume.where(price_zone == zone, 0.0).rolling(50).sum()
        zone_matrix = out[zone_cols]
        out["ext_ms_poc_zone"] = zone_matrix.to_numpy().argmax(axis=1)
        out["ext_ms_poc_volume"] = zone_matrix.max(axis=1)
        out["ext_ms_dist_to_poc"] = (price_zone - out["ext_ms_poc_zone"]).abs() / 10
        return out


@dataclass
class AdvancedVolatilityExpert:
    atr_period: int = 14
    bb_period: int = 20
    kc_period: int = 20

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        high = frame["high"].astype(float)
        low = frame["low"].astype(float)
        close = frame["close"].astype(float)
        true_range = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
        atr = true_range.rolling(self.atr_period, min_periods=max(2, self.atr_period // 2)).mean()
        out = pd.DataFrame(index=frame.index)
        out["ext_adv_atr_pct"] = (atr / (close + EPS) * 100).clip(0, 100)
        out["ext_adv_atr_ratio"] = (atr / (atr.rolling(50, min_periods=20).mean() + EPS)).clip(0, 5)
        out["ext_adv_atr_change"] = atr.pct_change().clip(-0.5, 0.5)
        out["ext_adv_atr_expanding"] = (out["ext_adv_atr_change"] > 0.02).astype(int)
        out["ext_adv_atr_contracting"] = (out["ext_adv_atr_change"] < -0.02).astype(int)
        out["ext_adv_atr_pct_zscore"] = (
            out["ext_adv_atr_pct"] - out["ext_adv_atr_pct"].rolling(100).mean()
        ) / (out["ext_adv_atr_pct"].rolling(100).std() + EPS)
        out["ext_adv_atr_percentile"] = atr.rolling(252).rank(pct=True)

        bb_middle = close.rolling(self.bb_period).mean()
        bb_std = close.rolling(self.bb_period).std()
        bb_upper = bb_middle + 2 * bb_std
        bb_lower = bb_middle - 2 * bb_std
        bb_width = (bb_upper - bb_lower) / (bb_middle + EPS)
        out["ext_adv_bb_width_ratio"] = (bb_width / (bb_width.rolling(50, min_periods=20).mean() + EPS)).clip(0, 5)
        out["ext_adv_bb_tight"] = (out["ext_adv_bb_width_ratio"] < 0.7).astype(int)
        out["ext_adv_bb_wide"] = (out["ext_adv_bb_width_ratio"] > 1.3).astype(int)
        out["ext_adv_bb_position"] = ((close - bb_lower) / (bb_upper - bb_lower + EPS)).clip(0, 1)

        kc_middle = close.ewm(span=self.kc_period, adjust=False).mean()
        kc_upper = kc_middle + 1.5 * atr
        kc_lower = kc_middle - 1.5 * atr
        kc_width = (kc_upper - kc_lower) / (kc_middle + EPS)
        out["ext_adv_kc_position"] = ((close - kc_lower) / (kc_upper - kc_lower + EPS)).clip(0, 1)
        out["ext_adv_bb_kc_width_ratio"] = (bb_width / (kc_width + EPS)).clip(0, 5)
        out["ext_adv_squeeze_on"] = ((bb_upper < kc_upper) & (bb_lower > kc_lower)).astype(int)
        out["ext_adv_squeeze_release"] = (
            (out["ext_adv_squeeze_on"] == 0) & (out["ext_adv_squeeze_on"].shift(1) == 1)
        ).astype(int)
        squeeze_tightness = (1 - ((bb_upper - bb_lower) / (kc_upper - kc_lower + EPS))).clip(0, 1)
        out["ext_adv_squeeze_tightness"] = squeeze_tightness
        out["ext_adv_squeeze_momentum"] = squeeze_tightness.diff()
        out["ext_adv_squeeze_direction"] = 0
        out.loc[out["ext_adv_bb_position"] > 0.7, "ext_adv_squeeze_direction"] = 1
        out.loc[out["ext_adv_bb_position"] < 0.3, "ext_adv_squeeze_direction"] = -1

        vol_percentile = bb_width.rolling(252).rank(pct=True)
        out["ext_adv_vol_regime_low"] = (vol_percentile < 0.25).astype(int)
        out["ext_adv_vol_regime_high"] = (vol_percentile > 0.75).astype(int)
        out["ext_adv_regime_change"] = (
            out["ext_adv_vol_regime_high"].diff().abs().fillna(0) + out["ext_adv_vol_regime_low"].diff().abs().fillna(0)
        ).clip(0, 1)
        out["ext_adv_projected_move"] = atr * np.select(
            [out["ext_adv_vol_regime_high"] == 1, out["ext_adv_vol_regime_low"] == 1],
            [1.5, 0.7],
            default=1.0,
        )
        out["ext_adv_projected_move_pct"] = (out["ext_adv_projected_move"] / (close + EPS) * 100).clip(0, 50)
        out["ext_adv_space_to_bb_upper"] = ((bb_upper - close) / (atr + EPS)).clip(0, 5)
        out["ext_adv_space_to_bb_lower"] = ((close - bb_lower) / (atr + EPS)).clip(0, 5)
        vol = bb_width
        vol_ma = vol.rolling(50).mean()
        vol_std = vol.rolling(50).std()
        out["ext_adv_high_vol_cluster"] = (vol > vol_ma + vol_std).astype(int)
        out["ext_adv_low_vol_cluster"] = (vol < vol_ma - vol_std).astype(int)
        out["ext_adv_cluster_transition"] = 0
        out.loc[(out["ext_adv_high_vol_cluster"] == 1) & (out["ext_adv_high_vol_cluster"].shift(1) == 0), "ext_adv_cluster_transition"] = 1
        out.loc[(out["ext_adv_low_vol_cluster"] == 1) & (out["ext_adv_low_vol_cluster"].shift(1) == 0), "ext_adv_cluster_transition"] = -1
        out["ext_adv_cluster_strength"] = np.where(
            out["ext_adv_high_vol_cluster"] == 1,
            ((vol / (vol_ma + EPS)) - 1).clip(0, 1),
            np.where(out["ext_adv_low_vol_cluster"] == 1, (1 - vol / (vol_ma + EPS)).clip(0, 1), 0),
        )
        return out


@dataclass
class CandlestickPatternExpert:
    body_threshold: float = 0.1
    engulfing_threshold: float = 1.2

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        open_ = frame["open"].astype(float)
        high = frame["high"].astype(float)
        low = frame["low"].astype(float)
        close = frame["close"].astype(float)
        body = close - open_
        body_abs = body.abs()
        candle_range = (high - low).replace(0, np.nan)
        upper_shadow = high - pd.concat([open_, close], axis=1).max(axis=1)
        lower_shadow = pd.concat([open_, close], axis=1).min(axis=1) - low
        out = pd.DataFrame(index=frame.index)
        out["ext_cdl_body"] = body
        out["ext_cdl_upper_shadow"] = upper_shadow
        out["ext_cdl_lower_shadow"] = lower_shadow
        out["ext_cdl_range"] = candle_range
        out["ext_cdl_body_ratio"] = body_abs / (candle_range + EPS)
        out["ext_cdl_upper_shadow_ratio"] = upper_shadow / (body_abs + EPS)
        out["ext_cdl_lower_shadow_ratio"] = lower_shadow / (body_abs + EPS)
        out["ext_cdl_is_bullish"] = (close > open_).astype(int)
        out["ext_cdl_is_bearish"] = (close < open_).astype(int)
        out["ext_cdl_doji"] = (out["ext_cdl_body_ratio"] < self.body_threshold).astype(int)
        out["ext_cdl_dragonfly_doji"] = (
            (out["ext_cdl_doji"] == 1) & (upper_shadow < candle_range * 0.1) & (lower_shadow > candle_range * 0.5)
        ).astype(int)
        out["ext_cdl_gravestone_doji"] = (
            (out["ext_cdl_doji"] == 1) & (lower_shadow < candle_range * 0.1) & (upper_shadow > candle_range * 0.5)
        ).astype(int)
        out["ext_cdl_hammer"] = (
            (out["ext_cdl_is_bearish"] == 1) & (lower_shadow > body_abs * 2) & (upper_shadow < body_abs * 0.3)
        ).astype(int)
        out["ext_cdl_shooting_star"] = (
            (out["ext_cdl_is_bullish"] == 1) & (upper_shadow > body_abs * 2) & (lower_shadow < body_abs * 0.3)
        ).astype(int)
        out["ext_cdl_inverted_hammer"] = (
            (out["ext_cdl_is_bullish"] == 1)
            & (upper_shadow > body_abs * 2)
            & (lower_shadow < body_abs * 0.1)
            & (body_abs < candle_range * 0.3)
        ).astype(int)
        out["ext_cdl_hanging_man"] = (
            (out["ext_cdl_is_bearish"] == 1)
            & (lower_shadow > body_abs * 2)
            & (upper_shadow < body_abs * 0.1)
            & (body_abs < candle_range * 0.3)
        ).astype(int)
        prev_body_abs = body.shift(1).abs()
        prev_bull = out["ext_cdl_is_bullish"].shift(1)
        prev_bear = out["ext_cdl_is_bearish"].shift(1)
        out["ext_cdl_bullish_engulfing"] = (
            (out["ext_cdl_is_bullish"] == 1) & (prev_bear == 1) & (body_abs > prev_body_abs * self.engulfing_threshold)
        ).astype(int)
        out["ext_cdl_bearish_engulfing"] = (
            (out["ext_cdl_is_bearish"] == 1) & (prev_bull == 1) & (body_abs > prev_body_abs * self.engulfing_threshold)
        ).astype(int)
        out["ext_cdl_bullish_harami"] = (
            (out["ext_cdl_is_bullish"] == 1) & (prev_bear == 1) & (body_abs < prev_body_abs * 0.5) & (high < high.shift(1)) & (low > low.shift(1))
        ).astype(int)
        out["ext_cdl_bearish_harami"] = (
            (out["ext_cdl_is_bearish"] == 1) & (prev_bull == 1) & (body_abs < prev_body_abs * 0.5) & (high < high.shift(1)) & (low > low.shift(1))
        ).astype(int)
        prev_open = open_.shift(1)
        prev_close = close.shift(1)
        out["ext_cdl_piercing_line"] = (
            (out["ext_cdl_is_bullish"] == 1) & (prev_bear == 1) & (open_ < low.shift(1)) & (close > (prev_open + prev_close) / 2)
        ).astype(int)
        out["ext_cdl_dark_cloud_cover"] = (
            (out["ext_cdl_is_bearish"] == 1) & (prev_bull == 1) & (open_ > high.shift(1)) & (close < (prev_open + prev_close) / 2)
        ).astype(int)
        out["ext_cdl_morning_star"] = (
            (prev_bear == 1) & (out["ext_cdl_doji"].shift(1) == 1) & (out["ext_cdl_is_bullish"] == 1) & (close > (prev_open + prev_close) / 2)
        ).astype(int)
        out["ext_cdl_evening_star"] = (
            (prev_bull == 1) & (out["ext_cdl_doji"].shift(1) == 1) & (out["ext_cdl_is_bearish"] == 1) & (close < (prev_open + prev_close) / 2)
        ).astype(int)
        prev2_bull = out["ext_cdl_is_bullish"].shift(2)
        prev2_bear = out["ext_cdl_is_bearish"].shift(2)
        out["ext_cdl_three_white_soldiers"] = (
            (out["ext_cdl_is_bullish"] == 1)
            & (prev_bull == 1)
            & (prev2_bull == 1)
            & (open_ > prev_open)
            & (close > prev_close)
            & (prev_open > open_.shift(2))
            & (prev_close > close.shift(2))
        ).astype(int)
        out["ext_cdl_three_black_crows"] = (
            (out["ext_cdl_is_bearish"] == 1)
            & (prev_bear == 1)
            & (prev2_bear == 1)
            & (open_ < prev_open)
            & (close < prev_close)
            & (prev_open < open_.shift(2))
            & (prev_close < close.shift(2))
        ).astype(int)
        out["ext_cdl_inside_bar"] = ((high < high.shift(1)) & (low > low.shift(1))).astype(int)
        out["ext_cdl_outside_bar"] = ((high > high.shift(1)) & (low < low.shift(1))).astype(int)
        out["ext_cdl_marubozu"] = (
            (upper_shadow < body_abs * 0.1) & (lower_shadow < body_abs * 0.1) & (body_abs > candle_range * 0.8)
        ).astype(int)
        out["ext_cdl_spinning_top"] = (
            (body_abs < candle_range * 0.3) & (upper_shadow > body_abs * 0.5) & (lower_shadow > body_abs * 0.5)
        ).astype(int)
        return out


class AnomalyRegimeExpert:
    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        close = frame["close"].astype(float)
        returns = close.pct_change()
        out = pd.DataFrame(index=frame.index)
        out["ext_ml_return_zscore"] = (returns - returns.rolling(50).mean()) / (returns.rolling(50).std() + EPS)
        out["ext_ml_is_anomaly"] = (out["ext_ml_return_zscore"].abs() > 3).astype(int)
        sma_20 = close.rolling(20).mean()
        sma_50 = close.rolling(50).mean()
        out["ext_ml_sma_regime"] = np.where(sma_20 > sma_50, 1, -1)
        out["ext_ml_vol_ratio"] = returns.rolling(20).std() / (returns.rolling(100).std() + EPS)
        return out


class ExhaustionCompositeExpert:
    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        close = frame["close"].astype(float)
        high = frame["high"].astype(float)
        low = frame["low"].astype(float)
        volume = _volume(frame)
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + gain / (loss + EPS)))
        lowest = low.rolling(14).min()
        highest = high.rolling(14).max()
        stoch_k = 100 * (close - lowest) / (highest - lowest + EPS)
        ema_12 = close.ewm(span=12, adjust=False).mean()
        ema_26 = close.ewm(span=26, adjust=False).mean()
        macd = ema_12 - ema_26
        macd_signal = macd.ewm(span=9, adjust=False).mean()
        macd_hist = macd - macd_signal
        bb_mid = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        bb_upper = bb_mid + 2 * bb_std
        bb_lower = bb_mid - 2 * bb_std
        vol_ma = volume.rolling(20).mean()
        vol_std = volume.rolling(20).std()
        out = pd.DataFrame(index=frame.index)
        out["ext_exh_rsi_overbought"] = (rsi > 70).astype(int)
        out["ext_exh_rsi_oversold"] = (rsi < 30).astype(int)
        out["ext_exh_rsi_extreme"] = ((rsi > 80) | (rsi < 20)).astype(int)
        out["ext_exh_stoch_overbought"] = (stoch_k > 80).astype(int)
        out["ext_exh_stoch_oversold"] = (stoch_k < 20).astype(int)
        out["ext_exh_volume_spike"] = (volume > vol_ma + 2 * vol_std).astype(int)
        out["ext_exh_volume_dry"] = (volume < vol_ma - vol_std).astype(int)
        out["ext_exh_volume_3x_increasing"] = ((volume > volume.shift(1)) & (volume.shift(1) > volume.shift(2))).astype(int)
        out["ext_exh_macd_losing_momentum"] = ((macd_hist > 0) & (macd_hist < macd_hist.shift(1))).astype(int)
        out["ext_exh_macd_bearish_cross"] = ((macd < macd_signal) & (macd.shift(1) >= macd_signal.shift(1))).astype(int)
        out["ext_exh_bb_touch_upper"] = (close >= bb_upper * 0.995).astype(int)
        out["ext_exh_bb_touch_lower"] = (close <= bb_lower * 1.005).astype(int)
        out["ext_exh_momentum_loss"] = 0.0
        for period, weight in ((5, 0.5), (10, 0.3), (20, 0.2)):
            momentum = close - close.shift(period)
            out["ext_exh_momentum_loss"] += (momentum.diff() < 0).astype(int) * weight
        out["ext_exh_acceleration"] = close.diff().diff()
        out["ext_exh_score"] = (
            out["ext_exh_rsi_extreme"] * 0.25
            + ((out["ext_exh_stoch_overbought"] == 1) | (out["ext_exh_stoch_oversold"] == 1)).astype(int) * 0.20
            + out["ext_exh_volume_spike"] * 0.20
            + out["ext_exh_macd_losing_momentum"] * 0.15
            + ((out["ext_exh_bb_touch_upper"] == 1) | (out["ext_exh_bb_touch_lower"] == 1)).astype(int) * 0.20
        ).clip(0, 1)
        out["ext_exh_bullish_reversal_setup"] = (
            (out["ext_exh_rsi_oversold"] == 1)
            & (out["ext_exh_stoch_oversold"] == 1)
            & (out["ext_exh_bb_touch_lower"] == 1)
        ).astype(int)
        out["ext_exh_bearish_reversal_setup"] = (
            (out["ext_exh_rsi_overbought"] == 1)
            & (out["ext_exh_stoch_overbought"] == 1)
            & (out["ext_exh_bb_touch_upper"] == 1)
        ).astype(int)
        return out


@dataclass
class RollingQuantRegimeExpert:
    windows: tuple[int, ...] = (20, 50, 100)

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        close = frame["close"].astype(float)
        returns = close.pct_change()
        out = pd.DataFrame(index=frame.index)
        for window in self.windows:
            mean = returns.rolling(window).mean()
            std = returns.rolling(window).std()
            zscore = (returns - mean) / (std + EPS)
            out[f"ext_qnt_ret_mean_{window}"] = mean
            out[f"ext_qnt_ret_std_{window}"] = std
            out[f"ext_qnt_ret_zscore_{window}"] = zscore
            out[f"ext_qnt_ret_skew_{window}"] = returns.rolling(window).skew()
            out[f"ext_qnt_ret_kurt_{window}"] = returns.rolling(window).kurt()
            out[f"ext_qnt_range_{window}"] = (close.rolling(window).max() - close.rolling(window).min()) / (close + EPS)
            out[f"ext_qnt_extreme_{window}"] = (zscore.abs() > 2).astype(int)
        for lag in (1, 2, 5):
            out[f"ext_qnt_autocorr_{lag}"] = returns.rolling(50).apply(
                lambda values: pd.Series(values).autocorr(lag) if len(values) > lag else 0.0,
                raw=False,
            )
        out["ext_qnt_autocorr_sum_1_5"] = out[[f"ext_qnt_autocorr_{lag}" for lag in (1, 2, 5)]].sum(axis=1)
        out["ext_qnt_autocorr_regime"] = np.sign(out["ext_qnt_autocorr_sum_1_5"]).fillna(0)
        out["ext_qnt_mean_reversion_score"] = 0.0
        for window in self.windows:
            out["ext_qnt_mean_reversion_score"] += np.where(
                out[f"ext_qnt_ret_zscore_{window}"] > 1,
                -0.25,
                np.where(out[f"ext_qnt_ret_zscore_{window}"] < -1, 0.25, 0),
            )
        out["ext_qnt_mean_reversion_score"] = out["ext_qnt_mean_reversion_score"].clip(-1, 1)
        out["ext_qnt_momentum_score"] = 0.0
        for period in (5, 10, 20):
            ret = close.pct_change(period)
            out["ext_qnt_momentum_score"] += np.sign(ret).fillna(0) * ret.abs().clip(0, 0.5)
        out["ext_qnt_momentum_score"] = out["ext_qnt_momentum_score"].clip(-1, 1)
        std_20 = out.get("ext_qnt_ret_std_20", pd.Series(0, index=frame.index))
        std_100 = out.get("ext_qnt_ret_std_100", pd.Series(0, index=frame.index))
        out["ext_qnt_volatility_score"] = (std_20 / (std_100 + EPS)).clip(0, 3) / 3
        extreme_cols = [f"ext_qnt_extreme_{window}" for window in self.windows]
        out["ext_qnt_extreme_score"] = out[extreme_cols].mean(axis=1)
        out["ext_qnt_statistical_regime"] = np.where(
            out["ext_qnt_momentum_score"].abs() > out["ext_qnt_mean_reversion_score"].abs(),
            np.sign(out["ext_qnt_momentum_score"]),
            -np.sign(out["ext_qnt_mean_reversion_score"]),
        )
        out["ext_qnt_confidence"] = (
            out["ext_qnt_momentum_score"].abs() * 0.35
            + out["ext_qnt_mean_reversion_score"].abs() * 0.35
            + out["ext_qnt_extreme_score"] * 0.30
        ).clip(0, 1)
        return out


def build_extended_expert_features(
    frame: pd.DataFrame,
    symbols: Mapping[str, pd.DataFrame] | None = None,
) -> pd.DataFrame:
    experts = [
        FibonacciLevelExpert(),
        IchimokuLiteExpert(),
        VolumeStructureExpert(),
        GapStructureExpert(),
        VolumeNodeExpert(),
        StochasticExpert(),
        SeasonalityExpert(),
        CorrelationExpert(),
        MomentumAccelerationExpert(),
        SwingPointExpert(),
        MicrostructureLiteExpert(),
        VolumeMicrostructureExpert(),
        AdvancedVolatilityExpert(),
        CandlestickPatternExpert(),
        AnomalyRegimeExpert(),
        ExhaustionCompositeExpert(),
        RollingQuantRegimeExpert(),
    ]
    parts = []
    for expert in experts:
        if isinstance(expert, CorrelationExpert):
            features = expert.transform(frame, symbols=symbols)
        else:
            features = expert.transform(frame)
        parts.append(features)
    return pd.concat(parts, axis=1).replace([np.inf, -np.inf], np.nan).fillna(0.0)
