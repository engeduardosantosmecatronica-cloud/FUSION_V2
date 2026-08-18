#!/usr/bin/env python3
"""Calibration sweep for HistoricalPriceAcceptanceEngine over lookback and use_profile options."""
import argparse
from pathlib import Path
from collections import defaultdict
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fusion.backtest.context import BacktestRunConfig
from fusion.backtest.market_data import HistoricalMarketDataProvider
from fusion.backtest.replay import MultiTimeframeReplayCursor
from fusion.backtest.feature_replay_runner import FeatureReplayRunner
from fusion.historical.acceptance_engine import HistoricalPriceAcceptanceEngine
from fusion.historical.price_profile import PriceProfileEngine, ZoneDetector


def sweep(symbol: str, lookbacks: list[int], use_profile_opts: list[bool], max_frames: int, data_root: Path):
    provider = HistoricalMarketDataProvider(data_root)
    results = defaultdict(dict)
    for lb in lookbacks:
        for up in use_profile_opts:
            profile = PriceProfileEngine() if up else None
            zone = ZoneDetector() if up else None
            engine = HistoricalPriceAcceptanceEngine(provider=provider, profile_engine=profile, zone_detector=zone)
            config = BacktestRunConfig(symbols=[symbol], timeframes=["M5","H1"], max_bars=max_frames)
            cursor = MultiTimeframeReplayCursor(provider, config, primary_timeframe="M5", lookback=lb)
            runner = FeatureReplayRunner(cursor, acceptance_engine=engine)
            counts = {'accepted':0,'rejected':0,'needs_validation':0}
            processed = 0
            for frame in runner.frames(symbol):
                res = frame.acceptance_result
                if res is None:
                    continue
                counts[res.status] += 1
                processed += 1
                if processed >= max_frames:
                    break
            results[lb][up] = (processed, counts)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("symbols", nargs="+", help="Symbols to sweep")
    parser.add_argument("--lookbacks", nargs="+", type=int, default=[40,80,120,200])
    parser.add_argument("--max_frames", type=int, default=500)
    parser.add_argument("--data_root", default="data/csv")
    args = parser.parse_args()
    data_root = Path(args.data_root)
    for sym in args.symbols:
        print(f"=== Calibration for {sym} ===")
        res = sweep(sym, args.lookbacks, [False, True], args.max_frames, data_root)
        for lb, d in res.items():
            for up, v in d.items():
                processed, counts = v
                print(f"lookback={lb} use_profile={up} processed={processed} -> {counts}")


if __name__ == '__main__':
    main()
