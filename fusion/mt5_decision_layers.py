from __future__ import annotations

import csv
import os
import time
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


DEFAULT_FILE_PREFIX = "fusion_decision_layers_"


def mt5_common_files_dir() -> Path:
    appdata = os.environ.get("APPDATA", "")
    if not appdata:
        return Path()
    return Path(appdata) / "MetaQuotes" / "Terminal" / "Common" / "Files"


def layer_status(output: Any) -> str:
    negative = list(getattr(output, "negative_factors", []) or [])
    warnings = list(getattr(output, "warnings", []) or [])
    state = str(getattr(output, "state", "") or "").lower()
    if negative or state in {"blocked", "block", "critical_risk", "avoid"}:
        return "BLOCK"
    if warnings or state in {"moderate", "high_risk", "reduced_risk", "diagnostic_error"}:
        return "WARN"
    return "OK"


def layer_reason(output: Any) -> str:
    factors = (
        list(getattr(output, "negative_factors", []) or [])
        or list(getattr(output, "warnings", []) or [])
        or list(getattr(output, "positive_factors", []) or [])
        or [str(getattr(output, "state", "") or "ok")]
    )
    return ";".join(str(item) for item in factors[:3])


class MT5DecisionLayersExporter:
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
        layers_state: dict[tuple[str, str], list[dict[str, str]]],
        symbols: list[str],
    ) -> None:
        if not self.enabled or not self.output_dir:
            return

        self.output_dir.mkdir(parents=True, exist_ok=True)
        for symbol in sorted({str(item).upper() for item in symbols}):
            rows: list[dict[str, str]] = []
            for (state_symbol, timeframe), state_rows in layers_state.items():
                if str(state_symbol).upper() != symbol:
                    continue
                rows.extend(state_rows)
            self._write_symbol(symbol, rows)

    @staticmethod
    def rows_from_outputs(timeframe: str, outputs: list[Any], decision: str = "", reason: str = "") -> list[dict[str, str]]:
        rows = []
        for output in outputs:
            rows.append(
                {
                    "timeframe": str(timeframe).upper(),
                    "layer": str(getattr(output, "engine", "") or ""),
                    "status": layer_status(output),
                    "score": f"{float(getattr(output, 'score', 0.0) or 0.0):.2f}",
                    "state": str(getattr(output, "state", "") or ""),
                    "reason": layer_reason(output),
                }
            )
        if decision:
            rows.append(
                {
                    "timeframe": str(timeframe).upper(),
                    "layer": "decision",
                    "status": "OK" if str(decision).upper() == "ALLOW" else "BLOCK",
                    "score": "",
                    "state": str(decision),
                    "reason": str(reason or ""),
                }
            )
        return rows

    def _write_symbol(self, symbol: str, rows: list[dict[str, str]]) -> None:
        path = self.output_dir / f"{self.file_prefix}{symbol}.csv"
        self._atomic_csv_write(path, rows)

    @staticmethod
    def _atomic_csv_write(path: Path, rows: list[dict[str, str]]) -> None:
        fieldnames = ["timeframe", "layer", "status", "score", "state", "reason"]
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
