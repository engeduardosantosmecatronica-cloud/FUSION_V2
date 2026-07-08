import pandas as pd


class FeatureBuilder:

    def __init__(self, engine):
        self.engine = engine

    def build(self, features: dict):
        df = self.engine.df.copy()
        new_cols = {}

        for name, expr in features.items():
            self.engine.df = pd.concat(
                [df, pd.DataFrame(new_cols)],
                axis=1
            )

            new_cols[name] = self.engine.compute_expression(expr)

        df = pd.concat([df, pd.DataFrame(new_cols)], axis=1)

        return df.copy()