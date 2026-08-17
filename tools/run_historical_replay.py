#!/usr/bin/env python3
"""Run a quick historical replay for a single symbol and report acceptance stats."""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fusion.backtest.context import BacktestRunConfig
from fusion.backtest.market_data import HistoricalMarketDataProvider
from fusion.backtest.replay import MultiTimeframeReplayCursor
from fusion.backtest.feature_replay_runner import FeatureReplayRunner
from fusion.historical.acceptance_engine import HistoricalPriceAcceptanceEngine


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol", nargs="?", default="AUDCAD", help="Symbol to replay (default AUDCAD)")
    parser.add_argument("--max_frames", type=int, default=200, help="Max frames to process")
    parser.add_argument("--data_root", default="data/csv", help="Path to historical CSV root")
    args = parser.parse_args()

    data_root = Path(args.data_root)
    provider = HistoricalMarketDataProvider(data_root)

    config = BacktestRunConfig(symbols=[args.symbol], timeframes=["M5", "H1", "H4"], max_bars=5000)
    cursor = MultiTimeframeReplayCursor(provider, config, primary_timeframe="M5", lookback=80)

    acceptance_engine = HistoricalPriceAcceptanceEngine(provider=provider)
    runner = FeatureReplayRunner(cursor, acceptance_engine=acceptance_engine)

    accepted = 0
    rejected = 0
    needs = 0
    processed = 0

    for frame in runner.frames(args.symbol):
        if frame.acceptance_result is None:
            continue
        res = frame.acceptance_result
        processed += 1
        if res.status == "accepted":
            accepted += 1
        elif res.status == "rejected":
            rejected += 1
        else:
            needs += 1
        if processed <= 5:
            print(f"[{processed}] idx={res.candle_index} price={res.current_price:.5f} status={res.status} reasons={res.reasons}")
        if processed >= args.max_frames:
            break

    print("--- Replay summary ---")
    print(f"symbol: {args.symbol}")
    print(f"frames_processed: {processed}")
    print(f"accepted: {accepted}")
    print(f"rejected: {rejected}")
    print(f"needs_validation: {needs}")


if __name__ == "__main__":
    main()
