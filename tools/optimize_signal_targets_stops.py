from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Otimiza TP/SL liquidos por ativo/timeframe/lado usando relatorio M1 com spread."
    )
    parser.add_argument("input_csv", help="CSV gerado por tools/analyze_signal_path_outcomes.py com spread.")
    parser.add_argument("--output-dir", default="reports/signal_path_optimization")
    parser.add_argument("--window", default="1p0", help="Janela do relatorio. Padrao: 1p0.")
    parser.add_argument("--targets", default="5,10,15,20,25,30,40,50")
    parser.add_argument("--stops", default="10,15,20,25,30,40,50,70,100")
    parser.add_argument("--min-signals", type=int, default=10)
    parser.add_argument("--max-loss-streak", type=int, default=4)
    parser.add_argument("--min-win-rate", type=float, default=45.0)
    parser.add_argument("--commission-points", type=float, default=0.0)
    return parser.parse_args()


def parse_numbers(value: str) -> list[float]:
    result: list[float] = []
    for item in str(value or "").split(","):
        item = item.strip()
        if item:
            result.append(float(item))
    return result


def max_consecutive_losses(values: list[str]) -> int:
    worst = 0
    current = 0
    for value in values:
        if value == "loss":
            current += 1
            worst = max(worst, current)
        elif value == "win":
            current = 0
    return worst


def simulate_group(group: pd.DataFrame, window: str, tp: float, sl: float, commission: float) -> dict:
    mfe = pd.to_numeric(group[f"w{window}_net_mfe_points"], errors="coerce").fillna(-10**9)
    mae = pd.to_numeric(group[f"w{window}_net_mae_points"], errors="coerce").fillna(10**9)

    target = tp + commission
    stop = sl + commission
    first_col = f"w{window}_t{str(tp).replace('.', 'p')}_net_first"

    outcomes: list[str] = []
    points: list[float] = []
    for idx, row in group.iterrows():
        hit_tp = float(mfe.loc[idx]) >= target
        hit_sl = float(mae.loc[idx]) >= stop
        first = str(row.get(first_col, "") or "")

        if hit_tp and hit_sl:
            if first == "target":
                outcomes.append("win")
                points.append(tp)
            elif first == "adverse":
                outcomes.append("loss")
                points.append(-sl)
            else:
                outcomes.append("ambiguous")
                points.append(0.0)
        elif hit_tp:
            outcomes.append("win")
            points.append(tp)
        elif hit_sl:
            outcomes.append("loss")
            points.append(-sl)
        else:
            outcomes.append("open")
            close_col = f"w{window}_net_close_points"
            close_points = row.get(close_col, 0.0)
            try:
                points.append(float(close_points))
            except (TypeError, ValueError):
                points.append(0.0)

    total = len(outcomes)
    wins = outcomes.count("win")
    losses = outcomes.count("loss")
    resolved = wins + losses
    win_rate = (wins / resolved * 100.0) if resolved else 0.0
    avg_points = sum(points) / total if total else 0.0
    expectancy = avg_points
    loss_streak = max_consecutive_losses(outcomes)
    profit_factor = (
        sum(p for p in points if p > 0) / abs(sum(p for p in points if p < 0))
        if abs(sum(p for p in points if p < 0)) > 0
        else 999.0
    )

    return {
        "signals": total,
        "wins": wins,
        "losses": losses,
        "open_or_ambiguous": total - resolved,
        "win_rate": round(win_rate, 2),
        "avg_points": round(avg_points, 2),
        "total_points": round(sum(points), 2),
        "profit_factor": round(profit_factor, 2),
        "max_loss_streak": loss_streak,
    }


def main() -> None:
    args = parse_args()
    path = Path(args.input_csv)
    df = pd.read_csv(path, low_memory=False)
    ok = df[df["status"].eq("ok")].copy()
    ok = ok.sort_values(["symbol", "signal_timeframe", "side", "entry_time"])

    targets = parse_numbers(args.targets)
    stops = parse_numbers(args.stops)
    rows: list[dict] = []

    group_cols = ["symbol", "signal_timeframe", "side"]
    for keys, group in ok.groupby(group_cols):
        symbol, timeframe, side = keys
        if len(group) < args.min_signals:
            continue
        for tp in targets:
            for sl in stops:
                metrics = simulate_group(group, args.window, tp, sl, args.commission_points)
                row = {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "side": side,
                    "tp_net_points": tp,
                    "sl_net_points": sl,
                    **metrics,
                }
                row["score"] = round(
                    row["avg_points"] * 10
                    + row["win_rate"] * 0.35
                    + min(row["profit_factor"], 5.0) * 5
                    - row["max_loss_streak"] * 8,
                    2,
                )
                row["recommended"] = (
                    row["signals"] >= args.min_signals
                    and row["win_rate"] >= args.min_win_rate
                    and row["avg_points"] > 0
                    and row["max_loss_streak"] <= args.max_loss_streak
                )
                rows.append(row)

    out = pd.DataFrame(rows)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = path.stem
    all_path = output_dir / f"tp_sl_optimization_{stem}.csv"
    out.to_csv(all_path, index=False)

    if out.empty:
        print(f"Sem grupos suficientes. Saida: {all_path}")
        return

    ranked = out.sort_values(["recommended", "score", "avg_points"], ascending=[False, False, False])
    best = ranked.groupby(["symbol", "timeframe", "side"], as_index=False).head(1)
    best_path = output_dir / f"tp_sl_best_by_group_{stem}.csv"
    best.to_csv(best_path, index=False)

    recommended = ranked[ranked["recommended"].eq(True)]
    recommended_path = output_dir / f"tp_sl_recommended_{stem}.csv"
    recommended.to_csv(recommended_path, index=False)

    print(f"Configuracoes avaliadas: {len(out)}")
    print(f"Saida completa: {all_path}")
    print(f"Melhor por grupo: {best_path}")
    print(f"Recomendadas: {recommended_path}")
    print(best.head(30).to_string(index=False))


if __name__ == "__main__":
    main()
