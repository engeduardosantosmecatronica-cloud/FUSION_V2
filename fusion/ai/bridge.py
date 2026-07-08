from __future__ import annotations

from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from typing import Any


@dataclass
class AIBridgeConfig:
    host: str = "127.0.0.1"
    port: int = 8765
    provider: str = "mock_heuristic"
    model_hint: str = "gpt-5.4-nano"


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _candidate_side(payload: dict[str, Any]) -> str:
    return str((payload.get("candidate", {}) or {}).get("side", "") or "").upper()


def _engine_conflicts(engine: dict[str, Any], side: str) -> bool:
    direction = str(engine.get("direction", "") or "").upper()
    return direction in {"BUY", "SELL"} and direction != side


def _engine_aligned(engine: dict[str, Any], side: str) -> bool:
    return str(engine.get("direction", "") or "").upper() == side


def mock_advice(payload: dict[str, Any]) -> dict[str, Any]:
    """Heuristica local para testar o contrato do AI Advisor sem API externa."""
    side = _candidate_side(payload)
    engines = payload.get("engines", []) or []
    conflicts = [engine for engine in engines if _engine_conflicts(engine, side)]
    aligned = [engine for engine in engines if _engine_aligned(engine, side)]
    context = next((engine for engine in engines if engine.get("engine") == "context_engine"), {})
    context_score = _as_float((context.get("features", {}) or {}).get("context_score", context.get("score", 0.0)))
    context_conflict = _as_float((context.get("features", {}) or {}).get("context_conflict_score", 0.0))
    macro_conflict = any(engine.get("engine") == "macro_flow" for engine in conflicts)
    portfolio_conflict = any(str(engine.get("engine", "")).startswith("portfolio") for engine in conflicts)

    if context_conflict >= 0.45 or macro_conflict or portfolio_conflict:
        return {
            "recommendation": "AVOID",
            "confidence": max(0.68, min(0.95, 0.55 + context_conflict)),
            "primary_reason": "conflito_contextual_ou_risco_portfolio",
            "risk_notes": [str(engine.get("engine", "")) for engine in conflicts[:5]],
            "provider": "mock_heuristic",
        }
    if context_score >= 0.62 and len(aligned) >= max(1, len(conflicts) + 1):
        return {
            "recommendation": "ALLOW",
            "confidence": min(0.90, max(0.60, context_score)),
            "primary_reason": "contexto_alinhado",
            "risk_notes": [],
            "provider": "mock_heuristic",
        }
    return {
        "recommendation": "NEUTRAL",
        "confidence": 0.55,
        "primary_reason": "contexto_sem_confirmacao_forte",
        "risk_notes": [str(engine.get("engine", "")) for engine in conflicts[:5]],
        "provider": "mock_heuristic",
    }


def mock_review(payload: dict[str, Any]) -> dict[str, Any]:
    """Heuristica local para testar o contrato do AI Review Agent sem API externa."""
    candidate = payload.get("candidate", {}) or {}
    result = payload.get("result", {}) or {}
    engines = payload.get("engines", []) or []
    side = str(candidate.get("side", "") or "").upper()
    decision = str(result.get("decision", "") or "").upper()
    reason = str(result.get("reason", "") or "")
    tradeability = _as_float(result.get("tradeability_score", 0.0))
    conflict = _as_float(result.get("conflict_score", 0.0))
    conflicts = [engine for engine in engines if _engine_conflicts(engine, side)]

    if decision == "BLOCK" and tradeability >= 0.65 and not conflicts:
        return {
            "decision_review": "POSSIBLE_FALSE_BLOCK",
            "confidence": 0.72,
            "original_reason": reason,
            "review_reason": "bloqueio_com_tradeability_alto_e_sem_conflito_claro",
            "suggested_action": f"investigar_filtro:{reason}",
            "safe_to_auto_change": False,
            "provider": "mock_heuristic",
        }
    if decision == "ALLOW" and (conflict >= 0.40 or len(conflicts) >= 2):
        return {
            "decision_review": "POSSIBLE_BAD_ENTRY",
            "confidence": 0.74,
            "original_reason": reason,
            "review_reason": "entrada_aprovada_com_conflitos_relevantes",
            "suggested_action": "revisar_context_engine_e_ai_advisor",
            "safe_to_auto_change": False,
            "provider": "mock_heuristic",
        }
    return {
        "decision_review": "OK",
        "confidence": 0.60,
        "original_reason": reason,
        "review_reason": "sem_inconsistencia_forte",
        "suggested_action": "manter_observacao",
        "safe_to_auto_change": False,
        "provider": "mock_heuristic",
    }


def route_payload(path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    if path == "/health":
        return 200, {"status": "ok", "service": "fusion_ai_bridge"}
    if path == "/advice":
        return 200, mock_advice(payload)
    if path == "/review":
        return 200, mock_review(payload)
    return 404, {"error": "not_found", "path": path}


class AIBridgeHandler(BaseHTTPRequestHandler):
    server_version = "FusionAIBridge/1.0"

    def _write_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        status, response = route_payload(self.path.split("?", 1)[0], {})
        self._write_json(status, response)

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0") or "0")
        except ValueError:
            length = 0
        raw = self.rfile.read(length).decode("utf-8", errors="replace") if length > 0 else "{}"
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            self._write_json(400, {"error": "invalid_json"})
            return
        status, response = route_payload(self.path.split("?", 1)[0], payload)
        self._write_json(status, response)

    def log_message(self, format: str, *args: Any) -> None:
        return


def run_bridge(config: AIBridgeConfig | None = None) -> None:
    cfg = config or AIBridgeConfig()
    server = ThreadingHTTPServer((cfg.host, int(cfg.port)), AIBridgeHandler)
    print(f"Fusion AI Bridge em http://{cfg.host}:{cfg.port} provider={cfg.provider}")
    server.serve_forever()
