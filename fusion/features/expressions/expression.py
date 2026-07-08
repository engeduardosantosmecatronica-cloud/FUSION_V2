import re
from fusion.features.expressions.registry import OPERATORS


class ExpressionEngine:

    def __init__(self, df):
        self.df = df

    def _replace_fields(self, expr: str):
        def repl(match):
            col = match.group(1)
            if col == "df":
                return "self.df"
            return f'self.df["{col}"]'

        return re.sub(r"\$([a-zA-Z_][a-zA-Z0-9_]*)", repl, expr)

    def compute_expression(self, expr: str):
        expr = self._replace_fields(expr)

        context = {
            **OPERATORS,
            "self": self,
        }

        return eval(expr, {"__builtins__": {}}, context)