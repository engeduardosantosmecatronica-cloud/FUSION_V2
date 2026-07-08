from fusion.features.expressions.operators.reference import Ref, Delta
from fusion.features.expressions.operators.rolling import Mean, Std, Max, Min, Sum
from fusion.features.expressions.operators.statistics import Corr, Cov
from fusion.features.expressions.operators.ranking import Rank, TsRank
from fusion.features.expressions.operators.transforms import Log, Abs, Sign
from fusion.features.expressions.operators.advanced import EWM, RSI, ATR, AlphaVAM, AlphaEffort, AlphaMRS, AlphaRSIGap, TrendAlignment


OPERATORS = {
    "Ref": Ref,
    "Delta": Delta,
    "Mean": Mean,
    "Std": Std,
    "Max": Max,
    "Min": Min,
    "Sum": Sum,
    "Corr": Corr,
    "Cov": Cov,
    "Rank": Rank,
    "TsRank": TsRank,
    "Log": Log,
    "Abs": Abs,
    "Sign": Sign,
    "EWM": EWM,
    "RSI": RSI,
    "ATR": ATR,
    "AlphaVAM": AlphaVAM,
    "AlphaEffort": AlphaEffort,
    "AlphaMRS": AlphaMRS,
    "AlphaRSIGap": AlphaRSIGap,
    "TrendAlignment": TrendAlignment,
}