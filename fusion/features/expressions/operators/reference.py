import pandas as pd


def Ref(series: pd.Series, n: int):
    return series.shift(n)


def Delta(series: pd.Series, n: int):
    return series.diff(n)