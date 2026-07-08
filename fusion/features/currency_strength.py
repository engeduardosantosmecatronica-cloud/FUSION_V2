from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


KNOWN_ASSETS = {
    "AUD", "CAD", "CHF", "DKK", "EUR", "GBP", "HKD", "HUF", "JPY", "MXN",
    "NOK", "NZD", "PLN", "SEK", "SGD", "TRY", "USD", "ZAR",
    "BTC", "DOG", "DOT", "ETH", "UNI", "XAG", "XAU",
}

ALIASES = {
    "GOLD": ("XAU", "USD"),
    "SILVER": ("XAG", "USD"),
}


@dataclass
class CurrencyStrengthConfig:
    timeframe_weights: dict[str, float] = field(
        default_factory=lambda: {
            "M5": 0.50,
            "M15": 0.80,
            "M30": 1.00,
            "H1": 1.30,
            "H4": 1.60,
            "D1": 1.20,
        }
    )
    wait_edge: float = 0.08
    min_confidence_weight: float = 0.20
    strong_pair_score: float = 4.0
    moderate_pair_score: float = 2.0


def split_symbol_components(symbol: str) -> tuple[str, str] | None:
    value = str(symbol or "").upper().replace("-", "").replace("_", "")
    if value in ALIASES:
        return ALIASES[value]
    if len(value) < 6:
        return None
    base = value[:3]
    quote = value[3:6]
    if base in KNOWN_ASSETS and quote in KNOWN_ASSETS:
        return base, quote
    return None


def direction_from_probs(signal: int, p_buy: Any, p_sell: Any, wait_edge: float) -> tuple[str, float]:
    try:
        buy = float(p_buy)
        sell = float(p_sell)
    except (TypeError, ValueError):
        return "NEUTRO", 0.0
    if buy == 0.0 and sell == 0.0:
        return "NEUTRO", 0.0
    edge = buy - sell
    if abs(edge) < wait_edge:
        return "NEUTRO", abs(edge)
    if int(signal or 0) == 1:
        return "BUY", max(abs(edge), buy)
    if int(signal or 0) == 2:
        return "SELL", max(abs(edge), sell)
    if edge > 0:
        return "BUY", abs(edge)
    if edge < 0:
        return "SELL", abs(edge)
    return "NEUTRO", 0.0


def build_currency_strength_map(
    monitor_state: dict[tuple[str, str], dict[str, Any]],
    config: CurrencyStrengthConfig | None = None,
) -> dict[str, Any]:
    cfg = config or CurrencyStrengthConfig()
    currency_scores: dict[str, float] = {}
    currency_votes: dict[str, int] = {}
    pair_scores: dict[str, dict[str, Any]] = {}

    for (symbol_raw, timeframe_raw), state in monitor_state.items():
        symbol = str(symbol_raw or "").upper()
        timeframe = str(timeframe_raw or "").upper()
        parsed = split_symbol_components(symbol)
        if not parsed:
            continue
        base, quote = parsed
        direction, confidence = direction_from_probs(
            int(state.get("signal", 0) or 0),
            state.get("p_buy"),
            state.get("p_sell"),
            cfg.wait_edge,
        )
        if direction == "NEUTRO":
            continue
        tf_weight = float(cfg.timeframe_weights.get(timeframe, 1.0) or 1.0)
        confidence_weight = max(cfg.min_confidence_weight, min(1.0, float(confidence or 0.0)))
        contribution = tf_weight * confidence_weight
        if direction == "SELL":
            contribution *= -1.0

        currency_scores[base] = currency_scores.get(base, 0.0) + contribution
        currency_scores[quote] = currency_scores.get(quote, 0.0) - contribution
        currency_votes[base] = currency_votes.get(base, 0) + 1
        currency_votes[quote] = currency_votes.get(quote, 0) + 1

        pair = pair_scores.setdefault(
            symbol,
            {
                "symbol": symbol,
                "base": base,
                "quote": quote,
                "raw_score": 0.0,
                "votes": 0,
                "timeframes": {},
            },
        )
        pair["raw_score"] += contribution
        pair["votes"] += 1
        pair["timeframes"][timeframe] = {
            "direction": direction,
            "confidence": confidence,
            "contribution": contribution,
        }

    for symbol, pair in pair_scores.items():
        base_score = float(currency_scores.get(pair["base"], 0.0))
        quote_score = float(currency_scores.get(pair["quote"], 0.0))
        pair_score = base_score - quote_score
        if pair_score >= cfg.strong_pair_score:
            classification = "FORTE BUY"
        elif pair_score >= cfg.moderate_pair_score:
            classification = "BUY"
        elif pair_score <= -cfg.strong_pair_score:
            classification = "FORTE SELL"
        elif pair_score <= -cfg.moderate_pair_score:
            classification = "SELL"
        else:
            classification = "NEUTRO"
        pair["base_score"] = base_score
        pair["quote_score"] = quote_score
        pair["pair_score"] = pair_score
        pair["classification"] = classification

    ranking = [
        {
            "currency": currency,
            "score": score,
            "votes": currency_votes.get(currency, 0),
        }
        for currency, score in sorted(currency_scores.items(), key=lambda item: item[1], reverse=True)
    ]
    return {
        "currency_scores": currency_scores,
        "currency_votes": currency_votes,
        "ranking": ranking,
        "pair_scores": pair_scores,
    }
