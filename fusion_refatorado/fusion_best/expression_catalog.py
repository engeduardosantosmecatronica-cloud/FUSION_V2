from __future__ import annotations

import numpy as np
import pandas as pd


FOREX_BASIC_EXPRESSIONS = {
    "ret_1": "Delta($close, 1)",
    "ret_5": "Delta($close, 5)",
    "ma_5": "Mean($close, 5)",
    "ma_10": "Mean($close, 10)",
    "ma_20": "Mean($close, 20)",
    "std_5": "Std($close, 5)",
    "std_10": "Std($close, 10)",
    "std_20": "Std($close, 20)",
    "corr_10": "Corr($close, $volume, 10)",
    "corr_20": "Corr($close, $volume, 20)",
    "range": "$high - $low",
    "body": "Abs($close - $open)",
    "upper_wick": "$high - Max($open, $close)",
    "lower_wick": "Min($open, $close) - $low",
}

ALPHA158_OPTIMIZED_WINDOWS = (12, 15, 22, 30, 45, 60, 62, 120)
ALPHA158_BASE_WINDOWS = (5, 10, 20, 30, 60)


def build_alpha158_expression_names(windows: tuple[int, ...] = ALPHA158_OPTIMIZED_WINDOWS) -> list[str]:
    names: list[str] = []
    names += [f"ret_{w}" for w in (1, 3, 5, 10, 20)]
    for w in windows:
        names += [
            f"ma_{w}",
            f"close_ma{w}_ratio",
            f"std_{w}",
            f"corr_{w}",
            f"high_max_{w}",
            f"low_min_{w}",
            f"close_high_ratio_{w}",
            f"close_low_ratio_{w}",
        ]
    names += [
        "range",
        "body",
        "upper_wick",
        "lower_wick",
        "close_position",
        "hl_range",
        "hc_range",
        "lc_range",
        "true_range",
    ]
    return names


def Ref(series: pd.Series, n: int) -> pd.Series:
    return series.shift(n)


def Delta(series: pd.Series, n: int) -> pd.Series:
    return series.diff(n)


def Mean(series: pd.Series, n: int) -> pd.Series:
    return series.rolling(n).mean()


def Std(series: pd.Series, n: int) -> pd.Series:
    return series.rolling(n).std()


def Corr(a: pd.Series, b: pd.Series, n: int) -> pd.Series:
    return a.rolling(n).corr(b)


def Cov(a: pd.Series, b: pd.Series, n: int) -> pd.Series:
    return a.rolling(n).cov(b)


def Rank(series: pd.Series) -> pd.Series:
    return series.rank(pct=True)


def TsRank(series: pd.Series, n: int) -> pd.Series:
    return series.rolling(n).rank(pct=True)


def Log(series: pd.Series) -> pd.Series:
    return np.log(series)


def Abs(series: pd.Series) -> pd.Series:
    return np.abs(series)


def Sign(series: pd.Series) -> pd.Series:
    return np.sign(series)
