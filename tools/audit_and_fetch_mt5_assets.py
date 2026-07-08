from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


PROJECT_DIR = Path(__file__).resolve().parents[1]
TIMEFRAMES = ["M5", "M15", "M30", "H1", "H4", "D1"]


ALIASES: dict[str, list[str]] = {
    "GOLD": ["GOLD", "XAUUSD"],
    "SILVER": ["SILVER", "XAGUSD"],
    "DOGUSD": ["DOGUSD", "DOGEUSD"],
    "US100CASH": ["US100CASH", "NAS100CASH", "NAS100", "US100"],
    "US30CASH": ["US30CASH", "US30"],
    "US500CASH": ["US500CASH", "US500", "SPX500"],
    "GER40CASH": ["GER40CASH", "GER40", "DE40"],
    "JP225CASH": ["JP225CASH", "JPN225", "JP225"],
    "AUS200CASH": ["AUS200CASH", "AUS200"],
}


def canonical(raw: str) -> str:
    return "".join(ch for ch in raw.upper() if ch.isalnum())


def load_config() -> dict[str, Any]:
    return yaml.safe_load((PROJECT_DIR / "config" / "fusion_config.yaml").read_text(encoding="utf-8"))


def mt5_timeframes(mt5: Any) -> dict[str, int]:
    return {
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
    }


def discover_broker_symbols(mt5: Any) -> dict[str, str]:
    symbols = mt5.symbols_get() or []
    mapping: dict[str, str] = {}
    for symbol in symbols:
        name = str(symbol.name)
        mapping[canonical(name)] = name
    return mapping


def resolve_symbol(requested: str, broker_symbols: dict[str, str]) -> tuple[str, str]:
    key = canonical(requested)
    candidates = [key, *ALIASES.get(key, [])]
    for candidate in candidates:
        ckey = canonical(candidate)
        if ckey in broker_symbols:
            return candidate.upper(), broker_symbols[ckey]
    for candidate in candidates:
        ckey = canonical(candidate)
        for broker_key, broker_name in broker_symbols.items():
            if ckey == broker_key or ckey in broker_key or broker_key in ckey:
                return candidate.upper(), broker_name
    return candidates[0].upper(), ""


def parquet_candidates(symbol_key: str, broker_symbol: str, timeframe: str, parquet_dir: Path) -> list[Path]:
    names = [symbol_key, broker_symbol, canonical(symbol_key), canonical(broker_symbol)]
    if symbol_key in ALIASES:
        names.extend(ALIASES[symbol_key])
    unique = []
    for name in names:
        clean = str(name).upper()
        if clean and clean not in unique:
            unique.append(clean)
    return [parquet_dir / timeframe / f"{name}.parquet" for name in unique]


def existing_parquet(symbol_key: str, broker_symbol: str, timeframe: str, parquet_dir: Path) -> Path | None:
    for candidate in parquet_candidates(symbol_key, broker_symbol, timeframe, parquet_dir):
        if candidate.exists() and candidate.stat().st_size > 0:
            return candidate
    return None


def model_status(symbol_key: str, broker_symbol: str) -> tuple[bool, bool]:
    keys = [symbol_key, canonical(broker_symbol)]
    if symbol_key in ALIASES:
        keys.extend(ALIASES[symbol_key])
    keys = [canonical(key) for key in keys if key]
    research = any((PROJECT_DIR / "models_research" / key).exists() for key in keys)
    principal = any((PROJECT_DIR / "models_principal" / key).exists() for key in keys)
    return research, principal


def rates_to_frame(rates: Any, symbol: str) -> pd.DataFrame:
    frame = pd.DataFrame(rates)
    if frame.empty:
        return frame
    frame["date"] = pd.to_datetime(frame["time"], unit="s", utc=True).dt.tz_convert(None)
    frame = frame.rename(columns={"tick_volume": "tick_volume"})
    frame["symbol"] = symbol
    keep = [col for col in ["date", "open", "high", "low", "close", "tick_volume", "spread", "real_volume", "symbol"] if col in frame.columns]
    return frame[keep].sort_values("date").reset_index(drop=True)


def fetch_and_save(mt5: Any, broker_symbol: str, output_symbol: str, timeframe: str, bars: int, parquet_dir: Path) -> tuple[str, int, str]:
    tf_code = mt5_timeframes(mt5)[timeframe]
    mt5.symbol_select(broker_symbol, True)
    counts = [bars, 100000, 50000, 20000, 10000, 5000, 1000]
    seen: set[int] = set()
    rates = None
    last_error = ""
    used_count = 0
    for count in counts:
        if count <= 0 or count in seen:
            continue
        seen.add(count)
        rates = mt5.copy_rates_from_pos(broker_symbol, tf_code, 0, count)
        last_error = str(mt5.last_error())
        if rates is not None and len(rates) > 0:
            used_count = count
            break
    if rates is None or len(rates) == 0:
        return "download_empty", 0, last_error
    frame = rates_to_frame(rates, output_symbol)
    tf_dir = parquet_dir / timeframe
    tf_dir.mkdir(parents=True, exist_ok=True)
    path = tf_dir / f"{output_symbol}.parquet"
    frame.to_parquet(path, index=False)
    return "downloaded", len(frame), f"{path} | requested_bars={used_count}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Audita modelos/historicos e baixa candles ausentes do MT5.")
    parser.add_argument("--symbols", nargs="+", required=True)
    parser.add_argument("--timeframes", nargs="*", default=TIMEFRAMES)
    parser.add_argument("--parquet-dir", default="data/parquet")
    parser.add_argument("--report-dir", default="reports/asset_history_audit")
    parser.add_argument("--bars", type=int, default=200000)
    parser.add_argument("--download-missing", action="store_true")
    args = parser.parse_args()

    cfg = load_config()
    parquet_dir = PROJECT_DIR / args.parquet_dir
    report_dir = PROJECT_DIR / args.report_dir
    report_dir.mkdir(parents=True, exist_ok=True)

    try:
        import MetaTrader5 as mt5
    except ImportError as exc:
        raise SystemExit(f"MetaTrader5 indisponivel: {exc}") from exc

    terminal_path = cfg.get("broker", {}).get("terminal_path")
    initialized = mt5.initialize(path=terminal_path) if terminal_path else mt5.initialize()
    if not initialized:
        raise SystemExit(f"Falha ao inicializar MT5: {mt5.last_error()}")

    rows: list[dict[str, Any]] = []
    try:
        broker_symbols = discover_broker_symbols(mt5)
        for raw in args.symbols:
            requested = canonical(raw)
            symbol_key, broker_symbol = resolve_symbol(raw, broker_symbols)
            has_research, has_principal = model_status(symbol_key, broker_symbol)
            for timeframe in [tf.upper() for tf in args.timeframes]:
                parquet = existing_parquet(symbol_key, broker_symbol, timeframe, parquet_dir)
                status = "history_ok" if parquet else "history_missing"
                rows_count = ""
                message = str(parquet or "")
                if parquet:
                    try:
                        rows_count = len(pd.read_parquet(parquet, columns=["close"]))
                    except Exception as exc:  # noqa: BLE001
                        status = "history_unreadable"
                        message = str(exc)
                elif args.download_missing and broker_symbol:
                    output_symbol = symbol_key
                    status, rows_count, message = fetch_and_save(mt5, broker_symbol, output_symbol, timeframe, args.bars, parquet_dir)
                elif not broker_symbol:
                    status = "broker_symbol_not_found"
                    message = "nao encontrado no MT5"

                rows.append(
                    {
                        "requested": raw,
                        "symbol_key": symbol_key,
                        "broker_symbol": broker_symbol,
                        "timeframe": timeframe,
                        "history_status": status,
                        "history_rows": rows_count,
                        "message": message,
                        "has_models_research": has_research,
                        "has_models_principal": has_principal,
                    }
                )
    finally:
        mt5.shutdown()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_path = report_dir / f"asset_history_model_audit_{stamp}.csv"
    with report_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        writer.writerows(rows)

    missing = [row for row in rows if row["history_status"] not in {"history_ok", "downloaded"}]
    no_research = sorted({row["symbol_key"] for row in rows if not row["has_models_research"]})
    print(f"Ativos solicitados: {len(args.symbols)}")
    print(f"Linhas de auditoria: {len(rows)}")
    print(f"Historicos pendentes: {len(missing)}")
    print(f"Sem models_research: {len(no_research)} -> {', '.join(no_research[:30])}")
    print(f"Relatorio: {report_path}")


if __name__ == "__main__":
    main()
