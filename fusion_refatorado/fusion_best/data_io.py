from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd


TIMEFRAME_NAMES = ("M1", "M5", "M15", "M30", "H1", "H4", "D1")


def load_ohlcv_file(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if path.suffix.lower() == ".parquet":
        df = pd.read_parquet(path)
    else:
        df = pd.read_csv(path)
    df.columns = [str(col).lower() for col in df.columns]
    if "datetime" in df.columns and "time" not in df.columns:
        df = df.rename(columns={"datetime": "time"})
    if "date" in df.columns and "time" not in df.columns:
        df = df.rename(columns={"date": "time"})
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"])
        df = df.set_index("time")
    rename = {
        "tick_volume": "volume",
        "real_volume": "volume",
        "volume": "volume",
    }
    df = df.rename(columns=rename)
    required = {"open", "high", "low", "close"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Colunas obrigatorias ausentes: {sorted(missing)}")
    if "volume" not in df.columns:
        df["volume"] = 0
    return df.sort_index()


def load_mt5_csv(path: str | Path, separator: str = "\t") -> pd.DataFrame:
    """Load raw MT5 exports with or without <DATE>/<TIME> headers."""
    path = Path(path)
    preview = pd.read_csv(path, sep=separator, header=None, nrows=2)
    first_row = preview.iloc[0].astype(str) if len(preview) else pd.Series(dtype=str)
    second_row = preview.iloc[1].astype(str) if len(preview) > 1 else pd.Series(dtype=str)
    if first_row.str.contains("<", regex=False).any():
        df = pd.read_csv(path, sep=separator)
        df.columns = [str(col).strip("<>").lower() for col in df.columns]
    elif second_row.str.contains("<", regex=False).any():
        df = pd.read_csv(path, sep=separator, header=1)
        df.columns = [str(col).strip("<>").lower() for col in df.columns]
    else:
        df = pd.read_csv(path, sep=separator, header=None)
        df.columns = ["date", "time", "open", "high", "low", "close", "tickvol", "vol", "spread"][: len(df.columns)]
    column_map = {
        "tickvol": "volume",
        "tick_volume": "volume",
        "real_volume": "volume",
        "vol": "volume",
        "datetime": "time",
    }
    df = df.rename(columns=column_map)
    if "date" in df.columns and "time" in df.columns:
        df["time"] = pd.to_datetime(df["date"].astype(str) + " " + df["time"].astype(str), errors="coerce")
        df = df.drop(columns=["date"])
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"], errors="coerce")
        df = df.set_index("time")
    required = {"open", "high", "low", "close"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Colunas obrigatorias ausentes: {sorted(missing)}")
    if "volume" not in df.columns:
        df["volume"] = 0
    return df[["open", "high", "low", "close", "volume"]].sort_index()


def get_candles_from_provider(
    provider: Callable[[str, str, int], pd.DataFrame],
    symbol: str,
    timeframe: str,
    n: int,
) -> pd.DataFrame:
    if timeframe not in TIMEFRAME_NAMES:
        raise ValueError(f"Timeframe desconhecido: {timeframe}")
    return provider(symbol, timeframe, n)


def infer_symbol_timeframe(path: str | Path) -> tuple[str | None, str | None]:
    stem = Path(path).stem.upper()
    parts = stem.split("_")
    if len(parts) < 2:
        return None, None
    timeframe = parts[-1]
    symbol = "_".join(parts[:-1])
    return symbol or None, timeframe or None


def inventory_historical_data(root: str | Path) -> pd.DataFrame:
    """Index CSV/Parquet historical files found in old OMNIS data folders."""
    root = Path(root)
    rows: list[dict[str, Any]] = []
    for path in sorted([*root.rglob("*.csv"), *root.rglob("*.parquet")]):
        symbol, timeframe = infer_symbol_timeframe(path)
        rows.append(
            {
                "path": str(path),
                "symbol": symbol,
                "timeframe": timeframe,
                "extension": path.suffix.lower(),
                "bytes": path.stat().st_size,
            }
        )
    return pd.DataFrame(rows)


def inventory_data_quality(root: str | Path) -> pd.DataFrame:
    frame = inventory_historical_data(root)
    if frame.empty:
        return frame
    frame = frame.copy()
    frame["folder_symbol"] = frame["path"].map(lambda value: Path(value).parent.name.upper())
    frame["symbol_matches_folder"] = frame["symbol"].fillna("") == frame["folder_symbol"].fillna("")
    return frame


def standardize_market_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(col).replace("<", "").replace(">", "").lower().strip() for col in out.columns]
    if "symbol" in out.columns:
        out["symbol"] = out["symbol"].astype(str).str.replace(".CSV", "", case=False).str.replace(".parquet", "", case=False).str.strip()
    if "date" in out.columns:
        out["date"] = pd.to_datetime(out["date"], errors="coerce")
    if "time" in out.columns and "date" not in out.columns:
        out["date"] = pd.to_datetime(out["time"], errors="coerce")
    return out


def resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    data = standardize_market_frame(df)
    if "date" in data.columns:
        data = data.set_index("date")
    if not isinstance(data.index, pd.DatetimeIndex):
        raise ValueError("DataFrame precisa de indice datetime ou coluna date/time.")
    volume_col = "volume" if "volume" in data.columns else "tick_volume" if "tick_volume" in data.columns else None
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    if volume_col:
        agg[volume_col] = "sum"
    result = data.resample(rule).agg(agg).dropna(subset=["open", "high", "low", "close"])
    return result.reset_index()


def calculate_genesis_alphas(df: pd.DataFrame) -> pd.DataFrame:
    calc = standardize_market_frame(df)
    for col in ("close", "high", "low"):
        calc[col] = pd.to_numeric(calc[col], errors="coerce")
    calc["ret"] = np.log(calc["close"] / calc["close"].shift(1))
    delta = calc["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    calc["rsi"] = 100 - (100 / (1 + gain / (loss + 1e-9)))
    calc["ema_21"] = calc["close"].ewm(span=21, adjust=False).mean()
    calc["dist_ema"] = calc["close"] / calc["ema_21"] - 1
    calc["range_pct"] = (calc["high"] - calc["low"]) / (calc["close"] + 1e-12)
    calc["alpha_vam"] = calc["ret"].rolling(20).mean() / (calc["range_pct"].rolling(20).std() + 1e-9)
    calc["alpha_effort"] = calc["range_pct"] / (calc["range_pct"].rolling(50).mean() + 1e-9)
    calc["alpha_mrs"] = calc["dist_ema"] / (calc["range_pct"].rolling(20).mean() + 1e-9)
    calc["alpha_rsi_gap"] = calc["rsi"] - calc["rsi"].rolling(10).mean()
    return calc[["rsi", "dist_ema", "ret", "range_pct", "alpha_vam", "alpha_effort", "alpha_mrs", "alpha_rsi_gap"]]


def shard_category(symbol: str) -> str:
    s = symbol.upper()
    if any(token in s for token in ("BTC", "ETH", "LTC", "ADA", "SOL", "TRX", "XLM", "DSH", "LNK", "UNI", "MKR", "YFI", "BCH")):
        return "SHARD_CRYPTO"
    if "GOLD" in s or "SILVER" in s or s.startswith(("XAU", "XAG")):
        return "SHARD_METALS_ELITE"
    if "_IDX" in s or s in {"VOL_IDX", "USA500", "USA30", "USATECH", "USSC2000"}:
        return "SHARD_INDEXES"
    if s.startswith(("AED", "SAR", "RON", "PLN", "TRY", "ZAR", "MXN", "HUF", "CZK", "ILS", "THB", "DKK", "NOK", "SEK")):
        return "SHARD_EXOTICS_WORLD"
    if any(token in s[:3] for token in ("EUR", "GBP", "AUD", "NZD", "CAD", "CHF", "USD")):
        return "SHARD_FOREX_MAJORS" if "USD" in s else "SHARD_FOREX_CROSSES"
    return "SHARD_OTHERS"


def build_genesis_live_features(frames_by_tf: dict[str, pd.DataFrame]) -> pd.DataFrame:
    parts = []
    for tf, frame in frames_by_tf.items():
        data = standardize_market_frame(frame)
        if "tick_volume" in data.columns and "volume" not in data.columns:
            data["volume"] = data["tick_volume"]
        alphas = calculate_genesis_alphas(data).add_suffix(f"_{tf.lower()}")
        if "close" in data.columns:
            alphas[f"close_{tf.lower()}"] = data["close"].values
        if "high" in data.columns:
            alphas[f"high_{tf.lower()}"] = data["high"].values
        if "low" in data.columns:
            alphas[f"low_{tf.lower()}"] = data["low"].values
        if "volume" in data.columns:
            alphas[f"volume_{tf.lower()}"] = data["volume"].values
        parts.append(alphas.tail(1).reset_index(drop=True))
    return pd.concat(parts, axis=1) if parts else pd.DataFrame()


GENESIS_SIGNAL_FACTORS = {
    "M15": ["rsi_m15", "dist_ema_m15", "alpha_vam_m15", "alpha_effort_m15", "alpha_mrs_m15", "alpha_accel_m15", "alpha_rsi_gap_m15"],
    "H1": ["rsi_h1", "dist_ema_h1", "alpha_vam_h1", "alpha_effort_h1", "alpha_mrs_h1", "alpha_accel_h1", "alpha_rsi_gap_h1"],
    "D1": ["rsi_d1", "dist_ema_d1", "alpha_vam_d1", "alpha_effort_d1", "alpha_mrs_d1", "alpha_accel_d1", "alpha_rsi_gap_d1"],
}


def _neutral_genesis_signal(timeframe: str = "H1") -> dict[str, Any]:
    return {"buy_signal": 0.5, "sell_signal": 0.5, "confidence": 0.0, "timeframe": timeframe.upper(), "factors_used": 0}


def _nearest_symbol_row(frame: pd.DataFrame, symbol: str, timestamp: pd.Timestamp) -> pd.Series | None:
    if frame.empty or "date" not in frame.columns or "symbol" not in frame.columns:
        return None
    df = frame.copy()
    df["date"] = pd.to_datetime(df["date"])
    scoped = df[df["symbol"].astype(str).str.upper() == symbol.upper()].sort_values("date")
    if scoped.empty:
        return None
    indexed = scoped.set_index("date")
    idx = indexed.index.get_indexer([pd.Timestamp(timestamp)], method="nearest")[0]
    if idx < 0 or idx >= len(scoped):
        return None
    return scoped.iloc[idx]


def genesis_signal_strength_at(frame: pd.DataFrame, symbol: str, timestamp: pd.Timestamp, timeframe: str = "H1") -> dict[str, Any]:
    row = _nearest_symbol_row(frame, symbol, timestamp)
    if row is None:
        return _neutral_genesis_signal(timeframe)
    factors = GENESIS_SIGNAL_FACTORS.get(timeframe.upper(), GENESIS_SIGNAL_FACTORS["H1"])
    values = [float(row[col]) for col in factors if col in row.index and pd.notna(row[col])]
    if not values:
        return _neutral_genesis_signal(timeframe)
    arr = np.asarray(values, dtype=float)
    sigma = float(arr.std()) or 1.0
    normalized = (arr - float(arr.mean())) / sigma
    buy = float(1 / (1 + np.exp(-normalized.mean())))
    confidence = 0.7
    if "target_label" in row.index and pd.notna(row["target_label"]):
        confidence = min(0.95, 0.5 + abs(0.5 - float(row["target_label"])))
    return {"buy_signal": buy, "sell_signal": 1 - buy, "confidence": confidence, "timeframe": timeframe.upper(), "factors_used": len(values)}


def genesis_trend_alignment_at(frame: pd.DataFrame, symbol: str, timestamp: pd.Timestamp) -> float:
    signals = [genesis_signal_strength_at(frame, symbol, timestamp, timeframe=tf) for tf in ("M15", "H1", "D1")]
    trends = [1 if sig["buy_signal"] > 0.6 else 0 if sig["sell_signal"] > 0.6 else 0.5 for sig in signals]
    return float(np.clip(1 - np.std(trends), 0, 1))


def genesis_risk_factors_at(frame: pd.DataFrame, symbol: str, timestamp: pd.Timestamp) -> dict[str, float]:
    row = _nearest_symbol_row(frame, symbol, timestamp)
    if row is None:
        return {"volatility": 0.5, "drawdown_risk": 0.5, "alpha_quality": 0.0}
    rsi_gaps = [abs(float(row[col])) for col in ("alpha_rsi_gap_m15", "alpha_rsi_gap_h1", "alpha_rsi_gap_d1") if col in row.index and pd.notna(row[col])]
    efforts = [float(row[col]) for col in ("alpha_effort_m15", "alpha_effort_h1", "alpha_effort_d1") if col in row.index and pd.notna(row[col])]
    alpha_vals = [
        float(row[f"alpha_{name}_{tf}"])
        for tf in ("m15", "h1", "d1")
        for name in ("vam", "mrs", "accel")
        if f"alpha_{name}_{tf}" in row.index and pd.notna(row[f"alpha_{name}_{tf}"])
    ]
    return {
        "volatility": min(1.0, (float(np.mean(rsi_gaps)) if rsi_gaps else 50.0) / 100),
        "drawdown_risk": float(1 - np.mean(efforts)) if efforts else 0.5,
        "alpha_quality": float(np.mean(alpha_vals)) if alpha_vals else 0.0,
    }


def tiingo_fx_price_url(symbol: str, start: str | pd.Timestamp, end: str | pd.Timestamp, token: str, freq: str = "15min") -> str:
    start_s = pd.Timestamp(start).strftime("%Y-%m-%d")
    end_s = pd.Timestamp(end).strftime("%Y-%m-%d")
    return f"https://api.tiingo.com/tiingo/fx/{symbol.lower()}/prices?startDate={start_s}&endDate={end_s}&resampleFreq={freq}&token={token}"


def normalize_tiingo_fx_prices(records: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    if "volume" not in df.columns:
        df["volume"] = 0
    return df[["date", "open", "high", "low", "close", "volume"]].sort_values("date").reset_index(drop=True)


def merge_ohlcv_without_duplicates(old: pd.DataFrame | None, new: pd.DataFrame, date_col: str = "date") -> pd.DataFrame:
    if old is None or old.empty:
        combined = new.copy()
    else:
        combined = pd.concat([old, new], ignore_index=True)
    combined[date_col] = pd.to_datetime(combined[date_col]).dt.strftime("%Y-%m-%d %H:%M:%S")
    return combined.drop_duplicates(subset=[date_col], keep="last").sort_values(date_col).reset_index(drop=True)
