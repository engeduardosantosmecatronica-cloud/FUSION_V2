from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import urllib.error
import urllib.request
from typing import Any, Iterable


@dataclass
class AIReviewConfig:
    endpoint_url: str = "http://127.0.0.1:8765/review"
    timeout_seconds: float = 12.0
    fail_open: bool = True
    model_hint: str = "gpt-5.4-nano"
    max_events: int = 50
    min_tradeability_gap: float = 0.20


class AIReviewAgent:
    """Revisa decisoes gravadas pelo Decision Audit.

    Este agente e deliberadamente offline: ele nao altera configuracao, nao abre
    ordem e nao fecha posicao. A saida e um JSONL de revisoes para analise.
    """

    def __init__(self, config: AIReviewConfig | None = None):
        self.config = config or AIReviewConfig()

    @staticmethod
    def iter_events(log_dir: Path, date: str = "") -> Iterable[dict[str, Any]]:
        pattern = f"decision_audit_{date}.jsonl" if date else "decision_audit_*.jsonl"
        for path in sorted(log_dir.glob(pattern)):
            with path.open("r", encoding="utf-8") as handle:
                for line_no, line in enumerate(handle, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    event["_source_file"] = path.name
                    event["_source_line"] = line_no
                    yield event

    @staticmethod
    def _compact_engine(engine: dict[str, Any]) -> dict[str, Any]:
        return {
            "engine": engine.get("engine", ""),
            "direction": engine.get("direction", ""),
            "score": engine.get("score", 0.0),
            "confidence": engine.get("confidence", 0.0),
            "state": engine.get("state", ""),
            "positive_factors": engine.get("positive_factors", [])[:8],
            "negative_factors": engine.get("negative_factors", [])[:8],
            "warnings": engine.get("warnings", [])[:8],
        }

    def build_payload(self, event: dict[str, Any]) -> dict[str, Any]:
        candidate = event.get("candidate", {}) or {}
        result = event.get("result", {}) or {}
        engines = event.get("engines", []) or []
        return {
            "task": "Revisar se a decisao do robo foi coerente com os sinais, filtros, contexto e risco.",
            "required_response_schema": {
                "decision_review": "OK | POSSIBLE_FALSE_BLOCK | POSSIBLE_BAD_ENTRY | NEEDS_MORE_DATA",
                "confidence": "0.0-1.0",
                "original_reason": "string",
                "review_reason": "string curta",
                "suggested_action": "string curta",
                "safe_to_auto_change": False,
            },
            "rules": [
                "Nao proponha abrir ordem retroativamente.",
                "Nao altere configuracao automaticamente.",
                "Responda apenas JSON valido.",
                "Marque safe_to_auto_change como false salvo em cenarios triviais de log/rotulo.",
            ],
            "model_hint": self.config.model_hint,
            "event_ref": {
                "source_file": event.get("_source_file", ""),
                "source_line": event.get("_source_line", 0),
                "timestamp": event.get("timestamp", ""),
            },
            "candidate": candidate,
            "result": result,
            "engines": [self._compact_engine(engine) for engine in engines],
            "portfolio": event.get("portfolio", {}) or {},
        }

    def heuristic_review(self, event: dict[str, Any]) -> dict[str, Any]:
        result = event.get("result", {}) or {}
        candidate = event.get("candidate", {}) or {}
        engines = event.get("engines", []) or []
        decision = str(result.get("decision", "")).upper()
        reason = str(result.get("reason", "") or "")
        tradeability = float(result.get("tradeability_score", 0.0) or 0.0)
        conflict = float(result.get("conflict_score", 0.0) or 0.0)
        aligned = 0
        conflicts = 0
        side = str(candidate.get("side", "")).upper()
        for engine in engines:
            direction = str(engine.get("direction", "")).upper()
            if direction == side:
                aligned += 1
            elif direction in {"BUY", "SELL"} and direction != side:
                conflicts += 1

        review = "OK"
        confidence = 0.55
        review_reason = "heuristica_sem_inconsistencia_forte"
        suggested_action = "manter_observacao"

        if decision == "BLOCK" and tradeability >= 0.65 and conflicts == 0:
            review = "POSSIBLE_FALSE_BLOCK"
            confidence = 0.70
            review_reason = "bloqueio_com_tradeability_alto_e_sem_conflito_direcional"
            suggested_action = f"revisar_filtro:{reason}"
        elif decision == "ALLOW" and (conflict >= 0.40 or conflicts >= max(2, aligned + 1)):
            review = "POSSIBLE_BAD_ENTRY"
            confidence = 0.72
            review_reason = "entrada_aprovada_com_conflito_contextual_relevante"
            suggested_action = "revisar_pesos_consensus_ou_filtro_conflitante"
        elif not engines:
            review = "NEEDS_MORE_DATA"
            confidence = 0.60
            review_reason = "evento_sem_engines_para_revisao"
            suggested_action = "verificar_decision_audit"

        return {
            "decision_review": review,
            "confidence": confidence,
            "original_reason": reason,
            "review_reason": review_reason,
            "suggested_action": suggested_action,
            "safe_to_auto_change": False,
            "reviewer": "heuristic",
        }

    def call_ai(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        request = urllib.request.Request(
            self.config.endpoint_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
            raw = response.read().decode("utf-8", errors="replace")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            start = raw.find("{")
            end = raw.rfind("}")
            if start >= 0 and end > start:
                return json.loads(raw[start : end + 1])
            raise

    def review_event(self, event: dict[str, Any], use_ai: bool = False) -> dict[str, Any]:
        payload = self.build_payload(event)
        ai_error = ""
        if use_ai:
            try:
                review = self.call_ai(payload)
                review["reviewer"] = "ai"
            except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
                ai_error = f"{type(exc).__name__}: {exc}"
                review = self.heuristic_review(event)
                review["reviewer"] = "heuristic_fallback"
        else:
            review = self.heuristic_review(event)

        if "safe_to_auto_change" not in review:
            review["safe_to_auto_change"] = False
        review["safe_to_auto_change"] = bool(review.get("safe_to_auto_change", False)) and False
        return {
            "timestamp": datetime.now().isoformat(),
            "event_ref": payload["event_ref"],
            "candidate": payload["candidate"],
            "original_result": payload["result"],
            "review": review,
            "ai_error": ai_error,
            "payload": payload,
        }

    def review_events(self, events: list[dict[str, Any]], use_ai: bool = False) -> list[dict[str, Any]]:
        limited = events[-max(1, int(self.config.max_events)) :]
        return [self.review_event(event, use_ai=use_ai) for event in limited]

    @staticmethod
    def write_reviews(reviews: list[dict[str, Any]], output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"ai_reviews_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        with path.open("w", encoding="utf-8") as handle:
            for review in reviews:
                handle.write(json.dumps(review, ensure_ascii=False, default=str) + "\n")
        return path

    @staticmethod
    def write_markdown(reviews: list[dict[str, Any]], path: Path) -> None:
        counts: dict[str, int] = {}
        for item in reviews:
            key = str((item.get("review", {}) or {}).get("decision_review", "UNKNOWN"))
            counts[key] = counts.get(key, 0) + 1
        lines = ["# AI Decision Review", ""]
        lines.append(f"- Revisoes: {len(reviews)}")
        for key, count in sorted(counts.items()):
            lines.append(f"- {key}: {count}")
        lines.extend(["", "## Eventos Relevantes", ""])
        for item in reviews:
            review = item.get("review", {}) or {}
            if review.get("decision_review") == "OK":
                continue
            candidate = item.get("candidate", {}) or {}
            original = item.get("original_result", {}) or {}
            ref = item.get("event_ref", {}) or {}
            lines.append(
                f"- {ref.get('timestamp', '')} {candidate.get('strategy', '')} "
                f"{candidate.get('symbol', '')} {candidate.get('timeframe', '')} {candidate.get('side', '')}: "
                f"{review.get('decision_review')} conf={float(review.get('confidence', 0.0) or 0.0):.2f} "
                f"original={original.get('decision', '')}/{original.get('reason', '')} "
                f"acao={review.get('suggested_action', '')}"
            )
        path.write_text("\n".join(lines), encoding="utf-8")
