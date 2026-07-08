from __future__ import annotations

import argparse
from pathlib import Path

from common import PROJECT_ROOT, infer_symbol_timeframe, load_market_frame, summarize_frame, write_json

from fusion_best import build_training_dataset, train_single_symbol_timeframe


def main() -> None:
    parser = argparse.ArgumentParser(description="Train one baseline model for a single symbol/timeframe dataset.")
    parser.add_argument("--input", required=True, help="CSV or parquet with OHLCV data.")
    parser.add_argument("--symbol")
    parser.add_argument("--timeframe")
    parser.add_argument("--output-root", default=str(PROJECT_ROOT / "models" / "fusion_single"))
    parser.add_argument("--horizon", type=int, default=12)
    parser.add_argument("--threshold", type=float, default=0.0008)
    parser.add_argument("--max-rows", type=int)
    parser.add_argument("--include-omnis-experts", action="store_true")
    parser.add_argument("--include-extended-experts", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    symbol, timeframe = infer_symbol_timeframe(args.input, args.symbol, args.timeframe)
    if args.dry_run:
        frame = load_market_frame(args.input, args.max_rows)
        dataset = build_training_dataset(
            frame,
            horizon=args.horizon,
            threshold=args.threshold,
            include_omnis_experts=args.include_omnis_experts,
            include_extended_experts=args.include_extended_experts,
        )
        report = {
            "mode": "single_model_dry_run",
            "input": args.input,
            "symbol": symbol,
            "timeframe": timeframe,
            "raw": summarize_frame(frame),
            "dataset": summarize_frame(dataset),
        }
        path = write_json(Path(args.output_root) / symbol / timeframe / "dry_run_report.json", report)
        print(f"dry-run ok: {path}")
        return

    result = train_single_symbol_timeframe(
        args.input,
        symbol=symbol,
        timeframe=timeframe,
        output_root=args.output_root,
        horizon=args.horizon,
        threshold=args.threshold,
        include_specialists=True,
    )
    print(result)


if __name__ == "__main__":
    main()
