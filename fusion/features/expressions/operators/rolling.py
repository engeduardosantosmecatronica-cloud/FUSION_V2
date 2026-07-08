import pandas as pd


def Mean(series: pd.Series, n: int):
    return series.rolling(n).mean()


def Std(series: pd.Series, n: int):
    return series.rolling(n).std()


def Max(*args):
    # rolling max
    if len(args) == 2 and isinstance(args[1], int):
        return args[0].rolling(args[1]).max()

    # max entre múltiplas séries
    return pd.concat(args, axis=1).max(axis=1)


def Min(*args):
    # rolling min
    if len(args) == 2 and isinstance(args[1], int):
        return args[0].rolling(args[1]).min()

    # min entre múltiplas séries
    return pd.concat(args, axis=1).min(axis=1)


def Sum(series: pd.Series, n: int):
    return series.rolling(n).sum()