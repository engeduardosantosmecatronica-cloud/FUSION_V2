from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / "venv" / "Scripts" / "python.exe"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Executa a suíte de validação do Event Bus.")
    parser.add_argument("--date", required=True, help="Data YYYYMMDD.")
    parser.add_argument("--skip-async-smoke", action="store_true")
    return parser.parse_args()


def run_step(label: str, args: list[str]) -> tuple[str, int, str]:
    print(f"\n=== {label} ===")
    result = subprocess.run(
        [str(PYTHON if PYTHON.exists() else sys.executable), *args],
        cwd=ROOT,
        text=True,
    )
    return label, result.returncode, ""


def main() -> None:
    args = parse_args()
    steps: list[tuple[str, list[str]]] = [
        ("Integridade", ["tools/check_event_bus_integrity.py", "--date", args.date]),
        ("Relatorio Event Bus", ["tools/build_event_bus_report.py", "--date", args.date]),
        ("Performance por evento", ["tools/analyze_event_performance.py", "--date", args.date]),
        ("Replay OMS", ["tools/replay_oms_state.py", "--date", args.date]),
        ("Cruzamento financeiro", ["tools/validate_order_financial_cross.py", "--date", args.date]),
    ]
    if not args.skip_async_smoke:
        steps.append(("Smoke async", ["tools/check_event_bus_async.py", "--events", "2000", "--output-dir", "reports/event_bus_async_smoke"]))

    results = [run_step(label, command) for label, command in steps]
    failed = [label for label, code, _ in results if code != 0]
    print("\n=== RESUMO ===")
    for label, code, _ in results:
        print(f"{label}: {'OK' if code == 0 else 'FAIL'}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
