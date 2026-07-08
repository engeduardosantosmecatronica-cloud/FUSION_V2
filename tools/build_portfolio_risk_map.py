from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fusion.features.macro_flow import split_forex_symbol


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera mapa de risco de portfolio usando matriz de correlacao.")
    parser.add_argument("--matrix", default="reports/correlation/correlation_matrix_H1.json")
    parser.add_argument("--positions", default="", help="JSON opcional com posicoes abertas/simuladas.")
    parser.add_argument("--output-dir", default="reports/portfolio_risk")
    parser.add_argument("--threshold", type=float, default=0.70)
    return parser.parse_args()


def load_matrix(path: Path) -> tuple[dict[str, dict[str, float]], dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw = payload.get("correlations", payload)
    matrix = {
        str(symbol).upper(): {str(other).upper(): float(value) for other, value in row.items()}
        for symbol, row in raw.items()
        if isinstance(row, dict)
    }
    return matrix, payload


def correlation_value(matrix: dict[str, dict[str, float]], a: str, b: str) -> float | None:
    a = a.upper()
    b = b.upper()
    if a == b:
        return 1.0
    value = matrix.get(a, {}).get(b)
    if value is None:
        value = matrix.get(b, {}).get(a)
    return None if value is None else float(value)


def strong_pairs(matrix: dict[str, dict[str, float]], threshold: float) -> pd.DataFrame:
    rows = []
    symbols = sorted(matrix)
    for i, a in enumerate(symbols):
        for b in symbols[i + 1 :]:
            corr = correlation_value(matrix, a, b)
            if corr is None or abs(corr) < threshold:
                continue
            rows.append(
                {
                    "symbol_a": a,
                    "symbol_b": b,
                    "correlation": corr,
                    "abs_correlation": abs(corr),
                    "risk_same_direction": corr > 0,
                    "risk_opposite_direction": corr < 0,
                }
            )
    frame = pd.DataFrame(rows)
    return frame.sort_values("abs_correlation", ascending=False) if not frame.empty else frame


def symbol_clusters(pairs: pd.DataFrame) -> pd.DataFrame:
    if pairs.empty:
        return pd.DataFrame()
    rows = []
    symbols = sorted(set(pairs["symbol_a"]).union(set(pairs["symbol_b"])))
    for symbol in symbols:
        related = pairs[(pairs["symbol_a"] == symbol) | (pairs["symbol_b"] == symbol)].copy()
        related["other"] = related.apply(lambda row: row["symbol_b"] if row["symbol_a"] == symbol else row["symbol_a"], axis=1)
        rows.append(
            {
                "symbol": symbol,
                "strong_links": int(len(related)),
                "avg_abs_corr": float(related["abs_correlation"].mean()),
                "max_abs_corr": float(related["abs_correlation"].max()),
                "top_related": ", ".join(
                    f"{row.other}:{row.correlation:.2f}" for row in related.sort_values("abs_correlation", ascending=False).head(8).itertuples()
                ),
            }
        )
    return pd.DataFrame(rows).sort_values(["strong_links", "max_abs_corr"], ascending=[False, False])


def load_positions(path: str) -> list[dict[str, Any]]:
    if not path:
        return []
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = payload.get("positions", [])
    return payload if isinstance(payload, list) else []


def position_direction(position: dict[str, Any]) -> int:
    direction = str(position.get("direction", "") or "").upper()
    if direction == "BUY":
        return 1
    if direction == "SELL":
        return -1
    return 0


def pair_legs(symbol: str) -> tuple[str, str] | None:
    symbol = str(symbol or "").upper()
    if symbol in {"GOLD", "XAUUSD"}:
        return ("XAU", "USD")
    return split_forex_symbol(symbol)


def currency_exposure(positions: list[dict[str, Any]]) -> pd.DataFrame:
    exposures: dict[str, float] = {}
    for position in positions:
        symbol = str(position.get("symbol", "") or "").upper()
        legs = pair_legs(symbol)
        direction = position_direction(position)
        if not legs or direction == 0:
            continue
        units = max(0.01, float(position.get("volume", 0.01) or 0.01) / 0.01)
        base, quote = legs
        exposures[base] = exposures.get(base, 0.0) + direction * units
        exposures[quote] = exposures.get(quote, 0.0) - direction * units
    frame = pd.DataFrame([{"currency": k, "exposure_units": v, "abs_exposure": abs(v)} for k, v in exposures.items()])
    return frame.sort_values("abs_exposure", ascending=False) if not frame.empty else frame


def correlated_position_risk(positions: list[dict[str, Any]], matrix: dict[str, dict[str, float]], threshold: float) -> pd.DataFrame:
    rows = []
    for i, pos_a in enumerate(positions):
        for pos_b in positions[i + 1 :]:
            a = str(pos_a.get("symbol", "") or "").upper()
            b = str(pos_b.get("symbol", "") or "").upper()
            corr = correlation_value(matrix, a, b)
            if corr is None or abs(corr) < threshold:
                continue
            dir_a = position_direction(pos_a)
            dir_b = position_direction(pos_b)
            pnl_similarity = corr * dir_a * dir_b
            rows.append(
                {
                    "symbol_a": a,
                    "direction_a": "BUY" if dir_a == 1 else "SELL" if dir_a == -1 else "NEUTRAL",
                    "profit_a": float(pos_a.get("profit", 0.0) or 0.0),
                    "symbol_b": b,
                    "direction_b": "BUY" if dir_b == 1 else "SELL" if dir_b == -1 else "NEUTRAL",
                    "profit_b": float(pos_b.get("profit", 0.0) or 0.0),
                    "correlation": corr,
                    "pnl_similarity": pnl_similarity,
                    "risk_stack": pnl_similarity > 0,
                }
            )
    frame = pd.DataFrame(rows)
    return frame.sort_values("pnl_similarity", ascending=False) if not frame.empty else frame


def write_report(path: Path, pairs: pd.DataFrame, clusters: pd.DataFrame, exposure: pd.DataFrame, pos_risk: pd.DataFrame, meta: dict[str, Any]) -> None:
    lines = ["# Portfolio Risk Map", ""]
    lines.append(f"- Matriz timeframe: {meta.get('timeframe', 'unknown')}")
    lines.append(f"- Ativos na matriz: {len(meta.get('symbols', []))}")
    lines.append(f"- Pares fortes: {0 if pairs.empty else len(pairs)}")
    lines.append("")
    lines.append("## Ativos Com Mais Conexoes")
    lines.append("")
    if clusters.empty:
        lines.append("_Sem clusters fortes._")
    else:
        lines.append("| symbol | links | avg_abs_corr | max_abs_corr | top_related |")
        lines.append("| --- | ---: | ---: | ---: | --- |")
        for row in clusters.head(20).itertuples(index=False):
            lines.append(f"| {row.symbol} | {row.strong_links} | {row.avg_abs_corr:.3f} | {row.max_abs_corr:.3f} | {row.top_related} |")
    lines.append("")
    lines.append("## Exposicao Por Moeda")
    lines.append("")
    if exposure.empty:
        lines.append("_Nenhuma posicao informada._")
    else:
        lines.append("| currency | exposure_units |")
        lines.append("| --- | ---: |")
        for row in exposure.itertuples(index=False):
            lines.append(f"| {row.currency} | {row.exposure_units:.2f} |")
    lines.append("")
    lines.append("## Risco Entre Posicoes")
    lines.append("")
    if pos_risk.empty:
        lines.append("_Nenhum risco correlacionado entre posicoes informado/encontrado._")
    else:
        lines.append("| A | dir | B | dir | corr | pnl_similarity | risk_stack |")
        lines.append("| --- | --- | --- | --- | ---: | ---: | --- |")
        for row in pos_risk.head(40).itertuples(index=False):
            lines.append(
                f"| {row.symbol_a} | {row.direction_a} | {row.symbol_b} | {row.direction_b} | "
                f"{row.correlation:.3f} | {row.pnl_similarity:.3f} | {row.risk_stack} |"
            )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    matrix, meta = load_matrix(Path(args.matrix))
    pairs = strong_pairs(matrix, args.threshold)
    clusters = symbol_clusters(pairs)
    positions = load_positions(args.positions)
    exposure = currency_exposure(positions)
    pos_risk = correlated_position_risk(positions, matrix, args.threshold)

    pairs.to_csv(output_dir / "strong_correlation_pairs.csv", index=False)
    clusters.to_csv(output_dir / "correlation_clusters.csv", index=False)
    exposure.to_csv(output_dir / "currency_exposure.csv", index=False)
    pos_risk.to_csv(output_dir / "position_correlation_risk.csv", index=False)
    write_report(output_dir / "portfolio_risk_map.md", pairs, clusters, exposure, pos_risk, meta)
    print(f"Pares fortes: {0 if pairs.empty else len(pairs)}")
    print(f"Saida: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
