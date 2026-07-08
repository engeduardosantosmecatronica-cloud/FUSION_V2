from __future__ import annotations

import csv
import os
import time
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


DEFAULT_FILE_PREFIX = "fusion_trade_zones_"


def mt5_common_files_dir() -> Path:
    appdata = os.environ.get("APPDATA", "")
    if not appdata:
        return Path()
    return Path(appdata) / "MetaQuotes" / "Terminal" / "Common" / "Files"


def prediction_to_signal(prediction: Any) -> str:
    try:
        pred = int(prediction)
    except (TypeError, ValueError):
        pred = 0
    if pred == 1:
        return "BUY"
    if pred == 2:
        return "SELL"
    return "WAIT"


class MT5TradeZonesExporter:
    TF_ATTRS = {
        "M5": "TIMEFRAME_M5",
        "M15": "TIMEFRAME_M15",
        "M30": "TIMEFRAME_M30",
        "H1": "TIMEFRAME_H1",
        "H4": "TIMEFRAME_H4",
        "D1": "TIMEFRAME_D1",
    }

    def __init__(
        self,
        output_dir: str | Path | None = None,
        use_common_files: bool = True,
        file_prefix: str = DEFAULT_FILE_PREFIX,
        enabled: bool = True,
        bars: int = 120,
        sr_lookback: int = 40,
        atr_period: int = 14,
        entry_atr_width: float = 0.15,
        sr_atr_width: float = 0.08,
        sl_atr_multiplier: float = 1.2,
        tp_r_multiple: float = 2.0,
    ) -> None:
        self.enabled = bool(enabled)
        self.file_prefix = file_prefix or DEFAULT_FILE_PREFIX
        self.bars = max(60, int(bars or 120))
        self.sr_lookback = max(10, int(sr_lookback or 40))
        self.atr_period = max(5, int(atr_period or 14))
        self.entry_atr_width = max(0.01, float(entry_atr_width or 0.15))
        self.sr_atr_width = max(0.01, float(sr_atr_width or 0.08))
        self.sl_atr_multiplier = max(0.1, float(sl_atr_multiplier or 1.2))
        self.tp_r_multiple = max(0.1, float(tp_r_multiple or 2.0))
        if output_dir:
            self.output_dir = Path(output_dir)
        elif use_common_files:
            self.output_dir = mt5_common_files_dir()
        else:
            self.output_dir = Path("runtime") / "mt5_files"

    def export(
        self,
        monitor_state: dict[tuple[str, str], dict[str, Any]],
        symbol_map: dict[str, str],
        timeframes: list[str],
        mt5_module: Any,
    ) -> None:
        if not self.enabled or not self.output_dir or mt5_module is None:
            return

        self.output_dir.mkdir(parents=True, exist_ok=True)
        for broker_symbol, logical_symbol in symbol_map.items():
            rows: list[dict[str, str]] = []
            symbol = str(logical_symbol).upper()
            for timeframe in timeframes:
                rows.extend(self._build_timeframe_rows(mt5_module, str(broker_symbol), symbol, str(timeframe).upper(), monitor_state))
            self._write_symbol(symbol, rows)

    def _build_timeframe_rows(
        self,
        mt5_module: Any,
        broker_symbol: str,
        symbol: str,
        timeframe: str,
        monitor_state: dict[tuple[str, str], dict[str, Any]],
    ) -> list[dict[str, str]]:
        tf_code = getattr(mt5_module, self.TF_ATTRS.get(timeframe, ""), None)
        if tf_code is None:
            return []
        rates = mt5_module.copy_rates_from_pos(broker_symbol, tf_code, 1, self.bars)
        if rates is None or len(rates) < max(self.sr_lookback, self.atr_period) + 2:
            return []

        highs = [float(item["high"]) for item in rates]
        lows = [float(item["low"]) for item in rates]
        closes = [float(item["close"]) for item in rates]
        last_close = closes[-1]
        atr = self._atr(highs, lows, closes)
        if atr <= 0:
            return []

        support = min(lows[-self.sr_lookback :])
        resistance = max(highs[-self.sr_lookback :])
        sr_width = atr * self.sr_atr_width
        rows = [
            self._row(timeframe, "SUPPORT", support - sr_width, support + sr_width, "Suporte"),
            self._row(timeframe, "RESISTANCE", resistance - sr_width, resistance + sr_width, "Resistencia"),
        ]

        state = monitor_state.get((symbol, timeframe), {})
        signal = prediction_to_signal(state.get("signal", 0))
        if signal == "WAIT":
            return rows

        entry_width = atr * self.entry_atr_width
        if signal == "BUY":
            sl_center = min(support, last_close - atr * self.sl_atr_multiplier)
            risk = max(last_close - sl_center, atr * 0.5)
            tp_center = last_close + risk * self.tp_r_multiple
        else:
            sl_center = max(resistance, last_close + atr * self.sl_atr_multiplier)
            risk = max(sl_center - last_close, atr * 0.5)
            tp_center = last_close - risk * self.tp_r_multiple

        rows.extend(
            [
                self._row(timeframe, "ENTRY_ZONE", last_close - entry_width, last_close + entry_width, f"Entrada {signal}", signal),
                self._row(timeframe, "SL_ZONE", sl_center - entry_width, sl_center + entry_width, "SL", signal),
                self._row(timeframe, "TP_ZONE", tp_center - entry_width, tp_center + entry_width, "TP", signal),
            ]
        )
        return rows

    def _atr(self, highs: list[float], lows: list[float], closes: list[float]) -> float:
        true_ranges = []
        start = max(1, len(closes) - self.atr_period)
        for idx in range(start, len(closes)):
            true_ranges.append(
                max(
                    highs[idx] - lows[idx],
                    abs(highs[idx] - closes[idx - 1]),
                    abs(lows[idx] - closes[idx - 1]),
                )
            )
        return sum(true_ranges) / len(true_ranges) if true_ranges else 0.0

    @staticmethod
    def _row(timeframe: str, zone_type: str, price1: float, price2: float, label: str, signal: str = "NONE") -> dict[str, str]:
        low = min(price1, price2)
        high = max(price1, price2)
        return {
            "timeframe": timeframe,
            "type": zone_type,
            "price1": f"{low:.8f}",
            "price2": f"{high:.8f}",
            "label": label,
            "signal": signal or "NONE",
        }

    def _write_symbol(self, symbol: str, rows: list[dict[str, str]]) -> None:
        path = self.output_dir / f"{self.file_prefix}{symbol}.csv"
        self._atomic_csv_write(path, rows)

    @staticmethod
    def _atomic_csv_write(path: Path, rows: list[dict[str, str]]) -> None:
        fieldnames = ["timeframe", "type", "price1", "price2", "label", "signal"]
        with NamedTemporaryFile("w", newline="", encoding="utf-8", delete=False, dir=path.parent, suffix=".tmp") as handle:
            tmp_path = Path(handle.name)
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        try:
            for attempt in range(5):
                try:
                    tmp_path.replace(path)
                    return
                except PermissionError:
                    if attempt == 4:
                        raise
                    time.sleep(0.15)
        except PermissionError:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
