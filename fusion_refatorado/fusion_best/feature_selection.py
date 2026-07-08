from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

import pandas as pd


@dataclass(frozen=True)
class FinalFeatureRules:
    alpha_core_contains: tuple[str, ...] = (
        "ret_",
        "ma_",
        "std_",
        "corr_",
        "close_ma",
        "lag_",
        "atr_",
        "close_position",
    )
    keep_exact: tuple[str, ...] = (
        "structure_trend",
        "liq_cluster",
        "liq_pressure",
        "spread",
        "spread_norm",
    )
    remove_contains: tuple[str, ...] = ("microstructure",)


def select_final_features(
    df: pd.DataFrame,
    target_col: str = "target",
    rules: FinalFeatureRules | None = None,
) -> pd.DataFrame:
    """Reusable version of ALPHAEDU alpha_final.py."""
    cfg = rules or FinalFeatureRules()
    numeric = df.select_dtypes(include=["number", "bool"]).replace([float("inf"), float("-inf")], pd.NA).dropna()
    selected: list[str] = []
    for col in numeric.columns:
        if col == target_col:
            continue
        keep = any(pattern in col for pattern in cfg.alpha_core_contains)
        keep = keep or col in cfg.keep_exact
        if any(pattern in col for pattern in cfg.remove_contains):
            keep = False
        if keep:
            selected.append(col)
    if target_col in numeric.columns:
        selected.append(target_col)
    return numeric[selected].copy()


def best_window_sets_from_scan(
    scan: pd.DataFrame,
    feature_col: str = "feature",
    window_col: str = "window",
    score_col: str = "logloss",
) -> dict[str, list[int]]:
    """Extract optimized window lists from a feature-parameter scan result."""
    if scan.empty:
        raise ValueError("scan vazio")
    best = scan.sort_values(score_col).groupby(feature_col, as_index=False).first()
    windows: set[int] = set()
    extra_windows: set[int] = set()
    final_windows: set[int] = set()
    for _, row in best.iterrows():
        feature = str(row[feature_col])
        window = int(row[window_col])
        if "_extra_" in feature:
            extra_windows.add(window)
        elif "_final_" in feature:
            final_windows.add(window)
        else:
            windows.add(window)
    return {
        "windows": sorted(windows or {5, 10, 20, 30, 60}),
        "extra_windows": sorted(extra_windows or {2, 4, 8, 15, 25, 40, 80}),
        "final_windows": sorted(final_windows or {6, 9, 12, 18, 24, 36, 48}),
    }


def replace_window_lists_in_source(source: str, window_sets: dict[str, list[int]]) -> str:
    """Pure function version of 07_apply_best_parameters.py without file side effects."""
    result = source
    for name, values in window_sets.items():
        result = re.sub(rf"{name}\s*=\s*\[[^\]]*\]", f"{name} = {values}", result)
    return result


def select_top_features(
    df: pd.DataFrame,
    importance: pd.DataFrame,
    top_n: int = 30,
    base_cols: Iterable[str] = ("date", "time", "close", "future_close", "target"),
) -> pd.DataFrame:
    keep_cols = [c for c in base_cols if c in df.columns]
    keep_cols += [c for c in importance["feature"].head(top_n).tolist() if c in df.columns]
    keep_cols = list(dict.fromkeys(keep_cols))
    return df[keep_cols].copy()
