from __future__ import annotations

import argparse
import csv
import shutil
from datetime import datetime
from pathlib import Path

import joblib


ROOT = Path(__file__).resolve().parents[1]
TIMEFRAMES = ["M5", "M15", "M30", "H1", "H4", "D1"]


def read_symbols(config_path: Path) -> list[str]:
    try:
        import yaml
    except ImportError as exc:
        raise SystemExit(f"PyYAML indisponivel: {exc}") from exc
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return [str(item).upper() for item in payload.get("symbols", [])]


def model_source(meta_path: Path) -> str:
    try:
        meta = joblib.load(meta_path)
    except Exception:
        return "erro_meta"
    return str(meta.get("source") or "fusion_original")


def iter_models(models_dir: Path):
    for symbol_dir in sorted(models_dir.iterdir()):
        if not symbol_dir.is_dir():
            continue
        for tf_dir in sorted(symbol_dir.iterdir()):
            if not tf_dir.is_dir():
                continue
            meta_path = tf_dir / "meta.pkl"
            if meta_path.exists():
                yield symbol_dir.name.upper(), tf_dir.name.upper(), tf_dir, model_source(meta_path)


def archive_model_dir(tf_dir: Path, archive_root: Path, source: str, dry_run: bool) -> Path:
    rel = tf_dir.relative_to(ROOT / "models_principal")
    dst = archive_root / source / rel
    if dry_run:
        return dst
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.move(str(tf_dir), str(dst))
    return dst


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Arquiva modelos importados e reporta lacunas.")
    parser.add_argument("--models-dir", default="models_principal")
    parser.add_argument("--config", default="config/fusion_config.yaml")
    parser.add_argument(
        "--archive-sources",
        nargs="+",
        default=["data/parquet"],
        help="sources a arquivar. Use fusion_original para os antigos sem source.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    models_dir = ROOT / args.models_dir
    config_path = ROOT / args.config
    archive_root = ROOT / "archive" / "models_discarded" / datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_sources = set(args.archive_sources)
    symbols = read_symbols(config_path)

    inventory_rows: list[dict] = []
    moved_rows: list[dict] = []
    existing_after: set[tuple[str, str]] = set()

    for symbol, timeframe, tf_dir, source in iter_models(models_dir):
        should_archive = source in archive_sources
        inventory_rows.append(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "source": source,
                "action": "archive" if should_archive else "keep",
                "path": str(tf_dir),
            }
        )
        if should_archive:
            dst = archive_model_dir(tf_dir, archive_root, source.replace("/", "_"), args.dry_run)
            moved_rows.append(
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "source": source,
                    "archive_path": str(dst),
                }
            )
        else:
            existing_after.add((symbol, timeframe))

    missing_rows = [
        {"symbol": symbol, "timeframe": timeframe}
        for symbol in symbols
        for timeframe in TIMEFRAMES
        if (symbol, timeframe) not in existing_after
    ]

    report_dir = ROOT / "reports" / "model_source_cleanup"
    suffix = "dry_run" if args.dry_run else "applied"
    write_csv(report_dir / f"inventory_{suffix}.csv", inventory_rows)
    write_csv(report_dir / f"archived_{suffix}.csv", moved_rows)
    write_csv(report_dir / f"missing_for_retrain_{suffix}.csv", missing_rows)

    print(f"Inventario: {len(inventory_rows)} modelos")
    print(f"Arquivados: {len(moved_rows)}")
    print(f"Faltando retreino: {len(missing_rows)}")
    print(f"Relatorios: {report_dir}")
    if moved_rows and not args.dry_run:
        print(f"Arquivo dos modelos removidos do runtime: {archive_root}")


if __name__ == "__main__":
    main()
