from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fusion.decision.schema import EngineOutput
from fusion.features.macro_flow import split_forex_symbol


@dataclass
class PortfolioExposureConfig:
    max_currency_exposure: float = 3.0
    max_projected_currency_exposure: float = 4.0
    max_cluster_exposure: float = 5.0
    warning_cluster_exposure: float = 3.0
    correlation_threshold: float = 0.70
    max_symbol_positions: int = 1
    warning_currency_exposure: float = 2.0
    max_gross_exposure: float = 12.0
    warning_gross_exposure: float = 8.0
    max_losing_currency_exposure: float = 3.0
    include_negative_profit_focus: bool = True


class PortfolioExposureEngine:
    name = "portfolio_exposure"

    def __init__(self, config: PortfolioExposureConfig | None = None):
        self.config = config or PortfolioExposureConfig()

    @staticmethod
    def _pair_legs(symbol: str) -> tuple[str, str] | None:
        symbol = str(symbol or "").upper()
        if symbol in {"GOLD", "XAUUSD"}:
            return ("XAU", "USD")
        return split_forex_symbol(symbol)

    @staticmethod
    def _position_direction(position: dict[str, Any]) -> int:
        direction = str(position.get("direction", "")).upper()
        if direction == "BUY":
            return 1
        if direction == "SELL":
            return -1
        raw_type = position.get("type")
        try:
            return 1 if int(raw_type) == 0 else -1
        except (TypeError, ValueError):
            return 0

    def _apply_symbol_exposure(self, exposures: dict[str, float], symbol: str, direction: int, units: float) -> None:
        legs = self._pair_legs(symbol)
        if not legs or direction == 0:
            return
        base, quote = legs
        exposures[base] = exposures.get(base, 0.0) + (direction * units)
        exposures[quote] = exposures.get(quote, 0.0) - (direction * units)

    def evaluate(
        self,
        candidate_symbol: str,
        candidate_side: str,
        positions: list[dict[str, Any]],
        candidate_units: float = 1.0,
        correlation_matrix: dict[str, dict[str, float]] | None = None,
    ) -> EngineOutput:
        cfg = self.config
        candidate_symbol = str(candidate_symbol or "").upper()
        candidate_side = str(candidate_side or "").upper()
        candidate_direction = 1 if candidate_side == "BUY" else -1 if candidate_side == "SELL" else 0

        exposures: dict[str, float] = {}
        losing_exposures: dict[str, float] = {}
        symbol_counts: dict[str, int] = {}
        losing_positions: list[dict[str, Any]] = []
        correlated_cluster: list[dict[str, Any]] = []
        cluster_units = max(0.01, candidate_units)
        gross_exposure = 0.0

        for position in positions:
            symbol = str(position.get("symbol", "") or "").upper()
            direction = self._position_direction(position)
            volume = float(position.get("volume", 1.0) or 1.0)
            units = max(0.01, volume / 0.01)
            gross_exposure += units
            symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
            self._apply_symbol_exposure(exposures, symbol, direction, units)
            profit = float(position.get("profit", 0.0) or 0.0)
            if profit < 0:
                self._apply_symbol_exposure(losing_exposures, symbol, direction, units)
                losing_positions.append(
                    {
                        "symbol": symbol,
                        "direction": "BUY" if direction == 1 else "SELL" if direction == -1 else "NEUTRAL",
                        "profit": profit,
                        "units": units,
                    }
                )
            corr = self._matrix_corr(correlation_matrix or {}, candidate_symbol, symbol)
            if corr is not None and abs(corr) >= cfg.correlation_threshold:
                correlated_cluster.append(
                    {
                        "symbol": symbol,
                        "direction": "BUY" if direction == 1 else "SELL" if direction == -1 else "NEUTRAL",
                        "profit": profit,
                        "units": units,
                        "correlation": corr,
                    }
                )
                cluster_units += units

        projected = dict(exposures)
        self._apply_symbol_exposure(projected, candidate_symbol, candidate_direction, max(0.01, candidate_units))

        max_current = max((abs(value) for value in exposures.values()), default=0.0)
        max_projected = max((abs(value) for value in projected.values()), default=0.0)
        max_losing_currency = max((abs(value) for value in losing_exposures.values()), default=0.0)
        projected_gross_exposure = gross_exposure + max(0.01, candidate_units)
        candidate_count = symbol_counts.get(candidate_symbol, 0)
        positive: list[str] = []
        negative: list[str] = []
        warnings: list[str] = []

        state = "ok"
        score = 1.0
        confidence = 0.75

        if candidate_count >= cfg.max_symbol_positions:
            state = "symbol_concentration"
            negative.append(f"simbolo_ja_exposto:{candidate_symbol}:{candidate_count}")
            score -= 0.35

        overloaded = [
            f"{currency}:{value:.2f}"
            for currency, value in sorted(projected.items())
            if abs(value) > cfg.max_projected_currency_exposure
        ]
        warning_overloaded = [
            f"{currency}:{value:.2f}"
            for currency, value in sorted(projected.items())
            if abs(value) > cfg.warning_currency_exposure
        ]
        if overloaded:
            state = "currency_overexposure"
            negative.extend(f"exposicao_excessiva:{item}" for item in overloaded)
            score -= 0.45
        elif warning_overloaded:
            state = "currency_warning"
            warnings.extend(f"exposicao_alta:{item}" for item in warning_overloaded)
            score -= 0.15

        if projected_gross_exposure > cfg.max_gross_exposure:
            state = "gross_overexposure"
            negative.append(f"gross_exposure:{projected_gross_exposure:.2f}")
            score -= 0.25
        elif projected_gross_exposure > cfg.warning_gross_exposure:
            if state == "ok":
                state = "gross_warning"
            warnings.append(f"gross_exposure_alta:{projected_gross_exposure:.2f}")
            score -= 0.10

        if cluster_units > cfg.max_cluster_exposure:
            state = "cluster_overexposure"
            negative.append(f"cluster_correlacionado:{cluster_units:.2f}")
            score -= 0.30
        elif cluster_units > cfg.warning_cluster_exposure:
            if state == "ok":
                state = "cluster_warning"
            warnings.append(f"cluster_correlacionado_alto:{cluster_units:.2f}")
            score -= 0.12

        if max_losing_currency > cfg.max_losing_currency_exposure:
            state = "losing_currency_overexposure"
            negative.append(f"exposicao_perdedora_moeda:{max_losing_currency:.2f}")
            score -= 0.25

        if cfg.include_negative_profit_focus and losing_positions:
            warnings.append(f"posicoes_negativas:{len(losing_positions)}")
            score -= min(0.20, 0.05 * len(losing_positions))

        if not negative:
            positive.append("exposicao_portfolio_ok")

        score = max(0.0, min(1.0, score))
        direction = "NEUTRAL"
        if negative and candidate_side in {"BUY", "SELL"}:
            direction = "SELL" if candidate_side == "BUY" else "BUY"

        return EngineOutput(
            engine=self.name,
            direction=direction,
            score=score,
            confidence=confidence,
            state=state,
            positive_factors=positive,
            negative_factors=negative,
            warnings=warnings,
            features={
                "currency_exposure": exposures,
                "projected_currency_exposure": projected,
                "losing_currency_exposure": losing_exposures,
                "max_current_exposure": max_current,
                "max_projected_exposure": max_projected,
                "max_losing_currency_exposure": max_losing_currency,
                "gross_exposure": gross_exposure,
                "projected_gross_exposure": projected_gross_exposure,
                "correlated_cluster_units": cluster_units,
                "correlated_cluster": correlated_cluster[:12],
                "symbol_counts": symbol_counts,
                "losing_positions": losing_positions[:10],
            },
        )

    @staticmethod
    def _matrix_corr(matrix: dict[str, dict[str, float]], symbol_a: str, symbol_b: str) -> float | None:
        symbol_a = str(symbol_a or "").upper()
        symbol_b = str(symbol_b or "").upper()
        if not symbol_a or not symbol_b:
            return None
        if symbol_a == symbol_b:
            return 1.0
        row = matrix.get(symbol_a, {})
        if symbol_b in row:
            try:
                return float(row[symbol_b])
            except (TypeError, ValueError):
                return None
        row = matrix.get(symbol_b, {})
        if symbol_a in row:
            try:
                return float(row[symbol_a])
            except (TypeError, ValueError):
                return None
        return None
