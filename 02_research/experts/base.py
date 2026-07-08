from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


Bias = Literal["buy", "sell", "neutral", "avoid"]
Status = Literal["ok", "insufficient_data", "error"]


@dataclass
class ExpertOutput:
    status: Status = "ok"
    bias: Bias = "neutral"
    score: float = 0.0
    confidence: float = 0.0
    reason: str = ""
    features: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["score"] = clamp(data["score"], -1.0, 1.0)
        data["confidence"] = clamp(data["confidence"], 0.0, 1.0)
        return data


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, float(value)))


def direction_from_score(score: float, threshold: float = 0.2) -> Bias:
    if score >= threshold:
        return "buy"
    if score <= -threshold:
        return "sell"
    return "neutral"


def required(data: dict[str, Any], keys: list[str]) -> list[str]:
    return [key for key in keys if key not in data or data[key] is None]
