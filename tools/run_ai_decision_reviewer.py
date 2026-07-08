from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fusion.ai import AIReviewAgent, AIReviewConfig
from fusion.core.config import get_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Revisa Decision Audit com heuristica local ou IA externa.")
    parser.add_argument("--log-dir", default="logs/decision_audit")
    parser.add_argument("--output-dir", default="logs/ai_reviews")
    parser.add_argument("--date", default="", help="Data YYYYMMDD. Se vazio, le todos os arquivos.")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--use-ai", action="store_true", help="Chama endpoint HTTP configurado.")
    parser.add_argument("--endpoint-url", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = get_config()
    cfg = config.get("ai_review_agent", {}) or {}
    endpoint = args.endpoint_url or str(cfg.get("endpoint_url", "http://127.0.0.1:8765/review"))
    agent = AIReviewAgent(
        AIReviewConfig(
            endpoint_url=endpoint,
            timeout_seconds=float(cfg.get("timeout_seconds", 12) or 12),
            fail_open=bool(cfg.get("fail_open", True)),
            model_hint=str(cfg.get("model_hint", "gpt-5.4-nano") or "gpt-5.4-nano"),
            max_events=int(args.limit or cfg.get("max_events", 50) or 50),
        )
    )
    events = list(agent.iter_events(Path(args.log_dir), args.date))
    reviews = agent.review_events(events, use_ai=args.use_ai)
    output_dir = Path(args.output_dir)
    jsonl_path = agent.write_reviews(reviews, output_dir)
    md_path = output_dir / f"{jsonl_path.stem}.md"
    agent.write_markdown(reviews, md_path)
    print(f"Eventos lidos: {len(events)}")
    print(f"Revisoes geradas: {len(reviews)}")
    print(f"JSONL: {jsonl_path}")
    print(f"Resumo: {md_path}")
    if args.use_ai:
        print(f"Endpoint IA: {endpoint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
