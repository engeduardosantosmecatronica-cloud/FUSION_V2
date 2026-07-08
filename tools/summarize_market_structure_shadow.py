from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resume logs JSONL do Market Structure shadow mode.")
    parser.add_argument("--log-dir", default="logs/market_structure_shadow")
    parser.add_argument("--output-dir", default="reports/market_structure_shadow")
    parser.add_argument("--date", default="", help="Data YYYYMMDD. Se vazio, le todos os arquivos.")
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


def flatten_events(events: list[dict]) -> pd.DataFrame:
    rows = []
    for event in events:
        reasons = event.get("reasons") or ["ok"]
        rows.append(
            {
                "timestamp": event.get("timestamp", ""),
                "strategy": event.get("strategy", ""),
                "symbol": event.get("symbol", ""),
                "broker_symbol": event.get("broker_symbol", ""),
                "timeframe": event.get("timeframe", ""),
                "signal_candle_time": event.get("signal_candle_time", ""),
                "prediction": event.get("prediction", 0),
                "mode": event.get("mode", ""),
                "aggregate_score": float(event.get("aggregate_score", 0.0) or 0.0),
                "reasons": ";".join(str(item) for item in reasons),
                "source_file": event.get("_source_file", ""),
            }
        )
    return pd.DataFrame(rows)


def reason_summary(events: list[dict]) -> pd.DataFrame:
    counter: Counter[str] = Counter()
    for event in events:
        for reason in event.get("reasons") or ["ok"]:
            counter[str(reason)] += 1
    return pd.DataFrame(
        [{"reason": reason, "count": count} for reason, count in counter.most_common()]
    )


def snapshot_summary(events: list[dict]) -> pd.DataFrame:
    rows = []
    for event in events:
        for snapshot in event.get("snapshots") or []:
            rows.append(
                {
                    "strategy": event.get("strategy", ""),
                    "symbol": event.get("symbol", ""),
                    "signal_timeframe": event.get("timeframe", ""),
                    "signal_candle_time": event.get("signal_candle_time", ""),
                    "analysis_timeframe": snapshot.get("timeframe", ""),
                    "analysis_candle_time": snapshot.get("candle_time", ""),
                    "market_regime": snapshot.get("market_regime", ""),
                    "score": float(snapshot.get("market_structure_score", 0.0) or 0.0),
                    "range_to_atr": snapshot.get("range_to_atr"),
                    "overlap_ratio_10": snapshot.get("overlap_ratio_10"),
                    "volatility_compression": snapshot.get("volatility_compression"),
                    "volatility_expansion": snapshot.get("volatility_expansion"),
                    "regime_consolidation": snapshot.get("regime_consolidation"),
                    "reasons": ";".join(str(item) for item in snapshot.get("market_structure_reasons", ["ok"])),
                }
            )
    return pd.DataFrame(rows)


def calibration_summary(events_df: pd.DataFrame) -> pd.DataFrame:
    if events_df.empty:
        return pd.DataFrame()
    frame = events_df.copy()
    frame["would_block"] = frame["reasons"].fillna("").ne("ok")
    frame["score_bucket"] = pd.cut(
        frame["aggregate_score"],
        bins=[-0.01, 0.20, 0.40, 0.60, 0.80, 1.00],
        labels=["0.00-0.20", "0.21-0.40", "0.41-0.60", "0.61-0.80", "0.81-1.00"],
    )
    grouped = (
        frame.groupby(["strategy", "symbol", "timeframe"], dropna=False)
        .agg(
            events=("aggregate_score", "size"),
            avg_score=("aggregate_score", "mean"),
            min_score=("aggregate_score", "min"),
            would_block_events=("would_block", "sum"),
        )
        .reset_index()
    )
    grouped["would_block_pct"] = grouped["would_block_events"] / grouped["events"]
    return grouped.sort_values(["would_block_pct", "avg_score", "events"], ascending=[False, True, False])


def score_bucket_summary(events_df: pd.DataFrame) -> pd.DataFrame:
    if events_df.empty:
        return pd.DataFrame()
    frame = events_df.copy()
    frame["score_bucket"] = pd.cut(
        frame["aggregate_score"],
        bins=[-0.01, 0.20, 0.40, 0.60, 0.80, 1.00],
        labels=["0.00-0.20", "0.21-0.40", "0.41-0.60", "0.61-0.80", "0.81-1.00"],
    )
    return frame.groupby("score_bucket", observed=False).size().reset_index(name="events")


def write_markdown(
    output_path: Path,
    events_df: pd.DataFrame,
    reasons_df: pd.DataFrame,
    snapshots_df: pd.DataFrame,
    calibration_df: pd.DataFrame,
    buckets_df: pd.DataFrame,
) -> None:
    lines = ["# Market Structure Shadow Summary", ""]
    if events_df.empty:
        lines.append("Nenhum evento encontrado.")
        output_path.write_text("\n".join(lines), encoding="utf-8")
        return

    lines.extend(
        [
            f"- Eventos: {len(events_df)}",
            f"- Estrategias: {events_df['strategy'].nunique()}",
            f"- Ativos: {events_df['symbol'].nunique()}",
            f"- Score medio: {events_df['aggregate_score'].mean():.3f}",
            "",
            "## Motivos",
            "",
        ]
    )
    for _, row in reasons_df.head(20).iterrows():
        lines.append(f"- {row['reason']}: {int(row['count'])}")

    lines.extend(["", "## Score medio por estrategia", ""])
    by_strategy = events_df.groupby("strategy")["aggregate_score"].agg(["count", "mean", "min"]).reset_index()
    for _, row in by_strategy.sort_values("mean").iterrows():
        lines.append(f"- {row['strategy']}: eventos={int(row['count'])}, media={row['mean']:.3f}, min={row['min']:.3f}")

    if not buckets_df.empty:
        lines.extend(["", "## Distribuicao de score", ""])
        for _, row in buckets_df.iterrows():
            lines.append(f"- {row['score_bucket']}: {int(row['events'])}")

    if not calibration_df.empty:
        lines.extend(["", "## Maior risco de bloqueio se sair do shadow", ""])
        for _, row in calibration_df.head(20).iterrows():
            lines.append(
                f"- {row['strategy']} {row['symbol']} {row['timeframe']}: "
                f"eventos={int(row['events'])}, score_medio={row['avg_score']:.3f}, "
                f"bloquearia={row['would_block_pct']:.1%}"
            )

    if not snapshots_df.empty:
        lines.extend(["", "## Regime por timeframe de analise", ""])
        grouped = snapshots_df.groupby(["analysis_timeframe", "market_regime"]).size().reset_index(name="count")
        for _, row in grouped.sort_values(["analysis_timeframe", "count"], ascending=[True, False]).iterrows():
            lines.append(f"- {row['analysis_timeframe']} {row['market_regime']}: {int(row['count'])}")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    log_dir = Path(args.log_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    events = list(iter_events(log_dir, args.date))
    events_df = flatten_events(events)
    reasons_df = reason_summary(events)
    snapshots_df = snapshot_summary(events)
    calibration_df = calibration_summary(events_df)
    buckets_df = score_bucket_summary(events_df)

    suffix = args.date if args.date else "all"
    events_df.to_csv(output_dir / f"market_structure_shadow_events_{suffix}.csv", index=False)
    reasons_df.to_csv(output_dir / f"market_structure_shadow_reasons_{suffix}.csv", index=False)
    snapshots_df.to_csv(output_dir / f"market_structure_shadow_snapshots_{suffix}.csv", index=False)
    calibration_df.to_csv(output_dir / f"market_structure_shadow_calibration_{suffix}.csv", index=False)
    buckets_df.to_csv(output_dir / f"market_structure_shadow_score_buckets_{suffix}.csv", index=False)
    write_markdown(
        output_dir / f"market_structure_shadow_summary_{suffix}.md",
        events_df,
        reasons_df,
        snapshots_df,
        calibration_df,
        buckets_df,
    )
    print(f"Eventos: {len(events_df)}")
    print(f"Saida: {output_dir}")


if __name__ == "__main__":
    main()
