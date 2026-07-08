from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

import pandas as pd

from fusion.strategy_bank import STRATEGY_BANK
from fusion.strategy_bank._factory import STRATEGY_ARCHETYPES, _build_strategy
from fusion.strategy_bank.executor import StrategySignal, evaluate_asset_bank, normalize_ohlcv


DEFAULT_REPORT_DIR = PROJECT_DIR / "reports" / "strategy_bank_backtests"


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_Sem dados._"
    cols = list(frame.columns)
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join(["---"] * len(cols)) + " |",
    ]
    for _, row in frame.iterrows():
        values = []
        for col in cols:
            value = row[col]
            if isinstance(value, float):
                values.append(f"{value:.4f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def load_frames(symbol: str, timeframes: list[str], parquet_dir: Path, years: int, tail: int) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    for timeframe in timeframes:
        path = parquet_dir / timeframe / f"{symbol}.parquet"
        if not path.exists() and symbol == "XAUUSD":
            for candidate in ("XAUUSD.parquet", "XAUUSD-F.parquet", "GOLD.parquet"):
                alt = parquet_dir / timeframe / candidate
                if alt.exists():
                    path = alt
                    break
        if not path.exists():
            continue
        frame = normalize_ohlcv(pd.read_parquet(path))
        if years > 0 and not frame.empty:
            cutoff = frame["date"].max() - pd.DateOffset(years=years)
            frame = frame[frame["date"] >= cutoff].reset_index(drop=True)
        if tail > 0:
            frame = frame.tail(tail).reset_index(drop=True)
        frame["timeframe"] = timeframe
        frames[timeframe] = frame
    return frames


def simulate_signal(signal: StrategySignal, frame: pd.DataFrame, max_bars: int) -> dict:
    df = frame.reset_index(drop=True)
    entry_idx = int(signal.metadata.get("row_index", -1))
    if entry_idx < 0 or entry_idx >= len(df):
        matches = df.index[df["date"] == signal.timestamp].tolist()
        if not matches:
            return {}
        entry_idx = int(matches[0])
    if entry_idx >= len(df):
        return {}
    end_idx = min(entry_idx + max_bars, len(df) - 1)
    result = "TIMEOUT"
    exit_price = float(df.iloc[end_idx]["close"])
    exit_time = df.iloc[end_idx]["date"]
    max_favorable = 0.0
    max_adverse = 0.0
    point = float(df.iloc[entry_idx].get("point_value", 0.0) or 0.0)
    if point <= 0:
        point = 0.01 if signal.asset == "XAUUSD" else 0.0001

    for idx in range(entry_idx, end_idx + 1):
        row = df.iloc[idx]
        if signal.side == "BUY":
            favorable = float(row["high"]) - signal.entry_price
            adverse = signal.entry_price - float(row["low"])
            hit_tp = float(row["high"]) >= signal.tp_price
            hit_sl = float(row["low"]) <= signal.sl_price
        else:
            favorable = signal.entry_price - float(row["low"])
            adverse = float(row["high"]) - signal.entry_price
            hit_tp = float(row["low"]) <= signal.tp_price
            hit_sl = float(row["high"]) >= signal.sl_price
        max_favorable = max(max_favorable, favorable)
        max_adverse = max(max_adverse, adverse)
        if hit_sl and hit_tp:
            result = "BOTH_TOUCHED_SL_FIRST"
            exit_price = signal.sl_price
            exit_time = row["date"]
            break
        if hit_tp:
            result = "WIN"
            exit_price = signal.tp_price
            exit_time = row["date"]
            break
        if hit_sl:
            result = "LOSS"
            exit_price = signal.sl_price
            exit_time = row["date"]
            break

    pnl_points = (exit_price - signal.entry_price) / point if signal.side == "BUY" else (signal.entry_price - exit_price) / point
    return {
        "asset": signal.asset,
        "strategy_id": signal.strategy_id,
        "setup": signal.setup,
        "timeframe": signal.timeframe,
        "timestamp": signal.timestamp,
        "side": signal.side,
        "entry_price": signal.entry_price,
        "tp_price": signal.tp_price,
        "sl_price": signal.sl_price,
        "exit_time": exit_time,
        "exit_price": exit_price,
        "result": result,
        "pnl_points": pnl_points,
        "max_favorable_price": max_favorable,
        "max_adverse_price": max_adverse,
        "reason": signal.reason,
    }


def bank_for_symbol(symbol: str, all_strategies: bool) -> dict:
    bank = STRATEGY_BANK[symbol]
    if not all_strategies:
        return bank
    profile = {
        "fingerprint": f"Full archetype sweep for {symbol}",
        "avoid": (),
    }
    return {
        **bank,
        "strategy_count": len(STRATEGY_ARCHETYPES),
        "strategies": [_build_strategy(symbol, strategy_id, profile) for strategy_id in STRATEGY_ARCHETYPES],
    }


def backtest_symbol(symbol: str, parquet_dir: Path, years: int, tail: int, max_bars: int, all_strategies: bool = False) -> pd.DataFrame:
    bank = bank_for_symbol(symbol, all_strategies)
    needed_timeframes = sorted({tf for strategy in bank["strategies"] for tf in strategy["timeframes"]})
    frames = load_frames(symbol, needed_timeframes, parquet_dir, years, tail)
    signals = evaluate_asset_bank(bank, frames)
    rows = []
    for signal in signals:
        frame = frames.get(signal.timeframe)
        if frame is None:
            continue
        row = simulate_signal(signal, frame, max_bars)
        if row:
            rows.append(row)
    return pd.DataFrame(rows)


def summarize(results: pd.DataFrame) -> pd.DataFrame:
    if results.empty:
        return pd.DataFrame()
    return (
        results.groupby(["asset", "strategy_id", "timeframe"], dropna=False)
        .agg(
            trades=("result", "size"),
            wins=("result", lambda s: int((s == "WIN").sum())),
            losses=("result", lambda s: int((s == "LOSS").sum())),
            win_rate=("result", lambda s: float((s == "WIN").mean() * 100)),
            pnl_points=("pnl_points", "sum"),
            avg_pnl_points=("pnl_points", "mean"),
        )
        .reset_index()
        .sort_values(["win_rate", "trades", "pnl_points"], ascending=[False, False, False])
    )


def build_markdown_report(results: pd.DataFrame, summary: pd.DataFrame, path: Path, symbols: list[str], years: int, max_bars: int) -> None:
    lines = [
        "# Relatorio Backtest Strategy Bank",
        "",
        "## Configuracao",
        "",
        f"- Ativos: {', '.join(symbols)}",
        f"- Periodo: ultimos {years} ano(s) do historico disponivel" if years > 0 else "- Periodo: historico completo disponivel",
        f"- Janela maxima por trade: {max_bars} candles",
        "- Sinais: setups tecnicos do banco de estrategias",
        "- Confirmacao de modelo: nao aplicada neste relatorio",
        "",
    ]

    if results.empty or summary.empty:
        lines.extend(["## Resultado", "", "Nenhum trade gerado."])
        path.write_text("\n".join(lines), encoding="utf-8")
        return

    total = len(results)
    wins = int((results["result"] == "WIN").sum())
    losses = int((results["result"] == "LOSS").sum())
    timeouts = int((results["result"] == "TIMEOUT").sum())
    pnl = float(results["pnl_points"].sum())
    win_rate = wins / total * 100 if total else 0.0

    lines.extend(
        [
            "## Resumo Geral",
            "",
            f"- Trades: {total}",
            f"- Wins: {wins}",
            f"- Losses: {losses}",
            f"- Timeouts: {timeouts}",
            f"- Win rate: {win_rate:.2f}%",
            f"- PnL total: {pnl:.2f} pontos",
            f"- PnL medio/trade: {float(results['pnl_points'].mean()):.2f} pontos",
            "",
            "## Top 30 Combinacoes",
            "",
            markdown_table(summary.head(30)),
            "",
            "## Piores 30 Combinacoes",
            "",
            markdown_table(summary.tail(30).sort_values(["pnl_points", "win_rate"], ascending=[True, True])),
            "",
            "## Melhor Combinacao Por Ativo",
            "",
        ]
    )

    best_rows = []
    for asset, group in summary.groupby("asset", sort=True):
        candidates = group[group["trades"] >= 10].copy()
        if candidates.empty:
            candidates = group.copy()
        best_rows.append(candidates.sort_values(["pnl_points", "win_rate", "trades"], ascending=[False, False, False]).iloc[0])
    best_by_asset = pd.DataFrame(best_rows).sort_values(["pnl_points", "win_rate"], ascending=[False, False])
    lines.extend([markdown_table(best_by_asset), ""])

    lines.extend(["## Resumo Por Ativo", ""])
    by_asset = (
        results.groupby("asset")
        .agg(
            trades=("result", "size"),
            wins=("result", lambda s: int((s == "WIN").sum())),
            losses=("result", lambda s: int((s == "LOSS").sum())),
            timeouts=("result", lambda s: int((s == "TIMEOUT").sum())),
            pnl_points=("pnl_points", "sum"),
            avg_pnl_points=("pnl_points", "mean"),
        )
        .reset_index()
    )
    by_asset["win_rate"] = by_asset["wins"] / by_asset["trades"] * 100
    by_asset = by_asset.sort_values(["pnl_points", "win_rate"], ascending=[False, False])
    lines.extend([markdown_table(by_asset), ""])

    lines.extend(
        [
            "## Observacao",
            "",
            "Este relatorio testa apenas a logica tecnica das estrategias. A etapa seguinte e aplicar a confirmacao dos modelos por ativo/timeframe para reduzir sinais ruins.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backtest operacional do banco de estrategias por ativo.")
    parser.add_argument("--symbols", nargs="+", default=["EURCAD", "AUDSGD", "XAUUSD"])
    parser.add_argument("--years", type=int, default=2)
    parser.add_argument("--tail", type=int, default=0, help="Limita candles por timeframe; 0 usa tudo do periodo.")
    parser.add_argument("--max-bars", type=int, default=80, help="Janela maxima para TP/SL apos sinal.")
    parser.add_argument("--parquet-dir", default=str(PROJECT_DIR / "data" / "parquet"))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--all-strategies", action="store_true", help="Testa todos os arquetipos no ativo, ignorando a cesta selecionada.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    parquet_dir = Path(args.parquet_dir)
    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    requested_symbols = [item.upper() for item in args.symbols]
    symbols = sorted(STRATEGY_BANK) if "ALL" in requested_symbols else requested_symbols

    frames = []
    for symbol in symbols:
        if symbol not in STRATEGY_BANK:
            print(f"[SKIP] {symbol}: sem banco de estrategias", flush=True)
            continue
        print(f"[RUN] {symbol}", flush=True)
        result = backtest_symbol(symbol, parquet_dir, args.years, args.tail, args.max_bars, args.all_strategies)
        if result.empty:
            print(f"[EMPTY] {symbol}: nenhum sinal operacional", flush=True)
            continue
        frames.append(result)

    all_results = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    summary = summarize(all_results)
    results_path = report_dir / "strategy_bank_backtest_trades.csv"
    summary_path = report_dir / "strategy_bank_backtest_summary.csv"
    markdown_path = report_dir / "strategy_bank_backtest_report.md"
    all_results.to_csv(results_path, index=False)
    summary.to_csv(summary_path, index=False)
    build_markdown_report(all_results, summary, markdown_path, symbols, args.years, args.max_bars)
    print(f"Trades: {len(all_results)}")
    print(f"Resumo: {summary_path}")
    print(f"Detalhado: {results_path}")
    print(f"Relatorio: {markdown_path}")
    if not summary.empty:
        print(summary.head(20).to_string(index=False))


if __name__ == "__main__":
    main()
