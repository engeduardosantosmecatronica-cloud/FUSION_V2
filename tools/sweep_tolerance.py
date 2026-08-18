#!/usr/bin/env python3
"""Sweep min_tolerance for HistoricalPriceAcceptanceEngine by subclassing and overriding tolerance logic."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fusion.historical.acceptance_engine import HistoricalPriceAcceptanceEngine
from fusion.backtest.context import BacktestRunConfig
from fusion.backtest.market_data import HistoricalMarketDataProvider
from fusion.backtest.replay import MultiTimeframeReplayCursor
from fusion.backtest.feature_replay_runner import FeatureReplayRunner


class CustomAcceptanceEngine(HistoricalPriceAcceptanceEngine):
    def __init__(self, *args, min_tolerance=0.02, **kwargs):
        super().__init__(*args, **kwargs)
        self.min_tolerance = float(min_tolerance)

    def evaluate(self, symbol: str, timeframe: str, candle_index: int, lookback: int = 80, use_profile: bool = False):
        # Copy of parent logic but using self.min_tolerance instead of hard-coded 0.02
        if self.provider is None:
            return super().evaluate(symbol, timeframe, candle_index, lookback, use_profile)

        bars = self.provider.get_bars(symbol, timeframe, candle_index, lookback)
        if not bars:
            return super().evaluate(symbol, timeframe, candle_index, lookback, use_profile)

        # reuse parent's implementation but recompute tolerance
        from fusion.historical.acceptance_engine import HistoricalAcceptanceResult
        import pandas as pd

        prices = [self._bar_value(bar, 'close') for bar in bars]
        series = pd.Series(prices)
        current_price = float(series.iloc[-1])
        lower = float(series.quantile(0.10))
        upper = float(series.quantile(0.90))
        domain_low = min(float(series.min()), lower)
        domain_high = max(float(series.max()), upper)
        tolerance = max(self.min_tolerance, 0.05 * abs(domain_high - domain_low) / max(abs(domain_high), 1e-9))

        reasons = []
        if current_price < domain_low * (1.0 - tolerance):
            reasons.append('price_below_domain')
        if current_price > domain_high * (1.0 + tolerance):
            reasons.append('price_above_domain')

        profile_context = None
        zone_context = None
        if use_profile:
            profile_context, zone_context = self._profile_context(symbol, timeframe, bars)

        if profile_context is not None and zone_context is not None and zone_context.get('zones'):
            zone = self.zone_detector.current_zone(zone_context, current_price) if self.zone_detector is not None else None
            if zone is not None:
                zone_low = float(zone.get('price_low', domain_low))
                zone_high = float(zone.get('price_high', domain_high))
                if current_price < zone_low * (1.0 - tolerance) or current_price > zone_high * (1.0 + tolerance):
                    reasons.append('price_outside_profile_zone')

        if reasons:
            status = 'rejected'
        elif abs(current_price - float(series.mean())) <= max(1e-9, 0.75 * float(series.std(ddof=0) or 0.0)):
            status = 'accepted'
        else:
            status = 'needs_validation'

        details = {
            'lookback': lookback,
            'mean': float(series.mean()),
            'std': float(series.std(ddof=0) or 0.0),
            'lower_q10': lower,
            'upper_q90': upper,
            'tolerance': tolerance,
            'domain_low': domain_low,
            'domain_high': domain_high,
        }

        return HistoricalAcceptanceResult(
            symbol=symbol,
            timeframe=timeframe,
            candle_index=candle_index,
            current_price=current_price,
            price_domain_low=lower,
            price_domain_high=upper,
            status=status,
            reasons=reasons,
            details=details,
        )


def run_sweep(symbols, tolerances, max_frames, lookback, data_root):
    provider = HistoricalMarketDataProvider(Path(data_root))
    results = {}
    for tol in tolerances:
        results[tol] = {}
        engine = CustomAcceptanceEngine(provider=provider, min_tolerance=tol)
        for sym in symbols:
            config = BacktestRunConfig(symbols=[sym], timeframes=['M5','H1'], max_bars=max_frames)
            cursor = MultiTimeframeReplayCursor(provider, config, primary_timeframe='M5', lookback=lookback)
            runner = FeatureReplayRunner(cursor, acceptance_engine=engine)
            counts = {'accepted':0,'rejected':0,'needs_validation':0}
            processed = 0
            for frame in runner.frames(sym):
                res = frame.acceptance_result
                if res is None:
                    continue
                counts[res.status] += 1
                processed += 1
                if processed >= max_frames:
                    break
            results[tol][sym] = (processed, counts)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('symbols', nargs='+')
    parser.add_argument('--tolerances', nargs='+', type=float, default=[0.005,0.01,0.02,0.03])
    parser.add_argument('--max_frames', type=int, default=1000)
    parser.add_argument('--lookback', type=int, default=80)
    parser.add_argument('--data_root', default='data/csv')
    args = parser.parse_args()
    res = run_sweep(args.symbols, args.tolerances, args.max_frames, args.lookback, args.data_root)
    for tol, d in res.items():
        print(f"\n=== tolerance={tol} ===")
        for sym, (processed, counts) in d.items():
            print(f"{sym}: processed={processed} -> {counts}")


if __name__ == '__main__':
    main()
