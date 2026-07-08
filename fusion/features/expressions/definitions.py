import pandas as pd
from fusion.features.expressions.expression import ExpressionEngine
from fusion.features.expressions.feature_builder import FeatureBuilder
from fusion.features.expressions.operators.advanced import AlphaVAM, AlphaEffort, AlphaMRS, AlphaRSIGap, TrendAlignment


EXPRESSION_FEATURES = {
    "ret": "Log($close / Ref($close, 1))",
    "ret_5": "Sum(Log($close / Ref($close, 1)), 5)",
    "ret_10": "Sum(Log($close / Ref($close, 1)), 10)",
    "ret_20": "Sum(Log($close / Ref($close, 1)), 20)",

    "rsi14": "RSI($df, 14)",
    "rsi28": "RSI($df, 28)",
    "rsi_diff": "$rsi14 - $rsi28",
    "rsi_ma5": "Mean($rsi14, 5)",
    "rsi_gap": "$rsi14 - Mean($rsi14, 10)",

    "ema8": "EWM($close, 8)",
    "ema21": "EWM($close, 21)",
    "ema50": "EWM($close, 50)",
    "ema200": "EWM($close, 200)",

    "dist_ema8": "($close / $ema8) - 1",
    "dist_ema21": "($close / $ema21) - 1",
    "dist_ema50": "($close / $ema50) - 1",
    "dist_ema200": "($close / $ema200) - 1",

    "range_pct": "($high - $low) / $close",
    "range_ma10": "Mean(($high - $low) / $close, 10)",

    "high_20": "Max($high, 20)",
    "low_20": "Min($low, 20)",
    "position_in_range": "($close - $low_20) / ($high_20 - $low_20 + 1e-9)",

    "vol5": "Std(Log($close / Ref($close, 1)), 5)",
    "vol20": "Std(Log($close / Ref($close, 1)), 20)",
    "vol_ratio": "$vol5 / ($vol20 + 1e-9)",

    "macd": "EWM($close, 12) - EWM($close, 26)",
    "macd_signal": "EWM($macd, 9)",
    "macd_hist": "$macd - $macd_signal",

    "upper_bb": "$ema21 + (Std(Log($close / Ref($close, 1)), 20) * 2)",
    "lower_bb": "$ema21 - (Std(Log($close / Ref($close, 1)), 20) * 2)",
    "bb_width": "$upper_bb - $lower_bb",
}

CUSTOM_FEATURES = {
    "alpha_vam": lambda df: AlphaVAM(df, 20),
    "alpha_effort": lambda df: AlphaEffort(df, 50),
    "alpha_mrs": lambda df: AlphaMRS(df, 20),
    "alpha_rsi_gap": lambda df: AlphaRSIGap(df, 14),
    "trend_alignment": lambda df: TrendAlignment(df),
}


def build_expression_features(df: pd.DataFrame) -> pd.DataFrame:
    if len(df) < 100:
        return pd.DataFrame()

    engine = ExpressionEngine(df)
    builder = FeatureBuilder(engine)

    result = builder.build(EXPRESSION_FEATURES)

    for name, func in CUSTOM_FEATURES.items():
        engine.df = result
        result[name] = func(result)

    return result.dropna()
