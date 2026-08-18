#!/usr/bin/env python3
"""Run a short historical replay using price-profile and zone detector to collect reasons."""
import argparse
from pathlib import Path
from collections import Counter

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fusion.backtest.context import BacktestRunConfig
from fusion.backtest.market_data import HistoricalMarketDataProvider
from fusion.backtest.replay import MultiTimeframeReplayCursor
from fusion.backtest.feature_replay_runner import FeatureReplayRunner
from fusion.historical.acceptance_engine import HistoricalPriceAcceptanceEngine
from fusion.historical.price_profile import PriceProfileEngine, ZoneDetector


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol", nargs="?", default="EURUSD")
    parser.add_argument("--max_frames", type=int, default=200)
    parser.add_argument("--data_root", default="data/csv")
    parser.add_argument("--lookback", type=int, default=120)
    args = parser.parse_args()

    provider = HistoricalMarketDataProvider(Path(args.data_root))
    config = BacktestRunConfig(symbols=[args.symbol], timeframes=["M5", "H1"], max_bars=5000)
    cursor = MultiTimeframeReplayCursor(provider, config, primary_timeframe="M5", lookback=args.lookback)

    profile = PriceProfileEngine()
    zone = ZoneDetector()
    acceptance_engine = HistoricalPriceAcceptanceEngine(provider=provider, profile_engine=profile, zone_detector=zone)
    runner = FeatureReplayRunner(cursor, acceptance_engine=acceptance_engine)

    counts = Counter()
    processed = 0
    for frame in runner.frames(args.symbol):
        res = frame.acceptance_result
        if res is None:
            counts['no_result'] += 1
        else:
            counts[res.status] += 1
            if processed < 10:
                print(f"[{processed+1}] idx={res.candle_index} price={res.current_price} status={res.status} reasons={res.reasons} details={res.details}")
        processed += 1
        if processed >= args.max_frames:
            break

    print("--- Profile Replay summary ---")
    print(f"symbol: {args.symbol}")
    print(f"frames_processed: {processed}")
    for k in ['accepted', 'rejected', 'needs_validation', 'no_result']:
        print(f"{k}: {counts[k]}")


if __name__ == '__main__':
    main()
