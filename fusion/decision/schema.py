from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class SignalCandidate:
    symbol: str
    broker_symbol: str
    timeframe: str
    side: str
    strategy: str
    raw_prediction: int
    p_buy: float = 0.0
    p_sell: float = 0.0
    model_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def direction_score(self) -> float:
        if self.side.upper() == "BUY":
            return float(self.p_buy)
        if self.side.upper() == "SELL":
            return float(self.p_sell)
        return 0.0


@dataclass
class EngineOutput:
    engine: str
    direction: str = "NEUTRAL"
    score: float = 0.0
    confidence: float = 0.0
    state: str = ""
    positive_factors: list[str] = field(default_factory=list)
    negative_factors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    features: dict[str, Any] = field(default_factory=dict)

    def aligned_with(self, side: str) -> bool:
        direction = self.direction.upper()
        side = side.upper()
        return direction == side

    def conflicts_with(self, side: str) -> bool:
        direction = self.direction.upper()
        side = side.upper()
        return direction in {"BUY", "SELL"} and direction != side


@dataclass
class DecisionResult:
    decision: str
    reason: str
    consensus_score: float
    conflict_score: float
    tradeability_score: float
    position_multiplier: float = 1.0
    positive_factors: list[str] = field(default_factory=list)
    negative_factors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class DecisionEvent:
    candidate: SignalCandidate
    result: DecisionResult
    engines: list[EngineOutput] = field(default_factory=list)
    account: dict[str, Any] = field(default_factory=dict)
    portfolio: dict[str, Any] = field(default_factory=dict)
    explanation: dict[str, Any] = field(default_factory=dict)
    correlation_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    version: str = "decision_event_v2"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
