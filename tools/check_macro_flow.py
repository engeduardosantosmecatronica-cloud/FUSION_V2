from __future__ import annotations

import argparse
import json
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd
import yaml

from fusion.features.macro_flow import (
    MacroFlowConfig,
    aggregate_symbol_flow,
    currency_strength_from_flows,
    direction_to_prediction,
    split_forex_symbol,
    timeframe_flow,
)


TF_CODES = {
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verifica fluxo macro dominante antes de uma ordem.")
    parser.add_argument("--config", default="config/fusion_config.yaml")
    parser.add_argument("--symbol", default="")
    parser.add_argument("--direction", choices=["BUY", "SELL", "buy", "sell"], default="BUY")
    parser.add_argument("--signal-timeframe", default="M5")
    parser.add_argument("--output", default="")
    return parser.parse_args()


def load_config(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def real_symbol(symbol: str, mapping: dict) -> str:
    return str(mapping.get(symbol, mapping.get(symbol.upper(), symbol))).upper()


def load_rates(symbol: str, tf: str, bars: int) -> pd.DataFrame:
    rates = mt5.copy_rates_from_pos(symbol, TF_CODES[tf], 0, bars)
    if rates is None or len(rates) == 0:
        return pd.DataFrame()
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    return df.sort_values("time").reset_index(drop=True)


def build_flow_cfg(config: dict, signal_tf: str) -> MacroFlowConfig:
    cfg = ((config.get("entry_filters") or {}).get("macro_flow") or {})
    strength_cfg = cfg.get("currency_strength", {}) or {}
    tf_cfg = (cfg.get("by_signal_timeframe", {}) or {}).get(signal_tf.upper(), {}) or {}
    return MacroFlowConfig(
        timeframes=[str(item).upper() for item in tf_cfg.get("timeframes", cfg.get("timeframes", ["H1", "H4", "D1"]))],
        bars=max(80, int(cfg.get("bars", 260) or 260)),
        ema_fast=int(cfg.get("ema_fast", 21) or 21),
        ema_slow=int(cfg.get("ema_slow", 50) or 50),
        atr_period=int(cfg.get("atr_period", 14) or 14),
        momentum_bars=int(cfg.get("momentum_bars", 20) or 20),
        min_score=float(cfg.get("min_score", 0.20) or 0.20),
        weights=tf_cfg.get("weights", cfg.get("weights", {}) or {}) or {},
        aggregation=str(cfg.get("aggregation", "weighted_majority") or "weighted_majority"),
        currency_strength_enabled=bool(strength_cfg.get("enabled", True)),
        currency_strength_weight=float(strength_cfg.get("weight", 0.35) or 0.35),
    )


def analyze(config: dict, target_symbol: str, direction: str, signal_tf: str) -> dict:
    data_cfg = config.get("data", {}) or {}
    mapping = data_cfg.get("symbol_mapping", {}) or {}
    symbols = [str(item).upper() for item in config.get("symbols", []) or []]
    flow_cfg = build_flow_cfg(config, signal_tf)

    symbol_results = {}
    for symbol in symbols:
        broker_symbol = real_symbol(symbol, mapping)
        tf_results = {}
        for tf in flow_cfg.timeframes:
            frame = load_rates(broker_symbol, tf, flow_cfg.bars)
            tf_results[tf] = timeframe_flow(frame, flow_cfg)
        aggregate = aggregate_symbol_flow(tf_results, flow_cfg)
        symbol_results[symbol] = {
            "broker_symbol": broker_symbol,
            "score": aggregate["score"],
            "direction": aggregate["direction"],
            "reason": aggregate["reason"],
            "timeframes": tf_results,
        }

    strengths = currency_strength_from_flows({symbol: data["score"] for symbol, data in symbol_results.items()})
    target = target_symbol.upper()
    target_flow = symbol_results.get(target, {})
    macro_score = float(target_flow.get("score", 0.0) or 0.0)
    parsed = split_forex_symbol(target)
    if parsed and flow_cfg.currency_strength_enabled:
        base, quote = parsed
        pair_strength = float(strengths.get(base, 0.0) or 0.0) - float(strengths.get(quote, 0.0) or 0.0)
        macro_score = ((1.0 - flow_cfg.currency_strength_weight) * macro_score) + (
            flow_cfg.currency_strength_weight * pair_strength
        )
        target_flow["base_strength"] = strengths.get(base, 0.0)
        target_flow["quote_strength"] = strengths.get(quote, 0.0)
        target_flow["pair_strength"] = pair_strength

    macro_direction = "BUY" if macro_score > flow_cfg.min_score else "SELL" if macro_score < -flow_cfg.min_score else "NEUTRO"
    wanted_pred = 1 if direction.upper() == "BUY" else 2
    macro_pred = direction_to_prediction(macro_direction)
    decision = "OK"
    if macro_pred == 0:
        decision = "NEUTRO"
    elif macro_pred != wanted_pred:
        decision = "CONTRA"

    return {
        "symbol": target,
        "signal_timeframe": signal_tf.upper(),
        "aggregation": flow_cfg.aggregation,
        "direction_requested": direction.upper(),
        "macro_direction": macro_direction,
        "macro_score": macro_score,
        "decision": decision,
        "target_flow": target_flow,
        "currency_strength": strengths,
    }


def main() -> None:
    args = parse_args()
    config = load_config(Path(args.config))
    if not mt5.initialize():
        raise SystemExit("Falha ao inicializar MetaTrader5.")
    try:
        result = analyze(config, args.symbol or (config.get("symbols") or ["EURUSD"])[0], args.direction, args.signal_timeframe)
    finally:
        mt5.shutdown()
    text = json.dumps(result, indent=2, ensure_ascii=False, default=str)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
