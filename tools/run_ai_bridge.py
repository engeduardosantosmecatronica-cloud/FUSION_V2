from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fusion.ai import AIBridgeConfig, run_bridge
from fusion.core.config import get_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sobe a ponte local /advice e /review para IA.")
    parser.add_argument("--host", default="")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--provider", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = get_config()
    cfg = config.get("ai_bridge", {}) or {}
    run_bridge(
        AIBridgeConfig(
            host=args.host or str(cfg.get("host", "127.0.0.1")),
            port=int(args.port or cfg.get("port", 8765) or 8765),
            provider=args.provider or str(cfg.get("provider", "mock_heuristic")),
            model_hint=str(cfg.get("model_hint", "gpt-5.4-nano")),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
