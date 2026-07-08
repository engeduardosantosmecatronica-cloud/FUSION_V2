from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from fusion.features.market_structure import (  # noqa: E402
    MarketStructureConfig,
    build_asset_profile,
    build_market_structure_features,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera features observacionais de estrutura de mercado.")
    parser.add_argument("--symbols", nargs="+", required=True)
    parser.add_argument("--timeframes", nargs="+", default=["M5", "M15", "H1"])
    parser.add_argument("--parquet-dir", default="data/parquet")
    parser.add_argument("--output-dir", default="reports/market_structure")
    parser.add_argument("--tail", type=int, default=5000, help="Quantidade maxima de candles por ativo/timeframe.")
    parser.add_argument("--include-raw-ohlcv", action="store_true")
    parser.add_argument("--profile", action="store_true", help="Tambem gera perfil estatistico por ativo.")
    return parser.parse_args()


def read_frame(parquet_dir: Path, symbol: str, timeframe: str, tail: int) -> pd.DataFrame:
    path = parquet_dir / timeframe / f"{symbol}.parquet"
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_parquet(path)
    if "date" in frame.columns:
        frame["date"] = pd.to_datetime(frame["date"])
        frame = frame.sort_values("date")
    return frame.tail(tail).copy()


def main() -> None:
    args = parse_args()
    parquet_dir = Path(args.parquet_dir)
    output_dir = Path(args.output_dir)
    if not parquet_dir.is_absolute():
        parquet_dir = PROJECT_DIR / parquet_dir
    if not output_dir.is_absolute():
        output_dir = PROJECT_DIR / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    config = MarketStructureConfig()
    manifest = []
    profiles = []

    for symbol in [item.upper() for item in args.symbols]:
        symbol_frames: dict[str, pd.DataFrame] = {}
        for timeframe in [item.upper() for item in args.timeframes]:
            frame = read_frame(parquet_dir, symbol, timeframe, args.tail)
            if frame.empty:
                print(f"[SKIP] {symbol} {timeframe}: parquet ausente ou vazio", flush=True)
                continue
            symbol_frames[timeframe] = frame
            features = build_market_structure_features(
                frame,
                config=config,
                include_raw_ohlcv=args.include_raw_ohlcv,
            )
            features.insert(0, "symbol", symbol)
            features.insert(1, "timeframe", timeframe)
            out_path = output_dir / f"{symbol}_{timeframe}_market_structure.csv"
            features.to_csv(out_path, index=False)
            manifest.append(
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "rows": int(len(features)),
                    "columns": int(len(features.columns)),
                    "path": str(out_path),
                }
            )
            print(f"[OK] {symbol} {timeframe}: {len(features)} linhas, {len(features.columns)} colunas", flush=True)

        if args.profile and symbol_frames:
            profile = build_asset_profile(symbol_frames, symbol)
            profiles.append(profile)

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    if profiles:
        profile_path = output_dir / "asset_profiles.json"
        profile_path.write_text(json.dumps(profiles, indent=2, ensure_ascii=False), encoding="utf-8")
        pd.DataFrame(profiles).to_csv(output_dir / "asset_profiles.csv", index=False)
    print(f"Manifest: {manifest_path}", flush=True)


if __name__ == "__main__":
    main()
