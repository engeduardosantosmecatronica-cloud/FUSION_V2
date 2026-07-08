from __future__ import annotations

import re
import json
import sys
import time
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

try:
    import plotly.express as px
except Exception:  # pragma: no cover - dashboard dependency
    px = None

try:
    import plotly.graph_objects as go
except Exception:  # pragma: no cover - dashboard dependency
    go = None


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dashboard.event_readers import (
        events_to_decision_audit_frames,
        events_to_status_table,
        latest_event_file,
        read_event_jsonl,
        read_latest_oms_snapshot,
        summarize_event_types,
    )
except ModuleNotFoundError:
    from event_readers import (
        events_to_decision_audit_frames,
        events_to_status_table,
        latest_event_file,
        read_event_jsonl,
        read_latest_oms_snapshot,
        summarize_event_types,
    )

LOG_DIR = ROOT / "logs"
REPORTS_DIR = ROOT / "reports"
TIMEFRAMES = ["M5", "M15", "M30", "H1", "H4", "D1"]
INSTITUTIONAL_ENGINES = [
    "market_regime",
    "volatility_engine",
    "session_context",
    "macro_flow",
    "portfolio_exposure",
    "portfolio_correlation",
    "market_structure",
    "feature_engineering",
    "entry_timing",
    "execution_engine",
    "risk_engine",
    "meta_model_ensemble",
    "confidence_calibration",
    "context_engine",
    "consensus_engine",
    "opportunity_engine",
    "ai_advisor",
]

REASON_HELP = {
    "preco_candle_nao_confirmado": (
        "Filtro de preco/candle bloqueou. BUY exige preco atual acima da abertura do candle atual "
        "e candle anterior de alta. SELL exige preco atual abaixo da abertura atual e candle anterior de baixa."
    ),
    "ema_nao_alinhada": "Filtro de EMAs bloqueou. As EMAs 9, 21 e 50 nao estao alinhadas, distantes ou inclinadas o suficiente.",
    "sem_feature": "A estrategia precisa de uma regra aprovada em features_backteste_dinamica.csv, mas nao encontrou uma valida.",
    "POSICAO_JA_EXISTE": "Ja existe posicao aberta para o ativo dentro do limite configurado.",
    "aguardando_setup": "A estrategia esta ativa, mas o setup especifico ainda nao apareceu.",
    "cooldown": "A estrategia esta aguardando o intervalo minimo entre trades.",
    "allow_new_orders_false": "Trava global ativa: trading.allow_new_orders=false em config/fusion_config.yaml.",
    "ordens_bloqueadas_config": "Motivo legado equivalente a trading.allow_new_orders=false.",
    "market_structure_block": "Market Structure bloquearia/ bloqueou conforme modo configurado.",
}


def latest_file(pattern: str, base: Path = LOG_DIR) -> Path | None:
    files = sorted(base.glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)
    return files[0] if files else None


@st.cache_data(ttl=10)
def read_text(path: str) -> str:
    file_path = Path(path)
    if not file_path.exists():
        return ""
    return file_path.read_text(encoding="utf-8", errors="ignore")


@st.cache_data(ttl=10)
def read_csv(path: str) -> pd.DataFrame:
    file_path = Path(path)
    if not file_path.exists() or file_path.stat().st_size <= 2:
        return pd.DataFrame()
    try:
        return pd.read_csv(file_path)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=10)
def read_runtime_config(path: str) -> dict:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    raw = file_path.read_text(encoding="utf-8", errors="ignore")
    try:
        import yaml

        data = yaml.safe_load(raw) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        parsed: dict[str, dict[str, object]] = {}
        section = ""
        for line in raw.splitlines():
            clean = line.split("#", 1)[0].rstrip()
            if not clean.strip():
                continue
            if not line.startswith((" ", "\t")) and clean.endswith(":"):
                section = clean[:-1].strip()
                parsed.setdefault(section, {})
                continue
            if section and ":" in clean:
                key, value = clean.strip().split(":", 1)
                value = value.strip().strip('"').strip("'")
                if value.lower() in {"true", "false"}:
                    parsed[section][key.strip()] = value.lower() == "true"
                else:
                    parsed[section][key.strip()] = value
        return parsed


@st.cache_data(ttl=30)
def read_latest_ohlcv(symbol: str, timeframe: str, bars: int = 220) -> pd.DataFrame:
    symbol = _raw_asset_symbol(str(symbol or "")).upper()
    timeframe = str(timeframe or "M5").upper()
    candidates = sorted((ROOT / "data" / "csv" / timeframe).glob(f"**/{symbol}.csv"))
    if not candidates and symbol == "XAUUSD":
        candidates = sorted((ROOT / "data" / "csv" / timeframe).glob("**/GOLD.csv"))
    if not candidates:
        return pd.DataFrame()
    path = max(candidates, key=lambda item: item.stat().st_mtime)
    try:
        from collections import deque

        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            header = handle.readline().strip()
            tail = deque(handle, maxlen=max(10, int(bars)))
        if not header or not tail:
            return pd.DataFrame()
        import io

        df = pd.read_csv(io.StringIO(header + "\n" + "".join(tail)))
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
        return df.dropna(subset=["date", "open", "high", "low", "close"]).tail(bars)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=10)
def read_decision_audit(path: str, tail: int = 500) -> tuple[pd.DataFrame, pd.DataFrame]:
    file_path = Path(path)
    if not file_path.exists():
        return pd.DataFrame(), pd.DataFrame()
    lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    events = []
    engines = []
    for line in lines[-max(1, int(tail)) :]:
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        candidate = event.get("candidate", {}) or {}
        result = event.get("result", {}) or {}
        explanation = event.get("explanation", {}) or {}
        event_row = {
            "timestamp": event.get("timestamp", ""),
            "correlation_id": event.get("correlation_id", ""),
            "symbol": candidate.get("symbol", ""),
            "timeframe": candidate.get("timeframe", ""),
            "side": candidate.get("side", ""),
            "strategy": candidate.get("strategy", ""),
            "p_buy": float(candidate.get("p_buy", 0.0) or 0.0),
            "p_sell": float(candidate.get("p_sell", 0.0) or 0.0),
            "decision": result.get("decision", ""),
            "reason": result.get("reason", ""),
            "consensus_score": float(result.get("consensus_score", 0.0) or 0.0),
            "conflict_score": float(result.get("conflict_score", 0.0) or 0.0),
            "tradeability_score": float(result.get("tradeability_score", 0.0) or 0.0),
            "position_multiplier": float(result.get("position_multiplier", 1.0) or 1.0),
            "xai_final_score": float(explanation.get("final_score", 0.0) or 0.0),
            "xai_confidence_band": explanation.get("confidence_band", ""),
            "xai_summary": explanation.get("summary", ""),
            "xai_positive": "; ".join(str(item.get("factor", "")) for item in explanation.get("top_positive_factors", []) or []),
            "xai_negative": "; ".join(str(item.get("factor", "")) for item in explanation.get("top_negative_factors", []) or []),
        }
        events.append(event_row)
        for engine in event.get("engines", []) or []:
            features = engine.get("features", {}) or {}
            positive_factors = engine.get("positive_factors", []) or []
            negative_factors = engine.get("negative_factors", []) or []
            warnings = engine.get("warnings", []) or []
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
                    "positive_factors": "; ".join(str(item) for item in positive_factors),
                    "negative_factors": "; ".join(str(item) for item in negative_factors),
                    "warnings": "; ".join(str(item) for item in warnings),
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


def extract_latest_dashboard(log_text: str) -> tuple[pd.DataFrame, str, str]:
    marker = "FUSION_V2 DASHBOARD"
    pos = log_text.rfind(marker)
    if pos < 0:
        return pd.DataFrame(), "", ""

    start = log_text.rfind("=", 0, pos)
    end = log_text.find("Legenda:", pos)
    if start < 0:
        start = pos
    if end < 0:
        end = len(log_text)

    block = log_text[start:end]
    after = log_text[end : min(len(log_text), end + 5000)]
    rows = []
    for line in block.splitlines():
        if "|" not in line:
            continue
        if line.strip().startswith(("ATIVO", "---", "===")):
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) < 8:
            continue
        symbol = parts[0]
        if not symbol or symbol.startswith("FUSION"):
            continue
        row = {"symbol": symbol}
        for index, tf in enumerate(TIMEFRAMES, start=1):
            row[tf] = parts[index] if index < len(parts) else ""
        row["motivos"] = parts[7] if len(parts) > 7 and parts[7] else "-"
        rows.append(row)
    return pd.DataFrame(rows), block, after


def parse_reason_tokens(text: str) -> pd.DataFrame:
    tokens = re.findall(
        r"(preco_candle_nao_confirmado|ema_nao_alinhada|sem_feature|POSICAO_JA_EXISTE|aguardando_setup|cooldown|allow_new_orders_false|ordens_bloqueadas_config|market_structure_block)",
        text,
    )
    if not tokens:
        return pd.DataFrame(columns=["motivo", "count"])
    return (
        pd.Series(tokens)
        .value_counts()
        .rename_axis("motivo")
        .reset_index(name="count")
    )


def parse_recent_events(log_text: str, limit: int = 300) -> pd.DataFrame:
    lines = log_text.splitlines()[-limit:]
    events = []
    for line in lines:
        if " | " not in line:
            continue
        kind = ""
        if "SINAL " in line:
            kind = "sinal"
        elif "[TRAILING " in line and "Novo SL" in line:
            kind = "trailing"
        elif "bloqueada" in line or "NAO EXECUTADA" in line or "sem feature" in line:
            kind = "bloqueio"
        elif "EXECUTADA" in line:
            kind = "ordem"
        if not kind:
            continue
        pieces = line.split(" | ", 3)
        events.append(
            {
                "timestamp": pieces[0] if pieces else "",
                "tipo": kind,
                "mensagem": pieces[-1] if pieces else line,
            }
        )
    return pd.DataFrame(events)


def _latest_trailing_alerts(log_text: str, limit: int = 800, max_items: int = 6) -> list[dict[str, str]]:
    alerts = []
    for line in log_text.splitlines()[-max(1, int(limit)) :]:
        if "[TRAILING " not in line or "Novo SL" not in line:
            continue
        pieces = line.split(" | ")
        timestamp = pieces[0].strip() if pieces else ""
        message = " | ".join(pieces[3:]).strip() if len(pieces) > 3 else line.strip()
        match = re.search(r"\[TRAILING\s+(BUY|SELL)\]\s+([A-Z0-9._-]+)", line)
        direction = match.group(1) if match else "-"
        symbol = _format_asset_symbol(match.group(2).upper()) if match else "-"
        alerts.append(
            {
                "key": f"trailing:{timestamp}:{symbol}:{message}",
                "kind": "trailing",
                "title": f"Trailing {direction} ajustado | {symbol}",
                "detail": message,
                "timestamp": timestamp,
            }
        )
    return alerts[-max_items:][::-1]


def _latest_signal_alerts(events_df: pd.DataFrame, max_items: int = 6) -> list[dict[str, str]]:
    if events_df.empty or "type" not in events_df.columns:
        return []
    signals = events_df[events_df["type"].astype(str).eq("SIGNAL")].copy()
    if signals.empty:
        return []
    alerts = []
    for _, row in signals.sort_values("timestamp", ascending=False).head(max_items).iterrows():
        raw = row.get("raw", {}) or {}
        if not isinstance(raw, dict):
            raw = {}
        symbol = _format_asset_symbol(str(row.get("symbol") or raw.get("symbol") or "-").upper())
        timeframe = str(row.get("timeframe") or raw.get("timeframe") or "-").upper()
        direction = str(row.get("direction") or raw.get("direction") or raw.get("side") or "-").upper()
        p_buy = _safe_float(raw.get("p_buy"), 0.0)
        p_sell = _safe_float(raw.get("p_sell"), 0.0)
        score = max(p_buy, p_sell)
        timestamp = str(row.get("timestamp") or "")
        key = str(row.get("event_id") or row.get("correlation_id") or f"signal:{timestamp}:{symbol}:{timeframe}:{direction}")
        alerts.append(
            {
                "key": key,
                "kind": "signal",
                "title": f"Sinal {direction} | {symbol} {timeframe}",
                "detail": f"p_buy={p_buy:.3f} | p_sell={p_sell:.3f} | score={score:.3f}",
                "timestamp": timestamp,
            }
        )
    return alerts


def _play_dashboard_sound(kind: str) -> None:
    frequency = 880 if kind == "signal" else 660
    duration = 170 if kind == "signal" else 230
    repeats = 2 if kind == "signal" else 1
    components.html(
        f"""
        <script>
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (AudioContext) {{
            const ctx = new AudioContext();
            let start = ctx.currentTime + 0.02;
            for (let i = 0; i < {repeats}; i++) {{
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = "sine";
                osc.frequency.value = {frequency};
                gain.gain.setValueAtTime(0.0001, start);
                gain.gain.exponentialRampToValueAtTime(0.18, start + 0.015);
                gain.gain.exponentialRampToValueAtTime(0.0001, start + ({duration} / 1000));
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start(start);
                osc.stop(start + ({duration} / 1000) + 0.02);
                start += ({duration} / 1000) + 0.08;
            }}
        }}
        </script>
        """,
        height=0,
        width=0,
    )


def render_live_alerts(
    structured_events_df: pd.DataFrame,
    log_text: str,
    enable_signal_alerts: bool,
    enable_trailing_alerts: bool,
    sound_enabled: bool,
    sound_cooldown_seconds: int,
) -> None:
    alerts: list[dict[str, str]] = []
    if enable_signal_alerts:
        alerts.extend(_latest_signal_alerts(structured_events_df, max_items=4))
    if enable_trailing_alerts:
        alerts.extend(_latest_trailing_alerts(log_text, max_items=4))
    alerts = sorted(alerts, key=lambda item: item.get("timestamp", ""), reverse=True)[:6]
    if not alerts:
        return

    latest = alerts[0]
    latest_key = str(latest.get("key", ""))
    initialized_key = "live_alerts_initialized"
    last_key_name = "last_live_alert_key"
    last_sound_name = "last_live_alert_sound_ts"
    if not st.session_state.get(initialized_key):
        st.session_state[initialized_key] = True
        st.session_state[last_key_name] = latest_key
        st.session_state[last_sound_name] = time.time()
    elif latest_key and latest_key != st.session_state.get(last_key_name):
        elapsed = time.time() - float(st.session_state.get(last_sound_name, 0.0) or 0.0)
        if sound_enabled and elapsed >= max(1, int(sound_cooldown_seconds)):
            _play_dashboard_sound(str(latest.get("kind", "signal")))
            st.session_state[last_sound_name] = time.time()
        st.session_state[last_key_name] = latest_key

    st.subheader("Alertas")
    cols = st.columns(min(3, len(alerts)))
    for index, alert in enumerate(alerts):
        with cols[index % len(cols)]:
            with st.container(border=True):
                st.markdown(f"**{alert.get('title', '-')}**")
                st.caption(str(alert.get("timestamp", "-")))
                st.caption(str(alert.get("detail", "-")))


def audit_to_status_table(events_df: pd.DataFrame) -> pd.DataFrame:
    if events_df.empty:
        return pd.DataFrame()
    latest = (
        events_df.sort_values("timestamp")
        .drop_duplicates(["symbol", "timeframe"], keep="last")
        .copy()
    )
    rows = []
    for symbol, group in latest.groupby("symbol"):
        row = {"symbol": "GOLD" if symbol == "XAUUSD" else symbol}
        reasons = []
        for tf in TIMEFRAMES:
            item = group[group["timeframe"] == tf]
            if item.empty:
                row[tf] = "-/-"
                continue
            rec = item.iloc[-1]
            side = str(rec.get("side", "") or "").upper()
            p_buy = float(rec.get("p_buy", 0.0) or 0.0)
            p_sell = float(rec.get("p_sell", 0.0) or 0.0)
            if side == "BUY":
                row[tf] = f"B:{p_buy:.3f}"
            elif side == "SELL":
                row[tf] = f"S:{p_sell:.3f}"
            else:
                row[tf] = f"{p_buy:.3f}/{p_sell:.3f}"
            reason = str(rec.get("reason", "") or "")
            if reason:
                reasons.append(f"{tf}:{reason}")
        row["motivos"] = " | ".join(reasons[:3]) if reasons else "-"
        rows.append(row)
    return pd.DataFrame(rows)


def reasons_from_audit(events_df: pd.DataFrame) -> pd.DataFrame:
    if events_df.empty or "reason" not in events_df.columns:
        return pd.DataFrame(columns=["motivo", "count"])
    reasons = events_df["reason"].dropna().astype(str)
    reasons = reasons[reasons.str.len() > 0]
    if reasons.empty:
        return pd.DataFrame(columns=["motivo", "count"])
    normalized = reasons.str.split(":", n=1).str[0]
    return normalized.value_counts().rename_axis("motivo").reset_index(name="count")


def latest_shadow_date_file(kind: str) -> Path | None:
    base = REPORTS_DIR / "market_structure_shadow"
    return latest_file(f"market_structure_shadow_{kind}_*.csv", base=base)


def latest_decision_audit_file() -> Path | None:
    return latest_file("decision_audit_*.jsonl", base=LOG_DIR / "decision_audit")


def metric_card(label: str, value: object, help_text: str = "") -> None:
    st.metric(label, value, help=help_text or None)


def inject_terminal_css() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: #080d14;
            color: #d7e2ee;
        }
        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 2rem;
        }
        div[data-testid="stMetric"] {
            background: #0f1722;
            border: 1px solid #1f2c3a;
            border-radius: 8px;
            padding: 0.75rem 0.9rem;
            box-shadow: 0 1px 0 rgba(255,255,255,0.03) inset;
        }
        div[data-testid="stMetric"] label {
            color: #8fa3b7;
            font-size: 0.78rem;
        }
        .terminal-header {
            display: flex;
            align-items: end;
            justify-content: space-between;
            gap: 1rem;
            padding: 0.65rem 0.85rem;
            background: linear-gradient(90deg, #0d1520, #101923);
            border: 1px solid #223142;
            border-radius: 8px;
            margin-bottom: 0.8rem;
        }
        .terminal-title {
            font-size: 1.15rem;
            font-weight: 700;
            letter-spacing: 0;
            color: #f4f8fb;
        }
        .terminal-subtitle {
            color: #8fa3b7;
            font-size: 0.78rem;
            margin-top: 0.2rem;
        }
        .terminal-badge {
            display: inline-flex;
            align-items: center;
            border: 1px solid #2c3e50;
            border-radius: 999px;
            padding: 0.18rem 0.55rem;
            color: #b9c7d6;
            background: #0b121b;
            font-size: 0.76rem;
            margin-left: 0.35rem;
            white-space: nowrap;
        }
        .watch-card {
            border: 1px solid #223142;
            border-radius: 8px;
            padding: 0.55rem 0.65rem;
            margin-bottom: 0.45rem;
            background: #0d1520;
        }
        .watch-symbol {
            color: #f5f8fb;
            font-weight: 700;
            font-size: 0.92rem;
        }
        .watch-meta {
            color: #8fa3b7;
            font-size: 0.73rem;
            margin-top: 0.18rem;
        }
        .tf-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(118px, 1fr));
            gap: 0.55rem;
            margin: 0.55rem 0 1rem 0;
        }
        .tf-card {
            border: 1px solid #26384a;
            border-radius: 8px;
            background: #0e1721;
            padding: 0.65rem;
            min-height: 86px;
        }
        .tf-card.buy { border-color: rgba(45, 212, 191, 0.55); }
        .tf-card.sell { border-color: rgba(248, 113, 113, 0.55); }
        .tf-card.empty { opacity: 0.72; }
        .tf-label {
            color: #8fa3b7;
            font-size: 0.72rem;
            text-transform: uppercase;
            margin-bottom: 0.25rem;
        }
        .tf-value {
            color: #edf5fc;
            font-size: 1rem;
            font-weight: 700;
        }
        .tf-side-buy { color: #2dd4bf; }
        .tf-side-sell { color: #fb7185; }
        .tf-note {
            color: #7f93a6;
            font-size: 0.72rem;
            margin-top: 0.3rem;
        }
        .reason-card {
            border-left: 3px solid #f59e0b;
            background: #101923;
            border-radius: 8px;
            padding: 0.55rem 0.65rem;
            margin-bottom: 0.45rem;
            border-top: 1px solid #243345;
            border-right: 1px solid #243345;
            border-bottom: 1px solid #243345;
        }
        .reason-title {
            color: #f5f8fb;
            font-weight: 700;
            font-size: 0.84rem;
        }
        .reason-line {
            color: #a9b8c7;
            font-size: 0.76rem;
            margin-top: 0.12rem;
        }
        .engine-card {
            border: 1px solid #243345;
            background: #0d1520;
            border-radius: 8px;
            padding: 0.65rem;
            margin-bottom: 0.5rem;
        }
        .engine-name {
            color: #edf5fc;
            font-size: 0.86rem;
            font-weight: 700;
        }
        .engine-meta {
            color: #93a8ba;
            font-size: 0.74rem;
            margin-top: 0.18rem;
        }
        .mini-divider {
            height: 1px;
            background: #1e2a37;
            margin: 0.7rem 0;
        }
        .alert-strip {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 0.55rem;
            margin: 0.7rem 0 0.9rem 0;
        }
        .live-alert {
            border-radius: 8px;
            padding: 0.62rem 0.72rem;
            border: 1px solid #2a3a4d;
            background: #0f1722;
        }
        .live-alert.signal {
            border-left: 4px solid #38bdf8;
            box-shadow: 0 0 0 1px rgba(56, 189, 248, 0.08);
        }
        .live-alert.trailing {
            border-left: 4px solid #f59e0b;
            box-shadow: 0 0 0 1px rgba(245, 158, 11, 0.08);
        }
        .live-alert-title {
            color: #f5f8fb;
            font-size: 0.86rem;
            font-weight: 700;
        }
        .live-alert-meta {
            color: #91a6b9;
            font-size: 0.74rem;
            margin-top: 0.16rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _parse_status_value(value: object) -> dict[str, object]:
    text = str(value or "").strip()
    if not text or text in {"-", "-/-"}:
        return {"side": "-", "score": None, "p_buy": None, "p_sell": None, "raw": "-/-", "css": "empty"}
    if text.startswith("B:"):
        return {"side": "BUY", "score": _safe_float(text.split(":", 1)[1], 0.0), "p_buy": None, "p_sell": None, "raw": text, "css": "buy"}
    if text.startswith("S:"):
        return {"side": "SELL", "score": _safe_float(text.split(":", 1)[1], 0.0), "p_buy": None, "p_sell": None, "raw": text, "css": "sell"}
    if "/" in text:
        left, right = text.split("/", 1)
        return {
            "side": "NEUTRO",
            "score": None,
            "p_buy": _safe_float(left, 0.0),
            "p_sell": _safe_float(right, 0.0),
            "raw": text,
            "css": "",
        }
    return {"side": "INFO", "score": None, "p_buy": None, "p_sell": None, "raw": text, "css": ""}


def _status_signal_count(row: pd.Series) -> int:
    return sum(1 for tf in TIMEFRAMES if re.search(r"B:|S:", str(row.get(tf, ""))))


def _status_reason_count(row: pd.Series) -> int:
    reason = str(row.get("motivos", "") or "")
    if not reason or reason == "-":
        return 0
    return len([part for part in reason.split("|") if part.strip()])


def _oms_payload(oms_snapshot: dict | None) -> dict:
    if not oms_snapshot:
        return {}
    oms = oms_snapshot.get("oms", oms_snapshot)
    return oms if isinstance(oms, dict) else {}


def _asset_positions(oms_snapshot: dict | None, selected_symbol: str) -> list[dict]:
    oms = _oms_payload(oms_snapshot)
    selected = _raw_asset_symbol(str(selected_symbol or "")).upper()
    aliases = {selected}
    if selected in {"XAUUSD", "GOLD"}:
        aliases.update({"XAUUSD", "GOLD"})
    positions = []
    for position in oms.get("positions", []) or []:
        symbol = str(position.get("symbol") or position.get("broker_symbol") or "").upper()
        if symbol in aliases:
            positions.append(position)
    return positions


def _positions_summary_by_symbol(oms_snapshot: dict | None) -> dict[str, dict[str, object]]:
    summary: dict[str, dict[str, object]] = {}
    for position in _oms_payload(oms_snapshot).get("positions", []) or []:
        symbol = _format_asset_symbol(str(position.get("symbol") or position.get("broker_symbol") or "").upper())
        if not symbol:
            continue
        item = summary.setdefault(symbol, {"count": 0, "profit": 0.0, "directions": set()})
        item["count"] = int(item["count"]) + 1
        item["profit"] = float(item["profit"]) + _safe_float(position.get("profit"), 0.0)
        directions = item.get("directions")
        if isinstance(directions, set):
            directions.add(str(position.get("direction") or "-").upper())
    for item in summary.values():
        directions = item.get("directions")
        if isinstance(directions, set):
            item["directions"] = "/".join(sorted(directions))
    return summary


def _terminal_score(value: float | None) -> str:
    return "-" if value is None else f"{value:.3f}"


def _render_terminal_reasons(raw_reason: object) -> None:
    cards = _parse_asset_reason_cards(raw_reason)
    if not cards:
        st.caption("Sem bloqueio ou motivo acionavel no ultimo status.")
        return
    for card in cards:
        st.markdown(
            f"""
            <div class="reason-card">
                <div class="reason-title">{card['timeframe']} · {card['filtro']}</div>
                <div class="reason-line">Estado: {card['estado']}</div>
                <div class="reason-line">Direcao: {card['direcao']} · Score: {card['score']}</div>
                <div class="reason-line">{card['detalhe']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_timeframe_strip(row: pd.Series) -> None:
    cols = st.columns(len(TIMEFRAMES))
    for col, tf in zip(cols, TIMEFRAMES):
        parsed = _parse_status_value(row.get(tf, "-/-"))
        side = str(parsed["side"])
        raw = str(parsed["raw"])
        if side == "BUY":
            value = f"BUY {_terminal_score(parsed['score'])}"
            note = "sinal comprador"
            delta = "BUY"
        elif side == "SELL":
            value = f"SELL {_terminal_score(parsed['score'])}"
            note = "sinal vendedor"
            delta = "SELL"
        elif side == "NEUTRO":
            value = f"{_terminal_score(parsed['p_buy'])}/{_terminal_score(parsed['p_sell'])}"
            note = "p_buy / p_sell"
            delta = "neutro"
        else:
            value = raw
            note = "sem modelo/status"
            delta = "sem status"
        with col:
            st.metric(tf, value, delta=delta, help=note)


def _render_price_chart(symbol: str, timeframe: str, oms_snapshot: dict | None = None) -> None:
    df = read_latest_ohlcv(symbol, timeframe, bars=180)
    if df.empty or go is None:
        st.caption("Grafico OHLC local indisponivel para este ativo/timeframe.")
        return
    df = df.reset_index(drop=True).copy()
    df["bar_index"] = df.index.astype(int)
    tick_step = max(1, len(df) // 8)
    tick_values = df["bar_index"].iloc[::tick_step].tolist()
    tick_text = df["date"].dt.strftime("%d/%m %H:%M").iloc[::tick_step].tolist()
    positions = _asset_positions(oms_snapshot, symbol)
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=df["bar_index"],
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                increasing_line_color="#2dd4bf",
                decreasing_line_color="#fb7185",
                increasing_fillcolor="#2dd4bf",
                decreasing_fillcolor="#fb7185",
                name=symbol,
            )
        ]
    )
    for period, color in [(9, "#38bdf8"), (21, "#f59e0b"), (50, "#e879f9")]:
        if len(df) >= period:
            fig.add_trace(
                go.Scatter(
                    x=df["bar_index"],
                    y=df["close"].rolling(period).mean(),
                    mode="lines",
                    line=dict(width=1.2, color=color),
                    name=f"MA{period}",
                )
            )
    fig.update_layout(
        height=440,
        margin=dict(l=8, r=8, t=30, b=8),
        paper_bgcolor="#080d14",
        plot_bgcolor="#080d14",
        font=dict(color="#d7e2ee"),
        xaxis=dict(
            type="linear",
            showgrid=True,
            gridcolor="#172231",
            rangeslider=dict(visible=False),
            tickmode="array",
            tickvals=tick_values,
            ticktext=tick_text,
        ),
        yaxis=dict(showgrid=True, gridcolor="#172231", side="right"),
        title=f"{symbol} · {timeframe} · OHLC local",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    for position in positions:
        direction = str(position.get("direction", "") or "").upper()
        open_price = _safe_float(position.get("price_open"), 0.0)
        current_price = _safe_float(position.get("price_current"), 0.0)
        profit = _safe_float(position.get("profit"), 0.0)
        color = "#2dd4bf" if direction == "BUY" else "#fb7185"
        if open_price > 0:
            fig.add_hline(
                y=open_price,
                line_width=1.4,
                line_dash="dash",
                line_color=color,
                annotation_text=f"{direction} entrada {open_price:g}",
                annotation_position="top right",
                annotation_font_color=color,
            )
        if current_price > 0:
            fig.add_hline(
                y=current_price,
                line_width=1.0,
                line_dash="dot",
                line_color="#f8fafc",
                annotation_text=f"atual {current_price:g} | PnL {profit:.2f}",
                annotation_position="bottom right",
                annotation_font_color="#f8fafc",
            )
    st.plotly_chart(fig, use_container_width=True)


def _latest_asset_events(events_df: pd.DataFrame, selected_symbol: str) -> pd.DataFrame:
    if events_df.empty:
        return pd.DataFrame()
    return events_df[_asset_symbol_mask(events_df, selected_symbol)].sort_values("timestamp")


def _latest_asset_engines(engines_df: pd.DataFrame, selected_symbol: str) -> pd.DataFrame:
    if engines_df.empty:
        return pd.DataFrame()
    asset_engines = engines_df[_asset_symbol_mask(engines_df, selected_symbol)].copy()
    if asset_engines.empty:
        return asset_engines
    return (
        asset_engines.sort_values("timestamp")
        .drop_duplicates(["timeframe", "strategy", "side", "engine"], keep="last")
        .sort_values(["timeframe", "engine"])
    )


def render_trading_terminal(
    dashboard_df: pd.DataFrame,
    reason_df: pd.DataFrame,
    audit_events_df: pd.DataFrame,
    audit_engines_df: pd.DataFrame,
    log_path: Path | None,
    oms_snapshot: dict | None = None,
) -> None:
    st.markdown(
        """
        <div class="terminal-header">
            <div>
                <div class="terminal-title">FUSION_V2 Market Terminal</div>
                <div class="terminal-subtitle">Monitoramento, decisão, risco e explicabilidade. Execução desabilitada nesta interface.</div>
            </div>
            <div>
                <span class="terminal-badge">READ ONLY</span>
                <span class="terminal-badge">NO ORDER BUTTONS</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if dashboard_df.empty:
        st.info("Sem status para montar o terminal. Aguarde o robo gerar log, decision_audit ou Event Bus.")
        return

    display = dashboard_df.copy()
    display["symbol"] = display["symbol"].astype(str).map(_format_asset_symbol)
    display = display.drop_duplicates("symbol", keep="last").sort_values("symbol")
    symbols = display["symbol"].dropna().astype(str).tolist()
    position_summary = _positions_summary_by_symbol(oms_snapshot)
    total_positions = sum(int(item.get("count", 0) or 0) for item in position_summary.values())
    total_position_pnl = sum(float(item.get("profit", 0.0) or 0.0) for item in position_summary.values())

    top1, top2, top3, top4, top5, top6 = st.columns(6)
    active_signals = int(display[TIMEFRAMES].astype(str).apply(lambda col: col.str.contains("B:|S:", regex=True)).sum().sum())
    blocked = int(reason_df["count"].sum()) if not reason_df.empty and "count" in reason_df.columns else 0
    with top1:
        metric_card("Ativos", len(display))
    with top2:
        metric_card("Sinais ativos", active_signals)
    with top3:
        metric_card("Motivos", blocked)
    with top4:
        metric_card("Posicoes", total_positions)
    with top5:
        metric_card("PnL aberto", f"{total_position_pnl:.2f}")
    with top6:
        metric_card("Fonte", log_path.name if log_path else "-")

    left, center, right = st.columns([1.05, 2.3, 1.25], gap="medium")
    with left:
        st.subheader("Watchlist")
        only_signals = st.toggle("Somente com sinal", value=False)
        only_reasons = st.toggle("Somente com alerta", value=False)
        watch = display.copy()
        watch["sinais"] = watch.apply(_status_signal_count, axis=1)
        watch["alertas"] = watch.apply(_status_reason_count, axis=1)
        watch["posicoes"] = watch["symbol"].map(lambda symbol: int(position_summary.get(str(symbol), {}).get("count", 0) or 0))
        watch["pnl"] = watch["symbol"].map(lambda symbol: float(position_summary.get(str(symbol), {}).get("profit", 0.0) or 0.0))
        if only_signals:
            watch = watch[watch["sinais"] > 0]
        if only_reasons:
            watch = watch[watch["alertas"] > 0]
        selected_label = st.radio(
            "Ativo",
            watch["symbol"].tolist() if not watch.empty else symbols,
            label_visibility="collapsed",
            index=0,
        )
        for _, item in watch.head(35).iterrows():
            position_note = ""
            if int(item.get("posicoes", 0)) > 0:
                pnl = _safe_float(item.get("pnl"), 0.0)
                pnl_class = "tf-side-buy" if pnl >= 0 else "tf-side-sell"
                position_note = f"<div class='watch-meta'>Pos: {int(item.get('posicoes', 0))} | <span class='{pnl_class}'>PnL {pnl:.2f}</span></div>"
            st.markdown(
                f"""
                <div class="watch-card">
                    <div class="watch-symbol">{item.get('symbol', '-')}</div>
                    {position_note}
                    <div class="watch-meta">Sinais: {int(item.get('sinais', 0))} · Alertas: {int(item.get('alertas', 0))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    selected_symbol = _raw_asset_symbol(str(selected_label))
    selected_rows = display[display["symbol"].astype(str).eq(str(selected_label))]
    selected_row = selected_rows.iloc[-1] if not selected_rows.empty else display.iloc[0]
    asset_events = _latest_asset_events(audit_events_df, selected_symbol)
    asset_engines = _latest_asset_engines(audit_engines_df, selected_symbol)
    asset_positions = _asset_positions(oms_snapshot, selected_symbol)

    with center:
        st.subheader(f"{selected_label} · Painel do Ativo")
        _render_timeframe_strip(selected_row)
        chart_tf = st.radio(
            "Grafico",
            TIMEFRAMES,
            index=1 if "M15" in TIMEFRAMES else 0,
            horizontal=True,
            label_visibility="collapsed",
        )
        _render_price_chart(str(selected_label), str(chart_tf or "M15"), oms_snapshot)

        latest_event = asset_events.iloc[-1] if not asset_events.empty else pd.Series(dtype=object)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            metric_card("Ultima decisao", latest_event.get("decision", "-") if not latest_event.empty else "-")
        with c2:
            metric_card("Tradeability", f"{_safe_float(latest_event.get('tradeability_score')):.3f}" if not latest_event.empty else "-")
        with c3:
            metric_card("Conflito", f"{_safe_float(latest_event.get('conflict_score')):.3f}" if not latest_event.empty else "-")
        with c4:
            metric_card("Lado", latest_event.get("side", "-") if not latest_event.empty else "-")

        st.markdown("<div class='mini-divider'></div>", unsafe_allow_html=True)
        st.subheader("Timeline de Decisao")
        if asset_events.empty:
            st.caption("Sem decision_audit para este ativo.")
        else:
            timeline = asset_events.sort_values("timestamp", ascending=False).head(8)
            for _, event in timeline.iterrows():
                st.markdown(
                    f"""
                    <div class="engine-card">
                        <div class="engine-name">{event.get('timeframe', '-')} · {event.get('side', '-')} · {event.get('decision', '-')}</div>
                        <div class="engine-meta">{event.get('timestamp', '-')} · {event.get('reason', '-')}</div>
                        <div class="engine-meta">p_buy={_safe_float(event.get('p_buy')):.3f} · p_sell={_safe_float(event.get('p_sell')):.3f} · consenso={_safe_float(event.get('consensus_score')):.3f}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with right:
        st.subheader("Posicao")
        if not asset_positions:
            st.caption("Sem posicao aberta para este ativo.")
        else:
            for position in asset_positions:
                direction = str(position.get("direction", "-"))
                profit = _safe_float(position.get("profit"), 0.0)
                pnl_class = "tf-side-buy" if profit >= 0 else "tf-side-sell"
                st.markdown(
                    f"""
                    <div class="engine-card">
                        <div class="engine-name">{direction} Â· {position.get('volume', '-')} lote</div>
                        <div class="engine-meta">Entrada: {position.get('price_open', '-')} Â· Atual: {position.get('price_current', '-')}</div>
                        <div class="engine-meta"><span class="{pnl_class}">PnL: {profit:.2f}</span> Â· Magic: {position.get('magic', '-')}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        st.markdown("<div class='mini-divider'></div>", unsafe_allow_html=True)
        st.subheader("Motivos")
        _render_terminal_reasons(selected_row.get("motivos", "-"))
        st.markdown("<div class='mini-divider'></div>", unsafe_allow_html=True)
        st.subheader("Engines")
        if asset_engines.empty:
            st.caption("Sem engines auditadas para este ativo.")
        else:
            engine_filter = st.selectbox(
                "Timeframe",
                ["Todos"] + [tf for tf in TIMEFRAMES if tf in set(asset_engines["timeframe"].astype(str))],
            )
            engine_view = asset_engines if engine_filter == "Todos" else asset_engines[asset_engines["timeframe"] == engine_filter]
            for _, engine in engine_view.head(18).iterrows():
                st.markdown(
                    f"""
                    <div class="engine-card">
                        <div class="engine-name">{engine.get('engine', '-')}</div>
                        <div class="engine-meta">{engine.get('timeframe', '-')} · {engine.get('engine_state', '-')} · {engine.get('engine_direction', '-')}</div>
                        <div class="engine-meta">score={_safe_float(engine.get('engine_score')):.3f} · conf={_safe_float(engine.get('engine_confidence')):.3f} · neg={int(_safe_float(engine.get('negative_count')))}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.markdown("<div class='mini-divider'></div>", unsafe_allow_html=True)
    if px is not None:
        heat = display.set_index("symbol")
        rows = []
        for symbol, row in heat.iterrows():
            for tf in TIMEFRAMES:
                parsed = _parse_status_value(row.get(tf, "-/-"))
                if parsed["side"] == "BUY":
                    value = _safe_float(parsed["score"])
                elif parsed["side"] == "SELL":
                    value = -_safe_float(parsed["score"])
                elif parsed["side"] == "NEUTRO":
                    value = _safe_float(parsed["p_buy"]) - _safe_float(parsed["p_sell"])
                else:
                    value = 0.0
                rows.append({"symbol": symbol, "timeframe": tf, "bias": value})
        heat_df = pd.DataFrame(rows)
        pivot = heat_df.pivot_table(index="symbol", columns="timeframe", values="bias", aggfunc="mean")
        pivot = pivot.reindex(columns=TIMEFRAMES)
        fig = px.imshow(
            pivot,
            color_continuous_scale="RdBu",
            color_continuous_midpoint=0,
            aspect="auto",
            title="Mapa Direcional: positivo=BUY, negativo=SELL",
        )
        fig.update_layout(height=420, margin=dict(l=10, r=10, t=45, b=10), paper_bgcolor="#080d14", plot_bgcolor="#080d14")
        st.plotly_chart(fig, use_container_width=True)


def render_status_tab(dashboard_df: pd.DataFrame, reason_df: pd.DataFrame, log_path: Path | None) -> None:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Ativos", len(dashboard_df) if not dashboard_df.empty else 0)
    with col2:
        active_signals = 0
        if not dashboard_df.empty:
            active_signals = int(dashboard_df[TIMEFRAMES].astype(str).apply(lambda col: col.str.contains("B:|S:", regex=True)).sum().sum())
        metric_card("Sinais B/S", active_signals)
    with col3:
        metric_card("Motivos", int(reason_df["count"].sum()) if not reason_df.empty else 0)
    with col4:
        metric_card("Log", log_path.name if log_path else "nao encontrado")

    if dashboard_df.empty:
        st.info("Nenhum dashboard encontrado no log e nenhum decision_audit disponivel para fallback.")
        return

    display = dashboard_df.copy()
    display["motivos"] = display["motivos"].replace({"-": "sem motivo acionavel"})

    symbols = sorted(display["symbol"].dropna().astype(str).unique()) if "symbol" in display.columns else []
    selected_symbols = st.multiselect("Ativos na visao", symbols, default=symbols[:12])
    show_only_with_reasons = st.checkbox("Mostrar apenas ativos com motivo acionavel", value=False)
    filtered = display[display["symbol"].astype(str).isin(selected_symbols)] if selected_symbols else display
    if show_only_with_reasons:
        filtered = filtered[filtered["motivos"].astype(str).ne("sem motivo acionavel")]

    for _, row in filtered.iterrows():
        symbol = str(row.get("symbol", "-") or "-")
        signal_count = sum(1 for tf in TIMEFRAMES if re.search(r"B:|S:", str(row.get(tf, ""))))
        reason_text = str(row.get("motivos", "sem motivo acionavel") or "sem motivo acionavel")
        with st.expander(f"{symbol} | sinais={signal_count} | {reason_text.split('|')[0].strip()}", expanded=False):
            tf_rows = [{"timeframe": tf, "status": row.get(tf, "-")} for tf in TIMEFRAMES]
            st.dataframe(pd.DataFrame(tf_rows), use_container_width=True, hide_index=True)
            st.markdown("**Motivos**")
            render_reason_cards(row.get("motivos", "-"))

    with st.expander("Tabela bruta do status", expanded=False):
        st.dataframe(display, use_container_width=True, hide_index=True)


def render_reasons_tab(reason_df: pd.DataFrame) -> None:
    if reason_df.empty:
        st.info("Nenhum motivo acionavel encontrado.")
        return
    col1, col2 = st.columns([1, 1])
    with col1:
        st.dataframe(reason_df, use_container_width=True, hide_index=True)
    with col2:
        if px is not None:
            fig = px.bar(reason_df, x="motivo", y="count", title="Motivos no log atual")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Plotly nao esta instalado no ambiente.")

    st.subheader("Glossario")
    for reason, help_text in REASON_HELP.items():
        st.markdown(f"**{reason}**: {help_text}")


def render_shadow_tab() -> None:
    summary = latest_file("market_structure_shadow_summary_*.md", REPORTS_DIR / "market_structure_shadow")
    calibration = latest_shadow_date_file("calibration")
    buckets = latest_shadow_date_file("score_buckets")

    if summary and summary.exists():
        st.markdown(read_text(str(summary)))
    else:
        st.info("Relatorio de Market Structure Shadow ainda nao encontrado.")

    if calibration:
        df = read_csv(str(calibration))
        if not df.empty:
            st.subheader("Calibracao por estrategia/ativo/timeframe")
            st.dataframe(df.head(200), use_container_width=True, hide_index=True)

    if buckets:
        df = read_csv(str(buckets))
        if not df.empty and px is not None:
            st.subheader("Distribuicao de score")
            st.plotly_chart(px.bar(df, x="score_bucket", y="events"), use_container_width=True)


def render_events_tab(events_df: pd.DataFrame) -> None:
    if events_df.empty:
        st.info("Nenhum evento recente encontrado.")
        return
    if "type" in events_df.columns:
        types = sorted(events_df["type"].dropna().astype(str).unique())
        selected = st.multiselect("Tipos", types, default=types[:12] if len(types) > 12 else types)
        filtered = events_df[events_df["type"].isin(selected)] if selected else events_df
        cols = [
            "timestamp",
            "type",
            "source",
            "symbol",
            "timeframe",
            "strategy",
            "direction",
            "status",
            "reason",
            "correlation_id",
        ]
        available = [col for col in cols if col in filtered.columns]
        st.caption("Fonte: Event Bus")
        st.dataframe(filtered.sort_values("timestamp", ascending=False)[available].head(300), use_container_width=True, hide_index=True)
        return
    selected = st.multiselect("Tipos", sorted(events_df["tipo"].unique()), default=sorted(events_df["tipo"].unique()))
    filtered = events_df[events_df["tipo"].isin(selected)] if selected else events_df
    st.caption("Fonte: log textual legado")
    st.dataframe(filtered.tail(200), use_container_width=True, hide_index=True)


def render_structured_events_tab(events_df: pd.DataFrame, oms_snapshot: dict | None = None) -> None:
    oms_snapshot = oms_snapshot or {}
    if oms_snapshot:
        oms = oms_snapshot.get("oms", {}) or {}
        st.subheader("OMS atual")
        cols = st.columns(5)
        cols[0].metric("Posicoes", len(oms.get("positions", []) or []))
        cols[1].metric("Ordens", len(oms.get("orders", []) or []))
        cols[2].metric("Ativas", len(oms.get("active_orders", []) or []))
        cols[3].metric("Contratos", len(oms.get("contracts", []) or []))
        cols[4].metric("Ticks", len(oms.get("ticks", []) or []))
        with st.expander("Snapshot OMS"):
            account = oms.get("account", {}) or {}
            if account:
                st.write("Conta")
                st.json(account)
            if oms.get("positions"):
                st.write("Posicoes")
                st.dataframe(pd.DataFrame(oms.get("positions", [])), use_container_width=True, hide_index=True)
            if oms.get("contracts"):
                st.write("Contratos")
                st.dataframe(pd.DataFrame(oms.get("contracts", [])), use_container_width=True, hide_index=True)

    if events_df.empty:
        st.info("Nenhum evento estruturado encontrado em logs/events ainda.")
        return

    summary = summarize_event_types(events_df)
    left, right = st.columns([1, 2])
    with left:
        st.subheader("Tipos")
        st.dataframe(summary, use_container_width=True, hide_index=True)
    with right:
        st.subheader("Filtros")
        types = sorted(events_df["type"].dropna().astype(str).unique())
        symbols = sorted([item for item in events_df["symbol"].dropna().astype(str).unique() if item])
        selected_types = st.multiselect("Tipo de evento", types, default=types)
        selected_symbol = st.selectbox("Ativo", ["Todos"] + symbols)

    filtered = events_df.copy()
    if selected_types:
        filtered = filtered[filtered["type"].isin(selected_types)]
    if selected_symbol != "Todos":
        filtered = filtered[filtered["symbol"] == selected_symbol]

    st.subheader("Timeline")
    timeline_cols = [
        "timestamp",
        "type",
        "source",
        "symbol",
        "timeframe",
        "strategy",
        "direction",
        "status",
        "reason",
        "correlation_id",
    ]
    st.dataframe(
        filtered.sort_values("timestamp", ascending=False)[[col for col in timeline_cols if col in filtered.columns]].head(300),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Detalhe")
    for _, row in filtered.sort_values("timestamp", ascending=False).head(30).iterrows():
        title = f"{row.get('timestamp', '-')} | {row.get('type', '-')} | {row.get('symbol', '-') or '-'} {row.get('timeframe', '-') or '-'}"
        with st.expander(title):
            st.json(row.get("raw", {}))

    if "correlation_id" in events_df.columns:
        st.subheader("Saude do ciclo por correlation_id")
        lifecycle_rows = []
        for correlation_id, group in events_df.groupby("correlation_id", dropna=False):
            types = set(group["type"].astype(str))
            first = group.sort_values("timestamp").iloc[0]
            last = group.sort_values("timestamp").iloc[-1]
            lifecycle_rows.append(
                {
                    "correlation_id": correlation_id,
                    "symbol": first.get("symbol", ""),
                    "timeframe": first.get("timeframe", ""),
                    "strategy": first.get("strategy", ""),
                    "has_decision": "DECISION" in types,
                    "has_order_request": "ORDER_REQUEST" in types,
                    "has_order_result": "ORDER_RESULT" in types,
                    "events": len(group),
                    "last_type": last.get("type", ""),
                    "last_status": last.get("status", ""),
                    "last_reason": last.get("reason", ""),
                }
            )
        lifecycle_df = pd.DataFrame(lifecycle_rows)
        if not lifecycle_df.empty:
            order_cycles = lifecycle_df[lifecycle_df["has_order_request"] == True]
            c1, c2, c3 = st.columns(3)
            c1.metric("Ciclos", len(lifecycle_df))
            c2.metric("ORDER_REQUEST", len(order_cycles))
            c3.metric("Sem ORDER_RESULT", int((order_cycles["has_order_result"] == False).sum()) if not order_cycles.empty else 0)
            st.dataframe(
                lifecycle_df.sort_values(["has_order_request", "events"], ascending=[False, False]).head(200),
                use_container_width=True,
                hide_index=True,
            )


def render_audit_overview(events_df: pd.DataFrame, engines_df: pd.DataFrame) -> None:
    if events_df.empty:
        st.info("Nenhum decision_audit encontrado ainda.")
        return
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        metric_card("Audit eventos", len(events_df))
    with col2:
        metric_card("ALLOW", int((events_df["decision"] == "ALLOW").sum()))
    with col3:
        metric_card("BLOCK", int((events_df["decision"] == "BLOCK").sum()))
    with col4:
        metric_card("Tradeability medio", f"{events_df['tradeability_score'].mean():.3f}")
    with col5:
        metric_card("Conflito medio", f"{events_df['conflict_score'].mean():.3f}")

    xai_cols = [
        "timestamp",
        "symbol",
        "timeframe",
        "side",
        "strategy",
        "decision",
        "reason",
        "xai_final_score",
        "xai_confidence_band",
        "xai_summary",
        "xai_negative",
        "xai_positive",
    ]
    xai_available = [col for col in xai_cols if col in events_df.columns]
    if "xai_summary" in events_df.columns and events_df["xai_summary"].astype(str).str.len().sum() > 0:
        st.subheader("Explicabilidade XAI")
        st.dataframe(
            events_df.sort_values("timestamp", ascending=False)[xai_available].head(80),
            use_container_width=True,
            hide_index=True,
        )

    col_left, col_right = st.columns([1, 1])
    with col_left:
        st.subheader("Ultimos eventos auditados")
        st.dataframe(
            events_df.sort_values("timestamp", ascending=False).head(80),
            use_container_width=True,
            hide_index=True,
        )
    with col_right:
        if engines_df.empty:
            st.info("Sem engines no audit.")
        else:
            state_counts = (
                engines_df.groupby(["engine", "engine_state"])
                .size()
                .reset_index(name="count")
                .sort_values("count", ascending=False)
                .head(60)
            )
            st.subheader("Estados por engine")
            st.dataframe(state_counts, use_container_width=True, hide_index=True)


def _format_asset_symbol(symbol: str) -> str:
    return "GOLD" if symbol == "XAUUSD" else symbol


def _raw_asset_symbol(symbol: str) -> str:
    return "XAUUSD" if symbol == "GOLD" else symbol


def _asset_symbol_mask(df: pd.DataFrame, selected_symbol: str) -> pd.Series:
    values = df["symbol"].astype(str).str.upper()
    selected = str(selected_symbol or "").upper()
    aliases = {selected}
    if selected in {"XAUUSD", "GOLD"}:
        aliases.update({"XAUUSD", "GOLD"})
    return values.isin(aliases)


def _json_to_metrics_table(raw_json: str) -> pd.DataFrame:
    try:
        data = json.loads(raw_json or "{}")
    except json.JSONDecodeError:
        data = {}
    rows = []
    for key, value in sorted(data.items()):
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False, default=str)
        rows.append({"metrica": key, "resultado": value})
    return pd.DataFrame(rows)


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _compact_value(value: object) -> object:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.4f}"
    if isinstance(value, str) and not value.strip():
        return "-"
    return value


def _series_to_metric_table(row: pd.Series, fields: list[tuple[str, str]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"campo": label, "valor": _compact_value(row.get(field, "-"))}
            for field, label in fields
            if field in row.index
        ]
    )


def _render_factor_block(title: str, value: object) -> None:
    text = str(value or "").strip()
    if not text or text == "-":
        st.caption(f"{title}: -")
        return
    st.markdown(f"**{title}**")
    for item in [part.strip() for part in text.split(";") if part.strip()]:
        st.caption(f"- {item}")


def _parse_asset_reason_cards(raw_reason: object) -> list[dict[str, str]]:
    text = str(raw_reason or "").strip()
    if not text or text == "-":
        return []
    cards = []
    for block in [part.strip() for part in text.split("|") if part.strip()]:
        timeframe = "-"
        remainder = block
        if ":" in block:
            first, remainder = block.split(":", 1)
            if first.strip() in TIMEFRAMES:
                timeframe = first.strip()
        parts = [part.strip() for part in remainder.split(":") if part.strip()]
        score = "-"
        clean_parts = []
        for part in parts:
            if part.startswith("score="):
                score = part.replace("score=", "", 1)
            else:
                clean_parts.append(part)
        cards.append(
            {
                "timeframe": timeframe,
                "filtro": clean_parts[0] if len(clean_parts) > 0 else "-",
                "estado": clean_parts[1] if len(clean_parts) > 1 else "-",
                "direcao": clean_parts[2] if len(clean_parts) > 2 else "-",
                "score": score,
                "detalhe": " / ".join(clean_parts[3:]) if len(clean_parts) > 3 else "-",
            }
        )
    return cards


def render_reason_cards(raw_reason: object) -> None:
    cards = _parse_asset_reason_cards(raw_reason)
    if not cards:
        st.caption("Sem motivo acionavel.")
        return
    for card in cards:
        with st.container(border=True):
            st.markdown(f"**{card['timeframe']}**")
            reason_rows = [
                {"campo": "Filtro", "valor": card["filtro"]},
                {"campo": "Estado", "valor": card["estado"]},
                {"campo": "Direcao", "valor": card["direcao"]},
                {"campo": "Score", "valor": card["score"]},
            ]
            st.dataframe(pd.DataFrame(reason_rows), use_container_width=True, hide_index=True)
            if card["detalhe"] != "-":
                st.caption(card["detalhe"])


def render_asset_detail(events_df: pd.DataFrame, engines_df: pd.DataFrame, dashboard_df: pd.DataFrame) -> None:
    if events_df.empty:
        st.info("Sem decision_audit ainda. Quando o robo registrar tentativas de decisao, o raio-x por ativo aparece aqui.")
        return

    symbols = sorted({_format_asset_symbol(str(item)) for item in events_df["symbol"].dropna().unique() if str(item)})
    selected_label = st.selectbox("Ativo", symbols)
    selected_symbol = _raw_asset_symbol(selected_label)

    asset_events = events_df[_asset_symbol_mask(events_df, selected_symbol)].copy()
    asset_engines = engines_df[_asset_symbol_mask(engines_df, selected_symbol)].copy() if not engines_df.empty else pd.DataFrame()
    if asset_events.empty:
        st.info("Sem eventos auditados para este ativo.")
        return

    asset_events = asset_events.sort_values("timestamp")
    latest_event = asset_events.iloc[-1]
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        metric_card("Eventos", len(asset_events))
    with col2:
        metric_card("ALLOW", int((asset_events["decision"] == "ALLOW").sum()))
    with col3:
        metric_card("BLOCK", int((asset_events["decision"] == "BLOCK").sum()))
    with col4:
        metric_card("Tradeability", f"{asset_events['tradeability_score'].mean():.3f}")
    with col5:
        metric_card("Conflito", f"{asset_events['conflict_score'].mean():.3f}")
    with col6:
        metric_card("Ultima decisao", str(latest_event.get("decision", "-") or "-"))

    if not dashboard_df.empty and "symbol" in dashboard_df.columns:
        display_row = dashboard_df[dashboard_df["symbol"].astype(str).isin([selected_label, selected_symbol])]
        if not display_row.empty:
            st.subheader("Status atual no dashboard operacional")
            status_row = display_row.iloc[-1]
            status_rows = [{"timeframe": tf, "status": status_row.get(tf, "-")} for tf in TIMEFRAMES]
            st.dataframe(pd.DataFrame(status_rows), use_container_width=True, hide_index=True)
            st.markdown("**Motivos**")
            render_reason_cards(status_row.get("motivos", "-"))

    st.subheader("Ultimas decisoes por timeframe")
    latest_by_tf = (
        asset_events.sort_values("timestamp")
        .drop_duplicates(["timeframe"], keep="last")
        .sort_values("timeframe", key=lambda col: col.map({tf: i for i, tf in enumerate(TIMEFRAMES)}).fillna(99))
    )
    tf_order = {tf: i for i, tf in enumerate(TIMEFRAMES)}
    for _, row in latest_by_tf.iterrows():
        tf = str(row.get("timeframe", "-") or "-")
        side = str(row.get("side", "-") or "-")
        decision = str(row.get("decision", "-") or "-")
        reason = str(row.get("reason", "-") or "-")
        with st.expander(f"{tf} | {side} | {decision} | {reason}", expanded=tf_order.get(tf, 99) < 2):
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                metric_card("p_buy", f"{_safe_float(row.get('p_buy')):.3f}")
            with c2:
                metric_card("p_sell", f"{_safe_float(row.get('p_sell')):.3f}")
            with c3:
                metric_card("tradeability", f"{_safe_float(row.get('tradeability_score')):.3f}")
            with c4:
                metric_card("conflito", f"{_safe_float(row.get('conflict_score')):.3f}")
            event_table = _series_to_metric_table(
                row,
                [
                    ("timestamp", "timestamp"),
                    ("strategy", "estrategia"),
                    ("consensus_score", "consenso"),
                    ("position_multiplier", "multiplicador"),
                    ("xai_confidence_band", "faixa XAI"),
                    ("xai_summary", "resumo XAI"),
                ],
            )
            st.dataframe(event_table, use_container_width=True, hide_index=True)

    available_tfs = [tf for tf in TIMEFRAMES if tf in set(asset_events["timeframe"])]
    selected_tf = st.selectbox("Timeframe para detalhe", ["Todos"] + available_tfs)
    if selected_tf != "Todos":
        detail_events = asset_events[asset_events["timeframe"] == selected_tf]
        detail_engines = asset_engines[asset_engines["timeframe"] == selected_tf] if not asset_engines.empty else pd.DataFrame()
    else:
        detail_events = asset_events
        detail_engines = asset_engines

    st.subheader("Engines e metricas analisadas")
    if detail_engines.empty:
        st.info("Sem detalhes de engines para o filtro selecionado.")
    else:
        latest_engines = (
            detail_engines.sort_values("timestamp")
            .drop_duplicates(["timeframe", "strategy", "side", "engine"], keep="last")
            .copy()
        )
        with st.expander("Resumo das engines por timeframe", expanded=True):
            for tf, tf_group in latest_engines.sort_values(["timeframe", "engine"]).groupby("timeframe", sort=False):
                if selected_tf != "Todos" and tf != selected_tf:
                    continue
                st.markdown(f"**{tf}**")
                for _, engine_row in tf_group.iterrows():
                    engine_name = str(engine_row.get("engine", "-") or "-")
                    state = str(engine_row.get("engine_state", "-") or "-")
                    score = _safe_float(engine_row.get("engine_score"))
                    confidence = _safe_float(engine_row.get("engine_confidence"))
                    negative_count = int(_safe_float(engine_row.get("negative_count")))
                    warning_count = int(_safe_float(engine_row.get("warning_count")))
                    positive_count = int(_safe_float(engine_row.get("positive_count")))
                    st.caption(
                        f"{engine_name}: estado={state} | score={score:.3f} | "
                        f"conf={confidence:.3f} | pos={positive_count} | neg={negative_count} | avisos={warning_count}"
                    )

        with st.expander("Tabela bruta das engines", expanded=False):
            summary = latest_engines[
                [
                    col
                    for col in [
                        "timeframe",
                        "engine",
                        "engine_state",
                        "engine_score",
                        "engine_confidence",
                        "negative_count",
                        "warning_count",
                        "positive_count",
                    ]
                    if col in latest_engines.columns
                ]
            ].sort_values(["timeframe", "engine"])
            st.dataframe(summary, use_container_width=True, hide_index=True)

        if px is not None:
            score_pivot = latest_engines.pivot_table(index="engine", columns="timeframe", values="engine_score", aggfunc="mean")
            score_pivot = score_pivot.reindex(columns=[tf for tf in TIMEFRAMES if tf in score_pivot.columns])
            if not score_pivot.empty:
                fig = px.imshow(
                    score_pivot,
                    text_auto=".2f",
                    color_continuous_scale="RdYlGn",
                    aspect="auto",
                    title=f"{selected_label} - score por engine/timeframe",
                )
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Detalhe por engine")
        for tf, tf_group in latest_engines.sort_values(["timeframe", "engine"]).groupby("timeframe", sort=False):
            if selected_tf != "Todos" and tf != selected_tf:
                continue
            with st.expander(f"{tf} - engines ({len(tf_group)})", expanded=selected_tf != "Todos"):
                for _, engine_row in tf_group.iterrows():
                    engine_name = str(engine_row.get("engine", "-") or "-")
                    state = str(engine_row.get("engine_state", "-") or "-")
                    score = _safe_float(engine_row.get("engine_score"))
                    confidence = _safe_float(engine_row.get("engine_confidence"))
                    st.markdown(f"#### {engine_name}")
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        metric_card("Estado", state)
                    with c2:
                        metric_card("Score", f"{score:.3f}")
                    with c3:
                        metric_card("Confianca", f"{confidence:.3f}")
                    with c4:
                        metric_card("Direcao", engine_row.get("engine_direction", "-") or "-")

                    left, right = st.columns([1, 1])
                    with left:
                        detail_table = _series_to_metric_table(
                            engine_row,
                            [
                                ("timestamp", "timestamp"),
                                ("strategy", "estrategia"),
                                ("side", "lado"),
                                ("negative_count", "fatores negativos"),
                                ("warning_count", "avisos"),
                                ("positive_count", "fatores positivos"),
                                ("risk_score", "risk score"),
                                ("feature_coverage", "feature coverage"),
                                ("session_fit_score", "session fit"),
                                ("position_multiplier_suggested", "multiplicador sugerido"),
                                ("calibrated_probability", "probabilidade calibrada"),
                                ("quality_floor", "quality floor"),
                                ("penalty", "penalidade"),
                                ("model_type", "tipo de modelo"),
                                ("ensemble_agreement", "acordo ensemble"),
                            ],
                        )
                        st.dataframe(detail_table, use_container_width=True, hide_index=True)
                    with right:
                        _render_factor_block("Negativos", engine_row.get("negative_factors", ""))
                        _render_factor_block("Warnings", engine_row.get("warnings", ""))
                        _render_factor_block("Positivos", engine_row.get("positive_factors", ""))

                    metrics_table = _json_to_metrics_table(str(engine_row.get("features_json", "{}") or "{}"))
                    if not metrics_table.empty:
                        with st.expander(f"Metricas internas - {engine_name}", expanded=False):
                            st.dataframe(metrics_table, use_container_width=True, hide_index=True)

    st.subheader("XAI do ativo")
    for _, row in detail_events.sort_values("timestamp", ascending=False).head(20).iterrows():
        with st.expander(f"{row.get('timestamp', '-')} | {row.get('timeframe', '-')} | {row.get('side', '-')} | {row.get('decision', '-')}"):
            st.write(str(row.get("xai_summary", "") or "Sem resumo XAI."))
            left, right = st.columns([1, 1])
            with left:
                _render_factor_block("XAI negativos", row.get("xai_negative", ""))
            with right:
                _render_factor_block("XAI positivos", row.get("xai_positive", ""))


def render_engine_heatmaps(events_df: pd.DataFrame, engines_df: pd.DataFrame) -> None:
    if events_df.empty:
        st.info("Nenhum audit para heatmap.")
        return
    metric = st.selectbox(
        "Metrica",
        ["tradeability_score", "conflict_score", "consensus_score", "p_buy", "p_sell"],
        index=0,
    )
    pivot = events_df.pivot_table(index="symbol", columns="timeframe", values=metric, aggfunc="mean")
    pivot = pivot.reindex(columns=[tf for tf in TIMEFRAMES if tf in pivot.columns])
    if px is not None and not pivot.empty:
        fig = px.imshow(
            pivot,
            text_auto=".2f",
            color_continuous_scale="RdYlGn",
            aspect="auto",
            title=f"Heatmap {metric}",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.dataframe(pivot, use_container_width=True)

    if not engines_df.empty:
        available_engines = [e for e in INSTITUTIONAL_ENGINES if e in set(engines_df["engine"])]
        if not available_engines:
            st.info("Nenhuma engine institucional encontrada no decision audit.")
            return
        engine = st.selectbox("Engine", available_engines)
        metric2 = st.selectbox("Metrica do engine", ["engine_score", "engine_confidence", "negative_count", "warning_count"])
        filtered = engines_df[engines_df["engine"] == engine]
        pivot_engine = filtered.pivot_table(index="symbol", columns="timeframe", values=metric2, aggfunc="mean")
        pivot_engine = pivot_engine.reindex(columns=[tf for tf in TIMEFRAMES if tf in pivot_engine.columns])
        if px is not None and not pivot_engine.empty:
            fig = px.imshow(
                pivot_engine,
                text_auto=".2f",
                color_continuous_scale="RdYlGn",
                aspect="auto",
                title=f"{engine} - {metric2}",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.dataframe(pivot_engine, use_container_width=True)


def render_risk_terminal(engines_df: pd.DataFrame) -> None:
    if engines_df.empty:
        st.info("Sem engines no audit.")
        return
    risk = engines_df[engines_df["engine"].isin(["risk_engine", "portfolio_exposure", "portfolio_correlation", "opportunity_engine"])]
    if risk.empty:
        st.info("Sem dados de risco no audit.")
        return
    cols = [
        "timestamp",
        "symbol",
        "timeframe",
        "side",
        "strategy",
        "engine",
        "engine_state",
        "engine_score",
        "risk_score",
        "position_multiplier_suggested",
        "quality_floor",
        "penalty",
        "negative_count",
        "warning_count",
    ]
    available = [col for col in cols if col in risk.columns]
    st.dataframe(risk.sort_values("timestamp", ascending=False)[available].head(200), use_container_width=True, hide_index=True)
    if px is not None:
        latest = risk.dropna(subset=["engine_score"])
        if not latest.empty:
            fig = px.box(latest, x="engine", y="engine_score", points="all", title="Distribuicao de score por engine de risco")
            st.plotly_chart(fig, use_container_width=True)


def render_engine_matrix(engines_df: pd.DataFrame) -> None:
    if engines_df.empty:
        st.info("Sem dados de engines.")
        return
    selected = st.multiselect(
        "Engines",
        sorted(engines_df["engine"].dropna().unique()),
        default=[engine for engine in INSTITUTIONAL_ENGINES if engine in set(engines_df["engine"])][:8],
    )
    filtered = engines_df[engines_df["engine"].isin(selected)] if selected else engines_df
    cols = [
        "timestamp",
        "symbol",
        "timeframe",
        "side",
        "engine",
        "engine_state",
        "engine_direction",
        "engine_score",
        "engine_confidence",
        "feature_coverage",
        "session_fit_score",
        "model_type",
        "ensemble_agreement",
        "calibrated_probability",
        "negative_count",
        "warning_count",
    ]
    available = [col for col in cols if col in filtered.columns]
    st.dataframe(filtered.sort_values("timestamp", ascending=False)[available].head(500), use_container_width=True, hide_index=True)


def render_sidebar_health(
    structured_events_df: pd.DataFrame,
    structured_event_path: Path | None,
    backfill_event_path: Path | None,
    oms_snapshot: dict,
    prefer_event_bus: bool,
) -> None:
    config = read_runtime_config(str(ROOT / "config" / "fusion_config.yaml"))
    event_bus_cfg = config.get("event_bus", {}) if isinstance(config.get("event_bus", {}), dict) else {}
    trading_cfg = config.get("trading", {}) if isinstance(config.get("trading", {}), dict) else {}
    oms_cfg = config.get("oms", {}) if isinstance(config.get("oms", {}), dict) else {}

    latest_ts = "-"
    latest_type = "-"
    if not structured_events_df.empty:
        latest = structured_events_df.sort_values("timestamp", ascending=False).iloc[0]
        latest_ts = str(latest.get("timestamp", "-"))
        latest_type = str(latest.get("type", "-"))

    with st.sidebar:
        st.divider()
        st.subheader("Saude")
        source = "Event Bus" if prefer_event_bus and not structured_events_df.empty else "Log/Fallback"
        st.caption(f"Fonte ativa: {source}")
        st.caption(f"Event Bus async: {'ON' if bool(event_bus_cfg.get('use_async', False)) else 'OFF'}")
        st.caption(f"Novas ordens: {'ON' if bool(trading_cfg.get('allow_new_orders', False)) else 'OFF'}")
        st.caption(f"OMS snapshot: {'ON' if bool(oms_cfg.get('snapshot_enabled', False)) else 'OFF'}")
        st.caption(f"Eventos carregados: {len(structured_events_df)}")
        st.caption(f"Ultimo evento: {latest_type} | {latest_ts}")
        if structured_event_path:
            st.caption(f"JSONL: {structured_event_path.name}")
        if backfill_event_path:
            st.caption(f"Backfill: {backfill_event_path.name}")
        if oms_snapshot:
            st.caption("OMS: snapshot encontrado")


def main() -> None:
    st.set_page_config(page_title="FUSION_V2 Terminal", page_icon="FX", layout="wide")
    inject_terminal_css()

    log_path = latest_file("fusion_*.log")
    if not log_path:
        st.error("Nenhum arquivo de log encontrado em logs/.")
        return

    with st.sidebar:
        st.header("FUSION_V2")
        st.caption("Terminal read-only")
        st.divider()
        st.subheader("Fonte")
        st.write(str(log_path.relative_to(ROOT)))
        refresh = st.slider("Atualizar a cada segundos", 5, 120, 15)
        prefer_event_bus = st.checkbox("Preferir Event Bus como fonte", value=True)
        st.checkbox("Mostrar campos vazios como explicacao", value=True, key="empty_hint")
        st.divider()
        st.subheader("Alertas")
        enable_signal_alerts = st.checkbox("Alertar sinais", value=True)
        enable_trailing_alerts = st.checkbox("Alertar trailing", value=True)
        sound_enabled = st.checkbox("Som", value=True)
        sound_cooldown_seconds = st.slider("Cooldown som segundos", 5, 300, 45)
        st.caption("Execute com: streamlit run dashboard/fusion_dashboard.py")

    st.markdown(
        f"<script>setTimeout(function(){{window.location.reload();}}, {refresh * 1000});</script>",
        unsafe_allow_html=True,
    )

    log_text = read_text(str(log_path))
    audit_path = latest_decision_audit_file()
    audit_events_df, audit_engines_df = read_decision_audit(str(audit_path), tail=20000) if audit_path else (pd.DataFrame(), pd.DataFrame())
    structured_event_path = latest_event_file(LOG_DIR / "events")
    structured_events_df = read_event_jsonl(structured_event_path, tail=20000) if structured_event_path else pd.DataFrame()
    backfill_event_path = latest_event_file(LOG_DIR / "events_backfill")
    backfill_events_df = read_event_jsonl(backfill_event_path, tail=20000) if backfill_event_path else pd.DataFrame()
    if not backfill_events_df.empty:
        structured_events_df = pd.concat([backfill_events_df, structured_events_df], ignore_index=True)
        if "event_id" in structured_events_df.columns:
            structured_events_df = structured_events_df.drop_duplicates("event_id", keep="last")
    event_audit_events_df, event_audit_engines_df = events_to_decision_audit_frames(structured_events_df)
    if prefer_event_bus and not event_audit_events_df.empty:
        audit_events_df = event_audit_events_df
        audit_engines_df = event_audit_engines_df
    elif audit_events_df.empty and not event_audit_events_df.empty:
        audit_events_df = event_audit_events_df
        audit_engines_df = event_audit_engines_df
    oms_snapshot = read_latest_oms_snapshot(LOG_DIR / "oms")
    dashboard_df, dashboard_block, recent_block = extract_latest_dashboard(log_text)
    reason_df = parse_reason_tokens(dashboard_block + recent_block)
    event_status_df = events_to_status_table(structured_events_df)
    if prefer_event_bus and not event_status_df.empty:
        dashboard_df = event_status_df
        reason_df = parse_reason_tokens(" ".join(event_status_df.get("motivos", pd.Series(dtype=str)).astype(str)))
    if dashboard_df.empty and not event_status_df.empty:
        dashboard_df = event_status_df
        reason_df = parse_reason_tokens(" ".join(event_status_df.get("motivos", pd.Series(dtype=str)).astype(str)))
    if dashboard_df.empty and not audit_events_df.empty:
        dashboard_df = audit_to_status_table(audit_events_df)
        reason_df = reasons_from_audit(audit_events_df)
    events_df = parse_recent_events(log_text)
    render_sidebar_health(structured_events_df, structured_event_path, backfill_event_path, oms_snapshot, prefer_event_bus)
    render_live_alerts(
        structured_events_df,
        log_text,
        enable_signal_alerts,
        enable_trailing_alerts,
        sound_enabled,
        sound_cooldown_seconds,
    )

    tabs = st.tabs([
        "Terminal",
        "Status",
        "Ativo",
        "Decision Audit",
        "Heatmaps",
        "Risco",
        "Engines",
        "Motivos",
        "Market Structure",
        "Eventos Recentes",
        "Event Bus",
        "Arquivos",
    ])
    with tabs[0]:
        render_trading_terminal(dashboard_df, reason_df, audit_events_df, audit_engines_df, log_path, oms_snapshot)
    with tabs[1]:
        render_status_tab(dashboard_df, reason_df, log_path)
    with tabs[2]:
        render_asset_detail(audit_events_df, audit_engines_df, dashboard_df)
    with tabs[3]:
        render_audit_overview(audit_events_df, audit_engines_df)
    with tabs[4]:
        render_engine_heatmaps(audit_events_df, audit_engines_df)
    with tabs[5]:
        render_risk_terminal(audit_engines_df)
    with tabs[6]:
        render_engine_matrix(audit_engines_df)
    with tabs[7]:
        render_reasons_tab(reason_df)
    with tabs[8]:
        render_shadow_tab()
    with tabs[9]:
        render_events_tab(structured_events_df if not structured_events_df.empty else events_df)
    with tabs[10]:
        render_structured_events_tab(structured_events_df, oms_snapshot)
    with tabs[11]:
        files = []
        for folder in [
            LOG_DIR,
            REPORTS_DIR / "market_structure_shadow",
            REPORTS_DIR / "market_structure_labels",
            REPORTS_DIR / "event_bus",
            REPORTS_DIR / "event_replay",
            REPORTS_DIR / "event_performance",
            REPORTS_DIR / "operational_day",
            REPORTS_DIR / "oms_replay",
        ]:
            if not folder.exists():
                continue
            for path in folder.glob("*"):
                if path.is_file():
                    files.append({"arquivo": str(path.relative_to(ROOT)), "tamanho": path.stat().st_size, "modificado": path.stat().st_mtime})
        st.dataframe(pd.DataFrame(files).sort_values("modificado", ascending=False), use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
