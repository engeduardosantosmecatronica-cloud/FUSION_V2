from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import json
from pathlib import Path
from typing import Any

from fusion.decision.schema import EngineOutput, SignalCandidate
from fusion.features.currency_strength import split_symbol_components


@dataclass
class MarketBriefingConfig:
    briefing_path: str = "config/market_briefing_today.json"
    min_risk_to_block: str = "EXTREMO"
    apply_expired_as_shadow: bool = True
    min_bias_strength: float = 0.35


RISK_RANK = {
    "LOW": 1,
    "BAIXO": 1,
    "MEDIUM": 2,
    "MEDIO": 2,
    "MÉDIO": 2,
    "ALTO": 3,
    "HIGH": 3,
    "MUITO_ALTO": 4,
    "MUITO ALTO": 4,
    "EXTREMO": 5,
    "EXTREME": 5,
}


class MarketBriefingEngine:
    name = "market_briefing"

    def __init__(self, config: MarketBriefingConfig | None = None):
        self.config = config or MarketBriefingConfig()

    @staticmethod
    def _risk_rank(value: str) -> int:
        return RISK_RANK.get(str(value or "").upper().replace("-", "_"), 0)

    @staticmethod
    def _symbol_aliases(symbol: str) -> set[str]:
        symbol = str(symbol or "").upper()
        aliases = {symbol}
        if symbol == "GOLD":
            aliases.add("XAUUSD")
        if symbol == "XAUUSD":
            aliases.add("GOLD")
        return aliases

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _list(value: Any) -> list:
        if value is None:
            return []
        return value if isinstance(value, list) else [value]

    @staticmethod
    def _bias_score(value: Any) -> float:
        if isinstance(value, dict):
            raw_bias = str(value.get("bias", value.get("direction", "")) or "").upper()
            strength = float(value.get("strength", value.get("confidence", 0.65)) or 0.65)
        else:
            raw_bias = str(value or "").upper()
            strength = 0.65
        if raw_bias in {"BUY", "BULL", "BULLISH", "ALTA", "FORTE_BUY", "FORTE BUY"}:
            return abs(strength)
        if raw_bias in {"SELL", "BEAR", "BEARISH", "BAIXA", "FORTE_SELL", "FORTE SELL"}:
            return -abs(strength)
        return 0.0

    @staticmethod
    def _bias_drivers(value: Any) -> list[str]:
        if not isinstance(value, dict):
            return []
        raw = value.get("drivers", value.get("reasons", []))
        if raw is None:
            return []
        values = raw if isinstance(raw, list) else [raw]
        return [str(item) for item in values if str(item or "").strip()]

    def _pair_bias_score(self, briefing: dict[str, Any], candidate: SignalCandidate) -> tuple[float, list[str]]:
        symbol = candidate.symbol.upper()
        aliases = self._symbol_aliases(symbol)
        drivers: list[str] = []
        direct_maps = [
            briefing.get("pair_bias", {}) or {},
            briefing.get("asset_bias", {}) or {},
            briefing.get("symbol_bias", {}) or {},
        ]
        for bias_map in direct_maps:
            for alias in aliases:
                if alias in bias_map:
                    value = bias_map[alias]
                    drivers.extend(self._bias_drivers(value))
                    return self._bias_score(value), drivers

        parsed = split_symbol_components(symbol)
        if not parsed:
            return 0.0, drivers
        base, quote = parsed
        currency_bias = briefing.get("currency_bias", {}) or {}
        base_value = currency_bias.get(base, {})
        quote_value = currency_bias.get(quote, {})
        base_score = self._bias_score(base_value)
        quote_score = self._bias_score(quote_value)
        drivers.extend(f"{base}:{item}" for item in self._bias_drivers(base_value)[:3])
        drivers.extend(f"{quote}:{item}" for item in self._bias_drivers(quote_value)[:3])
        return base_score - quote_score, drivers

    def load_briefing(self) -> dict[str, Any]:
        path = Path(self.config.briefing_path)
        if not path.is_absolute():
            path = Path.cwd() / path
        return self._load_json(path)

    def _expired(self, briefing: dict[str, Any]) -> bool:
        valid_until = str(briefing.get("valid_until", "") or "")
        if not valid_until:
            return False
        try:
            return date.fromisoformat(valid_until[:10]) < datetime.now().date()
        except ValueError:
            return False

    def _setup_tags(self, candidate: SignalCandidate) -> set[str]:
        tags = {"market_order"}
        tf = candidate.timeframe.upper()
        strategy = candidate.strategy.lower()
        if tf in {"M1", "M5", "M15"}:
            tags.add("scalping")
        if strategy == "strategy4":
            tags.add("breakout")
        if strategy in {"strategy1", "strategy2", "strategy3", "strategy5"}:
            tags.add("continuation")
        return tags

    def _rule_applies(self, rule: dict[str, Any], candidate: SignalCandidate) -> bool:
        symbols = {str(item).upper() for item in self._list(rule.get("symbols"))}
        groups = {str(item).upper() for item in self._list(rule.get("groups"))}
        aliases = self._symbol_aliases(candidate.symbol)
        if symbols and not (symbols & aliases):
            return False
        if groups:
            if "GBP_CROSSES" in groups and not candidate.symbol.upper().startswith("GBP"):
                return False
            if "CHF_CROSSES" in groups and "CHF" not in candidate.symbol.upper():
                return False
            if "SGD_CROSSES" in groups and "SGD" not in candidate.symbol.upper():
                return False

        timeframes = {str(item).upper() for item in self._list(rule.get("timeframes"))}
        if timeframes and candidate.timeframe.upper() not in timeframes:
            return False
        strategies = {str(item).lower() for item in self._list(rule.get("strategies"))}
        if strategies and candidate.strategy.lower() not in strategies:
            return False
        sides = {str(item).upper() for item in self._list(rule.get("sides"))}
        if sides and candidate.side.upper() not in sides:
            return False
        avoid_setups = {str(item).lower() for item in self._list(rule.get("avoid_setups"))}
        if avoid_setups and not (avoid_setups & self._setup_tags(candidate)):
            return False
        return True

    def evaluate(self, candidate: SignalCandidate) -> EngineOutput:
        briefing = self.load_briefing()
        if not briefing or not bool(briefing.get("enabled", False)):
            return EngineOutput(
                engine=self.name,
                direction="NEUTRAL",
                score=0.80,
                confidence=0.20,
                state="no_briefing",
                warnings=["sem_briefing_ativo"],
            )

        expired = self._expired(briefing)
        rules = briefing.get("rules", []) or []
        matched = [rule for rule in rules if isinstance(rule, dict) and self._rule_applies(rule, candidate)]
        bias_score, bias_drivers = self._pair_bias_score(briefing, candidate)
        side = candidate.side.upper()
        side_sign = 1.0 if side == "BUY" else -1.0 if side == "SELL" else 0.0
        bias_alignment = bias_score * side_sign
        has_directional_bias = abs(bias_score) >= self.config.min_bias_strength and side_sign != 0.0

        if not matched and not has_directional_bias:
            return EngineOutput(
                engine=self.name,
                direction="NEUTRAL",
                score=0.85,
                confidence=0.60,
                state="ok",
                positive_factors=["sem_restricao_briefing"],
                warnings=["briefing_expirado"] if expired else [],
                features={"briefing_date": briefing.get("date"), "valid_until": briefing.get("valid_until")},
            )

        if matched:
            highest = max(matched, key=lambda item: self._risk_rank(str(item.get("risk", ""))))
        else:
            highest = {}
        action = str(highest.get("action", "moderate") or "moderate").lower()
        risk = str(highest.get("risk", "") or "")
        risk_rank = self._risk_rank(risk)
        block_rank = self._risk_rank(self.config.min_risk_to_block)
        should_block = action == "block" or (action != "allow" and risk_rank >= block_rank)
        if expired and self.config.apply_expired_as_shadow:
            should_block = False
            action = "shadow_expired"

        score = max(0.0, 1.0 - (risk_rank * 0.16)) if matched else min(0.95, abs(bias_score))
        factors = []
        for rule in matched[:5]:
            label = str(rule.get("label", "briefing_rule") or "briefing_rule")
            rule_risk = str(rule.get("risk", risk) or risk)
            factors.append(f"{label}:{rule_risk}")

        if has_directional_bias:
            expected_side = "BUY" if bias_score > 0 else "SELL"
            bias_factor = f"macro_bias:{expected_side}:score={bias_score:.2f}"
            if bias_drivers:
                bias_factor += ":" + "|".join(bias_drivers[:3])
            if bias_alignment >= self.config.min_bias_strength:
                return EngineOutput(
                    engine=self.name,
                    direction=side,
                    score=min(0.95, abs(bias_score)),
                    confidence=min(0.95, 0.45 + abs(bias_score) * 0.35),
                    state="macro_bias_aligned",
                    positive_factors=[bias_factor],
                    warnings=(["briefing_expirado"] if expired else []) + factors,
                    features={
                        "action": "support",
                        "bias_score": bias_score,
                        "expected_side": expected_side,
                        "briefing_date": briefing.get("date"),
                        "valid_until": briefing.get("valid_until"),
                        "summary": briefing.get("summary", ""),
                        "drivers": bias_drivers[:8],
                    },
                )
            if bias_alignment <= -self.config.min_bias_strength:
                return EngineOutput(
                    engine=self.name,
                    direction=expected_side,
                    score=max(0.0, 1.0 - min(0.80, abs(bias_score) * 0.25)),
                    confidence=min(0.95, 0.45 + abs(bias_score) * 0.35),
                    state="macro_bias_conflict",
                    negative_factors=[bias_factor] if not expired else [],
                    warnings=(["briefing_expirado"] if expired else [bias_factor]) + factors,
                    features={
                        "action": "conflict",
                        "bias_score": bias_score,
                        "expected_side": expected_side,
                        "briefing_date": briefing.get("date"),
                        "valid_until": briefing.get("valid_until"),
                        "summary": briefing.get("summary", ""),
                        "drivers": bias_drivers[:8],
                    },
                )

        direction = "SELL" if side == "BUY" else "BUY" if side == "SELL" else "NEUTRAL"
        return EngineOutput(
            engine=self.name,
            direction=direction if should_block else "NEUTRAL",
            score=score,
            confidence=min(0.95, 0.55 + (risk_rank * 0.08)),
            state="block" if should_block else "moderate",
            negative_factors=factors if should_block else [],
            warnings=[] if should_block else factors,
            features={
                "action": action,
                "risk": risk,
                "risk_rank": risk_rank,
                "matched_rules": matched[:5],
                "briefing_date": briefing.get("date"),
                "valid_until": briefing.get("valid_until"),
                "summary": briefing.get("summary", ""),
            },
        )
