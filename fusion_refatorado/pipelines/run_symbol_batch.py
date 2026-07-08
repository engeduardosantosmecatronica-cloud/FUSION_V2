from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from common import PROJECT_ROOT, write_json


DEFAULT_SYMBOLS = (
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "GBPJPY",
    "AUDUSD",
    "USDCAD",
    "USDCHF",
    "EURGBP",
    "EURJPY",
    "NZDUSD",
    "EURCHF",
    "AUDCAD",
    "AUDCHF",
    "EURCAD",
    "GBPCHF",
    "AUDJPY",
    "CADCHF",
    "EURAUD",
    "GBPAUD",
    "NZDCAD",
    "AUDNZD",
    "CHFJPY",
    "EURNZD",
)

DEFAULT_EXPERTS = ("volatility", "trend", "orderflow", "sr", "risk", "reversal", "candles", "pullback", "quant")


def unique_symbols(raw: str | None) -> list[str]:
    values = raw.replace(",", " ").split() if raw else list(DEFAULT_SYMBOLS)
    result: list[str] = []
    for value in values:
        symbol = value.strip().upper()
        if symbol and symbol not in result:
            result.append(symbol)
    return result


def run_command(command: list[str], cwd: Path, log_path: Path) -> tuple[str, int, float]:
    start = datetime.now()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"\n[{start.isoformat(timespec='seconds')}] RUN {' '.join(command)}\n")
        log.flush()
        proc = subprocess.run(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, text=True)
        elapsed = (datetime.now() - start).total_seconds()
        log.write(f"[{datetime.now().isoformat(timespec='seconds')}] EXIT {proc.returncode} elapsed={elapsed:.1f}s\n")
    status = "ok" if proc.returncode == 0 else "error"
    return status, proc.returncode, elapsed


def stage_outputs(symbol: str, timeframe: str) -> dict[str, Path]:
    return {
        "experts": PROJECT_ROOT / "models" / "fusion_experts" / symbol / timeframe / "training_report.json",
        "backtest": PROJECT_ROOT / "reports" / "fusion_backtests" / symbol / timeframe / "calibrated_weights.json",
        "walkforward": PROJECT_ROOT / "reports" / "fusion_walkforward" / symbol / timeframe / "walkforward_weights.json",
        "walkforward_ensemble": PROJECT_ROOT / "models" / "fusion_ensemble" / f"{symbol}_{timeframe}_ensemble_walkforward_config.json",
    }


def missing_experts(symbol: str, timeframe: str, experts: tuple[str, ...] = DEFAULT_EXPERTS) -> list[str]:
    root = PROJECT_ROOT / "models" / "fusion_experts" / symbol / timeframe
    return [expert for expert in experts if not (root / expert / "model.pkl").exists()]


def summarize_weights(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    weights = payload.get("weights", [])
    positive = [row for row in weights if float(row.get("calibrated_weight", 0.0) or 0.0) > 0]
    return {
        "positive_count": len(positive),
        "top": [
            {
                "expert": row.get("expert"),
                "mode": row.get("mode", "NORMAL"),
                "weight": row.get("calibrated_weight"),
                "trades": row.get("trades"),
                "winrate": row.get("winrate"),
                "total_return": row.get("total_return"),
            }
            for row in positive[:5]
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Fusion expert stages for a list of symbols/timeframes.")
    parser.add_argument("--symbols", help="Comma/space separated symbols. Defaults to the requested FX list.")
    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--data-root", default=str(PROJECT_ROOT.parent / "data" / "parquet"))
    parser.add_argument("--stages", default="experts,backtest,walkforward,ensemble", help="Stages: experts,backtest,walkforward,ensemble")
    parser.add_argument("--resume", action="store_true", help="Skip stages whose output already exists.")
    parser.add_argument("--limit", type=int, help="Process only the first N symbols.")
    parser.add_argument("--min-confidence", type=float, default=0.55)
    parser.add_argument("--min-trades", type=int, default=30)
    parser.add_argument("--train-fraction", type=float, default=0.80)
    args = parser.parse_args()

    symbols = unique_symbols(args.symbols)
    if args.limit:
        symbols = symbols[: args.limit]
    timeframe = args.timeframe.upper()
    stages = {stage.strip().lower() for stage in args.stages.split(",") if stage.strip()}
    data_root = Path(args.data_root) / timeframe
    batch_root = PROJECT_ROOT / "reports" / "batch_runs" / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{timeframe}"
    batch_root.mkdir(parents=True, exist_ok=True)
    rows = []

    for index, symbol in enumerate(symbols, start=1):
        input_path = data_root / f"{symbol}.parquet"
        symbol_log = batch_root / f"{symbol}.log"
        outputs = stage_outputs(symbol, timeframe)
        row: dict[str, Any] = {
            "symbol": symbol,
            "timeframe": timeframe,
            "input": str(input_path),
            "input_exists": input_path.exists(),
            "started_at": datetime.now().isoformat(timespec="seconds"),
        }
        print(f"[{index}/{len(symbols)}] {symbol} {timeframe}")
        if not input_path.exists():
            row["status"] = "missing_input"
            rows.append(row)
            pd.DataFrame(rows).to_csv(batch_root / "batch_summary.csv", index=False)
            continue

        commands: list[tuple[str, list[str], Path | None]] = []
        py = sys.executable
        if "experts" in stages:
            experts_to_train = missing_experts(symbol, timeframe) if args.resume else list(DEFAULT_EXPERTS)
            expert_command = [
                py,
                str(PROJECT_ROOT / "pipelines" / "train_experts.py"),
                "--input",
                str(input_path),
                "--symbol",
                symbol,
                "--timeframe",
                timeframe,
            ]
            if experts_to_train:
                expert_command.extend(["--experts", ",".join(experts_to_train)])
            else:
                expert_command.append("--merge-existing-only")
            commands.append(
                (
                    "experts",
                    expert_command,
                    outputs["experts"],
                )
            )
        if "backtest" in stages:
            commands.append(
                (
                    "backtest",
                    [
                        py,
                        str(PROJECT_ROOT / "pipelines" / "backtest_fusion_experts.py"),
                        "--input",
                        str(input_path),
                        "--symbol",
                        symbol,
                        "--timeframe",
                        timeframe,
                        "--min-confidence",
                        str(args.min_confidence),
                        "--min-trades",
                        str(args.min_trades),
                    ],
                    outputs["backtest"],
                )
            )
        if "walkforward" in stages:
            commands.append(
                (
                    "walkforward",
                    [
                        py,
                        str(PROJECT_ROOT / "pipelines" / "walkforward_fusion_experts.py"),
                        "--input",
                        str(input_path),
                        "--symbol",
                        symbol,
                        "--timeframe",
                        timeframe,
                        "--train-fraction",
                        str(args.train_fraction),
                        "--min-confidence",
                        str(args.min_confidence),
                        "--min-trades",
                        str(args.min_trades),
                    ],
                    outputs["walkforward"],
                )
            )
        if "ensemble" in stages:
            commands.append(
                (
                    "ensemble",
                    [
                        py,
                        str(PROJECT_ROOT / "pipelines" / "train_fusion_ensemble.py"),
                        "--calibration-report",
                        str(outputs["walkforward"]),
                        "--output",
                        str(outputs["walkforward_ensemble"]),
                    ],
                    outputs["walkforward_ensemble"],
                )
            )

        symbol_ok = True
        for stage, command, expected in commands:
            if args.resume and expected is not None and expected.exists():
                row[f"{stage}_status"] = "skipped"
                row[f"{stage}_output"] = str(expected)
                continue
            status, code, elapsed = run_command(command, PROJECT_ROOT.parent, symbol_log)
            row[f"{stage}_status"] = status
            row[f"{stage}_code"] = code
            row[f"{stage}_elapsed_sec"] = elapsed
            row[f"{stage}_output"] = str(expected) if expected else ""
            if status != "ok":
                symbol_ok = False
                break
        row["status"] = "ok" if symbol_ok else "error"
        row["finished_at"] = datetime.now().isoformat(timespec="seconds")
        row["backtest_summary"] = summarize_weights(outputs["backtest"])
        row["walkforward_summary"] = summarize_weights(outputs["walkforward"])
        rows.append(row)
        pd.DataFrame(rows).to_csv(batch_root / "batch_summary.csv", index=False)
        write_json(batch_root / "batch_summary.json", {"rows": rows})

    print(f"summary: {batch_root / 'batch_summary.csv'}")
    print(f"logs: {batch_root}")


if __name__ == "__main__":
    main()
