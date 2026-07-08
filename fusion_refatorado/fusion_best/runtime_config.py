from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


BUY = 1
SELL = -1
HOLD = 0


@dataclass(frozen=True)
class AssetRuntimeConfig:
    point: float = 0.00001
    spread: float = 0.00016
    digits: int = 5


@dataclass(frozen=True)
class RuntimeConfig:
    mode: str = "BACKTEST"
    timezone: str = "America/Sao_Paulo"
    refresh_seconds: int = 10
    n_candles: int = 1200
    target_symbols: tuple[str, ...] = (
        "EURUSD",
        "GOLD",
        "GBPCAD",
        "GBPAUD",
        "GBPJPY",
        "NZDJPY",
        "EURCAD",
        "AUDCHF",
        "USDCAD",
        "NZDUSD",
        "USDJPY",
        "USDCHF",
        "AUDUSD",
        "GBPUSD",
    )
    timeframe_weights: dict[str, float] = field(
        default_factory=lambda: {"D1": 0.15, "H4": 0.20, "H1": 0.30, "M15": 0.25, "M5": 0.10}
    )
    confidence_min: float = 0.55
    risk_per_trade: float = 0.01
    max_daily_risk: float = 0.02
    min_rr: float = 1.5
    default_winrate: float = 0.52
    min_lot: float = 0.01
    max_lot: float = 0.02
    max_positions_total: int = 14
    max_positions_same_direction: int = 7
    cooldown_seconds: int = 60
    opposite_cooldown_seconds: int = 300
    trailing_mode: str = "DINAMICO"
    anti_spam_percent: float = 0.1
    m15_slope_threshold: float = 0.001
    risk_veto_threshold: float = 70.0
    price_filter_min_orders: int = 3
    deviation: int = 30
    magic_number: int = 777777
    order_comment: str = "Fusion_AI"
    backtest_start: datetime = datetime(2024, 1, 1)
    backtest_end: datetime = datetime(2025, 2, 18)
    telegram_enabled: bool = False
    telegram_token_env: str = "FUSION_TELEGRAM_TOKEN"
    telegram_chat_id_env: str = "FUSION_TELEGRAM_CHAT_ID"

    @property
    def telegram_token(self) -> str | None:
        return os.getenv(self.telegram_token_env)

    @property
    def telegram_chat_id(self) -> str | None:
        return os.getenv(self.telegram_chat_id_env)


ASSET_CONFIG: dict[str, AssetRuntimeConfig] = {
    "EURUSD": AssetRuntimeConfig(point=0.00001, spread=0.00016, digits=5),
    "GBPUSD": AssetRuntimeConfig(point=0.00001, spread=0.00018, digits=5),
    "GOLD": AssetRuntimeConfig(point=0.01, spread=0.30, digits=2),
    "XAUUSD": AssetRuntimeConfig(point=0.01, spread=0.30, digits=2),
    "USDJPY": AssetRuntimeConfig(point=0.001, spread=0.018, digits=3),
    "BTCUSD": AssetRuntimeConfig(point=1.0, spread=15.0, digits=0),
    "ETHUSD": AssetRuntimeConfig(point=0.1, spread=1.5, digits=1),
}
ASSET_CONFIG_DEFAULT = AssetRuntimeConfig()

SL_TP_CONFIG: dict[str, dict[str, int]] = {
    "EURUSD": {"sl": 500, "tp": 1000},
    "GBPUSD": {"sl": 500, "tp": 1000},
    "USDJPY": {"sl": 50, "tp": 100},
    "AUDUSD": {"sl": 500, "tp": 1000},
    "USDCAD": {"sl": 500, "tp": 1000},
    "USDCHF": {"sl": 500, "tp": 1000},
    "NZDUSD": {"sl": 500, "tp": 1000},
    "XAUUSD": {"sl": 50, "tp": 100},
    "GOLD": {"sl": 50, "tp": 100},
    "BTCUSD": {"sl": 500, "tp": 1000},
    "ETHUSD": {"sl": 500, "tp": 1000},
    "SP500": {"sl": 500, "tp": 1000},
    "NAS100": {"sl": 500, "tp": 1000},
    "DAX40": {"sl": 500, "tp": 1000},
}
SL_TP_DEFAULT = {"sl": 500, "tp": 1000}

MIN_DISTANCE_CONFIG: dict[str, dict[str, int]] = {
    "EURUSD": {"BUY": 30, "SELL": 46},
    "GBPUSD": {"BUY": 30, "SELL": 46},
    "GOLD": {"BUY": 200, "SELL": 100},
    "XAUUSD": {"BUY": 30, "SELL": 46},
    "USDJPY": {"BUY": 30, "SELL": 46},
    "BTCUSD": {"BUY": 30, "SELL": 46},
    "ETHUSD": {"BUY": 30, "SELL": 46},
}
MIN_DISTANCE_DEFAULT = {"BUY": 30, "SELL": 46}

MIN_ALIGNMENT_DISTANCE = {
    "EURUSD": 20,
    "GBPUSD": 20,
    "GOLD": 5,
    "XAUUSD": 5,
    "USDJPY": 2,
    "BTCUSD": 100,
    "DEFAULT": 20,
}

TRAILING_FIXED = {
    "EURUSD": {"BUY": {"activation": 50, "distance": 30}, "SELL": {"activation": 66, "distance": 30}},
    "GBPUSD": {"BUY": {"activation": 100, "distance": 50}, "SELL": {"activation": 118, "distance": 68}},
    "GOLD": {"BUY": {"activation": 200, "distance": 150}, "SELL": {"activation": 200, "distance": 150}},
    "USDJPY": {"BUY": {"activation": 10, "distance": 5}, "SELL": {"activation": 28, "distance": 23}},
    "BTCUSD": {"BUY": {"activation": 500, "distance": 250}, "SELL": {"activation": 515, "distance": 265}},
}
TRAILING_FIXED_DEFAULT = {"BUY": {"activation": 50, "distance": 30}, "SELL": {"activation": 66, "distance": 46}}

ATR_FACTORS = {
    "EURUSD": {"start": 2.0, "step": 1.5, "lock": 0.8},
    "GBPUSD": {"start": 2.0, "step": 1.5, "lock": 0.8},
    "USDCAD": {"start": 2.0, "step": 1.5, "lock": 0.8},
    "AUDUSD": {"start": 2.0, "step": 1.5, "lock": 0.8},
    "NZDUSD": {"start": 2.0, "step": 1.5, "lock": 0.8},
    "USDCHF": {"start": 2.0, "step": 1.5, "lock": 0.8},
    "USDJPY": {"start": 1.8, "step": 1.2, "lock": 0.6},
    "EURJPY": {"start": 1.8, "step": 1.2, "lock": 0.6},
    "GBPJPY": {"start": 1.8, "step": 1.2, "lock": 0.6},
    "GOLD": {"start": 1.5, "step": 1.0, "lock": 0.5},
    "XAUUSD": {"start": 1.5, "step": 1.0, "lock": 0.5},
    "BTCUSD": {"start": 1.2, "step": 0.8, "lock": 0.4},
    "ETHUSD": {"start": 1.2, "step": 0.8, "lock": 0.4},
    "SP500": {"start": 1.8, "step": 1.2, "lock": 0.6},
    "NAS100": {"start": 1.8, "step": 1.2, "lock": 0.6},
    "DAX40": {"start": 1.8, "step": 1.2, "lock": 0.6},
}
ATR_FACTORS_DEFAULT = {"start": 2.5, "step": 1.5, "lock": 0.9}

SL_TP_ATR_FACTORS = {
    "EURUSD": {"sl_mult": 1.5, "tp_mult": 3.0},
    "GBPUSD": {"sl_mult": 1.5, "tp_mult": 3.0},
    "USDCAD": {"sl_mult": 1.5, "tp_mult": 3.0},
    "AUDUSD": {"sl_mult": 1.5, "tp_mult": 3.0},
    "NZDUSD": {"sl_mult": 1.5, "tp_mult": 3.0},
    "USDCHF": {"sl_mult": 1.5, "tp_mult": 3.0},
    "USDJPY": {"sl_mult": 1.2, "tp_mult": 2.4},
    "EURJPY": {"sl_mult": 1.2, "tp_mult": 2.4},
    "GBPJPY": {"sl_mult": 1.2, "tp_mult": 2.4},
    "GOLD": {"sl_mult": 1.0, "tp_mult": 2.0},
    "XAUUSD": {"sl_mult": 1.0, "tp_mult": 2.0},
    "BTCUSD": {"sl_mult": 0.8, "tp_mult": 1.6},
    "ETHUSD": {"sl_mult": 0.8, "tp_mult": 1.6},
    "SP500": {"sl_mult": 1.2, "tp_mult": 2.4},
    "NAS100": {"sl_mult": 1.2, "tp_mult": 2.4},
    "DAX40": {"sl_mult": 1.2, "tp_mult": 2.4},
}
SL_TP_ATR_FACTORS_DEFAULT = {"sl_mult": 1.5, "tp_mult": 3.0}

FIBO_LEVELS = (0.236, 0.382, 0.500, 0.618, 0.786)
FIBO_WEIGHTS = {"0.236": 0.5, "0.382": 0.8, "0.500": 1.0, "0.618": 1.0, "0.786": 0.6}
INSIDEBAR_CONFIG: dict[str, Any] = {
    "enabled": True,
    "level": 2,
    "timeframe": "M15",
    "min_strength": 0.5,
    "buffer_points": 5,
    "confidence_boost": 0.3,
    "trigger_strength": 0.8,
    "block_counter_trend": True,
}
VOLATILITY_MULTIPLIERS = {2: 0.5, 1: 1.2, 0: 1.5}

MODEL_PATHS = {
    "trend": "models/trained/trend_model.pkl",
    "sr": "models/trained/sr_model.pkl",
    "orderflow": "models/trained/orderflow_model.pkl",
    "candles": "models/trained/candles_model.pkl",
    "volatility": "models/trained/volatility_model.pkl",
    "risk": "models/trained/risk_model.pkl",
    "reversal": "models/trained/reversal_model.pkl",
}


def _symbol_key(symbol: str) -> str:
    return symbol.upper().strip()


def get_asset_config(symbol: str) -> AssetRuntimeConfig:
    return ASSET_CONFIG.get(_symbol_key(symbol), ASSET_CONFIG_DEFAULT)


def get_sl_tp_config(symbol: str) -> dict[str, int]:
    return dict(SL_TP_CONFIG.get(_symbol_key(symbol), SL_TP_DEFAULT))


def get_min_distance(symbol: str) -> dict[str, int]:
    return dict(MIN_DISTANCE_CONFIG.get(_symbol_key(symbol), MIN_DISTANCE_DEFAULT))


def get_min_alignment_distance(symbol: str) -> int:
    return int(MIN_ALIGNMENT_DISTANCE.get(_symbol_key(symbol), MIN_ALIGNMENT_DISTANCE["DEFAULT"]))


def get_trailing_fixed(symbol: str) -> dict[str, dict[str, int]]:
    cfg = TRAILING_FIXED.get(_symbol_key(symbol), TRAILING_FIXED_DEFAULT)
    return {side: dict(values) for side, values in cfg.items()}


def get_atr_factors(symbol: str) -> dict[str, float]:
    return dict(ATR_FACTORS.get(_symbol_key(symbol), ATR_FACTORS_DEFAULT))


def get_sl_tp_atr_factors(symbol: str) -> dict[str, float]:
    return dict(SL_TP_ATR_FACTORS.get(_symbol_key(symbol), SL_TP_ATR_FACTORS_DEFAULT))

