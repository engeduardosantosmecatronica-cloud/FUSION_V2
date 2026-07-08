from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from analyze_signal_outcomes import (
    ROOT,
    Signal,
    build_market_data,
    load_config,
    load_signals,
    point_size,
    signal_market_time,
)
from analyze_signal_path_outcomes import candle_spread_points


@dataclass
class PathStats:
    samples: int = 0
    median: float = 0.0
    p70: float = 0.0
    p80: float = 0.0
    p90: float = 0.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera matriz operacional de alvo/stop/drawdown por ativo e lado usando M1 + spread historico."
    )
    parser.add_argument("--date", action="append", required=True, help="Data YYYYMMDD. Pode repetir.")
    parser.add_argument("--audit-dir", default="logs/decision_audit")
    parser.add_argument("--output-dir", default="reports/operational_target_matrix")
    parser.add_argument("--symbols", default="", help="Lista separada por virgula. Vazio usa symbols do config.")
    parser.add_argument("--start", default="", help="Inicio Fusion time: YYYY-MM-DD HH:MM[:SS].")
    parser.add_argument("--end", default="", help="Fim Fusion time: YYYY-MM-DD HH:MM[:SS].")
    parser.add_argument("--only-decision", default="ALLOW", help="ALLOW, BLOCK ou vazio para todos.")
    parser.add_argument("--since-hours", type=float, default=0.0)
    parser.add_argument("--max-signals", type=int, default=0)
    parser.add_argument("--market-time-offset-hours", type=float, default=6.0)
    parser.add_argument("--use-mt5", action="store_true")
    parser.add_argument("--save-mt5-history", action="store_true")
    parser.add_argument("--lookahead-minutes", type=int, default=240)
    parser.add_argument("--min-samples", type=int, default=10)
    parser.add_argument("--targets", default="5,10,15,20,25,30,40,50")
    parser.add_argument("--stops", default="10,15,20,25,30,40,50,70,100")
    parser.add_argument("--max-loss-streak", type=int, default=4)
    parser.add_argument("--min-win-rate", type=float, default=45.0)
    return parser.parse_args()


def parse_numbers(value: str) -> list[float]:
    return [float(item.strip()) for item in str(value or "").split(",") if item.strip()]


def configured_symbols() -> list[str]:
    cfg = load_config()
    return [str(item).upper() for item in (cfg.get("symbols", []) or [])]


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    return round(float(pd.Series(values).quantile(q)), 2)


def summarize_values(values: list[float]) -> PathStats:
    return PathStats(
        samples=len(values),
        median=percentile(values, 0.50),
        p70=percentile(values, 0.70),
        p80=percentile(values, 0.80),
        p90=percentile(values, 0.90),
    )


def max_consecutive_losses(outcomes: list[str]) -> int:
    current = 0
    worst = 0
    for item in outcomes:
        if item == "loss":
            current += 1
            worst = max(worst, current)
        elif item == "win":
            current = 0
    return worst


def build_m1_market_data(signals: list[Signal], args: argparse.Namespace, config: dict[str, Any]) -> dict[tuple[str, str], pd.DataFrame]:
    m1_signals = [
        Signal(
            correlation_id=signal.correlation_id,
            timestamp=signal.timestamp,
            symbol=signal.symbol,
            timeframe="M1",
            strategy=signal.strategy,
            side=signal.side,
            p_buy=signal.p_buy,
            p_sell=signal.p_sell,
            decision=signal.decision,
            reason=signal.reason,
        )
        for signal in signals
    ]
    args.horizons = str(max(10, args.lookahead_minutes + 10))
    return build_market_data(m1_signals, args, config)


def bid_ask_points(candle: pd.Series, point: float) -> tuple[float, float, float, float, float]:
    spread_price = candle_spread_points(candle) * point
    high_bid = float(candle["high"])
    low_bid = float(candle["low"])
    high_ask = high_bid + spread_price
    low_ask = low_bid + spread_price
    close_bid = float(candle["close"])
    return high_bid, low_bid, high_ask, low_ask, close_bid


def path_metrics(signal: Signal, candles: pd.DataFrame, args: argparse.Namespace) -> dict[str, Any] | None:
    if candles.empty:
        return None
    market_timestamp = signal_market_time(signal.timestamp, args)
    idx = candles["date"].searchsorted(market_timestamp, side="right")
    if idx >= len(candles):
        return None

    entry = candles.iloc[idx]
    entry_time = pd.Timestamp(entry["date"])
    end_time = entry_time + pd.Timedelta(minutes=args.lookahead_minutes)
    future = candles[(candles["date"] >= entry_time) & (candles["date"] <= end_time)]
    if future.empty:
        return None

    point = point_size(signal.symbol, candles)
    entry_bid = float(entry["open"])
    entry_ask = entry_bid + candle_spread_points(entry) * point

    net_curve: list[float] = []
    for _, candle in future.iterrows():
        high_bid, low_bid, high_ask, low_ask, _ = bid_ask_points(candle, point)
        if signal.side == "BUY":
            favorable = (high_bid - entry_ask) / point
            adverse = (entry_ask - low_bid) / point
        else:
            favorable = (entry_bid - low_ask) / point
            adverse = (high_ask - entry_bid) / point
        net_curve.append(round(float(favorable), 2))
        net_curve.append(round(float(-adverse), 2))

    if not net_curve:
        return None

    clean_move = 0.0
    drawdown_before_recovery = 0.0
    move_after_recovery = 0.0
    seen_drawdown = False
    recovered = False
    min_before_recovery = 0.0

    for value in net_curve:
        if not seen_drawdown:
            if value >= 0:
                clean_move = max(clean_move, value)
            else:
                seen_drawdown = True
                min_before_recovery = min(min_before_recovery, value)
        elif not recovered:
            min_before_recovery = min(min_before_recovery, value)
            if value >= 0:
                recovered = True
                move_after_recovery = max(move_after_recovery, value)
        else:
            move_after_recovery = max(move_after_recovery, value)

    net_mfe = max(net_curve)
    net_mae = abs(min(net_curve))
    if seen_drawdown:
        drawdown_before_recovery = abs(min_before_recovery)

    return {
        "symbol": signal.symbol,
        "side": signal.side,
        "timestamp": signal.timestamp.isoformat(),
        "market_timestamp": market_timestamp.isoformat(),
        "entry_time": entry_time.isoformat(),
        "entry_spread_points": candle_spread_points(entry),
        "point_size": point,
        "net_mfe_points": round(float(net_mfe), 2),
        "net_mae_points": round(float(net_mae), 2),
        "clean_move_points": round(float(clean_move), 2),
        "drawdown_before_recovery_points": round(float(drawdown_before_recovery), 2),
        "move_after_recovery_points": round(float(move_after_recovery), 2),
        "recovered_after_drawdown": bool(recovered),
    }


def simulate_tp_sl(group: pd.DataFrame, tp: float, sl: float) -> dict[str, Any]:
    outcomes: list[str] = []
    points: list[float] = []
    for _, row in group.iterrows():
        mfe = float(row.get("net_mfe_points", 0.0) or 0.0)
        mae = float(row.get("net_mae_points", 0.0) or 0.0)
        hit_tp = mfe >= tp
        hit_sl = mae >= sl
        if hit_tp and not hit_sl:
            outcomes.append("win")
            points.append(tp)
        elif hit_sl and not hit_tp:
            outcomes.append("loss")
            points.append(-sl)
        elif hit_tp and hit_sl:
            # Ordem intrabar desconhecida; usa regra conservadora quando houve drawdown maior que clean move.
            if float(row.get("clean_move_points", 0.0) or 0.0) >= tp:
                outcomes.append("win")
                points.append(tp)
            else:
                outcomes.append("loss")
                points.append(-sl)
        else:
            outcomes.append("open")
            points.append(0.0)

    wins = outcomes.count("win")
    losses = outcomes.count("loss")
    resolved = wins + losses
    win_rate = wins / resolved * 100.0 if resolved else 0.0
    total_points = sum(points)
    avg_points = total_points / len(points) if points else 0.0
    gross_profit = sum(item for item in points if item > 0)
    gross_loss = abs(sum(item for item in points if item < 0))
    return {
        "tp_net_points": tp,
        "sl_net_points": sl,
        "wins": wins,
        "losses": losses,
        "open": len(points) - resolved,
        "win_rate": round(float(win_rate), 2),
        "avg_points": round(float(avg_points), 2),
        "total_points": round(float(total_points), 2),
        "profit_factor": round(float(gross_profit / gross_loss), 2) if gross_loss > 0 else 999.0,
        "max_loss_streak": max_consecutive_losses(outcomes),
    }


def best_tp_sl(group: pd.DataFrame, targets: list[float], stops: list[float], args: argparse.Namespace) -> dict[str, Any]:
    best: dict[str, Any] | None = None
    for tp in targets:
        for sl in stops:
            result = simulate_tp_sl(group, tp, sl)
            result["recommended"] = (
                result["win_rate"] >= args.min_win_rate
                and result["avg_points"] > 0
                and result["max_loss_streak"] <= args.max_loss_streak
            )
            result["score"] = round(
                result["avg_points"] * 10
                + result["win_rate"] * 0.30
                + min(result["profit_factor"], 5.0) * 5
                - result["max_loss_streak"] * 8,
                2,
            )
            if best is None or (result["recommended"], result["score"]) > (best["recommended"], best["score"]):
                best = result
    return best or {}


def main() -> None:
    args = parse_args()
    config = load_config()
    requested_symbols = [item.strip().upper() for item in args.symbols.split(",") if item.strip()] or configured_symbols()
    requested_set = set(requested_symbols)
    targets = parse_numbers(args.targets)
    stops = parse_numbers(args.stops)

    signals = load_signals(args)
    if requested_set:
        signals = [signal for signal in signals if signal.symbol.upper() in requested_set]

    market_data = build_m1_market_data(signals, args, config)
    rows: list[dict[str, Any]] = []
    for signal in signals:
        candles = market_data.get((signal.symbol, "M1"), pd.DataFrame())
        row = path_metrics(signal, candles, args)
        if row:
            rows.append(row)

    events = pd.DataFrame(rows)
    output_dir = ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")

    events_path = output_dir / f"operational_target_events_{today}.csv"
    events.to_csv(events_path, index=False)

    latest_path = output_dir / "operational_target_matrix_latest.json"
    previous: dict[str, Any] = {}
    if latest_path.exists():
        try:
            previous = json.loads(latest_path.read_text(encoding="utf-8"))
        except Exception:
            previous = {}

    previous_is_today = str(previous.get("date") or "") == datetime.now().strftime("%Y-%m-%d")
    previous_assets = previous.get("assets", {}) if previous_is_today and isinstance(previous.get("assets"), dict) else {}
    previous_symbols = {str(item).upper() for item in (previous.get("symbols", []) or [])} if previous_is_today else set()

    matrix: dict[str, Any] = {
        "schema": "fusion.operational_target_matrix.v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "source_dates": args.date,
        "lookahead_minutes": args.lookahead_minutes,
        "market_time_offset_hours": args.market_time_offset_hours,
        "decision_filter": args.only_decision,
        "symbols": sorted(previous_symbols | requested_set),
        "assets": dict(previous_assets),
    }

    summary_rows: list[dict[str, Any]] = []
    if not events.empty:
        for (symbol, side), group in events.groupby(["symbol", "side"]):
            clean = pd.to_numeric(group["clean_move_points"], errors="coerce").fillna(0.0).tolist()
            dd = pd.to_numeric(group["drawdown_before_recovery_points"], errors="coerce").fillna(0.0).tolist()
            after = pd.to_numeric(group["move_after_recovery_points"], errors="coerce").fillna(0.0).tolist()
            mfe = pd.to_numeric(group["net_mfe_points"], errors="coerce").fillna(0.0).tolist()
            mae = pd.to_numeric(group["net_mae_points"], errors="coerce").fillna(0.0).tolist()
            spread = pd.to_numeric(group["entry_spread_points"], errors="coerce").fillna(0.0).tolist()
            best = best_tp_sl(group, targets, stops, args) if len(group) >= args.min_samples else {}

            side_data = {
                "samples": int(len(group)),
                "spread_points": asdict(summarize_values(spread)),
                "net_mfe_points": asdict(summarize_values(mfe)),
                "net_mae_points": asdict(summarize_values(mae)),
                "clean_move_points": asdict(summarize_values(clean)),
                "drawdown_before_recovery_points": asdict(summarize_values(dd)),
                "move_after_recovery_points": asdict(summarize_values(after)),
                "recovery_rate": round(float(group["recovered_after_drawdown"].mean() * 100.0), 2),
                "best_tp_sl": best,
            }
            matrix["assets"].setdefault(symbol, {})[side] = side_data
            summary_rows.append(
                {
                    "symbol": symbol,
                    "side": side,
                    "samples": len(group),
                    "spread_median": side_data["spread_points"]["median"],
                    "clean_move_median": side_data["clean_move_points"]["median"],
                    "drawdown_before_recovery_median": side_data["drawdown_before_recovery_points"]["median"],
                    "move_after_recovery_median": side_data["move_after_recovery_points"]["median"],
                    "net_mfe_median": side_data["net_mfe_points"]["median"],
                    "net_mae_median": side_data["net_mae_points"]["median"],
                    "recovery_rate": side_data["recovery_rate"],
                    "tp_net_points": best.get("tp_net_points", ""),
                    "sl_net_points": best.get("sl_net_points", ""),
                    "win_rate": best.get("win_rate", ""),
                    "avg_points": best.get("avg_points", ""),
                    "max_loss_streak": best.get("max_loss_streak", ""),
                    "recommended": best.get("recommended", False),
                }
            )

    matrix_path = output_dir / f"operational_target_matrix_{today}.json"
    summary_path = output_dir / f"operational_target_matrix_{today}.csv"
    matrix_path.write_text(json.dumps(matrix, ensure_ascii=False, indent=2), encoding="utf-8")
    latest_path.write_text(json.dumps(matrix, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(summary_rows).to_csv(summary_path, index=False)

    print(f"Sinais avaliados: {len(signals)}")
    print(f"Eventos validos: {len(events)}")
    print(f"Matriz JSON: {matrix_path}")
    print(f"Matriz latest: {latest_path}")
    print(f"Resumo CSV: {summary_path}")


if __name__ == "__main__":
    main()
