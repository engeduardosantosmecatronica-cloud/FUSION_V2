from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import joblib
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def iter_model_meta(models_dir: Path):
    for meta_path in sorted(models_dir.glob("*/*/meta.pkl")):
        try:
            meta = joblib.load(meta_path)
        except Exception as exc:
            yield {
                "symbol": meta_path.parts[-3].upper(),
                "timeframe": meta_path.parts[-2].upper(),
                "source": "erro_meta",
                "features": [],
                "error": f"{type(exc).__name__}: {exc}",
                "path": str(meta_path),
            }
            continue
        yield {
            "symbol": str(meta.get("symbol") or meta_path.parts[-3]).upper(),
            "timeframe": str(meta.get("timeframe") or meta_path.parts[-2]).upper(),
            "source": str(meta.get("source") or "fusion_original"),
            "features": list(meta.get("feature_columns", []) or []),
            "error": "",
            "path": str(meta_path),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventaria features usadas pelos modelos ativos.")
    parser.add_argument("--models-dir", default="models_principal")
    parser.add_argument("--output-dir", default="reports/model_feature_inventory")
    args = parser.parse_args()

    models_dir = ROOT / args.models_dir
    output_dir = ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    models = list(iter_model_meta(models_dir))
    model_rows = []
    long_rows = []
    counter = Counter()
    by_source = defaultdict(Counter)
    by_timeframe = defaultdict(Counter)
    by_feature_set = Counter()

    for item in models:
        features = item["features"]
        feature_signature = "|".join(features)
        by_feature_set[feature_signature] += 1
        model_rows.append(
            {
                "symbol": item["symbol"],
                "timeframe": item["timeframe"],
                "source": item["source"],
                "feature_count": len(features),
                "feature_signature_id": abs(hash(feature_signature)),
                "error": item["error"],
                "meta_path": item["path"],
            }
        )
        for feature in features:
            counter[feature] += 1
            by_source[item["source"]][feature] += 1
            by_timeframe[item["timeframe"]][feature] += 1
            long_rows.append(
                {
                    "symbol": item["symbol"],
                    "timeframe": item["timeframe"],
                    "source": item["source"],
                    "feature": feature,
                }
            )

    model_df = pd.DataFrame(model_rows).sort_values(["symbol", "timeframe"])
    long_df = pd.DataFrame(long_rows).sort_values(["feature", "symbol", "timeframe"])
    freq_df = pd.DataFrame(
        [{"feature": feature, "model_count": count} for feature, count in counter.most_common()]
    )

    signatures = []
    for idx, (signature, count) in enumerate(by_feature_set.most_common(), start=1):
        features = signature.split("|") if signature else []
        signatures.append(
            {
                "signature_id": idx,
                "model_count": count,
                "feature_count": len(features),
                "features": ", ".join(features),
            }
        )
    sig_df = pd.DataFrame(signatures)

    model_df.to_csv(output_dir / "models_feature_summary.csv", index=False)
    long_df.to_csv(output_dir / "model_features_long.csv", index=False)
    freq_df.to_csv(output_dir / "feature_frequency.csv", index=False)
    sig_df.to_csv(output_dir / "feature_sets.csv", index=False)

    payload = {
        "models": len(models),
        "unique_features": len(counter),
        "feature_frequency": dict(counter.most_common()),
        "by_source": {source: dict(counts.most_common()) for source, counts in by_source.items()},
        "by_timeframe": {tf: dict(counts.most_common()) for tf, counts in by_timeframe.items()},
    }
    (output_dir / "feature_inventory.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# Inventario de Features dos Modelos Ativos",
        "",
        f"- Modelos inventariados: {len(models)}",
        f"- Features unicas: {len(counter)}",
        f"- Conjuntos distintos de features: {len(by_feature_set)}",
        "",
        "## Features Mais Usadas",
    ]
    for feature, count in counter.most_common():
        lines.append(f"- `{feature}`: {count} modelos")
    lines.extend(["", "## Arquivos Gerados", ""])
    for name in [
        "models_feature_summary.csv",
        "model_features_long.csv",
        "feature_frequency.csv",
        "feature_sets.csv",
        "feature_inventory.json",
    ]:
        lines.append(f"- `{name}`")
    (output_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"Modelos: {len(models)}")
    print(f"Features unicas: {len(counter)}")
    print(f"Saida: {output_dir}")


if __name__ == "__main__":
    main()
