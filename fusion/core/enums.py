from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    """Enum string compatível com JSON e comparações simples."""

    def __str__(self) -> str:
        return self.value


class FusionEventType(StrEnum):
    SIGNAL = "SIGNAL"
    DECISION = "DECISION"
    ORDER_REQUEST = "ORDER_REQUEST"
    ORDER_RESULT = "ORDER_RESULT"
    POSITION_UPDATE = "POSITION_UPDATE"
    ACCOUNT_UPDATE = "ACCOUNT_UPDATE"
    TICK_UPDATE = "TICK_UPDATE"
    TRADE_UPDATE = "TRADE_UPDATE"
    RISK_ALERT = "RISK_ALERT"
    DASHBOARD_UPDATE = "DASHBOARD_UPDATE"
    AUDIT_RECORD = "AUDIT_RECORD"
    ADVISOR_REQUEST = "ADVISOR_REQUEST"
    ADVISOR_RESPONSE = "ADVISOR_RESPONSE"
    ENGINE_RESULT = "ENGINE_RESULT"


class OrderStatus(StrEnum):
    PENDING = "PENDING"
    SENT = "SENT"
    FILLED = "FILLED"
    PART_FILLED = "PART_FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class TradeDirection(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    NEUTRAL = "NEUTRAL"


class DecisionAction(StrEnum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    SHADOW = "SHADOW"
    MODERATE = "MODERATE"
    REDUCE_SIZE = "REDUCE_SIZE"


class AssetType(StrEnum):
    FOREX = "forex"
    METAL = "metal"
    INDEX = "index"
    CRYPTO = "crypto"
    CFD = "cfd"
    UNKNOWN = "unknown"
