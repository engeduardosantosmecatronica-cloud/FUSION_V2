from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

import joblib
import numpy as np
import pandas as pd
import yaml

from train_model import TF_MAP, calculate_features, create_target, train_single_model


TIMEFRAMES = ["M5", "M15", "M30", "H1", "H4", "D1"]
MT5_TF = {}


def load_config(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def read_missing(path: Path) -> list[tuple[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [(row["symbol"].upper(), row["timeframe"].upper()) for row in reader]


def latest_missing_report() -> Path | None:
    report_dir = PROJECT_DIR / "reports" / "model_source_cleanup"
    candidates = sorted(report_dir.glob("missing_for_retrain_applied.csv"), key=lambda p: p.stat().st_mtime)
    return candidates[-1] if candidates else None


def broker_symbol(mt5, requested: str, broker_symbols: dict[str, str]) -> str | None:
    symbol = requested.upper()
    if symbol in broker_symbols:
        return broker_symbols[symbol]
    if symbol == "XAUUSD":
        for name, real in broker_symbols.items():
            if "XAUUSD" in name or "GOLD" in name:
                return real
    for name, real in broker_symbols.items():
        if name.startswith(symbol):
            return real
    return None


def get_rates(mt5, symbol: str, timeframe: str, count: int) -> pd.DataFrame | None:
    rates = mt5.copy_rates_from_pos(symbol, MT5_TF[timeframe], 0, count)
    if rates is None or len(rates) == 0:
        return None
    frame = pd.DataFrame(rates)
    frame["time"] = pd.to_datetime(frame["time"], unit="s")
    return frame.set_index("time").sort_index()


def save_model(output_dir: Path, symbol: str, timeframe: str, payload: dict) -> None:
    model_dir = output_dir / symbol / timeframe
    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(payload["model"], model_dir / "model.pkl")
    joblib.dump(payload["scaler"], model_dir / "scaler.pkl")
    joblib.dump(payload["meta"], model_dir / "meta.pkl")


def merge_index(output_dir: Path, rows: list[dict]) -> None:
    index_path = output_dir / "models_index.csv"
    old = pd.read_csv(index_path) if index_path.exists() else pd.DataFrame()
    new = pd.DataFrame(rows)
    merged = pd.concat([old, new], ignore_index=True) if not old.empty else new
    merged = merged.drop_duplicates(subset=["symbol", "timeframe"], keep="last")
    merged = merged.sort_values(["symbol", "timeframe"])
    merged.to_csv(index_path, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Retreina lacunas do runtime direto no MT5.")
    parser.add_argument("--missing-report", default="")
    parser.add_argument("--config", default="config/fusion_config.yaml")
    parser.add_argument("--output-dir", default="models_principal")
    parser.add_argument("--bars", type=int, default=5000)
    parser.add_argument("--min-samples", type=int, default=500)
    args = parser.parse_args()

    try:
        import MetaTrader5 as mt5
    except ImportError as exc:
        raise SystemExit(f"MetaTrader5 indisponivel: {exc}") from exc

    global MT5_TF
    MT5_TF = {
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
    }

    cfg = load_config(PROJECT_DIR / args.config)
    terminal_path = cfg.get("broker", {}).get("terminal_path", "")
    initialized = mt5.initialize(path=terminal_path) if terminal_path else mt5.initialize()
    if not initialized:
        raise SystemExit(f"Falha ao inicializar MT5: {mt5.last_error()}")

    missing_path = Path(args.missing_report) if args.missing_report else latest_missing_report()
    if missing_path is None:
        raise SystemExit("Relatorio de lacunas nao encontrado. Rode tools/model_source_cleanup.py antes.")
    if not missing_path.is_absolute():
        missing_path = PROJECT_DIR / missing_path

    output_dir = PROJECT_DIR / args.output_dir
    missing = read_missing(missing_path)
    broker_symbols = {s.name.upper(): s.name for s in mt5.symbols_get()}
    report_rows: list[dict] = []
    trained_rows: list[dict] = []

    try:
        for symbol, timeframe in missing:
            real_symbol = broker_symbol(mt5, symbol, broker_symbols)
            status = "skipped"
            message = ""
            try:
                if not real_symbol:
                    message = "simbolo ausente no broker"
                    print(f"[SKIP] {symbol} {timeframe} | {message}")
                    report_rows.append({"symbol": symbol, "timeframe": timeframe, "status": status, "message": message})
                    continue
                mt5.symbol_select(real_symbol, True)
                frame = get_rates(mt5, real_symbol, timeframe, args.bars)
                if frame is None or len(frame) < args.min_samples:
                    message = f"dados insuficientes: {0 if frame is None else len(frame)}"
                    print(f"[SKIP] {symbol} {timeframe} | {message}")
                    report_rows.append({"symbol": symbol, "timeframe": timeframe, "status": status, "message": message})
                    continue

                features = calculate_features(frame)
                target = create_target(frame, horizon=TF_MAP[timeframe])
                common_idx = features.dropna().index.intersection(target.dropna().index)
                x = features.loc[common_idx]
                y = target.loc[common_idx]
                if len(x) < args.min_samples:
                    message = f"features insuficientes: {len(x)}"
                    print(f"[SKIP] {symbol} {timeframe} | {message}")
                    report_rows.append({"symbol": symbol, "timeframe": timeframe, "status": status, "message": message})
                    continue
                if y.nunique() < 2:
                    message = f"target com classe unica: {sorted(y.unique().tolist())}"
                    print(f"[SKIP] {symbol} {timeframe} | {message}")
                    report_rows.append({"symbol": symbol, "timeframe": timeframe, "status": status, "message": message})
                    continue

                model, scaler, accuracy, buy_thresh, sell_thresh = train_single_model(x, y, symbol, timeframe)
                if model is None:
                    message = "falha no treino"
                    print(f"[SKIP] {symbol} {timeframe} | {message}")
                    report_rows.append({"symbol": symbol, "timeframe": timeframe, "status": status, "message": message})
                    continue

                classes = sorted(int(cls) for cls in getattr(model, "classes_", []))
                meta = {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "accuracy": float(accuracy),
                    "buy_threshold": float(buy_thresh),
                    "sell_threshold": float(sell_thresh),
                    "feature_columns": x.columns.tolist(),
                    "training_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "train_samples": int(len(x) * 0.8),
                    "test_samples": int(len(x) * 0.2),
                    "source": "fusion_mt5_direct",
                    "broker_symbol": real_symbol,
                    "bars": args.bars,
                    "classes": classes,
                }
                save_model(output_dir, symbol, timeframe, {"model": model, "scaler": scaler, "meta": meta})
                trained_rows.append(
                    {
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "accuracy": accuracy,
                        "buy_threshold": buy_thresh,
                        "sell_threshold": sell_thresh,
                        "train_samples": meta["train_samples"],
                        "source": "fusion_mt5_direct",
                    }
                )
                status = "trained"
                message = f"acc={accuracy:.3f} classes={classes} samples={len(x)}"
                print(f"[OK] {symbol} {timeframe} | {message}")
            except Exception as exc:
                status = "error"
                message = f"{type(exc).__name__}: {exc}"
                print(f"[ERROR] {symbol} {timeframe} | {message}")
            report_rows.append({"symbol": symbol, "timeframe": timeframe, "status": status, "message": message})
    finally:
        mt5.shutdown()

    if trained_rows:
        merge_index(output_dir, trained_rows)

    report_dir = PROJECT_DIR / "reports" / "model_training"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"missing_retrain_mt5_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    pd.DataFrame(report_rows).to_csv(report_path, index=False)
    print(f"Relatorio: {report_path}")
    print(f"Modelos treinados: {len(trained_rows)}")


if __name__ == "__main__":
    main()
