import numpy as np
import pandas as pd


def Log(series: pd.Series):
    return np.log(series)


def Abs(series: pd.Series):
    return np.abs(series)


def Sign(series: pd.Series):
    return np.sign(series)