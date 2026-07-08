import pandas as pd


def Rank(series: pd.Series):
    return series.rank(pct=True)


def TsRank(series: pd.Series, n: int):
    return (
        series
        .rolling(n)
        .rank(pct=True)
    )