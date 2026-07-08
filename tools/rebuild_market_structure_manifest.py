from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reconstrói o manifest dos CSVs de market structure.")
    parser.add_argument("--market-structure-dir", default="reports/market_structure")
    return parser.parse_args()


def infer_symbol_timeframe(path: Path) -> tuple[str, str]:
    stem = path.name.replace("_market_structure.csv", "")
    parts = stem.split("_")
    if len(parts) < 2:
        return "", ""
    return "_".join(parts[:-1]).upper(), parts[-1].upper()


def main() -> None:
    args = parse_args()
    base = Path(args.market_structure_dir)
    if not base.is_absolute():
        base = PROJECT_DIR / base
    manifest = []
    for path in sorted(base.glob("*_market_structure.csv")):
        symbol, timeframe = infer_symbol_timeframe(path)
        if not symbol or not timeframe:
            continue
        try:
            header = pd.read_csv(path, nrows=0)
            rows = sum(1 for _ in path.open("r", encoding="utf-8", errors="ignore")) - 1
        except Exception:
            continue
        manifest.append(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "rows": max(0, int(rows)),
                "columns": int(len(header.columns)),
                "path": str(path),
            }
        )
    out_path = base / "manifest.json"
    out_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Manifest reconstruido: {out_path}")
    print(f"Arquivos: {len(manifest)}")


if __name__ == "__main__":
    main()
