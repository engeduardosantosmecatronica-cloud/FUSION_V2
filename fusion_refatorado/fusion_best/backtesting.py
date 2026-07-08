from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd

from .signals import SignalSide, TradingSignal


SignalFn = Callable[[pd.DataFrame], TradingSignal | None]


@dataclass
class BacktestConfig:
    horizon: int = 12
    spread_cost: float = 0.0
    min_confidence: float = 0.55


def simple_signal_backtest(
    df: pd.DataFrame,
    signal_fn: SignalFn,
    config: BacktestConfig | None = None,
) -> pd.DataFrame:
    """Small causal backtest harness extracted from the useful BACKUP backtest ideas."""
    cfg = config or BacktestConfig()
    rows = []
    for i in range(200, len(df) - cfg.horizon):
        history = df.iloc[: i + 1]
        signal = signal_fn(history)
        if signal is None or signal.side == SignalSide.HOLD or signal.confidence < cfg.min_confidence:
            continue
        entry = float(df["close"].iloc[i])
        exit_price = float(df["close"].iloc[i + cfg.horizon])
        direction = 1 if signal.side > 0 else -1
        raw_ret = direction * ((exit_price / entry) - 1)
        net_ret = raw_ret - cfg.spread_cost
        rows.append(
            {
                "timestamp": df.index[i],
                "side": signal.side.name,
                "confidence": signal.confidence,
                "entry": entry,
                "exit": exit_price,
                "raw_return": raw_ret,
                "net_return": net_ret,
                "win": int(net_ret > 0),
            }
        )
    return pd.DataFrame(rows)


def summarize_backtest(trades: pd.DataFrame) -> dict[str, float]:
    if trades.empty:
        return {
            "trades": 0,
            "winrate": 0.0,
            "avg_return": 0.0,
            "total_return": 0.0,
            "sharpe_like": 0.0,
            "max_drawdown": 0.0,
        }
    returns = trades["net_return"].astype(float)
    equity = (1 + returns).cumprod()
    drawdown = equity / equity.cummax() - 1
    return {
        "trades": int(len(trades)),
        "winrate": float(trades["win"].mean()),
        "avg_return": float(returns.mean()),
        "total_return": float(equity.iloc[-1] - 1),
        "sharpe_like": float(returns.mean() / (returns.std() + 1e-12) * np.sqrt(len(returns))),
        "max_drawdown": float(drawdown.min()),
    }


def evaluate_shard_oos_setups(
    shard: pd.DataFrame,
    predictions: np.ndarray,
    metrics_map: dict[str, dict] | None = None,
    point_factor_default: float = 100000.0,
    spread_points: float = 15.0,
    min_trades: int = 50,
) -> pd.DataFrame:
    data = shard.copy()
    data["pred"] = predictions
    metrics_map = metrics_map or {}
    rows = []
    for symbol, sub in data.groupby("symbol"):
        active = sub[sub["pred"] != 0].copy()
        if len(active) < min_trades or "target_label" not in active:
            continue
        metrics = metrics_map.get(str(symbol), {})
        point_factor = float(metrics.get("Pt_Factor", point_factor_default))
        pnl_points = active["pred"].astype(float) * active["target_label"].astype(float) * point_factor
        pnl_net = pnl_points - spread_points
        total_points = float(pnl_net.sum())
        rows.append(
            {
                "symbol": symbol,
                "trades_oos": int(len(active)),
                "wr": float((pnl_net > 0).mean() * 100),
                "pips_pts": round(total_points, 2),
                "sl": int(metrics.get("SL_Ideal_80p", 500)),
                "tp": int(metrics.get("MFE_80p", 500)),
                "ts_act": int(metrics.get("TS_Activation", metrics.get("SL_Ideal_80p", 500) * 0.5)),
                "ts_dist": int(metrics.get("TS_Distance", metrics.get("SL_Ideal_80p", 500) * 1.1)),
                "mode": "NORMAL" if total_points > 0 else "INVERT",
            }
        )
    return pd.DataFrame(rows).sort_values("pips_pts", ascending=False).reset_index(drop=True) if rows else pd.DataFrame()


def excursion_stats(trades: pd.DataFrame, candles: pd.DataFrame, point_factor: float = 100.0) -> pd.DataFrame:
    rows = []
    candle_frame = candles.copy()
    if "time" in candle_frame.columns:
        candle_frame["time"] = pd.to_datetime(candle_frame["time"])
        candle_frame = candle_frame.set_index("time")
    for _, trade in trades.iterrows():
        open_time = pd.to_datetime(trade.get("Open_Time", trade.get("open_time")))
        close_time = pd.to_datetime(trade.get("Close_Time", trade.get("close_time")))
        entry = float(trade.get("Open_Price", trade.get("open_price")))
        exit_price = float(trade.get("Close_Price", trade.get("close_price")))
        side = str(trade.get("Type", trade.get("type", ""))).lower()
        window = candle_frame.loc[open_time:close_time]
        if window.empty:
            continue
        if side == "buy":
            mae = max(0.0, entry - float(window["low"].min()))
            mfe = max(0.0, float(window["high"].max()) - entry)
            profit = exit_price - entry
        elif side == "sell":
            mae = max(0.0, float(window["high"].max()) - entry)
            mfe = max(0.0, entry - float(window["low"].min()))
            profit = entry - exit_price
        else:
            continue
        rows.append({"mae": mae * point_factor, "mfe": mfe * point_factor, "profit_pts": profit * point_factor})
    return pd.DataFrame(rows)


def summarize_excursions(frame: pd.DataFrame) -> dict[str, float]:
    if frame.empty:
        return {"count": 0, "mae_median": 0.0, "mae_80p": 0.0, "mae_95p": 0.0, "mfe_median": 0.0, "mfe_80p": 0.0}
    return {
        "count": int(len(frame)),
        "mae_median": float(frame["mae"].median()),
        "mae_80p": float(np.percentile(frame["mae"], 80)),
        "mae_95p": float(np.percentile(frame["mae"], 95)),
        "mfe_median": float(frame["mfe"].median()),
        "mfe_80p": float(np.percentile(frame["mfe"], 80)),
    }


def spread_realistic_backtest(
    frame: pd.DataFrame,
    predictions: pd.Series | np.ndarray,
    close_col: str = "close_m15",
    spread_col: str = "spread",
    threshold: float = 0.01,
    point_size: float = 0.01,
) -> dict[str, float]:
    data = frame.copy()
    data["prediction"] = np.asarray(predictions)
    data["signal"] = 0
    data.loc[data["prediction"] > threshold, "signal"] = 1
    data.loc[data["prediction"] < -threshold, "signal"] = -1
    data["spread_cost"] = (data.get(spread_col, 0) * point_size) / (data[close_col] + 1e-12)
    data["pct_change"] = data[close_col].pct_change()
    data["trade_entry"] = data["signal"].diff().fillna(0).abs()
    data["net_ret"] = data["signal"].shift(1) * data["pct_change"] - data["trade_entry"] * data["spread_cost"]
    return {
        "net_return_pct": float(data["net_ret"].fillna(0).sum() * 100),
        "trades": int(data["trade_entry"].sum()),
        "avg_net_return": float(data["net_ret"].fillna(0).mean()),
    }


def long_only_equity_backtest(
    prices: pd.Series,
    predictions: np.ndarray,
    probabilities: np.ndarray | None = None,
    min_confidence: float = 0.55,
    initial_capital: float = 10000.0,
) -> dict[str, float | int]:
    prices = prices.astype(float).ffill()
    probs = probabilities if probabilities is not None else np.ones(len(predictions))
    capital = initial_capital
    quantity = 0.0
    entry = 0.0
    returns: list[float] = []
    equity = []
    for i, signal in enumerate(predictions[: len(prices)]):
        price = float(prices.iloc[i])
        conf = float(probs[i])
        if quantity == 0 and signal == 1 and conf >= min_confidence:
            quantity = capital / price
            entry = price
        elif quantity > 0 and signal == 0 and conf >= min_confidence:
            capital = quantity * price
            returns.append((price - entry) / entry)
            quantity = 0.0
        equity.append(capital if quantity == 0 else quantity * price)
    if quantity > 0:
        final_price = float(prices.iloc[-1])
        capital = quantity * final_price
        returns.append((final_price - entry) / entry)
        equity[-1] = capital
    equity_arr = np.asarray(equity, dtype=float)
    drawdown = (np.maximum.accumulate(equity_arr) - equity_arr) / np.maximum.accumulate(equity_arr)
    return {
        "trades": int(len(returns)),
        "total_return": float((equity_arr[-1] - initial_capital) / initial_capital) if len(equity_arr) else 0.0,
        "win_rate": float(np.mean(np.asarray(returns) > 0)) if returns else 0.0,
        "avg_trade": float(np.mean(returns)) if returns else 0.0,
        "max_drawdown": float(drawdown.max()) if len(drawdown) else 0.0,
    }
