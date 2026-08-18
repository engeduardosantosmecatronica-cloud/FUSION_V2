"""
FUSION_V2 - Main Entry Point
=============================
Sistema unificado com modelos por ATIVO/TIMEFRAME
"""

import sys
import time
import threading
import json
import csv
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

from fusion.core.config import get_config, FusionConfig
from fusion.core.contracts import apply_contract_override, contract_from_mt5_info
from fusion.core.enums import FusionEventType, OrderStatus
from fusion.core.engine_registry import FusionEngineRegistry
from fusion.core.event_logger import FusionEventLogger
from fusion.core.event_service import FusionEventService
from fusion.core.events import FusionEvent, FusionEventBus
from fusion.core.logger import get_logger, FusionLogger
from fusion.core.objects import FusionAccount, FusionOrder, FusionPosition, FusionSignal, FusionTick, FusionTrade
from fusion.data.pipeline import MT5Connector
from fusion.features.engine import FeatureEngine, AlphaMiner, RSI, EMA
from fusion.features.feature_calculator import FeatureCalculator
from fusion.features.ema_alignment import EMAAlignment
from fusion.features.market_structure import MarketStructureConfig, build_market_structure_features
from fusion.features.macro_flow import (
    MacroFlowConfig,
    aggregate_symbol_flow,
    currency_strength_from_flows,
    direction_to_prediction,
    split_forex_symbol,
    timeframe_flow,
)
from fusion.features.currency_strength import CurrencyStrengthConfig, build_currency_strength_map, direction_from_probs
from fusion.engines import (
    AIAdvisorConfig,
    AIAdvisorEngine,
    CalibrationConfig,
    ConfidenceCalibrationEngine,
    ConsensusConfig,
    ConsensusEngine,
    ContextEngine,
    ContextBrainConfig,
    ContextBrainEngine,
    ContextEngineConfig,
    EntryTimingConfig,
    EntryTimingEngine,
    ExecutionConfig,
    ExecutionEngine,
    FactorEngine,
    FeatureEngineeringConfig,
    FeatureEngineeringEngine,
    MarketBriefingConfig,
    MarketBriefingEngine,
    MetaModelConfig,
    MetaModelEnsembleEngine,
    OpportunityConfig,
    OpportunityEngine,
    MarketRegimeEngine,
    PortfolioExposureConfig,
    PortfolioExposureEngine,
    RegimeConfig,
    RiskConfig,
    RiskEngine,
    SessionConfig,
    SessionEngine,
    VolatilityConfig,
    VolatilityEngine,
)
from fusion.execution.controls import ExecutionControlService
from fusion.execution.trading import TradingExecutor
from fusion.execution.trailing import TrailingManager
from fusion.execution.oms import FusionOMS
from fusion.execution.oms_snapshot import OMSSnapshotWriter
from fusion.filters.swap_filter import evaluate_swap_filter
from fusion.approved_ensembles import ApprovedEnsembleRegistry
from fusion.runtime_control import RuntimeControl
from fusion.runtime_bootstrap import FusionRuntimeBootstrap
from fusion.mt5_decision_layers import MT5DecisionLayersExporter
from fusion.mt5_signal_panel import mt5_common_files_dir
from fusion.decision import (
    DecisionAuditLogger,
    DecisionAuditService,
    DecisionEvaluationService,
    DecisionEvent,
    DecisionOrchestrator,
    DecisionPolicy,
    DecisionResult,
    EngineOutput,
    SignalCandidate,
    build_xai_explanation,
)
from fusion.oms_service import FusionOMSService
from fusion.signal_loop import FusionSignalLoopService
from fusion.startup_service import FusionStartupService
from fusion.strategy.strategy_service import FusionStrategyService
from fusion.strategies import Estrategia1, Estrategia2, Estrategia3, Estrategia4, Estrategia5, Estrategia6, Estrategia7, Estrategia8, Estrategia9, Estrategia10, Estrategia11, Estrategia12, Estrategia13, Estrategia14, StrategyFeatures
from fusion.strategies.base import StrategyContext


from fusion.models.single_model import SingleModel
from fusion.models.model_loader import ModelLoader
from fusion.filters.signal_filters import SignalFilters
from fusion.core.symbol_manager import SymbolManager
from fusion.backtest.market_data import HistoricalMarketDataProvider
from fusion.historical.acceptance_engine import HistoricalPriceAcceptanceEngine
from fusion.historical import (
    PriceProfileEngine,
    ZoneDetector,
    HistoricalDecisionEngine,
    HistoricalRecencyEngine,
    HistoricalMTFContextEngine,
)
from fusion.utils import (
    normalized_signal_symbol,
    opposite_prediction,
    truthy_config_value,
    merge_policy_dicts,
    refresh_market_briefing,
)


class FusionV2:
    """Sistema principal FUSION_V2."""
    
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"
    
    def __init__(self):
        boot_started = time.perf_counter()
        self.logger = get_logger("FusionV2")
        self.logger.info(f"[BOOT] {datetime.now().isoformat(timespec='seconds')} | iniciando construcao do FusionV2")
        self.config = get_config()
        self.runtime_control = RuntimeControl()
        self.trading = TradingExecutor()
        self.trailing = TrailingManager()
        self.logger.info(f"[BOOT][TIMING] base runtime/trading/trailing prontos em {time.perf_counter() - boot_started:.3f}s")
        self.models: dict = None
        self.sync_dict: dict = None
        self.monitor_state: dict = {}
        self.actionable_signal_state: dict = {}
        self.final_signal_state: dict = {}
        self.decision_layers_state: dict = {}
        self.runtime_bootstrap = FusionRuntimeBootstrap(config=self.config, logger=self.logger)
        self.mt5_signal_panel, self.mt5_trade_zones, self.mt5_decision_layers = self.runtime_bootstrap.build_mt5_exporters()
        self.logger.info(f"[BOOT][TIMING] exportadores MT5 prontos em {time.perf_counter() - boot_started:.3f}s")
        self._last_execution_block_reason = ""
        self._last_market_structure_reason = ""
        self._last_market_structure_snapshot: dict = {}
        self._last_market_briefing_reason = ""
        self._correlation_matrix_cache: dict = {}
        self._correlation_matrix_path: Path | None = None
        self._correlation_matrix_mtime: float = 0.0
        self._macro_flow_cache: dict = {}
        self._macro_flow_cache_minute: str = ""
        self._decision_engine_outputs: list[EngineOutput] = []
        self._seen_deal_tickets: set[str] = set()
        self._active_signal_correlation_id = ""
        self.decision_orchestrator = self._build_decision_orchestrator()
        self.decision_evaluator = DecisionEvaluationService(
            decision_orchestrator=self.decision_orchestrator,
            logger=self.logger,
        )
        self.event_bus, self.event_logger, self._event_bus_async, self._event_bus_async_stop_timeout = self.runtime_bootstrap.build_event_bus()
        self.event_service = FusionEventService(
            event_bus=self.event_bus,
            logger=self.logger,
            async_mode=self._event_bus_async,
        )
        self.decision_audit_service = DecisionAuditService(
            config=self.config,
            logger=self.logger,
            decision_orchestrator=self.decision_orchestrator,
            publish_event=self.event_service.publish,
            decision_layers_state=self.decision_layers_state,
            active_signal_correlation_id_getter=lambda: self._active_signal_correlation_id,
        )
        if self._event_bus_async:
            self.event_bus.start_async()
        self.oms = FusionOMS()
        self.oms_snapshot_writer = self.runtime_bootstrap.build_oms_snapshot_writer()
        self.execution_controls = ExecutionControlService(
            config=self.config,
            runtime_control=self.runtime_control,
            logger=self.logger,
            cwd=Path.cwd(),
        )
        self.engine_registry = FusionEngineRegistry()
        
        # Inicializar delegados
        self.model_loader = ModelLoader(self.config, self.logger)
        self.signal_filters = SignalFilters(self.config, self.logger)
        self.symbol_manager = SymbolManager(self.config, self.logger, self.oms, self._publish_event)
        
        # Vincular estruturas internas aos delegados
        self.models = self.model_loader.models
        self.approved_models = self.model_loader.approved_models
        self.approved_tp_sl = self.model_loader.approved_tp_sl
        self.sync_dict = self.symbol_manager.sync_dict

        self.logger.info(f"[BOOT][TIMING] event bus/oms/registry prontos em {time.perf_counter() - boot_started:.3f}s")
        self.TIMEFRAMES = ["M5", "M15", "M30", "H1", "H4", "D1"]
        self.TF_MINUTES = {"M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440}
        self.TF_MAP = {
            "M5": 5, "M15": 15, "M30": 30,
            "H1": 60, "H4": 240, "D1": 1440
        }
        self.SETUPS = {}
        self.gold_penultimate_log: dict = {}
        self._last_strategy4_setup_reason = ""
        self._last_strategy4_setup_details = {}
        
        # Cache de features com TTL para distribuiÃ§Ã£o de processamento
        self.features_cache = {}  # {(symbol, tf): (features_df, timestamp)}
        self.features_cache_ttl = 55  # segundos (< 60 para renovar antes do minuto)
        self.features_cache_hits = 0  # EstatÃ­sticas
        self.features_cache_misses = 0  # EstatÃ­sticas

        # Cache compartilhado de candles/rates para evitar chamadas repetidas ao MT5
        self.rates_cache = {}  # {(symbol, tf, start_pos): (rates_df, timestamp, bars)}
        self.rates_cache_ttl = 55
        self.rates_cache_hits = 0
        self.rates_cache_misses = 0
        
        # Fila de processamento distribuÃ­do ao longo do minuto
        self.processing_queue = []  # [(symbol, tf), ...]
        self.processing_queue_initialized = False
        self.processing_cycle_started_at = 0.0
        self.processing_cycle_completed_at = 0.0
        self.cycle_order_symbols: set[str] = set()
        self.signal_loop_service = FusionSignalLoopService(self)
        self.startup_service = FusionStartupService(self)
        self.oms_service = FusionOMSService(self)
        self.strategy_service = FusionStrategyService(self)
        self.logger.info(f"[BOOT][TIMING] estruturas principais prontas em {time.perf_counter() - boot_started:.3f}s")
        
        self._trailing_stop_event: threading.Event | None = None
        self._trailing_thread: threading.Thread | None = None
        self.mt5 = mt5
        # Inicializar FeatureCalculator e EMAAlignment com dependências injetadas
        self.feature_calc = FeatureCalculator(self.config, self.logger, self.mt5)
        self.ema_alignment = EMAAlignment(self.config, self.logger, self.feature_calc)
        parquet_root = Path(__file__).resolve().parents[1] / "data" / "parquet"
        self.historical_market_provider = HistoricalMarketDataProvider(parquet_root, max_cache_items=32)
        # Historical engines (profile, zone, acceptance, recency, mtf, decision)
        self.historical_profile_engine = PriceProfileEngine()
        self.historical_zone_detector = ZoneDetector()
        self.historical_acceptance_engine = HistoricalPriceAcceptanceEngine(
            provider=self.historical_market_provider,
            base_dir=Path(__file__).resolve().parents[1],
            profile_engine=self.historical_profile_engine,
            zone_detector=self.historical_zone_detector,
        )
        self.historical_recency_engine = HistoricalRecencyEngine()
        self.historical_mtf_context_engine = HistoricalMTFContextEngine()
        self.historical_decision_engine = HistoricalDecisionEngine()
        self.strategy_features = StrategyFeatures(self.config, self.logger, self.feature_calc)
        self.strategy_runners = [
            Estrategia5(self),
            Estrategia1(self),
            Estrategia2(self),
            Estrategia3(self),
            Estrategia4(self),
            Estrategia6(self),
            Estrategia7(self),
            Estrategia8(self),
            Estrategia9(self),
            Estrategia10(self),
            Estrategia11(self),
            Estrategia12(self),
            Estrategia13(self),
            Estrategia14(self),
        ]
        self._register_core_engines()
        self.logger.info(f"[BOOT][TIMING] construcao completa do FusionV2 em {time.perf_counter() - boot_started:.3f}s")

    def _log_timing(self, label: str, started: float, extra: str = "") -> float:
        elapsed = time.perf_counter() - started
        suffix = f" | {extra}" if extra else ""
        self.logger.info(f"[TIMING] {datetime.now().isoformat(timespec='seconds')} | {label} | {elapsed:.3f}s{suffix}")
        return elapsed

    def _build_decision_orchestrator(self) -> DecisionOrchestrator:
        cfg = self.config.get("decision_engine", {}) or {}
        policy = DecisionPolicy(
            min_tradeability_score=float(cfg.get("min_tradeability_score", 0.55) or 0.55),
            max_conflict_score=float(cfg.get("max_conflict_score", 0.40) or 0.40),
            reduce_size_conflict_score=float(cfg.get("reduce_size_conflict_score", 0.25) or 0.25),
            min_direction_score=float(cfg.get("min_direction_score", 0.60) or 0.60),
            macro_alignment_guard_enabled=bool(cfg.get("macro_alignment_guard_enabled", True)),
            macro_alignment_min_tradeability=float(cfg.get("macro_alignment_min_tradeability", 0.60) or 0.60),
            macro_alignment_min_consensus=float(cfg.get("macro_alignment_min_consensus", 0.45) or 0.45),
            losing_positions_guard_enabled=bool(cfg.get("losing_positions_guard_enabled", True)),
            losing_positions_min_tradeability=float(cfg.get("losing_positions_min_tradeability", 0.68) or 0.68),
            extreme_breakout_guard_enabled=bool(cfg.get("extreme_breakout_guard_enabled", True)),
            extreme_breakout_min_tradeability=float(cfg.get("extreme_breakout_min_tradeability", 0.68) or 0.68),
            extreme_breakout_min_consensus=float(cfg.get("extreme_breakout_min_consensus", 0.55) or 0.55),
            stale_data_guard_enabled=bool(cfg.get("stale_data_guard_enabled", True)),
            fragile_structure_guard_enabled=bool(cfg.get("fragile_structure_guard_enabled", True)),
            fragile_structure_min_tradeability=float(cfg.get("fragile_structure_min_tradeability", 0.70) or 0.70),
            fragile_structure_min_consensus=float(cfg.get("fragile_structure_min_consensus", 0.50) or 0.50),
        )
        audit_logger = DecisionAuditLogger(
            log_dir=cfg.get("audit_log_dir", "logs/decision_audit"),
            enabled=bool(cfg.get("audit_enabled", True)),
        )
        return DecisionOrchestrator(policy=policy, audit_logger=audit_logger)

    def _publish_event(
        self,
        event_type: FusionEventType | str,
        data: dict,
        source: str = "FusionV2",
        correlation_id: str = "",
    ) -> None:
        self.event_service.publish(event_type, data, source=source, correlation_id=correlation_id)

    def stop_event_bus(self) -> None:
        if not getattr(self, "_event_bus_async", False):
            return
        pending = self.event_bus.pending_async_events()
        if pending:
            self.logger.info(f"[EVENT_BUS] Encerrando modo async | eventos_pendentes={pending}")
        self.event_bus.stop_async(timeout=getattr(self, "_event_bus_async_stop_timeout", 10.0))
        remaining = self.event_bus.pending_async_events()
        if remaining:
            self.logger.warning(f"[EVENT_BUS] Async encerrado com eventos pendentes: {remaining}")
        else:
            self.logger.info("[EVENT_BUS] Async encerrado com fila drenada")

    def _register_core_engines(self) -> None:
        core_engines = [
            ("decision_orchestrator", self.decision_orchestrator),
            ("event_bus", self.event_bus),
            ("event_logger", self.event_logger),
            ("oms", self.oms),
            ("oms_snapshot_writer", self.oms_snapshot_writer),
            ("trading_executor", self.trading),
            ("trailing_manager", self.trailing),
        ]
        for name, engine in core_engines:
            self.engine_registry.register(name, engine, enabled=True)
        
        optional_engines = [
            ("market_briefing", MarketBriefingEngine, "entry_filters.market_briefing.enabled"),
            ("meta_model_ensemble", MetaModelEnsembleEngine, "entry_filters.meta_model_ensemble.enabled"),
            ("market_regime", MarketRegimeEngine, "entry_filters.market_regime.enabled"),
            ("volatility_engine", VolatilityEngine, "entry_filters.volatility_engine.enabled"),
            ("session_context", SessionEngine, "entry_filters.session_context.enabled"),
            ("portfolio_exposure", PortfolioExposureEngine, "entry_filters.portfolio_exposure.enabled"),
            ("feature_engineering", FeatureEngineeringEngine, "entry_filters.feature_engineering.enabled"),
            ("factor_engine", FactorEngine, "entry_filters.factor_engine.enabled"),
            ("entry_timing", EntryTimingEngine, "entry_filters.entry_timing.enabled"),
            ("execution_engine", ExecutionEngine, "entry_filters.execution_engine.enabled"),
            ("risk_engine", RiskEngine, "entry_filters.risk_engine.enabled"),
            ("context_engine", ContextEngine, "entry_filters.context_engine.enabled"),
            ("context_brain", ContextBrainEngine, "entry_filters.context_brain.enabled"),
            ("confidence_calibration", ConfidenceCalibrationEngine, "entry_filters.confidence_calibration.enabled"),
            ("consensus_engine", ConsensusEngine, "entry_filters.consensus_engine.enabled"),
            ("opportunity_engine", OpportunityEngine, "entry_filters.opportunity_engine.enabled"),
            ("ai_advisor", AIAdvisorEngine, "entry_filters.ai_advisor.enabled"),
        ]
        
        enabled_count = 0
        for name, engine_cls, config_path in optional_engines:
            enabled = bool(self.config.get(config_path, False))
            if enabled:
                enabled_count += 1
            self.engine_registry.register(name, engine_cls, enabled=enabled)
        
        self._publish_event(
            FusionEventType.DASHBOARD_UPDATE,
            {"engine_registry": self.engine_registry.snapshot()},
            source="EngineRegistry",
        )

    def evaluate_candidate(self, candidate: SignalCandidate, context: dict | None = None, account: dict | None = None, portfolio: dict | None = None, audit: bool = True):
        """Avalia um `SignalCandidate` usando motores de fatores, estratégias e classificação de mercado,
        compõe os `EngineOutput` e executa o `DecisionOrchestrator`.
        Após a avaliação principal, opcionalmente complementa com a `HistoricalDecisionEngine` quando
        `decision_engine.historical_enabled` estiver ativo na configuração, registrando o output.
        """
        result = self.decision_evaluator.evaluate(candidate, context=context, account=account, portfolio=portfolio, audit=audit)

        try:
            hist_cfg = self.config.get("decision_engine", {}) or {}
            if bool(hist_cfg.get("historical_enabled", False)):
                # determine end index for historical queries
                bar_count = self.historical_market_provider.bar_count(candidate.symbol, candidate.timeframe)
                end_index = max(0, int(bar_count) - 1)
                lookback = int(self.config.get("entry_filters", {}).get("historical_price_acceptance", {}).get("lookback_bars", 80) or 80)

                acceptance = self.historical_acceptance_engine.evaluate(candidate.symbol, candidate.timeframe, end_index, lookback, use_profile=True)

                # build a simple DataFrame from recent bars for recency/mtf engines
                bars = self.historical_market_provider.get_bars(candidate.symbol, candidate.timeframe, end_index, lookback)
                rows = []
                for b in bars:
                    rows.append(
                        {
                            "time": getattr(b, "timestamp", None),
                            "open": getattr(b, "open", 0.0),
                            "high": getattr(b, "high", 0.0),
                            "low": getattr(b, "low", 0.0),
                            "close": getattr(b, "close", 0.0),
                            "volume": getattr(b, "volume", 0.0),
                        }
                    )
                import pandas as _pd
                frame = _pd.DataFrame(rows)

                recency = self.historical_recency_engine.evaluate(frame)
                mtf = self.historical_mtf_context_engine.evaluate({candidate.timeframe: frame})

                zone_type = None
                zone_low = None
                zone_high = None
                zone_ctx = acceptance.details.get("zone_context") if acceptance.details else None
                if isinstance(zone_ctx, dict) and zone_ctx.get("zones"):
                    zone = self.historical_zone_detector.current_zone(zone_ctx, acceptance.current_price)
                    if zone:
                        zone_type = zone.get("zone_type")
                        zone_low = zone.get("price_low")
                        zone_high = zone.get("price_high")

                hist_decision = self.historical_decision_engine.evaluate(
                    acceptance_status=acceptance.status,
                    zone_type=zone_type,
                    recent_bias=recency.get("recent_bias"),
                    mtf_alignment=mtf.get("alignment"),
                    price=acceptance.current_price,
                    zone_low=zone_low,
                    zone_high=zone_high,
                )

                # register as engine output for observability
                self._record_engine_output(
                    "historical_decision",
                    direction=(hist_decision.get("decision") or "NEUTRAL").upper(),
                    score=float(hist_decision.get("confidence", 0.0) or 0.0),
                    confidence=float(hist_decision.get("confidence", 0.0) or 0.0),
                    positive_factors=hist_decision.get("reasons", []),
                    features=hist_decision.get("details", {}),
                )

        except Exception as exc:
            self.logger.exception("Falha ao integrar historical decision engine: %s", exc)

        return result
    
    def initialize(self) -> bool:
        """Inicializa MT5 e carrega modelos."""
        return self.startup_service.initialize()

    def _current_configured_symbols(self) -> list[str]:
        symbols = self.execution_controls.current_configured_symbols()
        if not symbols and self.sync_dict:
            symbols = [str(item).upper() for item in self.sync_dict.values()]
        return sorted(set(symbols))

    def _operational_matrix_due(self, latest_path: Path, symbols: list[str]) -> tuple[bool, list[str], str]:
        return self.execution_controls.operational_matrix_due(latest_path, symbols)

    def _bootstrap_operational_target_matrix(self) -> None:
        self.execution_controls.bootstrap_operational_target_matrix()

    def _load_operational_target_matrix(self, path_value: str | Path | None = None) -> dict:
        return self.execution_controls.load_operational_target_matrix(path_value)

    def _refine_panel_signal(
        self,
        pred: int,
        p_buy: float,
        p_sell: float,
        symbol: str,
        timeframe: str,
        reason_parts: list[str],
    ) -> tuple[int, float, float, list[str]]:
        cfg = self.config.get("mt5_signal_panel.refined_display", {}) or {}
        if not bool(cfg.get("enabled", False)):
            return pred, p_buy, p_sell, reason_parts
        if pred not in (1, 2):
            return pred, p_buy, p_sell, reason_parts

        side = "BUY" if pred == 1 else "SELL"
        new_reasons = list(reason_parts)
        new_reasons.append(f"raw_signal:{side}")

        if bool(cfg.get("require_operational_matrix", True)):
            matrix_path = cfg.get("matrix_path") or self.config.get(
                "operational_target_matrix.latest_path",
                "reports/operational_target_matrix/operational_target_matrix_latest.json",
            )
            matrix = self._load_operational_target_matrix(matrix_path)
            assets = matrix.get("assets", {}) if isinstance(matrix.get("assets"), dict) else {}
            side_data = {}
            symbol_data = assets.get(str(symbol).upper(), {}) if isinstance(assets, dict) else {}
            if isinstance(symbol_data, dict):
                side_data = symbol_data.get(side, {}) or {}

            if not side_data:
                if bool(cfg.get("block_on_missing_matrix", True)):
                    new_reasons.append("panel_refined:matrix_missing")
                    return 0, p_buy, p_sell, new_reasons
                new_reasons.append("panel_refined:matrix_missing_shadow")
                return pred, p_buy, p_sell, new_reasons

            samples = int(float(side_data.get("samples", 0) or 0))
            min_samples = int(cfg.get("min_samples", 10) or 10)
            if samples < min_samples:
                if bool(cfg.get("block_on_low_samples", False)):
                    new_reasons.append(f"panel_refined:matrix_samples_low:{samples}")
                    return 0, p_buy, p_sell, new_reasons
                new_reasons.append(f"panel_refined:matrix_samples_low_shadow:{samples}")
                return pred, p_buy, p_sell, new_reasons

            best = side_data.get("best_tp_sl", {}) if isinstance(side_data.get("best_tp_sl"), dict) else {}
            if not best:
                if bool(cfg.get("block_on_missing_target_plan", False)):
                    new_reasons.append("panel_refined:matrix_target_plan_missing")
                    return 0, p_buy, p_sell, new_reasons
                new_reasons.append("panel_refined:matrix_target_plan_missing_shadow")
                return pred, p_buy, p_sell, new_reasons
            recommended = bool(best.get("recommended", False))
            if bool(cfg.get("require_recommended", True)) and not recommended:
                avg_points = best.get("avg_points", "")
                loss_streak = best.get("max_loss_streak", "")
                new_reasons.append(
                    f"panel_refined:matrix_not_recommended:avg={avg_points}:loss_streak={loss_streak}"
                )
                return 0, p_buy, p_sell, new_reasons

            tp = best.get("tp_net_points", "")
            sl = best.get("sl_net_points", "")
            win_rate = best.get("win_rate", "")
            new_reasons.append(f"panel_refined:matrix_ok:tp={tp}:sl={sl}:wr={win_rate}")

        return pred, p_buy, p_sell, new_reasons

    def _load_all_models(self):
        """Carrega todos os modelos por símbolo/timeframe."""
        self.model_loader.load_all_models()

    def _load_approved_ensembles(self):
        """Carrega ensembles M5 aprovados do FUSION refatorado em modo staging."""
        self.model_loader.load_approved_ensembles()

    def _load_approved_tp_sl(self) -> dict:
        """Carrega TP/SL otimizado por ativo/timeframe para strategy5."""
        return self.model_loader.load_approved_tp_sl()
    
    def _sync_symbols(self):
        """Sincroniza símbolos do broker."""
        self.symbol_manager.sync_symbols()

    def _sync_contract(self, sym_ia: str, broker_sym: str, overrides: dict | None = None) -> None:
        self.symbol_manager._sync_contract(sym_ia, broker_sym, overrides)

    def _refresh_oms_state(self) -> None:
        self.oms_service.refresh_state()
    
    def _strategy_config(self, strategy_name: str) -> dict:
        return self.strategy_service._strategy_config(strategy_name)

    def _strategy_enabled(self, strategy_name: str) -> bool:
        return self.strategy_service._strategy_enabled(strategy_name)

    def _strategy_magic(self, strategy_name: str, tf: str) -> int:
        return self.strategy_service._strategy_magic(strategy_name, tf)

    def _strategy_magic_group(self, strategy_name: str) -> list:
        return self.strategy_service._strategy_magic_group(strategy_name)

    def _system_magic_group(self) -> list:
        return self.strategy_service._system_magic_group()

    def _log_strategy_magic_map(self):
        return self.strategy_service._log_strategy_magic_map()

    def _strategy_cooldown(self, strategy_name: str) -> int:
        return self.strategy_service._strategy_cooldown(strategy_name)

    def _recent_close_cooldown_remaining(self, strategy_name: str, broker_sym: str, sym_ia: str, tf: str) -> int:
        return self.strategy_service._recent_close_cooldown_remaining(strategy_name, broker_sym, sym_ia, tf)

    def _approved_feature_row(self, sym_ia: str, tf: str) -> dict:
        return self.strategy_service._approved_feature_row(sym_ia, tf)

    def _strategy_prediction(self, strategy_name: str, pred: int) -> int:
        return self.strategy_service._strategy_prediction(strategy_name, pred)

    @staticmethod
    def _normalized_signal_symbol(symbol: str) -> str:
        return normalized_signal_symbol(symbol)

    @staticmethod
    def _opposite_prediction(pred: int) -> int:
        return opposite_prediction(pred)

    @staticmethod
    def _truthy_config_value(value) -> bool:
        return truthy_config_value(value)

    def _runtime_section(self, name: str) -> dict:
        try:
            return self.runtime_control.section(name)
        except Exception as exc:
            self.logger.warning(f"[RUNTIME_CONTROL] Falha ao ler secao {name}: {exc}")
            return {}

    @staticmethod
    def _merge_policy_dicts(base: dict | None, override: dict | None) -> dict:
        return merge_policy_dicts(base, override)

    def _symbol_timeframe_policy(self, symbol: str | None, timeframe: str | None) -> dict:
        policies = self._runtime_section("symbol_timeframe_policies")
        if not isinstance(policies, dict) or not policies:
            return {}

        symbol_key = self._normalized_signal_symbol(symbol or "")
        timeframe_key = str(timeframe or "").upper().strip()

        merged: dict = {}
        default_policy = policies.get("default")
        if isinstance(default_policy, dict):
            merged = self._merge_policy_dicts(merged, default_policy)

        symbol_policy = None
        for candidate in (symbol_key, symbol_key.upper() if symbol_key else ""):
            if candidate and isinstance(policies.get(candidate), dict):
                symbol_policy = policies.get(candidate)
                break
        if isinstance(symbol_policy, dict):
            merged = self._merge_policy_dicts(merged, symbol_policy)
            symbol_default = symbol_policy.get("default")
            if isinstance(symbol_default, dict):
                merged = self._merge_policy_dicts(merged, symbol_default)
            if timeframe_key:
                tf_policy = symbol_policy.get(timeframe_key)
                if isinstance(tf_policy, dict):
                    merged = self._merge_policy_dicts(merged, tf_policy)

        exact_key = f"{symbol_key}:{timeframe_key}" if symbol_key and timeframe_key else ""
        if exact_key and isinstance(policies.get(exact_key), dict):
            merged = self._merge_policy_dicts(merged, policies.get(exact_key))

        return merged

    def _runtime_symbol_allowed(self, symbol: str) -> tuple[bool, str]:
        symbol_key = self._normalized_signal_symbol(symbol)
        symbols_cfg = self._runtime_section("symbols")
        mode = str(symbols_cfg.get("mode", "exclude") or "exclude").lower()
        include = {self._normalized_signal_symbol(item) for item in (symbols_cfg.get("include", []) or [])}
        exclude = {self._normalized_signal_symbol(item) for item in (symbols_cfg.get("exclude", []) or [])}
        if symbol_key in exclude:
            return False, "runtime_symbol_excluded"
        if mode == "include" and include and symbol_key not in include:
            return False, "runtime_symbol_not_in_include"
        risk_cfg = self._runtime_section("risk_by_symbol").get(symbol_key, {}) or {}
        if risk_cfg and risk_cfg.get("allow_new_orders") is False:
            return False, "runtime_symbol_orders_disabled"
        return True, "runtime_symbol_allowed"

    def _apply_runtime_signal_thresholds(self, pred: int, p_buy: float, p_sell: float, symbol: str, timeframe: str):
        return self.signal_filters.apply_runtime_signal_thresholds(pred, p_buy, p_sell, symbol, timeframe)

    def _runtime_tp_sl_points(self, symbol: str, tp_points: int, sl_points: int) -> tuple[int, int, str]:
        symbol_key = self._normalized_signal_symbol(symbol)
        reason_parts: list[str] = []
        global_cfg = self._runtime_section("global_tp_sl")
        if bool(global_cfg.get("use_runtime_override", False)):
            original = (tp_points, sl_points)
            tp_points = int(global_cfg.get("tp_points", tp_points) or tp_points or 0)
            sl_points = int(global_cfg.get("sl_points", sl_points) or sl_points or 0)
            if original != (tp_points, sl_points):
                reason_parts.append("runtime_global_tp_sl")
        symbol_cfg = self._runtime_section("symbol_tp_sl").get(symbol_key, {}) or {}
        if symbol_cfg:
            original = (tp_points, sl_points)
            tp_points = int(symbol_cfg.get("tp_points", tp_points) or tp_points or 0)
            sl_points = int(symbol_cfg.get("sl_points", sl_points) or sl_points or 0)
            if original != (tp_points, sl_points):
                reason_parts.append(f"runtime_symbol_tp_sl:{symbol_key}")
        return int(tp_points or 0), int(sl_points or 0), ";".join(reason_parts)

    def _apply_signal_inversion(self, pred: int, p_buy: float, p_sell: float, symbol: str, timeframe: str):
        return self.signal_filters.apply_signal_inversion(pred, p_buy, p_sell, symbol, timeframe)

    def _apply_signal_override(self, pred: int, p_buy: float, p_sell: float, symbol: str, timeframe: str):
        return self.signal_filters.apply_signal_override(pred, p_buy, p_sell, symbol, timeframe)

    def _strategy_max_positions(self, strategy_name: str) -> int:
        return self.strategy_service._strategy_max_positions(strategy_name)

    def _position_limit_scope(self, strategy_name: str) -> str:
        return self.strategy_service._position_limit_scope(strategy_name)

    def _position_limit_any_direction(self, strategy_name: str) -> bool:
        return self.strategy_service._position_limit_any_direction(strategy_name)

    def _strategy_feature_candidate(self, strategy_name: str, sym_ia: str, tf: str, pred: int, broker_sym: str) -> dict:
        return self.strategy_features.get_feature_candidate(strategy_name, sym_ia, tf, pred, broker_sym)

    def _strategy2_feature_candidate(self, sym_ia: str, tf: str, pred: int, broker_sym: str) -> dict:
        return self.strategy_features.get_strategy2_candidate(sym_ia, tf, pred, broker_sym)

    def _is_gold_symbol(self, sym_ia: str) -> bool:
        return self.strategy_service._is_gold_symbol(sym_ia)

    def _strategy4_ema_alignment_ok(self, broker_sym: str, tf: str) -> bool:
        return self.strategy_service._strategy4_ema_alignment_ok(broker_sym, tf)

    def _symbol_point_value(self, broker_sym: str, sym_ia: str) -> float:
        overrides = self.config.get("data.point_values", {}) or {}
        for key in [broker_sym, sym_ia, str(broker_sym).upper(), str(sym_ia).upper()]:
            if key in overrides:
                try:
                    value = float(overrides[key])
                except (TypeError, ValueError):
                    value = 0.0
                if value > 0:
                    return value
        if mt5 is None:
            return 0.0
        info = mt5.symbol_info(broker_sym)
        if info is None and broker_sym != sym_ia:
            info = mt5.symbol_info(sym_ia)
        if info is None:
            return 0.0
        point = float(getattr(info, "point", 0.0) or 0.0)
        if point > 0:
            return point
        tick_size = float(getattr(info, "trade_tick_size", 0.0) or 0.0)
        return tick_size if tick_size > 0 else 0.0

    def _strategy_ema_alignment_ok(self, strategy_name: str, pred: int, broker_sym: str, sym_ia: str, tf: str) -> bool:
        return self.strategy_service._strategy_ema_alignment_ok(strategy_name, pred, broker_sym, sym_ia, tf)

    def _ema_lower_timeframes_direction_ok(
        self,
        strategy_name: str,
        pred: int,
        broker_sym: str,
        sym_ia: str,
        signal_tf: str,
        direction: str,
        periods: list[int],
        start_pos: int,
    ) -> bool:
        return self.ema_alignment.ema_lower_timeframes_direction_ok(
            strategy_name=strategy_name,
            pred=pred,
            broker_sym=broker_sym,
            sym_ia=sym_ia,
            signal_tf=signal_tf,
            direction=direction,
            periods=periods,
            start_pos=start_pos,
        )

    def _strategy_candle_price_confirmation_ok(self, strategy_name: str, pred: int, broker_sym: str, sym_ia: str, tf: str) -> bool:
        return self.strategy_service._strategy_candle_price_confirmation_ok(strategy_name, pred, broker_sym, sym_ia, tf)

    def _strategy4_insidebar_buy_allowed(self, broker_sym: str, sym_ia: str, tf: str) -> bool:
        return self.strategy_service._strategy4_insidebar_buy_allowed(broker_sym, sym_ia, tf)

    def _broker_symbol_to_base(self, broker_symbol: str) -> str:
        return self.sync_dict.get(broker_symbol, broker_symbol).upper()

    @staticmethod
    def _prediction_side(pred: int) -> str:
        if pred == 1:
            return "BUY"
        if pred == 2:
            return "SELL"
        return "NEUTRAL"

    def _record_engine_output(
        self,
        engine: str,
        direction: str = "NEUTRAL",
        score: float = 0.0,
        confidence: float = 0.0,
        state: str = "",
        positive_factors: list[str] | None = None,
        negative_factors: list[str] | None = None,
        warnings: list[str] | None = None,
        features: dict | None = None,
    ) -> None:
        self._decision_engine_outputs.append(
            EngineOutput(
                engine=engine,
                direction=direction,
                score=max(0.0, min(1.0, float(score or 0.0))),
                confidence=max(0.0, min(1.0, float(confidence or 0.0))),
                state=state,
                positive_factors=positive_factors or [],
                negative_factors=negative_factors or [],
                warnings=warnings or [],
                features=features or {},
            )
        )

    def _emit_gate_decision(
        self,
        strategy_name: str,
        sym_ia: str,
        tf: str,
        gate_name: str,
        passed: bool,
        reason: str = "",
    ) -> None:
        status = "PASS" if passed else "BLOCK"
        reason_text = str(reason or "ok").strip() or "ok"
        self.logger.info(
            f"[GATE] {status} {strategy_name.upper()} {sym_ia} {tf} gate={gate_name} reason={reason_text}"
        )

    def _run_gate_check(
        self,
        strategy_name: str,
        pred: int,
        broker_sym: str,
        sym_ia: str,
        tf: str,
        gate_name: str,
        check_fn,
    ) -> bool:
        passed = bool(check_fn())
        reason = self._last_execution_block_reason if not passed else "ok"
        self._emit_gate_decision(strategy_name, sym_ia, tf, gate_name, passed, reason)
        return passed

    @staticmethod
    def _engine_state_should_block(cfg: dict, output: EngineOutput) -> bool:
        """Decide se o estado do engine deve bloquear uma ordem.

        Comportamento padrão alterado para só considerar fatores negativos como bloqueadores
        quando o prejuízo flutuante em dólares for maior ou igual ao limite configurado
        (`max_floating_loss_money` em `cfg`). Isso atende à regra: não bloquear por muitas
        posições negativas/demais fatores a menos que drawdown (em $) exceda o limiar.
        """
        states = cfg.get("block_states", []) or []
        # se o usuário especificou estados explícitos, respeitamos isso, porém
        # não devemos bloquear apenas por contagem de posicoes negativas ('muitas_posicoes',
        # 'muitas_posicoes_negativas') quando o prejuizo flutuante em $ for menor que o limite.
        if states:
            normalized = {str(item).strip().lower() for item in states if str(item).strip()}
            state_in = str(output.state or "").strip().lower() in normalized
            if not state_in:
                return False
            # se estiver no conjunto de estados bloqueadores, checar excecoes por fatores
            try:
                money_limit = float(cfg.get("max_floating_loss_money", 70.0) or 70.0)
            except Exception:
                money_limit = 70.0
            floating_profit = float((output.features or {}).get("floating_profit", 0.0) or 0.0)
            floating_loss = max(0.0, -floating_profit)
            if floating_loss < money_limit:
                # filtrar fatores que nao devem bloquear
                neg = [str(item or "") for item in (output.negative_factors or [])]
                filtered = [f for f in neg if not (f.startswith("muitas_posicoes") or f.startswith("muitas_posicoes_negativas"))]
                # se apos filtrar nao houver fatores negativos remanescentes, nao bloqueia
                if not filtered:
                    return False
            return True

        # sem estados explicitados: por compatibilidade antiga, normalmente bloqueia se houver fatores negativos
        # mas agora só bloquearemos por fatores negativos se o prejuízo flutuante em $ >= limite config (default $70)
        try:
            money_limit = float(cfg.get("max_floating_loss_money", 70.0) or 70.0)
        except Exception:
            money_limit = 70.0
        floating_profit = float((output.features or {}).get("floating_profit", 0.0) or 0.0)
        floating_loss = max(0.0, -floating_profit)
        if floating_loss < money_limit:
            return False
        return bool(output.negative_factors)

    @staticmethod
    def _should_relax_filter_for_daytrade(cfg: dict | None, filter_name: str, timeframe: str | None = None, p_buy: float = 0.0, p_sell: float = 0.0) -> bool:
        if not cfg:
            return False
        if not bool(cfg.get("enabled", False)):
            return False
        timeframe = str(timeframe or "").upper()
        if timeframe not in {str(item).upper() for item in (cfg.get("timeframes", []) or [])}:
            return False
        if filter_name not in {str(item).strip() for item in (cfg.get("relax_filters", []) or [])}:
            return False
        try:
            edge = float(p_buy or 0.0) - float(p_sell or 0.0)
        except (TypeError, ValueError):
            edge = 0.0
        min_edge = float(cfg.get("strong_signal_edge", 0.12) or 0.12)
        return edge > min_edge + 1e-9

    def _historical_price_acceptance_check(self, strategy_name: str, pred: int, broker_sym: str, sym_ia: str, tf: str, p_buy: float = 0.0, p_sell: float = 0.0) -> bool:
        cfg = self._runtime_filter_config(
            "historical_price_acceptance",
            (getattr(self, "config", {}) or {}).get("entry_filters", {}).get("historical_price_acceptance", {}) or {},
            sym_ia,
            tf,
        )
        if not bool(cfg.get("enabled", True)):
            return True
        mode = str(cfg.get("mode", "block") or "block").lower()
        if mode == "shadow":
            return True

        symbol_for_check = self._normalized_signal_symbol(sym_ia) or str(sym_ia or broker_sym or "").upper()
        if not symbol_for_check:
            return True

        provider = getattr(self, "historical_market_provider", None)
        if provider is None:
            return True
        total = provider.bar_count(symbol_for_check, tf)
        if total <= 0:
            return True
        index = max(0, total - 1)
        result = self.historical_acceptance_engine.evaluate(symbol_for_check, tf, index, lookback=int(cfg.get("lookback_bars", 80) or 80))

        self._record_engine_output(
            engine="historical_price_acceptance",
            direction=self._prediction_side(pred),
            score=1.0 if result.status == "accepted" else 0.7 if result.status == "needs_validation" else 0.2,
            confidence=0.85 if result.status == "accepted" else 0.55 if result.status == "needs_validation" else 0.95,
            state="ok" if result.status == "accepted" else "needs_validation" if result.status == "needs_validation" else "blocked",
            positive_factors=["historical_price_in_domain"] if result.status == "accepted" else [],
            negative_factors=result.reasons if result.status == "rejected" else (["historical_price_needs_validation"] if result.status == "needs_validation" else []),
            warnings=[] if result.status == "accepted" else [result.status],
            features={
                "symbol": symbol_for_check,
                "timeframe": tf,
                "status": result.status,
                "current_price": result.current_price,
                "price_domain_low": result.price_domain_low,
                "price_domain_high": result.price_domain_high,
                "reasons": result.reasons,
            },
        )

        if result.status == "rejected":
            self._last_execution_block_reason = ";".join(result.reasons) or "historical_price_out_of_domain"
            return False
        if result.status == "needs_validation":
            self._last_execution_block_reason = "historical_price_needs_validation"
            if str(cfg.get("strict_mode", "soft") or "soft").lower() == "block":
                return False
            return True
        return True

    def _historical_decision_check(self, strategy_name: str, pred: int, broker_sym: str, sym_ia: str, tf: str, p_buy: float = 0.0, p_sell: float = 0.0) -> bool:
        cfg = self._runtime_filter_config(
            "historical_decision",
            (getattr(self, "config", {}) or {}).get("entry_filters", {}).get("historical_decision", {}) or {},
            sym_ia,
            tf,
        )
        if not bool(cfg.get("enabled", True)):
            return True
        mode = str(cfg.get("mode", "shadow") or "shadow").lower()

        # shadow mode only records diagnostics
        symbol_for_check = self._normalized_signal_symbol(sym_ia) or str(sym_ia or broker_sym or "").upper()
        if not symbol_for_check:
            return True

        provider = getattr(self, "historical_market_provider", None)
        if provider is None:
            return True
        total = provider.bar_count(symbol_for_check, tf)
        if total <= 0:
            return True
        index = max(0, total - 1)
        lookback = int(cfg.get("lookback_bars", 80) or 80)

        try:
            acceptance = self.historical_acceptance_engine.evaluate(symbol_for_check, tf, index, lookback, use_profile=True)

            bars = provider.get_bars(symbol_for_check, tf, index, lookback)
            rows = []
            for b in bars:
                rows.append(
                    {
                        "time": getattr(b, "timestamp", None),
                        "open": getattr(b, "open", 0.0),
                        "high": getattr(b, "high", 0.0),
                        "low": getattr(b, "low", 0.0),
                        "close": getattr(b, "close", 0.0),
                        "volume": getattr(b, "volume", 0.0),
                    }
                )
            import pandas as _pd
            frame = _pd.DataFrame(rows)
            recency = self.historical_recency_engine.evaluate(frame)
            mtf = self.historical_mtf_context_engine.evaluate({tf: frame})

            zone_type = None
            zone_low = None
            zone_high = None
            zone_ctx = acceptance.details.get("zone_context") if acceptance.details else None
            if isinstance(zone_ctx, dict) and zone_ctx.get("zones"):
                zone = self.historical_zone_detector.current_zone(zone_ctx, acceptance.current_price)
                if zone:
                    zone_type = zone.get("zone_type")
                    zone_low = zone.get("price_low")
                    zone_high = zone.get("price_high")

            hist_decision = self.historical_decision_engine.evaluate(
                acceptance_status=acceptance.status,
                zone_type=zone_type,
                recent_bias=recency.get("recent_bias"),
                mtf_alignment=mtf.get("alignment"),
                price=acceptance.current_price,
                zone_low=zone_low,
                zone_high=zone_high,
            )

            self._record_engine_output(
                engine="historical_decision_gate",
                direction=(hist_decision.get("decision") or "NEUTRAL").upper(),
                score=float(hist_decision.get("confidence", 0.0) or 0.0),
                confidence=float(hist_decision.get("confidence", 0.0) or 0.0),
                state="ok" if hist_decision.get("decision") in {"buy", "sell"} else "blocked",
                positive_factors=hist_decision.get("reasons", []),
                negative_factors=hist_decision.get("reasons", []) if hist_decision.get("decision") == "hold" else [],
                features={"acceptance_status": acceptance.status, "recency": recency, "mtf": mtf, "zone": {"type": zone_type, "low": zone_low, "high": zone_high}},
            )

            if hist_decision.get("decision") == "hold" and mode == "block":
                self._last_execution_block_reason = ";".join(hist_decision.get("reasons") or ["historical_decision_hold"]) or "historical_decision_hold"
                return False
            return True
        except Exception as exc:
            self.logger.exception("Falha no historical decision check: %s", exc)
            return True

    def _trend_direction_allowed(self, strategy_name: str, pred: int, broker_sym: str, sym_ia: str, tf: str) -> bool:
        cfg = self._runtime_filter_config(
            "trend_direction_guard",
            (getattr(self, "config", {}) or {}).get("entry_filters", {}).get("trend_direction_guard", {}) or {},
            sym_ia,
            tf,
        )
        # If not specified, default to enabled=True so the guard is active unless explicitly disabled
        if not bool(cfg.get("enabled", True)):
            return True
        if pred not in (1, 2):
            return True

        requested_timeframes = [str(item).upper() for item in (cfg.get("timeframes", ["M15", "H1", "H4"]) or ["M15", "H1", "H4"])]
        if not requested_timeframes:
            requested_timeframes = ["M15", "H1", "H4"]
        ordered = []
        seen = set()
        for item in requested_timeframes:
            if item == "CURRENT":
                item = str(tf).upper()
            if item not in seen:
                ordered.append(item)
                seen.add(item)
        if not ordered:
            ordered = [str(tf).upper()]

        votes = {"BUY": 0, "SELL": 0}
        total_simple_slope = 0.0
        bars = max(10, int(cfg.get("bars", 20) or 20))
        min_rows = max(3, int(cfg.get("min_rows", 5) or 5))
        local_timeframes = set(getattr(self, "TIMEFRAMES", ("M5", "M15", "M30", "H1", "H4", "D1")))
        for timeframe in ordered:
            if timeframe not in local_timeframes and timeframe not in {"CURRENT"}:
                continue
            frame = self.feature_calc.get_rates_frame(broker_sym, timeframe, bars, start_pos=0, min_rows=min_rows)
            if frame.empty or len(frame) < min_rows:
                continue
            close = pd.to_numeric(frame["close"], errors="coerce")
            ema_fast = close.ewm(span=int(cfg.get("ema_fast", 21) or 21), adjust=False).mean()
            ema_slow = close.ewm(span=int(cfg.get("ema_slow", 50) or 50), adjust=False).mean()
            if len(close) < 5:
                continue
            price = float(close.iloc[-1])
            fast = float(ema_fast.iloc[-1])
            slow = float(ema_slow.iloc[-1])
            lookback = max(2, min(10, len(close) - 1))
            fast_slope = float(ema_fast.iloc[-1] - ema_fast.iloc[-lookback])
            if price > fast > slow and fast_slope >= 0.0:
                votes["BUY"] += 1
            elif price < fast < slow and fast_slope <= 0.0:
                votes["SELL"] += 1
            else:
                # Fallback: simple slope over the available window for short frames
                try:
                    simple_slope = float(close.iloc[-1] - close.iloc[0])
                except Exception:
                    simple_slope = 0.0
                total_simple_slope += simple_slope
                if simple_slope > 0:
                    votes["BUY"] += 1
                elif simple_slope < 0:
                    votes["SELL"] += 1

        mode = str(cfg.get("mode", "block") or "block").lower()
        if mode == "shadow":
            return True

        # Primary vote check
        if pred == 1 and votes["SELL"] > votes["BUY"]:
            self._last_execution_block_reason = "trend_direction_contra:SELL>BUY"
            return False
        if pred == 2 and votes["BUY"] > votes["SELL"]:
            self._last_execution_block_reason = "trend_direction_contra:BUY>SELL"
            return False
        # Fallback: if aggregate simple slope across timeframes clearly contradicts the signal, block
        if total_simple_slope > 0 and pred == 2:
            self._last_execution_block_reason = "trend_direction_contra:aggregate_positive_slope"
            return False
        if total_simple_slope < 0 and pred == 1:
            self._last_execution_block_reason = "trend_direction_contra:aggregate_negative_slope"
            return False
        if not votes["BUY"] and not votes["SELL"]:
            return True
        return True

    def _runtime_filter_config(self, filter_name: str, base_cfg: dict, symbol: str | None = None, timeframe: str | None = None) -> dict:
        """Apply hot runtime overrides for entry filters without mutating YAML config."""
        cfg = dict(base_cfg or {})
        runtime_cfg = getattr(self, "runtime_control", {})
        # runtime_control may be a dict (tests) or an object with section()
        if hasattr(runtime_cfg, "section"):
            try:
                runtime_cfg = runtime_cfg.section("filters")
            except Exception:
                runtime_cfg = {}
        elif not isinstance(runtime_cfg, dict):
            runtime_cfg = {}
        specific = runtime_cfg.get(filter_name, {}) if isinstance(runtime_cfg, dict) else {}
        if isinstance(specific, dict):
            for key, value in specific.items():
                if value is not None:
                    cfg[key] = value

        mode_key = f"{filter_name}_mode"
        states_key = f"{filter_name}_block_states"
        if mode_key in runtime_cfg and runtime_cfg.get(mode_key) is not None:
            cfg["mode"] = runtime_cfg.get(mode_key)
        if states_key in runtime_cfg and isinstance(runtime_cfg.get(states_key), list):
            cfg["block_states"] = runtime_cfg.get(states_key)

        policy = self._symbol_timeframe_policy(symbol, timeframe)
        policy_filters = {}
        if isinstance(policy, dict):
            candidate = policy.get("filters", {})
            if isinstance(candidate, dict):
                policy_filters = candidate
        if isinstance(policy_filters, dict):
            exact_override = policy_filters.get(filter_name)
            if isinstance(exact_override, dict):
                for key, value in exact_override.items():
                    if value is not None:
                        cfg[key] = value
            required = {str(item).strip().lower() for item in (policy_filters.get("required_filters") or policy_filters.get("required") or []) if str(item).strip()}
            soft = {str(item).strip().lower() for item in (policy_filters.get("soft_filters") or policy_filters.get("soft") or []) if str(item).strip()}
            filter_key = str(filter_name).strip().lower()
            if filter_key in required:
                cfg["mode"] = "block"
            elif filter_key in soft:
                cfg["mode"] = "shadow"
        # Runtime control is the operator hot override and must win over YAML/policy defaults.
        if mode_key in runtime_cfg and runtime_cfg.get(mode_key) is not None:
            cfg["mode"] = runtime_cfg.get(mode_key)
        if states_key in runtime_cfg and isinstance(runtime_cfg.get(states_key), list):
            cfg["block_states"] = runtime_cfg.get(states_key)
        return cfg

    def _audit_decision_event(
        self,
        strategy_name: str,
        pred: int,
        broker_sym: str,
        sym_ia: str,
        tf: str,
        decision: str,
        reason: str,
        p_buy: float = 0.0,
        p_sell: float = 0.0,
        extra: dict | None = None,
        correlation_id: str = "",
    ) -> str:
        return self.decision_audit_service.audit_decision_event(
            strategy_name=strategy_name,
            pred=pred,
            broker_sym=broker_sym,
            sym_ia=sym_ia,
            tf=tf,
            decision=decision,
            reason=reason,
            p_buy=p_buy,
            p_sell=p_sell,
            extra=extra,
            correlation_id=correlation_id,
            decision_engine_outputs=self._decision_engine_outputs,
        )

    def _decision_engine_final_check(
        self,
        strategy_name: str,
        pred: int,
        broker_sym: str,
        sym_ia: str,
        tf: str,
        p_buy: float = 0.0,
        p_sell: float = 0.0,
        extra: dict | None = None,
    ) -> tuple[bool, DecisionResult | None]:
        cfg = self.config.get("decision_engine", {}) or {}
        if not bool(cfg.get("enabled", True)):
            return True, None
        if pred not in (1, 2):
            return True, None
        candidate = SignalCandidate(
            symbol=sym_ia.upper(),
            broker_symbol=broker_sym,
            timeframe=tf,
            side=self._prediction_side(pred),
            strategy=strategy_name,
            raw_prediction=pred,
            p_buy=float(p_buy or 0.0),
            p_sell=float(p_sell or 0.0),
        )
        policy_result = self.decision_orchestrator.policy.combine(candidate, self._decision_engine_outputs)
        return self.decision_audit_service.decision_engine_final_check(
            strategy_name=strategy_name,
            pred=pred,
            broker_sym=broker_sym,
            sym_ia=sym_ia,
            tf=tf,
            p_buy=p_buy,
            p_sell=p_sell,
            extra=extra,
            decision_engine_outputs=self._decision_engine_outputs,
            emit_gate_decision=self._emit_gate_decision,
        )

    @staticmethod
    def _dashboard_reason_key(part: str) -> str:
        text = str(part or "").strip()
        if not text:
            return ""
        if ":" in text:
            maybe_tag, rest = text.split(":", 1)
            if maybe_tag.upper().startswith("S") and maybe_tag[1:].isdigit():
                text = rest
        known_prefixes = [
            "macro_fluxo_contra",
            "correlacao_prejuizo",
            "preco_candle_nao_confirmado",
            "ema_nao_alinhada",
            "allow_new_orders_false",
            "market_structure_block",
            "market_briefing",
            "entry_timing",
            "MB:shadow",
            "portfolio_exposure",
            "ai_advisor",
            "context_engine",
            "confidence_calibration",
            "session_context",
            "volatility_engine",
            "sem_feature",
            "cooldown",
            "POSICAO_JA_EXISTE",
            "aguardando_setup",
            "setup_block",
            "sell_ignored",
        ]
        for prefix in known_prefixes:
            if text == prefix or text.startswith(prefix + ":"):
                return prefix
        if ":MS:shadow:" in part or text.startswith("MS:shadow:"):
            return "MS:shadow"
        return text.split(":", 1)[0]

    def _macro_flow_tf_code(self, tf: str):
        if mt5 is None:
            return None
        return {
            "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1
        }.get(str(tf).upper())

    def _macro_flow_rates(self, broker_sym: str, tf: str, bars: int) -> pd.DataFrame:
        frame = self.feature_calc.get_rates_frame(broker_sym, tf, bars, start_pos=0, min_rows=60)
        if frame.empty or len(frame) < 60:
            return pd.DataFrame()
        return frame

    def _market_regime_check(self, strategy_name: str, pred: int, broker_sym: str, sym_ia: str, tf: str) -> bool:
        cfg = self._runtime_filter_config("market_regime", self.config.get("entry_filters.market_regime", {}) or {}, sym_ia, tf)
        if not bool(cfg.get("enabled", False)):
            return True
        if mt5 is None:
            return True
        mode = str(cfg.get("mode", "shadow") or "shadow").lower()
        bars = max(120, int(cfg.get("bars", 260) or 260))
        frame = self._macro_flow_rates(broker_sym, tf, bars)
        engine = MarketRegimeEngine(
            RegimeConfig(
                atr_period=int(cfg.get("atr_period", 14) or 14),
                long_window=int(cfg.get("long_window", 100) or 100),
                adx_period=int(cfg.get("adx_period", 14) or 14),
                efficiency_window=int(cfg.get("efficiency_window", 20) or 20),
                entropy_window=int(cfg.get("entropy_window", 30) or 30),
                compression_threshold=float(cfg.get("compression_threshold", 0.75) or 0.75),
                expansion_threshold=float(cfg.get("expansion_threshold", 1.25) or 1.25),
                trend_adx_threshold=float(cfg.get("trend_adx_threshold", 22.0) or 22.0),
                range_adx_threshold=float(cfg.get("range_adx_threshold", 16.0) or 16.0),
                panic_atr_percentile=float(cfg.get("panic_atr_percentile", 0.95) or 0.95),
            )
        )
        output = engine.evaluate(frame, side=self._prediction_side(pred))
        self._decision_engine_outputs.append(output)
        if bool(cfg.get("log_each_check", False)):
            self.logger.info(
                f"{strategy_name.upper()} {sym_ia} {tf} regime {mode}: "
                f"state={output.state} direction={output.direction} score={output.score:.2f} "
                f"conf={output.confidence:.2f}"
            )
        if mode == "shadow":
            return True
        if output.state in {"PANIC_VOLATILITY", "ILLIQUID"}:
            self._last_execution_block_reason = f"regime_bloqueado:{output.state}"
            return False
        if output.conflicts_with(self._prediction_side(pred)) and output.confidence >= 0.65:
            self._last_execution_block_reason = f"regime_contra:{output.state}:{output.direction}"
            return False
        return True

    def _volatility_engine_check(
        self,
        strategy_name: str,
        broker_sym: str,
        sym_ia: str,
        tf: str,
        p_buy: float = 0.0,
        p_sell: float = 0.0,
    ) -> bool:
        cfg = self._runtime_filter_config("volatility_engine", self.config.get("entry_filters.volatility_engine", {}) or {}, sym_ia, tf)
        if not bool(cfg.get("enabled", False)):
            return True
        if mt5 is None:
            return True
        mode = str(cfg.get("mode", "shadow") or "shadow").lower()
        bars = max(130, int(cfg.get("bars", 180) or 180))
        frame = self._macro_flow_rates(broker_sym, tf, bars)
        engine = VolatilityEngine(
            VolatilityConfig(
                atr_period=int(cfg.get("atr_period", 14) or 14),
                short_window=int(cfg.get("short_window", 20) or 20),
                long_window=int(cfg.get("long_window", 100) or 100),
                compression_threshold=float(cfg.get("compression_threshold", 0.75) or 0.75),
                expansion_threshold=float(cfg.get("expansion_threshold", 1.25) or 1.25),
                panic_percentile=float(cfg.get("panic_percentile", 0.95) or 0.95),
                min_range_to_atr=float(cfg.get("min_range_to_atr", 0.55) or 0.55),
            )
        )
        output = engine.evaluate(frame)
        self._decision_engine_outputs.append(output)
        if bool(cfg.get("log_each_check", False)):
            self.logger.info(
                f"{strategy_name.upper()} {sym_ia} {tf} volatility_engine {mode}: "
                f"state={output.state} score={output.score:.2f} atr_pct={output.features.get('atr_percentile')}"
            )
        if mode == "shadow" or not self._engine_state_should_block(cfg, output):
            return True
        relax_cfg = self.config.get("entry_filters.daytrade_relaxation", {}) or {}
        if self._should_relax_filter_for_daytrade(relax_cfg, "volatility_engine", tf, p_buy, p_sell):
            self.logger.info(
                f"[DAYTRADE_RELAX] {strategy_name.upper()} {sym_ia} {tf} volatility_engine relaxed for strong short-term edge"
            )
            return True
        self._last_execution_block_reason = f"volatility_engine:{output.state}"
        return False

    def _session_context_check(self, strategy_name: str, pred: int, sym_ia: str, tf: str) -> bool:
        cfg = self._runtime_filter_config("session_context", self.config.get("entry_filters.session_context", {}) or {}, sym_ia, tf)
        if not bool(cfg.get("enabled", False)):
            return True
        mode = str(cfg.get("mode", "shadow") or "shadow").lower()
        engine = SessionEngine(
            SessionConfig(
                low_liquidity_start_hour_utc=int(cfg.get("low_liquidity_start_hour_utc", 21) or 21),
                low_liquidity_end_hour_utc=int(cfg.get("low_liquidity_end_hour_utc", 23) or 23),
                asian_start_hour_utc=int(cfg.get("asian_start_hour_utc", 0) or 0),
                asian_end_hour_utc=int(cfg.get("asian_end_hour_utc", 7) or 7),
                london_start_hour_utc=int(cfg.get("london_start_hour_utc", 7) or 7),
                london_end_hour_utc=int(cfg.get("london_end_hour_utc", 16) or 16),
                new_york_start_hour_utc=int(cfg.get("new_york_start_hour_utc", 12) or 12),
                new_york_end_hour_utc=int(cfg.get("new_york_end_hour_utc", 21) or 21),
                london_open_risk_minutes=int(cfg.get("london_open_risk_minutes", 20) or 20),
                new_york_open_risk_minutes=int(cfg.get("new_york_open_risk_minutes", 20) or 20),
                transition_risk_minutes=int(cfg.get("transition_risk_minutes", 15) or 15),
                friday_cutoff_hour_utc=int(cfg.get("friday_cutoff_hour_utc", 18) or 18),
                scalping_timeframes=tuple(str(item).upper() for item in cfg.get("scalping_timeframes", ["M5", "M15"]) or ["M5", "M15"]),
                asia_preferred_currencies=tuple(str(item).upper() for item in cfg.get("asia_preferred_currencies", ["JPY", "AUD", "NZD", "SGD"]) or ["JPY", "AUD", "NZD", "SGD"]),
                london_preferred_currencies=tuple(str(item).upper() for item in cfg.get("london_preferred_currencies", ["EUR", "GBP", "CHF"]) or ["EUR", "GBP", "CHF"]),
                new_york_preferred_currencies=tuple(str(item).upper() for item in cfg.get("new_york_preferred_currencies", ["USD", "CAD", "XAU"]) or ["USD", "CAD", "XAU"]),
                high_noise_symbols=tuple(str(item).upper() for item in cfg.get("high_noise_symbols", ["GOLD", "GBPJPY", "GBPNZD", "AUDSGD", "NZDSGD"]) or ["GOLD", "GBPJPY", "GBPNZD", "AUDSGD", "NZDSGD"]),
                session_scores={str(key): float(value) for key, value in (cfg.get("session_scores", {}) or {}).items()} or SessionConfig().session_scores,
            )
        )
        output = engine.evaluate(symbol=sym_ia, timeframe=tf, side=self._prediction_side(pred))
        self._decision_engine_outputs.append(output)
        if bool(cfg.get("log_each_check", False)):
            self.logger.info(
                f"{strategy_name.upper()} {sym_ia} {tf} session_context {mode}: "
                f"state={output.state} score={output.score:.2f}"
            )
        if mode == "shadow" or not output.negative_factors:
            return True
        self._last_execution_block_reason = f"session_context:{output.state}"
        return False

    def _macro_flow_config(self, cfg: dict, signal_tf: str = "") -> MacroFlowConfig:
        strength_cfg = cfg.get("currency_strength", {}) or {}
        tf_cfg = {}
        if signal_tf:
            tf_cfg = (cfg.get("by_signal_timeframe", {}) or {}).get(str(signal_tf).upper(), {}) or {}
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

    def _build_macro_flow_snapshot(self, cfg: dict, signal_tf: str = "") -> dict:
        minute_key = datetime.now().strftime("%Y%m%d%H%M")
        cache_key = f"{minute_key}:{str(signal_tf).upper()}"
        if self._macro_flow_cache_minute == cache_key and self._macro_flow_cache:
            return self._macro_flow_cache

        flow_cfg = self._macro_flow_config(cfg, signal_tf)
        symbols = {}
        for broker_sym, sym_ia in self.sync_dict.items():
            tf_results = {}
            for tf in flow_cfg.timeframes:
                frame = self._macro_flow_rates(broker_sym, tf, flow_cfg.bars)
                tf_results[tf] = timeframe_flow(frame, flow_cfg)
            aggregate = aggregate_symbol_flow(tf_results, flow_cfg)
            symbols[sym_ia.upper()] = {
                "broker_symbol": broker_sym,
                "score": aggregate["score"],
                "direction": aggregate["direction"],
                "reason": aggregate["reason"],
                "timeframes": tf_results,
            }

        symbol_scores = {symbol: float(data.get("score", 0.0)) for symbol, data in symbols.items()}
        strengths = currency_strength_from_flows(symbol_scores)
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "signal_timeframe": str(signal_tf).upper(),
            "aggregation": flow_cfg.aggregation,
            "symbols": symbols,
            "currency_strength": strengths,
        }
        self._macro_flow_cache = snapshot
        self._macro_flow_cache_minute = cache_key
        return snapshot

    def _macro_flow_gate(self, strategy_name: str, pred: int, sym_ia: str, tf: str, p_buy: float = 0.0, p_sell: float = 0.0) -> bool:
        cfg = self._runtime_filter_config("macro_flow", self.config.get("entry_filters.macro_flow", {}) or {}, sym_ia, tf)
        if not bool(cfg.get("enabled", False)):
            return True
        if pred not in (1, 2):
            return True
        if mt5 is None:
            return True

        mode = str(cfg.get("mode", "shadow") or "shadow").lower()
        flow_cfg = self._macro_flow_config(cfg, tf)
        snapshot = self._build_macro_flow_snapshot(cfg, tf)
        symbol = sym_ia.upper()
        symbol_flow = snapshot.get("symbols", {}).get(symbol, {})
        symbol_score = float(symbol_flow.get("score", 0.0) or 0.0)
        macro_score = symbol_score
        reasons = []

        parsed = split_forex_symbol(symbol)
        strength_cfg = cfg.get("currency_strength", {}) or {}
        if parsed and flow_cfg.currency_strength_enabled:
            base, quote = parsed
            strengths = snapshot.get("currency_strength", {})
            base_strength = float(strengths.get(base, 0.0) or 0.0)
            quote_strength = float(strengths.get(quote, 0.0) or 0.0)
            pair_strength = base_strength - quote_strength
            macro_score = ((1.0 - flow_cfg.currency_strength_weight) * symbol_score) + (
                flow_cfg.currency_strength_weight * pair_strength
            )
            macro_score = max(-1.0, min(1.0, macro_score))
            symbol_flow["base_strength"] = base_strength
            symbol_flow["quote_strength"] = quote_strength
            symbol_flow["pair_strength"] = pair_strength

        wanted_direction = "BUY" if pred == 1 else "SELL"
        macro_direction = "BUY" if macro_score > flow_cfg.min_score else "SELL" if macro_score < -flow_cfg.min_score else "NEUTRO"
        macro_pred = direction_to_prediction(macro_direction)
        if macro_pred == 0:
            reasons.append("macro_neutro")
        elif macro_pred != pred:
            reasons.append(f"macro_contra:{macro_direction}")

        reason_code = str(cfg.get("reason_code", "macro_fluxo_contra") or "macro_fluxo_contra")
        if bool(cfg.get("log_each_check", True)):
            vote_text = ""
            if "bullish_weight" in symbol_flow:
                vote_text = (
                    f" votos_alta={float(symbol_flow.get('bullish_weight', 0.0)):.1f}"
                    f" votos_baixa={float(symbol_flow.get('bearish_weight', 0.0)):.1f}"
                    f" peso_total={float(symbol_flow.get('total_weight', 0.0)):.1f}"
                )
            self.logger.info(
                f"{strategy_name.upper()} {symbol} {tf} {wanted_direction} macro_flow {mode}: "
                f"score={macro_score:.3f} direction={macro_direction}{vote_text} "
                f"reasons={','.join(reasons or ['ok'])}"
            )

        engine_direction = "NEUTRAL" if macro_direction == "NEUTRO" else macro_direction
        self._record_engine_output(
            engine="macro_flow",
            direction=engine_direction,
            score=abs(macro_score),
            confidence=abs(macro_score),
            state=macro_direction,
            positive_factors=[] if reasons else [f"macro_alinhado:{macro_direction}"],
            negative_factors=reasons,
            features={
                "macro_score": macro_score,
                "symbol_score": symbol_score,
                "signal_timeframe": tf,
                "aggregation": snapshot.get("aggregation", ""),
                "bullish_weight": symbol_flow.get("bullish_weight"),
                "bearish_weight": symbol_flow.get("bearish_weight"),
                "total_weight": symbol_flow.get("total_weight"),
            },
        )
        if not reasons:
            return True
        if mode == "shadow":
            return True
        relax_cfg = self.config.get("entry_filters.daytrade_relaxation", {}) or {}
        if self._should_relax_filter_for_daytrade(relax_cfg, "macro_flow", tf, p_buy, p_sell):
            self.logger.info(
                f"[DAYTRADE_RELAX] {strategy_name.upper()} {sym_ia} {tf} macro_flow relaxed for strong short-term edge"
            )
            return True
        self._last_execution_block_reason = f"{reason_code}:{'+'.join(reasons)}:score={macro_score:.3f}"
        return False

    def _market_alignment_check(
        self,
        strategy_name: str,
        pred: int,
        broker_sym: str,
        sym_ia: str,
        tf: str,
        p_buy: float = 0.0,
        p_sell: float = 0.0,
    ) -> bool:
        cfg = self._runtime_filter_config(
            "market_alignment",
            self.config.get("entry_filters.market_alignment", {}) or {},
            sym_ia,
            tf,
        )
        if not bool(cfg.get("enabled", False)):
            return True
        if pred not in (1, 2):
            return True
        if mt5 is None:
            return True

        mode = str(cfg.get("mode", "shadow") or "shadow").lower()
        side = self._prediction_side(pred)
        snapshot = self._market_alignment_snapshot(broker_sym, sym_ia, tf, side, cfg)
        state = snapshot["state"]
        reasons = list(snapshot["reasons"])
        direction = snapshot["market_direction"]
        score = float(snapshot["alignment_score"])
        confidence = float(snapshot["confidence"])

        self._record_engine_output(
            engine="market_alignment",
            direction=direction,
            score=abs(score),
            confidence=confidence,
            state=state,
            positive_factors=[] if reasons else [f"fluxo_alinhado:{direction}"],
            negative_factors=reasons,
            warnings=list(snapshot["warnings"]),
            features=snapshot,
        )
        if bool(cfg.get("write_monitor_log", True)):
            self._write_market_alignment_log(strategy_name, pred, sym_ia, tf, p_buy, p_sell, snapshot)
        if bool(cfg.get("log_each_check", False)) and state != "aligned":
            self.logger.info(
                f"{strategy_name.upper()} {sym_ia} {tf} market_alignment {mode}: "
                f"side={side} state={state} market={direction} "
                f"score={score:.3f} structural={float(snapshot['structural_score']):.3f} "
                f"reasons={','.join(reasons or ['ok'])}"
            )

        if mode == "shadow":
            return True
        relax_cfg = self.config.get("entry_filters.daytrade_relaxation", {}) or {}
        if self._should_relax_filter_for_daytrade(relax_cfg, "market_alignment", tf, p_buy, p_sell):
            self.logger.info(
                f"[DAYTRADE_RELAX] {strategy_name.upper()} {sym_ia} {tf} market_alignment relaxed for strong short-term edge"
            )
            return True
        if not self._engine_state_should_block(cfg, self._decision_engine_outputs[-1]):
            return True
        reason_code = str(cfg.get("reason_code", "market_alignment") or "market_alignment")
        self._last_execution_block_reason = f"{reason_code}:{state}:{'+'.join(reasons or ['desalinhado'])}:score={score:.3f}"
        return False

    def _timeframe_consensus_check(
        self,
        strategy_name: str,
        pred: int,
        broker_sym: str,
        sym_ia: str,
        tf: str,
        p_buy: float = 0.0,
        p_sell: float = 0.0,
    ) -> bool:
        cfg = self._runtime_filter_config(
            "timeframe_consensus",
            self.config.get("entry_filters.timeframe_consensus", {}) or {},
            sym_ia,
            tf,
        )
        if not bool(cfg.get("enabled", False)):
            return True
        if pred not in (1, 2):
            return True

        mode = str(cfg.get("mode", "shadow") or "shadow").lower()
        side = self._prediction_side(pred)
        snapshot = self._timeframe_consensus_snapshot(sym_ia, tf, side, p_buy, p_sell, cfg)
        state = snapshot["state"]
        reasons = list(snapshot["reasons"])
        consensus_direction = snapshot["consensus_direction"]
        score = float(snapshot["consensus_score"])
        alignment = float(snapshot["alignment_score"])
        confidence = float(snapshot["confidence"])

        self._record_engine_output(
            engine="timeframe_consensus",
            direction=consensus_direction,
            score=abs(score),
            confidence=confidence,
            state=state,
            positive_factors=[] if reasons else [f"consenso_alinhado:{consensus_direction}"],
            negative_factors=reasons,
            warnings=list(snapshot["warnings"]),
            features=snapshot,
        )
        if bool(cfg.get("log_each_check", False)) and state != "aligned":
            self.logger.info(
                f"{strategy_name.upper()} {sym_ia} {tf} timeframe_consensus {mode}: "
                f"side={side} state={state} consensus={consensus_direction} "
                f"score={score:.3f} alignment={alignment:.3f} "
                f"structural={float(snapshot['structural_score']):.3f} "
                f"valid={int(snapshot['valid_timeframes'])} "
                f"reasons={','.join(reasons or ['ok'])}"
            )

        if mode == "shadow":
            return True
        relax_cfg = self.config.get("entry_filters.daytrade_relaxation", {}) or {}
        if self._should_relax_filter_for_daytrade(relax_cfg, "timeframe_consensus", tf, p_buy, p_sell):
            self.logger.info(
                f"[DAYTRADE_RELAX] {strategy_name.upper()} {sym_ia} {tf} timeframe_consensus relaxed for strong short-term edge"
            )
            return True
        if not self._engine_state_should_block(cfg, self._decision_engine_outputs[-1]):
            return True
        reason_code = str(cfg.get("reason_code", "timeframe_consensus") or "timeframe_consensus")
        self._last_execution_block_reason = f"{reason_code}:{state}:{'+'.join(reasons or ['sem_consenso'])}:score={alignment:.3f}"
        return False

    def _timeframe_consensus_snapshot(
        self,
        sym_ia: str,
        signal_tf: str,
        side: str,
        current_p_buy: float,
        current_p_sell: float,
        cfg: dict,
    ) -> dict:
        tf_names = ["M5", "M15", "M30", "H1", "H4", "D1"]
        weights_cfg = cfg.get("timeframe_weights", {}) or {}
        weights = {
            "M5": float(weights_cfg.get("M5", 0.50) or 0.50),
            "M15": float(weights_cfg.get("M15", 0.75) or 0.75),
            "M30": float(weights_cfg.get("M30", 1.00) or 1.00),
            "H1": float(weights_cfg.get("H1", 1.50) or 1.50),
            "H4": float(weights_cfg.get("H4", 2.50) or 2.50),
            "D1": float(weights_cfg.get("D1", 3.00) or 3.00),
        }
        wait_edge = float(cfg.get("wait_edge", 0.08) or 0.08)
        signal_tf = str(signal_tf or "").upper()
        symbol = str(sym_ia or "").upper()
        labels: dict[str, str] = {}
        scores: dict[str, float | None] = {}
        edges: dict[str, float | None] = {}
        valid_timeframes = 0
        weighted_total = 0.0
        weighted_score_total = 0.0
        buy_weight = 0.0
        sell_weight = 0.0
        wait_weight = 0.0

        for tf_name in tf_names:
            if tf_name == signal_tf:
                p_buy = float(current_p_buy or 0.0)
                p_sell = float(current_p_sell or 0.0)
                status = "current"
            else:
                state = self.monitor_state.get((symbol, tf_name), {}) or {}
                p_buy = state.get("p_buy")
                p_sell = state.get("p_sell")
                status = str(state.get("status", "") or "")
            try:
                p_buy_f = float(p_buy)
                p_sell_f = float(p_sell)
            except (TypeError, ValueError):
                labels[tf_name] = "SEM_DADOS"
                scores[tf_name] = None
                edges[tf_name] = None
                continue
            if status.startswith("SEM_MODELO") or (p_buy_f == 0.0 and p_sell_f == 0.0):
                labels[tf_name] = "SEM_DADOS"
                scores[tf_name] = None
                edges[tf_name] = None
                continue

            edge = max(-1.0, min(1.0, p_buy_f - p_sell_f))
            if abs(edge) < wait_edge:
                label = "WAIT"
                score = 0.0
                wait_weight += weights[tf_name]
            elif edge > 0:
                label = "BUY"
                score = edge
                buy_weight += weights[tf_name] * abs(score)
            else:
                label = "SELL"
                score = edge
                sell_weight += weights[tf_name] * abs(score)
            labels[tf_name] = label
            scores[tf_name] = score
            edges[tf_name] = edge
            valid_timeframes += 1
            weighted_total += weights[tf_name]
            weighted_score_total += score * weights[tf_name]

        consensus_score = weighted_score_total / weighted_total if weighted_total else 0.0
        consensus_direction = "BUY" if consensus_score > 0 else "SELL" if consensus_score < 0 else "NEUTRAL"

        structural_items = [
            (scores.get("H4"), weights["H4"]),
            (scores.get("D1"), weights["D1"]),
        ]
        structural_total = sum(weight for score, weight in structural_items if score is not None)
        structural_score = (
            sum(float(score or 0.0) * weight for score, weight in structural_items if score is not None) / structural_total
            if structural_total
            else 0.0
        )
        h1_h4_items = [
            (scores.get("H1"), weights["H1"]),
            (scores.get("H4"), weights["H4"]),
        ]
        h1_h4_total = sum(weight for score, weight in h1_h4_items if score is not None)
        h1_h4_score = (
            sum(float(score or 0.0) * weight for score, weight in h1_h4_items if score is not None) / h1_h4_total
            if h1_h4_total
            else 0.0
        )

        side_factor = 1.0 if side == "BUY" else -1.0
        alignment_score = consensus_score * side_factor
        structural_alignment = structural_score * side_factor
        h1_h4_alignment = h1_h4_score * side_factor
        min_valid = int(cfg.get("min_valid_timeframes", 3) or 3)
        min_consensus = float(cfg.get("min_consensus_score", 0.18) or 0.18)
        min_structural = float(cfg.get("min_structural_score", 0.10) or 0.10)
        low_tf = signal_tf in {"M5", "M15", "M30"}

        reasons: list[str] = []
        warnings: list[str] = []
        if valid_timeframes < min_valid:
            warnings.append(f"timeframes_validos_insuficientes:{valid_timeframes}")
        else:
            if abs(consensus_score) < min_consensus:
                reasons.append("consenso_fraco")
            if alignment_score < -min_consensus:
                reasons.append(f"consenso_contra:{consensus_direction}")
            elif alignment_score < min_consensus:
                reasons.append("alinhamento_fraco")
            if structural_total > 0 and structural_alignment < -min_structural:
                reasons.append("estrutura_h4_d1_contra")
            elif structural_total > 0 and structural_alignment < min_structural:
                warnings.append("estrutura_h4_d1_fraca")
            if bool(cfg.get("require_h1_or_h4_alignment", True)) and h1_h4_total > 0 and h1_h4_alignment < min_structural:
                reasons.append("h1_h4_nao_confirma")
            if bool(cfg.get("block_lower_tf_against_h4_d1", True)) and low_tf and structural_total > 0 and structural_alignment < -min_structural:
                reasons.append("pullback_contra_estrutura")

        if valid_timeframes < min_valid:
            state = "insufficient_data"
        elif "estrutura_h4_d1_contra" in reasons or "pullback_contra_estrutura" in reasons:
            state = "structural_conflict"
        elif any(item.startswith("consenso_contra") for item in reasons):
            state = "counter_consensus"
        elif "consenso_fraco" in reasons or "alinhamento_fraco" in reasons:
            state = "weak_consensus"
        else:
            state = "aligned"

        return {
            "symbol": symbol,
            "signal_timeframe": signal_tf,
            "signal_side": side,
            "consensus_direction": consensus_direction,
            "state": state,
            "consensus_score": consensus_score,
            "alignment_score": alignment_score,
            "structural_score": structural_score,
            "structural_alignment": structural_alignment,
            "h1_h4_score": h1_h4_score,
            "h1_h4_alignment": h1_h4_alignment,
            "valid_timeframes": valid_timeframes,
            "confidence": min(1.0, max(0.0, abs(consensus_score))),
            "buy_weight": buy_weight,
            "sell_weight": sell_weight,
            "wait_weight": wait_weight,
            "labels": labels,
            "scores": scores,
            "edges": edges,
            "reasons": reasons,
            "warnings": warnings,
        }

    def _build_final_signal_state(self) -> dict:
        panel_cfg = self.config.get("mt5_signal_panel.refined_display", {}) or {}
        if not bool(panel_cfg.get("show_final_row", True)):
            self.final_signal_state = {}
            return self.final_signal_state

        consensus_cfg = self.config.get("entry_filters.timeframe_consensus", {}) or {}
        tf_names = ["M5", "M15", "M30", "H1", "H4", "D1"]
        weights_cfg = consensus_cfg.get("timeframe_weights", {}) or {}
        weights = {
            "M5": float(weights_cfg.get("M5", 0.50) or 0.50),
            "M15": float(weights_cfg.get("M15", 0.75) or 0.75),
            "M30": float(weights_cfg.get("M30", 1.00) or 1.00),
            "H1": float(weights_cfg.get("H1", 1.50) or 1.50),
            "H4": float(weights_cfg.get("H4", 2.50) or 2.50),
            "D1": float(weights_cfg.get("D1", 3.00) or 3.00),
        }
        wait_edge = float(consensus_cfg.get("wait_edge", 0.08) or 0.08)
        min_valid = int(consensus_cfg.get("min_valid_timeframes", 3) or 3)
        min_consensus = float(consensus_cfg.get("min_consensus_score", 0.18) or 0.18)

        final_state: dict[str, dict] = {}
        symbols = sorted({str(symbol).upper() for symbol, _tf in self.monitor_state.keys()})
        for symbol in symbols:
            valid_timeframes = 0
            weighted_total = 0.0
            weighted_score_total = 0.0
            buy_weight = 0.0
            sell_weight = 0.0
            wait_weight = 0.0
            labels: list[str] = []

            for tf_name in tf_names:
                state = self.monitor_state.get((symbol, tf_name), {}) or {}
                signal = int(state.get("raw_signal", state.get("signal", 0)) or 0)
                if signal == -1:
                    continue
                try:
                    p_buy = float(state.get("raw_p_buy", state.get("p_buy")) or 0.0)
                    p_sell = float(state.get("raw_p_sell", state.get("p_sell")) or 0.0)
                except (TypeError, ValueError):
                    p_buy = 0.0
                    p_sell = 0.0
                if p_buy == 0.0 and p_sell == 0.0 and signal == 0:
                    continue

                edge = max(-1.0, min(1.0, p_buy - p_sell))
                weight = weights.get(tf_name, 1.0)
                if signal == 1:
                    score = max(abs(edge), wait_edge)
                    buy_weight += weight * score
                    label = "BUY"
                elif signal == 2:
                    score = -max(abs(edge), wait_edge)
                    sell_weight += weight * abs(score)
                    label = "SELL"
                else:
                    score = 0.0
                    wait_weight += weight
                    label = "WAIT"

                valid_timeframes += 1
                weighted_total += weight
                weighted_score_total += score * weight
                labels.append(f"{tf_name}:{label}")

            consensus_score = weighted_score_total / weighted_total if weighted_total else 0.0
            direction = "BUY" if consensus_score > 0 else "SELL" if consensus_score < 0 else "WAIT"
            reason_parts = [
                (
                    f"final_consensus:{direction}:score={consensus_score:.3f}:"
                    f"valid={valid_timeframes}:buy_w={buy_weight:.3f}:sell_w={sell_weight:.3f}:wait_w={wait_weight:.3f}"
                )
            ]
            if labels:
                reason_parts.append("tf_votes:" + "|".join(labels))

            if valid_timeframes < min_valid:
                pred = 0
                reason_parts.append(f"final_wait:valid_timeframes_low:{valid_timeframes}")
            elif abs(consensus_score) < min_consensus:
                pred = 0
                reason_parts.append(f"final_wait:weak_consensus:{consensus_score:.3f}")
            elif consensus_score > 0:
                pred = 1
            else:
                pred = 2

            p_buy = max(0.0, min(1.0, 0.5 + consensus_score / 2.0))
            p_sell = max(0.0, min(1.0, 1.0 - p_buy))
            display_pred, display_p_buy, display_p_sell, display_reasons = self._refine_panel_signal(
                pred,
                p_buy,
                p_sell,
                symbol,
                "FINAL",
                reason_parts,
            )
            final_state[symbol] = {
                "signal": display_pred,
                "p_buy": display_p_buy,
                "p_sell": display_p_sell,
                "reason": ";".join(display_reasons),
                "alert_signal": display_pred,
                "alert_reason": ";".join(display_reasons),
                "consensus_score": consensus_score,
                "valid_timeframes": valid_timeframes,
            }

        self.final_signal_state = final_state
        return self.final_signal_state

    def _position_side(self, position) -> str:
        raw_type = getattr(position, "type", None)
        if mt5 is not None:
            if raw_type == mt5.ORDER_TYPE_BUY:
                return "BUY"
            if raw_type == mt5.ORDER_TYPE_SELL:
                return "SELL"
        direction = str(getattr(position, "direction", "") or "").upper()
        if direction in {"BUY", "SELL"}:
            return direction
        return ""

    def _position_in_close_scope(self, position, scope: str, fusion_magics: set[int]) -> bool:
        scope = str(scope or "fusion_magics").strip().lower()
        if scope in {"all", "all_positions"}:
            return True
        if scope in {"fusion_magics", "system", "system_magics"}:
            try:
                return int(getattr(position, "magic", 0) or 0) in fusion_magics
            except (TypeError, ValueError):
                return False
        return False

    def _manual_order_approval_cfg(self) -> dict:
        return self.execution_controls.manual_order_approval_cfg()

    def _mt5_execution_control(self) -> dict:
        # Legado do bridge/CSV removido do fluxo ativo.
        # O runtime agora usa somente config YAML + fusion_runtime_control.json.
        return {}

    def _fusion_orders_allowed(self) -> tuple[bool, str]:
        return self.execution_controls.fusion_orders_allowed()

    def _normalize_execution_mode(self, value) -> str:
        mode = str(value or "").strip().lower()
        if mode in {"auto", "automatic", "automatico", "automÃ¡tico"}:
            return "automatic"
        if mode in {"manual", "confirm", "confirmation", "confirmacao", "confirmaÃ§Ã£o"}:
            return "manual"
        return ""

    def _execution_mode(self) -> str:
        return self.execution_controls.execution_mode()

    def _manual_order_approval_required(self) -> bool:
        return self.execution_controls.manual_order_approval_required()

    def _read_manual_order_response(self, request_id: str) -> str:
        return self.execution_controls.read_manual_order_response(request_id)

    def _await_manual_order_approval(
        self,
        request_id: str,
        broker_sym: str,
        sym_ia: str,
        tf: str,
        side: str,
        p_buy: float,
        p_sell: float,
        tp_points: int,
        sl_points: int,
        magic: int,
        strategy_name: str,
    ) -> bool:
        result = self.execution_controls.await_manual_order_approval(
            request_id,
            broker_sym,
            sym_ia,
            tf,
            side,
            p_buy,
            p_sell,
            tp_points,
            sl_points,
            magic,
            strategy_name,
        )
        if not result and self._last_execution_block_reason == "":
            self._last_execution_block_reason = "manual_approval_timeout"
        return result

    def _market_alignment_snapshot(self, broker_sym: str, sym_ia: str, signal_tf: str, side: str, cfg: dict) -> dict:
        tf_names = ["M5", "M15", "M30", "H1", "H4", "D1"]
        weights_cfg = cfg.get("timeframe_weights", {}) or {}
        weights = {
            "M5": float(weights_cfg.get("M5", 0.50) or 0.50),
            "M15": float(weights_cfg.get("M15", 0.75) or 0.75),
            "M30": float(weights_cfg.get("M30", 1.00) or 1.00),
            "H1": float(weights_cfg.get("H1", 1.50) or 1.50),
            "H4": float(weights_cfg.get("H4", 2.50) or 2.50),
            "D1": float(weights_cfg.get("D1", 3.00) or 3.00),
        }
        labels: dict[str, str] = {}
        scores: dict[str, float] = {}
        changes: dict[str, float] = {}
        for tf_name in tf_names:
            label, score, change = self._market_alignment_timeframe(broker_sym, tf_name)
            labels[tf_name] = label
            scores[tf_name] = score
            changes[tf_name] = change

        total_weight = sum(weights.values()) or 1.0
        weighted_score = sum(float(scores.get(tf_name, 0.0)) * weights[tf_name] for tf_name in tf_names) / total_weight
        structural_weight = weights["H4"] + weights["D1"]
        structural_score = ((scores.get("H4", 0.0) * weights["H4"]) + (scores.get("D1", 0.0) * weights["D1"])) / structural_weight
        h1_h4_score = ((scores.get("H1", 0.0) * weights["H1"]) + (scores.get("H4", 0.0) * weights["H4"])) / (weights["H1"] + weights["H4"])

        side_factor = 1.0 if side == "BUY" else -1.0
        alignment_score = weighted_score * side_factor
        structural_alignment = structural_score * side_factor
        h1_h4_alignment = h1_h4_score * side_factor
        market_direction = "BUY" if weighted_score > 0 else "SELL" if weighted_score < 0 else "NEUTRAL"
        signal_tf = str(signal_tf or "").upper()
        low_tf = signal_tf in {"M5", "M15", "M30"}

        reasons: list[str] = []
        warnings: list[str] = []
        min_alignment = float(cfg.get("min_alignment_score", 0.18) or 0.18)
        min_structural = float(cfg.get("min_structural_score", 0.10) or 0.10)
        chop_abs_score = float(cfg.get("chop_abs_score", 0.14) or 0.14)

        if abs(weighted_score) < chop_abs_score:
            reasons.append("chop_sem_fluxo")
        if alignment_score < -min_alignment:
            reasons.append(f"fluxo_contra:{market_direction}")
        elif alignment_score < min_alignment:
            warnings.append("alinhamento_fraco")
        if structural_alignment < -min_structural:
            reasons.append("estrutura_h4_d1_contra")
        elif structural_alignment < min_structural:
            warnings.append("estrutura_h4_d1_fraca")
        if bool(cfg.get("require_h1_or_h4_alignment", True)) and h1_h4_alignment < min_structural:
            reasons.append("h1_h4_nao_confirma")
        if bool(cfg.get("block_lower_tf_against_h4_d1", True)) and low_tf and structural_alignment < -min_structural:
            reasons.append("pullback_contra_estrutura")

        if "chop_sem_fluxo" in reasons:
            state = "chop"
        elif "pullback_contra_estrutura" in reasons:
            state = "pullback"
        elif "estrutura_h4_d1_contra" in reasons:
            state = "structural_conflict"
        elif any(item.startswith("fluxo_contra") for item in reasons):
            state = "countertrend"
        elif alignment_score < min_alignment or warnings:
            state = "weak_alignment"
        else:
            state = "aligned"

        return {
            "symbol": sym_ia.upper(),
            "signal_timeframe": signal_tf,
            "signal_side": side,
            "market_direction": market_direction,
            "state": state,
            "alignment_score": alignment_score,
            "weighted_score": weighted_score,
            "structural_score": structural_score,
            "structural_alignment": structural_alignment,
            "h1_h4_score": h1_h4_score,
            "h1_h4_alignment": h1_h4_alignment,
            "confidence": min(1.0, max(0.0, abs(weighted_score))),
            "labels": labels,
            "scores": scores,
            "changes_20": changes,
            "reasons": reasons,
            "warnings": warnings,
        }

    def _market_alignment_timeframe(self, broker_sym: str, tf_name: str) -> tuple[str, float, float]:
        bars = 220 if tf_name != "D1" else 140
        frame = self.feature_calc.get_rates_frame(broker_sym, tf_name, bars, start_pos=0, min_rows=80)
        if frame.empty or len(frame) < 80:
            return "NEUTRO", 0.0, 0.0
        closes = [float(item) for item in frame["close"].tolist()]
        highs = [float(item) for item in frame["high"].tolist()]
        lows = [float(item) for item in frame["low"].tolist()]
        last = closes[-1]
        ema20 = self._series_ema(closes, 20)
        ema50 = self._series_ema(closes, 50)
        if ema20 is None or ema50 is None or last <= 0:
            return "NEUTRO", 0.0, 0.0
        change20 = (last / closes[-21] - 1.0) if len(closes) > 21 and closes[-21] else 0.0
        change5 = (last / closes[-6] - 1.0) if len(closes) > 6 and closes[-6] else 0.0
        atr_value = self._series_atr(highs, lows, closes, 14)
        noise = (atr_value / last) if last else 0.0
        score = 0.0
        score += 0.35 if last > ema20 else -0.35
        score += 0.30 if ema20 > ema50 else -0.30
        score += 0.25 if change20 > 0 else -0.25
        score += 0.10 if change5 > 0 else -0.10
        score = max(-1.0, min(1.0, score))
        strength = abs(change20) + abs((ema20 / ema50) - 1.0)
        if abs(score) < 0.35 or strength < max(0.0004, noise * 0.35):
            return "NEUTRO", 0.0, change20
        if score >= 0.75 and strength > max(0.0022, noise * 1.10):
            return "FORTE BUY", score, change20
        if score >= 0.35:
            return "BUY", score, change20
        if score <= -0.75 and strength > max(0.0022, noise * 1.10):
            return "FORTE SELL", score, change20
        if score <= -0.35:
            return "SELL", score, change20
        return "NEUTRO", 0.0, change20

    @staticmethod
    def _series_ema(values: list[float], period: int) -> float | None:
        if len(values) < period:
            return None
        k = 2.0 / (period + 1.0)
        ema_value = sum(values[:period]) / period
        for value in values[period:]:
            ema_value = (value * k) + (ema_value * (1.0 - k))
        return ema_value

    @staticmethod
    def _series_atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> float:
        if len(closes) < period + 2:
            return 0.0
        ranges = []
        start = max(1, len(closes) - period)
        for idx in range(start, len(closes)):
            ranges.append(
                max(
                    highs[idx] - lows[idx],
                    abs(highs[idx] - closes[idx - 1]),
                    abs(lows[idx] - closes[idx - 1]),
                )
            )
        return sum(ranges) / len(ranges) if ranges else 0.0

    def _write_market_alignment_log(
        self,
        strategy_name: str,
        pred: int,
        sym_ia: str,
        tf: str,
        p_buy: float,
        p_sell: float,
        snapshot: dict,
    ) -> None:
        try:
            out_dir = Path("reports") / "market_alignment"
            out_dir.mkdir(parents=True, exist_ok=True)
            path = out_dir / f"market_alignment_{datetime.now().strftime('%Y%m%d')}.csv"
            fieldnames = [
                "timestamp", "symbol", "timeframe", "strategy", "prediction", "side",
                "state", "market_direction", "alignment_score", "structural_score",
                "h1_h4_score", "p_buy", "p_sell", "reasons", "warnings",
                "M5", "M15", "M30", "H1", "H4", "D1",
            ]
            write_header = not path.exists()
            labels = snapshot.get("labels", {}) or {}
            with path.open("a", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                if write_header:
                    writer.writeheader()
                writer.writerow(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "symbol": sym_ia.upper(),
                        "timeframe": str(tf).upper(),
                        "strategy": strategy_name,
                        "prediction": pred,
                        "side": self._prediction_side(pred),
                        "state": snapshot.get("state", ""),
                        "market_direction": snapshot.get("market_direction", ""),
                        "alignment_score": f"{float(snapshot.get('alignment_score', 0.0)):.4f}",
                        "structural_score": f"{float(snapshot.get('structural_score', 0.0)):.4f}",
                        "h1_h4_score": f"{float(snapshot.get('h1_h4_score', 0.0)):.4f}",
                        "p_buy": f"{float(p_buy or 0.0):.4f}",
                        "p_sell": f"{float(p_sell or 0.0):.4f}",
                        "reasons": ";".join(snapshot.get("reasons", []) or []),
                        "warnings": ";".join(snapshot.get("warnings", []) or []),
                        "M5": labels.get("M5", ""),
                        "M15": labels.get("M15", ""),
                        "M30": labels.get("M30", ""),
                        "H1": labels.get("H1", ""),
                        "H4": labels.get("H4", ""),
                        "D1": labels.get("D1", ""),
                    }
                )
        except Exception as exc:
            self.logger.warning(f"Falha ao gravar market_alignment log: {exc}")

    def _load_correlation_matrix(self, cfg: dict) -> dict:
        path_value = cfg.get("matrix_path", "reports/correlation/correlation_matrix_H1.json")
        path = Path(path_value)
        if not path.is_absolute():
            path = Path.cwd() / path
        try:
            mtime = path.stat().st_mtime
        except OSError:
            return {}
        if self._correlation_matrix_path == path and self._correlation_matrix_mtime == mtime:
            return self._correlation_matrix_cache
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            matrix = payload.get("correlations", payload)
            self._correlation_matrix_cache = {
                str(symbol).upper(): {str(other).upper(): float(value) for other, value in row.items()}
                for symbol, row in matrix.items()
                if isinstance(row, dict)
            }
            self._correlation_matrix_path = path
            self._correlation_matrix_mtime = mtime
            self.logger.info(f"Matriz de correlacao carregada: {path}")
            return self._correlation_matrix_cache
        except Exception as exc:
            self.logger.warning(f"Falha ao carregar matriz de correlacao: {exc}")
            return {}

    @staticmethod
    def _correlation_value(matrix: dict, symbol_a: str, symbol_b: str) -> float | None:
        symbol_a = symbol_a.upper()
        symbol_b = symbol_b.upper()
        if symbol_a == symbol_b:
            return 1.0
        value = matrix.get(symbol_a, {}).get(symbol_b)
        if value is None:
            value = matrix.get(symbol_b, {}).get(symbol_a)
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _correlation_reversal_relief_ok(
        self,
        broker_symbol: str,
        sym_ia: str,
        position_direction: int,
        cfg: dict,
    ) -> tuple[bool, str]:
        relief_cfg = cfg.get("reversal_relief", {}) or {}
        if not bool(relief_cfg.get("enabled", False)):
            return False, ""
        if mt5 is None:
            return False, "mt5_indisponivel"

        required_tfs = [str(item).upper() for item in relief_cfg.get("timeframes", ["M5", "M15"]) or ["M5", "M15"]]
        min_confirmations = max(1, int(relief_cfg.get("min_confirmations", len(required_tfs)) or len(required_tfs)))
        require_candle = bool(relief_cfg.get("require_candle_confirmation", True))
        require_ema = bool(relief_cfg.get("require_ema_alignment", True))
        pred = 1 if position_direction == 1 else 2
        confirmations = []
        failures = []

        for tf in required_tfs:
            df = self.feature_calc.get_rates_frame(broker_symbol, tf, 90, start_pos=0, min_rows=55)
            tick = mt5.symbol_info_tick(broker_symbol)
            if df.empty or len(df) < 55 or tick is None:
                failures.append(f"{tf}:dados_insuficientes")
                continue
            df = df.copy()
            current = df.iloc[-1]
            previous = df.iloc[-2]
            current_open = float(current["open"])
            previous_open = float(previous["open"])
            previous_close = float(previous["close"])
            previous_bull = previous_close > previous_open
            previous_bear = previous_close < previous_open
            if pred == 1:
                price = float(tick.ask)
                candle_ok = price > current_open and previous_bull
            else:
                price = float(tick.bid)
                candle_ok = price < current_open and previous_bear

            close = df["close"].astype(float)
            ema9 = close.ewm(span=9, adjust=False).mean().iloc[-1]
            ema21 = close.ewm(span=21, adjust=False).mean().iloc[-1]
            ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
            ema_ok = ema9 > ema21 > ema50 if pred == 1 else ema9 < ema21 < ema50

            checks = []
            if require_candle:
                checks.append(candle_ok)
            if require_ema:
                checks.append(ema_ok)
            if all(checks) if checks else (candle_ok or ema_ok):
                confirmations.append(tf)
            else:
                failed_parts = []
                if require_candle and not candle_ok:
                    failed_parts.append("candle")
                if require_ema and not ema_ok:
                    failed_parts.append("ema")
                failures.append(f"{tf}:{'+'.join(failed_parts) or 'sem_confirmacao'}")

        if len(confirmations) >= min_confirmations:
            return True, f"reversao_confirmada:{'+'.join(confirmations)}"
        return False, ";".join(failures[:4])

    def _portfolio_correlation_allowed(self, strategy_name: str, sym_ia: str, pred: int) -> bool:
        cfg = self._runtime_filter_config(
            "portfolio_correlation",
            self.config.get("entry_filters.portfolio_correlation", {}) or {},
            sym_ia,
            None,
        )
        if not bool(cfg.get("enabled", False)):
            return True
        if pred not in (1, 2):
            return True
        if mt5 is None:
            return True

        matrix = self._load_correlation_matrix(cfg)
        if not matrix:
            if bool(cfg.get("log_missing_matrix", True)):
                self.logger.warning("Filtro correlacao sem matriz disponivel; ordem nao bloqueada")
            return True

        candidate_symbol = sym_ia.upper()
        candidate_direction = 1 if pred == 1 else -1
        min_abs_corr = float(cfg.get("min_abs_correlation", 0.70) or 0.70)
        min_loss_money = float(cfg.get("min_loss_money", 0.01) or 0.01)
        mode = str(cfg.get("mode", "block") or "block").lower()
        scope = str(cfg.get("position_scope", "all") or "all").lower()
        current_strategy_magics = set(self._strategy_magic_group(strategy_name))
        system_magics = set()
        if scope == "system":
            for name in ["strategy1", "strategy2", "strategy3", "strategy4", "strategy5", "strategy6", "strategy7", "strategy8", "strategy9", "strategy10", "strategy11", "strategy12", "strategy13", "strategy14"]:
                system_magics.update(self._strategy_magic_group(name))

        positions = mt5.positions_get()
        positions = list(positions) if positions else []
        for pos in positions:
            if scope == "strategy" and int(pos.magic) not in current_strategy_magics:
                continue
            if scope == "system" and int(pos.magic) not in system_magics:
                continue
            profit = float(getattr(pos, "profit", 0.0) or 0.0)
            if profit >= -min_loss_money:
                continue
            position_symbol = self._broker_symbol_to_base(pos.symbol)
            corr = self._correlation_value(matrix, candidate_symbol, position_symbol)
            if corr is None or abs(corr) < min_abs_corr:
                continue

            position_direction = 1 if pos.type == mt5.ORDER_TYPE_BUY else -1
            pnl_similarity = corr * candidate_direction * position_direction
            if pnl_similarity <= 0:
                if bool(cfg.get("log_passed_filter", False)):
                    self.logger.info(
                        f"{strategy_name.upper()} {candidate_symbol} correlacao favoravel/hedge: "
                        f"pos={position_symbol} corr={corr:.2f} profit={profit:.2f}"
                    )
                continue

            direction = "BUY" if pred == 1 else "SELL"
            pos_direction = "BUY" if position_direction == 1 else "SELL"
            relief_ok, relief_reason = self._correlation_reversal_relief_ok(
                broker_symbol=pos.symbol,
                sym_ia=position_symbol,
                position_direction=position_direction,
                cfg=cfg,
            )
            relief_mode = str((cfg.get("reversal_relief", {}) or {}).get("mode", "allow") or "allow").lower()
            if relief_ok and relief_mode == "allow":
                self.logger.info(
                    f"{strategy_name.upper()} {candidate_symbol} {direction} correlacao liberada por possivel reversao: "
                    f"posicao {position_symbol} {pos_direction} em prejuizo {profit:.2f}, corr={corr:.2f}, {relief_reason}"
                )
                self._record_engine_output(
                    engine="portfolio_correlation",
                    direction="NEUTRAL",
                    score=0.70,
                    confidence=abs(corr),
                    state="relief",
                    positive_factors=[f"reversao_posicao_perdedora:{position_symbol}"],
                    warnings=[f"risco_correlacionado_liberado:{corr:.2f}"],
                    features={
                        "position_symbol": position_symbol,
                        "position_profit": profit,
                        "correlation": corr,
                        "pnl_similarity": pnl_similarity,
                        "relief_reason": relief_reason,
                    },
                )
                continue

            reason_code = str(cfg.get("reason_code", "correlacao_prejuizo") or "correlacao_prejuizo")
            message = (
                f"{reason_code}:{position_symbol}:{pos_direction}:profit={profit:.2f}:"
                f"corr={corr:.2f}:similaridade={pnl_similarity:.2f}"
            )
            if relief_reason:
                safe_relief_reason = relief_reason.replace(":", "_").replace(";", ",")
                message += f":sem_reversao={safe_relief_reason}"
            self._last_execution_block_reason = message
            self.logger.info(
                f"{strategy_name.upper()} {candidate_symbol} {direction} bloqueada por correlacao: "
                f"posicao {position_symbol} {pos_direction} em prejuizo {profit:.2f}, corr={corr:.2f}, "
                f"sem reversao confirmada: {relief_reason or 'n/a'}"
            )
            conflict_direction = "SELL" if pred == 1 else "BUY"
            self._record_engine_output(
                engine="portfolio_correlation",
                direction=conflict_direction,
                score=1.0,
                confidence=abs(corr),
                state="risk_accumulation",
                negative_factors=[reason_code, f"posicao_perdedora:{position_symbol}", f"corr={corr:.2f}"],
                features={
                    "position_symbol": position_symbol,
                    "position_direction": pos_direction,
                    "position_profit": profit,
                    "correlation": corr,
                    "pnl_similarity": pnl_similarity,
                    "relief_reason": relief_reason,
                },
            )
            return mode == "shadow"

        self._record_engine_output(
            engine="portfolio_correlation",
            direction="NEUTRAL",
            score=0.80,
            confidence=0.80,
            state="ok",
            positive_factors=["sem_risco_correlacionado_perdedor"],
        )
        return True

    def _portfolio_positions_snapshot(self, scope: str = "system", strategy_name: str = "") -> list[dict]:
        if mt5 is None:
            return []
        positions = mt5.positions_get()
        positions = list(positions) if positions else []
        scope = str(scope or "system").lower()
        magic_filter: set[int] = set()
        if scope == "system":
            magic_filter = set(self._system_magic_group())
        elif scope == "strategy" and strategy_name:
            magic_filter = set(self._strategy_magic_group(strategy_name))

        snapshot = []
        for pos in positions:
            magic = int(getattr(pos, "magic", 0) or 0)
            if magic_filter and magic not in magic_filter:
                continue
            direction = "BUY" if getattr(pos, "type", None) == mt5.ORDER_TYPE_BUY else "SELL"
            symbol = self._broker_symbol_to_base(getattr(pos, "symbol", "") or "")
            snapshot.append(
                {
                    "symbol": symbol,
                    "broker_symbol": getattr(pos, "symbol", ""),
                    "direction": direction,
                    "type": int(getattr(pos, "type", -1)),
                    "volume": float(getattr(pos, "volume", 0.0) or 0.0),
                    "profit": float(getattr(pos, "profit", 0.0) or 0.0),
                    "magic": magic,
                    "ticket": int(getattr(pos, "ticket", 0) or 0),
                }
            )
        return snapshot

    def _portfolio_exposure_check(self, strategy_name: str, pred: int, sym_ia: str) -> bool:
        cfg = self._runtime_filter_config(
            "portfolio_exposure",
            self.config.get("entry_filters.portfolio_exposure", {}) or {},
            sym_ia,
            None,
        )
        if not bool(cfg.get("enabled", False)):
            return True
        if pred not in (1, 2):
            return True

        mode = str(cfg.get("mode", "shadow") or "shadow").lower()
        positions = self._portfolio_positions_snapshot(str(cfg.get("position_scope", "system") or "system"), strategy_name)
        engine = PortfolioExposureEngine(
            PortfolioExposureConfig(
                max_currency_exposure=float(cfg.get("max_currency_exposure", 3.0) or 3.0),
                max_projected_currency_exposure=float(cfg.get("max_projected_currency_exposure", 4.0) or 4.0),
                max_cluster_exposure=float(cfg.get("max_cluster_exposure", 5.0) or 5.0),
                warning_cluster_exposure=float(cfg.get("warning_cluster_exposure", 3.0) or 3.0),
                correlation_threshold=float(cfg.get("correlation_threshold", 0.70) or 0.70),
                max_symbol_positions=int(cfg.get("max_symbol_positions", 1) or 1),
                warning_currency_exposure=float(cfg.get("warning_currency_exposure", 2.0) or 2.0),
                max_gross_exposure=float(cfg.get("max_gross_exposure", 12.0) or 12.0),
                warning_gross_exposure=float(cfg.get("warning_gross_exposure", 8.0) or 8.0),
                max_losing_currency_exposure=float(cfg.get("max_losing_currency_exposure", 3.0) or 3.0),
                include_negative_profit_focus=bool(cfg.get("include_negative_profit_focus", True)),
            )
        )
        matrix_cfg = {
            "matrix_path": cfg.get(
                "matrix_path",
                self.config.get("entry_filters.portfolio_correlation.matrix_path", "reports/correlation/correlation_matrix_H1.json"),
            )
        }
        output = engine.evaluate(
            candidate_symbol=sym_ia,
            candidate_side=self._prediction_side(pred),
            positions=positions,
            candidate_units=float(cfg.get("candidate_units", 1.0) or 1.0),
            correlation_matrix=self._load_correlation_matrix(matrix_cfg),
        )
        self._decision_engine_outputs.append(output)
        if bool(cfg.get("log_each_check", False)):
            self.logger.info(
                f"{strategy_name.upper()} {sym_ia} portfolio_exposure {mode}: "
                f"state={output.state} score={output.score:.2f} "
                f"max_proj={output.features.get('max_projected_exposure', 0.0):.2f}"
            )
        if mode == "shadow" or not self._engine_state_should_block(cfg, output):
            return True
        reason_code = str(cfg.get("reason_code", "portfolio_exposure") or "portfolio_exposure")
        self._last_execution_block_reason = f"{reason_code}:{output.state}"
        return False

    def _ai_advisor_check(
        self,
        strategy_name: str,
        pred: int,
        broker_sym: str,
        sym_ia: str,
        tf: str,
        p_buy: float = 0.0,
        p_sell: float = 0.0,
        extra: dict | None = None,
    ) -> bool:
        cfg = self.config.get("entry_filters.ai_advisor", {}) or {}
        if not bool(cfg.get("enabled", False)):
            return True
        if pred not in (1, 2):
            return True

        mode = str(cfg.get("mode", "shadow") or "shadow").lower()
        candidate = SignalCandidate(
            symbol=sym_ia.upper(),
            broker_symbol=broker_sym,
            timeframe=tf,
            side=self._prediction_side(pred),
            strategy=strategy_name,
            raw_prediction=pred,
            p_buy=float(p_buy or 0.0),
            p_sell=float(p_sell or 0.0),
        )
        advisor = AIAdvisorEngine(
            AIAdvisorConfig(
                endpoint_url=str(cfg.get("endpoint_url", "http://127.0.0.1:8765/advice") or "http://127.0.0.1:8765/advice"),
                timeout_seconds=float(cfg.get("timeout_seconds", 8) or 8),
                min_confidence_to_block=float(cfg.get("min_confidence_to_block", 0.65) or 0.65),
                fail_open=bool(cfg.get("fail_open", True)),
                model_hint=str(cfg.get("model_hint", "gpt-5.4-nano") or "gpt-5.4-nano"),
            )
        )
        advisor_correlation_id = f"{sym_ia.upper()}:{tf}:{strategy_name}:ADVISOR:{datetime.now().isoformat()}"
        advisor_payload = advisor.build_payload(candidate, list(self._decision_engine_outputs), portfolio=extra or {})
        self._publish_event(
            FusionEventType.ADVISOR_REQUEST,
            advisor_payload,
            source="AIAdvisor",
            correlation_id=advisor_correlation_id,
        )
        output = advisor.evaluate(candidate, list(self._decision_engine_outputs), portfolio=extra or {})
        self._decision_engine_outputs.append(output)
        self._publish_event(
            FusionEventType.ADVISOR_RESPONSE,
            {
                "candidate": advisor_payload.get("candidate", {}),
                "engine": {
                    "engine": output.engine,
                    "direction": output.direction,
                    "score": output.score,
                    "confidence": output.confidence,
                    "state": output.state,
                    "positive_factors": output.positive_factors,
                    "negative_factors": output.negative_factors,
                    "warnings": output.warnings,
                    "features": output.features,
                },
                "mode": mode,
            },
            source="AIAdvisor",
            correlation_id=advisor_correlation_id,
        )
        if bool(cfg.get("log_each_check", True)):
            factors = output.negative_factors or output.positive_factors or [output.state]
            self.logger.info(
                f"{strategy_name.upper()} {sym_ia} {tf} ai_advisor {mode}: "
                f"state={output.state} conf={output.confidence:.2f} "
                f"factors={','.join((factors)[:2])}"
            )
        if mode == "shadow":
            return True
        if output.state == "unavailable" and bool(cfg.get("fail_open", True)):
            return True
        if output.state == "avoid" and output.confidence >= float(cfg.get("min_confidence_to_block", 0.65) or 0.65):
            reason_code = str(cfg.get("reason_code", "ai_advisor") or "ai_advisor")
            reason = (output.negative_factors or ["avoid"])[0]
            self._last_execution_block_reason = f"{reason_code}:avoid:{reason}"
            return False
        return True

    def _context_engine_check(
        self,
        strategy_name: str,
        pred: int,
        broker_sym: str,
        sym_ia: str,
        tf: str,
        p_buy: float = 0.0,
        p_sell: float = 0.0,
    ) -> bool:
        cfg = self.config.get("entry_filters.context_engine", {}) or {}
        if not bool(cfg.get("enabled", False)):
            return True
        mode = str(cfg.get("mode", "shadow") or "shadow").lower()
        candidate = SignalCandidate(
            symbol=sym_ia.upper(),
            broker_symbol=broker_sym,
            timeframe=tf,
            side=self._prediction_side(pred),
            strategy=strategy_name,
            raw_prediction=pred,
            p_buy=float(p_buy or 0.0),
            p_sell=float(p_sell or 0.0),
        )
        weights = cfg.get("weights", {}) or {}
        engine = ContextEngine(
            ContextEngineConfig(
                weights={str(key): float(value) for key, value in weights.items()},
                min_context_score=float(cfg.get("min_context_score", 0.55) or 0.55),
                max_context_conflict=float(cfg.get("max_context_conflict", 0.35) or 0.35),
            )
        )
        output = engine.evaluate(candidate, list(self._decision_engine_outputs))
        self._decision_engine_outputs.append(output)
        if bool(cfg.get("log_each_check", False)):
            self.logger.info(
                f"{strategy_name.upper()} {sym_ia} {tf} context_engine {mode}: "
                f"state={output.state} score={output.score:.2f} conf={output.confidence:.2f}"
            )
        if mode == "shadow" or not output.negative_factors:
            return True
        reason_code = str(cfg.get("reason_code", "context_engine") or "context_engine")
        self._last_execution_block_reason = f"{reason_code}:{output.state}"
        return False

    def _context_brain_check(
        self,
        strategy_name: str,
        pred: int,
        broker_sym: str,
        sym_ia: str,
        tf: str,
        p_buy: float = 0.0,
        p_sell: float = 0.0,
    ) -> bool:
        cfg = self.config.get("entry_filters.context_brain", {}) or {}
        if not bool(cfg.get("enabled", False)):
            return True
        if pred not in (1, 2):
            return True
        mode = str(cfg.get("mode", "shadow") or "shadow").lower()
        candidate = SignalCandidate(
            symbol=sym_ia.upper(),
            broker_symbol=broker_sym,
            timeframe=tf,
            side=self._prediction_side(pred),
            strategy=strategy_name,
            raw_prediction=pred,
            p_buy=float(p_buy or 0.0),
            p_sell=float(p_sell or 0.0),
        )
        weights = cfg.get("weights", {}) or {}
        engine = ContextBrainEngine(
            ContextBrainConfig(
                weights={str(key): float(value) for key, value in weights.items()},
                min_brain_score=float(cfg.get("min_brain_score", 0.55) or 0.55),
                strong_score=float(cfg.get("strong_score", 0.72) or 0.72),
                max_conflict_score=float(cfg.get("max_conflict_score", 0.35) or 0.35),
            )
        )
        output = engine.evaluate(candidate, list(self._decision_engine_outputs))
        self._decision_engine_outputs.append(output)
        if bool(cfg.get("write_monitor_log", True)):
            self._write_context_brain_log(strategy_name, pred, sym_ia, tf, p_buy, p_sell, output)
        if bool(cfg.get("log_each_check", False)) and output.state not in {
            "institutional_aligned",
            "strong_institutional_alignment",
        }:
            label = str((output.features or {}).get("final_label", output.direction) or output.direction)
            factors = output.negative_factors or output.positive_factors or [output.state]
            self.logger.info(
                f"{strategy_name.upper()} {sym_ia} {tf} context_brain {mode}: "
                f"label={label} state={output.state} score={output.score:.2f} "
                f"conf={output.confidence:.2f} factors={','.join(factors[:3])}"
            )
        if mode == "shadow":
            return True
        relax_cfg = self.config.get("entry_filters.daytrade_relaxation", {}) or {}
        if self._should_relax_filter_for_daytrade(relax_cfg, "context_brain", tf, p_buy, p_sell):
            self.logger.info(
                f"[DAYTRADE_RELAX] {strategy_name.upper()} {sym_ia} {tf} context_brain relaxed for strong short-term edge"
            )
            return True
        if not self._engine_state_should_block(cfg, output):
            return True
        reason_code = str(cfg.get("reason_code", "context_brain") or "context_brain")
        reason = (output.negative_factors or [output.state])[0]
        self._last_execution_block_reason = f"{reason_code}:{output.state}:{reason}"
        return False

    def _write_context_brain_log(
        self,
        strategy_name: str,
        pred: int,
        sym_ia: str,
        tf: str,
        p_buy: float,
        p_sell: float,
        output: EngineOutput,
    ) -> None:
        try:
            out_dir = Path("reports") / "context_brain"
            out_dir.mkdir(parents=True, exist_ok=True)
            path = out_dir / f"context_brain_{datetime.now().strftime('%Y%m%d')}.csv"
            fieldnames = [
                "timestamp", "symbol", "timeframe", "strategy", "prediction", "side",
                "final_label", "state", "direction", "score", "confidence",
                "conflict_score", "model_edge", "p_buy", "p_sell",
                "aligned_engines", "conflicting_engines", "structural_conflicts",
                "negative_factors", "warnings",
            ]
            write_header = not path.exists()
            features = output.features or {}
            with path.open("a", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                if write_header:
                    writer.writeheader()
                writer.writerow(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "symbol": str(sym_ia).upper(),
                        "timeframe": str(tf).upper(),
                        "strategy": strategy_name,
                        "prediction": pred,
                        "side": self._prediction_side(pred),
                        "final_label": features.get("final_label", ""),
                        "state": output.state,
                        "direction": output.direction,
                        "score": f"{float(output.score or 0.0):.4f}",
                        "confidence": f"{float(output.confidence or 0.0):.4f}",
                        "conflict_score": f"{float(features.get('conflict_score', 0.0) or 0.0):.4f}",
                        "model_edge": f"{float(features.get('model_edge', 0.0) or 0.0):.4f}",
                        "p_buy": f"{float(p_buy or 0.0):.4f}",
                        "p_sell": f"{float(p_sell or 0.0):.4f}",
                        "aligned_engines": ";".join(features.get("aligned_engines", []) or []),
                        "conflicting_engines": ";".join(features.get("conflicting_engines", []) or []),
                        "structural_conflicts": ";".join(features.get("structural_conflicts", []) or []),
                        "negative_factors": ";".join(output.negative_factors or []),
                        "warnings": ";".join(output.warnings or []),
                    }
                )
        except Exception as exc:
            self.logger.warning(f"Falha ao gravar context_brain log: {exc}")

    def _currency_strength_config(self) -> tuple[dict, CurrencyStrengthConfig]:
        cfg = self.config.get("currency_strength_map", {}) or {}
        weights = cfg.get("timeframe_weights", {}) or {}
        parsed_weights = {str(key).upper(): float(value) for key, value in weights.items()}
        defaults = CurrencyStrengthConfig()
        return cfg, CurrencyStrengthConfig(
            timeframe_weights=parsed_weights or defaults.timeframe_weights,
            wait_edge=float(cfg.get("wait_edge", 0.08) or 0.08),
            min_confidence_weight=float(cfg.get("min_confidence_weight", 0.20) or 0.20),
            strong_pair_score=float(cfg.get("strong_pair_score", 4.0) or 4.0),
            moderate_pair_score=float(cfg.get("moderate_pair_score", 2.0) or 2.0),
        )

    def _annotate_currency_strength_neutrals(self) -> None:
        try:
            cfg, strength_cfg = self._currency_strength_config()
            if not bool(cfg.get("enabled", False)):
                return
            detector_cfg = cfg.get("false_neutral_detector", {}) or {}
            if not bool(detector_cfg.get("enabled", False)):
                return

            snapshot = build_currency_strength_map(self.monitor_state, strength_cfg)
            pair_scores = snapshot.get("pair_scores", {}) or {}
            min_pair_score = float(detector_cfg.get("min_pair_score", 4.0) or 4.0)
            min_aligned = int(detector_cfg.get("min_aligned_timeframes", 2) or 2)
            structural_timeframes = {
                str(tf).upper() for tf in (detector_cfg.get("structural_timeframes", []) or ["H1", "H4", "D1"])
            }
            require_structural_short = bool(detector_cfg.get("require_structural_for_short_tf", True))
            short_timeframes = {"M5", "M15", "M30"}
            stamp = datetime.now()
            candidates = []

            for (symbol_raw, timeframe_raw), state in list(self.monitor_state.items()):
                symbol = str(symbol_raw or "").upper()
                timeframe = str(timeframe_raw or "").upper()
                if int((state or {}).get("signal", 0) or 0) != 0:
                    continue
                if symbol not in pair_scores:
                    continue

                pair = pair_scores[symbol]
                pair_score = float(pair.get("pair_score", 0.0) or 0.0)
                if abs(pair_score) < min_pair_score:
                    continue
                target_direction = "BUY" if pair_score > 0 else "SELL"
                target_signal = 1 if target_direction == "BUY" else 2

                current_direction, current_confidence = direction_from_probs(
                    int(state.get("signal", 0) or 0),
                    state.get("p_buy"),
                    state.get("p_sell"),
                    strength_cfg.wait_edge,
                )
                current_edge = 0.0
                try:
                    current_edge = float(state.get("p_buy") or 0.0) - float(state.get("p_sell") or 0.0)
                except (TypeError, ValueError):
                    current_edge = 0.0
                if current_direction not in {"NEUTRO", target_direction}:
                    continue
                if target_signal == 1 and current_edge < -strength_cfg.wait_edge:
                    continue
                if target_signal == 2 and current_edge > strength_cfg.wait_edge:
                    continue

                aligned_timeframes = []
                structural_aligned = []
                opposite_timeframes = []
                for tf in self.TIMEFRAMES:
                    tf_key = (symbol, str(tf).upper())
                    tf_state = self.monitor_state.get(tf_key, {}) or {}
                    tf_signal = int(tf_state.get("signal", 0) or 0)
                    if tf_signal == target_signal:
                        aligned_timeframes.append(str(tf).upper())
                        if str(tf).upper() in structural_timeframes:
                            structural_aligned.append(str(tf).upper())
                    elif tf_signal in (1, 2):
                        opposite_timeframes.append(str(tf).upper())

                if len(aligned_timeframes) < min_aligned and not structural_aligned:
                    continue
                if timeframe in short_timeframes and require_structural_short and not structural_aligned:
                    continue

                reason = (
                    f"currency_strength_false_neutral:{target_direction}:"
                    f"score={pair_score:.2f}:aligned={'+'.join(aligned_timeframes)}"
                )
                existing_reason = str(state.get("reason", "") or "")
                if "currency_strength_false_neutral" not in existing_reason:
                    state["reason"] = f"{existing_reason};{reason}" if existing_reason else reason
                state["currency_strength_candidate"] = {
                    "direction": target_direction,
                    "pair_score": pair_score,
                    "base_score": float(pair.get("base_score", 0.0) or 0.0),
                    "quote_score": float(pair.get("quote_score", 0.0) or 0.0),
                    "aligned_timeframes": aligned_timeframes,
                    "structural_aligned": structural_aligned,
                    "opposite_timeframes": opposite_timeframes,
                }
                candidates.append(
                    {
                        "timestamp": stamp.isoformat(),
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "candidate_direction": target_direction,
                        "pair_score": f"{pair_score:.6f}",
                        "base": pair.get("base", ""),
                        "quote": pair.get("quote", ""),
                        "base_score": f"{float(pair.get('base_score', 0.0) or 0.0):.6f}",
                        "quote_score": f"{float(pair.get('quote_score', 0.0) or 0.0):.6f}",
                        "p_buy": f"{float(state.get('p_buy') or 0.0):.6f}",
                        "p_sell": f"{float(state.get('p_sell') or 0.0):.6f}",
                        "model_edge": f"{current_edge:.6f}",
                        "aligned_timeframes": ";".join(aligned_timeframes),
                        "structural_aligned": ";".join(structural_aligned),
                        "opposite_timeframes": ";".join(opposite_timeframes),
                        "reason": reason,
                    }
                )

            if candidates and bool(detector_cfg.get("write_csv", True)):
                out_dir = Path(str(cfg.get("output_dir", "reports/currency_strength") or "reports/currency_strength"))
                out_dir.mkdir(parents=True, exist_ok=True)
                path = out_dir / f"false_neutral_candidates_{stamp.strftime('%Y%m%d')}.csv"
                fields = [
                    "timestamp", "symbol", "timeframe", "candidate_direction", "pair_score",
                    "base", "quote", "base_score", "quote_score", "p_buy", "p_sell",
                    "model_edge", "aligned_timeframes", "structural_aligned",
                    "opposite_timeframes", "reason",
                ]
                write_header = not path.exists()
                with path.open("a", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(handle, fieldnames=fields)
                    if write_header:
                        writer.writeheader()
                    writer.writerows(candidates)
        except Exception as exc:
            self.logger.warning(f"Falha ao analisar falsos neutros por currency_strength_map: {exc}")

    def _annotate_currency_strength_directional_signals(self) -> None:
        try:
            cfg, strength_cfg = self._currency_strength_config()
            if not bool(cfg.get("enabled", False)):
                return
            guard_cfg = cfg.get("directional_signal_guard", {}) or {}
            if not bool(guard_cfg.get("enabled", False)):
                return

            snapshot = build_currency_strength_map(self.monitor_state, strength_cfg)
            pair_scores = snapshot.get("pair_scores", {}) or {}
            min_confirm = float(guard_cfg.get("min_confirm_score", 2.0) or 2.0)
            min_conflict = float(guard_cfg.get("min_conflict_score", 3.0) or 3.0)
            reason_code = str(guard_cfg.get("reason_code", "currency_strength_guard") or "currency_strength_guard")
            stamp = datetime.now()
            rows = []

            for (symbol_raw, timeframe_raw), state in list(self.monitor_state.items()):
                symbol = str(symbol_raw or "").upper()
                timeframe = str(timeframe_raw or "").upper()
                pred = int((state or {}).get("signal", 0) or 0)
                if pred not in (1, 2):
                    continue
                if symbol not in pair_scores:
                    continue

                pair = pair_scores[symbol]
                pair_score = float(pair.get("pair_score", 0.0) or 0.0)
                raw_symbol_score = float(pair.get("raw_score", 0.0) or 0.0)
                external_pair_score = pair_score - (2.0 * raw_symbol_score)
                expected_direction = (
                    "BUY" if external_pair_score > 0 else "SELL" if external_pair_score < 0 else "NEUTRO"
                )
                signal_direction = "BUY" if pred == 1 else "SELL"
                signed_alignment = external_pair_score if pred == 1 else -external_pair_score
                if signed_alignment >= min_confirm:
                    verdict = "confirmed"
                    reason = f"{reason_code}:confirmed:{signal_direction}:score={external_pair_score:.2f}"
                elif signed_alignment <= -min_conflict:
                    verdict = "conflict"
                    reason = (
                        f"{reason_code}:conflict:{signal_direction}->"
                        f"{expected_direction}:score={external_pair_score:.2f}"
                    )
                else:
                    verdict = "weak_or_mixed"
                    reason = f"{reason_code}:weak_or_mixed:{signal_direction}:score={external_pair_score:.2f}"

                existing_reason = str(state.get("reason", "") or "")
                if reason_code not in existing_reason:
                    state["reason"] = f"{existing_reason};{reason}" if existing_reason else reason
                state["currency_strength_guard"] = {
                    "verdict": verdict,
                    "signal_direction": signal_direction,
                    "expected_direction": expected_direction,
                    "pair_score": pair_score,
                    "external_pair_score": external_pair_score,
                    "base_score": float(pair.get("base_score", 0.0) or 0.0),
                    "quote_score": float(pair.get("quote_score", 0.0) or 0.0),
                }
                rows.append(
                    {
                        "timestamp": stamp.isoformat(),
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "signal_direction": signal_direction,
                        "expected_direction": expected_direction,
                        "verdict": verdict,
                        "pair_score": f"{pair_score:.6f}",
                        "external_pair_score": f"{external_pair_score:.6f}",
                        "base": pair.get("base", ""),
                        "quote": pair.get("quote", ""),
                        "base_score": f"{float(pair.get('base_score', 0.0) or 0.0):.6f}",
                        "quote_score": f"{float(pair.get('quote_score', 0.0) or 0.0):.6f}",
                        "p_buy": f"{float(state.get('p_buy') or 0.0):.6f}",
                        "p_sell": f"{float(state.get('p_sell') or 0.0):.6f}",
                        "reason": reason,
                    }
                )

            if rows and bool(guard_cfg.get("write_csv", True)):
                out_dir = Path(str(cfg.get("output_dir", "reports/currency_strength") or "reports/currency_strength"))
                out_dir.mkdir(parents=True, exist_ok=True)
                path = out_dir / f"signal_flow_guard_{stamp.strftime('%Y%m%d')}.csv"
                fields = [
                    "timestamp", "symbol", "timeframe", "signal_direction", "expected_direction",
                    "verdict", "pair_score", "external_pair_score", "base", "quote", "base_score", "quote_score",
                    "p_buy", "p_sell", "reason",
                ]
                write_header = not path.exists()
                with path.open("a", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(handle, fieldnames=fields)
                    if write_header:
                        writer.writeheader()
                    writer.writerows(rows)
        except Exception as exc:
            self.logger.warning(f"Falha ao validar sinais por currency_strength_map: {exc}")

    def _write_currency_strength_map(self) -> None:
        try:
            cfg, strength_cfg = self._currency_strength_config()
            if not bool(cfg.get("enabled", False)):
                return

            snapshot = build_currency_strength_map(self.monitor_state, strength_cfg)
            out_dir = Path(str(cfg.get("output_dir", "reports/currency_strength") or "reports/currency_strength"))
            out_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now()
            day = stamp.strftime("%Y%m%d")

            if bool(cfg.get("write_csv", True)):
                currency_path = out_dir / f"currency_strength_{day}.csv"
                currency_fields = ["timestamp", "rank", "currency", "score", "votes"]
                write_header = not currency_path.exists()
                with currency_path.open("a", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(handle, fieldnames=currency_fields)
                    if write_header:
                        writer.writeheader()
                    for rank, row in enumerate(snapshot.get("ranking", []) or [], start=1):
                        writer.writerow(
                            {
                                "timestamp": stamp.isoformat(),
                                "rank": rank,
                                "currency": row.get("currency", ""),
                                "score": f"{float(row.get('score', 0.0) or 0.0):.6f}",
                                "votes": int(row.get("votes", 0) or 0),
                            }
                        )

                pair_path = out_dir / f"pair_strength_{day}.csv"
                tf_fields = [str(tf).upper() for tf in self.TIMEFRAMES]
                pair_fields = [
                    "timestamp", "symbol", "base", "quote", "classification", "pair_score",
                    "base_score", "quote_score", "raw_score", "votes",
                ] + tf_fields
                write_header = not pair_path.exists()
                with pair_path.open("a", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(handle, fieldnames=pair_fields)
                    if write_header:
                        writer.writeheader()
                    for symbol in sorted((snapshot.get("pair_scores") or {}).keys()):
                        row = snapshot["pair_scores"][symbol]
                        timeframes = row.get("timeframes", {}) or {}
                        payload = {
                            "timestamp": stamp.isoformat(),
                            "symbol": symbol,
                            "base": row.get("base", ""),
                            "quote": row.get("quote", ""),
                            "classification": row.get("classification", ""),
                            "pair_score": f"{float(row.get('pair_score', 0.0) or 0.0):.6f}",
                            "base_score": f"{float(row.get('base_score', 0.0) or 0.0):.6f}",
                            "quote_score": f"{float(row.get('quote_score', 0.0) or 0.0):.6f}",
                            "raw_score": f"{float(row.get('raw_score', 0.0) or 0.0):.6f}",
                            "votes": int(row.get("votes", 0) or 0),
                        }
                        for tf in tf_fields:
                            tf_row = timeframes.get(tf, {}) or {}
                            direction = str(tf_row.get("direction", "") or "")
                            contribution = float(tf_row.get("contribution", 0.0) or 0.0)
                            payload[tf] = f"{direction}:{contribution:.4f}" if direction else ""
                        writer.writerow(payload)

            if bool(cfg.get("write_json", True)):
                latest_path = out_dir / "currency_strength_latest.json"
                latest_path.write_text(
                    json.dumps(snapshot, ensure_ascii=False, indent=2, default=str),
                    encoding="utf-8",
                )
        except Exception as exc:
            self.logger.warning(f"Falha ao gravar currency_strength_map: {exc}")

    def _confidence_calibration_check(
        self,
        strategy_name: str,
        pred: int,
        broker_sym: str,
        sym_ia: str,
        tf: str,
        p_buy: float = 0.0,
        p_sell: float = 0.0,
    ) -> bool:
        cfg = self.config.get("entry_filters.confidence_calibration", {}) or {}
        if not bool(cfg.get("enabled", False)):
            return True
        if pred not in (1, 2):
            return True
        mode = str(cfg.get("mode", "shadow") or "shadow").lower()
        candidate = SignalCandidate(
            symbol=sym_ia.upper(),
            broker_symbol=broker_sym,
            timeframe=tf,
            side=self._prediction_side(pred),
            strategy=strategy_name,
            raw_prediction=pred,
            p_buy=float(p_buy or 0.0),
            p_sell=float(p_sell or 0.0),
        )
        engine = ConfidenceCalibrationEngine(
            CalibrationConfig(
                candidates_path=str(
                    cfg.get(
                        "candidates_path",
                        "reports/market_structure_calibration/market_structure_calibration_candidates_atr1.5_slatr1_lh100.csv",
                    )
                    or "reports/market_structure_calibration/market_structure_calibration_candidates_atr1.5_slatr1_lh100.csv"
                ),
                profiles_path=str(
                    cfg.get("profiles_path", "reports/confidence_calibration/confidence_calibration_profiles.json")
                    or "reports/confidence_calibration/confidence_calibration_profiles.json"
                ),
                min_samples=int(cfg.get("min_samples", 300) or 300),
                min_rules=int(cfg.get("min_rules", 2) or 2),
                raw_weight=float(cfg.get("raw_weight", 0.50) or 0.50),
                history_weight=float(cfg.get("history_weight", 0.50) or 0.50),
                prior_samples=int(cfg.get("prior_samples", 200) or 200),
                min_reliability=float(cfg.get("min_reliability", 0.45) or 0.45),
                use_profiles=bool(cfg.get("use_profiles", True)),
            )
        )
        output = engine.evaluate(candidate)
        self._decision_engine_outputs.append(output)
        if bool(cfg.get("log_each_check", False)):
            self.logger.info(
                f"{strategy_name.upper()} {sym_ia} {tf} confidence_calibration {mode}: "
                f"state={output.state} raw={output.features.get('raw_probability', 0.0):.3f} "
                f"cal={output.features.get('calibrated_probability', output.score):.3f}"
            )
        if mode == "shadow" or not output.negative_factors:
            return True
        reason_code = str(cfg.get("reason_code", "confidence_calibration") or "confidence_calibration")
        self._last_execution_block_reason = f"{reason_code}:{output.state}"
        return False

    def _meta_model_ensemble_check(
        self,
        strategy_name: str,
        pred: int,
        broker_sym: str,
        sym_ia: str,
        tf: str,
        p_buy: float = 0.0,
        p_sell: float = 0.0,
        model=None,
        approved_model=None,
        approved_status: str = "",
    ) -> bool:
        cfg = self.config.get("entry_filters.meta_model_ensemble", {}) or {}
        if not bool(cfg.get("enabled", False)):
            return True
        if pred not in (1, 2):
            return True
        mode = str(cfg.get("mode", "shadow") or "shadow").lower()
        candidate = SignalCandidate(
            symbol=sym_ia.upper(),
            broker_symbol=broker_sym,
            timeframe=tf,
            side=self._prediction_side(pred),
            strategy=strategy_name,
            raw_prediction=pred,
            p_buy=float(p_buy or 0.0),
            p_sell=float(p_sell or 0.0),
        )
        engine = MetaModelEnsembleEngine(
            MetaModelConfig(
                min_active_members=int(cfg.get("min_active_members", 2) or 2),
                max_conflict_ratio=float(cfg.get("max_conflict_ratio", 0.35) or 0.35),
                max_vote_concentration=float(cfg.get("max_vote_concentration", 0.70) or 0.70),
                min_avg_confidence=float(cfg.get("min_avg_confidence", 0.45) or 0.45),
                single_model_score=float(cfg.get("single_model_score", 0.45) or 0.45),
            )
        )
        output = engine.evaluate(
            candidate,
            model=model,
            approved_model=approved_model,
            approved_status=approved_status,
        )
        self._decision_engine_outputs.append(output)
        if bool(cfg.get("log_each_check", False)):
            self.logger.info(
                f"{strategy_name.upper()} {sym_ia} {tf} meta_model_ensemble {mode}: "
                f"state={output.state} score={output.score:.2f} "
                f"agreement={output.features.get('ensemble_agreement', 0.0):.2f} "
                f"active={output.features.get('active_members', 0)}"
            )
        if mode == "shadow" or not output.negative_factors:
            return True
        reason_code = str(cfg.get("reason_code", "meta_model_ensemble") or "meta_model_ensemble")
        self._last_execution_block_reason = f"{reason_code}:{output.state}"
        return False

    def _consensus_engine_check(
        self,
        strategy_name: str,
        pred: int,
        broker_sym: str,
        sym_ia: str,
        tf: str,
        p_buy: float = 0.0,
        p_sell: float = 0.0,
    ) -> bool:
        cfg = self.config.get("entry_filters.consensus_engine", {}) or {}
        if not bool(cfg.get("enabled", False)):
            return True
        mode = str(cfg.get("mode", "shadow") or "shadow").lower()
        candidate = SignalCandidate(
            symbol=sym_ia.upper(),
            broker_symbol=broker_sym,
            timeframe=tf,
            side=self._prediction_side(pred),
            strategy=strategy_name,
            raw_prediction=pred,
            p_buy=float(p_buy or 0.0),
            p_sell=float(p_sell or 0.0),
        )
        weights = cfg.get("weights", {}) or {}
        engine = ConsensusEngine(
            ConsensusConfig(
                weights={str(key): float(value) for key, value in weights.items()} if weights else ConsensusConfig().weights,
                min_consensus_score=float(cfg.get("min_consensus_score", 0.55) or 0.55),
                max_conflict_score=float(cfg.get("max_conflict_score", 0.35) or 0.35),
                weak_score_floor=float(cfg.get("weak_score_floor", 0.40) or 0.40),
            )
        )
        output = engine.evaluate(candidate, list(self._decision_engine_outputs))
        self._decision_engine_outputs.append(output)
        if bool(cfg.get("log_each_check", False)):
            self.logger.info(
                f"{strategy_name.upper()} {sym_ia} {tf} consensus_engine {mode}: "
                f"state={output.state} consensus={output.score:.2f} "
                f"conflict={output.features.get('conflict_score', 0.0):.2f}"
            )
        if mode == "shadow" or not output.negative_factors:
            return True
        reason_code = str(cfg.get("reason_code", "consensus_engine") or "consensus_engine")
        self._last_execution_block_reason = f"{reason_code}:{output.state}"
        return False

    def _opportunity_engine_check(
        self,
        strategy_name: str,
        pred: int,
        broker_sym: str,
        sym_ia: str,
        tf: str,
        p_buy: float = 0.0,
        p_sell: float = 0.0,
    ) -> bool:
        cfg = self._runtime_filter_config(
            "opportunity_engine",
            self.config.get("entry_filters.opportunity_engine", {}) or {},
            sym_ia,
            tf,
        )
        if not bool(cfg.get("enabled", False)):
            return True
        mode = str(cfg.get("mode", "shadow") or "shadow").lower()
        candidate = SignalCandidate(
            symbol=sym_ia.upper(),
            broker_symbol=broker_sym,
            timeframe=tf,
            side=self._prediction_side(pred),
            strategy=strategy_name,
            raw_prediction=pred,
            p_buy=float(p_buy or 0.0),
            p_sell=float(p_sell or 0.0),
        )
        weights = cfg.get("weights", {}) or {}
        engine = OpportunityEngine(
            OpportunityConfig(
                weights={str(key): float(value) for key, value in weights.items()} if weights else OpportunityConfig().weights,
                min_tradeability_score=float(cfg.get("min_tradeability_score", 0.55) or 0.55),
                marginal_tradeability_score=float(cfg.get("marginal_tradeability_score", 0.45) or 0.45),
                high_quality_score=float(cfg.get("high_quality_score", 0.70) or 0.70),
                max_conflict_score=float(cfg.get("max_conflict_score", 0.35) or 0.35),
                severe_conflict_penalty=float(cfg.get("severe_conflict_penalty", 0.18) or 0.18),
                warning_penalty=float(cfg.get("warning_penalty", 0.03) or 0.03),
                negative_penalty=float(cfg.get("negative_penalty", 0.06) or 0.06),
            )
        )
        output = engine.evaluate(candidate, list(self._decision_engine_outputs))
        self._decision_engine_outputs.append(output)
        if bool(cfg.get("log_each_check", False)):
            self.logger.info(
                f"{strategy_name.upper()} {sym_ia} {tf} opportunity_engine {mode}: "
                f"state={output.state} tradeability={output.score:.2f} "
                f"conflict={output.features.get('conflict_score', 0.0):.2f}"
            )
        if mode == "shadow" or not self._engine_state_should_block(cfg, output):
            return True
        relax_cfg = self.config.get("entry_filters.daytrade_relaxation", {}) or {}
        if self._should_relax_filter_for_daytrade(relax_cfg, "opportunity_engine", tf, p_buy, p_sell):
            self.logger.info(
                f"[DAYTRADE_RELAX] {strategy_name.upper()} {sym_ia} {tf} opportunity_engine relaxed for strong short-term edge"
            )
            return True
        reason_code = str(cfg.get("reason_code", "opportunity_engine") or "opportunity_engine")
        self._last_execution_block_reason = f"{reason_code}:{output.state}"
        return False

    def _factor_engine_check(
        self,
        strategy_name: str,
        pred: int,
        broker_sym: str,
        sym_ia: str,
        tf: str,
        p_buy: float = 0.0,
        p_sell: float = 0.0,
    ) -> bool:
        cfg = self._runtime_filter_config("factor_engine", self.config.get("entry_filters.factor_engine", {}) or {}, sym_ia, tf)
        if not bool(cfg.get("enabled", False)):
            return True
        if pred not in (1, 2):
            return True
        mode = str(cfg.get("mode", "shadow") or "shadow").lower()
        bars = max(100, int(cfg.get("bars", 120) or 120))
        frame = self.feature_calc.get_rates_frame(broker_sym, tf, bars, start_pos=0, min_rows=bars)
        candidate = SignalCandidate(
            symbol=sym_ia.upper(),
            broker_symbol=broker_sym,
            timeframe=tf,
            side=self._prediction_side(pred),
            strategy=strategy_name,
            raw_prediction=pred,
            p_buy=float(p_buy or 0.0),
            p_sell=float(p_sell or 0.0),
        )
        context: dict[str, Any] = {
            "symbol": sym_ia.upper(),
            "broker_symbol": broker_sym,
            "timeframe": tf,
            "side": self._prediction_side(pred),
            "strategy": strategy_name,
            "raw_prediction": pred,
            "p_buy": float(p_buy or 0.0),
            "p_sell": float(p_sell or 0.0),
            "closes": frame["close"].astype(float).tolist() if not frame.empty and "close" in frame.columns else [],
            "highs": frame["high"].astype(float).tolist() if not frame.empty and "high" in frame.columns else [],
            "lows": frame["low"].astype(float).tolist() if not frame.empty and "low" in frame.columns else [],
            "volumes": frame["tick_volume"].astype(float).tolist() if not frame.empty and "tick_volume" in frame.columns else [],
            "history_closes": frame["close"].astype(float).tolist() if not frame.empty and "close" in frame.columns else [],
        }
        enabled_factors = cfg.get("enabled_factors", []) or []
        if isinstance(enabled_factors, str):
            enabled_factors = [item.strip() for item in enabled_factors.split(",") if item.strip()]
        engine = FactorEngine(
            enabled_factors=enabled_factors,
            min_confidence=float(cfg.get("min_confidence", 0.15) or 0.15),
        )
        output = engine.evaluate(candidate, context)
        self._decision_engine_outputs.append(output)
        if bool(cfg.get("log_each_check", False)):
            self.logger.info(
                f"{strategy_name.upper()} {sym_ia} {tf} factor_engine {mode}: "
                f"state={output.state} score={output.score:.2f} conf={output.confidence:.2f} "
                f"aligned={len(output.positive_factors)} conflict={len(output.negative_factors)}"
            )
        if mode == "shadow" or not self._engine_state_should_block(cfg, output):
            return True
        reason_code = str(cfg.get("reason_code", "factor_engine") or "factor_engine")
        self._last_execution_block_reason = f"{reason_code}:{output.state}"
        return False

    def _market_briefing_check(
        self,
        strategy_name: str,
        pred: int,
        broker_sym: str,
        sym_ia: str,
        tf: str,
        p_buy: float = 0.0,
        p_sell: float = 0.0,
    ) -> bool:
        cfg = self._runtime_filter_config("market_briefing", self.config.get("entry_filters.market_briefing", {}) or {}, sym_ia, tf)
        if not bool(cfg.get("enabled", False)):
            return True
        if pred not in (1, 2):
            return True
        mode = str(cfg.get("mode", "shadow") or "shadow").lower()
        candidate = SignalCandidate(
            symbol=sym_ia.upper(),
            broker_symbol=broker_sym,
            timeframe=tf,
            side=self._prediction_side(pred),
            strategy=strategy_name,
            raw_prediction=pred,
            p_buy=float(p_buy or 0.0),
            p_sell=float(p_sell or 0.0),
        )
        engine = MarketBriefingEngine(
            MarketBriefingConfig(
                briefing_path=str(cfg.get("briefing_path", "config/market_briefing_today.json") or "config/market_briefing_today.json"),
                min_risk_to_block=str(cfg.get("min_risk_to_block", "EXTREMO") or "EXTREMO"),
                apply_expired_as_shadow=bool(cfg.get("apply_expired_as_shadow", True)),
                min_bias_strength=float(cfg.get("min_bias_strength", 0.35) or 0.35),
            )
        )
        output = engine.evaluate(candidate)
        self._decision_engine_outputs.append(output)
        self._last_market_briefing_reason = ""
        if output.state in {"block", "moderate"}:
            # Prefer explicit negative reasons, then positives; fallback to warnings for diagnosability
            factors = output.negative_factors or output.positive_factors or output.warnings or ["briefing"]
            self._last_market_briefing_reason = f"MB:shadow:{output.state}:{factors[0]}"
        if bool(cfg.get("log_each_check", True)) and output.state != "ok":
            factors = output.negative_factors or output.positive_factors or ["ok"]
            self.logger.info(
                f"{strategy_name.upper()} {sym_ia} {tf} market_briefing {mode}: "
                f"state={output.state} score={output.score:.2f} factors={','.join(factors[:2])}"
            )
        if mode == "shadow" or output.state != "block":
            return True
        reason_code = str(cfg.get("reason_code", "market_briefing") or "market_briefing")
        factor = (output.negative_factors or ["block"])[0]
        self._last_execution_block_reason = f"{reason_code}:{factor}"
        return False

    def _run_shadow_diagnostics(
        self,
        strategy_name: str,
        pred: int,
        broker_sym: str,
        sym_ia: str,
        tf: str,
        p_buy: float = 0.0,
        p_sell: float = 0.0,
        model=None,
        approved_model=None,
        approved_status: str = "",
    ) -> None:
        """Executa engines shadow mesmo quando a ordem nao pode ser enviada.

        Isso preserva a auditoria analitica quando o terminal esta com AutoTrading
        desligado, sem transformar filtros block em decisao operacional.
        """
        checks = [
            ("entry_filters.meta_model_ensemble", lambda: self._meta_model_ensemble_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell, model=model, approved_model=approved_model, approved_status=approved_status)),
            ("entry_filters.factor_engine", lambda: self._factor_engine_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell)),
            ("entry_filters.market_briefing", lambda: self._market_briefing_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell)),
            ("entry_filters.market_regime", lambda: self._market_regime_check(strategy_name, pred, broker_sym, sym_ia, tf)),
            ("entry_filters.volatility_engine", lambda: self._volatility_engine_check(strategy_name, broker_sym, sym_ia, tf)),
            ("entry_filters.session_context", lambda: self._session_context_check(strategy_name, pred, sym_ia, tf)),
            ("entry_filters.portfolio_exposure", lambda: self._portfolio_exposure_check(strategy_name, pred, sym_ia)),
            ("entry_filters.market_alignment", lambda: self._market_alignment_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell)),
            ("entry_filters.timeframe_consensus", lambda: self._timeframe_consensus_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell)),
            ("entry_filters.market_structure", lambda: self._market_structure_gate(strategy_name, pred, broker_sym, sym_ia, tf)),
            ("entry_filters.feature_engineering", lambda: self._feature_engineering_check(strategy_name, broker_sym, sym_ia, tf)),
            ("entry_filters.entry_timing", lambda: self._entry_timing_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell)),
            ("entry_filters.execution_engine", lambda: self._execution_engine_check(strategy_name, pred, broker_sym, sym_ia, tf)),
            ("entry_filters.risk_engine", lambda: self._risk_engine_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell)),
        ]
        engine_names = {
            "entry_filters.market_briefing": "market_briefing",
            "entry_filters.meta_model_ensemble": "meta_model_ensemble",
            "entry_filters.factor_engine": "factor_engine",
            "entry_filters.market_regime": "market_regime",
            "entry_filters.volatility_engine": "volatility_engine",
            "entry_filters.session_context": "session_context",
            "entry_filters.portfolio_exposure": "portfolio_exposure",
            "entry_filters.market_alignment": "market_alignment",
            "entry_filters.timeframe_consensus": "timeframe_consensus",
            "entry_filters.market_structure": "market_structure",
            "entry_filters.feature_engineering": "feature_engineering",
            "entry_filters.entry_timing": "entry_timing",
            "entry_filters.execution_engine": "execution_engine",
            "entry_filters.risk_engine": "risk_engine",
        }
        original_reason = self._last_execution_block_reason
        for cfg_path, check in checks:
            cfg = self.config.get(cfg_path, {}) or {}
            if not bool(cfg.get("enabled", False)):
                continue
            if str(cfg.get("mode", "shadow") or "shadow").lower() != "shadow":
                continue
            engine_name = engine_names.get(cfg_path, cfg_path.split(".")[-1])
            if any(output.engine == engine_name for output in self._decision_engine_outputs):
                continue
            try:
                check()
            except Exception as exc:
                self._record_engine_output(
                    engine=engine_name,
                    direction="NEUTRAL",
                    score=0.0,
                    confidence=0.0,
                    state="diagnostic_error",
                    warnings=[f"erro_diagnostico:{str(exc)[:60]}"],
                )
        try:
            context_cfg = self.config.get("entry_filters.context_engine", {}) or {}
            if (
                bool(context_cfg.get("enabled", False))
                and str(context_cfg.get("mode", "shadow") or "shadow").lower() == "shadow"
                and not any(output.engine == "context_engine" for output in self._decision_engine_outputs)
            ):
                self._context_engine_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell)
            calibration_cfg = self.config.get("entry_filters.confidence_calibration", {}) or {}
            if (
                bool(calibration_cfg.get("enabled", False))
                and str(calibration_cfg.get("mode", "shadow") or "shadow").lower() == "shadow"
                and not any(output.engine == "confidence_calibration" for output in self._decision_engine_outputs)
            ):
                self._confidence_calibration_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell)
            consensus_cfg = self.config.get("entry_filters.consensus_engine", {}) or {}
            if (
                bool(consensus_cfg.get("enabled", False))
                and str(consensus_cfg.get("mode", "shadow") or "shadow").lower() == "shadow"
                and not any(output.engine == "consensus_engine" for output in self._decision_engine_outputs)
            ):
                self._consensus_engine_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell)
            opportunity_cfg = self.config.get("entry_filters.opportunity_engine", {}) or {}
            if (
                bool(opportunity_cfg.get("enabled", False))
                and str(opportunity_cfg.get("mode", "shadow") or "shadow").lower() == "shadow"
                and not any(output.engine == "opportunity_engine" for output in self._decision_engine_outputs)
            ):
                self._opportunity_engine_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell)
            brain_cfg = self.config.get("entry_filters.context_brain", {}) or {}
            if (
                bool(brain_cfg.get("enabled", False))
                and str(brain_cfg.get("mode", "shadow") or "shadow").lower() == "shadow"
                and not any(output.engine == "context_brain" for output in self._decision_engine_outputs)
            ):
                self._context_brain_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell)
        finally:
            self._last_execution_block_reason = original_reason

    def _audit_block_with_shadow(
        self,
        strategy_name: str,
        pred: int,
        broker_sym: str,
        sym_ia: str,
        tf: str,
        reason: str,
        p_buy: float = 0.0,
        p_sell: float = 0.0,
        extra: dict | None = None,
    ) -> None:
        self._last_execution_block_reason = reason
        self._run_shadow_diagnostics(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell)
        self._last_execution_block_reason = reason
        self._audit_decision_event(
            strategy_name,
            pred,
            broker_sym,
            sym_ia,
            tf,
            "BLOCK",
            self._last_execution_block_reason,
            p_buy,
            p_sell,
            extra=extra,
        )

    def _audit_strategy_block_with_shadow(
        self,
        strategy_name: str,
        pred: int,
        broker_sym: str,
        sym_ia: str,
        tf: str,
        reason: str,
        p_buy: float = 0.0,
        p_sell: float = 0.0,
        model=None,
        approved_model=None,
        approved_status: str = "",
        extra: dict | None = None,
    ) -> None:
        self._decision_engine_outputs = []
        self._last_execution_block_reason = reason
        self._run_shadow_diagnostics(
            strategy_name,
            pred,
            broker_sym,
            sym_ia,
            tf,
            p_buy,
            p_sell,
            model=model,
            approved_model=approved_model,
            approved_status=approved_status,
        )
        self._last_execution_block_reason = reason
        self._audit_decision_event(
            strategy_name,
            pred,
            broker_sym,
            sym_ia,
            tf,
            "BLOCK",
            reason,
            p_buy,
            p_sell,
            extra=extra,
        )

    def _entry_timing_check(
        self,
        strategy_name: str,
        pred: int,
        broker_sym: str,
        sym_ia: str,
        tf: str,
        p_buy: float = 0.0,
        p_sell: float = 0.0,
    ) -> bool:
        cfg = self._runtime_filter_config(
            "entry_timing",
            self.config.get("entry_filters.entry_timing", {}) or {},
            sym_ia,
            tf,
        )
        if not bool(cfg.get("enabled", False)):
            return True
        if pred not in (1, 2):
            return True
        if mt5 is None:
            return True
        mode = str(cfg.get("mode", "shadow") or "shadow").lower()
        bars = max(100, int(cfg.get("bars", 260) or 260))
        frame = self._market_structure_rates(broker_sym, tf, bars)
        engine = EntryTimingEngine(
            EntryTimingConfig(
                bars=bars,
                top_bottom_distance_atr=float(cfg.get("top_bottom_distance_atr", 0.35) or 0.35),
                extension_atr=float(cfg.get("extension_atr", 1.20) or 1.20),
                require_valid_breakout=bool(cfg.get("require_valid_breakout", True)),
                breakout_max_bars=int(cfg.get("breakout_max_bars", 2) or 2),
                min_breakout_volume_ratio=float(cfg.get("min_breakout_volume_ratio", 1.10) or 1.10),
            )
        )
        output = engine.evaluate(frame, self._prediction_side(pred))
        self._decision_engine_outputs.append(output)
        features = output.features or {}
        buy_at_top = pred == 1 and (bool(features.get("near_top", False)) or bool(features.get("buy_extended", False)))
        sell_at_bottom = pred == 2 and (bool(features.get("near_bottom", False)) or bool(features.get("sell_extended", False)))
        valid_extreme_breakout = (
            (pred == 1 and bool(features.get("valid_buy_break", False)))
            or (pred == 2 and bool(features.get("valid_sell_break", False)))
        )
        if bool(cfg.get("block_extreme_entries", True)) and (buy_at_top or sell_at_bottom) and not valid_extreme_breakout:
            relax_cfg = self.config.get("entry_filters.daytrade_relaxation", {}) or {}
            if self._should_relax_filter_for_daytrade(relax_cfg, "entry_timing", tf, p_buy, p_sell):
                self.logger.info(
                    f"[DAYTRADE_RELAX] {strategy_name.upper()} {sym_ia} {tf} entry_timing relaxed for strong short-term edge"
                )
                return True
            reason_code = str(cfg.get("reason_code", "entry_timing") or "entry_timing")
            factor = "comprar_topo_sem_rompimento_validado" if buy_at_top else "vender_fundo_sem_rompimento_validado"
            self._last_execution_block_reason = f"{reason_code}:{factor}"
            self.logger.info(
                f"{strategy_name.upper()} {sym_ia} {tf} bloqueada por extremo sem rompimento validado: "
                f"{factor} state={output.state}"
            )
            return mode == "shadow"
        if bool(cfg.get("log_each_check", True)) and output.state not in {"ok", "validated_breakout_buy", "validated_breakout_sell"}:
            factors = output.negative_factors or output.positive_factors or [output.state]
            self.logger.info(
                f"{strategy_name.upper()} {sym_ia} {tf} entry_timing {mode}: "
                f"state={output.state} score={output.score:.2f} factors={','.join(factors[:2])}"
            )
        if mode == "shadow" or not output.negative_factors:
            return True
        relax_cfg = self.config.get("entry_filters.daytrade_relaxation", {}) or {}
        if self._should_relax_filter_for_daytrade(relax_cfg, "entry_timing", tf, p_buy, p_sell):
            self.logger.info(
                f"[DAYTRADE_RELAX] {strategy_name.upper()} {sym_ia} {tf} entry_timing relaxed for strong short-term edge"
            )
            return True
        reason_code = str(cfg.get("reason_code", "entry_timing") or "entry_timing")
        factor = output.negative_factors[0]
        self._last_execution_block_reason = f"{reason_code}:{factor}"
        return False

    def _execution_engine_check(
        self,
        strategy_name: str,
        pred: int,
        broker_sym: str,
        sym_ia: str,
        tf: str,
        p_buy: float = 0.0,
        p_sell: float = 0.0,
    ) -> bool:
        cfg = self._runtime_filter_config(
            "execution_engine",
            self.config.get("entry_filters.execution_engine", {}) or {},
            sym_ia,
            tf,
        )
        if not bool(cfg.get("enabled", False)):
            return True
        if pred not in (1, 2):
            return True
        if mt5 is None:
            return True
        mode = str(cfg.get("mode", "shadow") or "shadow").lower()
        bars = max(100, int(cfg.get("bars", 180) or 180))
        frame = self._market_structure_rates(broker_sym, tf, bars)
        engine = ExecutionEngine(
            ExecutionConfig(
                bars=bars,
                min_entry_quality_score=float(cfg.get("min_entry_quality_score", 0.55) or 0.55),
                min_breakout_quality_score=float(cfg.get("min_breakout_quality_score", 0.60) or 0.60),
                min_volume_ratio=float(cfg.get("min_volume_ratio", 0.80) or 0.80),
                exhaustion_streak=int(cfg.get("exhaustion_streak", 5) or 5),
                fake_breakout_max_bars=int(cfg.get("fake_breakout_max_bars", 3) or 3),
            )
        )
        output = engine.evaluate(frame, self._prediction_side(pred))
        self._decision_engine_outputs.append(output)
        if bool(cfg.get("log_each_check", True)) and output.state not in {"good_execution", "acceptable_with_warnings"}:
            factors = output.negative_factors or output.positive_factors or [output.state]
            self.logger.info(
                f"{strategy_name.upper()} {sym_ia} {tf} execution_engine {mode}: "
                f"state={output.state} score={output.score:.2f} factors={','.join(factors[:2])}"
            )
        if mode == "shadow" or not output.negative_factors:
            return True
        relax_cfg = self.config.get("entry_filters.daytrade_relaxation", {}) or {}
        if self._should_relax_filter_for_daytrade(relax_cfg, "execution_engine", tf, p_buy, p_sell):
            self.logger.info(
                f"[DAYTRADE_RELAX] {strategy_name.upper()} {sym_ia} {tf} execution_engine relaxed for strong short-term edge"
            )
            return True
        reason_code = str(cfg.get("reason_code", "execution_engine") or "execution_engine")
        factor = output.negative_factors[0]
        self._last_execution_block_reason = f"{reason_code}:{factor}"
        return False

    def _risk_engine_account_snapshot(self) -> dict:
        if mt5 is None:
            return {}
        account = mt5.account_info()
        if account is None:
            return {}
        return {
            "login": getattr(account, "login", 0),
            "balance": float(getattr(account, "balance", 0.0) or 0.0),
            "equity": float(getattr(account, "equity", 0.0) or 0.0),
            "profit": float(getattr(account, "profit", 0.0) or 0.0),
            "margin": float(getattr(account, "margin", 0.0) or 0.0),
            "margin_free": float(getattr(account, "margin_free", 0.0) or 0.0),
            "margin_level": float(getattr(account, "margin_level", 0.0) or 0.0),
        }

    def _risk_engine_positions_snapshot(self) -> list[dict]:
        if mt5 is None:
            return []
        positions = mt5.positions_get()
        if not positions:
            return []
        rows = []
        for pos in positions:
            pos_type = int(getattr(pos, "type", -1))
            if pos_type == mt5.ORDER_TYPE_BUY:
                direction = "BUY"
            elif pos_type == mt5.ORDER_TYPE_SELL:
                direction = "SELL"
            else:
                direction = "UNKNOWN"
            rows.append(
                {
                    "symbol": self._broker_symbol_to_base(str(getattr(pos, "symbol", ""))),
                    "broker_symbol": str(getattr(pos, "symbol", "")),
                    "direction": direction,
                    "volume": float(getattr(pos, "volume", 0.0) or 0.0),
                    "profit": float(getattr(pos, "profit", 0.0) or 0.0),
                    "magic": int(getattr(pos, "magic", 0) or 0),
                    "ticket": int(getattr(pos, "ticket", 0) or 0),
                }
            )
        return rows

    def _swap_filter_check(
        self,
        strategy_name: str,
        pred: int,
        broker_sym: str,
        sym_ia: str,
        tf: str,
        p_buy: float = 0.0,
        p_sell: float = 0.0,
        swap_long: float = 0.0,
        swap_short: float = 0.0,
    ) -> bool:
        """SWAP filtro removido do sistema. Não bloqueia ordens em qualquer condição."""
        _ = (strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell, swap_long, swap_short)
        self._last_execution_block_reason = ""
        self._record_engine_output(
            engine="swap_filter",
            direction=self._prediction_side(pred),
            score=1.0,
            confidence=1.0,
            state="disabled",
            positive_factors=["swap_filter_disabled"],
            negative_factors=[],
        )
        return True

    def _risk_engine_check(
        self,
        strategy_name: str,
        pred: int,
        broker_sym: str,
        sym_ia: str,
        tf: str,
        p_buy: float = 0.0,
        p_sell: float = 0.0,
    ) -> bool:
        cfg = self._runtime_filter_config(
            "risk_engine",
            self.config.get("entry_filters.risk_engine", {}) or {},
            sym_ia,
            tf,
        )
        if not bool(cfg.get("enabled", False)):
            return True
        mode = str(cfg.get("mode", "shadow") or "shadow").lower()
        candidate = SignalCandidate(
            symbol=sym_ia.upper(),
            broker_symbol=broker_sym,
            timeframe=tf,
            side=self._prediction_side(pred),
            strategy=strategy_name,
            raw_prediction=pred,
            p_buy=float(p_buy or 0.0),
            p_sell=float(p_sell or 0.0),
        )
        engine = RiskEngine(
            RiskConfig(
                max_drawdown_pct=float(cfg.get("max_drawdown_pct", 8.0) or 8.0),
                warning_drawdown_pct=float(cfg.get("warning_drawdown_pct", 4.0) or 4.0),
                max_floating_loss_pct=float(cfg.get("max_floating_loss_pct", 5.0) or 5.0),
                warning_floating_loss_pct=float(cfg.get("warning_floating_loss_pct", 2.5) or 2.5),
                max_open_positions=int(cfg.get("max_open_positions", 12) or 12),
                max_losing_positions=int(cfg.get("max_losing_positions", 6) or 6),
                min_margin_level_pct=float(cfg.get("min_margin_level_pct", 250.0) or 250.0),
                warning_margin_level_pct=float(cfg.get("warning_margin_level_pct", 400.0) or 400.0),
                max_margin_usage_pct=float(cfg.get("max_margin_usage_pct", 35.0) or 35.0),
                warning_margin_usage_pct=float(cfg.get("warning_margin_usage_pct", 25.0) or 25.0),
                max_currency_risk_units=float(cfg.get("max_currency_risk_units", 5.0) or 5.0),
                warning_currency_risk_units=float(cfg.get("warning_currency_risk_units", 3.0) or 3.0),
                max_symbol_positions=int(cfg.get("max_symbol_positions", 1) or 1),
                max_same_direction_positions=int(cfg.get("max_same_direction_positions", 4) or 4),
                high_conflict_threshold=float(cfg.get("high_conflict_threshold", 0.35) or 0.35),
                moderate_conflict_threshold=float(cfg.get("moderate_conflict_threshold", 0.22) or 0.22),
                low_opportunity_threshold=float(cfg.get("low_opportunity_threshold", 0.45) or 0.45),
                low_feature_quality_threshold=float(cfg.get("low_feature_quality_threshold", 0.55) or 0.55),
                min_multiplier=float(cfg.get("min_multiplier", 0.25) or 0.25),
            )
        )
        output = engine.evaluate(
            candidate,
            list(self._decision_engine_outputs),
            account=self._risk_engine_account_snapshot(),
            positions=self._risk_engine_positions_snapshot(),
        )
        # If floating loss in dollars is below configured money limit, remove
        # blocking-only factors related to position counts so they don't prevent
        # new openings. This enforces the operator rule: "não bloquear por
        # muitas posições negativas a menos que drawdown > limite ($70 por padrão)".
        money_limit = float(cfg.get("max_floating_loss_money", 70.0) or 70.0)
        floating_profit = float((output.features or {}).get("floating_profit", 0.0) or 0.0)
        floating_loss = max(0.0, -floating_profit)
        if floating_loss < money_limit:
            neg = [str(item or "") for item in (output.negative_factors or [])]
            filtered = [f for f in neg if not (f.startswith("muitas_posicoes") or f.startswith("muitas_posicoes_negativas"))]
            # update output in-place
            output.negative_factors = filtered
        self._decision_engine_outputs.append(output)
        if bool(cfg.get("log_each_check", True)) and output.state != "normal_risk":
            # Only show negative or positive factors in the short "factors" field.
            # Warnings should not be rendered here to avoid implying a blocking reason.
            factors = output.negative_factors or output.positive_factors or [output.state]
            self.logger.info(
                f"{strategy_name.upper()} {sym_ia} {tf} risk_engine {mode}: "
                f"state={output.state} score={output.score:.2f} "
                f"mult={output.features.get('position_multiplier_suggested', 1.0):.2f} "
                f"factors={','.join(factors[:2])}"
            )
        if mode == "shadow" or not self._engine_state_should_block(cfg, output):
            return True
        reason_code = str(cfg.get("reason_code", "risk_engine") or "risk_engine")
        factor = output.negative_factors[0] if output.negative_factors else output.state
        self._last_execution_block_reason = f"{reason_code}:{factor}"
        return False

    def _strategy_group_exposure_allowed(self, strategy_name: str, sym_ia: str, pred: int) -> bool:
        return self.strategy_service._strategy_group_exposure_allowed(strategy_name, sym_ia, pred)

    def _mt5_trading_allowed(self) -> tuple[bool, str]:
        if mt5 is None:
            return False, "mt5_indisponivel"
        terminal = mt5.terminal_info()
        if terminal is None:
            return False, "terminal_indisponivel"
        terminal_allowed = getattr(terminal, "trade_allowed", None)
        if terminal_allowed is False:
            return False, "autotrading_desativado_terminal"
        account = mt5.account_info()
        if account is not None:
            account_allowed = getattr(account, "trade_allowed", None)
            if account_allowed is False:
                return False, "trade_desativado_conta"
        return True, ""

    def _market_structure_tf_code(self, tf: str):
        if mt5 is None:
            return None
        return {
            "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1
        }.get(str(tf).upper())

    def _market_structure_rates(self, broker_sym: str, tf: str, bars: int) -> pd.DataFrame:
        frame = self.feature_calc.get_rates_frame(broker_sym, tf, bars, start_pos=0, min_rows=50)
        if frame.empty or len(frame) < 50:
            return pd.DataFrame()
        return frame

    def _feature_engineering_check(self, strategy_name: str, broker_sym: str, sym_ia: str, tf: str) -> bool:
        cfg = self.config.get("entry_filters.feature_engineering", {}) or {}
        if not bool(cfg.get("enabled", False)):
            return True
        mode = str(cfg.get("mode", "shadow") or "shadow").lower()
        bars = int(cfg.get("bars", 260) or 260)
        frame = self._market_structure_rates(broker_sym, tf, bars)
        engine = FeatureEngineeringEngine(
            FeatureEngineeringConfig(
                bars=bars,
                min_feature_coverage=float(cfg.get("min_feature_coverage", 0.72) or 0.72),
                min_family_coverage=float(cfg.get("min_family_coverage", 0.60) or 0.60),
                max_nan_critical=int(cfg.get("max_nan_critical", 3) or 3),
            )
        )
        output = engine.evaluate(frame)
        self._decision_engine_outputs.append(output)
        if bool(cfg.get("log_each_check", False)) and output.state != "feature_quality_ok":
            self.logger.info(
                f"{strategy_name.upper()} {sym_ia} {tf} feature_engineering {mode}: "
                f"state={output.state} score={output.score:.2f} "
                f"coverage={output.features.get('feature_coverage', 0.0):.2f}"
            )
        if mode == "shadow" or not output.negative_factors:
            return True
        reason_code = str(cfg.get("reason_code", "feature_engineering") or "feature_engineering")
        self._last_execution_block_reason = f"{reason_code}:{output.state}"
        return False

    @staticmethod
    def _market_structure_float(row: pd.Series, key: str, default: float = 0.0) -> float:
        value = row.get(key, default)
        try:
            value = float(value)
        except (TypeError, ValueError):
            return default
        return value if np.isfinite(value) else default

    @staticmethod
    def _market_structure_time_value(frame: pd.DataFrame) -> str:
        if frame.empty or "time" not in frame.columns:
            return ""
        value = frame["time"].iloc[-1]
        if pd.isna(value):
            return ""
        try:
            return pd.Timestamp(value).isoformat()
        except Exception:
            return str(value)

    def _market_structure_analyze_row(self, row: pd.Series, tf: str, cfg: dict) -> dict:
        min_range_to_atr = float(cfg.get("min_range_to_atr", 0.60) or 0.60)
        max_overlap = float(cfg.get("max_overlap_ratio_10", 0.65) or 0.65)
        penalties = cfg.get("score_penalties", {}) or {}
        score = 1.0
        reasons = []

        range_to_atr = self._market_structure_float(row, "range_to_atr", np.nan)
        overlap_ratio = self._market_structure_float(row, "overlap_ratio_10", 0.0)
        volatility_compression = int(self._market_structure_float(row, "volatility_compression", 0))
        volatility_expansion = int(self._market_structure_float(row, "volatility_expansion", 0))
        regime_consolidation = int(self._market_structure_float(row, "regime_consolidation", 0))
        regime_trend = int(self._market_structure_float(row, "regime_trend", 0))
        regime_expansion = int(self._market_structure_float(row, "regime_expansion", 0))
        institutional_score = self._market_structure_float(row, "institutional_structure_score", np.nan)
        stop_hunt_up = int(self._market_structure_float(row, "stop_hunt_up", 0))
        stop_hunt_down = int(self._market_structure_float(row, "stop_hunt_down", 0))
        bullish_fvg = int(self._market_structure_float(row, "bullish_fvg", 0))
        bearish_fvg = int(self._market_structure_float(row, "bearish_fvg", 0))
        bullish_imbalance = int(self._market_structure_float(row, "bullish_imbalance", 0))
        bearish_imbalance = int(self._market_structure_float(row, "bearish_imbalance", 0))
        displacement_up = int(self._market_structure_float(row, "displacement_up", 0))
        displacement_down = int(self._market_structure_float(row, "displacement_down", 0))
        bos_up = int(self._market_structure_float(row, "break_of_structure_up", 0))
        bos_down = int(self._market_structure_float(row, "break_of_structure_down", 0))
        choch_up = int(self._market_structure_float(row, "change_of_character_up", 0))
        choch_down = int(self._market_structure_float(row, "change_of_character_down", 0))
        bullish_sequence = int(self._market_structure_float(row, "bullish_structure_sequence", 0))
        bearish_sequence = int(self._market_structure_float(row, "bearish_structure_sequence", 0))

        if not np.isfinite(range_to_atr):
            reasons.append("sem_atr")
            score -= float(penalties.get("missing_data", 0.50) or 0.50)
        elif range_to_atr < min_range_to_atr:
            reasons.append("vol_baixa")
            score -= float(penalties.get("low_volatility", 0.30) or 0.30)

        if bool(cfg.get("flag_consolidation", True)) and (regime_consolidation == 1 or overlap_ratio >= max_overlap):
            reasons.append("consolidacao")
            score -= float(penalties.get("consolidation", 0.30) or 0.30)

        if bool(cfg.get("flag_compression", True)) and volatility_compression == 1 and volatility_expansion == 0:
            reasons.append("compressao")
            score -= float(penalties.get("compression", 0.20) or 0.20)

        if bool(cfg.get("flag_stop_hunt", True)) and (stop_hunt_up == 1 or stop_hunt_down == 1):
            reasons.append("stop_hunt")
            score -= float(penalties.get("stop_hunt", 0.20) or 0.20)

        if bool(cfg.get("use_institutional_score", True)) and np.isfinite(institutional_score):
            min_institutional_score = float(cfg.get("min_institutional_structure_score", 0.42) or 0.42)
            if institutional_score < min_institutional_score:
                reasons.append("estrutura_fraca")
                score -= float(penalties.get("weak_institutional_structure", 0.15) or 0.15)
            score = min(score, max(0.0, float(institutional_score) + 0.20))

        if regime_expansion == 1 or volatility_expansion == 1:
            regime = "expansao"
        elif regime_consolidation == 1:
            regime = "consolidacao"
        elif regime_trend == 1:
            regime = "tendencia"
        else:
            regime = "neutro"

        score = max(0.0, min(1.0, score))
        return {
            "timeframe": tf,
            "market_regime": regime,
            "range_to_atr": None if not np.isfinite(range_to_atr) else range_to_atr,
            "overlap_ratio_10": overlap_ratio,
            "volatility_compression": volatility_compression,
            "volatility_expansion": volatility_expansion,
            "regime_consolidation": regime_consolidation,
            "regime_trend": regime_trend,
            "regime_expansion": regime_expansion,
            "institutional_structure_score": None if not np.isfinite(institutional_score) else institutional_score,
            "stop_hunt_up": stop_hunt_up,
            "stop_hunt_down": stop_hunt_down,
            "bullish_fvg": bullish_fvg,
            "bearish_fvg": bearish_fvg,
            "bullish_imbalance": bullish_imbalance,
            "bearish_imbalance": bearish_imbalance,
            "displacement_up": displacement_up,
            "displacement_down": displacement_down,
            "break_of_structure_up": bos_up,
            "break_of_structure_down": bos_down,
            "change_of_character_up": choch_up,
            "change_of_character_down": choch_down,
            "bullish_structure_sequence": bullish_sequence,
            "bearish_structure_sequence": bearish_sequence,
            "market_structure_score": score,
            "market_structure_reasons": reasons or ["ok"],
        }

    def _market_structure_log_shadow(self, payload: dict, cfg: dict) -> None:
        if not bool(cfg.get("log_each_check", True)):
            return
        log_dir = Path(cfg.get("shadow_log_dir", "logs/market_structure_shadow"))
        if not log_dir.is_absolute():
            log_dir = Path.cwd() / log_dir
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            path = log_dir / f"market_structure_shadow_{datetime.now().strftime('%Y%m%d')}.jsonl"
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
        except Exception as exc:
            self.logger.warning(f"Falha ao gravar market_structure shadow log: {exc}")

    def _market_structure_gate(
        self,
        strategy_name: str,
        pred: int,
        broker_sym: str,
        sym_ia: str,
        tf: str,
        p_buy: float = 0.0,
        p_sell: float = 0.0,
    ) -> bool:
        cfg = self._runtime_filter_config("market_structure", self.config.get("entry_filters.market_structure", {}) or {}, sym_ia, tf)
        self._last_market_structure_reason = ""
        self._last_market_structure_snapshot = {}
        if not bool(cfg.get("enabled", False)):
            return True
        mode = str(cfg.get("mode", "shadow") or "shadow").lower()
        bars = max(80, int(cfg.get("bars", 260) or 260))
        requested_tfs = cfg.get("timeframes", ["current", "M5", "M15"]) or ["current", "M5", "M15"]
        actual_tfs = []
        for item in requested_tfs:
            item = str(item).upper()
            actual_tf = tf.upper() if item == "CURRENT" else item
            if actual_tf not in actual_tfs:
                actual_tfs.append(actual_tf)

        snapshots = []
        all_reasons = []
        analysis_candle_times = {}
        signal_candle_time = ""
        for actual_tf in actual_tfs:
            frame = self._market_structure_rates(broker_sym, actual_tf, bars)
            if frame.empty:
                snapshots.append({
                    "timeframe": actual_tf,
                    "market_regime": "sem_dados",
                    "market_structure_score": 0.0,
                    "market_structure_reasons": ["sem_dados"],
                })
                all_reasons.append(f"{actual_tf}:sem_dados")
                continue
            candle_time = self._market_structure_time_value(frame)
            analysis_candle_times[actual_tf] = candle_time
            if actual_tf == tf.upper() and not signal_candle_time:
                signal_candle_time = candle_time
            try:
                features = build_market_structure_features(
                    frame,
                    config=MarketStructureConfig(
                        atr_period=int(self.config.get("market_structure_features.atr_period", 14) or 14),
                        volume_window=int(self.config.get("market_structure_features.volume_window", 20) or 20),
                        compression_window=int(self.config.get("market_structure_features.compression_window", 10) or 10),
                        support_resistance_window=int(self.config.get("market_structure_features.support_resistance_window", 20) or 20),
                    ),
                )
                if features.empty:
                    raise ValueError("features_vazias")
                snapshot = self._market_structure_analyze_row(features.tail(1).iloc[0], actual_tf, cfg)
                snapshot["candle_time"] = candle_time
            except Exception as exc:
                snapshot = {
                    "timeframe": actual_tf,
                    "market_regime": "erro",
                    "market_structure_score": 0.0,
                    "market_structure_reasons": [f"erro:{str(exc)[:40]}"],
                    "candle_time": candle_time,
                }
            snapshots.append(snapshot)
            for reason in snapshot.get("market_structure_reasons", []):
                if reason != "ok":
                    all_reasons.append(f"{actual_tf}:{reason}")

        aggregate_score = min((float(item.get("market_structure_score", 0.0)) for item in snapshots), default=0.0)
        short_reasons = all_reasons or ["ok"]
        reason_token = "MS:shadow:" + ("+".join(short_reasons[:3]) if mode == "shadow" else "+".join(short_reasons[:3]))
        self._last_market_structure_reason = reason_token
        self._last_market_structure_snapshot = {
            "timestamp": datetime.now().isoformat(),
            "mode": mode,
            "strategy": strategy_name,
            "symbol": sym_ia,
            "broker_symbol": broker_sym,
            "timeframe": tf,
            "signal_candle_time": signal_candle_time,
            "analysis_candle_times": analysis_candle_times,
            "prediction": pred,
            "aggregate_score": aggregate_score,
            "reasons": short_reasons,
            "snapshots": snapshots,
        }
        self._market_structure_log_shadow(self._last_market_structure_snapshot, cfg)

        if bool(cfg.get("log_to_main", cfg.get("log_each_check", True))):
            direction = "BUY" if pred == 1 else "SELL" if pred == 2 else "NEUTRO"
            self.logger.info(
                f"{strategy_name.upper()} {sym_ia} {tf} {direction} market_structure {mode}: "
                f"score={aggregate_score:.2f} reasons={','.join(short_reasons[:5])}"
            )

        ms_direction = "NEUTRAL"
        self._record_engine_output(
            engine="market_structure",
            direction=ms_direction,
            score=aggregate_score,
            confidence=aggregate_score,
            state="shadow" if mode == "shadow" else "gate",
            positive_factors=["market_structure_ok"] if short_reasons == ["ok"] else [],
            negative_factors=[] if short_reasons == ["ok"] else [str(item) for item in short_reasons],
            warnings=[] if mode != "shadow" else [f"shadow:{'+'.join(short_reasons[:3])}"],
            features={
                "mode": mode,
                "aggregate_score": aggregate_score,
                "reasons": short_reasons,
                "signal_candle_time": signal_candle_time,
            },
        )
        if mode == "shadow":
            return True
        if short_reasons == ["ok"]:
            return True
        relax_cfg = self.config.get("entry_filters.daytrade_relaxation", {}) or {}
        if self._should_relax_filter_for_daytrade(relax_cfg, "market_structure", tf, p_buy, p_sell):
            self.logger.info(
                f"[DAYTRADE_RELAX] {strategy_name.upper()} {sym_ia} {tf} market_structure relaxed for strong short-term edge"
            )
            return True
        self._last_execution_block_reason = "market_structure_block"
        return False

    def _execute_strategy_order(self, strategy_name: str, pred: int, broker_sym: str,
                                sym_ia: str, tf: str, feature_row: dict = None,
                                p_buy: float = 0.0, p_sell: float = 0.0,
                                model=None, approved_model=None, approved_status: str = ""):
        self._decision_engine_outputs = []
        orders_allowed, orders_source = self._fusion_orders_allowed()
        if not orders_allowed:
            self._last_execution_block_reason = orders_source
            self.logger.info(f"Novas ordens bloqueadas por {orders_source}: {strategy_name} {sym_ia} {tf}")
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        runtime_symbol_ok, runtime_symbol_reason = self._runtime_symbol_allowed(sym_ia)
        if not runtime_symbol_ok:
            self._last_execution_block_reason = runtime_symbol_reason
            self.logger.info(f"Ordem bloqueada por runtime: {strategy_name} {sym_ia} {tf} | {runtime_symbol_reason}")
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        trading_allowed, trading_block_reason = self._mt5_trading_allowed()
        if not trading_allowed:
            self._last_execution_block_reason = trading_block_reason
            self._run_shadow_diagnostics(
                strategy_name,
                pred,
                broker_sym,
                sym_ia,
                tf,
                p_buy,
                p_sell,
                model=model,
                approved_model=approved_model,
                approved_status=approved_status,
            )
            self._last_execution_block_reason = trading_block_reason
            self.logger.info(f"{strategy_name.upper()} {sym_ia} {tf} bloqueada: {trading_block_reason}")
            self._audit_decision_event(strategy_name, pred, broker_sym, sym_ia, tf, "BLOCK", self._last_execution_block_reason, p_buy, p_sell)
            return None

        cfg = self._strategy_config(strategy_name)
        tf_minutes = self.TF_MINUTES.get(tf, 5)
        magic = self._strategy_magic(strategy_name, tf)
        max_positions = self._strategy_max_positions(strategy_name)
        tag = {
            "strategy1": "S1",
            "strategy2": "S2",
            "strategy3": "S3",
            "strategy4": "S4",
            "strategy5": "S5",
            "strategy6": "S6",
            "strategy7": "S7",
            "strategy8": "S8",
            "strategy9": "S9",
            "strategy10": "S10",
            "strategy11": "S11",
            "strategy12": "S12",
            "strategy13": "S13",
            "strategy14": "S14",
        }.get(strategy_name, strategy_name.upper())
        mode = f"FUSION_{tag}_{tf}"
        magic_group = None
        limit_scope = self._position_limit_scope(strategy_name)
        count_system_symbol = limit_scope == "system"
        if limit_scope == "strategy":
            magic_group = self._strategy_magic_group(strategy_name)
        count_any_direction = self._position_limit_any_direction(strategy_name)
        tp_points = 0
        sl_points = int(cfg.get("sl_points", cfg.get("default_sl_points", self.config.get("risk.default_sl_points", 100))))

        self._last_execution_block_reason = ""
        if not self._run_gate_check(
            strategy_name,
            pred,
            broker_sym,
            sym_ia,
            tf,
            "historical_price_acceptance",
            lambda: self._historical_price_acceptance_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell),
        ):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "historical_price_out_of_domain"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        # historical decision gate: optional higher-level decision combining acceptance, zones, recency and MTF
        if not self._run_gate_check(
            strategy_name,
            pred,
            broker_sym,
            sym_ia,
            tf,
            "historical_decision",
            lambda: self._historical_decision_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell),
        ):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "historical_decision_block"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._run_gate_check(
            strategy_name,
            pred,
            broker_sym,
            sym_ia,
            tf,
            "meta_model_ensemble",
            lambda: self._meta_model_ensemble_check(
                strategy_name,
                pred,
                broker_sym,
                sym_ia,
                tf,
                p_buy,
                p_sell,
                model=model,
                approved_model=approved_model,
                approved_status=approved_status,
            ),
        ):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "meta_model_ensemble"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._run_gate_check(
            strategy_name,
            pred,
            broker_sym,
            sym_ia,
            tf,
            "factor_engine",
            lambda: self._factor_engine_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell),
        ):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "factor_engine"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._run_gate_check(
            strategy_name,
            pred,
            broker_sym,
            sym_ia,
            tf,
            "market_briefing",
            lambda: self._market_briefing_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell),
        ):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "market_briefing"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._run_gate_check(
            strategy_name,
            pred,
            broker_sym,
            sym_ia,
            tf,
            "market_regime",
            lambda: self._market_regime_check(strategy_name, pred, broker_sym, sym_ia, tf),
        ):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "regime_bloqueado"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._trend_direction_allowed(strategy_name, pred, broker_sym, sym_ia, tf):
            self._audit_block_with_shadow(
                strategy_name,
                pred,
                broker_sym,
                sym_ia,
                tf,
                self._last_execution_block_reason or "trend_direction_contra",
                p_buy,
                p_sell,
            )
            return None
        # SWAP filter removido do fluxo de execução: qualquer custo de swap nunca deve
        # bloquear uma ordem no sistema. O valor continua disponível para observação,
        # mas não interfere na decisão de entrada.
        if not self._run_gate_check(
            strategy_name,
            pred,
            broker_sym,
            sym_ia,
            tf,
            "volatility_engine",
            lambda: self._volatility_engine_check(strategy_name, broker_sym, sym_ia, tf, p_buy, p_sell),
        ):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "volatility_engine"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._run_gate_check(
            strategy_name,
            pred,
            broker_sym,
            sym_ia,
            tf,
            "session_context",
            lambda: self._session_context_check(strategy_name, pred, sym_ia, tf),
        ):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "session_context"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._run_gate_check(
            strategy_name,
            pred,
            broker_sym,
            sym_ia,
            tf,
            "macro_flow",
            lambda: self._macro_flow_gate(strategy_name, pred, sym_ia, tf, p_buy, p_sell),
        ):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "macro_fluxo_contra"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._run_gate_check(
            strategy_name,
            pred,
            broker_sym,
            sym_ia,
            tf,
            "market_alignment",
            lambda: self._market_alignment_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell),
        ):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "market_alignment"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._run_gate_check(
            strategy_name,
            pred,
            broker_sym,
            sym_ia,
            tf,
            "timeframe_consensus",
            lambda: self._timeframe_consensus_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell),
        ):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "timeframe_consensus"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._run_gate_check(
            strategy_name,
            pred,
            broker_sym,
            sym_ia,
            tf,
            "portfolio_exposure",
            lambda: self._portfolio_exposure_check(strategy_name, pred, sym_ia),
        ):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "portfolio_exposure"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._run_gate_check(
            strategy_name,
            pred,
            broker_sym,
            sym_ia,
            tf,
            "portfolio_correlation",
            lambda: self._portfolio_correlation_allowed(strategy_name, sym_ia, pred),
        ):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "correlacao_prejuizo"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._run_gate_check(
            strategy_name,
            pred,
            broker_sym,
            sym_ia,
            tf,
            "market_structure",
            lambda: self._market_structure_gate(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell),
        ):
            self._last_execution_block_reason = "market_structure_block"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._run_gate_check(
            strategy_name,
            pred,
            broker_sym,
            sym_ia,
            tf,
            "feature_engineering",
            lambda: self._feature_engineering_check(strategy_name, broker_sym, sym_ia, tf),
        ):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "feature_engineering"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._run_gate_check(
            strategy_name,
            pred,
            broker_sym,
            sym_ia,
            tf,
            "entry_timing",
            lambda: self._entry_timing_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell),
        ):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "entry_timing"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._run_gate_check(
            strategy_name,
            pred,
            broker_sym,
            sym_ia,
            tf,
            "execution_engine",
            lambda: self._execution_engine_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell),
        ):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "execution_engine"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._run_gate_check(
            strategy_name,
            pred,
            broker_sym,
            sym_ia,
            tf,
            "risk_engine",
            lambda: self._risk_engine_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell),
        ):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "risk_engine"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self.ema_alignment.strategy_candle_price_confirmation_ok(strategy_name, pred, broker_sym, sym_ia, tf):
            self._last_execution_block_reason = "preco_candle_nao_confirmado"
            self._record_engine_output(
                engine="candle_price",
                direction="SELL" if pred == 1 else "BUY",
                score=1.0,
                confidence=0.80,
                state="blocked",
                negative_factors=["preco_candle_nao_confirmado"],
            )
            self._emit_gate_decision(strategy_name, sym_ia, tf, "candle_price", False, self._last_execution_block_reason)
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        self._record_engine_output(
            engine="candle_price",
            direction=self._prediction_side(pred),
            score=0.80,
            confidence=0.80,
            state="ok",
            positive_factors=["preco_candle_confirmado"],
        )
        if not self.ema_alignment.strategy_ema_alignment_ok(strategy_name, pred, broker_sym, sym_ia, tf):
            self._last_execution_block_reason = "ema_nao_alinhada"
            self._record_engine_output(
                engine="ema_alignment",
                direction="SELL" if pred == 1 else "BUY",
                score=1.0,
                confidence=0.85,
                state="blocked",
                negative_factors=["ema_nao_alinhada"],
            )
            self._emit_gate_decision(strategy_name, sym_ia, tf, "ema_alignment", False, self._last_execution_block_reason)
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        self._record_engine_output(
            engine="ema_alignment",
            direction=self._prediction_side(pred),
            score=0.85,
            confidence=0.85,
            state="ok",
            positive_factors=["emas_alinhadas"],
        )

        if not self._run_gate_check(
            strategy_name,
            pred,
            broker_sym,
            sym_ia,
            tf,
            "context_engine",
            lambda: self._context_engine_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell),
        ):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "context_engine"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._run_gate_check(
            strategy_name,
            pred,
            broker_sym,
            sym_ia,
            tf,
            "confidence_calibration",
            lambda: self._confidence_calibration_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell),
        ):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "confidence_calibration"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._run_gate_check(
            strategy_name,
            pred,
            broker_sym,
            sym_ia,
            tf,
            "consensus_engine",
            lambda: self._consensus_engine_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell),
        ):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "consensus_engine"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._run_gate_check(
            strategy_name,
            pred,
            broker_sym,
            sym_ia,
            tf,
            "opportunity_engine",
            lambda: self._opportunity_engine_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell),
        ):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "opportunity_engine"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._run_gate_check(
            strategy_name,
            pred,
            broker_sym,
            sym_ia,
            tf,
            "context_brain",
            lambda: self._context_brain_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell),
        ):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "context_brain"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None

        if strategy_name == "strategy1" and bool(cfg.get("use_tp_sl", False)):
            tp_points = int(cfg.get("tp_points", 0))
        elif strategy_name in ["strategy2", "strategy3", "strategy5", "strategy7", "strategy8", "strategy9", "strategy10", "strategy11", "strategy12", "strategy13", "strategy14"]:
            if bool(cfg.get("use_feature_tp_sl", True)) and feature_row:
                tp_points = int(float(feature_row.get("target", cfg.get("default_tp_points", 500))))
                if bool(cfg.get("use_feature_sl", False)):
                    sl_points = int(float(feature_row.get("stop_sugerido", sl_points)))
            else:
                tp_points = int(cfg.get("default_tp_points", 500))

        tp_points, sl_points, runtime_tp_sl_reason = self._runtime_tp_sl_points(sym_ia, tp_points, sl_points)
        if runtime_tp_sl_reason:
            self.logger.info(
                f"[RUNTIME_TP_SL] {sym_ia} {tf} {runtime_tp_sl_reason} | tp={tp_points} sl={sl_points}"
            )

        advisor_extra = {"tp_points": tp_points, "sl_points": sl_points, "magic": magic}
        if not self._ai_advisor_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell, advisor_extra):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "ai_advisor"
            self._audit_block_with_shadow(
                strategy_name,
                pred,
                broker_sym,
                sym_ia,
                tf,
                self._last_execution_block_reason,
                p_buy,
                p_sell,
                extra=advisor_extra,
            )
            return None

        final_allowed, decision_result = self._decision_engine_final_check(
            strategy_name,
            pred,
            broker_sym,
            sym_ia,
            tf,
            p_buy,
            p_sell,
            extra=advisor_extra,
        )
        if not final_allowed:
            self._last_execution_block_reason = (
                decision_result.reason if decision_result is not None else "decision_engine"
            )
            return None

        if decision_result is not None:
            advisor_extra["decision_score"] = decision_result.decision_score
            advisor_extra["decision_reason"] = decision_result.reason
            advisor_extra["tradeability_score"] = decision_result.tradeability_score
            advisor_extra["conflict_score"] = decision_result.conflict_score

        loss_ok, loss_reason = self.trading._floating_loss_guard()
        if not loss_ok:
            self._last_execution_block_reason = loss_reason
            self._record_engine_output(
                engine="floating_loss_guard",
                direction="WAIT",
                score=0.0,
                confidence=1.0,
                state="blocked",
                negative_factors=[loss_reason],
            )
            self._audit_block_with_shadow(
                strategy_name,
                pred,
                broker_sym,
                sym_ia,
                tf,
                self._last_execution_block_reason,
                p_buy,
                p_sell,
                extra=advisor_extra,
            )
            return None

        side = "BUY" if pred == 1 else "SELL"
        order_correlation_id = f"{sym_ia.upper()}:{tf}:{strategy_name}:{datetime.now().isoformat()}"
        self.logger.info(
            f"[ORDER] ATTEMPT {tag} {side} {broker_sym} {tf} | signal={pred} p_buy={p_buy:.4f} p_sell={p_sell:.4f} "
            f"tp={tp_points} sl={sl_points}"
        )
        if not self._await_manual_order_approval(
            order_correlation_id,
            broker_sym,
            sym_ia,
            tf,
            side,
            p_buy,
            p_sell,
            tp_points,
            sl_points,
            magic,
            strategy_name,
        ):
            self._audit_block_with_shadow(
                strategy_name,
                pred,
                broker_sym,
                sym_ia,
                tf,
                self._last_execution_block_reason or "manual_approval_blocked",
                p_buy,
                p_sell,
                extra=advisor_extra,
            )
            return None

        order_metadata = {
            "tp_points": tp_points,
            "sl_points": sl_points,
            "p_buy": p_buy,
            "p_sell": p_sell,
        }
        if "decision_score" in advisor_extra:
            order_metadata["decision_score"] = advisor_extra["decision_score"]
            order_metadata["tradeability_score"] = advisor_extra["tradeability_score"]
            order_metadata["conflict_score"] = advisor_extra["conflict_score"]
            order_metadata["decision_reason"] = advisor_extra["decision_reason"]

        if pred == 1:
            self._audit_decision_event(
                strategy_name, pred, broker_sym, sym_ia, tf, "ALLOW", "pre_order_checks_ok", p_buy, p_sell,
                extra={"tp_points": tp_points, "sl_points": sl_points, "magic": magic},
                correlation_id=order_correlation_id,
            )
            pending_order = FusionOrder(
                order_id=order_correlation_id,
                symbol=sym_ia.upper(),
                broker_symbol=broker_sym,
                strategy=strategy_name,
                timeframe=tf,
                direction="BUY",
                magic=magic,
                status=OrderStatus.PENDING,
                reason="pre_order_checks_ok",
                metadata=order_metadata,
            )
            self.oms.update_order(pending_order)
            self._publish_event(FusionEventType.ORDER_REQUEST, pending_order.to_dict(), correlation_id=order_correlation_id)
            result = self.trading.execute_buy_strategy(
                broker_sym, tf_minutes, mode=mode, magic=magic,
                max_positions=max_positions, tp_points=tp_points, sl_points=sl_points,
                magic_group=magic_group, count_any_direction=count_any_direction,
                count_system_symbol=count_system_symbol, p_buy=p_buy, p_sell=p_sell
            )
            action = "BUY"
        else:
            self._audit_decision_event(
                strategy_name, pred, broker_sym, sym_ia, tf, "ALLOW", "pre_order_checks_ok", p_buy, p_sell,
                extra={"tp_points": tp_points, "sl_points": sl_points, "magic": magic},
                correlation_id=order_correlation_id,
            )
            pending_order = FusionOrder(
                order_id=order_correlation_id,
                symbol=sym_ia.upper(),
                broker_symbol=broker_sym,
                strategy=strategy_name,
                timeframe=tf,
                direction="SELL",
                magic=magic,
                status=OrderStatus.PENDING,
                reason="pre_order_checks_ok",
                metadata=order_metadata,
            )
            self.oms.update_order(pending_order)
            self._publish_event(FusionEventType.ORDER_REQUEST, pending_order.to_dict(), correlation_id=order_correlation_id)
            result = self.trading.execute_sell_strategy(
                broker_sym, tf_minutes, mode=mode, magic=magic,
                max_positions=max_positions, tp_points=tp_points, sl_points=sl_points,
                magic_group=magic_group, count_any_direction=count_any_direction,
                count_system_symbol=count_system_symbol, p_buy=p_buy, p_sell=p_sell
            )
            action = "SELL"

        if result and result.success:
            pending_order.status = OrderStatus.FILLED
            pending_order.price = float(getattr(result, "price", 0.0) or 0.0)
            pending_order.reason = str(getattr(result, "message", "") or "ORDEM_EXECUTADA")
            pending_order.updated_at = datetime.now().isoformat()
            pending_order.metadata["ticket"] = int(getattr(result, "ticket", 0) or 0)
            self.oms.update_order(pending_order)
            self._publish_event(FusionEventType.ORDER_RESULT, pending_order.to_dict(), correlation_id=order_correlation_id)
            self._refresh_oms_state()
            self.logger.info(
                f"{tag} {action} EXECUTADA: {broker_sym} {tf} #{result.ticket} "
                f"magic={magic} tp={tp_points} sl={sl_points}"
            )
        elif result:
            pending_order.status = OrderStatus.REJECTED if "JA_EXISTE" in str(result.message) else OrderStatus.FAILED
            pending_order.reason = str(getattr(result, "message", "") or "NAO_EXECUTADA")
            pending_order.updated_at = datetime.now().isoformat()
            self.oms.update_order(pending_order)
            self._publish_event(FusionEventType.ORDER_RESULT, pending_order.to_dict(), correlation_id=order_correlation_id)
            self._refresh_oms_state()
            self.logger.info(f"{tag} {action} NAO EXECUTADA: {sym_ia} {tf} | {result.message}")
        result_message = str(getattr(result, "message", "") if result else "")
        if result and (result.success or "JA_EXISTE" in result_message):
            actionable_entry = {
                "signal": pred,
                "p_buy": p_buy,
                "p_sell": p_sell,
                "strategy": strategy_name,
                "reason": result_message or "pre_order_checks_ok",
                "timestamp": datetime.now().isoformat(),
            }
            if "decision_score" in advisor_extra:
                actionable_entry["decision_score"] = advisor_extra["decision_score"]
                actionable_entry["tradeability_score"] = advisor_extra["tradeability_score"]
                actionable_entry["conflict_score"] = advisor_extra["conflict_score"]
                actionable_entry["decision_reason"] = advisor_extra["decision_reason"]
            self.actionable_signal_state[(sym_ia.upper(), tf.upper())] = actionable_entry
        else:
            self.actionable_signal_state.pop((sym_ia.upper(), tf.upper()), None)
        return result
    
    def _process_symbol_timeframe(self, broker_sym: str, sym_ia: str, tf: str, now: datetime, cycle_order_symbols: set, last_trade_time: dict) -> None:
        """Processa um Ãºnico sÃ­mbolo/timeframe. Chamado pela fila de distribuiÃ§Ã£o."""
        key = (sym_ia, tf)
        started = time.perf_counter()
        try:
            approved_model = self.approved_models.get((sym_ia.upper(), tf.upper()))
            model = self.models.get(key)
            if not model and not approved_model and not (self._strategy_enabled("strategy6") or self._strategy_enabled("strategy7") or self._strategy_enabled("strategy8") or self._strategy_enabled("strategy9") or self._strategy_enabled("strategy10") or self._strategy_enabled("strategy11") or self._strategy_enabled("strategy12") or self._strategy_enabled("strategy13") or self._strategy_enabled("strategy14")):
                self.monitor_state[key] = {
                    "signal": -1, "p_buy": 0, "p_sell": 0,
                    "status": "SEM_MODELO", "reason": "sem_modelo"
                }
                return

            approved_status = ""
            active_approved_model = approved_model
            reason_parts = []
            if approved_model:
                pred, p_buy, p_sell, approved_status = approved_model.predict(broker_sym)
                if approved_status in {"SEM_DADOS", "SEM_FEATURES", "ERRO_FEATURES", "SEM_EXPERT_ATIVO"}:
                    active_approved_model = None
                    if model:
                        reason_parts.append(f"approved_fallback:{approved_status}")
                        X = self.feature_calc.calculate_features(broker_sym, tf)
                        if X.empty:
                            self.monitor_state[key] = {
                                "signal": -1,
                                "p_buy": None,
                                "p_sell": None,
                                "status": "ERRO_DADOS",
                                "reason": f"approved:{approved_status};erro_dados",
                            }
                            return
                        pred, p_buy, p_sell = model.predict(X)
                        if pred == 0:
                            reason_parts.append("modelo:neutro_threshold")
                    else:
                        self.monitor_state[key] = {
                            "signal": -1,
                            "p_buy": None,
                            "p_sell": None,
                            "status": approved_status,
                            "reason": f"approved:{approved_status}",
                        }
                        return
                if pred == 0:
                    status_text = approved_status or "neutro"
                    if active_approved_model:
                        reason_parts.append(f"approved:{status_text}")
            elif model:
                X = self.feature_calc.calculate_features(broker_sym, tf)
                if X.empty:
                    self.monitor_state[key] = {
                        "signal": -1, "p_buy": None, "p_sell": None,
                        "status": "ERRO_DADOS", "reason": "erro_dados"
                    }
                    return
                pred, p_buy, p_sell = model.predict(X)
                if pred == 0:
                    reason_parts.append("modelo:neutro_threshold")
            else:
                pred = 0
                p_buy = 0.0
                p_sell = 0.0
                reason_parts.append("sem_modelo_runtime")

            pred, p_buy, p_sell, inversion_reason = self._apply_signal_inversion(
                pred, p_buy, p_sell, sym_ia, tf
            )
            if inversion_reason:
                reason_parts.append(f"signal_inversion:{inversion_reason}")

            pred, p_buy, p_sell, override_reason = self._apply_signal_override(
                pred, p_buy, p_sell, sym_ia, tf
            )
            if override_reason:
                reason_parts.append(f"signal_override:{override_reason}")

            pred, p_buy, p_sell, runtime_signal_reason = self._apply_runtime_signal_thresholds(
                pred, p_buy, p_sell, sym_ia, tf
            )
            if runtime_signal_reason:
                reason_parts.append(runtime_signal_reason)

            executed_tags = []
            strategy_reasons = []
            strategy_context = StrategyContext(
                broker_symbol=broker_sym,
                symbol=sym_ia,
                timeframe=tf,
                prediction=pred,
                p_buy=p_buy,
                p_sell=p_sell,
                now=now,
                model=model,
                approved_model=active_approved_model,
                approved_status=approved_status,
            )
            signal_correlation_id = ""
            if pred in (1, 2):
                signal_name = "BUY" if pred == 1 else "SELL"
                signal_correlation_id = f"{sym_ia.upper()}:{tf}:SIGNAL:{now.isoformat()}"
                signal_payload = FusionSignal(
                    symbol=sym_ia.upper(),
                    broker_symbol=broker_sym,
                    timeframe=tf,
                    strategy="model_signal",
                    direction=signal_name,
                    p_buy=float(p_buy or 0.0),
                    p_sell=float(p_sell or 0.0),
                    raw_prediction=int(pred),
                    metadata={
                        "approved_model": bool(active_approved_model),
                        "approved_status": approved_status,
                    },
                )
                self._publish_event(
                    FusionEventType.SIGNAL,
                    signal_payload.to_dict(),
                    source="SignalLoop",
                    correlation_id=signal_correlation_id,
                )
                self.logger.info(
                    f"SINAL {signal_name}: {sym_ia} {tf} | "
                    f"p_buy: {p_buy:.4f} | p_sell: {p_sell:.4f}"
                )

            previous_signal_correlation_id = self._active_signal_correlation_id
            self._active_signal_correlation_id = signal_correlation_id
            try:
                symbol_key = sym_ia.upper()
                if symbol_key in cycle_order_symbols:
                    strategy_reasons.append("symbol_order_already_executed_this_cycle")
                else:
                    for strategy in self.strategy_runners:
                        self._last_market_structure_reason = ""
                        self._last_market_structure_snapshot = {}
                        self._last_market_briefing_reason = ""
                        decision = strategy.evaluate(strategy_context, last_trade_time)
                        if decision.executed:
                            executed_tags.append(decision.tag)
                            cycle_order_symbols.add(symbol_key)
                        elif decision.attempted:
                            executed_tags.append(f"{decision.tag}T")
                        if self._last_market_briefing_reason and (decision.executed or decision.attempted):
                            strategy_reasons.append(f"{decision.tag}:{self._last_market_briefing_reason}")
                        if self._last_market_structure_reason and (decision.executed or decision.attempted):
                            strategy_reasons.append(f"{decision.tag}:{self._last_market_structure_reason}")
                        if decision.message:
                            strategy_reasons.append(f"{decision.tag}:{decision.message}")
                        if decision.executed:
                            break
            finally:
                self._active_signal_correlation_id = previous_signal_correlation_id

            status = f"{pred}_{p_buy:.4f}_{p_sell:.4f}"
            if active_approved_model:
                status += "_APPROVED"
                if approved_status:
                    status += f"_{approved_status[:40]}"
            if executed_tags:
                status += "_" + "+".join(executed_tags)
            reason = ";".join(strategy_reasons or reason_parts or ["aguardando_setup"])
            raw_pred = pred
            raw_p_buy = p_buy
            raw_p_sell = p_sell
            display_reason_parts = strategy_reasons or reason_parts or ["aguardando_setup"]
            display_pred, display_p_buy, display_p_sell, display_reason_parts = self._refine_panel_signal(
                pred, p_buy, p_sell, sym_ia, tf, list(display_reason_parts)
            )
            display_reason = ";".join(display_reason_parts)
            if display_pred != raw_pred:
                status += "_PANEL_REFINED_WAIT"
            self.monitor_state[key] = {
                "signal": display_pred,
                "p_buy": display_p_buy,
                "p_sell": display_p_sell,
                "status": status,
                "reason": display_reason,
                "raw_signal": raw_pred,
                "raw_p_buy": raw_p_buy,
                "raw_p_sell": raw_p_sell,
                "raw_reason": reason,
            }
        except Exception as e:
            self.logger.error(f"[ANALISE_ERRO] {sym_ia} {tf}: {e}", exc_info=True)
            self.monitor_state[key] = {
                "signal": 0, "p_buy": 0, "p_sell": 0,
                "status": f"ERRO: {str(e)[:80]}",
                "reason": f"erro:{str(e)[:160]}",
            }
        finally:
            state = self.monitor_state.get(key, {}) or {}
            self.logger.info(
                f"[TIMING] {datetime.now().isoformat(timespec='seconds')} | analise {sym_ia} {tf} | "
                f"{time.perf_counter() - started:.3f}s | status={state.get('status', '')} | signal={state.get('signal', '')}"
            )

    def _run_signals(self):
        """Loop principal de sinais e execuÃ§Ã£o com distribuiÃ§Ã£o por fila."""
        last_trade_time: dict = {}
        last_cache_cleanup = time.time()
        last_idle_log = 0.0
        CACHE_CLEANUP_INTERVAL = 60  # A cada 60 segundos

        self.signal_loop_service.run()

    def _run_signals_legacy(self):
        """Loop principal de sinais e execuÃ§Ã£o."""
        last_min = -1
        last_trade_time: dict = {}
        cooldown_seconds = 300
        
        while True:
            now = datetime.now()
            
            if now.minute != last_min:
                for broker_sym, sym_ia in self.sync_dict.items():
                    for tf in self.TIMEFRAMES:
                        key = (sym_ia, tf)
                        
                        model = self.models.get(key)
                        if not model:
                            self.monitor_state[key] = {"signal": -1, "p_buy": 0, "p_sell": 0, "status": "SEM_MODELO"}
                            continue
                        
                        if self.trading.is_position_open(broker_sym, 0):
                            X = self.feature_calc.calculate_features(broker_sym, tf)
                            if not X.empty:
                                try:
                                    pred, p_buy, p_sell = model.predict(X)
                                    self.monitor_state[key] = {"signal": pred, "p_buy": p_buy, "p_sell": p_sell, "status": "EM_POSICAO"}
                                except:
                                    self.monitor_state[key] = {"signal": 0, "p_buy": 0, "p_sell": 0, "status": "EM_POSICAO"}
                            else:
                                self.monitor_state[key] = {"signal": 0, "p_buy": 0, "p_sell": 0, "status": "EM_POSICAO"}
                            continue
                        
                        cooldown_key = f"{sym_ia}_{tf}"
                        if cooldown_key in last_trade_time:
                            if (now - last_trade_time[cooldown_key]).seconds < cooldown_seconds:
                                continue
                        
                        X = self.feature_calc.calculate_features(broker_sym, tf)
                        if X.empty:
                            self.monitor_state[key] = {"signal": 0, "p_buy": 0, "p_sell": 0, "status": "ERRO_DADOS"}
                            continue
                        
                        try:
                            pred, p_buy, p_sell = model.predict(X)
                            pred, p_buy, p_sell, _ = self._apply_signal_inversion(
                                pred,
                                p_buy,
                                p_sell,
                                sym_ia,
                                tf,
                            )
                            
                            if pred == 1:
                                self.logger.info(f"SINAL BUY: {sym_ia} {tf} | p_buy: {p_buy:.4f} | Thresh: {model.buy_thresh:.2f}")
                                result = self.trading.execute_buy(broker_sym, self.TF_MINUTES.get(tf, 5), mode=f"FUSION_{tf}")
                                if result.success:
                                    last_trade_time[cooldown_key] = now
                                    self.logger.info(f"ORDEM BUY EXECUTADA: {broker_sym} #{result.ticket}")
                            
                            elif pred == 2:
                                self.logger.info(f"SINAL SELL: {sym_ia} {tf} | p_sell: {p_sell:.4f} | Thresh: {model.sell_thresh:.2f}")
                                result = self.trading.execute_sell(broker_sym, self.TF_MINUTES.get(tf, 5), mode=f"FUSION_{tf}")
                                if result.success:
                                    last_trade_time[cooldown_key] = now
                                    self.logger.info(f"ORDEM SELL EXECUTADA: {broker_sym} #{result.ticket}")
                            
                            self.monitor_state[key] = {"signal": pred, "p_buy": p_buy, "p_sell": p_sell, "status": f"{pred}_{p_buy:.4f}_{p_sell:.4f}"}
                        except Exception as e:
                            self.monitor_state[key] = {"signal": 0, "p_buy": 0, "p_sell": 0, "status": f"ERRO: {str(e)[:15]}"}
                
                self._print_dashboard()
                last_min = now.minute
            
            time.sleep(1)
    
    def _print_dashboard(self):
        """Imprime dashboard de status."""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            neutral_tokens = ("modelo:neutro_threshold", "approved:NEUTRO")
            data_quality_tokens = (
                "approved:SEM_DADOS",
                "approved:SEM_FEATURES",
                "approved:ERRO_FEATURES",
                "approved:SEM_EXPERT_ATIVO",
                "sem_feature",
                "sem_modelo",
                "erro_dados",
                "sem_modelo_runtime",
            )
            show_neutral = bool(self.config.get("dashboard.show_neutral_details", False))
            show_data_quality = bool(self.config.get("dashboard.show_data_quality_details", False))
            show_ms_shadow = bool(self.config.get("dashboard.show_market_structure_shadow", False))
            show_reason_column = bool(self.config.get("dashboard.show_reason_column", True))
            max_reason_items = int(self.config.get("dashboard.max_reason_items", 3) or 3)
            max_summary_items = int(self.config.get("dashboard.max_summary_items", 8) or 8)
            cell_width = 25
            dashboard_width = 10 + 1 + (cell_width + 1) * 6 + (80 if show_reason_column else 0)
            print(f"\n{'='*dashboard_width}")
            print(f" FUSION_V2 DASHBOARD | {now} | STATUS: OPERACIONAL | Modelos: {len(self.models)}")
            print(f"{'='*dashboard_width}")
            header = f"{'ATIVO':<10}|{'M5':^{cell_width}}|{'M15':^{cell_width}}|{'M30':^{cell_width}}|{'H1':^{cell_width}}|{'H4':^{cell_width}}|{'D1':^{cell_width}}|"
            if show_reason_column:
                header += " MOTIVOS"
            print(header)
            print("-" * dashboard_width)
            
            symbols = list(set(k[0] for k in self.monitor_state.keys()))
            detail_lines = []
            reason_counts = {}
            for sym in sorted(symbols):
                display = "GOLD" if sym == "gold" else sym
                cells_raw = []
                reasons = []
                
                for tf in ["M5", "M15", "M30", "H1", "H4", "D1"]:
                    key = (sym, tf)
                    state = self.monitor_state.get(key, {})
                    model = self.models.get(key)
                    has_model = bool(model or self.approved_models.get((sym.upper(), tf.upper())))
                    
                    p_buy = state.get('p_buy', None)
                    p_sell = state.get('p_sell', None)
                    sig = state.get('signal', -1)
                    st = state.get('status', '')
                    reason = str(state.get("reason", "") or "")
                    if reason:
                        parts = [part.strip() for part in reason.split(";") if part.strip()]
                        actionable_parts = []
                        for part in parts:
                            if not show_neutral and part in neutral_tokens:
                                continue
                            if not show_data_quality and any(token in part for token in data_quality_tokens):
                                continue
                            if not show_ms_shadow and ":MS:shadow:" in part:
                                continue
                            actionable_parts.append(part)
                            reason_key = self._dashboard_reason_key(part)
                            if not reason_key:
                                continue
                            if not show_ms_shadow and reason_key.startswith("MS:shadow:"):
                                continue
                            reason_counts[reason_key] = reason_counts.get(reason_key, 0) + 1
                        if actionable_parts:
                            compact_reason = ";".join(actionable_parts[:max_reason_items])
                            reasons.append(f"{tf}:{compact_reason}")
                            detail_lines.append(f"{display} {tf}: {compact_reason}")
                    
                    p_buy_num = float(p_buy) if p_buy is not None else None
                    p_sell_num = float(p_sell) if p_sell is not None else None
                    has_empty_probs = (
                        p_buy_num is None
                        or p_sell_num is None
                    )
                    unavailable_status = str(st).upper() in {
                        "SEM_MODELO",
                        "ERRO_DADOS",
                        "SEM_DADOS",
                        "SEM_FEATURES",
                        "ERRO_FEATURES",
                        "SEM_EXPERT_ATIVO",
                    }

                    if not has_model:
                        cell = f"-/-"
                    elif sig == -1:
                        cell = f"-/-"
                    elif unavailable_status or has_empty_probs:
                        cell = "-/-"
                    elif st == "EM_POSICAO":
                        p_wait_num = max(0.0, min(1.0, 1.0 - p_buy_num - p_sell_num))
                        cell = f"W:{p_wait_num:.3f} B:{p_buy_num:.3f} S:{p_sell_num:.3f}"
                    elif sig == 0:
                        p_wait_num = max(0.0, min(1.0, 1.0 - p_buy_num - p_sell_num))
                        cell = f"W:{p_wait_num:.3f} B:{p_buy_num:.3f} S:{p_sell_num:.3f}"
                    elif sig == 1:
                        cell = f"B:{p_buy_num:.3f}"
                    elif sig == 2:
                        cell = f"S:{p_sell_num:.3f}"
                    else:
                        cell = f"{p_buy_num:.3f}/{p_sell_num:.3f}"
                    
                    cells_raw.append(cell)
                
                row = f"{display:<10}|"
                for cr in cells_raw:
                    row += f"{cr[:cell_width]:^{cell_width}}|"
                if show_reason_column:
                    motivo = " | ".join(reasons[:max_reason_items]) if reasons else "-"
                    if len(motivo) > 76:
                        motivo = motivo[:73] + "..."
                    row += f" {motivo}"
                print(row)
            
            print(f"{'='*dashboard_width}")
            print(" Legenda: B=BUY | S=SELL | W=p_wait | -/-=SEM_MODELO/SEM_DADOS/SEM_FEATURE")
            if bool(self.config.get("dashboard.show_reason_summary", True)) and reason_counts:
                summary = " | ".join(
                    f"{reason}:{count}" for reason, count in sorted(reason_counts.items(), key=lambda item: (-item[1], item[0]))
                    [:max_summary_items]
                )
                print(f" Resumo dos motivos acionaveis: {summary}")
            if bool(self.config.get("dashboard.show_reason_details", True)) and detail_lines:
                print(" Detalhe dos motivos:")
                for line in detail_lines:
                    print(f"  - {line}")
            print()
        except Exception:
            pass
    
    def _print_dashboard_premium(self):
        """Dashboard com todos os ativos - layout simples e eficiente."""
        try:
            now = datetime.now().strftime("%H:%M:%S")
            
            # Cores ANSI
            GREEN = '\033[92m'
            RED = '\033[91m'
            YELLOW = '\033[93m'
            BLUE = '\033[94m'
            CYAN = '\033[96m'
            RESET = '\033[0m'
            BOLD = '\033[1m'
            
            # EstatÃ­sticas globais
            symbols = sorted(list(set(k[0] for k in self.monitor_state.keys())))
            buy_count = sell_count = wait_count = 0
            actions = []
            
            for sym in symbols:
                for tf in ["M5", "M15", "M30", "H1", "H4", "D1"]:
                    state = self.monitor_state.get((sym, tf), {})
                    sig = state.get('signal', -1)
                    if sig >= 0:
                        if sig == 1: buy_count += 1
                        elif sig == 2: sell_count += 1
                        elif sig == 0: wait_count += 1
                        
                        if sig >= 1:
                            p_buy = float(state.get('p_buy', 0) or 0)
                            p_sell = float(state.get('p_sell', 0) or 0)
                            strength = p_buy if sig == 1 else p_sell
                            reason = str(state.get('reason', '') or '').split(';')[0][:50]
                            actions.append((sym, tf, sig, strength, reason))
            
            total = buy_count + sell_count + wait_count
            
            # Header
            print(f"\n{BOLD}{CYAN}{'=' * 140}{RESET}")
            print(f"{BOLD}FUSION V2 | {now} | BUY: {GREEN}{buy_count}{RESET} | SELL: {RED}{sell_count}{RESET} | WAIT: {YELLOW}{wait_count}{RESET} | Total: {total}{RESET}")
            print(f"{BOLD}{CYAN}{'=' * 140}{RESET}")
            
            # Grid: Mostrar TODOS os ativos (mÃ¡ximo espaÃ§o permitido)
            timeframes = ["M5", "M15", "M30", "H1", "H4", "D1"]
            
            # Header de colunas
            header = f"{'ATIVO':<8s} | "
            for tf in timeframes:
                header += f"{tf:>4s} | "
            print(f"{BOLD}{header}{RESET}")
            print(f"{'-' * len(header)}")
            
            # Dados dos ativos (todos!)
            for sym in symbols:
                line = f"{sym[:8]:<8s} | "
                for tf in timeframes:
                    state = self.monitor_state.get((sym, tf), {})
                    sig = state.get('signal', -1)
                    
                    if sig == -1:
                        cell = " -  "
                    elif sig == 0:
                        p_wait = 1 - float(state.get('p_buy', 0) or 0) - float(state.get('p_sell', 0) or 0)
                        cell = f"{YELLOW}W{p_wait:3.0%}{RESET}"
                    elif sig == 1:
                        p_buy = float(state.get('p_buy', 0) or 0)
                        cell = f"{GREEN}B{p_buy:3.0%}{RESET}"
                    elif sig == 2:
                        p_sell = float(state.get('p_sell', 0) or 0)
                        cell = f"{RED}S{p_sell:3.0%}{RESET}"
                    else:
                        cell = " ?  "
                    
                    line += f"{cell} | "
                print(line)
            
            # AÃ§Ãµes acionÃ¡veis
            if actions:
                print(f"\n{BOLD}{BLUE}{'=' * 140}{RESET}")
                print(f"{BOLD}ACOES (Top {min(5, len(actions))}): {RESET}")
                for sym, tf, sig, strength, reason in sorted(actions, key=lambda x: -x[3])[:5]:
                    sig_str = f"{GREEN}BUY{RESET}" if sig == 1 else f"{RED}SELL{RESET}"
                    print(f"  {sig_str}  {sym:8s} {tf:4s} ({strength:5.1%}) - {reason}")
            
            print(f"{BOLD}{CYAN}{'=' * 140}{RESET}\n")
            
        except Exception as e:
            self.logger.error(f"Dashboard: {e}")
    
    def start_trailing_loop(self):
        """Inicia loop de trailing em thread separada."""
        runtime_trailing_enabled = self.runtime_control.get("trailing.enabled")
        if runtime_trailing_enabled is False:
            self.logger.info("[TRAILING] Desativado em runtime_control.trailing.enabled")
            return
        if not self.config.trailing.enabled:
            self.logger.info("[TRAILING] Desativado em config.trailing.enabled")
            return
        if self._trailing_thread and self._trailing_thread.is_alive():
            self.logger.info("[TRAILING] Loop ja esta ativo")
            return

        symbols = list(self.sync_dict.keys())
        trailing_magics = []
        for strategy_name in ["strategy1", "strategy2", "strategy3", "strategy4", "strategy5"]:
            if self._strategy_enabled(strategy_name):
                trailing_magics.extend(self._strategy_magic_group(strategy_name))
        trailing_magics = sorted(set(trailing_magics))
        interval = max(float(getattr(self.config.trailing, "check_interval", 1) or 1), 0.1)
        self._trailing_stop_event = threading.Event()
        self._trailing_thread = threading.Thread(
            target=self.trailing.start_background_loop,
            args=(symbols, interval, trailing_magics, self._trailing_stop_event),
            daemon=True,
            name="FusionTrailingLoop",
        )
        self._trailing_thread.start()
        self.logger.info(
            f"[TRAILING] Loop separado iniciado | intervalo={interval:.2f}s | simbolos={len(symbols)}"
        )
    
    def stop_trailing_loop(self):
        """Para o loop de trailing antes de encerrar o MT5."""
        if self._trailing_stop_event:
            self._trailing_stop_event.set()
        if self._trailing_thread and self._trailing_thread.is_alive():
            self._trailing_thread.join(timeout=3)
            if self._trailing_thread.is_alive():
                self.logger.warning("[TRAILING] Loop nao encerrou dentro do timeout")
        self._trailing_thread = None
        self._trailing_stop_event = None
    
    def run(self):
        """Executa sistema principal."""
        try:
            self.logger.info(f"[BOOT][run] {datetime.now().isoformat(timespec='seconds')} | entrada no loop principal")
            if not self.initialize():
                self.logger.error("Falha na inicializaÃ§Ã£o")
                return
            self.logger.info(f"[BOOT][run] {datetime.now().isoformat(timespec='seconds')} | initialize ok, iniciando trailing")
            self.start_trailing_loop()
            self.logger.info(f"[BOOT][run] {datetime.now().isoformat(timespec='seconds')} | trailing ok, entrando no monitoramento")
            self.signal_loop_service.run()
        except KeyboardInterrupt:
            self.logger.warning("Sistema pausado pelo usuÃ¡rio")
        finally:
            self.stop_trailing_loop()
            self.stop_event_bus()
            MT5Connector.shutdown()
            self.logger.info("FUSION_V2 encerrado")


if __name__ == "__main__":
    import MetaTrader5 as mt5
    import numpy as np
    import pandas as pd
    
    fusion = FusionV2()
    fusion.run()