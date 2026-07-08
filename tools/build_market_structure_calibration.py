from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seleciona candidatos de calibracao Market Structure por ativo/timeframe/lado."
    )
    parser.add_argument(
        "--ranking",
        default="reports/market_structure_labels/market_structure_feature_ranking_atr1.5_slatr1_lh100.csv",
    )
    parser.add_argument("--output-dir", default="reports/market_structure_calibration")
    parser.add_argument("--min-samples", type=int, default=300)
    parser.add_argument("--min-win-rate", type=float, default=0.60)
    parser.add_argument("--min-edge-score", type=float, default=0.50)
    parser.add_argument("--top-per-group", type=int, default=5)
    return parser.parse_args()


def load_candidates(path: Path, min_samples: int, min_win_rate: float, min_edge_score: float) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    ranking = pd.read_csv(path)
    required = {"symbol", "timeframe", "side", "feature", "bucket", "samples", "win_rate", "edge_score"}
    if not required.issubset(ranking.columns):
        missing = ", ".join(sorted(required - set(ranking.columns)))
        raise ValueError(f"Ranking sem colunas obrigatorias: {missing}")
    candidates = ranking[
        (ranking["samples"] >= min_samples)
        & (ranking["win_rate"] >= min_win_rate)
        & (ranking["edge_score"] >= min_edge_score)
    ].copy()
    if candidates.empty:
        return candidates
    return candidates.sort_values(["symbol", "timeframe", "side", "edge_score", "samples"], ascending=[True, True, True, False, False])


def top_by_group(candidates: pd.DataFrame, top_per_group: int) -> pd.DataFrame:
    if candidates.empty:
        return candidates
    return (
        candidates.groupby(["symbol", "timeframe", "side"], group_keys=False)
        .head(top_per_group)
        .reset_index(drop=True)
    )


def build_config_preview(selected: pd.DataFrame) -> dict:
    config: dict[str, dict] = {}
    if selected.empty:
        return config
    for (symbol, timeframe, side), group in selected.groupby(["symbol", "timeframe", "side"]):
        symbol_block = config.setdefault(symbol, {})
        timeframe_block = symbol_block.setdefault(timeframe, {})
        timeframe_block[side] = [
            {
                "feature": str(row.feature),
                "bucket": str(row.bucket),
                "samples": int(row.samples),
                "win_rate": round(float(row.win_rate), 4),
                "edge_score": round(float(row.edge_score), 4),
            }
            for row in group.itertuples(index=False)
        ]
    return config


def write_markdown(path: Path, selected: pd.DataFrame, args: argparse.Namespace) -> None:
    lines = ["# Market Structure Calibration Candidates", ""]
    lines.extend(
        [
            "Candidatos offline para calibracao. Nenhuma regra daqui e aplicada automaticamente no robo.",
            "",
            "## Filtros",
            "",
            f"- Min samples: {args.min_samples}",
            f"- Min win rate: {args.min_win_rate:.2%}",
            f"- Min edge score: {args.min_edge_score:.3f}",
            f"- Top por ativo/timeframe/lado: {args.top_per_group}",
            "",
        ]
    )
    if selected.empty:
        lines.append("Nenhum candidato passou nos filtros.")
        path.write_text("\n".join(lines), encoding="utf-8")
        return

    lines.extend(
        [
            f"- Ativos com candidatos: {selected['symbol'].nunique()}",
            f"- Combinacoes ativo/timeframe/lado: {selected.groupby(['symbol', 'timeframe', 'side']).ngroups}",
            f"- Regras candidatas: {len(selected)}",
            "",
            "## Top candidatos",
            "",
            "| symbol | timeframe | side | feature | bucket | samples | win_rate | edge_score |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    top = selected.sort_values(["edge_score", "samples"], ascending=[False, False]).head(80)
    for row in top.itertuples(index=False):
        lines.append(
            f"| {row.symbol} | {row.timeframe} | {row.side} | {row.feature} | {row.bucket} | "
            f"{int(row.samples)} | {float(row.win_rate):.2%} | {float(row.edge_score):.4f} |"
        )

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ranking_path = Path(args.ranking)
    candidates = load_candidates(ranking_path, args.min_samples, args.min_win_rate, args.min_edge_score)
    selected = top_by_group(candidates, args.top_per_group)

    suffix = ranking_path.stem.replace("market_structure_feature_ranking_", "")
    selected_path = output_dir / f"market_structure_calibration_candidates_{suffix}.csv"
    preview_path = output_dir / f"market_structure_calibration_preview_{suffix}.json"
    report_path = output_dir / f"market_structure_calibration_candidates_{suffix}.md"

    selected.to_csv(selected_path, index=False)
    preview_path.write_text(json.dumps(build_config_preview(selected), indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(report_path, selected, args)

    print(f"Candidatos: {len(selected)}")
    print(f"Saida: {output_dir}")


if __name__ == "__main__":
    main()
