from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cruza eventos Market Structure shadow com labels alvo/stop para medir impacto posterior."
    )
    parser.add_argument("--log-dir", default="logs/market_structure_shadow")
    parser.add_argument("--date", default="", help="Data YYYYMMDD. Se vazio, le todos os logs shadow.")
    parser.add_argument(
        "--labels",
        default="reports/market_structure_labels/market_structure_labels_optimized_lh100.csv",
    )
    parser.add_argument("--output-dir", default="reports/market_structure_shadow_outcomes")
    parser.add_argument("--chunk-size", type=int, default=250000)
    return parser.parse_args()


def iter_events(log_dir: Path, date: str):
    pattern = f"market_structure_shadow_{date}.jsonl" if date else "market_structure_shadow_*.jsonl"
    for path in sorted(log_dir.glob(pattern)):
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                event["_source_file"] = path.name
                yield event


def load_events(log_dir: Path, date: str) -> pd.DataFrame:
    rows = []
    for event in iter_events(log_dir, date):
        signal_time = event.get("signal_candle_time") or ""
        rows.append(
            {
                "event_id": len(rows),
                "timestamp": event.get("timestamp", ""),
                "signal_candle_time": signal_time,
                "strategy": event.get("strategy", ""),
                "symbol": str(event.get("symbol", "")).upper(),
                "broker_symbol": event.get("broker_symbol", ""),
                "timeframe": str(event.get("timeframe", "")).upper(),
                "prediction": int(event.get("prediction", 0) or 0),
                "mode": event.get("mode", ""),
                "aggregate_score": float(event.get("aggregate_score", 0.0) or 0.0),
                "reasons": ";".join(str(item) for item in event.get("reasons") or ["ok"]),
                "source_file": event.get("_source_file", ""),
            }
        )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    frame["signal_candle_time"] = pd.to_datetime(frame["signal_candle_time"], errors="coerce")
    return frame


def load_matching_labels(labels_path: Path, event_keys: pd.DataFrame, chunk_size: int) -> pd.DataFrame:
    if event_keys.empty or not labels_path.exists():
        return pd.DataFrame()

    keys = {
        (row.symbol, row.timeframe, row.signal_candle_time)
        for row in event_keys.itertuples(index=False)
        if pd.notna(row.signal_candle_time)
    }
    if not keys:
        return pd.DataFrame()

    usecols = [
        "symbol",
        "timeframe",
        "time",
        "target_points",
        "stop_points",
        "lookahead",
        "buy_result",
        "buy_target_before_stop",
        "buy_bars_to_event",
        "buy_mfe_points",
        "buy_mae_points",
        "sell_result",
        "sell_target_before_stop",
        "sell_bars_to_event",
        "sell_mfe_points",
        "sell_mae_points",
    ]
    matches = []
    for chunk in pd.read_csv(labels_path, usecols=usecols, chunksize=chunk_size):
        chunk["symbol"] = chunk["symbol"].astype(str).str.upper()
        chunk["timeframe"] = chunk["timeframe"].astype(str).str.upper()
        chunk["time"] = pd.to_datetime(chunk["time"], errors="coerce")
        mask = [
            (symbol, timeframe, time_value) in keys
            for symbol, timeframe, time_value in zip(chunk["symbol"], chunk["timeframe"], chunk["time"])
        ]
        if any(mask):
            matches.append(chunk.loc[mask].copy())
    if not matches:
        return pd.DataFrame()
    return pd.concat(matches, ignore_index=True).drop_duplicates(["symbol", "timeframe", "time"])


def attach_outcomes(events: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return events
    valid_events = events.dropna(subset=["signal_candle_time"]).copy()
    if labels.empty or valid_events.empty:
        out = events.copy()
        out["label_matched"] = False
        return out

    merged = valid_events.merge(
        labels,
        left_on=["symbol", "timeframe", "signal_candle_time"],
        right_on=["symbol", "timeframe", "time"],
        how="left",
    )
    merged["label_matched"] = merged["time"].notna()
    is_buy = merged["prediction"].eq(1)
    is_sell = merged["prediction"].eq(2)
    merged["side"] = "NEUTRO"
    merged.loc[is_buy, "side"] = "BUY"
    merged.loc[is_sell, "side"] = "SELL"
    merged["target_before_stop"] = pd.NA
    merged.loc[is_buy, "target_before_stop"] = merged.loc[is_buy, "buy_target_before_stop"]
    merged.loc[is_sell, "target_before_stop"] = merged.loc[is_sell, "sell_target_before_stop"]
    merged["result"] = ""
    merged.loc[is_buy, "result"] = merged.loc[is_buy, "buy_result"].fillna("")
    merged.loc[is_sell, "result"] = merged.loc[is_sell, "sell_result"].fillna("")
    merged["bars_to_event"] = pd.NA
    merged.loc[is_buy, "bars_to_event"] = merged.loc[is_buy, "buy_bars_to_event"]
    merged.loc[is_sell, "bars_to_event"] = merged.loc[is_sell, "sell_bars_to_event"]
    merged["mfe_points"] = pd.NA
    merged.loc[is_buy, "mfe_points"] = merged.loc[is_buy, "buy_mfe_points"]
    merged.loc[is_sell, "mfe_points"] = merged.loc[is_sell, "sell_mfe_points"]
    merged["mae_points"] = pd.NA
    merged.loc[is_buy, "mae_points"] = merged.loc[is_buy, "buy_mae_points"]
    merged.loc[is_sell, "mae_points"] = merged.loc[is_sell, "sell_mae_points"]
    for col in ["target_before_stop", "bars_to_event", "mfe_points", "mae_points"]:
        merged[col] = pd.to_numeric(merged[col], errors="coerce")

    missing_time_events = events[events["signal_candle_time"].isna()].copy()
    if missing_time_events.empty:
        return merged
    missing_time_events["label_matched"] = False
    missing_time_events["side"] = ""
    missing_time_events["target_before_stop"] = pd.NA
    missing_time_events["result"] = ""
    missing_time_events["bars_to_event"] = pd.NA
    missing_time_events["mfe_points"] = pd.NA
    missing_time_events["mae_points"] = pd.NA
    return pd.concat([merged, missing_time_events], ignore_index=True, sort=False)


def summarize_by_reason(outcomes: pd.DataFrame) -> pd.DataFrame:
    if outcomes.empty or "target_before_stop" not in outcomes.columns:
        return pd.DataFrame()
    rows = []
    matched = outcomes[outcomes["label_matched"].eq(True)].copy()
    for row in matched.itertuples(index=False):
        for reason in str(row.reasons or "ok").split(";"):
            rows.append(
                {
                    "reason": reason or "ok",
                    "target_before_stop": row.target_before_stop,
                    "aggregate_score": row.aggregate_score,
                    "bars_to_event": row.bars_to_event,
                    "mfe_points": row.mfe_points,
                    "mae_points": row.mae_points,
                }
            )
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows)
    for col in ["target_before_stop", "aggregate_score", "bars_to_event", "mfe_points", "mae_points"]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    grouped = (
        frame.groupby("reason", dropna=False)
        .agg(
            events=("target_before_stop", "size"),
            win_rate=("target_before_stop", "mean"),
            avg_score=("aggregate_score", "mean"),
            avg_bars_to_event=("bars_to_event", "mean"),
            avg_mfe_points=("mfe_points", "mean"),
            avg_mae_points=("mae_points", "mean"),
        )
        .reset_index()
    )
    return grouped.sort_values(["events", "win_rate"], ascending=[False, False])


def summarize_by_score(outcomes: pd.DataFrame) -> pd.DataFrame:
    if outcomes.empty or "target_before_stop" not in outcomes.columns:
        return pd.DataFrame()
    matched = outcomes[outcomes["label_matched"].eq(True)].copy()
    if matched.empty:
        return pd.DataFrame()
    matched["score_bucket"] = pd.cut(
        matched["aggregate_score"],
        bins=[-0.01, 0.20, 0.40, 0.60, 0.80, 1.00],
        labels=["0.00-0.20", "0.21-0.40", "0.41-0.60", "0.61-0.80", "0.81-1.00"],
    )
    return (
        matched.groupby("score_bucket", observed=False)
        .agg(
            events=("target_before_stop", "size"),
            win_rate=("target_before_stop", "mean"),
            avg_mfe_points=("mfe_points", "mean"),
            avg_mae_points=("mae_points", "mean"),
        )
        .reset_index()
    )


def write_report(path: Path, outcomes: pd.DataFrame, reason_df: pd.DataFrame, score_df: pd.DataFrame) -> None:
    lines = ["# Market Structure Shadow Outcomes", ""]
    if outcomes.empty:
        lines.append("Nenhum evento shadow encontrado.")
        path.write_text("\n".join(lines), encoding="utf-8")
        return
    matched = int(outcomes.get("label_matched", pd.Series(dtype=bool)).sum())
    with_time = int(outcomes["signal_candle_time"].notna().sum()) if "signal_candle_time" in outcomes.columns else 0
    lines.extend(
        [
            f"- Eventos shadow: {len(outcomes)}",
            f"- Eventos com candle_time: {with_time}",
            f"- Eventos cruzados com labels: {matched}",
            "",
        ]
    )
    if matched == 0:
        lines.extend(
            [
                "Ainda nao ha eventos suficientes com `signal_candle_time` cruzando com os labels.",
                "Deixe o sistema rodar com a nova versao do shadow log e regenere labels/features quando necessario.",
            ]
        )
        path.write_text("\n".join(lines), encoding="utf-8")
        return

    matched_df = outcomes[outcomes["label_matched"].eq(True)]
    lines.append(f"- Win rate posterior geral: {matched_df['target_before_stop'].mean():.2%}")
    lines.extend(["", "## Por motivo", ""])
    for _, row in reason_df.head(30).iterrows():
        lines.append(
            f"- {row['reason']}: eventos={int(row['events'])}, win_rate={row['win_rate']:.2%}, "
            f"score={row['avg_score']:.3f}, mfe={row['avg_mfe_points']:.1f}, mae={row['avg_mae_points']:.1f}"
        )
    if not score_df.empty:
        lines.extend(["", "## Por score", ""])
        for _, row in score_df.iterrows():
            lines.append(
                f"- {row['score_bucket']}: eventos={int(row['events'])}, "
                f"win_rate={row['win_rate']:.2%}, mfe={row['avg_mfe_points']:.1f}, mae={row['avg_mae_points']:.1f}"
            )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    events = load_events(Path(args.log_dir), args.date)
    labels = load_matching_labels(Path(args.labels), events, args.chunk_size)
    outcomes = attach_outcomes(events, labels)
    reason_df = summarize_by_reason(outcomes)
    score_df = summarize_by_score(outcomes)

    suffix = args.date if args.date else "all"
    outcomes.to_csv(output_dir / f"market_structure_shadow_outcomes_{suffix}.csv", index=False)
    reason_df.to_csv(output_dir / f"market_structure_shadow_outcomes_by_reason_{suffix}.csv", index=False)
    score_df.to_csv(output_dir / f"market_structure_shadow_outcomes_by_score_{suffix}.csv", index=False)
    write_report(output_dir / f"market_structure_shadow_outcomes_{suffix}.md", outcomes, reason_df, score_df)

    matched = int(outcomes.get("label_matched", pd.Series(dtype=bool)).sum()) if not outcomes.empty else 0
    print(f"Eventos: {len(outcomes)} | cruzados: {matched}")
    print(f"Saida: {output_dir}")


if __name__ == "__main__":
    main()
