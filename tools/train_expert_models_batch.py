from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml


PROJECT_DIR = Path(__file__).resolve().parents[1]
TIMEFRAMES = ["M5", "M15", "M30", "H1", "H4", "D1"]


def load_symbols(config_path: Path) -> list[str]:
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return [str(symbol).upper() for symbol in cfg.get("symbols", [])]


def parquet_path(symbol: str, timeframe: str, parquet_dir: Path) -> Path:
    candidates = [
        parquet_dir / timeframe / f"{symbol}.parquet",
        parquet_dir / timeframe / f"{symbol}-F.parquet",
    ]
    if symbol in {"GOLD", "XAUUSD"}:
        candidates.extend(
            [
                parquet_dir / timeframe / "XAUUSD.parquet",
                parquet_dir / timeframe / "XAUUSD-F.parquet",
                parquet_dir / timeframe / "GOLD.parquet",
            ]
        )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def run_job(
    symbol: str,
    timeframe: str,
    input_path: Path,
    output_root: Path,
    max_rows: int,
    dry_run: bool,
) -> tuple[str, str]:
    script = PROJECT_DIR / "fusion_refatorado" / "pipelines" / "train_experts.py"
    cmd = [
        sys.executable,
        str(script),
        "--input",
        str(input_path),
        "--symbol",
        symbol,
        "--timeframe",
        timeframe,
        "--output-root",
        str(output_root),
    ]
    if max_rows > 0:
        cmd.extend(["--max-rows", str(max_rows)])
    if dry_run:
        cmd.append("--dry-run")

    completed = subprocess.run(
        cmd,
        cwd=PROJECT_DIR,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return ("ok" if completed.returncode == 0 else "error", completed.stdout[-4000:])


def main() -> None:
    parser = argparse.ArgumentParser(description="Treina experts por ativo/timeframe em lote.")
    parser.add_argument("--config", default="config/fusion_config.yaml")
    parser.add_argument("--symbols", nargs="*", default=[])
    parser.add_argument("--timeframes", nargs="*", default=TIMEFRAMES)
    parser.add_argument("--parquet-dir", default="data/parquet")
    parser.add_argument("--output-root", default="models_experts")
    parser.add_argument("--report-dir", default="reports/expert_model_training")
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    symbols = [symbol.upper() for symbol in args.symbols] or load_symbols(PROJECT_DIR / args.config)
    timeframes = [tf.upper() for tf in args.timeframes]
    parquet_dir = PROJECT_DIR / args.parquet_dir
    output_root = PROJECT_DIR / args.output_root
    report_dir = PROJECT_DIR / args.report_dir
    report_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, str]] = []
    for symbol in symbols:
        for timeframe in timeframes:
            input_path = parquet_path(symbol, timeframe, parquet_dir)
            report_path = output_root / symbol / timeframe / ("dry_run_report.json" if args.dry_run else "training_report.json")
            if not input_path.exists():
                rows.append(
                    {
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "status": "missing_input",
                        "input": str(input_path),
                        "report": "",
                        "message": "parquet nao encontrado",
                    }
                )
                print(f"[MISS] {symbol} {timeframe} | {input_path}", flush=True)
                continue
            if report_path.exists() and not args.force:
                rows.append(
                    {
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "status": "skipped_existing",
                        "input": str(input_path),
                        "report": str(report_path),
                        "message": "ja treinado",
                    }
                )
                print(f"[SKIP] {symbol} {timeframe}", flush=True)
                continue

            status, output = run_job(symbol, timeframe, input_path, output_root, args.max_rows, args.dry_run)
            rows.append(
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "status": status,
                    "input": str(input_path),
                    "report": str(report_path) if report_path.exists() else "",
                    "message": output.replace("\r", " ").replace("\n", " ")[:2000],
                }
            )
            print(f"[{status.upper()}] {symbol} {timeframe}", flush=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = report_dir / f"expert_model_training_progress_{stamp}.json"
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Relatorio: {path}", flush=True)


if __name__ == "__main__":
    main()
