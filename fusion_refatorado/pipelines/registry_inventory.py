from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from common import PROJECT_ROOT


def inventory_files(root: Path) -> pd.DataFrame:
    rows = []
    if not root.exists():
        return pd.DataFrame(columns=["relative_path", "size_bytes", "extension"])
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rows.append(
                {
                    "relative_path": str(path.relative_to(root)),
                    "size_bytes": path.stat().st_size,
                    "extension": path.suffix.lower(),
                }
            )
    return pd.DataFrame(rows)


def build_registry_inventory(output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    targets = {
        "models": PROJECT_ROOT / "models",
        "data": PROJECT_ROOT / "data",
        "docs": PROJECT_ROOT / "docs",
        "config": PROJECT_ROOT / "config",
    }
    written: dict[str, str] = {}
    for name, root in targets.items():
        frame = inventory_files(root)
        out = output_dir / f"{name}_registry_inventory.csv"
        frame.to_csv(out, index=False)
        written[name] = str(out)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Build consolidated inventories for migrated FUSION_V2 artifacts.")
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "docs" / "registry"))
    args = parser.parse_args()
    written = build_registry_inventory(Path(args.output_dir))
    for name, path in written.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
