from __future__ import annotations

from pathlib import Path

import backteste_rapido as bt


def main() -> None:
    root = Path(__file__).resolve().parent
    cache_root = root / bt.CACHE_DIR
    years = bt.BACKTEST_YEARS

    summaries = []
    missing = []

    for symbol in bt.SYMBOLS:
        for timeframe in bt.TIMEFRAMES:
            key = bt.cache_key(symbol, timeframe, years)
            summary = bt.load_summary_cache(cache_root, key)
            if summary is None:
                missing.append(f"{symbol} {timeframe}")
                continue
            summaries.append(summary)

    if not summaries:
        raise SystemExit("Nenhum cache encontrado para gerar relatorios.")

    bt.generate_report_from_summaries(
        summaries,
        root / bt.REPORT_MD,
        root / bt.SUMMARY_CSV,
        root / bt.DYNAMICS_CSV,
        root / bt.DETAILED_CSV,
        bt.SYMBOLS,
        bt.TIMEFRAMES,
        years,
    )

    print(f"Relatorios gerados do cache: {len(summaries)} combinacoes")
    print(f"Relatorio geral: {root / bt.REPORT_MD}")
    print(f"Resumo por ativo: {root / bt.SYMBOL_SUMMARY_CSV}")
    print(f"Dinamica geral: {root / bt.DYNAMICS_CSV}")
    print(f"Relatorios por ativo: {root / bt.REPORTS_DIR}")
    if missing:
        print("\nCaches ausentes:")
        for item in missing:
            print(f"- {item}")


if __name__ == "__main__":
    main()
