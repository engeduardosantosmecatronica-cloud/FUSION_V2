from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def load_market_frame(path: str | Path, max_rows: int | None = None) -> pd.DataFrame:
    source = Path(path)
    if source.suffix.lower() == ".parquet":
        frame = pd.read_parquet(source)
    else:
        frame = pd.read_csv(source, sep=None, engine="python")
    if max_rows is not None and len(frame) > max_rows:
        frame = frame.tail(max_rows).reset_index(drop=True)
    return frame


def infer_symbol_timeframe(path: str | Path, symbol: str | None = None, timeframe: str | None = None) -> tuple[str, str]:
    if symbol and timeframe:
        return symbol.upper(), timeframe.upper()
    stem = Path(path).stem.upper()
    parts = stem.split("_")
    inferred_tf = timeframe or (parts[-1] if len(parts) > 1 else "M5")
    inferred_symbol = symbol or ("_".join(parts[:-1]) if len(parts) > 1 else stem)
    return inferred_symbol.upper(), inferred_tf.upper()


def write_json(path: str | Path, payload: dict[str, Any]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return output


def summarize_frame(frame: pd.DataFrame) -> dict[str, Any]:
    return {
        "rows": int(len(frame)),
        "columns": int(frame.shape[1]),
        "numeric_columns": int(len(frame.select_dtypes(include="number").columns)),
        "columns_sample": list(map(str, frame.columns[:20])),
    }
