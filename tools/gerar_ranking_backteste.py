from __future__ import annotations

from pathlib import Path
import math

import pandas as pd


INPUT_CSV = "backteste_rapido_resumo.csv"
OUTPUT_CSV = "ranking_backteste_timeframes.csv"
OUTPUT_MD = "ranking_backteste_timeframes.md"

MIN_ENTRADAS = 500
TARGETS = [100, 200, 300, 400, 500]
TIMEFRAME_ORDER = ["M5", "M15", "M30", "H1"]


def round_up(value: float, step: int = 10, minimum: int = 50) -> int:
    if pd.isna(value):
        return minimum
    return max(minimum, int(math.ceil(value / step) * step))


def fmt_num(value: float, decimals: int = 2) -> str:
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_int(value: float) -> str:
    return f"{int(value):,}".replace(",", ".")


def choose_best_target(group: pd.DataFrame) -> pd.Series:
    candidates = group[group["entradas"] >= MIN_ENTRADAS].copy()
    if candidates.empty:
        candidates = group.copy()

    # Pontos esperados brutos: quanto o alvo paga ponderado pela taxa de acerto.
    # Penaliza levemente alvos com queda forte de win rate.
    candidates["score"] = (
        candidates["target"] * (candidates["win_rate"] / 100.0)
        - candidates["contra_media"] * (1.0 - candidates["win_rate"] / 100.0)
    )
    best = candidates.sort_values(
        ["score", "target", "win_rate", "entradas"],
        ascending=[False, False, False, False],
    ).iloc[0]
    return best


def classify_quality(row: pd.Series) -> str:
    if row["win_rate"] >= 90 and row["entradas"] >= 1000:
        return "forte"
    if row["win_rate"] >= 80 and row["entradas"] >= 1000:
        return "bom"
    if row["win_rate"] >= 70 and row["entradas"] >= 500:
        return "observacao"
    return "fraco/amostra baixa"


def build_ranking(df: pd.DataFrame) -> pd.DataFrame:
    best_rows = []
    for (symbol, timeframe), group in df.groupby(["symbol", "timeframe"], sort=False):
        best = choose_best_target(group)
        stop_base = float(best["contra_media"])
        best_rows.append(
            {
                "timeframe": timeframe,
                "symbol": symbol,
                "melhor_tp": int(best["target"]),
                "stop_sugerido": round_up(stop_base * 1.5),
                "stop_curto": round_up(stop_base * 1.25),
                "stop_folgado": round_up(stop_base * 2.0),
                "entradas": int(best["entradas"]),
                "wins": int(best["wins"]),
                "win_rate": float(best["win_rate"]),
                "favor_media": float(best["favor_media"]),
                "contra_media": float(best["contra_media"]),
                "favor_apos_voltar_media": float(best["favor_apos_voltar_media"]),
                "score": float(best["score"]),
            }
        )

    ranking = pd.DataFrame(best_rows)
    ranking["qualidade"] = ranking.apply(classify_quality, axis=1)
    ranking["amostra_ok"] = ranking["entradas"] >= MIN_ENTRADAS
    ranking["timeframe_rank"] = (
        ranking.sort_values(
            ["timeframe", "amostra_ok", "score", "win_rate", "entradas"],
            ascending=[True, False, False, False, False],
        )
        .groupby("timeframe")
        .cumcount()
        + 1
    )
    ranking["tf_order"] = ranking["timeframe"].map({tf: i for i, tf in enumerate(TIMEFRAME_ORDER)})
    ranking = ranking.sort_values(["tf_order", "timeframe_rank"]).drop(columns=["tf_order"])
    return ranking


def markdown_table(df: pd.DataFrame) -> str:
    headers = [
        "Rank",
        "Ativo",
        "TP",
        "Stop",
        "Stop curto",
        "Stop folgado",
        "Entradas",
        "Win rate",
        "Favor media",
        "Contra media",
        "Qualidade",
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in df.iterrows():
        lines.append(
            "| "
            + " | ".join(
                [
                    str(int(row["timeframe_rank"])),
                    str(row["symbol"]),
                    str(int(row["melhor_tp"])),
                    str(int(row["stop_sugerido"])),
                    str(int(row["stop_curto"])),
                    str(int(row["stop_folgado"])),
                    fmt_int(row["entradas"]),
                    f"{fmt_num(row['win_rate'])}%",
                    fmt_num(row["favor_media"]),
                    fmt_num(row["contra_media"]),
                    str(row["qualidade"]),
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def build_markdown(ranking: pd.DataFrame) -> str:
    lines = [
        "# Ranking Backteste Por Timeframe",
        "",
        "## Como Ler",
        "",
        "- `TP` e o melhor alvo entre 100, 200, 300, 400 e 500 pontos pelo score do backtest.",
        "- `Stop` e uma sugestao inicial baseada em 1,5x a media contra ate voltar.",
        "- `Stop curto` usa 1,25x a media contra; `Stop folgado` usa 2x.",
        "- Este stop ainda nao e um stop loss testado candle a candle; e uma recomendacao para a proxima rodada de teste com SL/TP real.",
        f"- Ranking exige preferencialmente pelo menos {MIN_ENTRADAS} entradas por ativo/timeframe/alvo.",
        "",
    ]

    for timeframe in TIMEFRAME_ORDER:
        tf_df = ranking[ranking["timeframe"] == timeframe].copy()
        if tf_df.empty:
            continue
        lines.extend(
            [
                f"## {timeframe}",
                "",
                markdown_table(tf_df),
                "",
            ]
        )

    return "\n".join(lines)


def main() -> None:
    root = Path(__file__).resolve().parent
    df = pd.read_csv(root / INPUT_CSV)
    df = df[df["target"].isin(TARGETS)].copy()

    ranking = build_ranking(df)
    ranking.to_csv(root / OUTPUT_CSV, index=False)
    (root / OUTPUT_MD).write_text(build_markdown(ranking), encoding="utf-8")

    print(f"Ranking salvo: {root / OUTPUT_MD}")
    print(f"CSV salvo: {root / OUTPUT_CSV}")


if __name__ == "__main__":
    main()
