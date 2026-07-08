from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compara calibracoes Market Structure candidatas.")
    parser.add_argument("--calibration-dir", default="reports/market_structure_calibration")
    parser.add_argument("--output", default="reports/market_structure_calibration/market_structure_calibration_comparison.md")
    return parser.parse_args()


def load_calibrations(directory: Path) -> pd.DataFrame:
    frames = []
    for path in sorted(directory.glob("market_structure_calibration_candidates_*.csv")):
        frame = pd.read_csv(path)
        if frame.empty:
            continue
        name = path.stem.replace("market_structure_calibration_candidates_", "")
        frame["calibration"] = name
        frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


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


def write_report(path: Path, data: pd.DataFrame) -> None:
    lines = ["# Market Structure Calibration Comparison", ""]
    if data.empty:
        lines.append("Nenhuma calibracao encontrada.")
        path.write_text("\n".join(lines), encoding="utf-8")
        return

    summary = (
        data.groupby("calibration")
        .agg(
            rules=("feature", "size"),
            assets=("symbol", "nunique"),
            groups=("side", lambda s: data.loc[s.index, ["symbol", "timeframe", "side"]].drop_duplicates().shape[0]),
            avg_win_rate=("win_rate", "mean"),
            max_win_rate=("win_rate", "max"),
            avg_edge=("edge_score", "mean"),
        )
        .reset_index()
        .sort_values("rules", ascending=False)
    )
    lines.extend(["## Resumo", ""])
    lines.extend(markdown_table(summary, ["calibration", "rules", "assets", "groups", "avg_win_rate", "max_win_rate", "avg_edge"]))

    side_summary = (
        data.groupby(["calibration", "side"])
        .agg(rules=("feature", "size"), avg_win_rate=("win_rate", "mean"), avg_edge=("edge_score", "mean"))
        .reset_index()
        .sort_values(["calibration", "rules"], ascending=[True, False])
    )
    lines.extend(["", "## Por lado", ""])
    lines.extend(markdown_table(side_summary, ["calibration", "side", "rules", "avg_win_rate", "avg_edge"]))

    overlap = (
        data.groupby(["symbol", "timeframe", "side"])
        .agg(calibrations=("calibration", lambda s: ", ".join(sorted(set(s)))), rules=("feature", "size"), best_win_rate=("win_rate", "max"))
        .reset_index()
    )
    overlap["calibration_count"] = overlap["calibrations"].str.count(",") + 1
    stable = overlap[overlap["calibration_count"] >= 2].sort_values(["calibration_count", "best_win_rate"], ascending=[False, False])
    lines.extend(["", "## Grupos que aparecem em mais de uma calibracao", ""])
    lines.extend(markdown_table(stable.head(80), ["symbol", "timeframe", "side", "calibrations", "rules", "best_win_rate"]))

    lines.extend(["", "## Top geral", ""])
    top = data.sort_values(["edge_score", "samples"], ascending=[False, False]).head(80)
    lines.extend(markdown_table(top, ["calibration", "symbol", "timeframe", "side", "feature", "bucket", "samples", "win_rate", "edge_score"]))

    lines.extend(["", "## Leitura recomendada", ""])
    lines.extend(
        [
            "- `tp100_sl100_lh100` tende a gerar muitos candidatos; bom para exploracao, mas ruim para virar gate direto.",
            "- `optimized_lh100` e mais seletivo; bom para validar ativos especificos, mas pode ficar concentrado demais.",
            "- `atr1.5_slatr1_lh100` e o melhor ponto de partida para calibracao geral porque respeita volatilidade por candle.",
            "- A proxima promocao deve ser somente para shadow/forward por ativo/timeframe/lado, nao para bloqueio global.",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    data = load_calibrations(Path(args.calibration_dir))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    write_report(output, data)
    print(f"Calibracoes: {data['calibration'].nunique() if not data.empty else 0}")
    print(f"Regras: {len(data)}")
    print(f"Saida: {output}")


if __name__ == "__main__":
    main()
