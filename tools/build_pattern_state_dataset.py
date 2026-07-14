from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from fusion.features.pattern_state import PatternStateConfig, build_pattern_state_features, summarize_pattern_states


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera dataset candle a candle de estados para mineracao de padroes.")
    parser.add_argument("--symbols", nargs="*", default=[], help="Simbolos. Vazio = todos encontrados em latest_candles.")
    parser.add_argument("--timeframes", nargs="*", default=["M15", "M30", "H1", "H4"])
    parser.add_argument("--latest-dir", default="runtime/market_data/latest_candles")
    parser.add_argument("--config", default="config/fusion_config.yaml", help="Config usada para simbolos habilitados quando --symbols vier vazio.")
    parser.add_argument("--runtime-control", default="config/fusion_runtime_control.json", help="Runtime control usado para excluir simbolos bloqueados.")
    parser.add_argument("--scan-all-latest", action="store_true", help="Ignora config e varre todos os JSONs da pasta latest_candles.")
    parser.add_argument("--output-dir", default="reports/pattern_state")
    parser.add_argument("--tail", type=int, default=0, help="Limita os ultimos N candles por arquivo. 0 = todos.")
    return parser.parse_args()


def load_latest(path: Path) -> pd.DataFrame:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        print(f"[SKIP] {path.name}: json_invalido:{exc}")
        return pd.DataFrame()
    candles = payload.get("candles", [])
    if not candles:
        return pd.DataFrame()
    frame = pd.DataFrame(candles)
    for col in ["open", "high", "low", "close", "tick_volume", "real_volume", "volume", "spread"]:
        if col in frame.columns:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")
    frame["time"] = pd.to_datetime(frame["time"], errors="coerce")
    frame = frame.dropna(subset=["time", "open", "high", "low", "close"]).sort_values("time").reset_index(drop=True)
    if "tick_volume" not in frame.columns and "volume" not in frame.columns:
        frame["tick_volume"] = 0.0
    return frame


def infer(path: Path) -> tuple[str, str]:
    stem = path.stem
    if "_" not in stem:
        return "", ""
    symbol, timeframe = stem.rsplit("_", 1)
    return symbol.upper(), timeframe.upper()



def configured_symbols(config_path: Path, runtime_path: Path) -> set[str]:
    result: set[str] = set()
    if config_path.exists():
        try:
            cfg = yaml.safe_load(config_path.read_text(encoding="utf-8-sig")) or {}
            result.update(str(item).upper() for item in (cfg.get("symbols") or []) if item)
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] falha ao ler config de simbolos: {exc}")
    excluded: set[str] = set()
    if runtime_path.exists():
        try:
            runtime = json.loads(runtime_path.read_text(encoding="utf-8-sig"))
            symbols_cfg = runtime.get("symbols", {}) if isinstance(runtime, dict) else {}
            excluded.update(str(item).upper() for item in (symbols_cfg.get("exclude") or []) if item)
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] falha ao ler runtime_control: {exc}")
    return {symbol for symbol in result if symbol not in excluded}

def main() -> None:
    args = parse_args()
    latest_dir = Path(args.latest_dir)
    output_dir = Path(args.output_dir)
    if not latest_dir.is_absolute():
        latest_dir = PROJECT_DIR / latest_dir
    if not output_dir.is_absolute():
        output_dir = PROJECT_DIR / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    config_path = Path(args.config)
    runtime_path = Path(args.runtime_control)
    if not config_path.is_absolute():
        config_path = PROJECT_DIR / config_path
    if not runtime_path.is_absolute():
        runtime_path = PROJECT_DIR / runtime_path
    symbols = {item.upper() for item in args.symbols}
    if not symbols and not args.scan_all_latest:
        symbols = configured_symbols(config_path, runtime_path)
    timeframes = {item.upper() for item in args.timeframes}
    manifest: list[dict] = []
    combined: list[pd.DataFrame] = []

    for path in sorted(latest_dir.glob("*.json")):
        symbol, timeframe = infer(path)
        if not symbol or not timeframe:
            continue
        if symbols and symbol not in symbols:
            continue
        if timeframes and timeframe not in timeframes:
            continue
        frame = load_latest(path)
        if args.tail and len(frame) > args.tail:
            frame = frame.tail(args.tail).reset_index(drop=True)
        if frame.empty:
            print(f"[SKIP] {symbol} {timeframe}: sem candles")
            continue
        features = build_pattern_state_features(frame, PatternStateConfig())
        if features.empty:
            print(f"[SKIP] {symbol} {timeframe}: sem features")
            continue
        features.insert(0, "symbol", symbol)
        features.insert(1, "timeframe", timeframe)
        out_path = output_dir / f"{symbol}_{timeframe}_pattern_state.csv"
        features.to_csv(out_path, index=False)
        summary = summarize_pattern_states(features)
        summary.update({"symbol": symbol, "timeframe": timeframe, "path": str(out_path)})
        manifest.append(summary)
        combined.append(features)
        print(f"[OK] {symbol} {timeframe}: {len(features)} candles -> {out_path}")

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    if combined:
        all_features = pd.concat(combined, ignore_index=True)
        counts = all_features.groupby(["symbol", "timeframe", "regime", "estrutura", "momentum", "volume_state", "volatilidade"]).size().reset_index(name="samples")
        counts = counts.sort_values("samples", ascending=False)
        counts.to_csv(output_dir / "pattern_state_counts.csv", index=False)
        setup_cols = [col for col in all_features.columns if col.startswith("setup_")]
        setup_rows = []
        for col in setup_cols:
            by_pair = all_features.groupby(["symbol", "timeframe"])[col].sum().reset_index(name="signals")
            by_pair.insert(0, "setup", col)
            setup_rows.append(by_pair)
        if setup_rows:
            pd.concat(setup_rows, ignore_index=True).sort_values(["setup", "signals"], ascending=[True, False]).to_csv(output_dir / "setup_signal_counts.csv", index=False)
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
