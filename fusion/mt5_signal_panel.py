from __future__ import annotations

import csv
import os
import time
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


DEFAULT_FILE_PREFIX = "fusion_signal_panel_"
DEFAULT_FILE_NAME = "fusion_signal_panel.csv"


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


def format_probability(value: Any) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
      return ""


def probability_triplet_text(p_buy: Any, p_sell: Any) -> str:
    try:
        buy = max(0.0, min(1.0, float(p_buy)))
        sell = max(0.0, min(1.0, float(p_sell)))
    except (TypeError, ValueError):
        return ""

    wait = max(0.0, min(1.0, 1.0 - buy - sell))
    return f"W:{wait:.3f} B:{buy:.3f} S:{sell:.3f}"


def format_wait_probability(p_buy: Any, p_sell: Any) -> str:
    try:
        buy = max(0.0, min(1.0, float(p_buy)))
        sell = max(0.0, min(1.0, float(p_sell)))
    except (TypeError, ValueError):
        return ""
    return f"{max(0.0, min(1.0, 1.0 - buy - sell)):.4f}"


def panel_text(value: Any) -> str:
    """Keep CSV fields simple enough for the MQL5 panel reader."""
    text = str(value or "")
    return (
        text.replace("\r", " ")
        .replace("\n", " ")
        .replace(",", ";")
        .replace('"', "'")
        .strip()
    )


class MT5SignalPanelExporter:
    def __init__(
        self,
        output_dir: str | Path | None = None,
        use_common_files: bool = True,
        file_prefix: str = DEFAULT_FILE_PREFIX,
        enabled: bool = True,
    ) -> None:
        self.enabled = bool(enabled)
        self.file_prefix = file_prefix or DEFAULT_FILE_PREFIX
        if output_dir:
            self.output_dir = Path(output_dir)
        elif use_common_files:
            self.output_dir = mt5_common_files_dir()
        else:
            self.output_dir = Path("runtime") / "mt5_files"

    def export(
        self,
        monitor_state: dict[tuple[str, str], dict[str, Any]],
        symbols: list[str],
        timeframes: list[str],
        actionable_state: dict[tuple[str, str], dict[str, Any]] | None = None,
        final_state: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        if not self.enabled or not self.output_dir:
            return

        self.output_dir.mkdir(parents=True, exist_ok=True)
        actionable_state = actionable_state or {}
        for symbol in sorted({str(item).upper() for item in symbols}):
            rows = []
            for timeframe in timeframes:
                tf = str(timeframe).upper()
                state = monitor_state.get((symbol, tf), {})
                actionable = actionable_state.get((symbol, tf), {})
                signal = prediction_to_signal(state.get("signal", 0))
                rows.append(
                    {
                        "timeframe": tf,
                        "signal": signal,
                        "p_buy": format_probability(state.get("p_buy")),
                        "p_sell": format_probability(state.get("p_sell")),
                        "p_wait": format_wait_probability(state.get("p_buy"), state.get("p_sell")),
                        "prob_text": probability_triplet_text(state.get("p_buy"), state.get("p_sell")),
                        "reason": panel_text(state.get("reason") or state.get("status") or ""),
                        "alert_signal": prediction_to_signal(actionable.get("signal", 0)) if actionable else "",
                        "alert_reason": panel_text(actionable.get("reason") or ""),
                    }
                )
            final = (final_state or {}).get(symbol, {}) if final_state else {}
            if final:
                actionable_items = [
                    item
                    for (item_symbol, _tf), item in actionable_state.items()
                    if str(item_symbol).upper() == symbol and item
                ]
                actionable_items.sort(key=lambda item: str(item.get("timestamp") or ""))
                final_actionable = actionable_items[-1] if actionable_items else {}
                rows.append(
                    {
                        "timeframe": "FINAL",
                        "signal": prediction_to_signal(final.get("signal", 0)),
                        "p_buy": format_probability(final.get("p_buy")),
                        "p_sell": format_probability(final.get("p_sell")),
                        "p_wait": format_wait_probability(final.get("p_buy"), final.get("p_sell")),
                        "prob_text": probability_triplet_text(final.get("p_buy"), final.get("p_sell")),
                        "reason": panel_text(final.get("reason") or ""),
                        "alert_signal": prediction_to_signal(final_actionable.get("signal", 0)) if final_actionable else "",
                        "alert_reason": panel_text(final_actionable.get("reason") or ""),
                    }
                )
            self._write_symbol(symbol, rows)

    def _write_symbol(self, symbol: str, rows: list[dict[str, str]]) -> None:
        path = self.output_dir / f"{self.file_prefix}{symbol}.csv"
        self._atomic_csv_write(path, rows)

    @staticmethod
    def _atomic_csv_write(path: Path, rows: list[dict[str, str]]) -> None:
        fieldnames = [
            "timeframe",
            "signal",
            "p_buy",
            "p_sell",
            "reason",
            "alert_signal",
            "alert_reason",
            "p_wait",
            "prob_text",
        ]
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
