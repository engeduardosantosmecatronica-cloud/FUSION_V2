from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

from analyze_signal_outcomes import (
    ROOT,
    TIMEFRAME_MINUTES,
    Signal,
    build_market_data,
    load_config,
    load_signals,
    parse_time,
    point_size,
    signal_market_time,
)


PATH_TIMEFRAME_BY_SIGNAL = {
    "M15": "M1",
    "H1": "M1",
    "H4": "M1",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Avalia sinais pela trajetoria intraperiodo: MFE/MAE, fechamento da janela "
            "e alvos atingidos antes de devolver."
        )
    )
    parser.add_argument("--date", action="append", required=True, help="Data YYYYMMDD. Pode repetir.")
    parser.add_argument("--audit-dir", default="logs/decision_audit")
    parser.add_argument("--output-dir", default="reports/signal_path_outcomes")
    parser.add_argument("--timeframe", action="append", default=[], help="Filtra timeframes. Pode repetir.")
    parser.add_argument("--start", default="", help="Inicio Fusion time: YYYY-MM-DD HH:MM[:SS].")
    parser.add_argument("--end", default="", help="Fim Fusion time: YYYY-MM-DD HH:MM[:SS].")
    parser.add_argument("--only-decision", default="", help="Ex.: ALLOW ou BLOCK. Vazio analisa todos.")
    parser.add_argument("--since-hours", type=float, default=0.0)
    parser.add_argument("--market-time-offset-hours", type=float, default=0.0)
    parser.add_argument("--use-mt5", action="store_true")
    parser.add_argument("--save-mt5-history", action="store_true")
    parser.add_argument("--max-signals", type=int, default=0)
    parser.add_argument(
        "--windows",
        default="0.25,0.5,1,2,3",
        help="Janelas como multiplos do timeframe do sinal. Ex.: H4 com 0.25 = 1h.",
    )
    parser.add_argument("--targets", default="30,50,100", help="Alvos em pontos, separados por virgula.")
    return parser.parse_args()


def parse_float_list(value: str) -> list[float]:
    result: list[float] = []
    for item in str(value or "").split(","):
        item = item.strip()
        if not item:
            continue
        result.append(float(item))
    return result


def build_path_data(signals: list[Signal], args: argparse.Namespace, config: dict[str, Any]) -> dict[tuple[str, str], pd.DataFrame]:
    path_signals: list[Signal] = []
    for signal in signals:
        path_tf = PATH_TIMEFRAME_BY_SIGNAL.get(signal.timeframe, signal.timeframe)
        path_signals.append(
            Signal(
                correlation_id=signal.correlation_id,
                timestamp=signal.timestamp,
                symbol=signal.symbol,
                timeframe=path_tf,
                strategy=signal.strategy,
                side=signal.side,
                p_buy=signal.p_buy,
                p_sell=signal.p_sell,
                decision=signal.decision,
                reason=signal.reason,
            )
        )
    return build_market_data(path_signals, args, config)


def target_hit_info(
    future: pd.DataFrame,
    side: str,
    entry_price: float,
    point: float,
    target_points: float,
) -> dict[str, Any]:
    if future.empty or not point:
        return {"hit": False, "adverse_hit": False, "first": "", "time": ""}

    target = target_points * point
    for _, candle in future.iterrows():
        high = float(candle["high"])
        low = float(candle["low"])
        when = pd.Timestamp(candle["date"]).isoformat()
        if side == "BUY":
            hit_target = high >= entry_price + target
            hit_adverse = low <= entry_price - target
        else:
            hit_target = low <= entry_price - target
            hit_adverse = high >= entry_price + target

        if hit_target and hit_adverse:
            return {"hit": True, "adverse_hit": True, "first": "same_candle", "time": when}
        if hit_target:
            return {"hit": True, "adverse_hit": False, "first": "target", "time": when}
        if hit_adverse:
            return {"hit": False, "adverse_hit": True, "first": "adverse", "time": when}

    return {"hit": False, "adverse_hit": False, "first": "", "time": ""}


def candle_spread_points(candle: pd.Series) -> float:
    try:
        value = float(candle.get("spread", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, value)


def target_hit_info_net(
    future: pd.DataFrame,
    side: str,
    entry_bid: float,
    entry_ask: float,
    point: float,
    target_points: float,
) -> dict[str, Any]:
    if future.empty or not point:
        return {"hit": False, "adverse_hit": False, "first": "", "time": ""}

    target = target_points * point
    for _, candle in future.iterrows():
        spread_price = candle_spread_points(candle) * point
        high_bid = float(candle["high"])
        low_bid = float(candle["low"])
        high_ask = high_bid + spread_price
        low_ask = low_bid + spread_price
        when = pd.Timestamp(candle["date"]).isoformat()

        if side == "BUY":
            hit_target = high_bid >= entry_ask + target
            hit_adverse = low_bid <= entry_ask - target
        else:
            hit_target = low_ask <= entry_bid - target
            hit_adverse = high_ask >= entry_bid + target

        if hit_target and hit_adverse:
            return {"hit": True, "adverse_hit": True, "first": "same_candle", "time": when}
        if hit_target:
            return {"hit": True, "adverse_hit": False, "first": "target", "time": when}
        if hit_adverse:
            return {"hit": False, "adverse_hit": True, "first": "adverse", "time": when}

    return {"hit": False, "adverse_hit": False, "first": "", "time": ""}


def evaluate_paths(
    signals: list[Signal],
    market_data: dict[tuple[str, str], pd.DataFrame],
    windows: list[float],
    targets: list[float],
    args: argparse.Namespace,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for signal in signals:
        path_tf = PATH_TIMEFRAME_BY_SIGNAL.get(signal.timeframe, signal.timeframe)
        candles = market_data.get((signal.symbol, path_tf), pd.DataFrame())
        market_timestamp = signal_market_time(signal.timestamp, args)
        base = {
            "timestamp": signal.timestamp.isoformat(),
            "market_timestamp": market_timestamp.isoformat(),
            "symbol": signal.symbol,
            "signal_timeframe": signal.timeframe,
            "path_timeframe": path_tf,
            "strategy": signal.strategy,
            "side": signal.side,
            "p_buy": signal.p_buy,
            "p_sell": signal.p_sell,
            "decision": signal.decision,
            "reason": signal.reason,
            "correlation_id": signal.correlation_id,
        }

        if candles.empty:
            rows.append({**base, "status": "sem_historico"})
            continue

        idx = candles["date"].searchsorted(market_timestamp, side="right")
        if idx >= len(candles):
            rows.append({**base, "status": "sem_candle_posterior", "history_last": candles["date"].max().isoformat()})
            continue

        entry = candles.iloc[idx]
        entry_time = pd.Timestamp(entry["date"])
        entry_price = float(entry["open"])
        point = point_size(signal.symbol, candles)
        entry_spread_points = candle_spread_points(entry)
        entry_spread_price = entry_spread_points * point
        entry_bid = entry_price
        entry_ask = entry_price + entry_spread_price
        row = {
            **base,
            "status": "ok",
            "entry_time": entry_time.isoformat(),
            "entry_bid": entry_bid,
            "entry_ask": entry_ask,
            "entry_price": entry_price,
            "point_size": point,
            "entry_spread_points": entry_spread_points,
        }

        for window in windows:
            minutes = TIMEFRAME_MINUTES[signal.timeframe] * window
            window_label = str(window).replace(".", "p")
            window_end = entry_time + pd.Timedelta(minutes=minutes)
            future = candles[(candles["date"] >= entry_time) & (candles["date"] <= window_end)]
            if future.empty:
                row[f"w{window_label}_status"] = "sem_candle"
                continue

            future_spread_price = pd.to_numeric(future.get("spread", 0.0), errors="coerce").fillna(0.0).clip(lower=0.0) * point
            high_bid = future["high"].astype(float)
            low_bid = future["low"].astype(float)
            close_bid = float(future.iloc[-1]["close"])
            high_ask = high_bid + future_spread_price
            low_ask = low_bid + future_spread_price
            close_ask = close_bid + float(future_spread_price.iloc[-1])

            if signal.side == "BUY":
                mfe_price = float(high_bid.max()) - entry_price
                mae_price = entry_price - float(low_bid.min())
                close_delta = close_bid - entry_price
                net_mfe_price = float(high_bid.max()) - entry_ask
                net_mae_price = entry_ask - float(low_bid.min())
                net_close_delta = close_bid - entry_ask
            else:
                mfe_price = entry_price - float(low_bid.min())
                mae_price = float(high_bid.max()) - entry_price
                close_delta = entry_price - close_bid
                net_mfe_price = entry_bid - float(low_ask.min())
                net_mae_price = float(high_ask.max()) - entry_bid
                net_close_delta = entry_bid - close_ask

            row[f"w{window_label}_end"] = window_end.isoformat()
            row[f"w{window_label}_candles"] = len(future)
            row[f"w{window_label}_mfe_points"] = round(float(mfe_price / point), 2) if point else ""
            row[f"w{window_label}_mae_points"] = round(float(mae_price / point), 2) if point else ""
            row[f"w{window_label}_close_points"] = round(float(close_delta / point), 2) if point else ""
            row[f"w{window_label}_close_positive"] = bool(close_delta > 0)
            row[f"w{window_label}_net_mfe_points"] = round(float(net_mfe_price / point), 2) if point else ""
            row[f"w{window_label}_net_mae_points"] = round(float(net_mae_price / point), 2) if point else ""
            row[f"w{window_label}_net_close_points"] = round(float(net_close_delta / point), 2) if point else ""
            row[f"w{window_label}_net_close_positive"] = bool(net_close_delta > 0)

            for target in targets:
                target_label = str(target).replace(".", "p")
                info = target_hit_info(future, signal.side, entry_price, point, target)
                row[f"w{window_label}_t{target_label}_hit"] = info["hit"]
                row[f"w{window_label}_t{target_label}_adverse_hit"] = info["adverse_hit"]
                row[f"w{window_label}_t{target_label}_first"] = info["first"]
                row[f"w{window_label}_t{target_label}_time"] = info["time"]
                net_info = target_hit_info_net(future, signal.side, entry_bid, entry_ask, point, target)
                row[f"w{window_label}_t{target_label}_net_hit"] = net_info["hit"]
                row[f"w{window_label}_t{target_label}_net_adverse_hit"] = net_info["adverse_hit"]
                row[f"w{window_label}_t{target_label}_net_first"] = net_info["first"]
                row[f"w{window_label}_t{target_label}_net_time"] = net_info["time"]

        rows.append(row)

    return pd.DataFrame(rows)


def summarize(df: pd.DataFrame, output: Path, windows: list[float], targets: list[float]) -> None:
    lines = ["# Signal Path Outcomes", ""]
    lines.append(f"- Sinais avaliados: {len(df)}")
    ok = df[df["status"].eq("ok")] if "status" in df else pd.DataFrame()
    lines.append(f"- Com candle posterior: {len(ok)}")
    lines.append(f"- Sem historico/candle posterior: {len(df) - len(ok)}")

    if ok.empty:
        output.write_text("\n".join(lines), encoding="utf-8")
        return

    lines.extend(["", "## Fechamento e Trajetoria por Janela", ""])
    for window in windows:
        label = str(window).replace(".", "p")
        close_col = f"w{label}_close_positive"
        mfe_col = f"w{label}_mfe_points"
        mae_col = f"w{label}_mae_points"
        net_close_col = f"w{label}_net_close_positive"
        net_mfe_col = f"w{label}_net_mfe_points"
        net_mae_col = f"w{label}_net_mae_points"
        valid = ok[ok[close_col].isin([True, False])] if close_col in ok else pd.DataFrame()
        if valid.empty:
            continue
        close_acc = float(valid[close_col].mean() * 100)
        mfe_med = float(pd.to_numeric(valid[mfe_col], errors="coerce").median())
        mae_med = float(pd.to_numeric(valid[mae_col], errors="coerce").median())
        net_close_acc = float(valid[net_close_col].mean() * 100) if net_close_col in valid else close_acc
        net_mfe_med = float(pd.to_numeric(valid[net_mfe_col], errors="coerce").median()) if net_mfe_col in valid else mfe_med
        net_mae_med = float(pd.to_numeric(valid[net_mae_col], errors="coerce").median()) if net_mae_col in valid else mae_med
        target_parts = []
        for target in targets:
            target_label = str(target).replace(".", "p")
            hit_col = f"w{label}_t{target_label}_hit"
            net_hit_col = f"w{label}_t{target_label}_net_hit"
            if hit_col in valid:
                part = f"T{target:g}={valid[hit_col].mean() * 100:.1f}%"
                if net_hit_col in valid:
                    part += f"/net {valid[net_hit_col].mean() * 100:.1f}%"
                target_parts.append(part)
        lines.append(
            f"- W {window:g}xTF: fechamento positivo {close_acc:.1f}% | "
            f"MFE med {mfe_med:.1f} pts | MAE med {mae_med:.1f} pts"
            f" | net fechamento {net_close_acc:.1f}% | net MFE med {net_mfe_med:.1f} pts | net MAE med {net_mae_med:.1f} pts"
            + (f" | {' | '.join(target_parts)}" if target_parts else "")
        )

    lines.extend(["", "## Por Timeframe", ""])
    for timeframe, group in ok.groupby("signal_timeframe"):
        parts = [f"{timeframe}: {len(group)} sinais"]
        for window in windows[:3]:
            label = str(window).replace(".", "p")
            close_col = f"w{label}_close_positive"
            if close_col in group:
                valid = group[group[close_col].isin([True, False])]
                if not valid.empty:
                    parts.append(f"W{window:g}={valid[close_col].mean() * 100:.1f}%")
        lines.append("- " + " | ".join(parts))

    output.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    windows = parse_float_list(args.windows)
    targets = parse_float_list(args.targets)
    config = load_config()
    signals = load_signals(args)
    max_window = max(windows or [1.0])
    max_path_candles = 1
    for signal in signals:
        path_tf = PATH_TIMEFRAME_BY_SIGNAL.get(signal.timeframe, signal.timeframe)
        max_path_candles = max(
            max_path_candles,
            int((TIMEFRAME_MINUTES[signal.timeframe] * max_window) / TIMEFRAME_MINUTES[path_tf]) + 10,
        )
    args.horizons = str(max_path_candles)
    market_data = build_path_data(signals, args, config)
    df = evaluate_paths(signals, market_data, windows, targets, args)

    output_dir = ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    label = "_".join(args.date)
    if args.start or args.end:
        start_label = str(args.start or "start").replace(":", "").replace(" ", "_").replace("-", "")
        end_label = str(args.end or "end").replace(":", "").replace(" ", "_").replace("-", "")
        label += f"_{start_label}_to_{end_label}"
    if args.market_time_offset_hours:
        label += f"_mt5offset{args.market_time_offset_hours:g}h"
    if args.timeframe:
        tf_label = "_".join(str(item).upper().strip() for item in args.timeframe if str(item).strip())
        if tf_label:
            label += f"_{tf_label}"
    label += "_path"

    csv_path = output_dir / f"signal_path_outcomes_{label}.csv"
    md_path = output_dir / f"signal_path_outcomes_{label}.md"
    df.to_csv(csv_path, index=False)
    summarize(df, md_path, windows, targets)
    print(f"Sinais: {len(signals)}")
    print(f"Saida CSV: {csv_path}")
    print(f"Resumo: {md_path}")


if __name__ == "__main__":
    main()
