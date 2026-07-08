from fusion.features.expressions.registry import OPERATORS


class Executor:

    def __init__(self, df):
        self.df = df

    def compute(self, func, *args):
        operator = OPERATORS[func]
        return operator(*args)