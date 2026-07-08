from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from common import PROJECT_ROOT, infer_symbol_timeframe, load_market_frame, write_json

from fusion_best.dataset_builder import normalize_ohlcv_columns
from fusion_best.expert_training import EXPERT_SPECS, build_expert_dataset_from_feature_frame, build_expert_feature_frame


DIRECTIONAL_EXPERTS = {"trend", "orderflow", "sr", "pullback", "quant", "candles"}
DERIVED_DIRECTION_EXPERTS = {"reversal"}
CONTEXT_EXPERTS = {"risk", "volatility"}


def load_metadata(path: Path) -> dict[str, Any]:
    candidates = sorted(path.glob("*_metadata.json"))
    if not candidates:
        raise FileNotFoundError(f"Metadata ausente em {path}")
    return json.loads(candidates[0].read_text(encoding="utf-8"))


def confidence_from_model(model: Any, X: pd.DataFrame, pred: np.ndarray) -> np.ndarray:
    if not hasattr(model, "predict_proba"):
        return np.ones(len(pred), dtype=float)
    probs = model.predict_proba(X)
    classes = list(getattr(model, "classes_", []))
    confidence = []
    for i, value in enumerate(pred):
        try:
            class_idx = classes.index(value)
            confidence.append(float(probs[i, class_idx]))
        except ValueError:
            confidence.append(float(np.max(probs[i])))
    return np.asarray(confidence, dtype=float)


def realized_return(close: pd.Series, horizon: int) -> pd.Series:
    return close.shift(-horizon) / (close + 1e-12) - 1


def spread_cost(frame: pd.DataFrame, index: pd.Index, point_size: float) -> pd.Series:
    if "spread" not in frame.columns:
        return pd.Series(0.0, index=index)
    spread = frame["spread"].reindex(index).fillna(0).astype(float)
    close = frame["close"].reindex(index).replace(0, np.nan).ffill().bfill().astype(float)
    return (spread * point_size) / (close + 1e-12)


def derive_reversal_direction(dataset: pd.DataFrame) -> pd.Series:
    exhaustion = dataset.get("omnis_exhaustion_signal", pd.Series(0, index=dataset.index))
    divergence = dataset.get("omnis_bullish_divergence", 0) - dataset.get("omnis_bearish_divergence", 0)
    direction = np.sign(pd.Series(exhaustion, index=dataset.index) + pd.Series(divergence, index=dataset.index))
    return pd.Series(direction, index=dataset.index).replace(0, np.nan).fillna(0).astype(int)


def summarize_strategy(trades: pd.DataFrame) -> dict[str, float | int]:
    if trades.empty:
        return {
            "trades": 0,
            "winrate": 0.0,
            "avg_net_return": 0.0,
            "total_return": 0.0,
            "sharpe_like": 0.0,
            "max_drawdown": 0.0,
        }
    returns = trades["net_return"].astype(float)
    equity = (1.0 + returns).cumprod()
    drawdown = equity / equity.cummax() - 1.0
    return {
        "trades": int(len(trades)),
        "winrate": float((returns > 0).mean()),
        "avg_net_return": float(returns.mean()),
        "total_return": float(equity.iloc[-1] - 1.0),
        "sharpe_like": float(returns.mean() / (returns.std() + 1e-12) * np.sqrt(len(returns))),
        "max_drawdown": float(drawdown.min()),
    }


def score_for_weight(summary: dict[str, float | int], min_trades: int) -> float:
    trades = int(summary.get("trades", 0))
    if trades < min_trades:
        return 0.0
    total_return = float(summary.get("total_return", 0.0))
    if total_return <= 0:
        return 0.0
    avg_return = float(summary.get("avg_net_return", 0.0))
    winrate = float(summary.get("winrate", 0.0))
    sharpe = float(summary.get("sharpe_like", 0.0))
    score = max(avg_return, 0.0) * 10000.0 + max(winrate - 0.5, 0.0) + max(sharpe, 0.0) * 0.05
    return float(max(score, 0.0))


def backtest_expert(
    expert_name: str,
    expert_dir: Path,
    frame: pd.DataFrame,
    feature_frame: pd.DataFrame,
    oos_fraction: float,
    min_confidence: float,
    point_size: float,
) -> tuple[dict[str, Any], pd.DataFrame]:
    spec = EXPERT_SPECS[expert_name]
    metadata = load_metadata(expert_dir)
    model = joblib.load(expert_dir / "model.pkl")
    dataset = build_expert_dataset_from_feature_frame(feature_frame, expert_name)
    split = max(1, int(len(dataset) * (1.0 - oos_fraction)))
    test = dataset.iloc[split:].copy()
    feature_cols = [col for col in metadata.get("feature_columns", []) if col in test.columns]
    if not feature_cols:
        raise ValueError(f"Sem features alinhadas para {expert_name}")
    X = test[feature_cols]
    pred = model.predict(X)
    confidence = confidence_from_model(model, X, pred)

    direction = pd.Series(0, index=test.index, dtype=int)
    role = "context"
    if expert_name in DIRECTIONAL_EXPERTS:
        direction = pd.Series(pred, index=test.index).astype(int)
        role = "directional"
    elif expert_name in DERIVED_DIRECTION_EXPERTS:
        setup_direction = derive_reversal_direction(test)
        direction = setup_direction.where(pd.Series(pred, index=test.index).astype(int) == 1, 0)
        role = "derived_directional"

    ret = realized_return(frame["close"], spec.horizon).reindex(test.index)
    cost = spread_cost(frame, test.index, point_size)
    trades = pd.DataFrame(
        {
            "expert": expert_name,
            "timestamp": test.index,
            "prediction": pred,
            "direction": direction,
            "confidence": confidence,
            "realized_return": ret,
            "spread_cost": cost,
        }
    ).dropna(subset=["realized_return"])
    trades = trades[(trades["direction"] != 0) & (trades["confidence"] >= min_confidence)].copy()
    trades["net_return"] = trades["direction"].astype(float) * trades["realized_return"].astype(float) - trades["spread_cost"].astype(float)
    trades["win"] = (trades["net_return"] > 0).astype(int)

    summary = summarize_strategy(trades)
    summary.update(
        {
            "expert": expert_name,
            "role": role,
            "rows_oos": int(len(test)),
            "horizon": int(spec.horizon),
            "min_confidence": float(min_confidence),
            "metadata_path": str(next(expert_dir.glob("*_metadata.json"))),
            "model_path": str(expert_dir / "model.pkl"),
        }
    )
    if role == "context":
        summary["active_ratio"] = float(np.mean(pred != 0)) if len(pred) else 0.0
        summary["mean_confidence"] = float(np.mean(confidence)) if len(confidence) else 0.0
    return summary, trades


def build_weight_table(summary: pd.DataFrame, min_trades: int) -> pd.DataFrame:
    weighted = summary.copy()
    weighted["calibration_score"] = weighted.apply(lambda row: score_for_weight(row.to_dict(), min_trades), axis=1)
    directional = weighted[weighted["role"].isin(["directional", "derived_directional"])].copy()
    total = float(directional["calibration_score"].sum())
    weighted["calibrated_weight"] = 0.0
    if total > 0:
        weight_map = directional.set_index("expert")["calibration_score"] / total
        weighted["calibrated_weight"] = weighted["expert"].map(weight_map).fillna(0.0)
    return weighted.sort_values(["calibrated_weight", "calibration_score", "expert"], ascending=[False, False, True])


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest and calibrate Fusion expert weights on the last slice of one OHLCV file.")
    parser.add_argument("--input", required=True, help="CSV or parquet with OHLCV data.")
    parser.add_argument("--symbol")
    parser.add_argument("--timeframe")
    parser.add_argument("--experts-root", default=str(PROJECT_ROOT / "models" / "fusion_experts"))
    parser.add_argument("--output-root", default=str(PROJECT_ROOT / "reports" / "fusion_backtests"))
    parser.add_argument("--experts", default="")
    parser.add_argument("--oos-fraction", type=float, default=0.20)
    parser.add_argument("--min-confidence", type=float, default=0.55)
    parser.add_argument("--min-trades", type=int, default=30)
    parser.add_argument("--point-size", type=float, default=0.00001)
    args = parser.parse_args()

    symbol, timeframe = infer_symbol_timeframe(args.input, args.symbol, args.timeframe)
    frame = normalize_ohlcv_columns(load_market_frame(args.input))
    feature_frame = build_expert_feature_frame(frame)
    experts_root = Path(args.experts_root) / symbol / timeframe
    expert_names = [name.strip() for name in args.experts.split(",") if name.strip()]
    if not expert_names:
        expert_names = [path.name for path in sorted(experts_root.iterdir()) if (path / "model.pkl").exists()]

    summaries = []
    trade_frames = []
    for expert_name in expert_names:
        expert_dir = experts_root / expert_name
        if not (expert_dir / "model.pkl").exists() or expert_name not in EXPERT_SPECS:
            continue
        summary, trades = backtest_expert(
            expert_name,
            expert_dir,
            frame,
            feature_frame,
            oos_fraction=args.oos_fraction,
            min_confidence=args.min_confidence,
            point_size=args.point_size,
        )
        summaries.append(summary)
        if not trades.empty:
            trade_frames.append(trades)

    if not summaries:
        raise SystemExit(f"Nenhum expert valido encontrado em {experts_root}")

    summary_frame = build_weight_table(pd.DataFrame(summaries), args.min_trades)
    trades_frame = pd.concat(trade_frames, ignore_index=True) if trade_frames else pd.DataFrame()

    output_root = Path(args.output_root) / symbol / timeframe
    output_root.mkdir(parents=True, exist_ok=True)
    summary_csv = output_root / "expert_backtest_summary.csv"
    trades_csv = output_root / "expert_backtest_trades.csv"
    weights_json = output_root / "calibrated_weights.json"
    summary_frame.to_csv(summary_csv, index=False)
    trades_frame.to_csv(trades_csv, index=False)
    write_json(
        weights_json,
        {
            "symbol": symbol,
            "timeframe": timeframe,
            "input": args.input,
            "oos_fraction": args.oos_fraction,
            "min_confidence": args.min_confidence,
            "min_trades": args.min_trades,
            "weights": summary_frame[
                [
                    "expert",
                    "role",
                    "calibrated_weight",
                    "calibration_score",
                    "trades",
                    "winrate",
                    "avg_net_return",
                    "total_return",
                    "sharpe_like",
                    "max_drawdown",
                    "model_path",
                    "metadata_path",
                ]
            ].to_dict(orient="records"),
        },
    )
    print(f"summary: {summary_csv}")
    print(f"trades: {trades_csv}")
    print(f"weights: {weights_json}")


if __name__ == "__main__":
    main()
