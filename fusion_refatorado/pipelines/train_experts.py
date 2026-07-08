from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib

from common import PROJECT_ROOT, infer_symbol_timeframe, load_market_frame, summarize_frame, write_json

from fusion_best.expert_training import (
    DEFAULT_EXPERT_ORDER,
    build_expert_dataset_from_feature_frame,
    build_expert_feature_frame,
    save_expert_training_metadata,
    train_lightgbm_expert,
)


def merge_existing_expert_metadata(output_root: Path, reports: dict) -> dict:
    merged = dict(reports)
    for metadata_path in sorted(output_root.glob("*/*_metadata.json")):
        expert_name = metadata_path.parent.name
        if expert_name in merged:
            continue
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        model_path = metadata_path.parent / "model.pkl"
        merged[expert_name] = {
            "status": "ok",
            "metrics": payload.get("metrics", {}),
            "features": len(payload.get("feature_columns", [])),
            "model_path": str(model_path) if model_path.exists() else "",
            "metadata_path": str(metadata_path),
        }
    return merged


def main() -> None:
    parser = argparse.ArgumentParser(description="Train multiple specialist experts from one OHLCV dataset.")
    parser.add_argument("--input", required=True, help="CSV or parquet with OHLCV data.")
    parser.add_argument("--symbol")
    parser.add_argument("--timeframe")
    parser.add_argument("--experts", default=",".join(DEFAULT_EXPERT_ORDER))
    parser.add_argument("--output-root", default=str(PROJECT_ROOT / "models" / "fusion_experts"))
    parser.add_argument("--max-rows", type=int)
    parser.add_argument("--merge-existing-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    symbol, timeframe = infer_symbol_timeframe(args.input, args.symbol, args.timeframe)
    frame = load_market_frame(args.input, args.max_rows)
    feature_frame = None if args.merge_existing_only else build_expert_feature_frame(frame)
    expert_names = tuple(name.strip() for name in args.experts.split(",") if name.strip())
    output_root = Path(args.output_root) / symbol / timeframe
    reports = {}

    for expert_name in (() if args.merge_existing_only else expert_names):
        try:
            dataset = build_expert_dataset_from_feature_frame(feature_frame, expert_name)
            reports[expert_name] = {"status": "ok", "dataset": summarize_frame(dataset)}
            if not args.dry_run:
                result = train_lightgbm_expert(dataset, expert_name)
                expert_dir = output_root / expert_name
                expert_dir.mkdir(parents=True, exist_ok=True)
                joblib.dump(result["model"], expert_dir / "model.pkl")
                save_expert_training_metadata(result, expert_dir)
                reports[expert_name]["metrics"] = result["metrics"]
                reports[expert_name]["model_path"] = str(expert_dir / "model.pkl")
        except Exception as exc:
            reports[expert_name] = {"status": "error", "error": str(exc)}

    if not args.dry_run:
        reports = merge_existing_expert_metadata(output_root, reports)

    path = write_json(output_root / ("dry_run_report.json" if args.dry_run else "training_report.json"), {
        "mode": "experts_dry_run" if args.dry_run else "experts_training",
        "input": args.input,
        "symbol": symbol,
        "timeframe": timeframe,
        "raw": summarize_frame(frame),
        "experts": reports,
    })
    print(f"report: {path}")


if __name__ == "__main__":
    main()
