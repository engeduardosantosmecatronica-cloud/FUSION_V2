from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from common import PROJECT_ROOT, write_json


def load_weights(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("weights", [])


def positive_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if float(row.get("calibrated_weight", 0.0) or 0.0) > 0]


def classify_symbol(top: dict[str, Any], min_trades: int, min_winrate: float, min_return: float, max_drawdown: float) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if not top:
        return "rejected", ["sem expert positivo no walk-forward"]
    trades = int(top.get("trades", 0) or 0)
    winrate = float(top.get("winrate", 0.0) or 0.0)
    total_return = float(top.get("total_return", 0.0) or 0.0)
    drawdown = float(top.get("max_drawdown", 0.0) or 0.0)
    if trades < min_trades:
        reasons.append(f"trades abaixo do minimo ({trades} < {min_trades})")
    if winrate < min_winrate:
        reasons.append(f"winrate abaixo do minimo ({winrate:.4f} < {min_winrate:.4f})")
    if total_return < min_return:
        reasons.append(f"retorno abaixo do minimo ({total_return:.6f} < {min_return:.6f})")
    if drawdown < max_drawdown:
        reasons.append(f"drawdown abaixo do limite ({drawdown:.6f} < {max_drawdown:.6f})")
    if not reasons:
        return "approved", ["criterios conservadores atendidos"]
    if total_return > 0 and trades >= max(30, min_trades // 2):
        return "watchlist", reasons
    return "rejected", reasons


def main() -> None:
    parser = argparse.ArgumentParser(description="Select M5 Fusion candidates for production promotion.")
    parser.add_argument("--symbols", required=True, help="Comma/space separated symbols.")
    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--min-trades", type=int, default=100)
    parser.add_argument("--min-winrate", type=float, default=0.52)
    parser.add_argument("--min-return", type=float, default=0.01)
    parser.add_argument("--max-drawdown", type=float, default=-0.15)
    parser.add_argument("--output-root", default=str(PROJECT_ROOT / "reports" / "production_selection"))
    args = parser.parse_args()

    symbols = []
    for item in args.symbols.replace(",", " ").split():
        symbol = item.strip().upper()
        if symbol and symbol not in symbols:
            symbols.append(symbol)

    rows = []
    for symbol in symbols:
        wf_path = PROJECT_ROOT / "reports" / "fusion_walkforward" / symbol / args.timeframe / "walkforward_weights.json"
        bt_path = PROJECT_ROOT / "reports" / "fusion_backtests" / symbol / args.timeframe / "calibrated_weights.json"
        wf_positive = positive_rows(load_weights(wf_path))
        bt_positive = positive_rows(load_weights(bt_path))
        top = wf_positive[0] if wf_positive else {}
        status, reasons = classify_symbol(top, args.min_trades, args.min_winrate, args.min_return, args.max_drawdown)
        rows.append(
            {
                "symbol": symbol,
                "timeframe": args.timeframe,
                "status": status,
                "reason": "; ".join(reasons),
                "walkforward_positive_count": len(wf_positive),
                "backtest_positive_count": len(bt_positive),
                "top_expert": top.get("expert", ""),
                "top_mode": top.get("mode", ""),
                "top_weight": top.get("calibrated_weight", 0.0) if top else 0.0,
                "top_trades": top.get("trades", 0) if top else 0,
                "top_winrate": top.get("winrate", 0.0) if top else 0.0,
                "top_total_return": top.get("total_return", 0.0) if top else 0.0,
                "top_max_drawdown": top.get("max_drawdown", 0.0) if top else 0.0,
                "ensemble_path": str(PROJECT_ROOT / "models" / "fusion_ensemble" / f"{symbol}_{args.timeframe}_ensemble_walkforward_config.json"),
                "walkforward_report": str(wf_path),
                "backtest_report": str(bt_path),
            }
        )

    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows).sort_values(["status", "top_total_return"], ascending=[True, False])
    csv_path = output_root / f"{args.timeframe}_production_candidates.csv"
    json_path = output_root / f"{args.timeframe}_production_candidates.json"
    registry_root = PROJECT_ROOT / "models" / "production_registry"
    registry_root.mkdir(parents=True, exist_ok=True)
    approved = frame[frame["status"] == "approved"].copy()
    approved_csv = registry_root / f"{args.timeframe}_approved_ensembles.csv"
    approved_json = registry_root / f"{args.timeframe}_approved_ensembles.json"
    frame.to_csv(csv_path, index=False)
    approved.to_csv(approved_csv, index=False)
    write_json(
        json_path,
        {
            "timeframe": args.timeframe,
            "criteria": {
                "min_trades": args.min_trades,
                "min_winrate": args.min_winrate,
                "min_return": args.min_return,
                "max_drawdown": args.max_drawdown,
            },
            "counts": frame["status"].value_counts().to_dict(),
            "rows": frame.to_dict(orient="records"),
        },
    )
    write_json(
        approved_json,
        {
            "timeframe": args.timeframe,
            "status": "staging_approved",
            "selection_report": str(csv_path),
            "count": int(len(approved)),
            "symbols": approved["symbol"].tolist(),
            "ensembles": approved[
                [
                    "symbol",
                    "timeframe",
                    "ensemble_path",
                    "top_expert",
                    "top_mode",
                    "top_weight",
                    "top_trades",
                    "top_winrate",
                    "top_total_return",
                    "top_max_drawdown",
                ]
            ].to_dict(orient="records"),
        },
    )
    print(f"csv: {csv_path}")
    print(f"json: {json_path}")
    print(f"approved_csv: {approved_csv}")
    print(f"approved_json: {approved_json}")


if __name__ == "__main__":
    main()
