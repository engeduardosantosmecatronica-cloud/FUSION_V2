from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


TIMEFRAMES = ["M5", "M15", "M30", "H1", "H4", "D1"]


def latest_event_file(base: Path, pattern: str = "events_*.jsonl") -> Path | None:
    files = sorted(base.glob(pattern), key=lambda item: item.stat().st_mtime, reverse=True)
    return files[0] if files else None


def read_event_jsonl(path: str | Path | None, tail: int = 1000) -> pd.DataFrame:
    if not path:
        return pd.DataFrame()
    file_path = Path(path)
    if not file_path.exists():
        return pd.DataFrame()
    try:
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []
    for line in lines[-max(1, int(tail)) :]:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        data = event.get("data", {}) or {}
        if not isinstance(data, dict):
            data = {"value": data}
        candidate = data.get("candidate", {}) or {}
        result = data.get("result", {}) or {}
        row = {
            "timestamp": event.get("timestamp", ""),
            "type": event.get("type", ""),
            "source": event.get("source", ""),
            "event_id": event.get("event_id", ""),
            "correlation_id": event.get("correlation_id", ""),
            "symbol": data.get("symbol") or candidate.get("symbol") or "",
            "broker_symbol": data.get("broker_symbol") or candidate.get("broker_symbol") or "",
            "timeframe": data.get("timeframe") or candidate.get("timeframe") or "",
            "strategy": data.get("strategy") or candidate.get("strategy") or "",
            "direction": data.get("direction") or candidate.get("side") or "",
            "status": data.get("status") or result.get("decision") or "",
            "reason": data.get("reason") or result.get("reason") or "",
            "raw": data,
        }
        rows.append(row)
    return pd.DataFrame(rows)


def summarize_event_types(events_df: pd.DataFrame) -> pd.DataFrame:
    if events_df.empty or "type" not in events_df.columns:
        return pd.DataFrame(columns=["type", "count"])
    return (
        events_df["type"]
        .fillna("")
        .astype(str)
        .value_counts()
        .rename_axis("type")
        .reset_index(name="count")
    )


def events_to_decision_audit_frames(events_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if events_df.empty or "type" not in events_df.columns:
        return pd.DataFrame(), pd.DataFrame()
    decisions = events_df[events_df["type"].astype(str).eq("DECISION")].copy()
    if decisions.empty:
        return pd.DataFrame(), pd.DataFrame()
    events: list[dict[str, Any]] = []
    engines: list[dict[str, Any]] = []
    for _, row in decisions.sort_values("timestamp").iterrows():
        data = row.get("raw", {}) or {}
        if not isinstance(data, dict):
            data = {}
        candidate = data.get("candidate", {}) or {}
        result = data.get("result", {}) or {}
        explanation = data.get("explanation", {}) or {}
        event_row = {
            "timestamp": row.get("timestamp", data.get("timestamp", "")),
            "correlation_id": row.get("correlation_id", data.get("correlation_id", "")),
            "symbol": candidate.get("symbol", row.get("symbol", "")),
            "broker_symbol": candidate.get("broker_symbol", row.get("broker_symbol", "")),
            "timeframe": candidate.get("timeframe", row.get("timeframe", "")),
            "side": candidate.get("side", candidate.get("direction", row.get("direction", ""))),
            "strategy": candidate.get("strategy", row.get("strategy", "")),
            "p_buy": float(candidate.get("p_buy", 0.0) or 0.0),
            "p_sell": float(candidate.get("p_sell", 0.0) or 0.0),
            "decision": result.get("decision", row.get("status", "")),
            "reason": result.get("reason", row.get("reason", "")),
            "consensus_score": float(result.get("consensus_score", 0.0) or 0.0),
            "conflict_score": float(result.get("conflict_score", 0.0) or 0.0),
            "tradeability_score": float(result.get("tradeability_score", 0.0) or 0.0),
            "position_multiplier": float(result.get("position_multiplier", 1.0) or 1.0),
            "xai_final_score": float(explanation.get("final_score", 0.0) or 0.0),
            "xai_confidence_band": explanation.get("confidence_band", ""),
            "xai_summary": explanation.get("summary", ""),
            "xai_positive": "; ".join(str(item.get("factor", "")) for item in explanation.get("top_positive_factors", []) or []),
            "xai_negative": "; ".join(str(item.get("factor", "")) for item in explanation.get("top_negative_factors", []) or []),
            "source": "event_bus",
        }
        events.append(event_row)
        for engine in data.get("engines", []) or []:
            features = engine.get("features", {}) or {}
            engines.append(
                {
                    **event_row,
                    "engine": engine.get("engine", ""),
                    "engine_state": engine.get("state", ""),
                    "engine_direction": engine.get("direction", ""),
                    "engine_score": float(engine.get("score", 0.0) or 0.0),
                    "engine_confidence": float(engine.get("confidence", 0.0) or 0.0),
                    "negative_count": len(engine.get("negative_factors", []) or []),
                    "warning_count": len(engine.get("warnings", []) or []),
                    "positive_count": len(engine.get("positive_factors", []) or []),
                    "positive_factors": "; ".join(str(item) for item in engine.get("positive_factors", []) or []),
                    "negative_factors": "; ".join(str(item) for item in engine.get("negative_factors", []) or []),
                    "warnings": "; ".join(str(item) for item in engine.get("warnings", []) or []),
                    "feature_coverage": features.get("feature_coverage"),
                    "session_fit_score": features.get("session_fit_score"),
                    "risk_score": features.get("risk_score"),
                    "position_multiplier_suggested": features.get("position_multiplier_suggested"),
                    "model_type": features.get("model_type"),
                    "ensemble_agreement": features.get("ensemble_agreement"),
                    "calibrated_probability": features.get("calibrated_probability"),
                    "quality_floor": features.get("quality_floor"),
                    "penalty": features.get("penalty"),
                    "features_json": json.dumps(features, ensure_ascii=False, default=str),
                }
            )
    return pd.DataFrame(events), pd.DataFrame(engines)


def events_to_status_table(events_df: pd.DataFrame) -> pd.DataFrame:
    if events_df.empty:
        return pd.DataFrame()
    operational = events_df[events_df["type"].isin(["SIGNAL", "DECISION", "ORDER_RESULT"])].copy()
    if operational.empty:
        return pd.DataFrame()
    status_rows = []
    for (symbol, timeframe), group in operational.groupby(["symbol", "timeframe"], dropna=False):
        group = group.sort_values("timestamp")
        latest_signal = group[group["type"] == "SIGNAL"].tail(1)
        latest_decision = group[group["type"] == "DECISION"].tail(1)
        latest_order = group[group["type"] == "ORDER_RESULT"].tail(1)
        latest = group.tail(1).iloc[0]
        p_buy = 0.0
        p_sell = 0.0
        signal = 0
        if not latest_signal.empty:
            raw = latest_signal.iloc[0].get("raw", {}) or {}
            p_buy = float(raw.get("p_buy", 0.0) or 0.0)
            p_sell = float(raw.get("p_sell", 0.0) or 0.0)
            signal = int(raw.get("raw_prediction", 0) or 0)
        reason = ""
        status = latest.get("status", "") or latest.get("type", "")
        if not latest_decision.empty:
            decision_row = latest_decision.iloc[0]
            reason = str(decision_row.get("reason", "") or "")
            status = str(decision_row.get("status", "") or status)
        if not latest_order.empty:
            order_row = latest_order.iloc[0]
            reason = str(order_row.get("reason", "") or reason)
            status = str(order_row.get("status", "") or status)
        status_rows.append(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "signal": signal,
                "p_buy": p_buy,
                "p_sell": p_sell,
                "status": status,
                "reason": reason or str(latest.get("reason", "") or ""),
                "source": "event_bus",
                "timestamp": latest.get("timestamp", ""),
            }
        )
    if not status_rows:
        return pd.DataFrame()
    long_df = pd.DataFrame(status_rows)
    rows = []
    for symbol, group in long_df.sort_values("timestamp").groupby("symbol", dropna=False):
        row = {"symbol": "GOLD" if str(symbol).upper() == "XAUUSD" else symbol}
        reasons = []
        for tf in TIMEFRAMES:
            item = group[group["timeframe"].astype(str).str.upper() == tf]
            if item.empty:
                row[tf] = "-/-"
                continue
            rec = item.sort_values("timestamp").iloc[-1]
            signal = int(rec.get("signal", 0) or 0)
            p_buy = float(rec.get("p_buy", 0.0) or 0.0)
            p_sell = float(rec.get("p_sell", 0.0) or 0.0)
            if signal == 1:
                row[tf] = f"B:{p_buy:.3f}"
            elif signal == -1:
                row[tf] = f"S:{p_sell:.3f}"
            else:
                row[tf] = f"{p_buy:.3f}/{p_sell:.3f}"
            reason = str(rec.get("reason", "") or "")
            if reason:
                reasons.append(f"{tf}:{reason}")
        row["motivos"] = " | ".join(reasons[:4]) if reasons else "-"
        row["_source"] = "event_bus"
        row["_last_timestamp"] = group.sort_values("timestamp").iloc[-1].get("timestamp", "")
        rows.append(row)
    return pd.DataFrame(rows).sort_values("symbol")


def read_latest_oms_snapshot(base: Path) -> dict[str, Any]:
    file_path = latest_event_file(base, pattern="oms_snapshot_*.json")
    if not file_path:
        return {}
    try:
        return json.loads(file_path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return {}
