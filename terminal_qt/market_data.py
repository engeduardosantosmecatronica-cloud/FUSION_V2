from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from fusion_terminal_qt import ROOT, TIMEFRAMES, normalize_symbol

from runtime_utils import (
    BROKER_SETTINGS,
    SYMBOL_CONTRACTS,
    TARGET_SYMBOLS,
    TRAILING_SYMBOL_MAPPING,
    safe_float,
    sanitize_candles,
)

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None


MT5_TIMEFRAMES = {
    "M5": getattr(mt5, "TIMEFRAME_M5", 5),
    "M15": getattr(mt5, "TIMEFRAME_M15", 15),
    "M30": getattr(mt5, "TIMEFRAME_M30", 30),
    "H1": getattr(mt5, "TIMEFRAME_H1", 16385),
    "H4": getattr(mt5, "TIMEFRAME_H4", 16388),
    "D1": getattr(mt5, "TIMEFRAME_D1", 16408),
}


class MarketDataService:
    def __init__(self) -> None:
        self.mt5_ready = False
        self.last_broker_symbol = "-"
        self.last_mt5_error = ""
        self.broker_symbols: dict[str, str] = {}

    def available_symbols(self) -> list[str]:
        symbols: set[str] = set()
        for symbol in TARGET_SYMBOLS:
            symbols.add(normalize_symbol(symbol))
        for symbol in SYMBOL_CONTRACTS:
            symbols.add(normalize_symbol(symbol))
        for symbol in self.mt5_visible_symbols():
            symbols.add(normalize_symbol(symbol))
        for timeframe in TIMEFRAMES:
            for path in (ROOT / "data" / "csv" / timeframe).glob("**/*.csv"):
                symbols.add(normalize_symbol(path.stem))
        return sorted(symbols or {"GOLD"})

    def build_symbol_map(self) -> dict[str, str]:
        mapping: dict[str, str] = {}
        mt5_symbols = set(self.mt5_visible_symbols())
        for symbol in self.available_symbols():
            mapping[symbol] = self.broker_symbol_for(symbol, mt5_symbols)
        self.broker_symbols = mapping
        return mapping

    def broker_symbol_for(self, symbol: str, mt5_symbols: set[str] | None = None) -> str:
        symbol = normalize_symbol(symbol)
        contract = SYMBOL_CONTRACTS.get(symbol, {}) if isinstance(SYMBOL_CONTRACTS, dict) else {}
        if isinstance(contract, dict) and contract.get("broker_symbol"):
            return str(contract["broker_symbol"]).upper()
        if symbol in TRAILING_SYMBOL_MAPPING:
            return str(TRAILING_SYMBOL_MAPPING[symbol]).upper()
        if symbol == "XAUUSD":
            return "GOLD"
        if symbol == "GOLD":
            return "GOLD"
        mt5_symbols = mt5_symbols if mt5_symbols is not None else set(self.mt5_visible_symbols())
        if symbol in mt5_symbols:
            return symbol
        compact = symbol.replace("-", "")
        if compact in mt5_symbols:
            return compact
        if symbol.endswith("-F") and symbol[:-2] in mt5_symbols:
            return symbol[:-2]
        return symbol

    def mt5_visible_symbols(self) -> list[str]:
        if mt5 is None or not self.initialize_mt5():
            return []
        try:
            symbols = mt5.symbols_get()
        except Exception:
            return []
        if not symbols:
            return []
        return sorted(str(item.name).upper() for item in symbols if getattr(item, "visible", True))

    def read_market_data(self, symbol: str, timeframe: str, max_bars: int) -> tuple[list[dict[str, Any]], tuple[Any, ...], str]:
        csv_candles = sanitize_candles(self.read_csv_history(symbol, timeframe, max_bars))
        mt5_candles = self.read_ohlc_mt5(symbol, timeframe)
        if mt5_candles:
            mt5_candles = sanitize_candles(mt5_candles)
            merged = self.merge_candles(csv_candles, mt5_candles, max_bars)
            last = merged[-1] if merged else mt5_candles[-1]
            key = (
                "hybrid",
                symbol,
                timeframe,
                len(merged),
                last.get("time"),
                last.get("open"),
                last.get("high"),
                last.get("low"),
                last.get("close"),
            )
            self.last_mt5_error = ""
            return merged, key, "CSV historico + MT5 live"

        return csv_candles, self.source_key(symbol, timeframe), "CSV fallback"

    def read_csv_history(self, symbol: str, timeframe: str, max_bars: int) -> list[dict[str, Any]]:
        tf_dir = ROOT / "data" / "csv" / timeframe.upper()
        names = [normalize_symbol(symbol), self.last_broker_symbol]
        if normalize_symbol(symbol) in {"GOLD", "XAUUSD"}:
            names.extend(["XAUUSD", "GOLD"])

        paths: list[Path] = []
        for name in dict.fromkeys(str(item).upper() for item in names if item and item != "-"):
            paths.extend(tf_dir.glob(f"**/{name}.csv"))

        rows: list[dict[str, Any]] = []
        for path in sorted(set(paths)):
            try:
                with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
                    reader = csv.DictReader(handle)
                    for row in reader:
                        try:
                            rows.append(
                                {
                                    "time": row.get("time") or row.get("date") or "",
                                    "open": float(row.get("open", 0) or 0),
                                    "high": float(row.get("high", 0) or 0),
                                    "low": float(row.get("low", 0) or 0),
                                    "close": float(row.get("close", 0) or 0),
                                    "tick_volume": safe_float(row.get("tick_volume"), 1.0),
                                }
                            )
                        except (TypeError, ValueError):
                            continue
            except OSError:
                continue
        rows.sort(key=lambda item: str(item.get("time", "")))
        return rows[-max_bars:]

    def merge_candles(
        self,
        historical: list[dict[str, Any]],
        live: list[dict[str, Any]],
        max_bars: int,
    ) -> list[dict[str, Any]]:
        by_time: dict[str, dict[str, Any]] = {}
        for row in historical:
            key = str(row.get("time", ""))
            if key:
                by_time[key] = row
        for row in live:
            key = str(row.get("time", ""))
            if key:
                by_time[key] = row
        return sorted(by_time.values(), key=lambda item: str(item.get("time", "")))[-max_bars:]

    def read_ohlc_mt5(self, symbol: str, timeframe_name: str) -> list[dict[str, Any]]:
        if mt5 is None:
            self.last_mt5_error = "MetaTrader5 nao instalado"
            return []
        if not self.initialize_mt5():
            return []

        broker_symbol = self.broker_symbols.get(symbol) or self.broker_symbol_for(symbol)
        self.last_broker_symbol = broker_symbol
        timeframe = MT5_TIMEFRAMES.get(timeframe_name)
        if timeframe is None:
            self.last_mt5_error = f"timeframe invalido: {timeframe_name}"
            return []

        try:
            if not mt5.symbol_select(broker_symbol, True):
                self.last_mt5_error = f"symbol_select falhou: {broker_symbol} {mt5.last_error()}"
                return []
            rates = mt5.copy_rates_from_pos(broker_symbol, timeframe, 0, 600)
        except Exception:
            self.last_mt5_error = f"erro MT5: {broker_symbol}"
            return []
        if rates is None or len(rates) == 0:
            self.last_mt5_error = f"sem rates: {broker_symbol} {mt5.last_error()}"
            return []

        rows: list[dict[str, Any]] = []
        for row in rates:
            rows.append(
                {
                    "time": datetime.fromtimestamp(int(row["time"])).strftime("%Y-%m-%d %H:%M:%S"),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                }
            )
        return sorted(rows, key=lambda item: str(item.get("time", "")))

    def initialize_mt5(self) -> bool:
        if mt5 is None:
            return False
        if self.mt5_ready:
            return True
        terminal_path = str(BROKER_SETTINGS.get("terminal_path") or "").strip()
        if terminal_path and not Path(terminal_path).exists():
            self.last_mt5_error = f"terminal_path nao existe: {terminal_path}"
            return False
        try:
            self.mt5_ready = bool(mt5.initialize(path=terminal_path)) if terminal_path else bool(mt5.initialize())
        except TypeError:
            self.mt5_ready = bool(mt5.initialize())
        if not self.mt5_ready:
            self.last_mt5_error = f"initialize falhou: {mt5.last_error()}"
        return self.mt5_ready

    def source_key(self, symbol: str, timeframe: str) -> tuple[str, str, float, int]:
        path = self.source_path(symbol, timeframe)
        if not path:
            return symbol, timeframe, 0.0, 0
        stat = path.stat()
        return symbol, timeframe, stat.st_mtime, stat.st_size

    def source_path(self, symbol: str, timeframe: str) -> Path | None:
        tf_dir = ROOT / "data" / "csv" / timeframe.upper()
        names = [normalize_symbol(symbol), self.last_broker_symbol]
        if normalize_symbol(symbol) in {"GOLD", "XAUUSD"}:
            names.extend(["XAUUSD", "GOLD"])
        candidates: list[Path] = []
        for name in dict.fromkeys(names):
            candidates.extend(tf_dir.glob(f"**/{name}.csv"))
        return sorted(candidates, key=lambda item: item.stat().st_mtime, reverse=True)[0] if candidates else None
