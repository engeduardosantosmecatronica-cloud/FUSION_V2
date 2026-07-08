"""
Loader de ensembles aprovados do FUSION refatorado para o runtime atual.

Mantem a integracao isolada: o runtime chama `predict`, e este modulo cuida de
registry, modelos, features OMNIS e decisao ponderada.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import joblib
try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None
import numpy as np
import pandas as pd

from fusion.core.logger import get_logger

from fusion_refatorado.fusion_best.dataset_builder import normalize_ohlcv_columns
from fusion_refatorado.fusion_best.expert_training import build_expert_feature_frame


def timeframe_code(timeframe: str) -> int:
    if mt5 is None:
        raise RuntimeError("MetaTrader5 indisponivel para obter candles em tempo real")
    return {
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
    }[timeframe]


@dataclass
class EnsembleMember:
    expert: str
    model: Any
    feature_columns: list[str]
    weight: float
    mode: str
    role: str
    model_path: str


class ApprovedEnsembleModel:
    """Modelo de ensemble aprovado para um simbolo/timeframe."""

    def __init__(
        self,
        symbol: str,
        timeframe: str,
        members: list[EnsembleMember],
        min_score: float,
        bars: int,
    ):
        self.symbol = symbol.upper()
        self.timeframe = timeframe.upper()
        self.members = members
        self.min_score = float(min_score)
        self.bars = int(bars)
        self.logger = get_logger(f"ApprovedEnsemble_{self.symbol}_{self.timeframe}")

    def _market_frame(self, broker_symbol: str) -> pd.DataFrame:
        tf_code = timeframe_code(self.timeframe)
        rates = mt5.copy_rates_from_pos(broker_symbol, tf_code, 0, self.bars)
        if rates is None or len(rates) < 250:
            return pd.DataFrame()
        frame = pd.DataFrame(rates)
        frame["time"] = pd.to_datetime(frame["time"], unit="s")
        frame = frame.set_index("time").sort_index()
        return normalize_ohlcv_columns(frame)

    @staticmethod
    def _confidence(model: Any, row: pd.DataFrame, pred: int) -> float:
        if not hasattr(model, "predict_proba"):
            return 1.0
        probs = model.predict_proba(row)
        classes = list(getattr(model, "classes_", []))
        try:
            return float(probs[0, classes.index(pred)])
        except ValueError:
            return float(np.max(probs[0]))

    @staticmethod
    def _derive_reversal_direction(feature_frame: pd.DataFrame) -> pd.Series:
        exhaustion = feature_frame.get("omnis_exhaustion_signal", pd.Series(0, index=feature_frame.index))
        divergence = feature_frame.get("omnis_bullish_divergence", 0) - feature_frame.get("omnis_bearish_divergence", 0)
        direction = np.sign(pd.Series(exhaustion, index=feature_frame.index) + pd.Series(divergence, index=feature_frame.index))
        return pd.Series(direction, index=feature_frame.index).replace(0, np.nan).fillna(0).astype(int)

    @staticmethod
    def _direction(member: EnsembleMember, pred: int, feature_frame: pd.DataFrame) -> int:
        direction = int(pred)
        if member.role == "derived_directional":
            if int(pred) != 1:
                return 0
            setup_direction = ApprovedEnsembleModel._derive_reversal_direction(feature_frame).iloc[-1]
            direction = int(setup_direction)
        if member.mode.upper() == "INVERT":
            direction *= -1
        if direction > 0:
            return 1
        if direction < 0:
            return -1
        return 0

    def predict(self, broker_symbol: str) -> tuple[int, float, float, str]:
        frame = self._market_frame(broker_symbol)
        if frame.empty:
            return 0, 0.0, 0.0, "SEM_DADOS"

        try:
            feature_frame = build_expert_feature_frame(frame)
        except Exception as exc:
            self.logger.warning(f"Falha ao calcular features OMNIS {self.symbol} {self.timeframe}: {exc}")
            return 0, 0.0, 0.0, "ERRO_FEATURES"

        if feature_frame.empty:
            return 0, 0.0, 0.0, "SEM_FEATURES"

        buy_score = 0.0
        sell_score = 0.0
        active = []
        for member in self.members:
            missing = [col for col in member.feature_columns if col not in feature_frame.columns]
            if missing:
                self.logger.warning(
                    f"{self.symbol} {self.timeframe} {member.expert}: {len(missing)} features ausentes"
                )
                continue
            row = feature_frame[member.feature_columns].tail(1).replace([np.inf, -np.inf], np.nan)
            if row.isna().any(axis=None):
                continue
            raw_pred = int(member.model.predict(row)[0])
            direction = self._direction(member, raw_pred, feature_frame)
            if direction == 0:
                continue
            confidence = self._confidence(member.model, row, raw_pred)
            contribution = member.weight * confidence
            if direction > 0:
                buy_score += contribution
            else:
                sell_score += contribution
            active.append(f"{member.expert}:{direction}:{confidence:.3f}:w{member.weight:.3f}")

        if not active:
            return 0, 0.0, 0.0, "SEM_EXPERT_ATIVO"

        net_score = buy_score - sell_score
        if abs(net_score) < self.min_score:
            return 0, buy_score, sell_score, "NEUTRO"
        pred = 1 if net_score > 0 else 2
        return pred, buy_score, sell_score, ";".join(active)


class ApprovedEnsembleRegistry:
    """Carrega os ensembles aprovados para uso no runtime."""

    def __init__(
        self,
        registry_path: Path,
        min_member_weight: float = 0.25,
        min_score: float = 0.25,
        bars: int = 1200,
    ):
        self.registry_path = registry_path
        self.min_member_weight = float(min_member_weight)
        self.min_score = float(min_score)
        self.bars = int(bars)
        self.logger = get_logger("ApprovedEnsembleRegistry")
        self.models: dict[tuple[str, str], ApprovedEnsembleModel] = {}

    @staticmethod
    def _load_feature_columns(metadata_path: str | Path) -> list[str]:
        payload = json.loads(Path(metadata_path).read_text(encoding="utf-8"))
        return list(payload.get("feature_columns", []))

    def load(self) -> dict[tuple[str, str], ApprovedEnsembleModel]:
        if not self.registry_path.exists():
            self.logger.warning(f"Registry de ensembles aprovado ausente: {self.registry_path}")
            return {}

        payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        loaded = 0
        for item in payload.get("ensembles", []):
            symbol = str(item["symbol"]).upper()
            timeframe = str(item["timeframe"]).upper()
            ensemble_path = Path(item["ensemble_path"])
            if not ensemble_path.exists():
                self.logger.warning(f"Ensemble ausente: {ensemble_path}")
                continue
            ensemble = json.loads(ensemble_path.read_text(encoding="utf-8"))
            members: list[EnsembleMember] = []
            for member in ensemble.get("members", []):
                weight = float(member.get("weight") or 0.0)
                if weight < self.min_member_weight:
                    continue
                role = str(member.get("role", ""))
                if role == "context":
                    continue
                model_path = Path(member["model_path"])
                metadata_path = Path(member["metadata_path"])
                if not model_path.exists() or not metadata_path.exists():
                    self.logger.warning(f"Modelo/metadata ausente para {symbol} {timeframe}: {model_path}")
                    continue
                members.append(
                    EnsembleMember(
                        expert=str(member["expert"]),
                        model=joblib.load(model_path),
                        feature_columns=self._load_feature_columns(metadata_path),
                        weight=weight,
                        mode=str(member.get("mode", "NORMAL")),
                        role=role,
                        model_path=str(model_path),
                    )
                )
            if members:
                self.models[(symbol, timeframe)] = ApprovedEnsembleModel(
                    symbol=symbol,
                    timeframe=timeframe,
                    members=members,
                    min_score=self.min_score,
                    bars=self.bars,
                )
                loaded += 1

        self.logger.info(
            f"Ensembles aprovados carregados: {loaded} | min_member_weight={self.min_member_weight}"
        )
        return self.models
