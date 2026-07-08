from __future__ import annotations

from pathlib import Path

import pandas as pd
from pandas.api.types import is_datetime64_any_dtype

from .features import build_feature_matrix, create_multiclass_target
from .extended_experts import build_extended_expert_features
from .omnis_experts import build_omnis_expert_features
from .specialists import build_specialist_features


def normalize_ohlcv_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result.columns = [str(c).replace("<", "").replace(">", "").lower().strip() for c in result.columns]
    has_datetime_index = isinstance(result.index, pd.DatetimeIndex) or is_datetime64_any_dtype(result.index)
    if "date" in result.columns and "time" in result.columns:
        result["time"] = pd.to_datetime(result["date"].astype(str) + " " + result["time"].astype(str), errors="coerce")
    if "datetime" in result.columns and "time" not in result.columns:
        result = result.rename(columns={"datetime": "time"})
    if "date" in result.columns and "time" not in result.columns and not has_datetime_index:
        result = result.rename(columns={"date": "time"})
    if "tickvol" in result.columns and "volume" not in result.columns:
        result = result.rename(columns={"tickvol": "volume"})
    if "vol" in result.columns and "volume" not in result.columns:
        result = result.rename(columns={"vol": "volume"})
    if "time" in result.columns:
        result["time"] = pd.to_datetime(result["time"])
        result = result.set_index("time")
    elif has_datetime_index:
        result.index = pd.to_datetime(result.index)
    result = result.sort_index()
    return result[~result.index.duplicated(keep="last")]


def build_training_dataset(
    df: pd.DataFrame,
    horizon: int = 12,
    threshold: float = 0.0008,
    include_specialists: bool = True,
    include_omnis_experts: bool = False,
    include_extended_experts: bool = False,
    include_raw_ohlcv: bool = True,
) -> pd.DataFrame:
    """Build the reusable version of ALPHAEDU's feature orchestrator."""
    data = normalize_ohlcv_columns(df)
    features = build_feature_matrix(data, include_raw_ohlcv=include_raw_ohlcv)
    if include_specialists:
        specialist_features = build_specialist_features(data)
        features = pd.concat([features, specialist_features], axis=1)
        features = features.loc[:, ~features.columns.duplicated()]
    if include_omnis_experts:
        omnis_features = build_omnis_expert_features(data)
        features = pd.concat([features, omnis_features], axis=1)
        features = features.loc[:, ~features.columns.duplicated()]
    if include_extended_experts:
        extended_features = build_extended_expert_features(data)
        features = pd.concat([features, extended_features], axis=1)
        features = features.loc[:, ~features.columns.duplicated()]
    target = create_multiclass_target(data, horizon=horizon, threshold=threshold)
    dataset = pd.concat([features, target.rename("target")], axis=1)
    return dataset.replace([float("inf"), -float("inf")], pd.NA).dropna()


def build_training_dataset_from_file(
    input_path: str | Path,
    output_path: str | Path | None = None,
    horizon: int = 12,
    threshold: float = 0.0008,
    include_omnis_experts: bool = False,
    include_extended_experts: bool = False,
) -> pd.DataFrame:
    input_path = Path(input_path)
    if input_path.suffix.lower() == ".parquet":
        df = pd.read_parquet(input_path)
    else:
        df = pd.read_csv(input_path)
    dataset = build_training_dataset(
        df,
        horizon=horizon,
        threshold=threshold,
        include_omnis_experts=include_omnis_experts,
        include_extended_experts=include_extended_experts,
    )
    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.suffix.lower() == ".parquet":
            dataset.to_parquet(output_path)
        else:
            dataset.to_csv(output_path, index=True)
    return dataset
