from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Valida prontidao operacional do FUSION Event-Driven.")
    parser.add_argument("--date", required=True, help="Data YYYYMMDD.")
    parser.add_argument("--minutes", type=int, default=30, help="Janela recente para validar runtime.")
    parser.add_argument("--max-stale-minutes", type=int, default=15, help="Idade maxima aceitavel do ultimo evento.")
    parser.add_argument("--events-dir", default="logs/events")
    parser.add_argument("--output-dir", default="reports/operational_readiness")
    parser.add_argument("--require-order", action="store_true", help="Exige ORDER_REQUEST/ORDER_RESULT recente para status OK.")
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def load_events(date: str, events_dir: str) -> list[dict[str, Any]]:
    events = read_jsonl(ROOT / events_dir / f"events_{date}.jsonl")
    seen = set()
    unique = []
    for event in events:
        key = event.get("event_id") or json.dumps(event, sort_keys=True, default=str)
        if key in seen:
            continue
        seen.add(key)
        unique.append(event)
    return sorted(unique, key=lambda item: item.get("timestamp", ""))


def parse_ts(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def read_config() -> dict[str, Any]:
    path = ROOT / "config" / "fusion_config.yaml"
    if not path.exists():
        return {}
    try:
        import yaml

        data = yaml.safe_load(path.read_text(encoding="utf-8", errors="ignore")) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def data_of(event: dict[str, Any]) -> dict[str, Any]:
    data = event.get("data") or {}
    return data if isinstance(data, dict) else {}


def add_check(checks: list[dict[str, Any]], name: str, status: str, detail: str) -> None:
    checks.append({"name": name, "status": status, "detail": detail})


def main() -> None:
    args = parse_args()
    config = read_config()
    event_bus_cfg = config.get("event_bus", {}) if isinstance(config.get("event_bus", {}), dict) else {}
    trading_cfg = config.get("trading", {}) if isinstance(config.get("trading", {}), dict) else {}
    oms_cfg = config.get("oms", {}) if isinstance(config.get("oms", {}), dict) else {}

    events = load_events(args.date, args.events_dir)
    checks: list[dict[str, Any]] = []
    by_type = Counter(str(event.get("type", "") or "") for event in events)

    add_check(
        checks,
        "event_bus_config",
        "OK" if bool(event_bus_cfg.get("event_log_enabled", False)) else "FAIL",
        f"event_log_enabled={event_bus_cfg.get('event_log_enabled')}",
    )
    add_check(
        checks,
        "event_bus_async",
        "OK" if bool(event_bus_cfg.get("use_async", False)) else "WARN",
        f"use_async={event_bus_cfg.get('use_async')}",
    )
    add_check(
        checks,
        "oms_snapshot_config",
        "OK" if bool(oms_cfg.get("snapshot_enabled", False)) else "WARN",
        f"snapshot_enabled={oms_cfg.get('snapshot_enabled')}",
    )
    add_check(
        checks,
        "allow_new_orders",
        "OK" if bool(trading_cfg.get("allow_new_orders", False)) else "WARN",
        f"allow_new_orders={trading_cfg.get('allow_new_orders')}",
    )

    if not events:
        add_check(checks, "events_file", "FAIL", f"Nenhum evento em {ROOT / args.events_dir / f'events_{args.date}.jsonl'}")
        recent = []
        latest_ts = None
    else:
        timestamps = [ts for ts in (parse_ts(event.get("timestamp")) for event in events) if ts]
        latest_ts = max(timestamps) if timestamps else None
        if latest_ts:
            stale_minutes = max(0.0, (datetime.now() - latest_ts).total_seconds() / 60.0)
            status = "OK" if stale_minutes <= max(1, int(args.max_stale_minutes)) else "FAIL"
            add_check(checks, "events_freshness", status, f"ultimo_evento={latest_ts.isoformat()} idade_min={stale_minutes:.1f}")
            cutoff = latest_ts - timedelta(minutes=max(1, int(args.minutes)))
            recent = [event for event in events if (parse_ts(event.get("timestamp")) or datetime.min) >= cutoff]
        else:
            add_check(checks, "events_freshness", "FAIL", "Eventos sem timestamp valido")
            recent = []

    recent_by_type = Counter(str(event.get("type", "") or "") for event in recent)
    add_check(
        checks,
        "recent_signal_decision",
        "OK" if recent_by_type["SIGNAL"] and recent_by_type["DECISION"] else "WARN",
        f"SIGNAL={recent_by_type['SIGNAL']} DECISION={recent_by_type['DECISION']} janela_min={args.minutes}",
    )
    add_check(
        checks,
        "recent_engine_results",
        "OK" if recent_by_type["ENGINE_RESULT"] else "WARN",
        f"ENGINE_RESULT={recent_by_type['ENGINE_RESULT']} janela_min={args.minutes}",
    )
    add_check(
        checks,
        "recent_oms_events",
        "OK" if recent_by_type["POSITION_UPDATE"] or recent_by_type["ACCOUNT_UPDATE"] else "WARN",
        f"POSITION_UPDATE={recent_by_type['POSITION_UPDATE']} ACCOUNT_UPDATE={recent_by_type['ACCOUNT_UPDATE']}",
    )

    by_corr: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in recent:
        by_corr[str(event.get("correlation_id") or event.get("event_id"))].append(event)

    decision_without_signal = 0
    decision_without_engine = 0
    request_without_result = 0
    result_without_request = 0
    order_cycles = 0
    for group in by_corr.values():
        types = Counter(str(event.get("type", "") or "") for event in group)
        if types["DECISION"] and not types["SIGNAL"]:
            decision_without_signal += 1
        if types["DECISION"] and not types["ENGINE_RESULT"]:
            decision_without_engine += 1
        if types["ORDER_REQUEST"]:
            order_cycles += 1
        if types["ORDER_REQUEST"] and not types["ORDER_RESULT"]:
            request_without_result += 1
        if types["ORDER_RESULT"] and not types["ORDER_REQUEST"]:
            result_without_request += 1

    add_check(checks, "decision_correlation", "OK" if decision_without_signal == 0 else "WARN", f"decision_sem_signal={decision_without_signal}")
    add_check(checks, "engine_correlation", "OK" if decision_without_engine == 0 else "WARN", f"decision_sem_engine={decision_without_engine}")
    add_check(
        checks,
        "order_lifecycle",
        "OK"
        if order_cycles and request_without_result == 0 and result_without_request == 0
        else ("WARN" if order_cycles == 0 and args.require_order else ("INFO" if order_cycles == 0 else "FAIL")),
        f"order_cycles={order_cycles} request_sem_result={request_without_result} result_sem_request={result_without_request}",
    )
    add_check(
        checks,
        "order_result_presence",
        "OK" if by_type["ORDER_RESULT"] else ("WARN" if args.require_order else "INFO"),
        f"ORDER_RESULT_total={by_type['ORDER_RESULT']} TRADE_UPDATE_total={by_type['TRADE_UPDATE']} POSITION_UPDATE_total={by_type['POSITION_UPDATE']}",
    )

    status_rank = {"FAIL": 3, "WARN": 2, "INFO": 1, "OK": 0}
    overall = max((item["status"] for item in checks), key=lambda value: status_rank.get(value, 0))
    output_dir = ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"operational_readiness_{args.date}.md"
    json_path = output_dir / f"operational_readiness_{args.date}.json"

    lines = [
        "# Operational Readiness",
        "",
        f"- Data: {args.date}",
        f"- Status geral: {overall}",
        f"- Eventos totais: {len(events)}",
        f"- Eventos recentes: {len(recent)}",
        f"- Ultimo evento: {latest_ts.isoformat() if latest_ts else '-'}",
        "",
        "## Checks",
        "",
    ]
    for check in checks:
        lines.append(f"- {check['status']} | {check['name']} | {check['detail']}")
    lines.extend(["", "## Tipos Recentes", ""])
    for event_type, count in recent_by_type.most_common():
        lines.append(f"- {event_type}: {count}")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    json_path.write_text(json.dumps({"overall": overall, "checks": checks, "recent_types": dict(recent_by_type)}, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Status geral: {overall}")
    for check in checks:
        print(f"{check['status']:4} | {check['name']} | {check['detail']}")
    print(f"Saida: {output_dir}")


if __name__ == "__main__":
    main()
