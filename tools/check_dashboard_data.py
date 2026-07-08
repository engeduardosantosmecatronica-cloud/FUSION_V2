from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.fusion_dashboard import latest_decision_audit_file, read_decision_audit


def main() -> int:
    path = latest_decision_audit_file()
    if not path:
        print("sem decision_audit")
        return 0
    events, engines = read_decision_audit(str(path), tail=50)
    print(f"audit={path.name} events={len(events)} engines={len(engines)}")
    if events.empty:
        raise SystemExit("events empty")
    if engines.empty:
        raise SystemExit("engines empty")
    required = {"symbol", "timeframe", "tradeability_score"}
    if not required.issubset(events.columns):
        raise SystemExit("missing event columns")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
