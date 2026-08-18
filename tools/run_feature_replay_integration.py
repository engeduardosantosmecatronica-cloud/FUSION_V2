from __future__ import annotations

import argparse
from pathlib import Path
from collections import Counter

from fusion.backtest.context import BacktestRunConfig
from fusion.backtest.market_data import HistoricalMarketDataProvider
from fusion.backtest.replay import MultiTimeframeReplayCursor
from fusion.backtest.feature_replay_runner import FeatureReplayRunner
from fusion.historical.acceptance_engine import HistoricalPriceAcceptanceEngine


def run(symbol: str, max_frames: int, data_root: Path):
    provider = HistoricalMarketDataProvider(data_root)
    config = BacktestRunConfig(symbols=[symbol], timeframes=["M5", "H1", "D1"], max_bars=max_frames)
    cursor = MultiTimeframeReplayCursor(provider, config, primary_timeframe="M5", lookback=300)
    acceptance_engine = HistoricalPriceAcceptanceEngine()
    runner = FeatureReplayRunner(cursor, acceptance_engine=acceptance_engine)

    counts = Counter()
    processed = 0
    for frame in runner.frames(symbol):
        if frame.acceptance_result is None:
            counts["no_result"] += 1
        else:
            status = getattr(frame.acceptance_result, "status", "unknown")
            counts[status] += 1
        processed += 1
        if processed >= max_frames:
            break

    print(f"--- Integration replay summary ---")
    print(f"symbol: {symbol}")
    print(f"frames_processed: {processed}")
    for k in ["accepted", "rejected", "needs_validation", "no_result", "unknown"]:
        if counts[k]:
            print(f"{k}: {counts[k]}")


def main():
    parser = argparse.ArgumentParser(description="Run integration feature replay with acceptance engine")
    parser.add_argument("symbols", nargs="+", help="Symbols to run (e.g. EURUSD XAUUSD)")
    parser.add_argument("--max_frames", type=int, default=2000)
    parser.add_argument("--data_root", type=str, default="data/csv")
    args = parser.parse_args()
    data_root = Path(args.data_root)
    for s in args.symbols:
        run(s, args.max_frames, data_root)


if __name__ == "__main__":
    main()
