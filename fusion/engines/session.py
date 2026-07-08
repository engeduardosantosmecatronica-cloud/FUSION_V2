from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from fusion.decision.schema import EngineOutput


@dataclass
class SessionConfig:
    low_liquidity_start_hour_utc: int = 21
    low_liquidity_end_hour_utc: int = 23
    asian_start_hour_utc: int = 0
    asian_end_hour_utc: int = 7
    london_start_hour_utc: int = 7
    london_end_hour_utc: int = 16
    new_york_start_hour_utc: int = 12
    new_york_end_hour_utc: int = 21
    london_open_risk_minutes: int = 20
    new_york_open_risk_minutes: int = 20
    transition_risk_minutes: int = 15
    friday_cutoff_hour_utc: int = 18
    scalping_timeframes: tuple[str, ...] = ("M5", "M15")
    asia_preferred_currencies: tuple[str, ...] = ("JPY", "AUD", "NZD", "SGD")
    london_preferred_currencies: tuple[str, ...] = ("EUR", "GBP", "CHF")
    new_york_preferred_currencies: tuple[str, ...] = ("USD", "CAD", "XAU")
    high_noise_symbols: tuple[str, ...] = ("XAUUSD", "GOLD", "GBPJPY", "GBPNZD", "AUDSGD", "NZDSGD")
    session_scores: dict[str, float] = field(
        default_factory=lambda: {
            "london_new_york_overlap": 0.90,
            "london": 0.82,
            "new_york": 0.80,
            "asia": 0.62,
            "off_session": 0.50,
            "rollover_low_liquidity": 0.30,
            "weekend": 0.10,
            "friday_close_risk": 0.25,
        }
    )


class SessionEngine:
    name = "session_context"

    def __init__(self, config: SessionConfig | None = None):
        self.config = config or SessionConfig()

    @staticmethod
    def _in_window(hour: int, start: int, end: int) -> bool:
        start = int(start) % 24
        end = int(end) % 24
        if start == end:
            return True
        if start < end:
            return start <= hour < end
        return hour >= start or hour < end

    @staticmethod
    def _minutes_from_start(now_utc: datetime, start_hour: int) -> int:
        start_hour = int(start_hour) % 24
        start = now_utc.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        diff = int((now_utc - start).total_seconds() // 60)
        if diff < -720:
            diff += 1440
        if diff > 720:
            diff -= 1440
        return diff

    @staticmethod
    def _symbol_currencies(symbol: str) -> tuple[str, str]:
        symbol = str(symbol or "").upper().replace("/", "")
        if symbol in {"GOLD", "XAUUSD"}:
            return "XAU", "USD"
        if len(symbol) >= 6:
            return symbol[:3], symbol[3:6]
        return symbol[:3], ""

    @staticmethod
    def _contains_any(currencies: tuple[str, str], preferred: tuple[str, ...]) -> bool:
        preferred_set = {item.upper() for item in preferred}
        return any(currency.upper() in preferred_set for currency in currencies if currency)

    def evaluate(
        self,
        now_utc: datetime | None = None,
        symbol: str = "",
        timeframe: str = "",
        side: str = "NEUTRAL",
    ) -> EngineOutput:
        cfg = self.config
        now_utc = now_utc or datetime.now(timezone.utc)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=timezone.utc)
        hour = int(now_utc.hour)
        weekday = int(now_utc.weekday())
        minute_of_day = hour * 60 + int(now_utc.minute)

        in_asia = self._in_window(hour, cfg.asian_start_hour_utc, cfg.asian_end_hour_utc)
        in_london = self._in_window(hour, cfg.london_start_hour_utc, cfg.london_end_hour_utc)
        in_new_york = self._in_window(hour, cfg.new_york_start_hour_utc, cfg.new_york_end_hour_utc)
        in_low_liquidity = self._in_window(hour, cfg.low_liquidity_start_hour_utc, cfg.low_liquidity_end_hour_utc)
        is_weekend = weekday >= 5
        is_friday_close_risk = weekday == 4 and hour >= int(cfg.friday_cutoff_hour_utc)
        minutes_from_london_open = self._minutes_from_start(now_utc, cfg.london_start_hour_utc)
        minutes_from_ny_open = self._minutes_from_start(now_utc, cfg.new_york_start_hour_utc)
        near_london_open = 0 <= minutes_from_london_open < int(cfg.london_open_risk_minutes)
        near_ny_open = 0 <= minutes_from_ny_open < int(cfg.new_york_open_risk_minutes)
        near_transition = any(
            abs(self._minutes_from_start(now_utc, boundary)) < int(cfg.transition_risk_minutes)
            for boundary in (
                cfg.asian_start_hour_utc,
                cfg.asian_end_hour_utc,
                cfg.london_start_hour_utc,
                cfg.london_end_hour_utc,
                cfg.new_york_start_hour_utc,
                cfg.new_york_end_hour_utc,
                cfg.low_liquidity_start_hour_utc,
                cfg.low_liquidity_end_hour_utc,
            )
        )
        symbol_upper = str(symbol or "").upper()
        tf = str(timeframe or "").upper()
        currencies = self._symbol_currencies(symbol_upper)
        is_scalping = tf in {item.upper() for item in cfg.scalping_timeframes}
        is_high_noise = symbol_upper in {item.upper() for item in cfg.high_noise_symbols}

        positive: list[str] = []
        negative: list[str] = []
        warnings: list[str] = []
        state = "off_session"
        score = float(cfg.session_scores.get("off_session", 0.50))
        confidence = 0.70

        if is_weekend:
            state = "weekend"
            score = float(cfg.session_scores.get(state, 0.10))
            negative.append("fim_de_semana")
        elif is_friday_close_risk:
            state = "friday_close_risk"
            score = float(cfg.session_scores.get(state, 0.25))
            negative.append("sexta_fechamento_risco")
        elif in_low_liquidity:
            state = "rollover_low_liquidity"
            score = float(cfg.session_scores.get(state, 0.30))
            negative.append("baixa_liquidez_rollover")
        elif in_london and in_new_york:
            state = "london_new_york_overlap"
            score = float(cfg.session_scores.get(state, 0.90))
            positive.append("overlap_london_ny")
        elif in_london:
            state = "london"
            score = float(cfg.session_scores.get(state, 0.82))
            positive.append("sessao_london")
        elif in_new_york:
            state = "new_york"
            score = float(cfg.session_scores.get(state, 0.80))
            positive.append("sessao_new_york")
        elif in_asia:
            state = "asia"
            score = float(cfg.session_scores.get(state, 0.62))
            warnings.append("sessao_asia")
        else:
            warnings.append("fora_sessoes_principais")

        session_fit = 0.50
        if state == "asia":
            session_fit = 0.75 if self._contains_any(currencies, cfg.asia_preferred_currencies) else 0.40
        elif state == "london":
            session_fit = 0.78 if self._contains_any(currencies, cfg.london_preferred_currencies) else 0.55
        elif state == "new_york":
            session_fit = 0.78 if self._contains_any(currencies, cfg.new_york_preferred_currencies) else 0.55
        elif state == "london_new_york_overlap":
            session_fit = 0.85 if self._contains_any(currencies, cfg.london_preferred_currencies + cfg.new_york_preferred_currencies) else 0.62

        if is_scalping and state in {"asia", "off_session"} and not self._contains_any(currencies, cfg.asia_preferred_currencies):
            warnings.append("scalping_fora_sessao_ideal")
            score *= 0.85
        if near_london_open:
            warnings.append("abertura_london_spread_volatilidade")
            score *= 0.92
        if near_ny_open:
            warnings.append("abertura_new_york_spread_volatilidade")
            score *= 0.92
        if near_transition:
            warnings.append("transicao_de_sessao")
            score *= 0.95
        if is_high_noise and is_scalping:
            warnings.append("ativo_ruidoso_para_scalping")
            score *= 0.90
        if session_fit < 0.50 and state not in {"weekend", "rollover_low_liquidity", "friday_close_risk"}:
            state = "weak_session_fit"
            warnings.append("ativo_fora_sessao_preferencial")
        score = max(0.0, min(1.0, (score * 0.75) + (session_fit * 0.25)))

        return EngineOutput(
            engine=self.name,
            direction="NEUTRAL",
            score=score,
            confidence=confidence,
            state=state,
            positive_factors=positive,
            negative_factors=negative,
            warnings=warnings,
            features={
                "utc_time": now_utc.isoformat(),
                "utc_hour": hour,
                "minute_of_day": minute_of_day,
                "weekday": weekday,
                "symbol": symbol_upper,
                "timeframe": tf,
                "side": str(side or "NEUTRAL").upper(),
                "base_currency": currencies[0],
                "quote_currency": currencies[1],
                "in_asia": in_asia,
                "in_london": in_london,
                "in_new_york": in_new_york,
                "in_low_liquidity": in_low_liquidity,
                "is_friday_close_risk": is_friday_close_risk,
                "minutes_from_london_open": minutes_from_london_open,
                "minutes_from_new_york_open": minutes_from_ny_open,
                "near_london_open": near_london_open,
                "near_new_york_open": near_ny_open,
                "near_transition": near_transition,
                "session_fit_score": session_fit,
                "is_scalping_timeframe": is_scalping,
                "is_high_noise_symbol": is_high_noise,
            },
        )
