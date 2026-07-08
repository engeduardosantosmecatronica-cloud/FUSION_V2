from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Any

import numpy as np
import pandas as pd


class SignalSide(IntEnum):
    STRONG_SELL = -2
    SELL = -1
    HOLD = 0
    BUY = 1
    STRONG_BUY = 2


@dataclass
class TradingSignal:
    symbol: str
    timeframe: str
    timestamp: datetime | pd.Timestamp | None
    side: SignalSide
    confidence: float
    price: float
    source: str
    components: dict[str, Any] = field(default_factory=dict)
    stop_loss: float | None = None
    take_profit: float | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["side"] = self.side.name
        data["side_value"] = int(self.side)
        if self.timestamp is not None:
            data["timestamp"] = pd.Timestamp(self.timestamp).isoformat()
        return data


def signal_from_probabilities(
    symbol: str,
    timeframe: str,
    price: float,
    p_buy: float,
    p_sell: float,
    buy_threshold: float = 0.55,
    sell_threshold: float = 0.55,
    strong_margin: float = 0.12,
    source: str = "model",
    timestamp: datetime | pd.Timestamp | None = None,
) -> TradingSignal:
    if p_buy >= buy_threshold and p_buy >= p_sell:
        side = SignalSide.STRONG_BUY if p_buy >= buy_threshold + strong_margin else SignalSide.BUY
        confidence = p_buy
    elif p_sell >= sell_threshold and p_sell > p_buy:
        side = SignalSide.STRONG_SELL if p_sell >= sell_threshold + strong_margin else SignalSide.SELL
        confidence = p_sell
    else:
        side = SignalSide.HOLD
        confidence = max(1.0 - max(p_buy, p_sell), 0.0)
    return TradingSignal(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=timestamp,
        side=side,
        confidence=float(np.clip(confidence, 0.0, 1.0)),
        price=float(price),
        source=source,
        components={"p_buy": float(p_buy), "p_sell": float(p_sell)},
    )


def confluence_vote(signals: list[TradingSignal], min_confidence: float = 0.55) -> TradingSignal | None:
    valid = [s for s in signals if s.confidence >= min_confidence]
    if not valid:
        return None
    score = sum(int(s.side) * s.confidence for s in valid) / max(sum(s.confidence for s in valid), 1e-12)
    confidence = min(abs(score), 1.0)
    if score > 1.25:
        side = SignalSide.STRONG_BUY
    elif score > 0.25:
        side = SignalSide.BUY
    elif score < -1.25:
        side = SignalSide.STRONG_SELL
    elif score < -0.25:
        side = SignalSide.SELL
    else:
        side = SignalSide.HOLD
    last = valid[-1]
    return TradingSignal(
        symbol=last.symbol,
        timeframe=last.timeframe,
        timestamp=last.timestamp,
        side=side,
        confidence=confidence,
        price=last.price,
        source="confluence_vote",
        components={
            "score": float(score),
            "votes": [signal.to_dict() for signal in valid],
        },
    )
