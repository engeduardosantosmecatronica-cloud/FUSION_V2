from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fusion.engines import MarketRegimeEngine, RegimeConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verifica Market Regime Engine usando parquet local.")
    parser.add_argument("--config", default="config/fusion_config.yaml")
    parser.add_argument("--symbol", default="EURUSD")
    parser.add_argument("--timeframe", default="H1")
    parser.add_argument("--side", default="BUY", choices=["BUY", "SELL", "NEUTRAL"])
    parser.add_argument("--parquet-dir", default="data/parquet")
    parser.add_argument("--bars", type=int, default=260)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8")) or {}
    cfg = ((config.get("entry_filters") or {}).get("market_regime") or {})
    path = Path(args.parquet_dir) / args.timeframe.upper() / f"{args.symbol.upper()}.parquet"
    if not path.exists():
        raise SystemExit(f"Parquet nao encontrado: {path}")
    df = pd.read_parquet(path).tail(max(args.bars, int(cfg.get("bars", args.bars) or args.bars)))
    if "time" not in df.columns and "date" in df.columns:
        df["time"] = pd.to_datetime(df["date"])
    elif "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"])
    else:
        raise SystemExit("Arquivo sem coluna time/date.")

    engine = MarketRegimeEngine(
        RegimeConfig(
            atr_period=int(cfg.get("atr_period", 14) or 14),
            long_window=int(cfg.get("long_window", 100) or 100),
            adx_period=int(cfg.get("adx_period", 14) or 14),
            efficiency_window=int(cfg.get("efficiency_window", 20) or 20),
            entropy_window=int(cfg.get("entropy_window", 30) or 30),
            compression_threshold=float(cfg.get("compression_threshold", 0.75) or 0.75),
            expansion_threshold=float(cfg.get("expansion_threshold", 1.25) or 1.25),
            trend_adx_threshold=float(cfg.get("trend_adx_threshold", 22.0) or 22.0),
            range_adx_threshold=float(cfg.get("range_adx_threshold", 16.0) or 16.0),
            panic_atr_percentile=float(cfg.get("panic_atr_percentile", 0.95) or 0.95),
        )
    )
    output = engine.evaluate(df[["time", "open", "high", "low", "close"]], side=args.side.upper())
    print(json.dumps(output.__dict__, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
