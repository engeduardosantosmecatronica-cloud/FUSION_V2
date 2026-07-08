from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def prepare_qlib_ohlcv_csv(
    input_path: str | Path,
    output_path: str | Path,
    symbol: str,
    volume_column: str = "tick_volume",
) -> Path:
    df = pd.read_csv(input_path)
    if "date" not in df.columns and "time" in df.columns:
        df = df.rename(columns={"time": "date"})
    df["date"] = pd.to_datetime(df["date"])
    df["symbol"] = symbol.upper()
    if volume_column in df.columns and "volume" not in df.columns:
        df = df.rename(columns={volume_column: "volume"})
    if "volume" not in df.columns:
        df["volume"] = 0
    cols = ["date", "symbol", "open", "high", "low", "close", "volume"]
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    df[cols].sort_values("date").to_csv(output, index=False)
    return output


def prepare_qlib_binary_columns(
    frame: pd.DataFrame,
    output_dir: str | Path,
    symbol: str,
    freq: str = "5min",
    date_col: str = "date",
    columns: tuple[str, ...] = ("open", "high", "low", "close", "volume"),
) -> dict[str, Path]:
    df = frame.copy()
    df.columns = [str(col).lower() for col in df.columns]
    date_col = date_col.lower()
    if date_col not in df.columns and "time" in df.columns:
        date_col = "time"
    if date_col not in df.columns:
        raise ValueError("date/time column not found")
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col)

    root = Path(output_dir)
    feature_dir = root / "features" / symbol.lower()
    calendar_dir = root / "calendars"
    feature_dir.mkdir(parents=True, exist_ok=True)
    calendar_dir.mkdir(parents=True, exist_ok=True)

    calendar_path = calendar_dir / f"{freq}.txt"
    calendar_path.write_text("\n".join(df[date_col].dt.strftime("%Y-%m-%d %H:%M:%S").unique()) + "\n", encoding="utf-8")

    written: dict[str, Path] = {"calendar": calendar_path}
    for column in columns:
        if column not in df.columns:
            continue
        path = feature_dir / f"{column.lower()}.{freq}.bin"
        path.write_bytes(np.asarray(df[column], dtype=np.float32).tobytes())
        written[column] = path
    return written


def qlib_file_dumper_config(
    csv_path: str | Path,
    qlib_dir: str | Path,
    freq: str = "5min",
    max_workers: int = 4,
) -> dict[str, Any]:
    return {
        "class": "FileDataDumper",
        "module_path": "qlib.data.dump",
        "kwargs": {
            "csv_path": str(csv_path),
            "qlib_dir": str(qlib_dir),
            "freq": freq,
            "max_workers": max_workers,
            "date_field_name": "date",
            "symbol_field_name": "symbol",
        },
    }


def rank_information_coefficient(features: pd.DataFrame, label: pd.Series, min_samples: int = 100) -> pd.DataFrame:
    rows = []
    for col in features.columns:
        mask = ~features[col].isna() & ~label.isna()
        if int(mask.sum()) < min_samples:
            continue
        ic = features.loc[mask, col].corr(label.loc[mask], method="spearman")
        rows.append({"feature": col, "rank_ic": ic, "abs_ic": abs(ic)})
    return pd.DataFrame(rows).sort_values("abs_ic", ascending=False).reset_index(drop=True)


def build_omnis_elite_alphas(df: pd.DataFrame, horizon: int = 1) -> pd.DataFrame:
    frame = df.copy()
    frame.columns = [str(col).lower() for col in frame.columns]
    required = {"open", "high", "low", "close"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"missing required OHLC columns: {sorted(missing)}")
    frame["label"] = frame["close"].shift(-horizon) / frame["close"] - 1
    frame["roc_5"] = frame["close"] / frame["close"].shift(5) - 1
    low_20 = frame["low"].rolling(20).min()
    high_20 = frame["high"].rolling(20).max()
    frame["rsv_20"] = (frame["close"] - low_20) / (high_20 - low_20 + 1e-9)
    k = frame["rsv_20"].ewm(com=2).mean()
    d = k.ewm(com=2).mean()
    frame["j_indicator"] = 3 * k - 2 * d
    frame["persistence"] = frame["close"].rolling(10).apply(lambda x: np.corrcoef(x, np.arange(len(x)))[0, 1], raw=True)
    frame["vstd_20"] = frame["close"].rolling(20).std() / frame["close"].rolling(20).mean()
    return frame.replace([np.inf, -np.inf], np.nan)


def rank_omnis_elite_alphas(df: pd.DataFrame, horizon: int = 1, min_samples: int = 100) -> pd.DataFrame:
    alpha_frame = build_omnis_elite_alphas(df, horizon=horizon).dropna()
    features = alpha_frame[["roc_5", "rsv_20", "j_indicator", "persistence", "vstd_20"]]
    return rank_information_coefficient(features, alpha_frame["label"], min_samples=min_samples)


def alpha158_handler_config(
    instrument: str = "EURUSD",
    start_time: str = "2020-01-02",
    end_time: str = "2026-02-03",
    freq: str = "15min",
    horizon: int = 4,
) -> dict[str, Any]:
    return {
        "class": "Alpha158",
        "module_path": "qlib.contrib.data.handler",
        "kwargs": {
            "instruments": instrument,
            "start_time": start_time,
            "end_time": end_time,
            "freq": freq,
            "label": [f"Ref($close, -{horizon}) / Ref($close, -1) - 1"],
        },
    }


def probability_diagnostics(probabilities: pd.Series | list[float], thresholds: tuple[float, ...] = (0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8)) -> dict[str, Any]:
    probs = pd.Series(probabilities, dtype=float).dropna()
    return {
        "count": int(len(probs)),
        "mean": float(probs.mean()) if len(probs) else 0.0,
        "median": float(probs.median()) if len(probs) else 0.0,
        "std": float(probs.std()) if len(probs) else 0.0,
        "min": float(probs.min()) if len(probs) else 0.0,
        "max": float(probs.max()) if len(probs) else 0.0,
        "by_threshold": {str(thr): int((probs > thr).sum()) for thr in thresholds},
        "extreme_buy": int((probs > 0.7).sum()),
        "extreme_sell": int((probs < 0.3).sum()),
        "neutral_band": int(((probs >= 0.4) & (probs <= 0.6)).sum()),
    }


def binary_signal_from_probability(prob_up: float, buy_threshold: float = 0.55, sell_threshold: float = 0.45) -> str:
    if prob_up > buy_threshold:
        return "BUY"
    if prob_up < sell_threshold:
        return "SELL"
    return "NEUTRAL"


def prepare_qlib_port_config(config: dict[str, Any] | None = None, freq: str = "15min", topk: int = 5, n_drop: int = 2) -> dict[str, Any]:
    import copy

    cfg = copy.deepcopy(config or {})
    executor = cfg.setdefault("executor", {})
    executor["class"] = "SimulatorExecutor"
    executor["module_path"] = "qlib.backtest.executor"
    executor_kwargs = executor.setdefault("kwargs", {})
    executor_kwargs["time_per_step"] = freq
    executor_kwargs["generate_portfolio_metrics"] = True

    strategy = cfg.setdefault("strategy", {})
    strategy["class"] = "TopkDropoutStrategy"
    strategy["module_path"] = "qlib.contrib.strategy.signal_strategy"
    strategy_kwargs = strategy.setdefault("kwargs", {})
    strategy_kwargs["signal"] = "<PRED>"
    strategy_kwargs.setdefault("topk", topk)
    strategy_kwargs.setdefault("n_drop", n_drop)

    backtest = cfg.setdefault("backtest", {})
    backtest["benchmark"] = None
    exchange = backtest.setdefault("exchange_kwargs", {})
    exchange["freq"] = freq
    exchange["limit_threshold"] = None
    exchange.setdefault("deal_price", "close")
    return cfg


def summarize_qlib_predictions(pred: pd.Series, label: pd.Series, topk: int = 5) -> dict[str, float | int]:
    frame = pd.DataFrame({"pred": pred, "label": label}).dropna(subset=["label"])
    if frame.empty:
        return {"rows": 0, "positive_coverage": 0.0, "corr": 0.0, "topk_return": 0.0}
    positive_coverage = float((frame["pred"] > 0).mean())
    corr = float(frame["pred"].corr(frame["label"]))
    if isinstance(frame.index, pd.MultiIndex):
        indexed = frame.reset_index()
        time_col = "datetime" if "datetime" in indexed.columns else indexed.columns[0]
        top = indexed.sort_values([time_col, "pred"], ascending=[True, False]).groupby(time_col, group_keys=False).head(topk)
        step_returns = top.groupby(time_col)["label"].mean()
    else:
        step_returns = frame.sort_values("pred", ascending=False).head(topk)["label"]
    equity = (1 + step_returns).cumprod()
    return {
        "rows": int(len(frame)),
        "positive_coverage": positive_coverage,
        "corr": corr,
        "topk_return": float(equity.iloc[-1] - 1) if len(equity) else 0.0,
    }


def qlib_scalper_15m_fields() -> list[str]:
    return [
        "$close/Ref($close,1)-1",
        "Mean($close,20)/$close",
        "Mean($close,50)/$close",
        "Std($close,20)/$close",
        "($close-Min($low,20))/(Max($high,20)-Min($low,20)+1e-5)",
    ]


def qlib_forward_return_label(horizon: int = 4) -> str:
    return f"Ref($close, -{horizon})/$close - 1"


def evaluate_prediction_strategy_returns(
    predictions: np.ndarray | pd.Series,
    forward_returns: np.ndarray | pd.Series,
    horizon: int = 4,
    threshold: float | None = None,
) -> dict[str, Any]:
    pred = np.asarray(predictions, dtype=float)
    ret = np.asarray(forward_returns, dtype=float)
    n = min(len(pred), len(ret))
    if n <= horizon:
        return {"rows": 0, "total_return": 0.0, "win_rate": 0.0, "trades": 0, "equity_curve": []}
    pred = pred[: n - horizon]
    ret = ret[: n - horizon]
    cutoff = float(np.nanmean(pred)) if threshold is None else threshold
    signal = pred > cutoff
    strategy_returns = np.where(signal, ret, 0.0)
    equity = np.cumprod(1 + np.nan_to_num(strategy_returns, nan=0.0))
    trades = int(signal.sum())
    win_rate = float((strategy_returns[signal] > 0).mean()) if trades else 0.0
    return {
        "rows": int(len(strategy_returns)),
        "threshold": cutoff,
        "trades": trades,
        "win_rate": win_rate,
        "total_return": float(equity[-1] - 1) if len(equity) else 0.0,
        "equity_curve": equity.tolist(),
    }
