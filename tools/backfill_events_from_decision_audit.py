from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]


def write_event(handle, event_type: str, source: str, data: dict, timestamp: str, correlation_id: str) -> None:
    payload = {
        "version": "fusion_event_v1_backfill",
        "event_id": uuid4().hex,
        "correlation_id": correlation_id,
        "timestamp": timestamp or datetime.now().isoformat(),
        "type": event_type,
        "source": source,
        "data": data,
    }
    handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Converte decision_audit antigo em eventos estruturados.")
    parser.add_argument("--date", required=True, help="Data YYYYMMDD.")
    parser.add_argument("--input-dir", default="logs/decision_audit")
    parser.add_argument("--output-dir", default="logs/events_backfill")
    parser.add_argument("--include-engine-results", action="store_true")
    args = parser.parse_args()

    input_path = ROOT / args.input_dir / f"decision_audit_{args.date}.jsonl"
    if not input_path.exists():
        raise SystemExit(f"Arquivo nao encontrado: {input_path}")
    output_dir = ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"events_{args.date}.jsonl"

    events_count = 0
    with input_path.open("r", encoding="utf-8") as reader, output_path.open("w", encoding="utf-8") as writer:
        for line in reader:
            try:
                audit = json.loads(line)
            except json.JSONDecodeError:
                continue
            candidate = audit.get("candidate") or {}
            timestamp = audit.get("timestamp", "")
            correlation_id = audit.get("correlation_id") or (
                f"{candidate.get('symbol', '')}:{candidate.get('timeframe', '')}:"
                f"{candidate.get('strategy', '')}:{timestamp}"
            )
            if candidate.get("raw_prediction") in (1, 2):
                signal_data = {
                    "symbol": candidate.get("symbol", ""),
                    "broker_symbol": candidate.get("broker_symbol", ""),
                    "timeframe": candidate.get("timeframe", ""),
                    "strategy": "model_signal",
                    "direction": candidate.get("side", ""),
                    "p_buy": candidate.get("p_buy", 0.0),
                    "p_sell": candidate.get("p_sell", 0.0),
                    "raw_prediction": candidate.get("raw_prediction", 0),
                    "metadata": {"backfill": True},
                }
                write_event(writer, "SIGNAL", "BackfillDecisionAudit", signal_data, timestamp, correlation_id)
                events_count += 1
            if args.include_engine_results:
                for engine in audit.get("engines", []) or []:
                    write_event(
                        writer,
                        "ENGINE_RESULT",
                        str(engine.get("engine", "") or "BackfillEngine"),
                        {"candidate": candidate, "engine": engine},
                        timestamp,
                        correlation_id,
                    )
                    events_count += 1
            write_event(writer, "DECISION", "BackfillDecisionAudit", audit, timestamp, correlation_id)
            events_count += 1

    print(f"Eventos gerados: {events_count}")
    print(f"Saida: {output_path}")


if __name__ == "__main__":
    main()
