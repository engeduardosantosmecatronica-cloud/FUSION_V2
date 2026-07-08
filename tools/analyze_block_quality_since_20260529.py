from __future__ import annotations

import bisect
import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean, median
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "reports" / "block_quality_since_20260529"
START_DATE = datetime.fromisoformat("2026-05-29T00:00:00")
EVENT_DATES = ["20260529", "20260531", "20260601", "20260602", "20260603"]
TARGET_EVENT_DATES = ["20260529", "20260531", "20260601", "20260602"]


@dataclass(frozen=True)
class Outcome:
    symbol: str
    side: str
    timestamp: str
    dt: datetime
    entry_time: str
    spread_points: float
    point_size: float
    net_mfe_points: float
    net_mae_points: float
    clean_move_points: float
    drawdown_before_recovery_points: float
    move_after_recovery_points: float
    recovered_after_drawdown: bool
    source: str = "operational_target_events"


@dataclass
class Decision:
    source_file: str
    correlation_id: str
    timestamp: str
    candidate_timestamp: str
    dt: datetime
    symbol: str
    timeframe: str
    side: str
    strategy: str
    p_buy: float
    p_sell: float
    decision: str
    reason: str
    consensus_score: float
    conflict_score: float
    tradeability_score: float
    primary_blocker: str
    primary_blocker_detail: str
    negative_factors: list[str]
    warnings: list[str]
    engine_negative: list[str]


def parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def load_outcomes() -> tuple[dict[tuple[str, str], list[Outcome]], dict[tuple[str, str], list[datetime]]]:
    by_pair: dict[tuple[str, str], dict[str, Outcome]] = defaultdict(dict)
    for day in TARGET_EVENT_DATES:
        path = ROOT / "reports" / "operational_target_matrix" / f"operational_target_events_{day}.csv"
        if not path.exists():
            continue
        for row in read_csv_rows(path):
            dt = parse_dt(row.get("timestamp", ""))
            if not dt or dt < START_DATE:
                continue
            symbol = row.get("symbol", "").upper()
            side = row.get("side", "").upper()
            if not symbol or side not in {"BUY", "SELL"}:
                continue
            outcome = Outcome(
                symbol=symbol,
                side=side,
                timestamp=row.get("timestamp", ""),
                dt=dt,
                entry_time=row.get("entry_time", ""),
                spread_points=as_float(row.get("entry_spread_points")),
                point_size=as_float(row.get("point_size")),
                net_mfe_points=as_float(row.get("net_mfe_points")),
                net_mae_points=as_float(row.get("net_mae_points")),
                clean_move_points=as_float(row.get("clean_move_points")),
                drawdown_before_recovery_points=as_float(row.get("drawdown_before_recovery_points")),
                move_after_recovery_points=as_float(row.get("move_after_recovery_points")),
                recovered_after_drawdown=str(row.get("recovered_after_drawdown", "")).lower() == "true",
                source=path.name,
            )
            by_pair[(symbol, side)][outcome.timestamp] = outcome

    sorted_outcomes: dict[tuple[str, str], list[Outcome]] = {}
    sorted_times: dict[tuple[str, str], list[datetime]] = {}
    for key, values in by_pair.items():
        items = sorted(values.values(), key=lambda item: item.dt)
        sorted_outcomes[key] = items
        sorted_times[key] = [item.dt for item in items]
    return sorted_outcomes, sorted_times


M1_CACHE: dict[str, list[dict[str, Any]]] = {}


def load_m1_history(symbol: str) -> list[dict[str, Any]]:
    symbol = symbol.upper()
    if symbol in M1_CACHE:
        return M1_CACHE[symbol]
    history_dir = ROOT / "reports" / "operational_target_matrix" / "mt5_history"
    rows_by_time: dict[datetime, dict[str, Any]] = {}
    for path in sorted(history_dir.glob(f"{symbol}_M1_*.csv")):
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    dt = parse_dt(str(row.get("date", "")).replace(" ", "T"))
                    if not dt:
                        continue
                    rows_by_time[dt] = {
                        "dt": dt,
                        "open": as_float(row.get("open")),
                        "high": as_float(row.get("high")),
                        "low": as_float(row.get("low")),
                        "close": as_float(row.get("close")),
                        "point": as_float(row.get("point_value"), 0.00001),
                        "spread": as_float(row.get("spread")),
                    }
        except OSError:
            continue
    items = sorted(rows_by_time.values(), key=lambda item: item["dt"])
    M1_CACHE[symbol] = items
    return items


def compute_m1_outcome(decision: Decision, lookahead_minutes: int = 240) -> Outcome | None:
    candles = load_m1_history(decision.symbol)
    if not candles:
        return None
    times = [item["dt"] for item in candles]
    market_dt = decision.dt + timedelta(hours=6)
    idx = bisect.bisect_left(times, market_dt)
    if idx >= len(candles):
        return None
    end_dt = candles[idx]["dt"] + timedelta(minutes=lookahead_minutes)
    end_idx = bisect.bisect_right(times, end_dt)
    if end_idx <= idx + 1:
        return None
    window = candles[idx:end_idx]
    entry = window[0]["open"] or window[0]["close"]
    point = window[0]["point"] or 0.00001
    spread = window[0]["spread"]
    if point <= 0 or entry <= 0:
        return None
    highs = [item["high"] for item in window if item["high"]]
    lows = [item["low"] for item in window if item["low"]]
    if not highs or not lows:
        return None
    if decision.side == "BUY":
        mfe = (max(highs) - entry) / point
        mae = (entry - min(lows)) / point
    else:
        mfe = (entry - min(lows)) / point
        mae = (max(highs) - entry) / point
    mfe = round(mfe - spread, 1)
    mae = round(mae + spread, 1)
    return Outcome(
        symbol=decision.symbol,
        side=decision.side,
        timestamp=decision.candidate_timestamp,
        dt=decision.dt,
        entry_time=window[0]["dt"].isoformat(),
        spread_points=spread,
        point_size=point,
        net_mfe_points=mfe,
        net_mae_points=mae,
        clean_move_points=max(0.0, mfe) if mae <= spread * 2 else 0.0,
        drawdown_before_recovery_points=max(0.0, mae),
        move_after_recovery_points=max(0.0, mfe),
        recovered_after_drawdown=mfe > mae,
        source="m1_history_fallback",
    )


TECHNICAL_NON_BLOCK_REASONS = {
    "",
    "manual_approval_timeout",
    "pre_order_checks_ok",
    "no_reason",
}


def factor_engine(factor: str) -> str:
    return (factor or "unknown").split(":", 1)[0] or "unknown"


def extract_primary_blocker(result: dict[str, Any], engines: list[dict[str, Any]], explanation: dict[str, Any]) -> tuple[str, str, list[str]]:
    reason = str(result.get("reason", "") or "")
    negative = [str(item) for item in result.get("negative_factors", []) or [] if str(item or "").strip()]
    engine_negative: list[str] = []

    contributions = explanation.get("engine_contributions", []) if isinstance(explanation, dict) else []
    if isinstance(contributions, list):
        negative_contribs = [
            item for item in contributions
            if isinstance(item, dict) and str(item.get("impact", "")).lower() == "negative"
        ]
        negative_contribs.sort(key=lambda item: as_float(item.get("weight")), reverse=True)
        engine_negative = [
            f"{item.get('engine', 'unknown')}:{item.get('state', '')}:w={as_float(item.get('weight')):.3f}"
            for item in negative_contribs[:5]
        ]

    if reason not in TECHNICAL_NON_BLOCK_REASONS:
        return factor_engine(reason), reason, engine_negative
    if negative:
        return factor_engine(negative[0]), negative[0], engine_negative
    if engine_negative:
        return factor_engine(engine_negative[0]), engine_negative[0], engine_negative

    for engine in engines:
        direction = str(engine.get("direction", "") or "").upper()
        state = str(engine.get("state", "") or "")
        negs = engine.get("negative_factors", []) or []
        if negs:
            name = str(engine.get("engine", "") or "unknown")
            detail = f"{name}:{negs[0]}"
            return name, detail, engine_negative
        if direction in {"BUY", "SELL"}:
            name = str(engine.get("engine", "") or "unknown")
            detail = f"{name}:direction={direction}:state={state}"
            return name, detail, engine_negative
    return "unknown", reason or "unknown", engine_negative


def load_block_decisions() -> list[Decision]:
    decisions: dict[tuple[str, str, str, str, str], Decision] = {}
    for day in EVENT_DATES:
        path = ROOT / "logs" / "events" / f"events_{day}.jsonl"
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                if '"type": "DECISION"' not in line or '"decision": "BLOCK"' not in line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                data = event.get("data", {}) or {}
                candidate = data.get("candidate", {}) or {}
                result = data.get("result", {}) or {}
                dt = parse_dt(candidate.get("timestamp", "") or data.get("timestamp", "") or event.get("timestamp", ""))
                if not dt or dt < START_DATE:
                    continue
                symbol = str(candidate.get("symbol", "") or "").upper()
                side = str(candidate.get("side", "") or "").upper()
                timeframe = str(candidate.get("timeframe", "") or "").upper()
                strategy = str(candidate.get("strategy", "") or "")
                if not symbol or side not in {"BUY", "SELL"}:
                    continue
                engines = data.get("engines", []) or []
                explanation = data.get("explanation", {}) or {}
                primary, detail, engine_negative = extract_primary_blocker(result, engines, explanation)
                key = (
                    str(data.get("correlation_id") or event.get("correlation_id") or ""),
                    candidate.get("timestamp", ""),
                    symbol,
                    side,
                    strategy,
                )
                decisions[key] = Decision(
                    source_file=path.name,
                    correlation_id=key[0],
                    timestamp=str(event.get("timestamp", "") or ""),
                    candidate_timestamp=str(candidate.get("timestamp", "") or ""),
                    dt=dt,
                    symbol=symbol,
                    timeframe=timeframe,
                    side=side,
                    strategy=strategy,
                    p_buy=as_float(candidate.get("p_buy")),
                    p_sell=as_float(candidate.get("p_sell")),
                    decision=str(result.get("decision", "") or ""),
                    reason=str(result.get("reason", "") or ""),
                    consensus_score=as_float(result.get("consensus_score")),
                    conflict_score=as_float(result.get("conflict_score")),
                    tradeability_score=as_float(result.get("tradeability_score")),
                    primary_blocker=primary,
                    primary_blocker_detail=detail,
                    negative_factors=[str(item) for item in result.get("negative_factors", []) or []],
                    warnings=[str(item) for item in result.get("warnings", []) or []],
                    engine_negative=engine_negative,
                )
    return sorted(decisions.values(), key=lambda item: item.dt)


def match_outcome(decision: Decision, outcomes: dict[tuple[str, str], list[Outcome]], times: dict[tuple[str, str], list[datetime]]) -> Outcome | None:
    key = (decision.symbol, decision.side)
    items = outcomes.get(key, [])
    item_times = times.get(key, [])
    if not items:
        return None
    idx = bisect.bisect_left(item_times, decision.dt)
    candidates: list[Outcome] = []
    if idx < len(items):
        candidates.append(items[idx])
    if idx > 0:
        candidates.append(items[idx - 1])
    if idx + 1 < len(items):
        candidates.append(items[idx + 1])
    best = min(candidates, key=lambda item: abs((item.dt - decision.dt).total_seconds()), default=None)
    if best and abs((best.dt - decision.dt).total_seconds()) <= 8:
        return best
    return compute_m1_outcome(decision)


def classify(decision: Decision, outcome: Outcome | None) -> tuple[str, str, float, float, float]:
    if outcome is None:
        return "sem_outcome", "sem_medicao_de_preco", 0.0, 0.0, 0.0
    mfe = outcome.net_mfe_points
    mae = outcome.net_mae_points
    threshold = max(30.0, outcome.spread_points * 2.0)
    if mfe >= threshold and mae < threshold:
        return "trade_vencedor_perdido", "preco_andou_a_favor_sem_bater_risco_base", threshold, mfe, mae
    if mae >= threshold and mfe < threshold:
        return "bom_bloqueio", "preco_andou_contra_sem_entregar_alvo_base", threshold, mfe, mae
    if mfe >= threshold and mfe >= mae * 1.25:
        return "provavel_trade_vencedor", "mfe_superou_mae_com_folga", threshold, mfe, mae
    if mae >= threshold and mae >= mfe * 1.25:
        return "provavel_bom_bloqueio", "mae_superou_mfe_com_folga", threshold, mfe, mae
    if mfe >= threshold and mae >= threshold:
        return "ambiguo", "mfe_e_mae_altos_ordem_intracandle_desconhecida", threshold, mfe, mae
    return "sem_edge_claro", "movimento_insuficiente_para_classificar", threshold, mfe, mae


def build_rows(decisions: list[Decision], outcomes: dict[tuple[str, str], list[Outcome]], times: dict[tuple[str, str], list[datetime]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for decision in decisions:
        outcome = match_outcome(decision, outcomes, times)
        quality, rationale, threshold, mfe, mae = classify(decision, outcome)
        rows.append(
            {
                "timestamp": decision.candidate_timestamp,
                "symbol": decision.symbol,
                "timeframe": decision.timeframe,
                "side": decision.side,
                "strategy": decision.strategy,
                "decision_reason": decision.reason,
                "primary_blocker": decision.primary_blocker,
                "primary_blocker_detail": decision.primary_blocker_detail,
                "quality": quality,
                "quality_rationale": rationale,
                "threshold_points": f"{threshold:.1f}" if threshold else "",
                "net_mfe_points": f"{mfe:.1f}" if outcome else "",
                "net_mae_points": f"{mae:.1f}" if outcome else "",
                "clean_move_points": f"{outcome.clean_move_points:.1f}" if outcome else "",
                "spread_points": f"{outcome.spread_points:.1f}" if outcome else "",
                "entry_time": outcome.entry_time if outcome else "",
                "outcome_source": outcome.source if outcome else "",
                "tradeability_score": f"{decision.tradeability_score:.3f}",
                "consensus_score": f"{decision.consensus_score:.3f}",
                "conflict_score": f"{decision.conflict_score:.3f}",
                "p_buy": f"{decision.p_buy:.4f}",
                "p_sell": f"{decision.p_sell:.4f}",
                "correlation_id": decision.correlation_id,
                "source_file": decision.source_file,
                "top_negative_engines": "|".join(decision.engine_negative[:3]),
                "negative_factors": "|".join(decision.negative_factors[:8]),
            }
        )
    return rows


def summarize(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_group: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    by_blocker: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_symbol[str(row["symbol"])].append(row)
        by_group[(str(row["symbol"]), str(row["timeframe"]), str(row["side"]))].append(row)
        by_blocker[(str(row["symbol"]), str(row["primary_blocker"]))].append(row)

    def count_quality(items: list[dict[str, Any]]) -> Counter[str]:
        return Counter(str(row["quality"]) for row in items)

    symbol_rows: list[dict[str, Any]] = []
    for symbol, items in sorted(by_symbol.items()):
        q = count_quality(items)
        matched = len(items) - q.get("sem_outcome", 0)
        mfe_values = [as_float(row.get("net_mfe_points"), None) for row in items if row.get("net_mfe_points") != ""]
        mae_values = [as_float(row.get("net_mae_points"), None) for row in items if row.get("net_mae_points") != ""]
        blockers = Counter(str(row["primary_blocker"]) for row in items)
        symbol_rows.append(
            {
                "symbol": symbol,
                "blocked": len(items),
                "matched_outcome": matched,
                "trade_vencedor_perdido": q.get("trade_vencedor_perdido", 0),
                "provavel_trade_vencedor": q.get("provavel_trade_vencedor", 0),
                "bom_bloqueio": q.get("bom_bloqueio", 0),
                "provavel_bom_bloqueio": q.get("provavel_bom_bloqueio", 0),
                "ambiguo": q.get("ambiguo", 0),
                "sem_edge_claro": q.get("sem_edge_claro", 0),
                "sem_outcome": q.get("sem_outcome", 0),
                "missed_winner_rate": f"{((q.get('trade_vencedor_perdido', 0) + q.get('provavel_trade_vencedor', 0)) / matched * 100):.1f}" if matched else "",
                "good_block_rate": f"{((q.get('bom_bloqueio', 0) + q.get('provavel_bom_bloqueio', 0)) / matched * 100):.1f}" if matched else "",
                "median_mfe": f"{median(mfe_values):.1f}" if mfe_values else "",
                "median_mae": f"{median(mae_values):.1f}" if mae_values else "",
                "top_blocker": blockers.most_common(1)[0][0] if blockers else "",
                "top_blocker_count": blockers.most_common(1)[0][1] if blockers else 0,
            }
        )

    group_rows: list[dict[str, Any]] = []
    for (symbol, timeframe, side), items in sorted(by_group.items()):
        q = count_quality(items)
        matched = len(items) - q.get("sem_outcome", 0)
        blockers = Counter(str(row["primary_blocker"]) for row in items)
        group_rows.append(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "side": side,
                "blocked": len(items),
                "matched_outcome": matched,
                "trade_vencedor_perdido": q.get("trade_vencedor_perdido", 0),
                "provavel_trade_vencedor": q.get("provavel_trade_vencedor", 0),
                "bom_bloqueio": q.get("bom_bloqueio", 0),
                "provavel_bom_bloqueio": q.get("provavel_bom_bloqueio", 0),
                "ambiguo": q.get("ambiguo", 0),
                "missed_winner_rate": f"{((q.get('trade_vencedor_perdido', 0) + q.get('provavel_trade_vencedor', 0)) / matched * 100):.1f}" if matched else "",
                "good_block_rate": f"{((q.get('bom_bloqueio', 0) + q.get('provavel_bom_bloqueio', 0)) / matched * 100):.1f}" if matched else "",
                "top_blocker": blockers.most_common(1)[0][0] if blockers else "",
                "top_blocker_count": blockers.most_common(1)[0][1] if blockers else 0,
            }
        )

    blocker_rows: list[dict[str, Any]] = []
    for (symbol, blocker), items in sorted(by_blocker.items()):
        q = count_quality(items)
        matched = len(items) - q.get("sem_outcome", 0)
        blocker_rows.append(
            {
                "symbol": symbol,
                "blocker": blocker,
                "blocked": len(items),
                "matched_outcome": matched,
                "trade_vencedor_perdido": q.get("trade_vencedor_perdido", 0),
                "provavel_trade_vencedor": q.get("provavel_trade_vencedor", 0),
                "bom_bloqueio": q.get("bom_bloqueio", 0),
                "provavel_bom_bloqueio": q.get("provavel_bom_bloqueio", 0),
                "missed_winner_rate": f"{((q.get('trade_vencedor_perdido', 0) + q.get('provavel_trade_vencedor', 0)) / matched * 100):.1f}" if matched else "",
                "good_block_rate": f"{((q.get('bom_bloqueio', 0) + q.get('provavel_bom_bloqueio', 0)) / matched * 100):.1f}" if matched else "",
            }
        )
    return symbol_rows, group_rows, blocker_rows


def write_markdown(rows: list[dict[str, Any]], symbol_rows: list[dict[str, Any]], group_rows: list[dict[str, Any]], blocker_rows: list[dict[str, Any]]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    matched = [row for row in rows if row["quality"] != "sem_outcome"]
    missed = [row for row in rows if row["quality"] in {"trade_vencedor_perdido", "provavel_trade_vencedor"}]
    good = [row for row in rows if row["quality"] in {"bom_bloqueio", "provavel_bom_bloqueio"}]
    top_symbols = sorted(symbol_rows, key=lambda row: -int(row["matched_outcome"]))[:25]
    top_missed_groups = sorted(group_rows, key=lambda row: -(int(row["trade_vencedor_perdido"]) + int(row["provavel_trade_vencedor"])))[:25]
    top_good_groups = sorted(group_rows, key=lambda row: -(int(row["bom_bloqueio"]) + int(row["provavel_bom_bloqueio"])))[:25]
    top_bad_blockers = sorted(blocker_rows, key=lambda row: -(int(row["trade_vencedor_perdido"]) + int(row["provavel_trade_vencedor"])))[:25]

    lines = [
        "# Block Quality Since 2026-05-29",
        "",
        f"Generated at: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Method",
        "",
        "- Uses DECISION events with decision=BLOCK from logs/events/events_20260529..20260603.",
        "- Joins each blocked signal to operational_target_events price outcomes from 20260529, 20260531, 20260601 and 20260602.",
        "- Classifies using net MFE/MAE points and a dynamic base threshold=max(30, 2x spread).",
        "- 2026-06-03 decisions without operational_target_events remain marked sem_outcome.",
        "",
        "## Scope",
        "",
        f"- Blocked decisions found: {len(rows)}",
        f"- Decisions with price outcome: {len(matched)}",
        f"- Missed/possible winners: {len(missed)}",
        f"- Good/probable good blocks: {len(good)}",
        "",
        "## By Symbol",
        "",
        "| Symbol | Matched | Missed winners | Good blocks | Ambiguous | Missed % | Good % | Median MFE | Median MAE | Top blocker |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in top_symbols:
        missed_count = int(row["trade_vencedor_perdido"]) + int(row["provavel_trade_vencedor"])
        good_count = int(row["bom_bloqueio"]) + int(row["provavel_bom_bloqueio"])
        lines.append(
            f"| {row['symbol']} | {row['matched_outcome']} | {missed_count} | {good_count} | {row['ambiguo']} | "
            f"{row['missed_winner_rate']} | {row['good_block_rate']} | {row['median_mfe']} | {row['median_mae']} | {row['top_blocker']} |"
        )

    lines += [
        "",
        "## Most Missed Winner Groups",
        "",
        "| Symbol | TF | Side | Matched | Missed winners | Good blocks | Top blocker |",
        "|---|---|---|---:|---:|---:|---|",
    ]
    for row in top_missed_groups:
        missed_count = int(row["trade_vencedor_perdido"]) + int(row["provavel_trade_vencedor"])
        good_count = int(row["bom_bloqueio"]) + int(row["provavel_bom_bloqueio"])
        if missed_count <= 0:
            continue
        lines.append(
            f"| {row['symbol']} | {row['timeframe']} | {row['side']} | {row['matched_outcome']} | {missed_count} | {good_count} | {row['top_blocker']} |"
        )

    lines += [
        "",
        "## Best Blocks",
        "",
        "| Symbol | TF | Side | Matched | Good blocks | Missed winners | Top blocker |",
        "|---|---|---|---:|---:|---:|---|",
    ]
    for row in top_good_groups:
        missed_count = int(row["trade_vencedor_perdido"]) + int(row["provavel_trade_vencedor"])
        good_count = int(row["bom_bloqueio"]) + int(row["provavel_bom_bloqueio"])
        if good_count <= 0:
            continue
        lines.append(
            f"| {row['symbol']} | {row['timeframe']} | {row['side']} | {row['matched_outcome']} | {good_count} | {missed_count} | {row['top_blocker']} |"
        )

    lines += [
        "",
        "## Blockers Behind Possible Winners",
        "",
        "| Symbol | Blocker | Matched | Missed winners | Good blocks | Missed % | Good % |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in top_bad_blockers:
        missed_count = int(row["trade_vencedor_perdido"]) + int(row["provavel_trade_vencedor"])
        good_count = int(row["bom_bloqueio"]) + int(row["provavel_bom_bloqueio"])
        if missed_count <= 0:
            continue
        lines.append(
            f"| {row['symbol']} | {row['blocker']} | {row['matched_outcome']} | {missed_count} | {good_count} | {row['missed_winner_rate']} | {row['good_block_rate']} |"
        )

    (OUT_DIR / "block_quality_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    outcomes, times = load_outcomes()
    decisions = load_block_decisions()
    rows = build_rows(decisions, outcomes, times)
    symbol_rows, group_rows, blocker_rows = summarize(rows)

    write_csv(
        OUT_DIR / "blocked_trade_outcomes.csv",
        rows,
        [
            "timestamp",
            "symbol",
            "timeframe",
            "side",
            "strategy",
            "decision_reason",
            "primary_blocker",
            "primary_blocker_detail",
            "quality",
            "quality_rationale",
            "threshold_points",
            "net_mfe_points",
            "net_mae_points",
            "clean_move_points",
            "spread_points",
            "entry_time",
            "outcome_source",
            "tradeability_score",
            "consensus_score",
            "conflict_score",
            "p_buy",
            "p_sell",
            "correlation_id",
            "source_file",
            "top_negative_engines",
            "negative_factors",
        ],
    )
    write_csv(
        OUT_DIR / "block_quality_by_symbol.csv",
        sorted(symbol_rows, key=lambda row: -int(row["matched_outcome"])),
        [
            "symbol",
            "blocked",
            "matched_outcome",
            "trade_vencedor_perdido",
            "provavel_trade_vencedor",
            "bom_bloqueio",
            "provavel_bom_bloqueio",
            "ambiguo",
            "sem_edge_claro",
            "sem_outcome",
            "missed_winner_rate",
            "good_block_rate",
            "median_mfe",
            "median_mae",
            "top_blocker",
            "top_blocker_count",
        ],
    )
    write_csv(
        OUT_DIR / "block_quality_by_symbol_timeframe_side.csv",
        sorted(group_rows, key=lambda row: -(int(row["trade_vencedor_perdido"]) + int(row["provavel_trade_vencedor"]) + int(row["bom_bloqueio"]) + int(row["provavel_bom_bloqueio"]))),
        [
            "symbol",
            "timeframe",
            "side",
            "blocked",
            "matched_outcome",
            "trade_vencedor_perdido",
            "provavel_trade_vencedor",
            "bom_bloqueio",
            "provavel_bom_bloqueio",
            "ambiguo",
            "missed_winner_rate",
            "good_block_rate",
            "top_blocker",
            "top_blocker_count",
        ],
    )
    write_csv(
        OUT_DIR / "block_quality_by_symbol_blocker.csv",
        sorted(blocker_rows, key=lambda row: -(int(row["trade_vencedor_perdido"]) + int(row["provavel_trade_vencedor"]) + int(row["bom_bloqueio"]) + int(row["provavel_bom_bloqueio"]))),
        [
            "symbol",
            "blocker",
            "blocked",
            "matched_outcome",
            "trade_vencedor_perdido",
            "provavel_trade_vencedor",
            "bom_bloqueio",
            "provavel_bom_bloqueio",
            "missed_winner_rate",
            "good_block_rate",
        ],
    )
    missed = [
        row for row in rows
        if row["quality"] in {"trade_vencedor_perdido", "provavel_trade_vencedor"}
    ]
    write_csv(
        OUT_DIR / "missed_winning_trades.csv",
        sorted(missed, key=lambda row: -as_float(row.get("net_mfe_points"))),
        [
            "timestamp",
            "symbol",
            "timeframe",
            "side",
            "strategy",
            "primary_blocker",
            "primary_blocker_detail",
            "quality",
            "threshold_points",
            "net_mfe_points",
            "net_mae_points",
            "spread_points",
            "tradeability_score",
            "consensus_score",
            "conflict_score",
            "p_buy",
            "p_sell",
            "correlation_id",
            "negative_factors",
        ],
    )
    write_markdown(rows, symbol_rows, group_rows, blocker_rows)


if __name__ == "__main__":
    main()
