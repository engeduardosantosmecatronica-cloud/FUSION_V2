import pandas as pd


def Corr(a: pd.Series, b: pd.Series, n: int):
    return a.rolling(n).corr(b)


def Cov(a: pd.Series, b: pd.Series, n: int):
    return a.rolling(n).cov(b)