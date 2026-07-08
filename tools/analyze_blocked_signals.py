from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "filter_block_analysis"


@dataclass(frozen=True)
class BlockedSignal:
    source: str
    timestamp: str
    correlation_id: str
    symbol: str
    timeframe: str
    side: str
    strategy: str
    reason: str
    consensus_score: float | None = None
    conflict_score: float | None = None
    tradeability_score: float | None = None
    xai_final_score: float | None = None


def as_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def split_factors(value: str) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in str(value).split(";") if item.strip()]


def reason_engine(reason: str) -> str:
    if not reason:
        return "unknown"
    token = reason.split(":", 1)[0].strip()
    if not token:
        return "unknown"
    return token


def iter_csv(path: Path) -> Iterable[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            yield row


def load_decision_events() -> list[BlockedSignal]:
    signals: dict[tuple[str, str, str, str, str, str], BlockedSignal] = {}
    for path in sorted((ROOT / "reports" / "decision_audit").glob("decision_audit_events_*.csv")):
        for row in iter_csv(path):
            if row.get("decision", "").upper() != "BLOCK":
                continue
            cid = row.get("correlation_id", "")
            key = (
                cid or row.get("timestamp", ""),
                row.get("symbol", ""),
                row.get("timeframe", ""),
                row.get("side", ""),
                row.get("strategy", ""),
                row.get("reason", ""),
            )
            signals[key] = BlockedSignal(
                source=path.name,
                timestamp=row.get("timestamp", ""),
                correlation_id=cid,
                symbol=row.get("symbol", "").upper(),
                timeframe=row.get("timeframe", "").upper(),
                side=row.get("side", "").upper(),
                strategy=row.get("strategy", ""),
                reason=row.get("reason", ""),
                consensus_score=as_float(row.get("consensus_score")),
                conflict_score=as_float(row.get("conflict_score")),
                tradeability_score=as_float(row.get("tradeability_score")),
                xai_final_score=as_float(row.get("xai_final_score")),
            )
    return list(signals.values())


def load_engine_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in sorted((ROOT / "reports" / "decision_audit").glob("decision_audit_engines_*.csv")):
        for row in iter_csv(path):
            if row.get("decision", "").upper() == "BLOCK":
                row["_source"] = path.name
                rows.append(row)
    return rows


def load_market_alignment_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    block_states = {"countertrend", "structural_conflict", "chop", "weak_alignment"}
    for path in sorted((ROOT / "reports" / "market_alignment").glob("market_alignment_*.csv")):
        for row in iter_csv(path):
            state = row.get("state", "")
            if state in block_states:
                row["_source"] = path.name
                rows.append(row)
    return rows


def write_csv(path: Path, rows: Iterable[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def pct(part: int, total: int) -> str:
    if total <= 0:
        return "0.0"
    return f"{part / total * 100:.1f}"


def summarize_decision_events(signals: list[BlockedSignal]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    by_group: dict[tuple[str, str, str], list[BlockedSignal]] = defaultdict(list)
    by_symbol: dict[str, list[BlockedSignal]] = defaultdict(list)
    for signal in signals:
        by_group[(signal.symbol, signal.timeframe, signal.side)].append(signal)
        by_symbol[signal.symbol].append(signal)

    group_rows: list[dict[str, object]] = []
    for (symbol, timeframe, side), items in sorted(by_group.items()):
        reasons = Counter(reason_engine(item.reason) for item in items)
        top_reason, top_count = reasons.most_common(1)[0]
        tradeability = [item.tradeability_score for item in items if item.tradeability_score is not None]
        conflict = [item.conflict_score for item in items if item.conflict_score is not None]
        consensus = [item.consensus_score for item in items if item.consensus_score is not None]
        group_rows.append(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "side": side,
                "blocked": len(items),
                "top_blocker": top_reason,
                "top_blocker_count": top_count,
                "top_blocker_pct": pct(top_count, len(items)),
                "avg_tradeability": f"{mean(tradeability):.3f}" if tradeability else "",
                "avg_conflict": f"{mean(conflict):.3f}" if conflict else "",
                "avg_consensus": f"{mean(consensus):.3f}" if consensus else "",
            }
        )

    symbol_rows: list[dict[str, object]] = []
    for symbol, items in sorted(by_symbol.items()):
        side_counts = Counter(item.side for item in items)
        tf_counts = Counter(item.timeframe for item in items)
        reasons = Counter(reason_engine(item.reason) for item in items)
        top_reason, top_count = reasons.most_common(1)[0]
        symbol_rows.append(
            {
                "symbol": symbol,
                "blocked_total": len(items),
                "blocked_buy": side_counts.get("BUY", 0),
                "blocked_sell": side_counts.get("SELL", 0),
                "top_timeframe": tf_counts.most_common(1)[0][0],
                "top_blocker": top_reason,
                "top_blocker_count": top_count,
                "top_blocker_pct": pct(top_count, len(items)),
            }
        )
    return group_rows, symbol_rows


def summarize_engine_rows(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    counts: dict[tuple[str, str, str, str, str], Counter[str]] = defaultdict(Counter)
    for row in rows:
        symbol = row.get("symbol", "").upper()
        timeframe = row.get("timeframe", "").upper()
        side = row.get("side", "").upper()
        engine = row.get("engine", "")
        negatives = split_factors(row.get("negative_factors", ""))
        warnings = split_factors(row.get("warnings", ""))
        engine_direction = row.get("engine_direction", "").upper()
        if negatives:
            kind = "negative"
        elif engine_direction in {"BUY", "SELL"} and engine_direction != side:
            kind = "direction_conflict"
        elif warnings:
            kind = "warning"
        else:
            kind = "neutral_in_block"
        counts[(symbol, timeframe, side, engine, kind)].update([row.get("engine_state", "") or ""])

    out: list[dict[str, object]] = []
    for (symbol, timeframe, side, engine, kind), states in sorted(counts.items()):
        total = sum(states.values())
        top_state, top_state_count = states.most_common(1)[0]
        out.append(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "side": side,
                "engine": engine,
                "block_signal_role": kind,
                "rows": total,
                "top_state": top_state,
                "top_state_count": top_state_count,
                "top_state_pct": pct(top_state_count, total),
            }
        )
    return out


def summarize_market_alignment(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[(row.get("symbol", "").upper(), row.get("timeframe", "").upper(), row.get("side", "").upper())].append(row)

    out: list[dict[str, object]] = []
    for (symbol, timeframe, side), items in sorted(groups.items()):
        states = Counter(row.get("state", "") for row in items)
        reasons = Counter(reason for row in items for reason in split_factors(row.get("reasons", "")))
        top_state, top_state_count = states.most_common(1)[0]
        top_reason, top_reason_count = reasons.most_common(1)[0] if reasons else ("", 0)
        align = [as_float(row.get("alignment_score")) for row in items]
        structural = [as_float(row.get("structural_score")) for row in items]
        align_f = [value for value in align if value is not None]
        structural_f = [value for value in structural if value is not None]
        out.append(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "side": side,
                "blocked_by_market_alignment": len(items),
                "top_state": top_state,
                "top_state_count": top_state_count,
                "top_state_pct": pct(top_state_count, len(items)),
                "top_reason": top_reason,
                "top_reason_count": top_reason_count,
                "avg_alignment_score": f"{mean(align_f):.3f}" if align_f else "",
                "avg_structural_score": f"{mean(structural_f):.3f}" if structural_f else "",
            }
        )
    return out


def load_outcomes() -> dict[tuple[str, str, str], dict[str, str]]:
    path = ROOT / "reports" / "signal_outcomes" / "recent_5d_m15_h1_h4_by_symbol_timeframe_side.csv"
    if not path.exists():
        return {}
    return {
        (row.get("symbol", "").upper(), row.get("timeframe", "").upper(), row.get("side", "").upper()): row
        for row in iter_csv(path)
    }


def summarize_text_log_guards() -> list[dict[str, object]]:
    patterns: list[tuple[str, re.Pattern[str]]] = [
        ("ema_guard", re.compile(r"EMA_GUARD bloqueou (?P<side>BUY|SELL) (?P<symbol>[A-Z0-9]+) (?P<timeframe>M\d+|H\d+|D\d+)")),
        ("extreme_guard", re.compile(r"EXTREME_GUARD bloqueou (?P<side>BUY|SELL) (?P<symbol>[A-Z0-9]+) (?P<timeframe>M\d+|H\d+|D\d+)")),
        ("market_alignment", re.compile(r"(?P<strategy>STRATEGY\d+) (?P<symbol>[A-Z0-9]+) (?P<timeframe>M\d+|H\d+|D\d+) market_alignment block: side=(?P<side>BUY|SELL) state=(?P<state>[a-z_]+)")),
        ("timeframe_consensus", re.compile(r"(?P<strategy>STRATEGY\d+) (?P<symbol>[A-Z0-9]+) (?P<timeframe>M\d+|H\d+|D\d+) timeframe_consensus block: side=(?P<side>BUY|SELL) state=(?P<state>[a-z_]+)")),
        ("risk_engine", re.compile(r"(?P<strategy>STRATEGY\d+) (?P<symbol>[A-Z0-9]+) (?P<timeframe>M\d+|H\d+|D\d+) risk_engine block: state=(?P<state>[a-z_]+)")),
        ("correlation_guard", re.compile(r"(?P<strategy>STRATEGY\d+) (?P<symbol>[A-Z0-9]+) (?P<side>BUY|SELL) bloqueada por correlacao")),
        ("price_candle_guard", re.compile(r"(?P<strategy>STRATEGY\d+) (?P<symbol>[A-Z0-9]+) (?P<timeframe>M\d+|H\d+|D\d+) (?P<side>BUY|SELL) bloqueada por preco/candle")),
    ]
    counts: dict[tuple[str, str, str, str, str], int] = defaultdict(int)
    for path in sorted((ROOT / "logs").glob("fusion_*.log*")):
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for line in lines:
            for guard, pattern in patterns:
                match = pattern.search(line)
                if not match:
                    continue
                symbol = match.groupdict().get("symbol", "").upper()
                timeframe = match.groupdict().get("timeframe", "").upper() or "NA"
                side = match.groupdict().get("side", "").upper() or "NA"
                state = match.groupdict().get("state", "") or ""
                counts[(symbol, timeframe, side, guard, state)] += 1
                break
    return [
        {
            "symbol": symbol,
            "timeframe": timeframe,
            "side": side,
            "guard": guard,
            "state": state,
            "count": count,
        }
        for (symbol, timeframe, side, guard, state), count in sorted(counts.items(), key=lambda item: -item[1])
    ]


def recommendations(
    group_rows: list[dict[str, object]],
    ma_rows: list[dict[str, object]],
    outcomes: dict[tuple[str, str, str], dict[str, str]],
) -> list[dict[str, object]]:
    ma_index = {
        (row["symbol"], row["timeframe"], row["side"]): row
        for row in ma_rows
    }
    out: list[dict[str, object]] = []
    for row in group_rows:
        key = (str(row["symbol"]), str(row["timeframe"]), str(row["side"]))
        outcome = outcomes.get(key, {})
        signals = int(float(outcome.get("signals") or 0)) if outcome else 0
        h3_avg = as_float(outcome.get("h3_avg_points"))
        h3_acc = as_float(outcome.get("h3_acc"))
        ma = ma_index.get(key, {})
        blocked = int(row["blocked"])
        top_blocker = str(row["top_blocker"])
        blocked_ma = int(ma.get("blocked_by_market_alignment", 0) or 0)

        if h3_avg is not None and h3_avg > 20 and h3_acc is not None and h3_acc >= 55 and blocked >= 10:
            action = "consider_relax"
            rationale = "historico_h3_positivo_e_muitos_bloqueios"
        elif h3_avg is not None and h3_avg < 0 and blocked >= 10:
            action = "keep_or_tighten"
            rationale = "historico_h3_negativo_filtrar_ajuda"
        elif top_blocker in {"portfolio_exposure", "execution_engine"} and blocked >= 20:
            action = "review_risk_execution"
            rationale = "bloqueio_dominante_operacional"
        elif blocked_ma >= 20:
            action = "review_market_alignment"
            rationale = "muitos_bloqueios_de_alinhamento_recente"
        else:
            action = "monitor"
            rationale = "amostra_ou_edge_insuficiente"

        out.append(
            {
                "symbol": key[0],
                "timeframe": key[1],
                "side": key[2],
                "blocked_decision_audit": blocked,
                "blocked_market_alignment_recent": blocked_ma,
                "top_blocker": top_blocker,
                "outcome_signals": signals,
                "h3_acc": f"{h3_acc:.2f}" if h3_acc is not None else "",
                "h3_avg_points": f"{h3_avg:.2f}" if h3_avg is not None else "",
                "recommendation": action,
                "rationale": rationale,
            }
        )
    return sorted(out, key=lambda item: (str(item["recommendation"]) != "consider_relax", -int(item["blocked_decision_audit"])))


def write_markdown(
    signals: list[BlockedSignal],
    symbol_rows: list[dict[str, object]],
    group_rows: list[dict[str, object]],
    ma_rows: list[dict[str, object]],
    recs: list[dict[str, object]],
    log_guards: list[dict[str, object]],
) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    top_symbols = sorted(symbol_rows, key=lambda row: -int(row["blocked_total"]))[:20]
    top_groups = sorted(group_rows, key=lambda row: -int(row["blocked"]))[:25]
    top_ma = sorted(ma_rows, key=lambda row: -int(row["blocked_by_market_alignment"]))[:25]
    top_log_guards = sorted(log_guards, key=lambda row: -int(row["count"]))[:25]
    relax = [row for row in recs if row["recommendation"] == "consider_relax"][:25]
    tighten = [row for row in recs if row["recommendation"] == "keep_or_tighten"][:25]

    lines = [
        "# Filter Block Analysis",
        "",
        f"Generated at: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Scope",
        "",
        f"- Decision-audit blocked signals: {len(signals)}",
        f"- Symbols with blocked signals: {len(symbol_rows)}",
        f"- Symbol/timeframe/side groups: {len(group_rows)}",
        "",
        "## Top Blocked Symbols",
        "",
        "| Symbol | Total | BUY | SELL | Top TF | Top blocker | Pct |",
        "|---|---:|---:|---:|---|---|---:|",
    ]
    for row in top_symbols:
        lines.append(
            f"| {row['symbol']} | {row['blocked_total']} | {row['blocked_buy']} | {row['blocked_sell']} | "
            f"{row['top_timeframe']} | {row['top_blocker']} | {row['top_blocker_pct']} |"
        )

    lines += [
        "",
        "## Top Blocked Symbol/Timeframe/Side",
        "",
        "| Symbol | TF | Side | Blocked | Top blocker | Pct | Avg tradeability | Avg conflict | Avg consensus |",
        "|---|---|---|---:|---|---:|---:|---:|---:|",
    ]
    for row in top_groups:
        lines.append(
            f"| {row['symbol']} | {row['timeframe']} | {row['side']} | {row['blocked']} | {row['top_blocker']} | "
            f"{row['top_blocker_pct']} | {row['avg_tradeability']} | {row['avg_conflict']} | {row['avg_consensus']} |"
        )

    lines += [
        "",
        "## Recent Market Alignment Blocks",
        "",
        "| Symbol | TF | Side | Blocks | State | Reason | Avg align | Avg structural |",
        "|---|---|---|---:|---|---|---:|---:|",
    ]
    for row in top_ma:
        lines.append(
            f"| {row['symbol']} | {row['timeframe']} | {row['side']} | {row['blocked_by_market_alignment']} | "
            f"{row['top_state']} | {row['top_reason']} | {row['avg_alignment_score']} | {row['avg_structural_score']} |"
        )

    lines += [
        "",
        "## Text Log Guard Blocks",
        "",
        "| Symbol | TF | Side | Guard | State | Count |",
        "|---|---|---|---|---|---:|",
    ]
    for row in top_log_guards:
        lines.append(
            f"| {row['symbol']} | {row['timeframe']} | {row['side']} | {row['guard']} | {row['state']} | {row['count']} |"
        )

    lines += [
        "",
        "## Candidate Relaxations",
        "",
        "| Symbol | TF | Side | Blocked | MA blocks | Top blocker | H3 acc | H3 avg pts |",
        "|---|---|---|---:|---:|---|---:|---:|",
    ]
    for row in relax:
        lines.append(
            f"| {row['symbol']} | {row['timeframe']} | {row['side']} | {row['blocked_decision_audit']} | "
            f"{row['blocked_market_alignment_recent']} | {row['top_blocker']} | {row['h3_acc']} | {row['h3_avg_points']} |"
        )

    lines += [
        "",
        "## Candidate Keep/Tighten",
        "",
        "| Symbol | TF | Side | Blocked | Top blocker | H3 acc | H3 avg pts |",
        "|---|---|---|---:|---|---:|---:|",
    ]
    for row in tighten:
        lines.append(
            f"| {row['symbol']} | {row['timeframe']} | {row['side']} | {row['blocked_decision_audit']} | "
            f"{row['top_blocker']} | {row['h3_acc']} | {row['h3_avg_points']} |"
        )

    (REPORT_DIR / "blocked_signal_analysis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_symbol_plan(recs: list[dict[str, object]], symbol_rows: list[dict[str, object]]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    by_symbol: dict[str, list[dict[str, object]]] = defaultdict(list)
    symbol_index = {str(row["symbol"]): row for row in symbol_rows}
    for rec in recs:
        by_symbol[str(rec["symbol"])].append(rec)

    lines = [
        "# Configuration Plan By Symbol",
        "",
        "This is a measurement-based plan. It does not change config automatically.",
        "",
        "Legend:",
        "",
        "- consider_relax: historical H3 outcome is positive and blocks are frequent.",
        "- keep_or_tighten: historical H3 outcome is negative, so the current block is probably useful.",
        "- review_market_alignment: recent structural blocks are high; inspect before relaxing.",
        "- monitor: no enough matched outcome edge, or missing outcome sample.",
        "",
    ]

    for symbol in sorted(by_symbol):
        summary = symbol_index.get(symbol, {})
        lines.append(f"## {symbol}")
        if summary:
            lines.append(
                f"Blocked total: {summary['blocked_total']} "
                f"(BUY {summary['blocked_buy']}, SELL {summary['blocked_sell']}); "
                f"main blocker: {summary['top_blocker']} ({summary['top_blocker_pct']}%)."
            )
        symbol_recs = sorted(
            by_symbol[symbol],
            key=lambda row: (
                str(row["recommendation"]) != "consider_relax",
                str(row["recommendation"]) != "keep_or_tighten",
                -int(row["blocked_decision_audit"]),
            ),
        )
        lines.append("")
        lines.append("| TF | Side | Blocks | MA blocks | Top blocker | H3 acc | H3 pts | Action |")
        lines.append("|---|---|---:|---:|---|---:|---:|---|")
        for row in symbol_recs:
            lines.append(
                f"| {row['timeframe']} | {row['side']} | {row['blocked_decision_audit']} | "
                f"{row['blocked_market_alignment_recent']} | {row['top_blocker']} | "
                f"{row['h3_acc']} | {row['h3_avg_points']} | {row['recommendation']} |"
            )
        lines.append("")

    (REPORT_DIR / "configuration_plan_by_symbol.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    decision_signals = load_decision_events()
    engine_rows = load_engine_rows()
    ma_raw_rows = load_market_alignment_rows()
    group_rows, symbol_rows = summarize_decision_events(decision_signals)
    engine_summary = summarize_engine_rows(engine_rows)
    ma_rows = summarize_market_alignment(ma_raw_rows)
    log_guards = summarize_text_log_guards()
    recs = recommendations(group_rows, ma_rows, load_outcomes())

    write_csv(
        REPORT_DIR / "blocked_by_symbol.csv",
        sorted(symbol_rows, key=lambda row: -int(row["blocked_total"])),
        ["symbol", "blocked_total", "blocked_buy", "blocked_sell", "top_timeframe", "top_blocker", "top_blocker_count", "top_blocker_pct"],
    )
    write_csv(
        REPORT_DIR / "blocked_by_symbol_timeframe_side.csv",
        sorted(group_rows, key=lambda row: -int(row["blocked"])),
        [
            "symbol",
            "timeframe",
            "side",
            "blocked",
            "top_blocker",
            "top_blocker_count",
            "top_blocker_pct",
            "avg_tradeability",
            "avg_conflict",
            "avg_consensus",
        ],
    )
    write_csv(
        REPORT_DIR / "blocked_engine_roles.csv",
        sorted(engine_summary, key=lambda row: -int(row["rows"])),
        ["symbol", "timeframe", "side", "engine", "block_signal_role", "rows", "top_state", "top_state_count", "top_state_pct"],
    )
    write_csv(
        REPORT_DIR / "market_alignment_blocks_recent.csv",
        sorted(ma_rows, key=lambda row: -int(row["blocked_by_market_alignment"])),
        [
            "symbol",
            "timeframe",
            "side",
            "blocked_by_market_alignment",
            "top_state",
            "top_state_count",
            "top_state_pct",
            "top_reason",
            "top_reason_count",
            "avg_alignment_score",
            "avg_structural_score",
        ],
    )
    write_csv(
        REPORT_DIR / "text_log_guard_blocks.csv",
        log_guards,
        ["symbol", "timeframe", "side", "guard", "state", "count"],
    )
    write_csv(
        REPORT_DIR / "configuration_recommendations.csv",
        recs,
        [
            "symbol",
            "timeframe",
            "side",
            "blocked_decision_audit",
            "blocked_market_alignment_recent",
            "top_blocker",
            "outcome_signals",
            "h3_acc",
            "h3_avg_points",
            "recommendation",
            "rationale",
        ],
    )
    write_markdown(decision_signals, symbol_rows, group_rows, ma_rows, recs, log_guards)
    write_symbol_plan(recs, symbol_rows)


if __name__ == "__main__":
    main()
