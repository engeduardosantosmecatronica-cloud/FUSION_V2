import numpy as np
import pandas as pd


def EWM(series: pd.Series, span: int):
    return series.ewm(span=span, adjust=False).mean()


def RSI(df: pd.DataFrame, period: int = 14):
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))


def ATR(df: pd.DataFrame, period: int = 14):
    high_low = df["high"] - df["low"]
    high_close = np.abs(df["high"] - df["close"].shift())
    low_close = np.abs(df["low"] - df["close"].shift())
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return true_range.rolling(period).mean()


def AlphaVAM(df: pd.DataFrame, period: int = 20):
    ret = np.log(df["close"] / df["close"].shift(1))
    range_pct = (df["high"] - df["low"]) / df["close"]
    return ret.rolling(period).mean() / (range_pct.rolling(period).std() + 1e-9)


def AlphaEffort(df: pd.DataFrame, period: int = 50):
    range_pct = (df["high"] - df["low"]) / df["close"]
    return range_pct / (range_pct.rolling(period).mean() + 1e-9)


def AlphaMRS(df: pd.DataFrame, period: int = 20):
    ema21 = df["close"].ewm(span=21).mean()
    dist_ema = (df["close"] / ema21) - 1
    range_pct = (df["high"] - df["low"]) / df["close"]
    return dist_ema / (range_pct.rolling(period).mean() + 1e-9)


def AlphaRSIGap(df: pd.DataFrame, period: int = 14):
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / (loss + 1e-9)
    rsi = 100 - (100 / (1 + rs))
    return rsi - rsi.rolling(10).mean()


def TrendAlignment(df: pd.DataFrame):
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 1e-9)
    rsi14 = 100 - (100 / (1 + rs))

    result = (rsi14 > 50).astype(int)
    for period in [5, 10, 20]:
        ma = df["close"].rolling(period).mean()
        result = result + (df["close"] > ma).astype(int)
    return result
