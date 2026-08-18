from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fusion.decision.schema import EngineOutput, SignalCandidate


@dataclass
class RiskConfig:
    max_drawdown_pct: float = 8.0
    warning_drawdown_pct: float = 4.0
    max_floating_loss_pct: float = 5.0
    warning_floating_loss_pct: float = 2.5
    max_open_positions: int = 12
    max_losing_positions: int = 6
    min_margin_level_pct: float = 250.0
    warning_margin_level_pct: float = 400.0
    max_margin_usage_pct: float = 35.0
    warning_margin_usage_pct: float = 25.0
    max_currency_risk_units: float = 5.0
    warning_currency_risk_units: float = 3.0
    max_symbol_positions: int = 1
    max_same_direction_positions: int = 4
    high_conflict_threshold: float = 0.35
    moderate_conflict_threshold: float = 0.22
    low_opportunity_threshold: float = 0.45
    low_feature_quality_threshold: float = 0.55
    min_multiplier: float = 0.25
    volatility_risk_states: tuple[str, ...] = ("PANIC_VOLATILITY", "EXPANSION")


class RiskEngine:
    name = "risk_engine"

    def __init__(self, config: RiskConfig | None = None):
        self.config = config or RiskConfig()

    @staticmethod
    def _float(value: Any, default: float = 0.0) -> float:
        try:
            value = float(value)
        except (TypeError, ValueError):
            return default
        return value

    @staticmethod
    def _engine_by_name(engines: list[EngineOutput]) -> dict[str, EngineOutput]:
        result: dict[str, EngineOutput] = {}
        for engine in engines:
            result[engine.engine] = engine
        return result

    @staticmethod
    def _split_symbol(symbol: str) -> tuple[str, str]:
        symbol = str(symbol or "").upper().replace("/", "")
        if symbol in {"GOLD", "gold"}:
            return "XAU", "USD"
        if len(symbol) >= 6:
            return symbol[:3], symbol[3:6]
        return symbol[:3], ""

    @staticmethod
    def _position_units(direction: str, volume: float) -> float:
        direction = str(direction or "").upper()
        if direction == "BUY":
            return float(volume or 0.0)
        if direction == "SELL":
            return -float(volume or 0.0)
        return 0.0

    def _currency_exposure(self, positions: list[dict[str, Any]]) -> dict[str, float]:
        exposure: dict[str, float] = {}
        for pos in positions:
            base, quote = self._split_symbol(str(pos.get("symbol", "")))
            units = self._position_units(str(pos.get("direction", "")), self._float(pos.get("volume"), 0.0))
            if base:
                exposure[base] = exposure.get(base, 0.0) + units
            if quote:
                exposure[quote] = exposure.get(quote, 0.0) - units
        return exposure

    def evaluate(
        self,
        candidate: SignalCandidate,
        engines: list[EngineOutput],
        account: dict[str, Any] | None = None,
        positions: list[dict[str, Any]] | None = None,
    ) -> EngineOutput:
        cfg = self.config
        account = account or {}
        positions = positions or []
        by_name = self._engine_by_name(engines)

        balance = self._float(account.get("balance"), 0.0)
        equity = self._float(account.get("equity"), balance)
        floating = self._float(account.get("profit"), equity - balance if balance else 0.0)
        margin = self._float(account.get("margin"), 0.0)
        margin_free = self._float(account.get("margin_free"), 0.0)
        margin_level = self._float(account.get("margin_level"), 0.0)
        drawdown_pct = max(0.0, ((balance - equity) / balance) * 100.0) if balance > 0 else 0.0
        floating_loss_pct = max(0.0, (-floating / balance) * 100.0) if balance > 0 else 0.0
        margin_usage_pct = max(0.0, (margin / equity) * 100.0) if equity > 0 else 0.0
        open_positions = len(positions)
        losing_positions = sum(1 for pos in positions if self._float(pos.get("profit"), 0.0) < 0)
        same_symbol_positions = sum(1 for pos in positions if str(pos.get("symbol", "")).upper() == candidate.symbol.upper())
        same_direction_positions = sum(1 for pos in positions if str(pos.get("direction", "")).upper() == candidate.side.upper())
        currency_exposure = self._currency_exposure(positions)
        projected_exposure = dict(currency_exposure)
        base, quote = self._split_symbol(candidate.symbol)
        projected_units = 1.0 if candidate.side.upper() == "BUY" else -1.0 if candidate.side.upper() == "SELL" else 0.0
        if base:
            projected_exposure[base] = projected_exposure.get(base, 0.0) + projected_units
        if quote:
            projected_exposure[quote] = projected_exposure.get(quote, 0.0) - projected_units
        max_projected_currency_risk = max((abs(value) for value in projected_exposure.values()), default=0.0)

        conflict_score = 0.0
        for engine_name in ("opportunity_engine", "consensus_engine", "context_engine"):
            engine = by_name.get(engine_name)
            if engine:
                conflict_score = max(
                    conflict_score,
                    self._float(engine.features.get("conflict_score"), 0.0),
                    self._float(engine.features.get("context_conflict_score"), 0.0),
                )

        risk_score = 1.0
        multiplier = 1.0
        positive: list[str] = []
        negative: list[str] = []
        warnings: list[str] = []

        if drawdown_pct >= cfg.max_drawdown_pct:
            risk_score -= 0.35
            multiplier = min(multiplier, cfg.min_multiplier)
            negative.append(f"drawdown_critico:{drawdown_pct:.2f}%")
        elif drawdown_pct >= cfg.warning_drawdown_pct:
            risk_score -= 0.18
            multiplier = min(multiplier, 0.50)
            warnings.append(f"drawdown_alerta:{drawdown_pct:.2f}%")

        if floating_loss_pct >= cfg.max_floating_loss_pct:
            risk_score -= 0.30
            multiplier = min(multiplier, cfg.min_multiplier)
            negative.append(f"perda_flutuante_critica:{floating_loss_pct:.2f}%")
        elif floating_loss_pct >= cfg.warning_floating_loss_pct:
            risk_score -= 0.15
            multiplier = min(multiplier, 0.50)
            warnings.append(f"perda_flutuante_alerta:{floating_loss_pct:.2f}%")

        if margin_level and margin_level <= cfg.min_margin_level_pct:
            risk_score -= 0.30
            multiplier = min(multiplier, cfg.min_multiplier)
            negative.append(f"margin_level_critico:{margin_level:.1f}%")
        elif margin_level and margin_level <= cfg.warning_margin_level_pct:
            risk_score -= 0.12
            multiplier = min(multiplier, 0.70)
            warnings.append(f"margin_level_alerta:{margin_level:.1f}%")

        if margin_usage_pct >= cfg.max_margin_usage_pct:
            risk_score -= 0.22
            multiplier = min(multiplier, cfg.min_multiplier)
            negative.append(f"uso_margem_critico:{margin_usage_pct:.2f}%")
        elif margin_usage_pct >= cfg.warning_margin_usage_pct:
            risk_score -= 0.10
            multiplier = min(multiplier, 0.70)
            warnings.append(f"uso_margem_alerta:{margin_usage_pct:.2f}%")

        if open_positions >= cfg.max_open_positions:
            risk_score -= 0.18
            multiplier = min(multiplier, 0.50)
            negative.append(f"muitas_posicoes:{open_positions}")
        elif open_positions >= max(1, int(cfg.max_open_positions * 0.75)):
            risk_score -= 0.08
            multiplier = min(multiplier, 0.75)
            warnings.append(f"posicoes_elevadas:{open_positions}")

        # Treat negative (losing) positions as a warning rather than a hard negative factor.
        # This avoids direct blocking caused by existing losing positions while still
        # reflecting increased risk in warnings and modest score adjustments.
        if losing_positions >= cfg.max_losing_positions:
            risk_score -= 0.05
            multiplier = min(multiplier, 0.75)
            warnings.append(f"muitas_posicoes_negativas:{losing_positions}")
        elif losing_positions >= max(1, int(cfg.max_losing_positions * 0.70)):
            risk_score -= 0.03
            multiplier = min(multiplier, 0.85)
            warnings.append(f"posicoes_negativas_elevadas:{losing_positions}")

        if same_symbol_positions >= cfg.max_symbol_positions:
            risk_score -= 0.12
            multiplier = min(multiplier, 0.70)
            warnings.append(f"simbolo_ja_exposto:{candidate.symbol}:{same_symbol_positions}")

        if same_direction_positions >= cfg.max_same_direction_positions:
            risk_score -= 0.10
            multiplier = min(multiplier, 0.75)
            warnings.append(f"direcao_concentrada:{candidate.side}:{same_direction_positions}")

        if max_projected_currency_risk >= cfg.max_currency_risk_units:
            risk_score -= 0.20
            multiplier = min(multiplier, 0.50)
            negative.append(f"risco_moeda_excessivo:{max_projected_currency_risk:.2f}")
        elif max_projected_currency_risk >= cfg.warning_currency_risk_units:
            risk_score -= 0.08
            multiplier = min(multiplier, 0.75)
            warnings.append(f"risco_moeda_elevado:{max_projected_currency_risk:.2f}")

        portfolio = by_name.get("portfolio_exposure")
        if portfolio and portfolio.negative_factors:
            risk_score -= 0.12
            multiplier = min(multiplier, 0.75)
            warnings.extend(f"portfolio:{item}" for item in portfolio.negative_factors[:2])

        correlation = by_name.get("portfolio_correlation")
        if correlation and correlation.negative_factors:
            risk_score -= 0.16
            multiplier = min(multiplier, 0.50)
            negative.extend(f"correlacao:{item}" for item in correlation.negative_factors[:2])

        volatility = by_name.get("volatility_engine")
        if volatility and str(volatility.state).upper() in {item.upper() for item in cfg.volatility_risk_states}:
            if str(volatility.state).upper() == "PANIC_VOLATILITY":
                risk_score -= 0.18
                multiplier = min(multiplier, 0.50)
                negative.append("panic_volatility")
            else:
                risk_score -= 0.06
                multiplier = min(multiplier, 0.85)
                warnings.append(f"volatilidade_risco:{volatility.state}")

        session = by_name.get("session_context")
        if session and session.negative_factors:
            risk_score -= 0.10
            multiplier = min(multiplier, 0.75)
            warnings.extend(f"sessao:{item}" for item in session.negative_factors[:2])

        feature_quality = by_name.get("feature_engineering")
        if feature_quality and feature_quality.score < cfg.low_feature_quality_threshold:
            risk_score -= 0.10
            multiplier = min(multiplier, 0.75)
            warnings.append(f"feature_quality_baixa:{feature_quality.score:.2f}")

        opportunity = by_name.get("opportunity_engine")
        if opportunity and opportunity.score < cfg.low_opportunity_threshold:
            risk_score -= 0.12
            multiplier = min(multiplier, 0.70)
            warnings.append(f"oportunidade_fraca:{opportunity.score:.2f}")

        if conflict_score >= cfg.high_conflict_threshold:
            risk_score -= 0.18
            multiplier = min(multiplier, 0.50)
            negative.append(f"conflito_alto:{conflict_score:.2f}")
        elif conflict_score >= cfg.moderate_conflict_threshold:
            risk_score -= 0.08
            multiplier = min(multiplier, 0.75)
            warnings.append(f"conflito_moderado:{conflict_score:.2f}")

        risk_score = max(0.0, min(1.0, risk_score))
        multiplier = max(0.0, min(1.0, multiplier))

        state = "normal_risk"
        direction = candidate.side.upper()
        if risk_score < 0.35 or multiplier <= cfg.min_multiplier:
            state = "critical_risk"
            direction = "NEUTRAL"
        elif risk_score < 0.55 or negative:
            state = "high_risk"
            direction = "NEUTRAL"
        elif multiplier < 1.0 or warnings:
            state = "reduced_risk"

        if not negative and not warnings:
            positive.append("risco_operacional_normal")
        else:
            positive.append(f"multiplicador_sugerido:{multiplier:.2f}")

        return EngineOutput(
            engine=self.name,
            direction=direction,
            score=risk_score,
            confidence=0.80,
            state=state,
            positive_factors=positive,
            negative_factors=negative[:10],
            warnings=warnings[:10],
            features={
                "risk_score": risk_score,
                "position_multiplier_suggested": multiplier,
                "balance": balance,
                "equity": equity,
                "floating_profit": floating,
                "margin": margin,
                "margin_free": margin_free,
                "margin_level": margin_level,
                "margin_usage_pct": margin_usage_pct,
                "drawdown_pct": drawdown_pct,
                "floating_loss_pct": floating_loss_pct,
                "open_positions": open_positions,
                "losing_positions": losing_positions,
                "same_symbol_positions": same_symbol_positions,
                "same_direction_positions": same_direction_positions,
                "currency_exposure": currency_exposure,
                "projected_currency_exposure": projected_exposure,
                "max_projected_currency_risk": max_projected_currency_risk,
                "conflict_score": conflict_score,
            },
        )
