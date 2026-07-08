from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

import joblib
import numpy as np
import pandas as pd
import yaml
from lightgbm import LGBMClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, log_loss
from sklearn.preprocessing import StandardScaler

try:
    from catboost import CatBoostClassifier
except ImportError:  # pragma: no cover
    CatBoostClassifier = None

try:
    from hmmlearn.hmm import GaussianHMM
except ImportError:  # pragma: no cover
    GaussianHMM = None

from train_model import TF_MAP, calculate_features, create_target


TIMEFRAMES = ["M5", "M15", "M30", "H1", "H4", "D1"]
CLASS_LABELS = [0, 1, 2]


@dataclass
class TrainResult:
    symbol: str
    timeframe: str
    model_name: str
    calibrator: str
    split_mode: str
    train_samples: int
    test_samples: int
    valid_samples: int
    accuracy_test: float
    balanced_accuracy_test: float
    f1_macro_test: float
    logloss_test: float
    accuracy_valid: float
    balanced_accuracy_valid: float
    f1_macro_valid: float
    logloss_valid: float
    trade_coverage_valid: float
    directional_accuracy_valid: float
    source_path: str
    artifact_dir: str
    notes: str = ""


class LogisticProbabilityCalibrator:
    def __init__(self) -> None:
        self.model = LogisticRegression(max_iter=1000)
        self.classes_: list[int] = CLASS_LABELS

    def fit(self, probs: np.ndarray, y: np.ndarray) -> "LogisticProbabilityCalibrator":
        self.model.fit(probs, y)
        self.classes_ = [int(cls) for cls in self.model.classes_]
        return self

    def predict_proba(self, probs: np.ndarray) -> np.ndarray:
        raw = self.model.predict_proba(probs)
        return align_proba(raw, self.classes_)


class IsotonicProbabilityCalibrator:
    def __init__(self) -> None:
        self.models: dict[int, IsotonicRegression] = {}

    def fit(self, probs: np.ndarray, y: np.ndarray) -> "IsotonicProbabilityCalibrator":
        for class_idx, label in enumerate(CLASS_LABELS):
            binary = (y == label).astype(int)
            if binary.min() == binary.max():
                continue
            model = IsotonicRegression(out_of_bounds="clip")
            model.fit(probs[:, class_idx], binary)
            self.models[label] = model
        return self

    def predict_proba(self, probs: np.ndarray) -> np.ndarray:
        calibrated = np.zeros_like(probs, dtype=float)
        for class_idx, label in enumerate(CLASS_LABELS):
            model = self.models.get(label)
            calibrated[:, class_idx] = model.predict(probs[:, class_idx]) if model else probs[:, class_idx]
        row_sum = calibrated.sum(axis=1, keepdims=True)
        return calibrated / np.where(row_sum == 0, 1.0, row_sum)


def load_config(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def normalize_rates(frame: pd.DataFrame) -> pd.DataFrame:
    df = frame.copy()
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").set_index("date")
    elif "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"])
        df = df.sort_values("time").set_index("time")
    else:
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
    return df


def load_parquet(symbol: str, timeframe: str, parquet_dir: Path, max_bars: int) -> tuple[pd.DataFrame | None, Path]:
    path = parquet_dir / timeframe / f"{symbol}.parquet"
    if not path.exists() and symbol in {"XAUUSD", "GOLD"}:
        for candidate in ["XAUUSD.parquet", "XAUUSD-F.parquet", "GOLD.parquet"]:
            alt = parquet_dir / timeframe / candidate
            if alt.exists():
                path = alt
                break
    if not path.exists():
        return None, path
    frame = normalize_rates(pd.read_parquet(path))
    if max_bars > 0:
        frame = frame.tail(max_bars)
    return frame, path


def distributed_block_split(
    index: pd.DatetimeIndex,
    block_freq: str,
    train_ratio: float,
    test_ratio: float,
    valid_ratio: float,
    embargo: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    train_parts: list[np.ndarray] = []
    test_parts: list[np.ndarray] = []
    valid_parts: list[np.ndarray] = []
    periods = pd.Series(np.arange(len(index)), index=index).groupby(index.to_period(block_freq))
    ratio_sum = train_ratio + test_ratio + valid_ratio
    train_ratio = train_ratio / ratio_sum
    test_ratio = test_ratio / ratio_sum

    for _, positions in periods:
        pos = positions.to_numpy()
        n = len(pos)
        min_needed = max(12, embargo * 4 + 6)
        if n < min_needed:
            continue
        train_end = int(math.floor(n * train_ratio))
        test_end = int(math.floor(n * (train_ratio + test_ratio)))
        train = pos[: max(0, train_end - embargo)]
        test = pos[min(n, train_end + embargo): max(train_end + embargo, test_end - embargo)]
        valid = pos[min(n, test_end + embargo):]
        if len(train):
            train_parts.append(train)
        if len(test):
            test_parts.append(test)
        if len(valid):
            valid_parts.append(valid)

    if not train_parts or not test_parts or not valid_parts:
        return np.array([], dtype=int), np.array([], dtype=int), np.array([], dtype=int)
    return np.concatenate(train_parts), np.concatenate(test_parts), np.concatenate(valid_parts)


def align_proba(probs: np.ndarray, classes: list[int] | np.ndarray) -> np.ndarray:
    aligned = np.zeros((len(probs), len(CLASS_LABELS)), dtype=float)
    class_list = [int(cls) for cls in classes]
    for idx, label in enumerate(CLASS_LABELS):
        if label in class_list:
            aligned[:, idx] = probs[:, class_list.index(label)]
    row_sum = aligned.sum(axis=1, keepdims=True)
    return aligned / np.where(row_sum == 0, 1.0, row_sum)


def metrics_from_probs(y: np.ndarray, probs: np.ndarray) -> dict[str, float]:
    pred = np.array(CLASS_LABELS)[np.argmax(probs, axis=1)]
    directional_mask = pred != 0
    if directional_mask.any():
        directional_accuracy = float((pred[directional_mask] == y[directional_mask]).mean())
    else:
        directional_accuracy = 0.0
    try:
        ll = float(log_loss(y, probs, labels=CLASS_LABELS))
    except ValueError:
        ll = float("nan")
    return {
        "accuracy": float(accuracy_score(y, pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "f1_macro": float(f1_score(y, pred, average="macro", zero_division=0)),
        "logloss": ll,
        "trade_coverage": float(directional_mask.mean()),
        "directional_accuracy": directional_accuracy,
    }


def make_lgbm() -> LGBMClassifier:
    return LGBMClassifier(
        n_estimators=500,
        learning_rate=0.035,
        max_depth=6,
        num_leaves=31,
        min_child_samples=40,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_alpha=0.2,
        reg_lambda=0.4,
        objective="multiclass",
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )


def make_catboost() -> Any:
    if CatBoostClassifier is None:
        return None
    return CatBoostClassifier(
        iterations=500,
        learning_rate=0.035,
        depth=6,
        loss_function="MultiClass",
        eval_metric="MultiClass",
        random_seed=42,
        verbose=False,
        allow_writing_files=False,
    )


def fit_hmm_regime(x_train_scaled: np.ndarray, output_dir: Path) -> str:
    if GaussianHMM is None or len(x_train_scaled) < 500:
        return ""
    subset = x_train_scaled[:, : min(8, x_train_scaled.shape[1])]
    model = GaussianHMM(n_components=4, covariance_type="diag", n_iter=100, random_state=42)
    model.fit(subset)
    path = output_dir / "regime_hmm.pkl"
    joblib.dump(model, path)
    return str(path)


def train_one_model(
    model_name: str,
    base_model: Any,
    symbol: str,
    timeframe: str,
    x: pd.DataFrame,
    y: pd.Series,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    valid_idx: np.ndarray,
    source_path: Path,
    output_root: Path,
    split_mode: str,
) -> list[TrainResult]:
    artifact_dir = output_root / symbol / timeframe / model_name
    artifact_dir.mkdir(parents=True, exist_ok=True)

    x_train, y_train = x.iloc[train_idx], y.iloc[train_idx].to_numpy()
    x_test, y_test = x.iloc[test_idx], y.iloc[test_idx].to_numpy()
    x_valid, y_valid = x.iloc[valid_idx], y.iloc[valid_idx].to_numpy()

    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_test_scaled = scaler.transform(x_test)
    x_valid_scaled = scaler.transform(x_valid)

    base_model.fit(x_train_scaled, y_train)
    classes = getattr(base_model, "classes_", CLASS_LABELS)
    probs_test = align_proba(base_model.predict_proba(x_test_scaled), classes)
    probs_valid = align_proba(base_model.predict_proba(x_valid_scaled), classes)

    hmm_path = fit_hmm_regime(x_train_scaled, artifact_dir)

    calibrators: list[tuple[str, Any, np.ndarray, np.ndarray]] = [("raw", None, probs_test, probs_valid)]
    if len(np.unique(y_test)) >= 2:
        logistic = LogisticProbabilityCalibrator().fit(probs_test, y_test)
        calibrators.append(("logistic", logistic, logistic.predict_proba(probs_test), logistic.predict_proba(probs_valid)))
        isotonic = IsotonicProbabilityCalibrator().fit(probs_test, y_test)
        calibrators.append(("isotonic", isotonic, isotonic.predict_proba(probs_test), isotonic.predict_proba(probs_valid)))

    results: list[TrainResult] = []
    for calibrator_name, calibrator, c_test, c_valid in calibrators:
        test_metrics = metrics_from_probs(y_test, c_test)
        valid_metrics = metrics_from_probs(y_valid, c_valid)
        model_dir = artifact_dir / calibrator_name
        model_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(base_model, model_dir / "model.pkl")
        joblib.dump(scaler, model_dir / "scaler.pkl")
        if calibrator is not None:
            joblib.dump(calibrator, model_dir / "calibrator.pkl")
        meta = {
            "symbol": symbol,
            "timeframe": timeframe,
            "model_name": model_name,
            "calibrator": calibrator_name,
            "classes": [int(cls) for cls in classes],
            "feature_columns": x.columns.tolist(),
            "split_mode": split_mode,
            "source_path": str(source_path),
            "hmm_regime_path": hmm_path,
            "training_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        (model_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        results.append(
            TrainResult(
                symbol=symbol,
                timeframe=timeframe,
                model_name=model_name,
                calibrator=calibrator_name,
                split_mode=split_mode,
                train_samples=len(train_idx),
                test_samples=len(test_idx),
                valid_samples=len(valid_idx),
                accuracy_test=test_metrics["accuracy"],
                balanced_accuracy_test=test_metrics["balanced_accuracy"],
                f1_macro_test=test_metrics["f1_macro"],
                logloss_test=test_metrics["logloss"],
                accuracy_valid=valid_metrics["accuracy"],
                balanced_accuracy_valid=valid_metrics["balanced_accuracy"],
                f1_macro_valid=valid_metrics["f1_macro"],
                logloss_valid=valid_metrics["logloss"],
                trade_coverage_valid=valid_metrics["trade_coverage"],
                directional_accuracy_valid=valid_metrics["directional_accuracy"],
                source_path=str(source_path),
                artifact_dir=str(model_dir),
            )
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Treina modelos de pesquisa por ativo/timeframe.")
    parser.add_argument("--config", default="config/fusion_config.yaml")
    parser.add_argument("--symbols", nargs="*", default=[])
    parser.add_argument("--timeframes", nargs="*", default=TIMEFRAMES)
    parser.add_argument("--parquet-dir", default="data/parquet")
    parser.add_argument("--output-dir", default="models_research")
    parser.add_argument("--report-dir", default="reports/research_models")
    parser.add_argument("--max-bars", type=int, default=0)
    parser.add_argument("--min-samples", type=int, default=800)
    parser.add_argument("--block-freq", default="M", help="M=mensal, W=semanal, Q=trimestral.")
    parser.add_argument("--embargo", type=int, default=2)
    parser.add_argument("--models", nargs="*", default=["lightgbm", "catboost"])
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    cfg = load_config(PROJECT_DIR / args.config)
    symbols = [s.upper() for s in (args.symbols or cfg.get("symbols", []))]
    if not args.symbols:
        strategy4_symbol = str(cfg.get("strategies", {}).get("strategy4", {}).get("symbol", "") or "").upper()
        if strategy4_symbol and strategy4_symbol not in symbols:
            symbols.append(strategy4_symbol)
    timeframes = [tf.upper() for tf in args.timeframes]
    parquet_dir = PROJECT_DIR / args.parquet_dir
    output_root = PROJECT_DIR / args.output_dir
    report_dir = PROJECT_DIR / args.report_dir
    output_root.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    all_results: list[TrainResult] = []
    progress: list[dict[str, Any]] = []
    jobs = [(symbol, tf) for symbol in symbols for tf in timeframes]
    if args.limit > 0:
        jobs = jobs[: args.limit]

    for symbol, timeframe in jobs:
        frame, source_path = load_parquet(symbol, timeframe, parquet_dir, args.max_bars)
        if frame is None or len(frame) < args.min_samples:
            progress.append({"symbol": symbol, "timeframe": timeframe, "status": "skipped", "message": "dados insuficientes/ausentes"})
            print(f"[SKIP] {symbol} {timeframe} | dados ausentes/insuficientes")
            continue
        features = calculate_features(frame)
        target = create_target(frame, horizon=TF_MAP[timeframe])
        common_idx = features.dropna().index.intersection(target.dropna().index)
        x = features.loc[common_idx]
        y = target.loc[common_idx]
        if len(x) < args.min_samples or y.nunique() < 2:
            progress.append({"symbol": symbol, "timeframe": timeframe, "status": "skipped", "message": f"samples={len(x)} classes={sorted(y.unique().tolist())}"})
            print(f"[SKIP] {symbol} {timeframe} | samples={len(x)} classes={sorted(y.unique().tolist())}")
            continue

        train_idx, test_idx, valid_idx = distributed_block_split(
            x.index,
            block_freq=args.block_freq,
            train_ratio=0.40,
            test_ratio=0.40,
            valid_ratio=0.20,
            embargo=args.embargo,
        )
        if min(len(train_idx), len(test_idx), len(valid_idx)) < 100:
            progress.append({"symbol": symbol, "timeframe": timeframe, "status": "skipped", "message": "split insuficiente"})
            print(f"[SKIP] {symbol} {timeframe} | split insuficiente")
            continue

        model_specs: list[tuple[str, Any]] = []
        if "lightgbm" in args.models:
            model_specs.append(("lightgbm", make_lgbm()))
        if "catboost" in args.models:
            cat = make_catboost()
            if cat is not None:
                model_specs.append(("catboost", cat))

        for model_name, model in model_specs:
            try:
                results = train_one_model(
                    model_name=model_name,
                    base_model=model,
                    symbol=symbol,
                    timeframe=timeframe,
                    x=x,
                    y=y,
                    train_idx=train_idx,
                    test_idx=test_idx,
                    valid_idx=valid_idx,
                    source_path=source_path,
                    output_root=output_root,
                    split_mode=f"distributed_blocks_{args.block_freq}_40_40_20_embargo{args.embargo}",
                )
                all_results.extend(results)
                best = max(results, key=lambda r: (r.f1_macro_valid, r.directional_accuracy_valid))
                print(
                    f"[OK] {symbol} {timeframe} {model_name} | "
                    f"valid_f1={best.f1_macro_valid:.3f} acc={best.accuracy_valid:.3f} "
                    f"cal={best.calibrator} samples={len(train_idx)}/{len(test_idx)}/{len(valid_idx)}"
                )
                progress.append({"symbol": symbol, "timeframe": timeframe, "model": model_name, "status": "trained", "message": ""})
            except Exception as exc:
                progress.append({"symbol": symbol, "timeframe": timeframe, "model": model_name, "status": "error", "message": f"{type(exc).__name__}: {exc}"})
                print(f"[ERROR] {symbol} {timeframe} {model_name} | {type(exc).__name__}: {exc}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if all_results:
        result_df = pd.DataFrame([asdict(item) for item in all_results])
        result_df = result_df.sort_values(
            ["symbol", "timeframe", "f1_macro_valid", "directional_accuracy_valid"],
            ascending=[True, True, False, False],
        )
        result_df.to_csv(report_dir / f"research_model_results_{timestamp}.csv", index=False)
        best_df = result_df.sort_values(
            ["symbol", "timeframe", "f1_macro_valid", "directional_accuracy_valid"],
            ascending=[True, True, False, False],
        ).groupby(["symbol", "timeframe"], as_index=False).head(1)
        best_df.to_csv(report_dir / f"research_model_best_{timestamp}.csv", index=False)
    pd.DataFrame(progress).to_csv(report_dir / f"research_model_progress_{timestamp}.csv", index=False)
    print(f"Resultados: {report_dir}")
    print(f"Modelos/calibradores avaliados: {len(all_results)}")


if __name__ == "__main__":
    main()
