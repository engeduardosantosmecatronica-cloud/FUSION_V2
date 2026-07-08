from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analisa se sinais BUY/SELL parecem invertidos por ativo/timeframe/estrategia."
    )
    parser.add_argument("input_csv", help="CSV gerado por tools/analyze_signal_outcomes.py")
    parser.add_argument("--output-dir", default="reports/signal_outcomes")
    parser.add_argument("--horizon", default="h3", help="Horizonte: h1, h3, h6, h12 ou h24.")
    parser.add_argument("--min-samples", type=int, default=20)
    parser.add_argument("--group-by", default="symbol,timeframe,strategy", help="Colunas para agrupar.")
    parser.add_argument("--decision", default="", help="Filtra decisao, ex.: ALLOW ou BLOCK.")
    return parser.parse_args()


def bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return series.astype(str).str.lower().map({"true": True, "false": False})


def summarize(df: pd.DataFrame, group_cols: list[str], correct_col: str, min_samples: int) -> pd.DataFrame:
    rows: list[dict] = []
    valid = df[df["status"].astype(str) == "ok"].copy()
    valid[correct_col] = bool_series(valid[correct_col])
    valid = valid[valid[correct_col].isin([True, False])]

    for keys, group in valid.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        samples = len(group)
        if samples < min_samples:
            continue
        direct = float(group[correct_col].mean())
        inverted = 1.0 - direct
        verdict = "normal"
        if inverted >= 0.60 and inverted - direct >= 0.15:
            verdict = "provavel_inversao"
        elif direct < 0.45 and inverted > direct:
            verdict = "suspeito"
        elif direct >= 0.55:
            verdict = "direcao_ok"

        row = {col: key for col, key in zip(group_cols, keys)}
        row.update(
            {
                "samples": samples,
                "direct_accuracy": round(direct * 100.0, 2),
                "inverted_accuracy": round(inverted * 100.0, 2),
                "edge_inverted_minus_direct": round((inverted - direct) * 100.0, 2),
                "buy_count": int((group["side"].astype(str).str.upper() == "BUY").sum()),
                "sell_count": int((group["side"].astype(str).str.upper() == "SELL").sum()),
                "verdict": verdict,
            }
        )
        rows.append(row)
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values(["verdict", "edge_inverted_minus_direct", "samples"], ascending=[True, False, False])


def write_markdown(path: Path, summary: pd.DataFrame, horizon: str, group_cols: list[str]) -> None:
    lines = [
        "# Signal Inversion Check",
        "",
        f"- Horizonte analisado: {horizon.upper()}",
        f"- Agrupamento: {', '.join(group_cols)}",
        "",
    ]
    if summary.empty:
        lines.append("Nenhum grupo com amostras suficientes.")
        path.write_text("\n".join(lines), encoding="utf-8")
        return

    suspects = summary[summary["verdict"].isin(["provavel_inversao", "suspeito"])]
    ok = summary[summary["verdict"] == "direcao_ok"]

    lines.append(f"- Grupos analisados: {len(summary)}")
    lines.append(f"- Suspeitos/provavel inversao: {len(suspects)}")
    lines.append(f"- Direcao OK: {len(ok)}")
    lines.extend(["", "## Suspeitos", ""])
    if suspects.empty:
        lines.append("- Nenhum grupo forte indicando inversao.")
    else:
        for row in suspects.head(60).itertuples(index=False):
            group = " ".join(str(getattr(row, col)) for col in group_cols)
            lines.append(
                f"- {group} | amostras={row.samples} | direto={row.direct_accuracy:.2f}% | "
                f"invertido={row.inverted_accuracy:.2f}% | delta={row.edge_inverted_minus_direct:.2f}% | {row.verdict}"
            )

    lines.extend(["", "## Direcao OK", ""])
    if ok.empty:
        lines.append("- Nenhum grupo passou de 55% no sentido original.")
    else:
        for row in ok.sort_values("direct_accuracy", ascending=False).head(30).itertuples(index=False):
            group = " ".join(str(getattr(row, col)) for col in group_cols)
            lines.append(
                f"- {group} | amostras={row.samples} | direto={row.direct_accuracy:.2f}% | "
                f"invertido={row.inverted_accuracy:.2f}%"
            )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    input_path = Path(args.input_csv)
    if not input_path.is_absolute():
        input_path = ROOT / input_path
    horizon = args.horizon.lower().strip()
    correct_col = f"{horizon}_correct"
    df = pd.read_csv(input_path)
    if args.decision:
        df = df[df["decision"].astype(str).str.upper() == args.decision.upper()]
    if correct_col not in df.columns:
        raise SystemExit(f"Coluna nao encontrada: {correct_col}")

    group_cols = [item.strip() for item in args.group_by.split(",") if item.strip()]
    missing = [col for col in group_cols if col not in df.columns]
    if missing:
        raise SystemExit(f"Colunas de agrupamento ausentes: {missing}")

    summary = summarize(df, group_cols, correct_col, args.min_samples)
    output_dir = ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = input_path.stem.replace("signal_outcomes_", "")
    if args.decision:
        stem += f"_{args.decision.upper()}"
    suffix = "_".join(group_cols)
    csv_path = output_dir / f"signal_inversion_{stem}_{horizon}_{suffix}.csv"
    md_path = output_dir / f"signal_inversion_{stem}_{horizon}_{suffix}.md"
    summary.to_csv(csv_path, index=False)
    write_markdown(md_path, summary, horizon, group_cols)
    print(f"Entrada: {input_path}")
    print(f"Grupos: {len(summary)}")
    print(f"CSV: {csv_path}")
    print(f"Resumo: {md_path}")


if __name__ == "__main__":
    main()
