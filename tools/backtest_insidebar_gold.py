from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1] if Path(__file__).resolve().parent.name == "tools" else Path(__file__).resolve().parent
REPORT_DIR = PROJECT_DIR / "reports" / "insidebar_gold"
SYMBOL = "XAUUSD"
TIMEFRAMES = ["M5", "M15", "M30"]
MAX_LOOKAHEAD = 1000
TRAILING_ACTIVATION_POINTS = 1100
TRAILING_DISTANCE_POINTS = 600


def fmt_num(value: float) -> str:
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(value: float) -> str:
    return f"{value:.2f}%".replace(".", ",")


def load_data(tf: str) -> pd.DataFrame:
    files = sorted((PROJECT_DIR / "data" / "csv" / tf).glob(f"*/*/{SYMBOL}.csv"))
    if not files:
        return pd.DataFrame()
    parts = []
    for file_path in files:
        df = pd.read_csv(file_path)
        parts.append(df)
    df = pd.concat(parts, ignore_index=True).drop_duplicates("date")
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    for col in ["open", "high", "low", "close", "point_value"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna(subset=["date", "open", "high", "low", "close"])


def candle_type(row) -> str:
    if row["close"] > row["open"]:
        return "alta"
    if row["close"] < row["open"]:
        return "baixa"
    return "doji"


def simulate_trade(df: pd.DataFrame, start_idx: int, direction: str, entry: float, point: float) -> dict:
    exit_reason = "SEM_SAIDA"
    end_idx = min(len(df), start_idx + MAX_LOOKAHEAD)
    highs = df["_high"].values[start_idx:end_idx]
    lows = df["_low"].values[start_idx:end_idx]

    if direction == "BUY":
        favor_arr = np.maximum(0.0, (highs - entry) / point)
        against_arr = np.maximum(0.0, (entry - lows) / point)
    else:
        favor_arr = np.maximum(0.0, (entry - lows) / point)
        against_arr = np.maximum(0.0, (highs - entry) / point)

    max_favor = float(favor_arr.max()) if len(favor_arr) else 0.0
    max_against = float(against_arr.max()) if len(against_arr) else 0.0

    trailing_active = False
    trailing_stop = None
    best_price = entry
    exit_points = 0.0
    candles_to_exit = len(highs)

    for offset, (high, low) in enumerate(zip(highs, lows)):
        if direction == "BUY":
            best_price = max(best_price, float(high))
            favor_points = (best_price - entry) / point
            if favor_points >= TRAILING_ACTIVATION_POINTS:
                trailing_active = True
                trailing_stop = best_price - (TRAILING_DISTANCE_POINTS * point)
            if trailing_active and float(low) <= trailing_stop:
                exit_reason = "TRAILING"
                candles_to_exit = offset + 1
                exit_points = (trailing_stop - entry) / point
                break
        else:
            best_price = min(best_price, float(low))
            favor_points = (entry - best_price) / point
            if favor_points >= TRAILING_ACTIVATION_POINTS:
                trailing_active = True
                trailing_stop = best_price + (TRAILING_DISTANCE_POINTS * point)
            if trailing_active and float(high) >= trailing_stop:
                exit_reason = "TRAILING"
                candles_to_exit = offset + 1
                exit_points = (entry - trailing_stop) / point
                break

    if exit_reason == "SEM_SAIDA":
        if direction == "BUY" and len(highs):
            exit_points = (df["_close"].values[end_idx - 1] - entry) / point
        elif direction == "SELL" and len(lows):
            exit_points = (entry - df["_close"].values[end_idx - 1]) / point

    result = "WIN" if exit_points > 0 else "LOSS" if exit_points < 0 else "FLAT"
    if exit_reason == "SEM_SAIDA":
        exit_reason = "JANELA_MAXIMA"
    else:
        result = "WIN" if exit_points > 0 else "LOSS"

    return {
        "trailing_activation_points": TRAILING_ACTIVATION_POINTS,
        "trailing_distance_points": TRAILING_DISTANCE_POINTS,
        "result": result,
        "exit_reason": exit_reason,
        "exit_points": exit_points,
        "candles_to_exit": candles_to_exit,
        "max_favor_points": max_favor,
        "max_against_points": max_against,
    }


def backtest_timeframe(tf: str) -> pd.DataFrame:
    df = load_data(tf)
    if df.empty:
        return pd.DataFrame()

    point = float(df["point_value"].dropna().iloc[0]) if "point_value" in df.columns else 0.01
    df["_high"] = df["high"].astype(float)
    df["_low"] = df["low"].astype(float)
    df["_close"] = df["close"].astype(float)
    rows = []
    for i in range(1, len(df) - 2):
        mother = df.iloc[i - 1]
        inside = df.iloc[i]
        is_inside = inside["high"] < mother["high"] and inside["low"] > mother["low"]
        if not is_inside:
            continue

        for j in range(i + 1, min(len(df), i + 1 + MAX_LOOKAHEAD)):
            row = df.iloc[j]
            buy_break = row["high"] >= inside["high"]
            sell_break = row["low"] <= inside["low"]
            if not buy_break and not sell_break:
                continue

            if buy_break and sell_break:
                direction = "AMBIGUO"
                entry = None
                stop = None
            elif buy_break:
                direction = "BUY"
                entry = float(inside["high"])
            else:
                direction = "SELL"
                entry = float(inside["low"])

            if direction == "AMBIGUO":
                break

            base = {
                "symbol": SYMBOL,
                "timeframe": tf,
                "inside_time": inside["date"],
                "entry_time": row["date"],
                "direction": direction,
                "mother_candle": candle_type(mother),
                "inside_candle": candle_type(inside),
                "mother_range_points": (mother["high"] - mother["low"]) / point,
                "inside_range_points": (inside["high"] - inside["low"]) / point,
                "entry_price": entry,
            }
            result = simulate_trade(df, j, direction, entry, point)
            rows.append({**base, **result})
            break

    return pd.DataFrame(rows)


def summarize(results: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if results.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    grouped = results.groupby(["symbol", "timeframe"])
    summary = grouped.agg(
        trades=("result", "size"),
        wins=("result", lambda x: int((x == "WIN").sum())),
        losses=("result", lambda x: int((x == "LOSS").sum())),
        flats=("result", lambda x: int((x == "FLAT").sum())),
        avg_exit_points=("exit_points", "mean"),
        avg_favor_points=("max_favor_points", "mean"),
        avg_against_points=("max_against_points", "mean"),
        avg_candles_to_exit=("candles_to_exit", "mean"),
    ).reset_index()
    summary["win_rate"] = summary["wins"] / summary["trades"] * 100

    by_direction = results.groupby(["timeframe", "direction"]).agg(
        trades=("result", "size"),
        wins=("result", lambda x: int((x == "WIN").sum())),
        losses=("result", lambda x: int((x == "LOSS").sum())),
        avg_exit_points=("exit_points", "mean"),
        avg_favor_points=("max_favor_points", "mean"),
        avg_against_points=("max_against_points", "mean"),
    ).reset_index()
    by_direction["win_rate"] = by_direction["wins"] / by_direction["trades"] * 100

    by_pattern = results.groupby(["timeframe", "direction", "mother_candle", "inside_candle"]).agg(
        trades=("result", "size"),
        wins=("result", lambda x: int((x == "WIN").sum())),
        avg_exit_points=("exit_points", "mean"),
        avg_favor_points=("max_favor_points", "mean"),
        avg_against_points=("max_against_points", "mean"),
    ).reset_index()
    by_pattern["win_rate"] = by_pattern["wins"] / by_pattern["trades"] * 100
    by_pattern = by_pattern.sort_values(["win_rate", "trades"], ascending=[False, False])
    return summary, by_direction, by_pattern


def table_md(df: pd.DataFrame, columns: list[str], labels: list[str]) -> str:
    lines = ["| " + " | ".join(labels) + " |", "| " + " | ".join(["---"] * len(labels)) + " |"]
    for _, row in df.iterrows():
        vals = []
        for col in columns:
            value = row[col]
            if isinstance(value, float):
                vals.append(fmt_pct(value) if col == "win_rate" else fmt_num(value))
            else:
                vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def write_report(results: pd.DataFrame, summary: pd.DataFrame, by_direction: pd.DataFrame, by_pattern: pd.DataFrame):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / "relatorio_insidebar_gold.md"
    lines = [
        "# Relatorio Inside Bar - Gold",
        "",
        "## Configuracao",
        "",
        f"- Ativo historico/modelo: {SYMBOL}",
        "- Ativo corretora: GOLD",
        f"- Timeframes: {', '.join(TIMEFRAMES)}",
        "- Entrada BUY: rompimento da maxima da inside bar",
        "- Entrada SELL: rompimento da minima da inside bar",
        "- Sem SL e sem TP fixo",
        f"- Saida: trailing stop com ativacao em {TRAILING_ACTIVATION_POINTS} pontos e distancia de {TRAILING_DISTANCE_POINTS} pontos",
        f"- Janela maxima: {MAX_LOOKAHEAD} candles",
        "",
    ]

    if results.empty:
        lines.append("Nenhuma inside bar encontrada.")
    else:
        lines.extend([
            "## Resumo Por Timeframe",
            "",
            table_md(
                summary,
                ["timeframe", "trades", "wins", "losses", "flats", "win_rate", "avg_exit_points", "avg_favor_points", "avg_against_points", "avg_candles_to_exit"],
                ["TF", "Trades", "Wins", "Losses", "Flats", "Win rate", "Media resultado", "Media a favor", "Media contra", "Candles ate saida"],
            ),
            "",
            "## Resultado Por Direcao",
            "",
            table_md(
                by_direction,
                ["timeframe", "direction", "trades", "wins", "losses", "win_rate", "avg_exit_points", "avg_favor_points", "avg_against_points"],
                ["TF", "Direcao", "Trades", "Wins", "Losses", "Win rate", "Media resultado", "Media a favor", "Media contra"],
            ),
            "",
            "## Melhores Padroes",
            "",
            table_md(
                by_pattern.head(30),
                ["timeframe", "direction", "mother_candle", "inside_candle", "trades", "wins", "win_rate", "avg_exit_points", "avg_favor_points", "avg_against_points"],
                ["TF", "Direcao", "Candle mae", "Inside", "Trades", "Wins", "Win rate", "Media resultado", "Media a favor", "Media contra"],
            ),
        ])

    lines.extend([
        "",
        "## Arquivos Gerados",
        "",
        "- Relatorio: `relatorio_insidebar_gold.md`",
        "- Resumo CSV: `insidebar_gold_resumo.csv`",
        "- Direcao CSV: `insidebar_gold_direcao.csv`",
        "- Padroes CSV: `insidebar_gold_padroes.csv`",
        "- Trades CSV: `insidebar_gold_trades.csv`",
    ])
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    all_results = []
    for tf in TIMEFRAMES:
        print(f"Backtest {SYMBOL} {tf}...")
        result = backtest_timeframe(tf)
        print(f"  simulacoes: {len(result)}")
        all_results.append(result)

    results = pd.concat(all_results, ignore_index=True) if all_results else pd.DataFrame()
    summary, by_direction, by_pattern = summarize(results)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(REPORT_DIR / "insidebar_gold_trades.csv", index=False)
    summary.to_csv(REPORT_DIR / "insidebar_gold_resumo.csv", index=False)
    by_direction.to_csv(REPORT_DIR / "insidebar_gold_direcao.csv", index=False)
    by_pattern.to_csv(REPORT_DIR / "insidebar_gold_padroes.csv", index=False)
    write_report(results, summary, by_direction, by_pattern)
    print("Relatorio gerado: relatorio_insidebar_gold.md")


if __name__ == "__main__":
    main()
