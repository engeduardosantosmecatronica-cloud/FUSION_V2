from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera resumo Markdown do ranking OHLCV.")
    parser.add_argument("--labels", default="reports/market_structure_labels/market_structure_labels_tp100_sl100_lh100.csv")
    parser.add_argument("--ranking", default="reports/market_structure_labels/market_structure_feature_ranking_tp100_sl100_lh100.csv")
    parser.add_argument("--output", default="reports/market_structure_labels/market_structure_ranking_summary.md")
    parser.add_argument("--top", type=int, default=30)
    return parser.parse_args()


def markdown_table(df: pd.DataFrame, cols: list[str]) -> list[str]:
    if df.empty:
        return ["_Sem dados._"]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df[cols].iterrows():
        values = []
        for col in cols:
            value = row[col]
            if isinstance(value, float):
                values.append(f"{value:.4f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def main() -> None:
    args = parse_args()
    labels = pd.read_csv(args.labels)
    ranking = pd.read_csv(args.ranking)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Market Structure Feature Ranking",
        "",
        f"- Labels: {len(labels):,}".replace(",", "."),
        f"- Ranking rows: {len(ranking):,}".replace(",", "."),
        f"- Ativos: {labels['symbol'].nunique()}",
        f"- Timeframes: {', '.join(sorted(labels['timeframe'].unique()))}",
        "",
        "## Win rate geral por lado/timeframe",
        "",
    ]
    overview_rows = []
    for timeframe, group in labels.groupby("timeframe"):
        overview_rows.append(
            {
                "timeframe": timeframe,
                "samples": len(group),
                "buy_wr": group["buy_target_before_stop"].mean(),
                "sell_wr": group["sell_target_before_stop"].mean(),
                "buy_timeout_pct": (group["buy_result"] == "timeout").mean(),
                "sell_timeout_pct": (group["sell_result"] == "timeout").mean(),
            }
        )
    overview = pd.DataFrame(overview_rows).sort_values("timeframe")
    lines.extend(markdown_table(overview, ["timeframe", "samples", "buy_wr", "sell_wr", "buy_timeout_pct", "sell_timeout_pct"]))

    lines.extend(["", "## Top edges positivos", ""])
    top = ranking.sort_values(["edge_score", "samples"], ascending=[False, False]).head(args.top)
    lines.extend(markdown_table(top, ["feature", "side", "symbol", "timeframe", "bucket", "samples", "win_rate", "edge_score"]))

    lines.extend(["", "## Piores buckets", ""])
    worst = ranking.sort_values(["edge_score", "samples"], ascending=[True, False]).head(args.top)
    lines.extend(markdown_table(worst, ["feature", "side", "symbol", "timeframe", "bucket", "samples", "win_rate", "edge_score"]))

    lines.extend(["", "## Melhores features por frequencia no top 500", ""])
    top500 = ranking.sort_values(["edge_score", "samples"], ascending=[False, False]).head(500)
    feature_counts = top500.groupby(["feature", "side"]).size().reset_index(name="top500_count")
    feature_counts = feature_counts.sort_values("top500_count", ascending=False).head(args.top)
    lines.extend(markdown_table(feature_counts, ["feature", "side", "top500_count"]))

    output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Resumo: {output}")


if __name__ == "__main__":
    main()
