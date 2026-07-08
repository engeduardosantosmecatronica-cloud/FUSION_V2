from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

try:
    import MetaTrader5 as mt5
except ImportError:  # pragma: no cover
    mt5 = None


ROOT = Path(__file__).resolve().parents[1]
TIMEFRAME_MINUTES = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440}
MT5_TIMEFRAMES = {
    "M1": getattr(mt5, "TIMEFRAME_M1", 1),
    "M5": getattr(mt5, "TIMEFRAME_M5", 5),
    "M15": getattr(mt5, "TIMEFRAME_M15", 15),
    "M30": getattr(mt5, "TIMEFRAME_M30", 30),
    "H1": getattr(mt5, "TIMEFRAME_H1", 16385),
    "H4": getattr(mt5, "TIMEFRAME_H4", 16388),
    "D1": getattr(mt5, "TIMEFRAME_D1", 16408),
}


@dataclass(frozen=True)
class Signal:
    correlation_id: str
    timestamp: pd.Timestamp
    symbol: str
    timeframe: str
    strategy: str
    side: str
    p_buy: float | None
    p_sell: float | None
    decision: str
    reason: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compara sinais do robo com candles posteriores para medir acerto direcional."
    )
    parser.add_argument("--date", action="append", required=True, help="Data YYYYMMDD. Pode repetir.")
    parser.add_argument("--audit-dir", default="logs/decision_audit")
    parser.add_argument("--output-dir", default="reports/signal_outcomes")
    parser.add_argument("--horizons", default="1,3,6,12,24", help="Horizontes em candles, separados por virgula.")
    parser.add_argument("--since-hours", type=float, default=0.0, help="Filtra sinais das ultimas N horas dentro dos logs.")
    parser.add_argument("--start", default="", help="Inicio Fusion time: YYYY-MM-DD HH:MM[:SS].")
    parser.add_argument("--end", default="", help="Fim Fusion time: YYYY-MM-DD HH:MM[:SS].")
    parser.add_argument("--only-decision", default="", help="Ex.: ALLOW ou BLOCK. Vazio analisa todos.")
    parser.add_argument(
        "--timeframe",
        action="append",
        default=[],
        help="Filtra timeframes. Pode repetir. Ex.: --timeframe M15 --timeframe H1 --timeframe H4.",
    )
    parser.add_argument("--use-mt5", action="store_true", help="Busca candles recentes no MT5 quando parquet/csv nao cobrem.")
    parser.add_argument(
        "--market-time-offset-hours",
        type=float,
        default=0.0,
        help="Horas a somar no horario do sinal para alinhar com o horario dos candles/MT5.",
    )
    parser.add_argument(
        "--save-mt5-history",
        action="store_true",
        help="Salva historico MT5 baixado temporariamente em reports/signal_outcomes/mt5_history.",
    )
    parser.add_argument("--max-signals", type=int, default=0, help="Limite opcional para debug.")
    return parser.parse_args()


def as_float(value: Any) -> float | None:
    try:
        if value in ("", None):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_time(value: Any) -> pd.Timestamp | None:
    if not value:
        return None
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return None
    if getattr(ts, "tzinfo", None) is not None:
        ts = ts.tz_convert(None)
    return pd.Timestamp(ts).tz_localize(None) if pd.Timestamp(ts).tzinfo else pd.Timestamp(ts)


def load_config() -> dict[str, Any]:
    path = ROOT / "config" / "fusion_config.yaml"
    if yaml is None or not path.exists():
        return {}
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        data = yaml.safe_load(handle) or {}
    return data if isinstance(data, dict) else {}


def normalize_symbol(symbol: str) -> str:
    value = str(symbol or "").upper().replace("-F", "")
    if value == "XAUUSD":
        return "GOLD"
    if value in {"SILVER", "XAGUSD"}:
        return "XAGUSD"
    return value


def broker_symbol(symbol: str, config: dict[str, Any]) -> str:
    normalized = normalize_symbol(symbol)
    execution = config.get("execution") if isinstance(config.get("execution"), dict) else {}
    mapping = execution.get("symbol_mapping") if isinstance(execution.get("symbol_mapping"), dict) else {}
    return str(mapping.get(normalized) or normalized)


def load_signals(args: argparse.Namespace) -> list[Signal]:
    audit_dir = ROOT / args.audit_dir
    signals: list[Signal] = []
    seen: set[str] = set()
    only_decision = args.only_decision.upper().strip()
    only_timeframes = {str(item).upper().strip() for item in getattr(args, "timeframe", []) if str(item).strip()}
    start = parse_time(args.start)
    end = parse_time(args.end)

    for date in args.date:
        path = audit_dir / f"decision_audit_{date}.jsonl"
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue

                candidate = payload.get("candidate") or {}
                result = payload.get("result") or {}
                side = str(candidate.get("side") or "").upper()
                if side not in {"BUY", "SELL"}:
                    continue
                decision = str(result.get("decision") or "").upper()
                if only_decision and decision != only_decision:
                    continue

                timestamp = parse_time(candidate.get("timestamp") or payload.get("timestamp"))
                symbol = normalize_symbol(candidate.get("symbol") or "")
                timeframe = str(candidate.get("timeframe") or "").upper()
                if timestamp is None or not symbol or timeframe not in TIMEFRAME_MINUTES:
                    continue
                if only_timeframes and timeframe not in only_timeframes:
                    continue
                if start is not None and timestamp < start:
                    continue
                if end is not None and timestamp > end:
                    continue

                correlation_id = str(payload.get("correlation_id") or "")
                key = correlation_id or f"{symbol}:{timeframe}:{side}:{timestamp.isoformat()}"
                if key in seen:
                    continue
                seen.add(key)

                signals.append(
                    Signal(
                        correlation_id=correlation_id,
                        timestamp=timestamp,
                        symbol=symbol,
                        timeframe=timeframe,
                        strategy=str(candidate.get("strategy") or ""),
                        side=side,
                        p_buy=as_float(candidate.get("p_buy")),
                        p_sell=as_float(candidate.get("p_sell")),
                        decision=decision,
                        reason=str(result.get("reason") or ""),
                    )
                )
                if args.max_signals and len(signals) >= args.max_signals:
                    return signals

    if args.since_hours > 0 and signals:
        cutoff = max(signal.timestamp for signal in signals) - pd.Timedelta(hours=args.since_hours)
        signals = [signal for signal in signals if signal.timestamp >= cutoff]
    return sorted(signals, key=lambda item: item.timestamp)


def load_parquet(symbol: str, timeframe: str) -> pd.DataFrame:
    candidates = [
        ROOT / "data" / "parquet" / timeframe / f"{symbol}.parquet",
        ROOT / "data" / "parquet" / timeframe / f"{symbol}-F.parquet",
    ]
    if symbol == "GOLD":
        candidates.extend(
            [
                ROOT / "data" / "parquet" / timeframe / "XAUUSD.parquet",
                ROOT / "data" / "parquet" / timeframe / "XAUUSD-F.parquet",
            ]
        )
    for path in candidates:
        if path.exists():
            frame = pd.read_parquet(path)
            return normalize_candles(frame)
    return pd.DataFrame()


def load_csv(symbol: str, timeframe: str) -> pd.DataFrame:
    root = ROOT / "data" / "csv" / timeframe
    if not root.exists():
        return pd.DataFrame()
    names = [symbol]
    if symbol == "GOLD":
        names.extend(["XAUUSD", "GOLD-F", "XAUUSD-F"])
    frames = []
    for name in dict.fromkeys(names):
        for path in root.glob(f"**/{name}.csv"):
            try:
                frames.append(pd.read_csv(path))
            except Exception:
                continue
    if not frames:
        return pd.DataFrame()
    return normalize_candles(pd.concat(frames, ignore_index=True))


def initialize_mt5(config: dict[str, Any]) -> bool:
    if mt5 is None:
        return False
    broker = config.get("broker") if isinstance(config.get("broker"), dict) else {}
    terminal_path = str(broker.get("terminal_path") or "").strip()
    if terminal_path and Path(terminal_path).exists():
        return bool(mt5.initialize(path=terminal_path))
    return bool(mt5.initialize())


def mt5_rates_to_frame(rates: Any, symbol: str, point_value: float | None = None) -> pd.DataFrame:
    if rates is None or len(rates) == 0:
        return pd.DataFrame()
    frame = pd.DataFrame(rates)
    frame["date"] = pd.to_datetime(frame["time"], unit="s")
    frame["symbol"] = symbol
    if point_value and point_value > 0:
        frame["point_value"] = float(point_value)
    return normalize_candles(frame)


def load_mt5(symbol: str, timeframe: str, config: dict[str, Any], start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    if mt5 is None:
        return pd.DataFrame()
    real_symbol = broker_symbol(symbol, config)
    tf_code = MT5_TIMEFRAMES.get(timeframe)
    if tf_code is None:
        return pd.DataFrame()
    try:
        mt5.symbol_select(real_symbol, True)
        info = mt5.symbol_info(real_symbol)
        point_value = float(getattr(info, "point", 0.0) or 0.0) if info is not None else None
        rates = mt5.copy_rates_range(real_symbol, tf_code, start.to_pydatetime(), end.to_pydatetime())
    except Exception:
        rates = None
        point_value = None

    frame = mt5_rates_to_frame(rates, symbol, point_value)
    min_expected = start + pd.Timedelta(minutes=TIMEFRAME_MINUTES[timeframe] * 3)
    if not frame.empty and frame["date"].min() <= min_expected and frame["date"].max() >= end:
        return frame

    total_minutes = max(1.0, (end - start).total_seconds() / 60.0)
    count = int(total_minutes / TIMEFRAME_MINUTES[timeframe]) + 1000
    count = max(count, 1000)
    count = min(count, 100000)
    try:
        rates = mt5.copy_rates_from_pos(real_symbol, tf_code, 0, count)
    except Exception:
        rates = None
    fallback = mt5_rates_to_frame(rates, symbol, point_value)
    if fallback.empty:
        return frame
    return fallback[(fallback["date"] >= start) & (fallback["date"] <= end)].reset_index(drop=True)


def save_mt5_history(frame: pd.DataFrame, symbol: str, timeframe: str, args: argparse.Namespace) -> None:
    if frame.empty or not args.save_mt5_history:
        return
    out_dir = ROOT / args.output_dir / "mt5_history"
    out_dir.mkdir(parents=True, exist_ok=True)
    start_label = str(args.start or "start").replace(":", "").replace(" ", "_").replace("-", "")
    end_label = str(args.end or "end").replace(":", "").replace(" ", "_").replace("-", "")
    path = out_dir / f"{symbol}_{timeframe}_{start_label}_{end_label}.csv"
    frame.to_csv(path, index=False)


def normalize_candles(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    frame = frame.copy()
    if "date" not in frame.columns:
        if "time" in frame.columns:
            if pd.api.types.is_numeric_dtype(frame["time"]):
                frame["date"] = pd.to_datetime(frame["time"], unit="s", errors="coerce")
            else:
                frame["date"] = pd.to_datetime(frame["time"], errors="coerce")
        else:
            return pd.DataFrame()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    needed = ["date", "open", "high", "low", "close", "point_value", "spread"]
    frame = frame[[col for col in needed if col in frame.columns]]
    for col in ["open", "high", "low", "close", "point_value", "spread"]:
        if col in frame.columns:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")
    frame = frame.dropna(subset=["date", "open", "high", "low", "close"])
    frame = frame.sort_values("date").drop_duplicates("date", keep="last").reset_index(drop=True)
    return frame


def point_size(symbol: str, candles: pd.DataFrame) -> float:
    if "point_value" in candles.columns and candles["point_value"].notna().any():
        value = as_float(candles["point_value"].dropna().iloc[-1])
        if value and value > 0:
            return value
    if symbol.endswith("JPY") or symbol in {"GOLD", "XAUUSD", "XAGUSD"}:
        return 0.01
    if symbol in {"BTCUSD", "ETHUSD"} or symbol.endswith(("CASH", "200", "500", "100", "30", "40")):
        return 1.0
    if symbol.endswith("USD") and len(symbol) > 6:
        return 0.01
    return 0.0001


def signal_market_time(signal_time: pd.Timestamp, args: argparse.Namespace) -> pd.Timestamp:
    return signal_time + pd.Timedelta(hours=args.market_time_offset_hours)


def build_market_data(signals: list[Signal], args: argparse.Namespace, config: dict[str, Any]) -> dict[tuple[str, str], pd.DataFrame]:
    grouped: dict[tuple[str, str], list[Signal]] = {}
    for signal in signals:
        grouped.setdefault((signal.symbol, signal.timeframe), []).append(signal)

    if args.use_mt5:
        initialize_mt5(config)

    data: dict[tuple[str, str], pd.DataFrame] = {}
    horizons = [int(item) for item in args.horizons.split(",") if item.strip()]
    max_horizon = max(horizons or [1])
    for key, items in grouped.items():
        symbol, timeframe = key
        frame = load_parquet(symbol, timeframe)
        if frame.empty:
            frame = load_csv(symbol, timeframe)

        requested_start = parse_time(args.start)
        requested_end = parse_time(args.end)
        earliest_needed = (
            signal_market_time(requested_start, args)
            if requested_start is not None
            else min(signal_market_time(item.timestamp, args) for item in items)
        )
        latest_base = (
            signal_market_time(requested_end, args)
            if requested_end is not None
            else max(signal_market_time(item.timestamp, args) for item in items)
        )
        earliest_needed = earliest_needed - pd.Timedelta(minutes=TIMEFRAME_MINUTES[timeframe] * 2)
        latest_needed = latest_base + pd.Timedelta(minutes=TIMEFRAME_MINUTES[timeframe] * (max_horizon + 2))
        if args.use_mt5 and (frame.empty or frame["date"].max() < latest_needed):
            mt5_frame = load_mt5(symbol, timeframe, config, earliest_needed, latest_needed)
            if not mt5_frame.empty:
                save_mt5_history(mt5_frame, symbol, timeframe, args)
                frame = normalize_candles(pd.concat([frame, mt5_frame], ignore_index=True)) if not frame.empty else mt5_frame
        data[key] = frame
    return data


def evaluate(
    signals: list[Signal],
    market_data: dict[tuple[str, str], pd.DataFrame],
    horizons: list[int],
    args: argparse.Namespace,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for signal in signals:
        candles = market_data.get((signal.symbol, signal.timeframe), pd.DataFrame())
        base = {
            "timestamp": signal.timestamp.isoformat(),
            "market_timestamp": signal_market_time(signal.timestamp, args).isoformat(),
            "symbol": signal.symbol,
            "timeframe": signal.timeframe,
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

        market_timestamp = signal_market_time(signal.timestamp, args)
        idx = candles["date"].searchsorted(market_timestamp, side="right")
        if idx >= len(candles):
            rows.append({**base, "status": "sem_candle_posterior", "history_last": candles["date"].max().isoformat()})
            continue

        entry = candles.iloc[idx]
        point = point_size(signal.symbol, candles)
        future = candles.iloc[idx : min(len(candles), idx + max(horizons) + 1)]
        mfe_price = (future["high"].max() - entry["open"]) if signal.side == "BUY" else (entry["open"] - future["low"].min())
        mae_price = (entry["open"] - future["low"].min()) if signal.side == "BUY" else (future["high"].max() - entry["open"])

        row = {
            **base,
            "status": "ok",
            "entry_time": entry["date"].isoformat(),
            "entry_price": float(entry["open"]),
            "point_size": point,
            "mfe_points": round(float(mfe_price / point), 2) if point else "",
            "mae_points": round(float(mae_price / point), 2) if point else "",
        }
        for horizon in horizons:
            target_idx = idx + horizon
            if target_idx >= len(candles):
                row[f"h{horizon}_status"] = "sem_candle"
                continue
            close = float(candles.iloc[target_idx]["close"])
            raw_delta = close - float(entry["open"])
            signed_delta = raw_delta if signal.side == "BUY" else -raw_delta
            row[f"h{horizon}_close"] = close
            row[f"h{horizon}_price_delta"] = round(float(signed_delta), 6)
            row[f"h{horizon}_points"] = round(float(signed_delta / point), 2) if point else ""
            row[f"h{horizon}_correct"] = bool(signed_delta > 0)
        rows.append(row)
    return pd.DataFrame(rows)


def write_summary(df: pd.DataFrame, output: Path, horizons: list[int]) -> None:
    lines = ["# Signal Outcomes", ""]
    lines.append(f"- Sinais avaliados: {len(df)}")
    ok = df[df.get("status", "") == "ok"] if not df.empty else df
    lines.append(f"- Com candle posterior: {len(ok)}")
    lines.append(f"- Sem historico/candle posterior: {len(df) - len(ok)}")
    if ok.empty:
        output.write_text("\n".join(lines), encoding="utf-8")
        return

    for horizon in horizons:
        col = f"h{horizon}_correct"
        if col not in ok.columns:
            continue
        valid = ok[ok[col].isin([True, False])]
        if valid.empty:
            continue
        acc = float(valid[col].mean() * 100.0)
        median_points = float(pd.to_numeric(valid.get(f"h{horizon}_points"), errors="coerce").median())
        lines.append(f"- H+{horizon} candles: acerto {acc:.1f}% | mediana {median_points:.1f} pontos | amostras {len(valid)}")

    lines.extend(["", "## Por timeframe", ""])
    for timeframe, group in ok.groupby("timeframe"):
        parts = [f"{timeframe}: {len(group)} sinais"]
        for horizon in horizons[:3]:
            col = f"h{horizon}_correct"
            if col in group:
                valid = group[group[col].isin([True, False])]
                if not valid.empty:
                    parts.append(f"H+{horizon}={valid[col].mean() * 100:.1f}%")
        lines.append("- " + " | ".join(parts))

    lines.extend(["", "## Por decisao", ""])
    for decision, group in ok.groupby("decision"):
        decision_label = str(decision or "SEM_DECISAO")
        parts = [f"{decision_label}: {len(group)} sinais"]
        for horizon in horizons[:3]:
            col = f"h{horizon}_correct"
            if col in group:
                valid = group[group[col].isin([True, False])]
                if not valid.empty:
                    parts.append(f"H+{horizon}={valid[col].mean() * 100:.1f}%")
        lines.append("- " + " | ".join(parts))

    lines.extend(["", "## Melhores/Piores por ativo em H+3", ""])
    if "h3_correct" in ok.columns:
        by_symbol = ok[ok["h3_correct"].isin([True, False])].groupby("symbol")["h3_correct"].agg(["count", "mean"])
        by_symbol = by_symbol[by_symbol["count"] >= 5].sort_values("mean", ascending=False)
        for symbol, row in by_symbol.head(12).iterrows():
            lines.append(f"- {symbol}: {row['mean'] * 100:.1f}% ({int(row['count'])})")
        if not by_symbol.empty:
            lines.append("")
            lines.append("Piores:")
            for symbol, row in by_symbol.tail(12).sort_values("mean").iterrows():
                lines.append(f"- {symbol}: {row['mean'] * 100:.1f}% ({int(row['count'])})")

    output.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    horizons = [int(item) for item in args.horizons.split(",") if item.strip()]
    config = load_config()
    signals = load_signals(args)
    market_data = build_market_data(signals, args, config)
    df = evaluate(signals, market_data, horizons, args)

    output_dir = ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    label = "_".join(args.date)
    if args.since_hours:
        label += f"_last{int(args.since_hours)}h"
    if args.start or args.end:
        start_label = str(args.start or "start").replace(":", "").replace(" ", "_").replace("-", "")
        end_label = str(args.end or "end").replace(":", "").replace(" ", "_").replace("-", "")
        label += f"_{start_label}_to_{end_label}"
    if args.market_time_offset_hours:
        label += f"_mt5offset{args.market_time_offset_hours:g}h"
    if args.only_decision:
        label += f"_{args.only_decision.upper()}"
    if args.timeframe:
        tf_label = "_".join(str(item).upper().strip() for item in args.timeframe if str(item).strip())
        if tf_label:
            label += f"_{tf_label}"

    csv_path = output_dir / f"signal_outcomes_{label}.csv"
    md_path = output_dir / f"signal_outcomes_{label}.md"
    df.to_csv(csv_path, index=False)
    write_summary(df, md_path, horizons)
    print(f"Sinais: {len(signals)}")
    print(f"Saida CSV: {csv_path}")
    print(f"Resumo: {md_path}")

    if mt5 is not None:
        try:
            mt5.shutdown()
        except Exception:
            pass


if __name__ == "__main__":
    main()
