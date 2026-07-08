from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Calcula matriz de correlacao entre ativos para filtro de carteira.")
    parser.add_argument("--config", default="config/fusion_config.yaml")
    parser.add_argument("--parquet-dir", default="data/parquet")
    parser.add_argument("--output-dir", default="reports/correlation")
    parser.add_argument("--timeframe", default="H1")
    parser.add_argument("--tail", type=int, default=5000)
    parser.add_argument("--min-bars", type=int, default=500)
    parser.add_argument("--threshold", type=float, default=0.70)
    parser.add_argument("--symbols", nargs="*", default=[])
    return parser.parse_args()


def configured_symbols(config_path: Path) -> list[str]:
    if not config_path.exists():
        return []
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return [str(item).upper() for item in payload.get("symbols", []) or []]


def load_close(path: Path, tail: int) -> pd.Series:
    if not path.exists():
        return pd.Series(dtype=float)
    frame = pd.read_parquet(path)
    if "time" in frame.columns:
        time_col = "time"
    elif "date" in frame.columns:
        time_col = "date"
    else:
        return pd.Series(dtype=float)
    if "close" not in frame.columns:
        return pd.Series(dtype=float)
    frame = frame[[time_col, "close"]].copy()
    frame[time_col] = pd.to_datetime(frame[time_col], errors="coerce")
    frame = frame.dropna(subset=[time_col, "close"]).sort_values(time_col).tail(tail)
    return pd.Series(frame["close"].astype(float).to_numpy(), index=frame[time_col], name=path.stem)


def build_returns(parquet_dir: Path, timeframe: str, symbols: list[str], tail: int, min_bars: int) -> pd.DataFrame:
    series = {}
    tf_dir = parquet_dir / timeframe.upper()
    for symbol in symbols:
        close = load_close(tf_dir / f"{symbol}.parquet", tail)
        if len(close) < min_bars:
            continue
        returns = np.log(close / close.shift(1)).replace([np.inf, -np.inf], np.nan).dropna()
        if len(returns) >= min_bars:
            series[symbol] = returns
    if not series:
        return pd.DataFrame()
    return pd.concat(series.values(), axis=1, join="inner").dropna(how="any")


def pair_rows(corr: pd.DataFrame, threshold: float) -> pd.DataFrame:
    rows = []
    symbols = list(corr.columns)
    for i, symbol_a in enumerate(symbols):
        for symbol_b in symbols[i + 1 :]:
            value = float(corr.loc[symbol_a, symbol_b])
            if not np.isfinite(value):
                continue
            risk_cases = []
            if value >= threshold:
                risk_cases.append("BUY+BUY acumula risco se um estiver perdendo")
                risk_cases.append("SELL+SELL acumula risco se um estiver perdendo")
                favorable = "direcoes opostas tendem a hedge"
            elif value <= -threshold:
                risk_cases.append("BUY+SELL acumula risco se um estiver perdendo")
                risk_cases.append("SELL+BUY acumula risco se um estiver perdendo")
                favorable = "mesma direcao tende a hedge"
            else:
                favorable = "correlacao abaixo do limite"
            rows.append(
                {
                    "symbol_a": symbol_a,
                    "symbol_b": symbol_b,
                    "correlation": value,
                    "abs_correlation": abs(value),
                    "risk_cases": "; ".join(risk_cases) if risk_cases else "",
                    "favorable_case": favorable,
                }
            )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    return frame.sort_values("abs_correlation", ascending=False)


def write_report(path: Path, timeframe: str, returns: pd.DataFrame, pairs: pd.DataFrame, threshold: float) -> None:
    lines = ["# Asset Correlation Report", ""]
    lines.extend(
        [
            f"- Timeframe: {timeframe.upper()}",
            f"- Ativos calculados: {returns.shape[1]}",
            f"- Barras alinhadas: {returns.shape[0]}",
            f"- Threshold: {threshold:.2f}",
            "",
            "## Regra de risco",
            "",
            "- Correlacao positiva forte: mesma direcao empilha risco.",
            "- Correlacao negativa forte: direcoes opostas empilham risco.",
            "- O filtro bloqueia apenas quando a posicao correlacionada ja esta em prejuizo.",
            "",
            "## Pares fortes",
            "",
        ]
    )
    strong = pairs[pairs["abs_correlation"] >= threshold].head(80) if not pairs.empty else pd.DataFrame()
    if strong.empty:
        lines.append("_Nenhum par forte encontrado._")
    else:
        lines.append("| symbol_a | symbol_b | corr | risco | favoravel |")
        lines.append("| --- | --- | --- | --- | --- |")
        for row in strong.itertuples(index=False):
            lines.append(
                f"| {row.symbol_a} | {row.symbol_b} | {row.correlation:.4f} | "
                f"{row.risk_cases} | {row.favorable_case} |"
            )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    symbols = [item.upper() for item in args.symbols] or configured_symbols(Path(args.config))
    symbols = sorted(set(symbols))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    returns = build_returns(Path(args.parquet_dir), args.timeframe, symbols, args.tail, args.min_bars)
    if returns.empty:
        raise SystemExit("Sem dados suficientes para correlacao.")
    corr = returns.corr()
    pairs = pair_rows(corr, args.threshold)

    suffix = args.timeframe.upper()
    matrix_path = output_dir / f"correlation_matrix_{suffix}.json"
    corr.to_csv(output_dir / f"correlation_matrix_{suffix}.csv")
    pairs.to_csv(output_dir / f"correlation_pairs_{suffix}.csv", index=False)
    payload = {
        "timeframe": suffix,
        "tail": args.tail,
        "min_bars": args.min_bars,
        "aligned_bars": int(returns.shape[0]),
        "symbols": list(corr.columns),
        "threshold": args.threshold,
        "correlations": corr.round(6).to_dict(),
    }
    matrix_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(output_dir / f"correlation_report_{suffix}.md", suffix, returns, pairs, args.threshold)

    print(f"Ativos: {corr.shape[0]} | barras alinhadas: {returns.shape[0]}")
    print(f"Matriz: {matrix_path}")


if __name__ == "__main__":
    main()
