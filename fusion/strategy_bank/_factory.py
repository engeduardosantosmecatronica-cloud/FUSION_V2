from __future__ import annotations

from copy import deepcopy
from pathlib import Path


MODEL_ROOT = Path("models_research")
TIMEFRAMES = ("M5", "M15", "M30", "H1", "H4", "D1")
MODEL_FAMILIES = ("lightgbm", "catboost")
CALIBRATORS = ("isotonic", "logistic", "raw")


ASSETS = (
    "AUDCAD",
    "AUDCHF",
    "AUDJPY",
    "AUDNZD",
    "AUDSGD",
    "AUDUSD",
    "CADCHF",
    "CADJPY",
    "CHFJPY",
    "EURAUD",
    "EURCAD",
    "EURCHF",
    "EURGBP",
    "EURJPY",
    "EURNZD",
    "EURUSD",
    "GBPAUD",
    "GBPCAD",
    "GBPCHF",
    "GBPJPY",
    "GBPNZD",
    "GBPUSD",
    "NZDCAD",
    "NZDCHF",
    "NZDJPY",
    "NZDSGD",
    "NZDUSD",
    "USDCAD",
    "USDCHF",
    "USDJPY",
    "GOLD",
)


STRATEGY_ARCHETYPES = {
    "ema_cross_continuation": {
        "name": "EMA Cross Continuation",
        "style": "trend_following",
        "setup": "ema_cross",
        "entry_logic": [
            "BUY when EMA8 crosses or holds above EMA21 and price closes above EMA50.",
            "SELL when EMA8 crosses or holds below EMA21 and price closes below EMA50.",
            "Model signal must agree with the EMA direction.",
        ],
        "exit_logic": {
            "primary": "fixed_tp_sl",
            "invalidation": "close back across EMA21",
            "time_stop_candles": 18,
        },
        "filters": {
            "market_regime": "trend_or_expansion",
            "avoid": "low_adx_range",
            "confirmation": "trend_alignment >= 3",
        },
        "timeframes": ("M15", "M30", "H1"),
        "model_family": "ensemble",
        "calibrator_priority": ("isotonic", "logistic", "raw"),
        "signal_policy": {"min_probability": 0.55, "min_edge": 0.09, "allow_neutral": False},
        "risk": {"tp_points": 300, "sl_points": 130, "cooldown_seconds": 240},
    },
    "trend_pullback_ema21": {
        "name": "Trend Pullback EMA21",
        "style": "trend_pullback",
        "setup": "pullback_to_ema",
        "entry_logic": [
            "Detect H1/H4 trend by EMA21 and EMA50 slope.",
            "Enter after pullback touches EMA21 or EMA50 and closes back in trend direction.",
            "Reject entries if the model disagrees with the trend direction.",
        ],
        "exit_logic": {
            "primary": "fixed_tp_sl",
            "invalidation": "close beyond EMA50 against position",
            "time_stop_candles": 24,
        },
        "filters": {
            "market_regime": "trend",
            "macro_flow": "same_direction",
            "entry_timing": "not_extended",
        },
        "timeframes": ("M30", "H1", "H4"),
        "model_family": "ensemble",
        "calibrator_priority": ("isotonic", "logistic", "raw"),
        "signal_policy": {"min_probability": 0.56, "min_edge": 0.10, "allow_neutral": False},
        "risk": {"tp_points": 450, "sl_points": 170, "cooldown_seconds": 300},
    },
    "inside_bar_breakout": {
        "name": "Inside Bar Breakout",
        "style": "price_action_breakout",
        "setup": "inside_bar",
        "entry_logic": [
            "Mother candle contains the last closed candle.",
            "BUY on break of mother candle high; SELL on break of mother candle low.",
            "Model signal and breakout direction must match.",
        ],
        "exit_logic": {
            "primary": "fixed_tp_sl",
            "invalidation": "return inside mother candle after breakout",
            "time_stop_candles": 12,
        },
        "filters": {
            "volatility": "compression_then_expansion",
            "session": "liquid_session",
            "avoid": "panic_volatility",
        },
        "timeframes": ("M15", "M30", "H1", "H4"),
        "model_family": "ensemble",
        "calibrator_priority": ("isotonic", "logistic", "raw"),
        "signal_policy": {"min_probability": 0.55, "min_edge": 0.08, "allow_neutral": False},
        "risk": {"tp_points": 380, "sl_points": 150, "cooldown_seconds": 240},
    },
    "range_mean_reversion": {
        "name": "Range Mean Reversion",
        "style": "mean_reversion",
        "setup": "range_reversion",
        "entry_logic": [
            "Detect range with low ADX and price near 20-bar high or low.",
            "BUY rejection near range low; SELL rejection near range high.",
            "Model probability must confirm the reversal side.",
        ],
        "exit_logic": {
            "primary": "mid_range_or_fixed_tp",
            "invalidation": "close outside range boundary",
            "time_stop_candles": 20,
        },
        "filters": {
            "market_regime": "range",
            "avoid": "strong_macro_trend",
            "confirmation": "rsi_reversion",
        },
        "timeframes": ("M15", "M30", "H1"),
        "model_family": "lightgbm",
        "calibrator_priority": ("isotonic", "logistic", "raw"),
        "signal_policy": {"min_probability": 0.54, "min_edge": 0.08, "allow_neutral": False},
        "risk": {"tp_points": 240, "sl_points": 120, "cooldown_seconds": 240},
    },
    "volatility_expansion_breakout": {
        "name": "Volatility Expansion Breakout",
        "style": "momentum_breakout",
        "setup": "atr_expansion_breakout",
        "entry_logic": [
            "Identify compression by low ATR ratio or narrow Bollinger width.",
            "Enter in the direction of a close beyond the 20-bar high or low.",
            "Model signal must agree and probability edge must be above threshold.",
        ],
        "exit_logic": {
            "primary": "fixed_tp_sl",
            "invalidation": "failed breakout close back inside range",
            "time_stop_candles": 10,
        },
        "filters": {
            "volatility": "normal_to_expansion",
            "session": "london_or_new_york",
            "avoid": "late_friday",
        },
        "timeframes": ("M5", "M15", "M30", "H1"),
        "model_family": "ensemble",
        "calibrator_priority": ("logistic", "isotonic", "raw"),
        "signal_policy": {"min_probability": 0.56, "min_edge": 0.10, "allow_neutral": False},
        "risk": {"tp_points": 320, "sl_points": 140, "cooldown_seconds": 210},
    },
    "session_momentum_open": {
        "name": "Session Momentum Open",
        "style": "session_momentum",
        "setup": "london_ny_open_momentum",
        "entry_logic": [
            "Trade only during London open, New York open, or overlap.",
            "Enter when candle body expands with model direction and spread is acceptable.",
            "Skip if price is extended more than 1.2 ATR from EMA21.",
        ],
        "exit_logic": {
            "primary": "fixed_tp_sl",
            "invalidation": "opposite momentum candle",
            "time_stop_candles": 8,
        },
        "filters": {
            "session": "open_or_overlap",
            "spread": "strict",
            "entry_timing": "fresh_momentum",
        },
        "timeframes": ("M5", "M15", "M30"),
        "model_family": "lightgbm",
        "calibrator_priority": ("logistic", "isotonic", "raw"),
        "signal_policy": {"min_probability": 0.55, "min_edge": 0.09, "allow_neutral": False},
        "risk": {"tp_points": 180, "sl_points": 90, "cooldown_seconds": 180},
    },
    "liquidity_sweep_reversal": {
        "name": "Liquidity Sweep Reversal",
        "style": "reversal",
        "setup": "sweep_and_reclaim",
        "entry_logic": [
            "Price sweeps the previous 20-bar high or low and closes back inside the range.",
            "BUY after sell-side sweep reclaim; SELL after buy-side sweep reclaim.",
            "Model signal must confirm the reversal side.",
        ],
        "exit_logic": {
            "primary": "range_mid_or_fixed_tp",
            "invalidation": "new sweep continuation against entry",
            "time_stop_candles": 16,
        },
        "filters": {
            "market_structure": "liquidity_sweep",
            "avoid": "clean_trend_day",
            "confirmation": "rsi_divergence_or_exhaustion",
        },
        "timeframes": ("M15", "M30", "H1"),
        "model_family": "ensemble",
        "calibrator_priority": ("isotonic", "logistic", "raw"),
        "signal_policy": {"min_probability": 0.57, "min_edge": 0.11, "allow_neutral": False},
        "risk": {"tp_points": 300, "sl_points": 130, "cooldown_seconds": 300},
    },
    "daily_bias_intraday": {
        "name": "Daily Bias Intraday",
        "style": "top_down_trend",
        "setup": "d1_h4_bias_m15_entry",
        "entry_logic": [
            "Build directional bias from D1 and H4 EMA21/EMA50 alignment.",
            "Enter on M15/M30 continuation only in the higher-timeframe bias.",
            "Reject countertrend model signals.",
        ],
        "exit_logic": {
            "primary": "fixed_tp_sl",
            "invalidation": "higher_timeframe_bias_flip",
            "time_stop_candles": 30,
        },
        "filters": {
            "macro_flow": "required",
            "market_regime": "avoid_chop",
            "portfolio_correlation": "shadow_safe",
        },
        "timeframes": ("M15", "M30", "H1", "H4", "D1"),
        "model_family": "ensemble",
        "calibrator_priority": ("isotonic", "logistic", "raw"),
        "signal_policy": {"min_probability": 0.58, "min_edge": 0.12, "allow_neutral": False},
        "risk": {"tp_points": 520, "sl_points": 190, "cooldown_seconds": 360},
    },
    "support_resistance_bounce": {
        "name": "Support Resistance Bounce",
        "style": "level_reaction",
        "setup": "sr_bounce",
        "entry_logic": [
            "Mark 20-bar and 50-bar support/resistance zones.",
            "Enter on rejection candle away from the level.",
            "Model signal must point away from the tested level.",
        ],
        "exit_logic": {
            "primary": "next_sr_or_fixed_tp",
            "invalidation": "close through tested level",
            "time_stop_candles": 18,
        },
        "filters": {
            "market_structure": "near_sr",
            "avoid": "high_impact_breakout",
            "confirmation": "wick_rejection",
        },
        "timeframes": ("M15", "M30", "H1", "H4"),
        "model_family": "catboost",
        "calibrator_priority": ("isotonic", "logistic", "raw"),
        "signal_policy": {"min_probability": 0.55, "min_edge": 0.09, "allow_neutral": False},
        "risk": {"tp_points": 340, "sl_points": 145, "cooldown_seconds": 270},
    },
    "gold_impulse_pullback": {
        "name": "Gold Impulse Pullback",
        "style": "metal_momentum",
        "setup": "impulse_pullback",
        "entry_logic": [
            "Detect GOLD impulse candle above recent ATR.",
            "Wait for pullback into 38-61 percent of impulse or EMA21.",
            "Enter continuation only if model confirms the impulse direction.",
        ],
        "exit_logic": {
            "primary": "fixed_tp_sl_or_trailing",
            "invalidation": "close below impulse origin for buys or above it for sells",
            "time_stop_candles": 12,
        },
        "filters": {
            "session": "london_ny_only",
            "volatility": "normal_or_expansion",
            "spread": "metal_strict",
        },
        "timeframes": ("M5", "M15", "M30", "H1"),
        "model_family": "ensemble",
        "calibrator_priority": ("isotonic", "logistic", "raw"),
        "signal_policy": {"min_probability": 0.59, "min_edge": 0.13, "allow_neutral": False},
        "risk": {"tp_points": 900, "sl_points": 320, "cooldown_seconds": 240},
    },
}


ASSET_PROFILES = {
    "AUDCAD": {
        "fingerprint": "Commodity cross with frequent ranges and clean intraday reversions.",
        "preferred": ("range_mean_reversion", "support_resistance_bounce", "trend_pullback_ema21", "inside_bar_breakout", "daily_bias_intraday"),
        "avoid": ("session_momentum_open",),
    },
    "AUDCHF": {
        "fingerprint": "Risk-sensitive cross that often respects trend filters and support/resistance.",
        "preferred": ("trend_pullback_ema21", "ema_cross_continuation", "support_resistance_bounce", "range_mean_reversion", "daily_bias_intraday"),
        "avoid": ("volatility_expansion_breakout",),
    },
    "AUDJPY": {
        "fingerprint": "Risk-on/risk-off JPY cross with momentum bursts and strong session moves.",
        "preferred": ("session_momentum_open", "volatility_expansion_breakout", "trend_pullback_ema21", "inside_bar_breakout", "daily_bias_intraday"),
        "avoid": ("range_mean_reversion",),
    },
    "AUDNZD": {
        "fingerprint": "Relative-value cross, usually slower and more range-bound.",
        "preferred": ("range_mean_reversion", "support_resistance_bounce", "liquidity_sweep_reversal", "inside_bar_breakout", "ema_cross_continuation"),
        "avoid": ("session_momentum_open",),
    },
    "AUDSGD": {
        "fingerprint": "Asian-session cross with calmer movement and level reactions.",
        "preferred": ("support_resistance_bounce", "range_mean_reversion", "inside_bar_breakout", "ema_cross_continuation", "daily_bias_intraday"),
        "avoid": ("volatility_expansion_breakout",),
    },
    "AUDUSD": {
        "fingerprint": "Liquid major that alternates between macro trend and session momentum.",
        "preferred": ("daily_bias_intraday", "trend_pullback_ema21", "session_momentum_open", "volatility_expansion_breakout", "ema_cross_continuation"),
        "avoid": ("range_mean_reversion",),
    },
    "CADCHF": {
        "fingerprint": "Often slower and level-driven, with cleaner H1/H4 structure than scalping.",
        "preferred": ("support_resistance_bounce", "range_mean_reversion", "trend_pullback_ema21", "daily_bias_intraday", "inside_bar_breakout"),
        "avoid": ("session_momentum_open",),
    },
    "CADJPY": {
        "fingerprint": "JPY cross with oil/risk sensitivity, suited to trend and expansion setups.",
        "preferred": ("trend_pullback_ema21", "session_momentum_open", "volatility_expansion_breakout", "inside_bar_breakout", "daily_bias_intraday"),
        "avoid": ("range_mean_reversion",),
    },
    "CHFJPY": {
        "fingerprint": "Defensive JPY cross, often technical and trend-respecting.",
        "preferred": ("ema_cross_continuation", "trend_pullback_ema21", "inside_bar_breakout", "support_resistance_bounce", "daily_bias_intraday"),
        "avoid": ("session_momentum_open",),
    },
    "EURAUD": {
        "fingerprint": "Volatile EUR commodity cross with good directional swings.",
        "preferred": ("trend_pullback_ema21", "daily_bias_intraday", "inside_bar_breakout", "volatility_expansion_breakout", "support_resistance_bounce"),
        "avoid": ("range_mean_reversion",),
    },
    "EURCAD": {
        "fingerprint": "Cross that mixes H1/H4 trend phases with support/resistance reactions.",
        "preferred": ("trend_pullback_ema21", "support_resistance_bounce", "daily_bias_intraday", "inside_bar_breakout", "liquidity_sweep_reversal"),
        "avoid": ("session_momentum_open",),
    },
    "EURCHF": {
        "fingerprint": "Historically compressed cross, better for range and level logic.",
        "preferred": ("range_mean_reversion", "support_resistance_bounce", "inside_bar_breakout", "liquidity_sweep_reversal", "ema_cross_continuation"),
        "avoid": ("volatility_expansion_breakout",),
    },
    "EURGBP": {
        "fingerprint": "Mean-reverting cross that often respects levels more than raw momentum.",
        "preferred": ("range_mean_reversion", "support_resistance_bounce", "liquidity_sweep_reversal", "inside_bar_breakout", "daily_bias_intraday"),
        "avoid": ("session_momentum_open",),
    },
    "EURJPY": {
        "fingerprint": "Liquid JPY cross with trend continuation and breakout behavior.",
        "preferred": ("trend_pullback_ema21", "ema_cross_continuation", "session_momentum_open", "inside_bar_breakout", "daily_bias_intraday"),
        "avoid": ("range_mean_reversion",),
    },
    "EURNZD": {
        "fingerprint": "Volatile cross with strong swings and false-break reversals.",
        "preferred": ("trend_pullback_ema21", "liquidity_sweep_reversal", "inside_bar_breakout", "volatility_expansion_breakout", "daily_bias_intraday"),
        "avoid": ("session_momentum_open",),
    },
    "EURUSD": {
        "fingerprint": "Most liquid major, suitable for top-down trend and session momentum.",
        "preferred": ("daily_bias_intraday", "session_momentum_open", "ema_cross_continuation", "trend_pullback_ema21", "inside_bar_breakout"),
        "avoid": (),
    },
    "GBPAUD": {
        "fingerprint": "High-volatility GBP cross, strong trend and breakout personality.",
        "preferred": ("volatility_expansion_breakout", "trend_pullback_ema21", "inside_bar_breakout", "daily_bias_intraday", "liquidity_sweep_reversal"),
        "avoid": ("range_mean_reversion",),
    },
    "GBPCAD": {
        "fingerprint": "Volatile but technical cross, useful for pullback and level breaks.",
        "preferred": ("trend_pullback_ema21", "inside_bar_breakout", "volatility_expansion_breakout", "support_resistance_bounce", "daily_bias_intraday"),
        "avoid": ("session_momentum_open",),
    },
    "GBPCHF": {
        "fingerprint": "GBP volatility with CHF technical levels, needs stricter confirmation.",
        "preferred": ("inside_bar_breakout", "trend_pullback_ema21", "support_resistance_bounce", "liquidity_sweep_reversal", "daily_bias_intraday"),
        "avoid": ("session_momentum_open",),
    },
    "GBPJPY": {
        "fingerprint": "Fast JPY cross, suited to momentum, breakout, and trend continuation.",
        "preferred": ("session_momentum_open", "volatility_expansion_breakout", "trend_pullback_ema21", "inside_bar_breakout", "daily_bias_intraday"),
        "avoid": ("range_mean_reversion",),
    },
    "GBPNZD": {
        "fingerprint": "Very volatile cross with deep pullbacks and frequent sweeps.",
        "preferred": ("liquidity_sweep_reversal", "volatility_expansion_breakout", "trend_pullback_ema21", "inside_bar_breakout", "daily_bias_intraday"),
        "avoid": ("range_mean_reversion",),
    },
    "GBPUSD": {
        "fingerprint": "Liquid major with London momentum and structured pullbacks.",
        "preferred": ("session_momentum_open", "daily_bias_intraday", "trend_pullback_ema21", "inside_bar_breakout", "ema_cross_continuation"),
        "avoid": (),
    },
    "NZDCAD": {
        "fingerprint": "Commodity cross, often slower and responsive to range boundaries.",
        "preferred": ("range_mean_reversion", "support_resistance_bounce", "trend_pullback_ema21", "inside_bar_breakout", "liquidity_sweep_reversal"),
        "avoid": ("session_momentum_open",),
    },
    "NZDCHF": {
        "fingerprint": "Lower-volatility cross, better for levels, ranges, and measured trend.",
        "preferred": ("support_resistance_bounce", "range_mean_reversion", "ema_cross_continuation", "trend_pullback_ema21", "inside_bar_breakout"),
        "avoid": ("volatility_expansion_breakout",),
    },
    "NZDJPY": {
        "fingerprint": "JPY risk cross with momentum phases and clean pullbacks.",
        "preferred": ("trend_pullback_ema21", "session_momentum_open", "volatility_expansion_breakout", "inside_bar_breakout", "daily_bias_intraday"),
        "avoid": ("range_mean_reversion",),
    },
    "NZDSGD": {
        "fingerprint": "Asian-session cross with slower range and level behavior.",
        "preferred": ("range_mean_reversion", "support_resistance_bounce", "inside_bar_breakout", "ema_cross_continuation", "daily_bias_intraday"),
        "avoid": ("session_momentum_open",),
    },
    "NZDUSD": {
        "fingerprint": "Liquid commodity major, alternating trend continuation and range behavior.",
        "preferred": ("daily_bias_intraday", "trend_pullback_ema21", "range_mean_reversion", "session_momentum_open", "ema_cross_continuation"),
        "avoid": (),
    },
    "USDCAD": {
        "fingerprint": "Liquid major with oil sensitivity, good for trend and level strategies.",
        "preferred": ("daily_bias_intraday", "trend_pullback_ema21", "support_resistance_bounce", "inside_bar_breakout", "ema_cross_continuation"),
        "avoid": (),
    },
    "USDCHF": {
        "fingerprint": "Defensive major that often respects levels and H1 trend filters.",
        "preferred": ("support_resistance_bounce", "trend_pullback_ema21", "range_mean_reversion", "ema_cross_continuation", "daily_bias_intraday"),
        "avoid": ("session_momentum_open",),
    },
    "USDJPY": {
        "fingerprint": "Macro/trend-sensitive major with strong session impulses.",
        "preferred": ("daily_bias_intraday", "session_momentum_open", "trend_pullback_ema21", "ema_cross_continuation", "inside_bar_breakout"),
        "avoid": ("range_mean_reversion",),
    },
    "GOLD": {
        "fingerprint": "High-volatility metal, best handled with impulse, breakout, and strict session filters.",
        "preferred": ("gold_impulse_pullback", "inside_bar_breakout", "volatility_expansion_breakout", "liquidity_sweep_reversal", "daily_bias_intraday"),
        "avoid": ("range_mean_reversion",),
        "risk_multiplier": 2.4,
    },
}


def _available_routes(symbol: str, timeframes: tuple[str, ...], model_family: str, calibrators: tuple[str, ...]) -> list[dict]:
    families = MODEL_FAMILIES if model_family == "ensemble" else (model_family,)
    routes: list[dict] = []
    for timeframe in timeframes:
        for family in families:
            for calibrator in calibrators:
                base = MODEL_ROOT / symbol / timeframe / family / calibrator
                model_path = base / "model.pkl"
                meta_path = base / "meta.json"
                if not model_path.exists() or not meta_path.exists():
                    continue
                routes.append(
                    {
                        "timeframe": timeframe,
                        "model_family": family,
                        "calibrator": calibrator,
                        "model_path": str(model_path),
                        "scaler_path": str(base / "scaler.pkl"),
                        "calibrator_path": "" if calibrator == "raw" else str(base / "calibrator.pkl"),
                        "meta_path": str(meta_path),
                        "regime_hmm_path": str(MODEL_ROOT / symbol / timeframe / family / "regime_hmm.pkl"),
                    }
                )
    return routes


def _with_asset_risk(strategy: dict, multiplier: float) -> dict:
    if multiplier == 1.0:
        return strategy
    risk = dict(strategy["risk"])
    for key in ("tp_points", "sl_points"):
        risk[key] = int(round(float(risk[key]) * multiplier))
    strategy["risk"] = risk
    return strategy


def _build_strategy(symbol: str, strategy_id: str, profile: dict) -> dict:
    archetype = deepcopy(STRATEGY_ARCHETYPES[strategy_id])
    archetype["id"] = strategy_id
    archetype["asset"] = symbol
    archetype["model_root"] = str(MODEL_ROOT / symbol)
    archetype["asset_fingerprint"] = profile["fingerprint"]
    archetype["selection_reason"] = (
        f"Chosen for {symbol} because this asset profile is: {profile['fingerprint']}"
    )
    archetype["not_preferred_setups"] = tuple(profile.get("avoid", ()))
    archetype["available_model_routes"] = _available_routes(
        symbol,
        archetype["timeframes"],
        archetype["model_family"],
        archetype["calibrator_priority"],
    )
    return _with_asset_risk(archetype, float(profile.get("risk_multiplier", 1.0)))


def build_asset_strategy_bank(symbol: str) -> dict:
    """Return an asset-specific strategy bank for one trained asset."""
    symbol = symbol.upper()
    if symbol not in ASSETS:
        raise ValueError(f"Asset without registered models_research bank: {symbol}")

    profile = ASSET_PROFILES[symbol]
    strategies = [_build_strategy(symbol, strategy_id, profile) for strategy_id in profile["preferred"]]

    return {
        "asset": symbol,
        "source": "models_research",
        "asset_fingerprint": profile["fingerprint"],
        "timeframes": TIMEFRAMES,
        "strategy_count": len(strategies),
        "strategies": strategies,
    }


def build_strategy_bank() -> dict[str, dict]:
    return {asset: build_asset_strategy_bank(asset) for asset in ASSETS}
