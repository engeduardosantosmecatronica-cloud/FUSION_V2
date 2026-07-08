from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from common import PROJECT_ROOT, load_market_frame, write_json

from fusion_best.dataset_builder import normalize_ohlcv_columns
from fusion_best.expert_training import EXPERT_SPECS


DEFAULT_ACTIVATIONS = (50, 80, 100, 120, 150, 200, 250, 300, 400)
DEFAULT_DISTANCES = (30, 40, 50, 60, 80, 100, 120, 150)


def parse_points(value: str) -> tuple[int, ...]:
    return tuple(int(float(item.strip())) for item in value.split(",") if item.strip())


def infer_point_size(symbol: str) -> float:
    symbol = symbol.upper()
    if "JPY" in symbol:
        return 0.001
    if symbol.startswith(("XAU", "GOLD")):
        return 0.01
    if symbol.startswith(("XAG", "SILVER")):
        return 0.001
    return 0.00001


def load_tp_sl_report(path: Path) -> pd.DataFrame:
    report = pd.read_csv(path)
    report["symbol"] = report["symbol"].astype(str).str.upper()
    report["timeframe"] = report["timeframe"].astype(str).str.upper()
    return report


def tp_sl_for(report: pd.DataFrame, symbol: str, timeframe: str, default_tp: int, default_sl: int) -> tuple[int, int]:
    rows = report[(report["symbol"] == symbol.upper()) & (report["timeframe"] == timeframe.upper())]
    if rows.empty:
        return default_tp, default_sl
    row = rows.iloc[0]
    tp = int(float(row.get("best_target", default_tp) or default_tp))
    sl = int(float(row.get("stop_sugerido", default_sl) or default_sl))
    return tp, sl


def prepare_market_frame(path: Path) -> pd.DataFrame:
    frame = normalize_ohlcv_columns(load_market_frame(path))
    if not isinstance(frame.index, pd.DatetimeIndex):
        for col in ("time", "timestamp", "datetime", "date"):
            if col in frame.columns:
                frame[col] = pd.to_datetime(frame[col])
                frame = frame.set_index(col)
                break
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise ValueError(f"Sem coluna de tempo reconhecida em {path}")
    frame = frame.sort_index()
    return frame[["open", "high", "low", "close"] + ([ "spread" ] if "spread" in frame.columns else [])].copy()


def positive_weight_experts(path: Path, min_weight: float) -> set[str]:
    if not path.exists():
        return set()
    payload = json.loads(path.read_text(encoding="utf-8"))
    experts = set()
    for row in payload.get("weights", []):
        if float(row.get("calibrated_weight") or 0.0) >= min_weight:
            experts.add(str(row.get("expert", "")))
    return {expert for expert in experts if expert}


def load_trade_frame(
    path: Path,
    min_confidence: float,
    weights_path: Path | None = None,
    positive_weights_only: bool = True,
    min_weight: float = 0.25,
) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    trades = pd.read_csv(path)
    if trades.empty:
        return trades
    if positive_weights_only and weights_path is not None:
        allowed_experts = positive_weight_experts(weights_path, min_weight=min_weight)
        if allowed_experts and "expert" in trades.columns:
            trades = trades[trades["expert"].astype(str).isin(allowed_experts)].copy()
    trades["timestamp"] = pd.to_datetime(trades["timestamp"])
    trades["direction"] = trades["direction"].astype(int)
    if "confidence" in trades.columns:
        trades = trades[trades["confidence"].astype(float) >= min_confidence]
    trades = trades[trades["direction"] != 0].copy()
    return trades.sort_values("timestamp")


def exit_trade(
    market: pd.DataFrame,
    entry_pos: int,
    direction: int,
    horizon: int,
    point_size: float,
    tp_points: int,
    sl_points: int,
    activation_points: int,
    distance_points: int,
) -> dict[str, Any] | None:
    if entry_pos < 0 or entry_pos >= len(market) - 1:
        return None

    entry = float(market["close"].iloc[entry_pos])
    if not np.isfinite(entry) or entry <= 0:
        return None

    if direction > 0:
        tp = entry + tp_points * point_size
        stop = entry - sl_points * point_size
    else:
        tp = entry - tp_points * point_size
        stop = entry + sl_points * point_size

    activated = False
    best_price = entry
    end_pos = min(len(market) - 1, entry_pos + max(int(horizon), 1))

    for pos in range(entry_pos + 1, end_pos + 1):
        high = float(market["high"].iloc[pos])
        low = float(market["low"].iloc[pos])
        close = float(market["close"].iloc[pos])

        if direction > 0:
            if low <= stop:
                return {"exit_points": (stop - entry) / point_size, "reason": "SL_TRAIL" if activated else "SL", "bars": pos - entry_pos}
            if high >= tp:
                return {"exit_points": (tp - entry) / point_size, "reason": "TP", "bars": pos - entry_pos}
            if high > best_price:
                best_price = high
            if (best_price - entry) / point_size >= activation_points:
                activated = True
                stop = max(stop, best_price - distance_points * point_size)
        else:
            if high >= stop:
                return {"exit_points": (entry - stop) / point_size, "reason": "SL_TRAIL" if activated else "SL", "bars": pos - entry_pos}
            if low <= tp:
                return {"exit_points": (entry - tp) / point_size, "reason": "TP", "bars": pos - entry_pos}
            if low < best_price:
                best_price = low
            if (entry - best_price) / point_size >= activation_points:
                activated = True
                stop = min(stop, best_price + distance_points * point_size)

    exit_points = ((close - entry) / point_size) if direction > 0 else ((entry - close) / point_size)
    return {"exit_points": exit_points, "reason": "TIME", "bars": end_pos - entry_pos}


def summarize(results: list[float], reasons: list[str], bars: list[int]) -> dict[str, Any]:
    if not results:
        return {
            "trades": 0,
            "winrate": 0.0,
            "avg_points": 0.0,
            "total_points": 0.0,
            "profit_factor": 0.0,
            "max_drawdown_points": 0.0,
            "tp_hits": 0,
            "sl_hits": 0,
            "trail_hits": 0,
            "time_exits": 0,
            "avg_bars": 0.0,
        }
    returns = pd.Series(results, dtype=float)
    equity = returns.cumsum()
    drawdown = equity - equity.cummax()
    gross_profit = float(returns[returns > 0].sum())
    gross_loss = abs(float(returns[returns < 0].sum()))
    reason_series = pd.Series(reasons, dtype=str)
    return {
        "trades": int(len(returns)),
        "winrate": float((returns > 0).mean()),
        "avg_points": float(returns.mean()),
        "total_points": float(returns.sum()),
        "profit_factor": float(gross_profit / gross_loss) if gross_loss > 0 else float("inf"),
        "max_drawdown_points": float(drawdown.min()),
        "tp_hits": int((reason_series == "TP").sum()),
        "sl_hits": int((reason_series == "SL").sum()),
        "trail_hits": int((reason_series == "SL_TRAIL").sum()),
        "time_exits": int((reason_series == "TIME").sum()),
        "avg_bars": float(np.mean(bars)) if bars else 0.0,
    }


def optimize_symbol_timeframe(
    symbol: str,
    timeframe: str,
    market_path: Path,
    trades_path: Path,
    weights_path: Path,
    tp_points: int,
    sl_points: int,
    activations: tuple[int, ...],
    distances: tuple[int, ...],
    min_confidence: float,
    default_horizon: int,
    positive_weights_only: bool,
    min_weight: float,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    market = prepare_market_frame(market_path)
    trades = load_trade_frame(
        trades_path,
        min_confidence=min_confidence,
        weights_path=weights_path,
        positive_weights_only=positive_weights_only,
        min_weight=min_weight,
    )
    if trades.empty:
        return pd.DataFrame(), {"symbol": symbol, "timeframe": timeframe, "status": "no_trades"}

    positions = market.index.searchsorted(trades["timestamp"].to_numpy())
    point_size = infer_point_size(symbol)
    rows = []
    for activation in activations:
        for distance in distances:
            if distance >= activation:
                continue
            results: list[float] = []
            reasons: list[str] = []
            bars: list[int] = []
            for trade, entry_pos in zip(trades.itertuples(index=False), positions):
                expert = str(getattr(trade, "expert", ""))
                horizon = int(getattr(EXPERT_SPECS.get(expert), "horizon", default_horizon))
                outcome = exit_trade(
                    market=market,
                    entry_pos=int(entry_pos),
                    direction=int(getattr(trade, "direction")),
                    horizon=horizon,
                    point_size=point_size,
                    tp_points=tp_points,
                    sl_points=sl_points,
                    activation_points=activation,
                    distance_points=distance,
                )
                if outcome is None:
                    continue
                spread_points = 0.0
                if "spread" in market.columns and int(entry_pos) < len(market):
                    spread_points = float(market["spread"].iloc[int(entry_pos)] or 0.0)
                results.append(float(outcome["exit_points"]) - spread_points)
                reasons.append(str(outcome["reason"]))
                bars.append(int(outcome["bars"]))
            summary = summarize(results, reasons, bars)
            summary.update(
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "tp_points": int(tp_points),
                    "sl_points": int(sl_points),
                    "activation_points": int(activation),
                    "distance_points": int(distance),
                }
            )
            rows.append(summary)

    result = pd.DataFrame(rows)
    if result.empty:
        return result, {"symbol": symbol, "timeframe": timeframe, "status": "empty_grid"}
    result = result.sort_values(
        ["total_points", "profit_factor", "winrate", "max_drawdown_points"],
        ascending=[False, False, False, False],
    )
    best = result.iloc[0].replace({np.nan: None}).to_dict()
    best["status"] = "ok"
    return result, best


def discover_symbols(symbols: str, report: pd.DataFrame, timeframe: str) -> list[str]:
    if symbols:
        return [item.strip().upper() for item in symbols.split(",") if item.strip()]
    subset = report[report["timeframe"] == timeframe.upper()]
    return sorted(subset["symbol"].dropna().astype(str).str.upper().unique().tolist())


def main() -> None:
    parser = argparse.ArgumentParser(description="Optimize trailing activation and distance using walk-forward trades plus TP/SL report.")
    parser.add_argument("--market-root", default=str(PROJECT_ROOT.parent / "data" / "parquet"))
    parser.add_argument("--tp-sl-report", default=str(PROJECT_ROOT.parent / "features_backteste_ativo_timeframe.csv"))
    parser.add_argument("--trades-root", default=str(PROJECT_ROOT / "reports" / "fusion_walkforward"))
    parser.add_argument("--output-root", default=str(PROJECT_ROOT / "reports" / "trailing_optimization"))
    parser.add_argument("--registry-output", default=str(PROJECT_ROOT / "models" / "production_registry" / "trailing_optimized_M5.json"))
    parser.add_argument("--symbols", default="")
    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--activations", default=",".join(map(str, DEFAULT_ACTIVATIONS)))
    parser.add_argument("--distances", default=",".join(map(str, DEFAULT_DISTANCES)))
    parser.add_argument("--default-tp", type=int, default=500)
    parser.add_argument("--default-sl", type=int, default=80)
    parser.add_argument("--default-horizon", type=int, default=10)
    parser.add_argument("--min-confidence", type=float, default=0.55)
    parser.add_argument("--min-weight", type=float, default=0.25, help="Peso minimo do expert no walk-forward para entrar na otimizacao.")
    parser.add_argument("--all-experts", action="store_true", help="Use todos os trades; por padrao usa apenas experts com peso positivo.")
    args = parser.parse_args()

    timeframe = args.timeframe.upper()
    report = load_tp_sl_report(Path(args.tp_sl_report))
    symbols = discover_symbols(args.symbols, report, timeframe)
    activations = parse_points(args.activations)
    distances = parse_points(args.distances)

    output_root = Path(args.output_root) / timeframe
    output_root.mkdir(parents=True, exist_ok=True)
    best_rows = []
    registry: dict[str, Any] = {"timeframe": timeframe, "items": {}}

    for symbol in symbols:
        market_path = Path(args.market_root) / timeframe / f"{symbol}.parquet"
        trades_path = Path(args.trades_root) / symbol / timeframe / "walkforward_trades.csv"
        weights_path = Path(args.trades_root) / symbol / timeframe / "walkforward_weights.json"
        if not market_path.exists():
            best_rows.append({"symbol": symbol, "timeframe": timeframe, "status": "missing_market"})
            continue
        tp_points, sl_points = tp_sl_for(report, symbol, timeframe, args.default_tp, args.default_sl)
        grid, best = optimize_symbol_timeframe(
            symbol=symbol,
            timeframe=timeframe,
            market_path=market_path,
            trades_path=trades_path,
            weights_path=weights_path,
            tp_points=tp_points,
            sl_points=sl_points,
            activations=activations,
            distances=distances,
            min_confidence=args.min_confidence,
            default_horizon=args.default_horizon,
            positive_weights_only=not args.all_experts,
            min_weight=args.min_weight,
        )
        if not grid.empty:
            grid.to_csv(output_root / f"{symbol}_{timeframe}_trailing_grid.csv", index=False)
        best_rows.append(best)
        if best.get("status") == "ok" and float(best.get("total_points") or 0.0) > 0 and float(best.get("profit_factor") or 0.0) >= 1.0:
            registry["items"][f"{symbol}_{timeframe}"] = {
                "symbol": symbol,
                "timeframe": timeframe,
                "activation_points": int(best["activation_points"]),
                "distance_points": int(best["distance_points"]),
                "tp_points": int(best["tp_points"]),
                "sl_points": int(best["sl_points"]),
                "trades": int(best["trades"]),
                "winrate": float(best["winrate"]),
                "total_points": float(best["total_points"]),
                "profit_factor": float(best["profit_factor"]),
                "source": str(output_root / f"{symbol}_{timeframe}_trailing_grid.csv"),
            }

    best_frame = pd.DataFrame(best_rows)
    best_csv = output_root / f"{timeframe}_trailing_best.csv"
    best_json = output_root / f"{timeframe}_trailing_best.json"
    best_frame.to_csv(best_csv, index=False)
    write_json(best_json, {"timeframe": timeframe, "rows": best_frame.replace({np.nan: None}).to_dict(orient="records")})
    write_json(args.registry_output, registry)
    print(f"best_csv: {best_csv}")
    print(f"best_json: {best_json}")
    print(f"registry: {args.registry_output}")


if __name__ == "__main__":
    main()
