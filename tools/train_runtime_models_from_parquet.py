from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from train_model import TF_MAP, calculate_features, create_target, train_single_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Treina modelos runtime do FUSION_V2 usando data/parquet."
    )
    parser.add_argument("--symbols", nargs="+", required=True)
    parser.add_argument("--timeframes", nargs="+", default=["M5", "M15", "M30", "H1", "H4", "D1"])
    parser.add_argument("--parquet-dir", default="data/parquet")
    parser.add_argument("--output-dir", default="models_principal")
    parser.add_argument("--max-bars", type=int, default=5000)
    parser.add_argument("--min-samples", type=int, default=500)
    return parser.parse_args()


def load_rates(parquet_path: Path, max_bars: int) -> pd.DataFrame | None:
    if not parquet_path.exists():
        return None
    df = pd.read_parquet(parquet_path).copy()
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").tail(max_bars)
        df = df.set_index("date")
    else:
        df = df.sort_index().tail(max_bars)
    return df


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
    if old.empty:
        merged = new
    else:
        merged = pd.concat([old, new], ignore_index=True)
        merged = merged.drop_duplicates(subset=["symbol", "timeframe"], keep="last")
    merged = merged.sort_values(["symbol", "timeframe"])
    merged.to_csv(index_path, index=False)


def main() -> None:
    args = parse_args()
    parquet_dir = Path(args.parquet_dir)
    output_dir = Path(args.output_dir)
    if not parquet_dir.is_absolute():
        parquet_dir = PROJECT_DIR / parquet_dir
    if not output_dir.is_absolute():
        output_dir = PROJECT_DIR / output_dir

    trained_rows: list[dict] = []
    report_rows: list[dict] = []

    for symbol in [s.upper() for s in args.symbols]:
        for timeframe in [tf.upper() for tf in args.timeframes]:
            parquet_path = parquet_dir / timeframe / f"{symbol}.parquet"
            status = "skipped"
            message = ""
            try:
                df = load_rates(parquet_path, args.max_bars)
                if df is None:
                    message = f"parquet ausente: {parquet_path}"
                    print(f"[SKIP] {symbol} {timeframe} | {message}")
                    report_rows.append({"symbol": symbol, "timeframe": timeframe, "status": status, "message": message})
                    continue
                if len(df) < args.min_samples:
                    message = f"dados insuficientes: {len(df)}"
                    print(f"[SKIP] {symbol} {timeframe} | {message}")
                    report_rows.append({"symbol": symbol, "timeframe": timeframe, "status": status, "message": message})
                    continue

                features = calculate_features(df)
                target = create_target(df, horizon=TF_MAP[timeframe])
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

                meta = {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "accuracy": accuracy,
                    "buy_threshold": buy_thresh,
                    "sell_threshold": sell_thresh,
                    "feature_columns": x.columns.tolist(),
                    "training_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "train_samples": int(len(x) * 0.8),
                    "test_samples": int(len(x) * 0.2),
                    "source": "data/parquet",
                    "max_bars": args.max_bars,
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
                    }
                )
                status = "trained"
                message = f"acc={accuracy:.3f} buy={buy_thresh:.3f} sell={sell_thresh:.3f} samples={len(x)}"
                print(f"[OK] {symbol} {timeframe} | {message}")
            except Exception as exc:
                status = "error"
                message = str(exc)
                print(f"[ERROR] {symbol} {timeframe} | {message}")
            report_rows.append({"symbol": symbol, "timeframe": timeframe, "status": status, "message": message})

    if trained_rows:
        merge_index(output_dir, trained_rows)

    reports_dir = PROJECT_DIR / "reports"
    reports_dir.mkdir(exist_ok=True)
    report_path = reports_dir / "runtime_model_training_from_parquet.csv"
    pd.DataFrame(report_rows).to_csv(report_path, index=False)
    print(f"Relatorio: {report_path}")
    print(f"Modelos treinados: {len(trained_rows)}")


if __name__ == "__main__":
    main()
