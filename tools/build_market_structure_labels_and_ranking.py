from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_FEATURES = [
    "range_to_atr",
    "range_zscore_20",
    "atr_ratio_5_50",
    "range_contraction",
    "range_expansion",
    "overlap_ratio_10",
    "kaufman_er_10",
    "kaufman_er_20",
    "volatility_compression",
    "volatility_expansion",
    "regime_consolidation",
    "regime_trend",
    "regime_expansion",
    "volume_ratio",
    "volume_zscore",
    "delta_proxy",
    "pressure",
    "pressure_imbalance",
    "price_extension_atr",
    "ema_alignment_buy",
    "ema_alignment_sell",
    "ema21_slope_atr",
    "velocity_atr_10",
    "movement_efficiency",
    "close_position",
    "body_to_range",
    "upper_wick_to_range",
    "lower_wick_to_range",
    "absorption",
    "breakout_up_with_volume",
    "breakout_down_with_volume",
    "break_of_structure_up",
    "break_of_structure_down",
    "change_of_character_up",
    "change_of_character_down",
    "liquidity_grab_up",
    "liquidity_grab_down",
    "distance_to_swing_high_atr",
    "distance_to_swing_low_atr",
    "bars_since_breakout_up",
    "bars_since_breakout_down",
    "bars_since_volume_climax",
    "regime_reversal_risk",
    "hour",
    "day_of_week",
    "session",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cria labels alvo/stop e ranking das features OHLCV.")
    parser.add_argument("--market-structure-dir", default="reports/market_structure")
    parser.add_argument("--parquet-dir", default="data/parquet")
    parser.add_argument("--output-dir", default="reports/market_structure_labels")
    parser.add_argument("--target-points", type=int, default=100)
    parser.add_argument("--stop-points", type=int, default=100)
    parser.add_argument("--tp-sl-report", default="features/features_backteste_ativo_timeframe.csv")
    parser.add_argument("--use-optimized-target-stop", action="store_true")
    parser.add_argument("--use-atr-barriers", action="store_true")
    parser.add_argument("--target-atr-mult", type=float, default=1.5)
    parser.add_argument("--stop-atr-mult", type=float, default=1.0)
    parser.add_argument("--min-dynamic-points", type=int, default=10)
    parser.add_argument("--max-dynamic-points", type=int, default=2000)
    parser.add_argument("--min-stop-points", type=int, default=10)
    parser.add_argument("--max-stop-points", type=int, default=2000)
    parser.add_argument("--max-target-points", type=int, default=2000)
    parser.add_argument("--lookahead", type=int, default=100)
    parser.add_argument("--min-samples", type=int, default=100)
    parser.add_argument("--symbols", nargs="*", default=[])
    parser.add_argument("--timeframes", nargs="*", default=[])
    return parser.parse_args()


def load_tp_sl_map(
    path: Path,
    min_stop_points: int,
    max_stop_points: int,
    max_target_points: int,
) -> tuple[dict[tuple[str, str], tuple[int, int]], pd.DataFrame]:
    if not path.exists():
        return {}, pd.DataFrame()
    frame = pd.read_csv(path)
    result: dict[tuple[str, str], tuple[int, int]] = {}
    rejected = []
    required = {"symbol", "timeframe", "best_target", "stop_sugerido"}
    if not required.issubset(frame.columns):
        return result, pd.DataFrame()
    for _, row in frame.iterrows():
        try:
            target = int(float(row["best_target"]))
            stop = int(float(row["stop_sugerido"]))
        except (TypeError, ValueError):
            continue
        if target <= 0 or stop <= 0:
            continue
        symbol = str(row["symbol"]).upper()
        timeframe = str(row["timeframe"]).upper()
        if stop < min_stop_points or stop > max_stop_points or target > max_target_points:
            rejected.append(
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "best_target": target,
                    "stop_sugerido": stop,
                    "reason": "fora_dos_limites",
                }
            )
            continue
        result[(symbol, timeframe)] = (target, stop)
    return result, pd.DataFrame(rejected)


def infer_symbol_timeframe(path: Path) -> tuple[str, str]:
    name = path.name.replace("_market_structure.csv", "")
    parts = name.split("_")
    if len(parts) < 2:
        return "", ""
    return "_".join(parts[:-1]).upper(), parts[-1].upper()


def load_ohlcv(parquet_dir: Path, symbol: str, timeframe: str) -> pd.DataFrame:
    path = parquet_dir / timeframe / f"{symbol}.parquet"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_parquet(path)
    if "date" in df.columns:
        df["time"] = pd.to_datetime(df["date"])
    elif "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"])
    else:
        return pd.DataFrame()
    df = df.sort_values("time").reset_index(drop=True)
    if "point_value" not in df.columns:
        df["point_value"] = 0.00001
    if "spread" not in df.columns:
        df["spread"] = 0.0
    return df


def first_hit(
    highs: np.ndarray,
    lows: np.ndarray,
    entry: float,
    target: float,
    stop: float,
    side: str,
) -> tuple[str, int, float, float]:
    max_favorable = 0.0
    max_adverse = 0.0
    for pos, (high, low) in enumerate(zip(highs, lows), start=1):
        if side == "buy":
            max_favorable = max(max_favorable, high - entry)
            max_adverse = max(max_adverse, entry - low)
            hit_target = high >= target
            hit_stop = low <= stop
        else:
            max_favorable = max(max_favorable, entry - low)
            max_adverse = max(max_adverse, high - entry)
            hit_target = low <= target
            hit_stop = high >= stop
        if hit_target and hit_stop:
            return "both_same_candle", pos, max_favorable, max_adverse
        if hit_target:
            return "target", pos, max_favorable, max_adverse
        if hit_stop:
            return "stop", pos, max_favorable, max_adverse
    return "timeout", len(highs), max_favorable, max_adverse


def build_labels_for_file(
    feature_path: Path,
    parquet_dir: Path,
    target_points: int,
    stop_points: int,
    lookahead: int,
    use_atr_barriers: bool = False,
    target_atr_mult: float = 1.5,
    stop_atr_mult: float = 1.0,
    min_dynamic_points: int = 10,
    max_dynamic_points: int = 2000,
) -> pd.DataFrame:
    symbol, timeframe = infer_symbol_timeframe(feature_path)
    if not symbol or not timeframe:
        return pd.DataFrame()
    features = pd.read_csv(feature_path)
    if features.empty or "time" not in features.columns:
        return pd.DataFrame()
    features["time"] = pd.to_datetime(features["time"])
    ohlcv = load_ohlcv(parquet_dir, symbol, timeframe)
    if ohlcv.empty:
        return pd.DataFrame()
    base_cols = ["time", "open", "high", "low", "close", "spread", "point_value"]
    merged = features.merge(ohlcv[base_cols], on="time", how="inner", suffixes=("", "_ohlcv"))
    if merged.empty:
        return pd.DataFrame()

    highs = ohlcv["high"].astype(float).to_numpy()
    lows = ohlcv["low"].astype(float).to_numpy()
    time_to_idx = {value: idx for idx, value in enumerate(ohlcv["time"])}
    rows = []

    for _, row in merged.iterrows():
        idx = time_to_idx.get(row["time"])
        if idx is None or idx + 1 >= len(ohlcv):
            continue
        end = min(len(ohlcv), idx + 1 + lookahead)
        future_highs = highs[idx + 1:end]
        future_lows = lows[idx + 1:end]
        if len(future_highs) == 0:
            continue

        point = float(row.get("point_value", 0.00001) or 0.00001)
        spread_points = float(row.get("spread", 0.0) or 0.0)
        close = float(row["close"])
        effective_target_points = int(target_points)
        effective_stop_points = int(stop_points)
        label_mode = "fixed"
        if use_atr_barriers:
            try:
                atr = float(row.get("atr", np.nan))
            except (TypeError, ValueError):
                atr = np.nan
            if np.isfinite(atr) and atr > 0 and point > 0:
                effective_target_points = int(round((atr * target_atr_mult) / point))
                effective_stop_points = int(round((atr * stop_atr_mult) / point))
                effective_target_points = max(min_dynamic_points, min(max_dynamic_points, effective_target_points))
                effective_stop_points = max(min_dynamic_points, min(max_dynamic_points, effective_stop_points))
                label_mode = "atr_dynamic"
            else:
                label_mode = "atr_fallback_fixed"
        buy_entry = close + (spread_points * point)
        sell_entry = close
        buy_result, buy_bars, buy_mfe, buy_mae = first_hit(
            future_highs,
            future_lows,
            buy_entry,
            buy_entry + effective_target_points * point,
            buy_entry - effective_stop_points * point,
            "buy",
        )
        sell_result, sell_bars, sell_mfe, sell_mae = first_hit(
            future_highs,
            future_lows,
            sell_entry,
            sell_entry - effective_target_points * point,
            sell_entry + effective_stop_points * point,
            "sell",
        )

        out = row.to_dict()
        out["symbol"] = symbol
        out["timeframe"] = timeframe
        out["target_points"] = effective_target_points
        out["stop_points"] = effective_stop_points
        out["label_mode"] = label_mode
        out["lookahead"] = lookahead
        out["buy_result"] = buy_result
        out["buy_target_before_stop"] = int(buy_result == "target")
        out["buy_bars_to_event"] = buy_bars
        out["buy_mfe_points"] = buy_mfe / point
        out["buy_mae_points"] = buy_mae / point
        out["sell_result"] = sell_result
        out["sell_target_before_stop"] = int(sell_result == "target")
        out["sell_bars_to_event"] = sell_bars
        out["sell_mfe_points"] = sell_mfe / point
        out["sell_mae_points"] = sell_mae / point
        rows.append(out)

    return pd.DataFrame(rows)


def bucket_numeric(series: pd.Series) -> pd.Series:
    clean = series.replace([np.inf, -np.inf], np.nan)
    if clean.nunique(dropna=True) <= 2:
        return clean.astype(str)
    try:
        return pd.qcut(clean, q=4, duplicates="drop").astype(str)
    except ValueError:
        return clean.round(4).astype(str)


def build_feature_ranking(labels: pd.DataFrame, min_samples: int) -> pd.DataFrame:
    rows = []
    if labels.empty:
        return pd.DataFrame()
    available = [feature for feature in DEFAULT_FEATURES if feature in labels.columns]
    for feature in available:
        feature_values = labels[feature].replace([np.inf, -np.inf], np.nan)
        valid_mask = feature_values.notna()
        if not valid_mask.any():
            continue
        if pd.api.types.is_numeric_dtype(feature_values):
            buckets = bucket_numeric(feature_values)
        else:
            buckets = feature_values.astype(str)
        for side, target_col, bars_col, mfe_col, mae_col in [
            ("buy", "buy_target_before_stop", "buy_bars_to_event", "buy_mfe_points", "buy_mae_points"),
            ("sell", "sell_target_before_stop", "sell_bars_to_event", "sell_mfe_points", "sell_mae_points"),
        ]:
            temp = labels.loc[valid_mask, ["symbol", "timeframe", target_col, bars_col, mfe_col, mae_col]].copy()
            temp["bucket"] = buckets.loc[valid_mask]
            temp = temp[temp["bucket"].astype(str).str.lower() != "nan"]
            if temp.empty:
                continue
            grouped = temp.groupby(["symbol", "timeframe", "bucket"], dropna=False)
            for (symbol, timeframe, bucket), group in grouped:
                samples = len(group)
                if samples < min_samples:
                    continue
                rows.append(
                    {
                        "feature": feature,
                        "side": side,
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "bucket": str(bucket),
                        "samples": samples,
                        "win_rate": float(group[target_col].mean()),
                        "avg_bars_to_event": float(group[bars_col].mean()),
                        "avg_mfe_points": float(group[mfe_col].mean()),
                        "avg_mae_points": float(group[mae_col].mean()),
                        "edge_score": float((group[target_col].mean() - 0.5) * np.log1p(samples)),
                    }
                )
    ranking = pd.DataFrame(rows)
    if ranking.empty:
        return ranking
    return ranking.sort_values(["edge_score", "samples"], ascending=[False, False])


def main() -> None:
    args = parse_args()
    market_dir = Path(args.market_structure_dir)
    parquet_dir = Path(args.parquet_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    symbols = {item.upper() for item in args.symbols}
    timeframes = {item.upper() for item in args.timeframes}
    tp_sl_map = {}
    rejected_tp_sl = pd.DataFrame()
    if args.use_optimized_target_stop:
        report_path = Path(args.tp_sl_report)
        if not report_path.is_absolute():
            report_path = Path.cwd() / report_path
        tp_sl_map, rejected_tp_sl = load_tp_sl_map(
            report_path,
            min_stop_points=args.min_stop_points,
            max_stop_points=args.max_stop_points,
            max_target_points=args.max_target_points,
        )

    label_frames = []
    files = sorted(market_dir.glob("*_market_structure.csv"))
    for path in files:
        symbol, timeframe = infer_symbol_timeframe(path)
        if symbols and symbol not in symbols:
            continue
        if timeframes and timeframe not in timeframes:
            continue
        target_points = args.target_points
        stop_points = args.stop_points
        if args.use_optimized_target_stop:
            target_points, stop_points = tp_sl_map.get((symbol, timeframe), (args.target_points, args.stop_points))
        labels = build_labels_for_file(
            path,
            parquet_dir,
            target_points=target_points,
            stop_points=stop_points,
            lookahead=args.lookahead,
            use_atr_barriers=args.use_atr_barriers,
            target_atr_mult=args.target_atr_mult,
            stop_atr_mult=args.stop_atr_mult,
            min_dynamic_points=args.min_dynamic_points,
            max_dynamic_points=args.max_dynamic_points,
        )
        if labels.empty:
            print(f"[SKIP] {symbol} {timeframe}")
            continue
        label_frames.append(labels)
        if args.use_atr_barriers:
            mode_counts = labels["label_mode"].value_counts().to_dict()
            print(
                f"[OK] {symbol} {timeframe}: labels={len(labels)} "
                f"atr_tp={args.target_atr_mult:g} atr_sl={args.stop_atr_mult:g} modes={mode_counts}"
            )
        else:
            print(f"[OK] {symbol} {timeframe}: labels={len(labels)} tp={target_points} sl={stop_points}")

    all_labels = pd.concat(label_frames, ignore_index=True) if label_frames else pd.DataFrame()
    if args.use_atr_barriers:
        suffix = f"atr{args.target_atr_mult:g}_slatr{args.stop_atr_mult:g}_lh{args.lookahead}"
    elif args.use_optimized_target_stop:
        suffix = f"optimized_lh{args.lookahead}"
    else:
        suffix = f"tp{args.target_points}_sl{args.stop_points}_lh{args.lookahead}"
    labels_path = output_dir / f"market_structure_labels_{suffix}.csv"
    ranking_path = output_dir / f"market_structure_feature_ranking_{suffix}.csv"
    all_labels.to_csv(labels_path, index=False)
    ranking = build_feature_ranking(all_labels, args.min_samples)
    ranking.to_csv(ranking_path, index=False)
    if not rejected_tp_sl.empty:
        rejected_tp_sl.to_csv(output_dir / f"market_structure_rejected_tp_sl_{suffix}.csv", index=False)

    summary = {
        "label_rows": int(len(all_labels)),
        "ranking_rows": int(len(ranking)),
        "target_points": args.target_points,
        "stop_points": args.stop_points,
        "use_atr_barriers": bool(args.use_atr_barriers),
        "target_atr_mult": args.target_atr_mult,
        "stop_atr_mult": args.stop_atr_mult,
        "min_dynamic_points": args.min_dynamic_points,
        "max_dynamic_points": args.max_dynamic_points,
        "optimized_target_stop": bool(args.use_optimized_target_stop),
        "tp_sl_report": str(args.tp_sl_report),
        "min_stop_points": args.min_stop_points,
        "max_stop_points": args.max_stop_points,
        "max_target_points": args.max_target_points,
        "rejected_tp_sl_rows": int(len(rejected_tp_sl)),
        "lookahead": args.lookahead,
        "labels_path": str(labels_path),
        "ranking_path": str(ranking_path),
    }
    pd.Series(summary).to_json(output_dir / f"market_structure_label_summary_{suffix}.json", indent=2)
    print(f"Labels: {labels_path}")
    print(f"Ranking: {ranking_path}")
    print(f"Linhas labels: {len(all_labels)} | ranking: {len(ranking)}")


if __name__ == "__main__":
    main()
