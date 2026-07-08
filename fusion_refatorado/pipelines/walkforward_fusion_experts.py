from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score

from common import PROJECT_ROOT, infer_symbol_timeframe, load_market_frame, write_json

from backtest_fusion_experts import (
    CONTEXT_EXPERTS,
    DERIVED_DIRECTION_EXPERTS,
    DIRECTIONAL_EXPERTS,
    confidence_from_model,
    derive_reversal_direction,
    realized_return,
    score_for_weight,
    spread_cost,
    summarize_strategy,
)
from fusion_best.dataset_builder import normalize_ohlcv_columns
from fusion_best.expert_training import (
    DEFAULT_EXPERT_ORDER,
    EXPERT_SPECS,
    LIGHTGBM_EXPERT_PARAMS,
    build_expert_dataset_from_feature_frame,
    build_expert_feature_frame,
)


def temporal_split(dataset: pd.DataFrame, target_col: str, train_fraction: float) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    feature_cols = [col for col in dataset.columns if col != target_col]
    split = max(1, min(len(dataset) - 1, int(len(dataset) * train_fraction)))
    X_train = dataset.iloc[:split][feature_cols]
    X_test = dataset.iloc[split:][feature_cols]
    y_train = dataset.iloc[:split][target_col].astype(int)
    y_test = dataset.iloc[split:][target_col].astype(int)
    return X_train, X_test, y_train, y_test


def train_temporal_expert(X_train: pd.DataFrame, y_train: pd.Series, expert_name: str) -> Any:
    spec = EXPERT_SPECS[expert_name]
    if y_train.nunique() < 2:
        raise ValueError(f"Target com uma unica classe para {expert_name}")
    params = dict(spec.model_params or LIGHTGBM_EXPERT_PARAMS)
    if spec.objective == "binary":
        params["objective"] = "binary"
    else:
        params["objective"] = "multiclass"
        params.pop("num_class", None)
    model = lgb.LGBMClassifier(**params)
    model.fit(X_train, y_train)
    return model


def evaluate_temporal_expert(
    expert_name: str,
    frame: pd.DataFrame,
    feature_frame: pd.DataFrame,
    train_fraction: float,
    min_confidence: float,
    point_size: float,
    output_model_root: Path,
) -> tuple[dict[str, Any], pd.DataFrame]:
    spec = EXPERT_SPECS[expert_name]
    dataset = build_expert_dataset_from_feature_frame(feature_frame, expert_name)
    X_train, X_test, y_train, y_test = temporal_split(dataset, spec.target_column, train_fraction)
    model = train_temporal_expert(X_train, y_train, expert_name)
    pred = model.predict(X_test)
    confidence = confidence_from_model(model, X_test, pred)

    role = "context"
    direction = pd.Series(0, index=X_test.index, dtype=int)
    if expert_name in DIRECTIONAL_EXPERTS:
        role = "directional"
        direction = pd.Series(pred, index=X_test.index).astype(int)
    elif expert_name in DERIVED_DIRECTION_EXPERTS:
        role = "derived_directional"
        setup_direction = derive_reversal_direction(dataset.loc[X_test.index])
        direction = setup_direction.where(pd.Series(pred, index=X_test.index).astype(int) == 1, 0)
    elif expert_name in CONTEXT_EXPERTS:
        role = "context"

    def make_trades(signal_direction: pd.Series, mode: str) -> pd.DataFrame:
        ret = realized_return(frame["close"], spec.horizon).reindex(X_test.index)
        cost = spread_cost(frame, X_test.index, point_size)
        result = pd.DataFrame(
            {
                "expert": expert_name,
                "timestamp": X_test.index,
                "prediction": pred,
                "direction": signal_direction,
                "confidence": confidence,
                "realized_return": ret,
                "spread_cost": cost,
                "mode": mode,
            }
        ).dropna(subset=["realized_return"])
        result = result[(result["direction"] != 0) & (result["confidence"] >= min_confidence)].copy()
        result["net_return"] = result["direction"].astype(float) * result["realized_return"].astype(float) - result["spread_cost"].astype(float)
        result["win"] = (result["net_return"] > 0).astype(int)
        return result

    normal_trades = make_trades(direction, "NORMAL")
    inverted_trades = make_trades(direction * -1, "INVERT") if role in {"directional", "derived_directional"} else pd.DataFrame()
    normal_summary = summarize_strategy(normal_trades)
    inverted_summary = summarize_strategy(inverted_trades)
    chosen_mode = "NORMAL"
    if role in {"directional", "derived_directional"} and float(inverted_summary.get("total_return", 0.0)) > float(normal_summary.get("total_return", 0.0)):
        trades = inverted_trades
        chosen_mode = "INVERT"
    else:
        trades = normal_trades
        chosen_mode = "NORMAL"

    model_dir = output_model_root / expert_name
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / "model.pkl"
    metadata_path = model_dir / f"{expert_name}_metadata.json"
    joblib.dump(model, model_path)

    metrics = {
        "accuracy": float(accuracy_score(y_test, pred)),
        "f1_macro": float(f1_score(y_test, pred, average="macro")),
        "train_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "features": int(X_train.shape[1]),
    }
    write_json(
        metadata_path,
        {
            "expert": expert_name,
            "mode": "walkforward_temporal",
            "train_fraction": train_fraction,
            "feature_columns": X_train.columns.tolist(),
            "metrics": metrics,
            "spec": {key: value for key, value in spec.__dict__.items() if key != "target_builder"},
        },
    )

    summary = summarize_strategy(trades)
    summary.update(
        {
            "expert": expert_name,
            "role": role,
            "mode": chosen_mode,
            "normal_total_return": float(normal_summary.get("total_return", 0.0)),
            "inverted_total_return": float(inverted_summary.get("total_return", 0.0)) if not inverted_trades.empty else 0.0,
            "rows_train": int(len(X_train)),
            "rows_test": int(len(X_test)),
            "horizon": int(spec.horizon),
            "min_confidence": float(min_confidence),
            "classification_accuracy": metrics["accuracy"],
            "classification_f1_macro": metrics["f1_macro"],
            "model_path": str(model_path),
            "metadata_path": str(metadata_path),
        }
    )
    if role == "context":
        summary["active_ratio"] = float(np.mean(pred != 0)) if len(pred) else 0.0
        summary["mean_confidence"] = float(np.mean(confidence)) if len(confidence) else 0.0
    return summary, trades


def build_weight_table(summary: pd.DataFrame, min_trades: int) -> pd.DataFrame:
    result = summary.copy()
    result["calibration_score"] = result.apply(lambda row: score_for_weight(row.to_dict(), min_trades), axis=1)
    eligible = result[result["role"].isin(["directional", "derived_directional"])].copy()
    total = float(eligible["calibration_score"].sum())
    result["calibrated_weight"] = 0.0
    if total > 0:
        weights = eligible.set_index("expert")["calibration_score"] / total
        result["calibrated_weight"] = result["expert"].map(weights).fillna(0.0)
    return result.sort_values(["calibrated_weight", "calibration_score", "expert"], ascending=[False, False, True])


def main() -> None:
    parser = argparse.ArgumentParser(description="Train experts on past data and evaluate/calibrate them on future data.")
    parser.add_argument("--input", required=True, help="CSV or parquet with OHLCV data.")
    parser.add_argument("--symbol")
    parser.add_argument("--timeframe")
    parser.add_argument("--experts", default=",".join(DEFAULT_EXPERT_ORDER))
    parser.add_argument("--train-fraction", type=float, default=0.80)
    parser.add_argument("--min-confidence", type=float, default=0.55)
    parser.add_argument("--min-trades", type=int, default=30)
    parser.add_argument("--point-size", type=float, default=0.00001)
    parser.add_argument("--output-root", default=str(PROJECT_ROOT / "reports" / "fusion_walkforward"))
    parser.add_argument("--model-output-root", default=str(PROJECT_ROOT / "models" / "fusion_walkforward"))
    args = parser.parse_args()

    symbol, timeframe = infer_symbol_timeframe(args.input, args.symbol, args.timeframe)
    frame = normalize_ohlcv_columns(load_market_frame(args.input))
    feature_frame = build_expert_feature_frame(frame)
    expert_names = tuple(name.strip() for name in args.experts.split(",") if name.strip())
    output_root = Path(args.output_root) / symbol / timeframe
    model_root = Path(args.model_output_root) / symbol / timeframe
    output_root.mkdir(parents=True, exist_ok=True)

    summaries = []
    trade_frames = []
    for expert_name in expert_names:
        if expert_name not in EXPERT_SPECS:
            continue
        try:
            summary, trades = evaluate_temporal_expert(
                expert_name,
                frame,
                feature_frame,
                train_fraction=args.train_fraction,
                min_confidence=args.min_confidence,
                point_size=args.point_size,
                output_model_root=model_root,
            )
        except Exception as exc:
            summary = {"expert": expert_name, "status": "error", "error": str(exc), "calibrated_weight": 0.0}
            trades = pd.DataFrame()
        summaries.append(summary)
        if not trades.empty:
            trade_frames.append(trades)

    summary_frame = build_weight_table(pd.DataFrame(summaries), args.min_trades)
    trades_frame = pd.concat(trade_frames, ignore_index=True) if trade_frames else pd.DataFrame()
    summary_csv = output_root / "walkforward_summary.csv"
    trades_csv = output_root / "walkforward_trades.csv"
    weights_json = output_root / "walkforward_weights.json"
    summary_frame.to_csv(summary_csv, index=False)
    trades_frame.to_csv(trades_csv, index=False)
    weight_cols = [
        "expert",
        "role",
        "mode",
        "calibrated_weight",
        "calibration_score",
        "trades",
        "winrate",
        "avg_net_return",
        "total_return",
        "normal_total_return",
        "inverted_total_return",
        "sharpe_like",
        "max_drawdown",
        "classification_accuracy",
        "classification_f1_macro",
        "model_path",
        "metadata_path",
    ]
    existing_cols = [col for col in weight_cols if col in summary_frame.columns]
    write_json(
        weights_json,
        {
            "symbol": symbol,
            "timeframe": timeframe,
            "input": args.input,
            "train_fraction": args.train_fraction,
            "min_confidence": args.min_confidence,
            "min_trades": args.min_trades,
            "weights": summary_frame[existing_cols].replace({np.nan: None}).to_dict(orient="records"),
        },
    )
    print(f"summary: {summary_csv}")
    print(f"trades: {trades_csv}")
    print(f"weights: {weights_json}")


if __name__ == "__main__":
    main()
