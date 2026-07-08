from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera perfis de calibracao probabilistica por ativo/timeframe/lado.")
    parser.add_argument(
        "--candidates",
        nargs="+",
        default=[
            "reports/market_structure_calibration/market_structure_calibration_candidates_atr1.5_slatr1_lh100.csv",
            "reports/market_structure_calibration/market_structure_calibration_candidates_tp100_sl100_lh100.csv",
            "reports/market_structure_calibration/market_structure_calibration_candidates_optimized_lh100.csv",
        ],
    )
    parser.add_argument("--output-dir", default="reports/confidence_calibration")
    parser.add_argument("--prior-samples", type=float, default=200.0)
    parser.add_argument("--prior-probability", type=float, default=0.50)
    parser.add_argument("--min-samples", type=int, default=300)
    return parser.parse_args()


def load_candidates(paths: list[str]) -> pd.DataFrame:
    frames = []
    for value in paths:
        path = Path(value)
        if not path.is_absolute():
            path = ROOT / path
        if not path.exists():
            continue
        frame = pd.read_csv(path)
        if frame.empty:
            continue
        frame["source"] = path.stem.replace("market_structure_calibration_candidates_", "")
        frames.append(frame)
    if not frames:
        return pd.DataFrame()
    data = pd.concat(frames, ignore_index=True)
    data["symbol"] = data["symbol"].astype(str).str.upper()
    data["timeframe"] = data["timeframe"].astype(str).str.upper()
    data["side"] = data["side"].astype(str).str.lower()
    for col in ["samples", "win_rate", "edge_score"]:
        data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0.0)
    data = data[data["samples"] > 0].copy()
    return data


def wilson_lower(wins: float, samples: float, z: float = 1.96) -> float:
    if samples <= 0:
        return 0.0
    p = wins / samples
    denom = 1.0 + (z * z / samples)
    centre = p + (z * z / (2.0 * samples))
    margin = z * math.sqrt(((p * (1.0 - p)) + (z * z / (4.0 * samples))) / samples)
    return max(0.0, min(1.0, (centre - margin) / denom))


def build_profiles(data: pd.DataFrame, group_cols: list[str], prior_samples: float, prior_probability: float) -> list[dict]:
    rows = []
    for key, group in data.groupby(group_cols):
        if not isinstance(key, tuple):
            key = (key,)
        samples = group["samples"].sum()
        wins = (group["samples"] * group["win_rate"]).sum()
        posterior = (wins + (prior_samples * prior_probability)) / (samples + prior_samples)
        weighted_win_rate = wins / samples if samples else 0.0
        edge_weight = (group["edge_score"].clip(lower=0.0) + 0.10) * group["samples"]
        edge_weighted_win_rate = (
            (group["win_rate"] * edge_weight).sum() / edge_weight.sum()
            if edge_weight.sum() > 0
            else weighted_win_rate
        )
        wilson = wilson_lower(wins, samples)
        reliability = max(0.0, min(1.0, (wilson * 0.70) + (min(samples / 5000.0, 1.0) * 0.30)))
        row = {
            "samples": int(samples),
            "wins_estimated": float(wins),
            "feature_count": int(group["feature"].nunique()) if "feature" in group.columns else int(len(group)),
            "rule_count": int(len(group)),
            "weighted_win_rate": float(weighted_win_rate),
            "edge_weighted_win_rate": float(edge_weighted_win_rate),
            "posterior_probability": float(posterior),
            "wilson_lower": float(wilson),
            "reliability_score": float(reliability),
            "avg_edge": float(group["edge_score"].mean()),
            "max_edge": float(group["edge_score"].max()),
            "sources": sorted(str(item) for item in group["source"].dropna().unique()),
        }
        for col, value in zip(group_cols, key):
            row[col] = str(value)
        rows.append(row)
    return rows


def write_report(path: Path, payload: dict) -> None:
    profiles = pd.DataFrame(payload.get("profiles", []))
    lines = ["# Confidence Calibration Profiles", ""]
    lines.append(f"- Perfis exatos: {len(payload.get('profiles', []))}")
    lines.append(f"- Perfis fallback: {len(payload.get('fallback_profiles', []))}")
    lines.append(f"- Prior samples: {payload.get('prior_samples')}")
    lines.append(f"- Prior probability: {payload.get('prior_probability')}")
    if not profiles.empty:
        lines.extend(["", "## Top Perfis Por Confiabilidade", ""])
        cols = ["symbol", "timeframe", "side", "samples", "posterior_probability", "wilson_lower", "reliability_score"]
        for row in profiles.sort_values("reliability_score", ascending=False).head(30)[cols].itertuples(index=False):
            lines.append(
                f"- {row.symbol} {row.timeframe} {row.side}: "
                f"samples={row.samples} posterior={row.posterior_probability:.3f} "
                f"wilson={row.wilson_lower:.3f} reliability={row.reliability_score:.3f}"
            )
        lines.extend(["", "## Cobertura Por Ativo/Timeframe", ""])
        coverage = profiles.groupby(["symbol", "timeframe"]).size().reset_index(name="profiles")
        for row in coverage.sort_values(["symbol", "timeframe"]).itertuples(index=False):
            lines.append(f"- {row.symbol} {row.timeframe}: {row.profiles}")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    out_dir = Path(args.output_dir)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    data = load_candidates(args.candidates)
    if data.empty:
        print("Nenhum candidato encontrado.")
        return 1

    profiles = build_profiles(data, ["symbol", "timeframe", "side"], args.prior_samples, args.prior_probability)
    fallback_profiles = []
    fallback_profiles.extend(build_profiles(data.assign(symbol="*"), ["symbol", "timeframe", "side"], args.prior_samples, args.prior_probability))
    fallback_profiles.extend(build_profiles(data.assign(timeframe="*"), ["symbol", "timeframe", "side"], args.prior_samples, args.prior_probability))
    fallback_profiles.extend(build_profiles(data.assign(symbol="*", timeframe="*"), ["symbol", "timeframe", "side"], args.prior_samples, args.prior_probability))

    payload = {
        "version": "confidence_calibration_profiles_v1",
        "prior_samples": args.prior_samples,
        "prior_probability": args.prior_probability,
        "min_samples": args.min_samples,
        "profiles": profiles,
        "fallback_profiles": fallback_profiles,
        "sources": args.candidates,
    }
    json_path = out_dir / "confidence_calibration_profiles.json"
    md_path = out_dir / "confidence_calibration_profiles.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(md_path, payload)
    print(f"Perfis exatos: {len(profiles)}")
    print(f"Perfis fallback: {len(fallback_profiles)}")
    print(f"Saida: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
