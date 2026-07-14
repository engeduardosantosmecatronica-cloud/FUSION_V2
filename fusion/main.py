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
from fusion.core.events import FusionEvent, FusionEventBus
from fusion.core.logger import get_logger, FusionLogger
from fusion.core.objects import FusionAccount, FusionOrder, FusionPosition, FusionSignal, FusionTick, FusionTrade
from fusion.data.pipeline import MT5Connector
from fusion.features.engine import FeatureEngine, AlphaMiner, RSI, EMA
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
from fusion.execution.trading import TradingExecutor
from fusion.execution.trailing import TrailingManager
from fusion.execution.oms import FusionOMS
from fusion.execution.oms_snapshot import OMSSnapshotWriter
from fusion.approved_ensembles import ApprovedEnsembleRegistry
from fusion.runtime_control import RuntimeControl
from fusion.mt5_signal_panel import MT5SignalPanelExporter, mt5_common_files_dir
from fusion.mt5_trade_zones import MT5TradeZonesExporter
from fusion.mt5_decision_layers import MT5DecisionLayersExporter
from fusion.decision import (
    DecisionAuditLogger,
    DecisionEvent,
    DecisionOrchestrator,
    DecisionPolicy,
    DecisionResult,
    EngineOutput,
    SignalCandidate,
    build_xai_explanation,
)
from fusion.strategies import Estrategia1, Estrategia2, Estrategia3, Estrategia4, Estrategia5, Estrategia6, Estrategia7, Estrategia8, Estrategia9, Estrategia10, Estrategia11, Estrategia12, Estrategia13, Estrategia14
from fusion.strategies.base import StrategyContext


class SingleModel:
    """Modelo individual para um sÃ­mbolo/timeframe."""
    def __init__(self, model_path, scaler_path, meta_path, calibrator_path=None):
        import joblib
        from fusion.core.config import get_config
        config = get_config()
        
        self.model = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)
        if str(meta_path).lower().endswith(".json"):
            self.meta = json.loads(Path(meta_path).read_text(encoding="utf-8"))
        else:
            self.meta = joblib.load(meta_path)
        self.calibrator = joblib.load(calibrator_path) if calibrator_path and Path(calibrator_path).exists() else None
        self.logger: FusionLogger = get_logger(f"SingleModel_{self.meta.get('symbol', '?')}_{self.meta.get('timeframe', '?')}")
        self.feature_cols = self.meta.get('feature_columns', [])
        self.buy_thresh = self.meta.get('buy_threshold', getattr(config.signal, 'buy_threshold', 0.55))
        self.sell_thresh = self.meta.get('sell_threshold', getattr(config.signal, 'sell_threshold', 0.55))

    @staticmethod
    def _align_proba(probs, classes):
        aligned = np.zeros((len(probs), 3), dtype=float)
        class_list = [int(cls) for cls in classes]
        for target_idx, label in enumerate([0, 1, 2]):
            if label in class_list:
                aligned[:, target_idx] = probs[:, class_list.index(label)]
        row_sum = aligned.sum(axis=1, keepdims=True)
        return aligned / np.where(row_sum == 0, 1.0, row_sum)
    
    def predict(self, features_df):
        missing = [col for col in self.feature_cols if col not in features_df.columns]
        if missing:
            raise ValueError(f"Features ausentes para {self.meta.get('symbol', '?')}/{self.meta.get('timeframe', '?')}: {missing[:8]}")
        X = features_df[self.feature_cols]
        X_scaled = self.scaler.transform(X)
        X_df = pd.DataFrame(X_scaled, columns=self.feature_cols)
        probs = self.model.predict_proba(X_df)
        probs = self._align_proba(probs, getattr(self.model, "classes_", self.meta.get("classes", [0, 1, 2])))
        if self.calibrator is not None:
            probs = self.calibrator.predict_proba(probs)
            probs = self._align_proba(probs, getattr(self.calibrator, "classes_", [0, 1, 2]))
        
        p_buy = float(probs[0, 1])
        p_sell = float(probs[0, 2])
        
        if p_buy > self.buy_thresh: return 1, p_buy, p_sell
        if p_sell > self.sell_thresh: return 2, p_buy, p_sell
        return 0, p_buy, p_sell


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
        self.models: dict = {}
        self.sync_dict: dict = {}
        self.monitor_state: dict = {}
        self.actionable_signal_state: dict = {}
        self.final_signal_state: dict = {}
        self.decision_layers_state: dict = {}
        panel_cfg = self.config.get("mt5_signal_panel", {}) or {}
        self.mt5_signal_panel = MT5SignalPanelExporter(
            output_dir=panel_cfg.get("output_dir") or None,
            use_common_files=bool(panel_cfg.get("use_common_files", True)),
            file_prefix=str(panel_cfg.get("file_prefix", "fusion_signal_panel_") or "fusion_signal_panel_"),
            enabled=bool(panel_cfg.get("enabled", True)),
        )
        zones_cfg = self.config.get("mt5_trade_zones", {}) or {}
        self.mt5_trade_zones = MT5TradeZonesExporter(
            output_dir=zones_cfg.get("output_dir") or None,
            use_common_files=bool(zones_cfg.get("use_common_files", True)),
            file_prefix=str(zones_cfg.get("file_prefix", "fusion_trade_zones_") or "fusion_trade_zones_"),
            enabled=bool(zones_cfg.get("enabled", True)),
            bars=int(zones_cfg.get("bars", 120) or 120),
            sr_lookback=int(zones_cfg.get("sr_lookback", 40) or 40),
            atr_period=int(zones_cfg.get("atr_period", 14) or 14),
            entry_atr_width=float(zones_cfg.get("entry_atr_width", 0.15) or 0.15),
            sr_atr_width=float(zones_cfg.get("sr_atr_width", 0.08) or 0.08),
            sl_atr_multiplier=float(zones_cfg.get("sl_atr_multiplier", 1.2) or 1.2),
            tp_r_multiple=float(zones_cfg.get("tp_r_multiple", 2.0) or 2.0),
        )
        layers_cfg = self.config.get("mt5_decision_layers", {}) or {}
        self.mt5_decision_layers = MT5DecisionLayersExporter(
            output_dir=layers_cfg.get("output_dir") or None,
            use_common_files=bool(layers_cfg.get("use_common_files", True)),
            file_prefix=str(layers_cfg.get("file_prefix", "fusion_decision_layers_") or "fusion_decision_layers_"),
            enabled=bool(layers_cfg.get("enabled", True)),
        )
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
        self.event_bus = FusionEventBus()
        event_cfg = self.config.get("event_bus", {}) or {}
        self.event_logger = FusionEventLogger(
            log_dir=event_cfg.get("event_log_dir", "logs/events"),
            enabled=bool(event_cfg.get("event_log_enabled", True)),
        )
        self.event_bus.subscribe(FusionEventBus.ALL_EVENTS, self.event_logger.handle)
        self._event_bus_async = bool(event_cfg.get("use_async", False))
        self._event_bus_async_stop_timeout = float(event_cfg.get("async_stop_timeout", 10) or 10)
        if self._event_bus_async:
            self.event_bus.start_async()
        self.oms = FusionOMS()
        oms_cfg = self.config.get("oms", {}) or {}
        self.oms_snapshot_writer = OMSSnapshotWriter(
            output_dir=oms_cfg.get("snapshot_dir", "logs/oms"),
            enabled=bool(oms_cfg.get("snapshot_enabled", True)),
        )
        self.engine_registry = FusionEngineRegistry()
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
        self.strategy_features = self._load_strategy_features()
        self.approved_models: dict = {}
        self.approved_tp_sl: dict = {}
        
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
        self.logger.info(f"[BOOT][TIMING] estruturas principais prontas em {time.perf_counter() - boot_started:.3f}s")
        
        self._trailing_stop_event: threading.Event | None = None
        self._trailing_thread: threading.Thread | None = None
        self.mt5 = mt5
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
        try:
            event = FusionEvent(
                type=event_type,
                source=source,
                data=data or {},
                correlation_id=correlation_id,
            )
            if self._event_bus_async:
                self.event_bus.publish_async(event)
            else:
                self.event_bus.publish(event)
        except Exception as exc:
            self.logger.warning(f"Falha ao publicar evento {event_type}: {exc}")

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
    
    def initialize(self) -> bool:
        """Inicializa MT5 e carrega modelos."""
        startup_started = time.perf_counter()
        self.logger.info("=" * 80)
        self.logger.info("?? FUSION_V2 - SISTEMA DE TRADING IA - INICIALIZAÃ‡ÃƒO")
        self.logger.info("=" * 80)
        self.logger.info(f"[STARTUP] timestamp_inicial={datetime.now().isoformat(timespec='seconds')}")
        
        # Log de configuraÃ§Ã£o geral
        config_started = time.perf_counter()
        self.logger.info(f"[STARTUP] Config recarregada: {self.config.config_file if hasattr(self.config, 'config_file') else 'default'}")
        symbols_cfg = self.config.get("symbols", []) or []
        self._log_timing(
            "startup.config_lido",
            config_started,
            extra=f"ativos={len(symbols_cfg)} preview={symbols_cfg[:5]}{'...' if len(symbols_cfg) > 5 else ''}"
        )

        runtime_filters = self.runtime_control.section("filters")
        self.logger.info(
            "[RUNTIME] path=%s enabled=%s market_briefing_mode=%s macro_flow_mode=%s "
            "market_alignment_mode=%s timeframe_consensus_mode=%s"
            % (
                self.runtime_control.path,
                self.runtime_control.enabled(),
                runtime_filters.get("market_briefing_mode", "yaml"),
                runtime_filters.get("macro_flow_mode", "yaml"),
                runtime_filters.get("market_alignment_mode", "yaml"),
                runtime_filters.get("timeframe_consensus_mode", "yaml"),
            )
        )

        step_started = time.perf_counter()
        self.logger.info("[STARTUP] Conectando ao MT5...")
        if not MT5Connector.initialize():
            self.logger.critical("? Falha ao inicializar MT5")
            return False
        elapsed = time.perf_counter() - step_started
        self.logger.info(f"? [STARTUP] MT5 inicializado em {elapsed:.2f}s")
        
        step_started = time.perf_counter()
        acc = mt5.account_info()
        if acc:
            self.logger.info(f"   ?? Conta: {acc.login} | Corretora: {acc.server} | Moeda: {acc.currency}")
            self.logger.info(f"   ?? Saldo: {acc.balance:.2f} | PatrimÃ´nio: {acc.equity:.2f} | Margem Livre: {acc.margin_free:.2f}")
            self._refresh_oms_state()
        elapsed = time.perf_counter() - step_started
        self.logger.info(f"? [STARTUP] Conta/OMS sincronizados em {elapsed:.2f}s")

        step_started = time.perf_counter()
        self.logger.info("[STARTUP] Carregando modelos IA por ativo/timeframe...")
        self._load_all_models()
        models_count = len(self.models)
        self._log_timing("startup.modelos_carregados", step_started, extra=f"modelos={models_count}")
        if models_count == 0:
            self.logger.warning("??  Nenhum modelo encontrado! Verifique pasta models/")

        step_started = time.perf_counter()
        self.logger.info("[STARTUP] Carregando ensembles M5 aprovados...")
        self._load_approved_ensembles()
        
        ensembles_count = len(self.approved_models)
        self._log_timing("startup.ensembles_carregados", step_started, extra=f"ensembles={ensembles_count}")

        step_started = time.perf_counter()
        self.logger.info("[STARTUP] Carregando TP/SL otimizado...")
        self.approved_tp_sl = self._load_approved_tp_sl()
        
        tpsl_count = len(self.approved_tp_sl)
        self._log_timing("startup.tpsl_carregados", step_started, extra=f"tp_sl={tpsl_count}")

        step_started = time.perf_counter()
        self.logger.info("[STARTUP] Sincronizando sÃ­mbolos com broker...")
        self._sync_symbols()
        
        synced_count = len(self.sync_dict)
        self._log_timing("startup.sincronizacao_simbolos", step_started, extra=f"ativos={synced_count}")

        step_started = time.perf_counter()
        self.logger.info("[STARTUP] Bootstrap da matriz operacional...")
        self._bootstrap_operational_target_matrix()
        
        self._log_timing("startup.matriz_operacional", step_started)


        step_started = time.perf_counter()
        self.logger.info("[STARTUP] Registrando mapa de estratÃ©gias...")
        self._log_strategy_magic_map()
        
        self._log_timing("startup.mapa_estrategias", step_started)
        
        step_started = time.perf_counter()
        self.logger.info("[STARTUP] Inicializando engines de decisÃ£o...")
        engines_registered = len(self.engine_registry.engines)
        strategies_count = len(self.strategy_runners)
        self._log_timing(
            "startup.engines_decisao",
            step_started,
            extra=f"engines={engines_registered} estrategias={strategies_count}"
        )
        
        total_elapsed = time.perf_counter() - startup_started
        
        self.logger.info("=" * 80)
        
        self.logger.info(f"?? INICIALIZAÃ‡ÃƒO CONCLUÃDA em {total_elapsed:.2f}s ({int(total_elapsed//60)}m{int(total_elapsed%60)}s)")
        self.logger.info(f"[STARTUP] timestamp_final={datetime.now().isoformat(timespec='seconds')}")
        
        self.logger.info(f"   ?? {models_count} modelos | {ensembles_count} ensembles | {synced_count} ativos")
        
        self.logger.info(f"   ??  {engines_registered} engines | {strategies_count} estratÃ©gias ativas")
        
        self.logger.info(f"   ?? Cache TTL: {self.features_cache_ttl}s | Cleanup: 60s")
        
        self.logger.info("=" * 80)
        

        return True


    def _current_configured_symbols(self) -> list[str]:
        symbols = [str(item).upper() for item in (self.config.get("symbols", []) or [])]
        if not symbols and self.sync_dict:
            symbols = [str(item).upper() for item in self.sync_dict.values()]
        return sorted(set(symbols))

    def _operational_matrix_due(self, latest_path: Path, symbols: list[str]) -> tuple[bool, list[str], str]:
        if not latest_path.exists():
            return True, symbols, "arquivo_ausente"
        try:
            payload = json.loads(latest_path.read_text(encoding="utf-8"))
        except Exception:
            return True, symbols, "arquivo_invalido"

        today = datetime.now().strftime("%Y-%m-%d")
        matrix_date = str(payload.get("date") or "")
        matrix_symbols = {str(item).upper() for item in (payload.get("symbols", []) or [])}
        requested = {str(item).upper() for item in symbols}
        missing = sorted(requested - matrix_symbols)
        if matrix_date != today:
            return True, symbols, f"data_desatualizada:{matrix_date or 'sem_data'}"
        if missing:
            return True, missing, f"ativos_novos:{','.join(missing)}"
        return False, [], "atualizada"

    def _bootstrap_operational_target_matrix(self) -> None:
        cfg = self.config.get("operational_target_matrix", {}) or {}
        if not bool(cfg.get("enabled", False)) or not bool(cfg.get("update_on_startup", True)):
            return

        symbols = self._current_configured_symbols()
        if not symbols:
            self.logger.warning("[TARGET_MATRIX] Sem ativos configurados para atualizar matriz")
            return

        output_dir = Path(str(cfg.get("output_dir", "reports/operational_target_matrix") or "reports/operational_target_matrix"))
        if not output_dir.is_absolute():
            output_dir = Path.cwd() / output_dir
        latest_path = Path(str(cfg.get("latest_path", output_dir / "operational_target_matrix_latest.json")))
        if not latest_path.is_absolute():
            latest_path = Path.cwd() / latest_path

        due, update_symbols, reason = self._operational_matrix_due(latest_path, symbols)
        if not due:
            self.logger.info(f"[TARGET_MATRIX] Matriz operacional atualizada: {latest_path}")
            return

        lookback_days = max(int(cfg.get("lookback_days", 5) or 5), 1)
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=lookback_days)
        dates = []
        cursor = start_dt
        while cursor.date() <= end_dt.date():
            dates.append(cursor.strftime("%Y%m%d"))
            cursor += timedelta(days=1)

        cmd = [
            sys.executable,
            str(Path.cwd() / "tools" / "build_operational_target_matrix.py"),
        ]
        for date_label in dates:
            cmd.extend(["--date", date_label])
        cmd.extend(
            [
                "--symbols",
                ",".join(update_symbols or symbols),
                "--only-decision",
                str(cfg.get("decision_filter", "ALLOW") or ""),
                "--market-time-offset-hours",
                str(float(cfg.get("market_time_offset_hours", 6) or 6)),
                "--lookahead-minutes",
                str(int(cfg.get("lookahead_minutes", 240) or 240)),
                "--min-samples",
                str(int(cfg.get("min_samples", 10) or 10)),
                "--max-loss-streak",
                str(int(cfg.get("max_loss_streak", 4) or 4)),
                "--min-win-rate",
                str(float(cfg.get("min_win_rate", 45.0) or 45.0)),
                "--targets",
                ",".join(str(item) for item in (cfg.get("targets", [5, 10, 15, 20, 25, 30, 40, 50]) or [])),
                "--stops",
                ",".join(str(item) for item in (cfg.get("stops", [10, 15, 20, 25, 30, 40, 50, 70, 100]) or [])),
                "--start",
                start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "--end",
                end_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "--output-dir",
                str(output_dir),
            ]
        )
        if bool(cfg.get("use_mt5", True)):
            cmd.append("--use-mt5")
        if bool(cfg.get("save_mt5_history", True)):
            cmd.append("--save-mt5-history")

        self.logger.info(
            f"[TARGET_MATRIX] Atualizando matriz operacional | motivo={reason} | ativos={len(update_symbols or symbols)}"
        )

        def run_update() -> None:
            try:
                completed = subprocess.run(
                    cmd,
                    cwd=str(Path.cwd()),
                    capture_output=True,
                    text=True,
                    timeout=max(int(cfg.get("max_startup_seconds", 600) or 600), 30),
                )
                if completed.returncode != 0:
                    self.logger.warning(
                        f"[TARGET_MATRIX] Falha ao atualizar matriz rc={completed.returncode}: {completed.stderr[-1200:]}"
                    )
                    return
                self.logger.info(f"[TARGET_MATRIX] Matriz atualizada: {latest_path}")
                if completed.stdout:
                    self.logger.info(f"[TARGET_MATRIX] {completed.stdout.strip().splitlines()[-1]}")
            except subprocess.TimeoutExpired:
                self.logger.warning("[TARGET_MATRIX] Atualizacao excedeu timeout; Fusion seguira com a matriz existente")
            except Exception as exc:
                self.logger.warning(f"[TARGET_MATRIX] Falha ao atualizar matriz: {exc}")

        startup_mode = str(cfg.get("startup_mode", "blocking") or "blocking").strip().lower()
        if startup_mode in {"skip", "manual", "disabled", "off"}:
            self.logger.info(f"[TARGET_MATRIX] Atualizacao pendente ignorada no startup | modo={startup_mode}")
            return
        if startup_mode in {"background", "async", "thread"}:
            thread = threading.Thread(
                target=run_update,
                name="FusionTargetMatrixBootstrap",
                daemon=True,
            )
            thread.start()
            self.logger.info("[TARGET_MATRIX] Atualizacao iniciada em segundo plano; Fusion seguira a inicializacao")
            return

        run_update()

    def _load_operational_target_matrix(self, path_value: str | Path | None = None) -> dict:
        cfg = self.config.get("operational_target_matrix", {}) or {}
        path = Path(str(path_value or cfg.get("latest_path", "reports/operational_target_matrix/operational_target_matrix_latest.json")))
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except Exception as exc:
            self.logger.warning(f"[TARGET_MATRIX] Falha ao carregar matriz {path}: {exc}")
            return {}

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
        """Carrega todos os modelos por sÃ­mbolo/timeframe."""
        import joblib
        from pathlib import Path
        models_dir = Path(self.config.model.model_dir)
        self.logger.info(f"[BOOT][models] {datetime.now().isoformat(timespec='seconds')} | inicio varredura | dir={models_dir}")
        
        print(f"[DEBUG _load_all_models] Models dir: {models_dir}")
        
        self.logger.debug(f"   Procurando modelos em: {models_dir.absolute()}")
        
        if not models_dir.exists():
            self.logger.error(f"? DiretÃ³rio de modelos nÃ£o encontrado: {models_dir}")
            return
        
        configured_symbols = {str(item).upper() for item in (self.config.get("symbols", []) or [])}
        research_variants = [
            ("lightgbm", "raw"),
            ("lightgbm", "isotonic"),
            ("lightgbm", "logistic"),
            ("catboost", "raw"),
            ("catboost", "isotonic"),
            ("catboost", "logistic"),
        ]
        loaded = 0
        failed = 0
        per_symbol_counts: dict[str, int] = {}
        load_started = time.perf_counter()

        tasks = []
        for sym_dir in models_dir.iterdir():
            if not sym_dir.is_dir():
                continue
            symbol = sym_dir.name
            if configured_symbols and symbol.upper() not in configured_symbols:
                continue

            self.logger.info(f"[BOOT][models] {datetime.now().isoformat(timespec='seconds')} | varrendo simbolo={symbol}")

            for tf_dir in sym_dir.iterdir():
                if not tf_dir.is_dir():
                    continue
                tf = tf_dir.name
                self.logger.info(f"[BOOT][models] {datetime.now().isoformat(timespec='seconds')} | preparando {symbol}/{tf}")

                candidates = [
                    (tf_dir / "model.pkl", tf_dir / "scaler.pkl", tf_dir / "meta.pkl", None, "runtime")
                ]
                for model_name, calibrator_name in research_variants:
                    variant_dir = tf_dir / model_name / calibrator_name
                    candidates.append(
                        (
                            variant_dir / "model.pkl",
                            variant_dir / "scaler.pkl",
                            variant_dir / "meta.json",
                            variant_dir / "calibrator.pkl",
                            f"research:{model_name}/{calibrator_name}",
                        )
                    )
                tasks.append((symbol, tf, candidates))

        def load_one_model(symbol: str, tf: str, candidates: list[tuple]) -> tuple[str, str, SingleModel | None, str]:
            self.logger.info(f"[BOOT][models] {datetime.now().isoformat(timespec='seconds')} | tentando {symbol}/{tf} | candidatos={len(candidates)}")
            for model_path, scaler_path, meta_path, calibrator_path, source in candidates:
                if not all(p.exists() for p in [model_path, scaler_path, meta_path]):
                    self.logger.debug(f"[BOOT][models] {datetime.now().isoformat(timespec='seconds')} | faltando arquivo {symbol}/{tf} | source={source}")
                    continue
                try:
                    if calibrator_path is not None and not calibrator_path.exists():
                        calibrator_path = None
                    model = SingleModel(model_path, scaler_path, meta_path, calibrator_path)
                    self.logger.info(f"[BOOT][models] {datetime.now().isoformat(timespec='seconds')} | carregado {symbol}/{tf} | source={source}")
                    return symbol, tf, model, source
                except Exception as exc:
                    self.logger.warning(f"[BOOT][models] {datetime.now().isoformat(timespec='seconds')} | erro {symbol}/{tf} | source={source} | {exc}")
                    return symbol, tf, None, f"{source}:{exc}"
            self.logger.warning(f"[BOOT][models] {datetime.now().isoformat(timespec='seconds')} | sem candidato valido {symbol}/{tf}")
            return symbol, tf, None, ""

        max_workers = max(2, min(8, (os.cpu_count() or 4)))
        if len(tasks) <= 1:
            max_workers = 1

        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="FusionModelLoad") as executor:
            futures = [executor.submit(load_one_model, symbol, tf, candidates) for symbol, tf, candidates in tasks]
            for future in as_completed(futures):
                symbol, tf, model, source = future.result()
                if model is not None:
                    self.models[(symbol, tf)] = model
                    loaded += 1
                    per_symbol_counts[symbol] = per_symbol_counts.get(symbol, 0) + 1
                    if source != "runtime":
                        self.logger.debug(f"   ?? Modelo research: {symbol}/{tf} | {source}")
                else:
                    failed += 1
                    if source:
                        self.logger.warning(f"   ??  Erro ao carregar {symbol}/{tf}: {source}")
        
        self.logger.info(f"[BOOT][models] {datetime.now().isoformat(timespec='seconds')} | fim carregamento | carregados={loaded} erros={failed}")
        if per_symbol_counts:
            self.logger.info(
                f"[TIMING] {datetime.now().isoformat(timespec='seconds')} | modelos_por_ativo | "
                f"{time.perf_counter() - load_started:.3f}s | "
                + ", ".join(f"{sym}:{count}" for sym, count in sorted(per_symbol_counts.items())[:12])
            )
        if self.config.signal.invert_signals:
            self.logger.warning("?  SINAIS INVERTIDOS: COMPRA vira VENDA e VENDA vira COMPRA")

        inverted_groups = getattr(self.config.signal, "inverted_signal_groups", []) or []
        enabled_inverted_groups = [
            item for item in inverted_groups
            if isinstance(item, dict) and bool(item.get("enabled", True))
        ]
        if enabled_inverted_groups:
            self.logger.warning(
                f"SINAIS INVERTIDOS POR GRUPO: {len(enabled_inverted_groups)} ativo/timeframe(s)"
            )

    def _load_approved_ensembles(self):
        """Carrega ensembles M5 aprovados do FUSION refatorado em modo staging."""
        cfg = self.config.get("approved_ensembles", {}) or {}
        self.logger.info(f"[BOOT][approved_ensembles] {datetime.now().isoformat(timespec='seconds')} | inicio | enabled={bool(cfg.get('enabled', True))}")
        if not bool(cfg.get("enabled", True)):
            self.logger.info("Approved ensembles desativados em config")
            return
        registry_path = Path(cfg.get("registry_path", "fusion_refatorado/models/production_registry/M5_approved_ensembles.json"))
        if not registry_path.is_absolute():
            registry_path = Path.cwd() / registry_path
        loader = ApprovedEnsembleRegistry(
            registry_path=registry_path,
            min_member_weight=float(cfg.get("min_member_weight", 0.25)),
            min_score=float(cfg.get("min_score", 0.25)),
            bars=int(cfg.get("bars", 1200)),
        )
        self.approved_models = loader.load()
        self.logger.info(f"[BOOT][approved_ensembles] {datetime.now().isoformat(timespec='seconds')} | fim | carregados={len(self.approved_models)}")

    def _load_approved_tp_sl(self) -> dict:
        """Carrega TP/SL otimizado por ativo/timeframe para strategy5."""
        cfg = self.config.get("approved_ensembles", {}) or {}
        path = Path(cfg.get("tp_sl_report", "features/features_backteste_ativo_timeframe.csv"))
        self.logger.info(f"[BOOT][tpsl] {datetime.now().isoformat(timespec='seconds')} | inicio | path={path}")
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists():
            self.logger.warning(f"Relatorio TP/SL ausente para approved ensembles: {path}")
            return {}
        try:
            df = pd.read_csv(path)
            result = {}
            for _, row in df.iterrows():
                key = (str(row["symbol"]).upper(), str(row["timeframe"]).upper())
                result[key] = {
                    "target": int(float(row.get("best_target", 500))),
                    "stop_sugerido": int(float(row.get("stop_sugerido", 150))),
                }
            self.logger.info(f"[BOOT][tpsl] {datetime.now().isoformat(timespec='seconds')} | fim | carregados={len(result)}")
            return result
        except Exception as exc:
            self.logger.warning(f"Falha ao carregar TP/SL aprovado: {exc}")
            return {}
    
    def _sync_symbols(self):
        """Sincroniza sÃ­mbolos do broker."""
        broker_symbols = {s.name.upper(): s.name for s in mt5.symbols_get()}
        self.logger.debug(f"   SÃ­mbolos no broker: {len(broker_symbols)}")
        
        raw_configured_symbols = list(self.config.get("symbols", []) or [])
        configured_symbols = []
        for item in raw_configured_symbols:
            symbol = str(item or "").strip()
            if not symbol:
                self.logger.warning("[SYNC_SYMBOLS] Ignorando simbolo vazio/nulo em config.symbols")
                continue
            configured_symbols.append(symbol)
        
        configured_upper = {item.upper() for item in configured_symbols}
        for strategy_name in ["strategy4"]:
            strategy_cfg = self._strategy_config(strategy_name)
            if not bool(strategy_cfg.get("enabled", False)):
                continue
            strategy_symbol = str(strategy_cfg.get("symbol", "") or "").strip()
            if strategy_symbol and strategy_symbol.upper() not in configured_upper:
                configured_symbols.append(strategy_symbol)
                configured_upper.add(strategy_symbol.upper())
        
        contract_overrides = self.config.get("contracts.overrides", {}) or {}
        synced_symbols = []

        for sym in configured_symbols:
            sym_upper = sym.upper()
            mapped = self.config.data.symbol_mapping.get(sym, self.config.data.symbol_mapping.get(sym_upper))
            if mapped and mapped.upper() in broker_symbols:
                real = broker_symbols[mapped.upper()]
                mt5.symbol_select(real, True)
                self.sync_dict[real] = sym
                self._sync_contract(sym, real, contract_overrides)
                synced_symbols.append(f"{sym}?{real}")
                continue

            if sym_upper in broker_symbols:
                real = broker_symbols[sym_upper]
                mt5.symbol_select(real, True)
                self.sync_dict[real] = sym
                self._sync_contract(sym, real, contract_overrides)
                synced_symbols.append(f"{sym}")
                continue

            if sym_upper in ["XAUUSD", "GOLD"]:
                for name in broker_symbols:
                    if "GOLD" in name.upper() or "XAUUSD" in name:
                        mt5.symbol_select(broker_symbols[name], True)
                        self.sync_dict[broker_symbols[name]] = sym
                        self._sync_contract(sym, broker_symbols[name], contract_overrides)
                        synced_symbols.append(f"{sym}?{broker_symbols[name]}")
                        break
        
        if synced_symbols:
            self.logger.debug(f"   Ativos sincronizados: {', '.join(synced_symbols[:8])}" + ("..." if len(synced_symbols) > 8 else ""))
        
        self.logger.info(f"   ? {len(self.sync_dict)} ativos online | {len(broker_symbols)} disponÃ­veis no broker")

    def _sync_contract(self, sym_ia: str, broker_sym: str, overrides: dict | None = None) -> None:
        if mt5 is None:
            return
        try:
            info = mt5.symbol_info(broker_sym)
            if info is None:
                return
            override = None
            for key in [sym_ia, sym_ia.upper(), broker_sym, broker_sym.upper()]:
                if isinstance(overrides, dict) and key in overrides:
                    override = overrides[key]
                    break
            contract = apply_contract_override(contract_from_mt5_info(sym_ia.upper(), broker_sym, info), override)
            self.oms.update_contract(contract)
            self._publish_event(
                FusionEventType.DASHBOARD_UPDATE,
                {"contract": contract.to_dict()},
                source="ContractSync",
                correlation_id=f"{sym_ia.upper()}:CONTRACT",
            )
        except Exception as exc:
            self.logger.warning(f"Falha ao sincronizar contrato {sym_ia}/{broker_sym}: {exc}")

    def _refresh_oms_state(self) -> None:
        if mt5 is None:
            return
        try:
            log_ticks = bool((self.config.get("event_bus", {}) or {}).get("log_tick_updates", False))
            for broker_symbol, sym_ia in self.sync_dict.items():
                tick = mt5.symbol_info_tick(broker_symbol)
                if tick is None:
                    continue
                bid = float(getattr(tick, "bid", 0.0) or 0.0)
                ask = float(getattr(tick, "ask", 0.0) or 0.0)
                fusion_tick = FusionTick(
                    symbol=sym_ia.upper(),
                    broker_symbol=broker_symbol,
                    bid=bid,
                    ask=ask,
                    last=float(getattr(tick, "last", 0.0) or 0.0),
                    volume=float(getattr(tick, "volume", 0.0) or 0.0),
                    spread=max(0.0, ask - bid) if ask and bid else 0.0,
                )
                self.oms.update_tick(fusion_tick)
                if log_ticks:
                    self._publish_event(
                        FusionEventType.TICK_UPDATE,
                        fusion_tick.to_dict(),
                        source="OMS",
                        correlation_id=f"{sym_ia.upper()}:TICK",
                    )
        except Exception as exc:
            self.logger.warning(f"Falha ao atualizar ticks no OMS: {exc}")

        try:
            account = mt5.account_info()
            if account is not None:
                fusion_account = FusionAccount(
                    account_id=str(getattr(account, "login", "") or ""),
                    balance=float(getattr(account, "balance", 0.0) or 0.0),
                    equity=float(getattr(account, "equity", 0.0) or 0.0),
                    margin=float(getattr(account, "margin", 0.0) or 0.0),
                    free_margin=float(getattr(account, "margin_free", 0.0) or 0.0),
                    currency=str(getattr(account, "currency", "") or ""),
                )
                self.oms.update_account(fusion_account)
                self._publish_event(
                    FusionEventType.ACCOUNT_UPDATE,
                    fusion_account.to_dict(),
                    source="OMS",
                    correlation_id=f"ACCOUNT:{fusion_account.account_id}",
                )
        except Exception as exc:
            self.logger.warning(f"Falha ao atualizar conta no OMS: {exc}")

        try:
            positions = mt5.positions_get()
            positions = list(positions) if positions else []
            for pos in positions:
                broker_symbol = str(getattr(pos, "symbol", "") or "")
                symbol = self._broker_symbol_to_base(broker_symbol)
                direction = "BUY" if int(getattr(pos, "type", -1)) == mt5.ORDER_TYPE_BUY else "SELL"
                fusion_position = FusionPosition(
                    position_id=str(getattr(pos, "ticket", "") or ""),
                    symbol=symbol,
                    broker_symbol=broker_symbol,
                    direction=direction,
                    volume=float(getattr(pos, "volume", 0.0) or 0.0),
                    price_open=float(getattr(pos, "price_open", 0.0) or 0.0),
                    price_current=float(getattr(pos, "price_current", 0.0) or 0.0),
                    profit=float(getattr(pos, "profit", 0.0) or 0.0),
                    magic=int(getattr(pos, "magic", 0) or 0),
                )
                self.oms.update_position(fusion_position)
                self._publish_event(
                    FusionEventType.POSITION_UPDATE,
                    fusion_position.to_dict(),
                    source="OMS",
                    correlation_id=f"{symbol}:POSITION:{fusion_position.position_id}",
                )
        except Exception as exc:
            self.logger.warning(f"Falha ao atualizar posicoes no OMS: {exc}")

        try:
            cfg = self.config.get("oms", {}) or {}
            lookback_hours = int(cfg.get("trade_history_lookback_hours", 24) or 24)
            history_from = datetime.now() - timedelta(hours=max(1, lookback_hours))
            deals = mt5.history_deals_get(history_from, datetime.now())
            deals = list(deals) if deals else []
            for deal in deals:
                ticket = str(getattr(deal, "ticket", "") or "")
                if not ticket or ticket in self._seen_deal_tickets:
                    continue
                self._seen_deal_tickets.add(ticket)
                broker_symbol = str(getattr(deal, "symbol", "") or "")
                if not broker_symbol:
                    continue
                symbol = self._broker_symbol_to_base(broker_symbol)
                deal_type = int(getattr(deal, "type", -1))
                direction = "BUY" if deal_type == getattr(mt5, "DEAL_TYPE_BUY", 0) else "SELL"
                trade = FusionTrade(
                    trade_id=ticket,
                    order_id=str(getattr(deal, "order", "") or ""),
                    symbol=symbol,
                    broker_symbol=broker_symbol,
                    direction=direction,
                    volume=float(getattr(deal, "volume", 0.0) or 0.0),
                    price=float(getattr(deal, "price", 0.0) or 0.0),
                    profit=float(getattr(deal, "profit", 0.0) or 0.0),
                    metadata={
                        "position_id": getattr(deal, "position_id", ""),
                        "magic": getattr(deal, "magic", 0),
                        "comment": getattr(deal, "comment", ""),
                        "entry": getattr(deal, "entry", ""),
                    },
                )
                self.oms.update_trade(trade)
                self._publish_event(
                    FusionEventType.TRADE_UPDATE,
                    trade.to_dict(),
                    source="OMS",
                    correlation_id=f"{symbol}:TRADE:{ticket}",
                )
        except Exception as exc:
            self.logger.warning(f"Falha ao atualizar deals/trades no OMS: {exc}")
        try:
            self.oms_snapshot_writer.write(self.oms)
        except Exception as exc:
            self.logger.warning(f"Falha ao gravar snapshot do OMS: {exc}")
    
    def _calculate_features(self, symbol: str, tf: str) -> dict:
        """Calcula features para sÃ­mbolo/timeframe com cache TTL."""
        key = (symbol.upper(), tf.upper())
        now = time.time()
        
        # 1. Verifica cache
        if key in self.features_cache:
            features, timestamp = self.features_cache[key]
            age = now - timestamp
            if age < self.features_cache_ttl:
                self.features_cache_hits += 1
                return features  # HIT! Retorna cache sem recalcular
            # Cache expirou, precisa recalcular
        
        # 2. Se nÃ£o estÃ¡ em cache ou expirou, calcula
        self.features_cache_misses += 1
        
        df = self._get_rates_frame(symbol, tf, 100, start_pos=0, min_rows=100)
        if df.empty:
            return pd.DataFrame()
        df.set_index('time', inplace=True)
        
        if len(df) < 100:
            return pd.DataFrame()
        
        features = pd.DataFrame(index=df.index)
        close = df['close']
        high = df['high']
        low = df['low']
        
        ret = np.log(close / close.shift(1))
        features['ret'] = ret
        features['ret_5'] = ret.rolling(5).sum()
        features['ret_10'] = ret.rolling(10).sum()
        features['ret_20'] = ret.rolling(20).sum()
        
        rsi14 = RSI.calculate(df, 14)
        rsi28 = RSI.calculate(df, 28)
        features['rsi14'] = rsi14
        features['rsi28'] = rsi28
        features['rsi_diff'] = rsi14 - rsi28
        features['rsi_ma5'] = rsi14.rolling(5).mean()
        features['rsi_gap'] = rsi14 - rsi14.rolling(10).mean()
        
        ema8 = EMA.calculate(df, 8)
        ema21 = EMA.calculate(df, 21)
        ema50 = EMA.calculate(df, 50)
        ema200 = EMA.calculate(df, 200)
        
        features['ema8'] = ema8
        features['ema21'] = ema21
        features['ema50'] = ema50
        features['ema200'] = ema200
        
        features['dist_ema8'] = (close / ema8) - 1
        features['dist_ema21'] = (close / ema21) - 1
        features['dist_ema50'] = (close / ema50) - 1
        features['dist_ema200'] = (close / ema200) - 1
        
        range_pct = (high - low) / close
        features['range_pct'] = range_pct
        features['range_ma10'] = range_pct.rolling(10).mean()
        
        features['high_20'] = high.rolling(20).max()
        features['low_20'] = low.rolling(20).min()
        features['position_in_range'] = (close - features['low_20']) / (features['high_20'] - features['low_20'] + 1e-9)
        
        vol5 = ret.rolling(5).std()
        vol20 = ret.rolling(20).std()
        features['vol5'] = vol5
        features['vol20'] = vol20
        features['vol_ratio'] = vol5 / (vol20 + 1e-9)
        
        ema_fast = close.ewm(span=12).mean()
        ema_slow = close.ewm(span=26).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=9).mean()
        features['macd'] = macd_line
        features['macd_signal'] = signal_line
        features['macd_hist'] = macd_line - signal_line
        
        features['upper_bb'] = ema21 + (ret.rolling(20).std() * 2)
        features['lower_bb'] = ema21 - (ret.rolling(20).std() * 2)
        features['bb_width'] = features['upper_bb'] - features['lower_bb']
        
        features['alpha_vam'] = AlphaMiner.vam(df, 20)
        features['alpha_effort'] = AlphaMiner.effort(df, 50)
        features['alpha_mrs'] = AlphaMiner.mrs(df, 20)
        features['alpha_rsi_gap'] = AlphaMiner.rsi_gap(df, 14)
        
        trend_alignment = (rsi14 > 50).astype(int)
        for period in [5, 10, 20]:
            ma_trend = (close > EMA.calculate(df, period)).astype(int)
            trend_alignment = trend_alignment + ma_trend
        features['trend_alignment'] = trend_alignment
        
        raw_cols = ['open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume']
        for col in raw_cols:
            if col in df.columns and col not in features.columns:
                features[col] = df[col]
        
        result = features.dropna().iloc[[-1]]
        
        # 3. Armazena em cache
        self.features_cache[key] = (result, now)
        
        return result

    def _rates_tf_code(self, tf: str):
        if mt5 is None:
            return None
        return {
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1,
        }.get(str(tf).upper())

    def _rates_cache_preload_bars(self, tf: str, requested_bars: int) -> int:
        preload = {
            "M5": 260,
            "M15": 260,
            "M30": 260,
            "H1": 260,
            "H4": 260,
            "D1": 220,
        }.get(str(tf).upper(), 260)
        return max(int(requested_bars or 1), preload)

    def _get_rates_frame(self, broker_sym: str, tf: str, bars: int, start_pos: int = 0, min_rows: int = 0) -> pd.DataFrame:
        if mt5 is None:
            return pd.DataFrame()
        tf_code = self._rates_tf_code(tf)
        if tf_code is None:
            return pd.DataFrame()

        symbol = str(broker_sym or "").strip()
        if not symbol:
            return pd.DataFrame()

        tf_upper = str(tf).upper()
        start_pos = int(start_pos or 0)
        bars = max(1, int(bars or 1))
        min_rows = max(0, int(min_rows or 0))
        cache_key = (symbol.upper(), tf_upper, start_pos)
        now = time.time()

        cached = self.rates_cache.get(cache_key)
        if cached:
            frame, timestamp, cached_bars = cached
            if now - timestamp < self.rates_cache_ttl and (start_pos != 0 or cached_bars >= bars):
                self.rates_cache_hits += 1
                return frame.copy()

        fetch_bars = bars if start_pos != 0 else self._rates_cache_preload_bars(tf_upper, bars)
        try:
            rates = mt5.copy_rates_from_pos(symbol, tf_code, start_pos, fetch_bars)
        except Exception:
            return pd.DataFrame()

        if rates is None or len(rates) < max(2, min_rows):
            return pd.DataFrame()

        df = pd.DataFrame(rates)
        if df.empty or "time" not in df.columns:
            return pd.DataFrame()

        df["time"] = pd.to_datetime(df["time"], unit="s")
        df = df.sort_values("time").reset_index(drop=True)
        self.rates_cache[cache_key] = (df, now, fetch_bars)
        self.rates_cache_misses += 1
        return df.copy()

    def _strategy_config(self, strategy_name: str) -> dict:
        return self.config.get(f"strategies.{strategy_name}", {}) or {}

    def _strategy_enabled(self, strategy_name: str) -> bool:
        return bool(self._strategy_config(strategy_name).get("enabled", False))

    def _strategy_magic(self, strategy_name: str, tf: str) -> int:
        tf_minutes = self.TF_MINUTES.get(tf, 5)
        cfg = self._strategy_config(strategy_name)
        default_magic_prefix = {
            "strategy1": 10,
            "strategy2": 20,
            "strategy3": 30,
            "strategy4": 40,
            "strategy5": 50,
            "strategy6": 60,
            "strategy7": 70,
            "strategy8": 80,
            "strategy9": 90,
            "strategy10": 91,
            "strategy11": 92,
            "strategy12": 93,
            "strategy13": 94,
            "strategy14": 95,
        }.get(strategy_name, 90)
        magic_base = int(cfg.get("magic_base", default_magic_prefix))
        magic_prefix = magic_base if magic_base < 100 else magic_base // 100
        return int(f"{magic_prefix}{tf_minutes:02d}")

    def _strategy_magic_group(self, strategy_name: str) -> list:
        cfg = self._strategy_config(strategy_name)
        legacy_magics = cfg.get("legacy_magics", []) or []
        magics = {self._strategy_magic(strategy_name, tf) for tf in self.TIMEFRAMES}
        magics.update(int(magic) for magic in legacy_magics)
        return sorted(magics)

    def _system_magic_group(self) -> list:
        magics = set()
        for strategy_name in ["strategy1", "strategy2", "strategy3", "strategy4", "strategy5", "strategy6", "strategy7", "strategy8", "strategy9", "strategy10", "strategy11", "strategy12", "strategy13", "strategy14"]:
            magics.update(self._strategy_magic_group(strategy_name))
        return sorted(magics)

    def _log_strategy_magic_map(self):
        strategies_active = []
        for strategy_name in ["strategy1", "strategy2", "strategy3", "strategy4", "strategy5", "strategy6", "strategy7", "strategy8", "strategy9", "strategy10", "strategy11", "strategy12", "strategy13", "strategy14"]:
            if not self._strategy_enabled(strategy_name):
                continue
            magics = ", ".join(f"{tf}={self._strategy_magic(strategy_name, tf)}" for tf in self.TIMEFRAMES)
            strategies_active.append(strategy_name.upper())
            self.logger.debug(f"   {strategy_name.upper()} ? magics: {magics}")
        
        if strategies_active:
            self.logger.info(f"   ? EstratÃ©gias ativas: {', '.join(strategies_active)}")
        else:
            strategy_keys = list((self.config.get("strategies", {}) or {}).keys())
            self.logger.warning(f"   ??  Nenhuma estratÃ©gia ativa no config! keys={strategy_keys}")

    def _strategy_cooldown(self, strategy_name: str) -> int:
        return int(self._strategy_config(strategy_name).get("cooldown_seconds", 300))

    def _recent_close_cooldown_remaining(self, strategy_name: str, broker_sym: str, sym_ia: str, tf: str) -> int:
        cfg = self.config.get("trading.reentry_cooldown_after_close", {}) or {}
        if not bool(cfg.get("enabled", True)):
            return 0
        if mt5 is None:
            return 0
        seconds = int(cfg.get("seconds", self._strategy_cooldown(strategy_name)) or self._strategy_cooldown(strategy_name))
        if seconds <= 0:
            return 0
        scope = str(cfg.get("scope", "system_symbol") or "system_symbol").lower()
        now = datetime.now()
        history_from = now - timedelta(seconds=seconds + 120)
        try:
            deals = mt5.history_deals_get(history_from, now)
        except Exception as exc:
            self.logger.warning(f"Falha ao consultar historico para cooldown pos-fechamento: {exc}")
            return 0
        if not deals:
            return 0

        entry_out = getattr(mt5, "DEAL_ENTRY_OUT", 1)
        entry_out_by = getattr(mt5, "DEAL_ENTRY_OUT_BY", 3)
        candidate_symbol = sym_ia.upper()
        magic_filter = set(self._system_magic_group() if scope.startswith("system") else self._strategy_magic_group(strategy_name))
        newest_close_time = None

        for deal in deals:
            deal_symbol = str(getattr(deal, "symbol", "") or "")
            if deal_symbol != broker_sym and self._broker_symbol_to_base(deal_symbol) != candidate_symbol:
                continue
            if magic_filter and int(getattr(deal, "magic", 0) or 0) not in magic_filter:
                continue
            entry = int(getattr(deal, "entry", -1))
            if entry not in {entry_out, entry_out_by}:
                continue
            deal_time_raw = getattr(deal, "time", 0) or 0
            try:
                deal_time = datetime.fromtimestamp(int(deal_time_raw))
            except (TypeError, ValueError, OSError):
                continue
            if newest_close_time is None or deal_time > newest_close_time:
                newest_close_time = deal_time

        if newest_close_time is None:
            return 0
        elapsed = (now - newest_close_time).total_seconds()
        remaining = int(max(0, seconds - elapsed))
        return remaining

    def _approved_feature_row(self, sym_ia: str, tf: str) -> dict:
        return dict(self.approved_tp_sl.get((sym_ia.upper(), tf.upper()), {}))

    def _strategy_prediction(self, strategy_name: str, pred: int) -> int:
        """Aplica inversao de sinal no nivel da estrategia."""
        if not bool(self._strategy_config(strategy_name).get("invert_signal", False)):
            return pred
        if pred == 1:
            return 2
        if pred == 2:
            return 1
        return pred

    @staticmethod
    def _normalized_signal_symbol(symbol: str) -> str:
        value = str(symbol or "").upper().strip()
        if value == "XAUUSD":
            return "GOLD"
        return value

    @staticmethod
    def _opposite_prediction(pred: int) -> int:
        if pred == 1:
            return 2
        if pred == 2:
            return 1
        return pred

    @staticmethod
    def _truthy_config_value(value) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        return str(value).strip().lower() not in {"0", "false", "no", "nao", "nÃ£o", "off", "disabled"}

    def _runtime_section(self, name: str) -> dict:
        try:
            return self.runtime_control.section(name)
        except Exception as exc:
            self.logger.warning(f"[RUNTIME_CONTROL] Falha ao ler secao {name}: {exc}")
            return {}

    @staticmethod
    def _merge_policy_dicts(base: dict | None, override: dict | None) -> dict:
        result = dict(base or {})
        for key, value in (override or {}).items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = FusionV2._merge_policy_dicts(result.get(key), value)
            else:
                result[key] = value
        return result

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
        cfg = self._runtime_section("signals")
        if not cfg:
            return pred, p_buy, p_sell, ""
        try:
            buy_threshold = float(cfg.get("buy_threshold", getattr(self.config.signal, "buy_threshold", 0.55)) or 0.55)
            sell_threshold = float(cfg.get("sell_threshold", getattr(self.config.signal, "sell_threshold", 0.55)) or 0.55)
            confidence_filter = float(cfg.get("confidence_filter", getattr(self.config.signal, "confidence_filter", 0.0)) or 0.0)
            min_signal_strength = float(cfg.get("min_signal_strength", getattr(self.config.signal, "min_signal_strength", 0.0)) or 0.0)
        except (TypeError, ValueError):
            return pred, p_buy, p_sell, ""

        policy = self._symbol_timeframe_policy(symbol, timeframe)
        policy_signals = {}
        if isinstance(policy, dict):
            candidate = policy.get("signals", policy.get("thresholds", {}))
            if isinstance(candidate, dict):
                policy_signals = candidate
        try:
            buy_threshold = float(policy_signals.get("buy_threshold", buy_threshold) or buy_threshold)
            sell_threshold = float(policy_signals.get("sell_threshold", sell_threshold) or sell_threshold)
            confidence_filter = float(policy_signals.get("confidence_filter", confidence_filter) or confidence_filter)
            min_signal_strength = float(policy_signals.get("min_signal_strength", min_signal_strength) or min_signal_strength)
        except (TypeError, ValueError):
            pass

        p_buy = float(p_buy or 0.0)
        p_sell = float(p_sell or 0.0)
        edge = abs(p_buy - p_sell)
        confidence = max(p_buy, p_sell)
        original_pred = int(pred or 0)
        if confidence < confidence_filter or edge < min_signal_strength:
            new_pred = 0
        elif p_buy >= buy_threshold and p_buy > p_sell:
            new_pred = 1
        elif p_sell >= sell_threshold and p_sell > p_buy:
            new_pred = 2
        else:
            new_pred = 0

        if new_pred == original_pred:
            return pred, p_buy, p_sell, ""
        old_side = "BUY" if original_pred == 1 else "SELL" if original_pred == 2 else "WAIT"
        new_side = "BUY" if new_pred == 1 else "SELL" if new_pred == 2 else "WAIT"
        reason = (
            f"runtime_threshold:{old_side}->{new_side}:"
            f"buy={buy_threshold:.2f}:sell={sell_threshold:.2f}:"
            f"conf={confidence_filter:.2f}:edge={min_signal_strength:.2f}"
        )
        self.logger.info(
            f"[RUNTIME_SIGNAL] {symbol} {timeframe} {old_side}->{new_side} | "
            f"p_buy={p_buy:.4f} p_sell={p_sell:.4f} edge={edge:.4f}"
        )
        return new_pred, p_buy, p_sell, reason

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

    def _signal_group_inversion_reason(self, symbol: str, timeframe: str) -> str:
        groups = getattr(self.config.signal, "inverted_signal_groups", []) or []
        current_symbol = self._normalized_signal_symbol(symbol)
        current_tf = str(timeframe or "").upper().strip()
        for group in groups:
            if not isinstance(group, dict):
                continue
            if not self._truthy_config_value(group.get("enabled", True)):
                continue
            group_symbol = self._normalized_signal_symbol(group.get("symbol", ""))
            group_tf = str(group.get("timeframe", "")).upper().strip()
            symbol_match = group_symbol in {"*", "ALL"} or group_symbol == current_symbol
            timeframe_match = group_tf in {"*", "ALL"} or group_tf == current_tf
            if symbol_match and timeframe_match:
                return str(group.get("reason", "inverted_signal_group") or "inverted_signal_group")
        return ""

    def _apply_signal_inversion(self, pred: int, p_buy: float, p_sell: float, symbol: str, timeframe: str):
        if pred not in (1, 2):
            return pred, p_buy, p_sell, ""

        reason = ""
        if bool(getattr(self.config.signal, "invert_signals", False)):
            reason = "global_invert_signals"
        else:
            reason = self._signal_group_inversion_reason(symbol, timeframe)

        if not reason:
            return pred, p_buy, p_sell, ""

        original_p_buy = float(p_buy or 0.0)
        original_p_sell = float(p_sell or 0.0)
        inverted_pred = self._opposite_prediction(pred)
        inverted_p_buy = original_p_sell
        inverted_p_sell = original_p_buy
        original_side = "BUY" if pred == 1 else "SELL"
        inverted_side = "BUY" if inverted_pred == 1 else "SELL"
        self.logger.warning(
            f"[SIGNAL_INVERSION] {symbol} {timeframe} {original_side}->{inverted_side} | "
            f"motivo={reason} | p_buy={original_p_buy:.4f}->{inverted_p_buy:.4f} | "
            f"p_sell={original_p_sell:.4f}->{inverted_p_sell:.4f}"
        )
        return inverted_pred, inverted_p_buy, inverted_p_sell, reason

    def _signal_override_active(self, rule: dict) -> bool:
        if not self._truthy_config_value(rule.get("enabled", True)):
            return False
        now = datetime.now()
        valid_from = str(rule.get("valid_from", "") or "").strip()
        valid_until = str(rule.get("valid_until", "") or "").strip()
        try:
            if valid_from and now < datetime.fromisoformat(valid_from[:19]):
                return False
        except ValueError:
            pass
        try:
            if valid_until and now > datetime.fromisoformat(valid_until[:19]):
                return False
        except ValueError:
            pass
        return True

    def _matching_signal_override(self, symbol: str, timeframe: str) -> dict:
        cfg = self.config.get("signal_overrides", {}) or {}
        if not bool(cfg.get("enabled", False)):
            return {}
        current_symbol = self._normalized_signal_symbol(symbol)
        current_tf = str(timeframe or "").upper().strip()
        for rule in cfg.get("rules", []) or []:
            if not isinstance(rule, dict) or not self._signal_override_active(rule):
                continue
            rule_symbol = self._normalized_signal_symbol(rule.get("symbol", ""))
            rule_tf = str(rule.get("timeframe", "")).upper().strip()
            symbol_match = rule_symbol in {"*", "ALL"} or rule_symbol == current_symbol
            timeframe_match = rule_tf in {"*", "ALL"} or rule_tf == current_tf
            if symbol_match and timeframe_match:
                return rule
        return {}

    def _apply_signal_override(self, pred: int, p_buy: float, p_sell: float, symbol: str, timeframe: str):
        rule = self._matching_signal_override(symbol, timeframe)
        if not rule:
            return pred, p_buy, p_sell, ""

        action = str(rule.get("action", "") or "").lower().strip()
        reason = str(rule.get("reason", action or "signal_override") or "signal_override")
        original_pred = int(pred or 0)
        original_p_buy = float(p_buy or 0.0)
        original_p_sell = float(p_sell or 0.0)
        new_pred = original_pred
        new_p_buy = original_p_buy
        new_p_sell = original_p_sell

        if action in {"force_wait", "wait", "neutral", "neutro"}:
            new_pred = 0
        elif action == "block_buy" and original_pred == 1:
            new_pred = 0
        elif action == "block_sell" and original_pred == 2:
            new_pred = 0
        elif action == "force_buy":
            confidence = float(rule.get("confidence", max(original_p_buy, original_p_sell, 0.60)) or 0.60)
            new_pred = 1
            new_p_buy = max(original_p_buy, confidence)
            new_p_sell = min(original_p_sell, 1.0 - min(new_p_buy, 1.0))
        elif action == "force_sell":
            confidence = float(rule.get("confidence", max(original_p_buy, original_p_sell, 0.60)) or 0.60)
            new_pred = 2
            new_p_sell = max(original_p_sell, confidence)
            new_p_buy = min(original_p_buy, 1.0 - min(new_p_sell, 1.0))
        elif action == "invert" and original_pred in (1, 2):
            new_pred = self._opposite_prediction(original_pred)
            new_p_buy = original_p_sell
            new_p_sell = original_p_buy
        elif action == "reduce_confidence" and original_pred in (1, 2):
            factor = max(0.0, min(1.0, float(rule.get("factor", 0.50) or 0.50)))
            if original_pred == 1:
                new_p_buy = original_p_buy * factor
            else:
                new_p_sell = original_p_sell * factor
            new_pred = 0
        else:
            return pred, p_buy, p_sell, ""

        if new_pred == original_pred and new_p_buy == original_p_buy and new_p_sell == original_p_sell:
            return pred, p_buy, p_sell, ""

        original_side = "BUY" if original_pred == 1 else "SELL" if original_pred == 2 else "WAIT"
        new_side = "BUY" if new_pred == 1 else "SELL" if new_pred == 2 else "WAIT"
        self.logger.warning(
            f"[SIGNAL_OVERRIDE] {symbol} {timeframe} {original_side}->{new_side} | "
            f"action={action} motivo={reason} | p_buy={original_p_buy:.4f}->{new_p_buy:.4f} | "
            f"p_sell={original_p_sell:.4f}->{new_p_sell:.4f}"
        )
        return new_pred, new_p_buy, new_p_sell, f"{action}:{reason}"

    def _strategy_max_positions(self, strategy_name: str) -> int:
        cfg = self._strategy_config(strategy_name)
        runtime_value = self.runtime_control.get("trading.max_positions_per_symbol")
        if runtime_value is not None:
            try:
                return max(int(runtime_value), 0)
            except (TypeError, ValueError):
                pass
        if bool(self.config.get("trading.position_limits.enabled", True)):
            return int(self.config.get("trading.position_limits.max_per_symbol", cfg.get("max_positions_per_symbol", 1)))
        return int(cfg.get("max_positions_per_symbol", cfg.get("max_positions_per_side", 1)))

    def _position_limit_scope(self, strategy_name: str) -> str:
        cfg = self._strategy_config(strategy_name)
        if bool(self.config.get("trading.position_limits.enabled", True)):
            return str(self.config.get("trading.position_limits.scope", cfg.get("max_positions_scope", "strategy"))).lower()
        return str(cfg.get("max_positions_scope", "strategy")).lower()

    def _position_limit_any_direction(self, strategy_name: str) -> bool:
        cfg = self._strategy_config(strategy_name)
        if bool(self.config.get("trading.position_limits.enabled", True)):
            mode = self.config.get("trading.position_limits.mode", cfg.get("max_positions_mode", "any_direction"))
        else:
            mode = cfg.get("max_positions_mode", "any_direction")
        return str(mode).lower() == "any_direction"

    def _load_strategy_features(self) -> pd.DataFrame:
        path_value = self.config.get("strategies.strategy2.features_path", "./features/features_backteste_dinamica.csv")
        path = Path(path_value)
        if not path.is_absolute():
            path = Path.cwd() / path
        self.logger.info(f"[BOOT][strategy_features] {datetime.now().isoformat(timespec='seconds')} | caminho={path}")
        if not path.exists():
            self.logger.warning(f"[BOOT][strategy_features] {datetime.now().isoformat(timespec='seconds')} | arquivo ausente")
            return pd.DataFrame()
        try:
            df = pd.read_csv(path)
            self.logger.info(f"[BOOT][strategy_features] {datetime.now().isoformat(timespec='seconds')} | carregado rows={len(df)} cols={len(df.columns)}")
            for col in ["symbol", "timeframe"]:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.upper()
            for col in ["direcao", "entrada_posicao", "nivel_candle_anterior", "candle_anterior"]:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.lower()
            return df
        except Exception as e:
            self.logger.warning(f"Nao foi possivel carregar features da strategy2: {e}")
            return pd.DataFrame()

    def _recent_candle_context(self, symbol: str, tf: str) -> dict:
        df = self._get_rates_frame(symbol, tf, 3, start_pos=0, min_rows=2)
        if df.empty or len(df) < 2:
            return {}
        df = df.copy()
        current = df.iloc[-1]
        previous = df.iloc[-2]
        if previous["close"] > previous["open"]:
            candle_type = "alta"
        elif previous["close"] < previous["open"]:
            candle_type = "baixa"
        else:
            candle_type = "doji"
        return {"current": current, "previous": previous, "candle_type": candle_type}

    def _strategy_feature_candidate(self, strategy_name: str, sym_ia: str, tf: str, pred: int, broker_sym: str) -> dict:
        if self.strategy_features.empty:
            return {}
        ctx = self._recent_candle_context(broker_sym, tf)
        if not ctx:
            return {}

        direcao = "compra" if pred == 1 else "venda"
        entrada_posicao = "acima" if pred == 1 else "abaixo"
        current = ctx["current"]
        previous = ctx["previous"]
        levels = {
            "maxima": float(previous["high"]),
            "minima": float(previous["low"]),
            "abertura": float(previous["open"]),
            "fechamento": float(previous["close"]),
        }
        if pred == 1:
            triggered_levels = [name for name, value in levels.items() if float(current["high"]) >= value]
        else:
            triggered_levels = [name for name, value in levels.items() if float(current["low"]) <= value]
        if not triggered_levels:
            return {}

        cfg = self._strategy_config(strategy_name)
        df = self.strategy_features
        mask = (
            (df["symbol"] == sym_ia.upper()) &
            (df["timeframe"] == tf.upper()) &
            (df["direcao"] == direcao) &
            (df["entrada_posicao"] == entrada_posicao) &
            (df["candle_anterior"] == ctx["candle_type"]) &
            (df["nivel_candle_anterior"].isin(triggered_levels))
        )
        candidates = df.loc[mask].copy()
        if candidates.empty:
            return {}

        candidates = candidates[candidates["entradas"] >= int(cfg.get("min_entries", 100))]
        candidates = candidates[candidates["win_rate"] >= float(cfg.get("min_win_rate", 0.0))]
        if "score" in candidates.columns:
            candidates = candidates[candidates["score"] >= float(cfg.get("min_score", -999999.0))]
        if candidates.empty:
            return {}

        preferred_target = int(cfg.get("target_preference", 500))
        target_candidates = candidates[candidates["target"] == preferred_target]
        if not target_candidates.empty:
            candidates = target_candidates
        sort_cols = [col for col in ["score", "win_rate", "entradas"] if col in candidates.columns]
        if sort_cols:
            candidates = candidates.sort_values(sort_cols, ascending=[False] * len(sort_cols))
        return candidates.iloc[0].to_dict()

    def _strategy2_feature_candidate(self, sym_ia: str, tf: str, pred: int, broker_sym: str) -> dict:
        return self._strategy_feature_candidate("strategy2", sym_ia, tf, pred, broker_sym)

    def _is_gold_symbol(self, sym_ia: str) -> bool:
        return sym_ia.upper() in ["XAUUSD", "GOLD"]

    def _strategy4_ema_alignment_ok(self, broker_sym: str, tf: str) -> bool:
        return self._strategy_ema_alignment_ok("strategy4", 1, broker_sym, "GOLD", tf)

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
        cfg = self._runtime_filter_config("ema_alignment", self.config.get("entry_filters.ema_alignment", {}) or {}, sym_ia, tf)
        if not bool(cfg.get("enabled", True)):
            return True
        mode = str(cfg.get("mode", "block") or "block").lower()
        if mode == "shadow":
            return True
        periods = list(cfg.get("periods", [9, 21, 50]) or [9, 21, 50])
        if len(periods) != 3:
            periods = [9, 21, 50]
        fast, mid, slow = [int(period) for period in periods]
        if mt5 is None:
            self.logger.info(f"{strategy_name.upper()} {sym_ia} {tf} bloqueada: MT5 indisponivel para filtro EMA")
            return False
        tf_code = {
            "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1
        }.get(tf)
        if not tf_code:
            self.logger.info(f"{strategy_name.upper()} {sym_ia} {tf} bloqueada: MT5/timeframe indisponivel para filtro EMA")
            return False
        if not bool(cfg.get("require_signal_timeframe_alignment", True)):
            self.logger.warning(
                "entry_filters.ema_alignment.require_signal_timeframe_alignment=false ignorado; "
                "o timeframe da ordem sempre precisa estar alinhado."
            )
        bars = max(slow + 10, int(cfg.get("bars", 80)))
        slope_cfg = cfg.get("slope_filter", {}) or {}
        if bool(slope_cfg.get("enabled", False)):
            bars = max(bars, slow + max(1, int(slope_cfg.get("lookback_bars", 5) or 5)) + 5)
        start_pos = 1 if bool(cfg.get("use_closed_candle", True)) else 0
        rates_df = self._get_rates_frame(broker_sym, tf, bars, start_pos=start_pos, min_rows=slow + 5)
        if rates_df.empty or len(rates_df) < slow + 5:
            self.logger.info(f"{strategy_name.upper()} {sym_ia} {tf} bloqueada: dados insuficientes para filtro EMA")
            return False
        df = rates_df.copy()
        close = df["close"].astype(float)
        ema_fast_series = close.ewm(span=fast, adjust=False).mean()
        ema_mid_series = close.ewm(span=mid, adjust=False).mean()
        ema_slow_series = close.ewm(span=slow, adjust=False).mean()
        ema_fast = ema_fast_series.iloc[-1]
        ema_mid = ema_mid_series.iloc[-1]
        ema_slow = ema_slow_series.iloc[-1]
        point_value = self._symbol_point_value(broker_sym, sym_ia)
        if point_value <= 0:
            self.logger.info(f"{strategy_name.upper()} {sym_ia} {tf} bloqueada: point_value indisponivel para filtro EMA")
            return False
        distance_cfg = cfg.get("min_distance_points", {}) or {}
        default_dist = distance_cfg.get("default", {}) or {}
        timeframe_dist = (distance_cfg.get("by_timeframe", {}) or {}).get(tf, {}) or {}
        min_fast_mid = float(timeframe_dist.get("ema9_ema21", default_dist.get("ema9_ema21", 0)) or 0)
        min_mid_slow = float(timeframe_dist.get("ema21_ema50", default_dist.get("ema21_ema50", 0)) or 0)
        if pred == 1:
            aligned = ema_fast > ema_mid > ema_slow
            direction = "BUY"
            rule = f"EMA{fast} > EMA{mid} > EMA{slow}"
            fast_mid_points = (ema_fast - ema_mid) / point_value
            mid_slow_points = (ema_mid - ema_slow) / point_value
        elif pred == 2:
            aligned = ema_fast < ema_mid < ema_slow
            direction = "SELL"
            rule = f"EMA{fast} < EMA{mid} < EMA{slow}"
            fast_mid_points = (ema_mid - ema_fast) / point_value
            mid_slow_points = (ema_slow - ema_mid) / point_value
        else:
            return False
        if not aligned:
            self.logger.info(
                f"{strategy_name.upper()} {sym_ia} {tf} {direction} bloqueada por medias: "
                f"EMA{fast}={ema_fast:.5f} EMA{mid}={ema_mid:.5f} EMA{slow}={ema_slow:.5f} | regra {rule}"
            )
            return False
        if fast_mid_points < min_fast_mid or mid_slow_points < min_mid_slow:
            self.logger.info(
                f"{strategy_name.upper()} {sym_ia} {tf} {direction} bloqueada por distancia entre medias: "
                f"EMA{fast}-EMA{mid}={fast_mid_points:.1f}p min={min_fast_mid:.1f}p | "
                f"EMA{mid}-EMA{slow}={mid_slow_points:.1f}p min={min_mid_slow:.1f}p | "
                f"point_value={point_value:g}"
            )
            return False
        if bool(slope_cfg.get("enabled", False)):
            lookback = max(1, int(slope_cfg.get("lookback_bars", 5) or 5))
            if len(ema_slow_series) <= lookback:
                self.logger.info(f"{strategy_name.upper()} {sym_ia} {tf} {direction} bloqueada: dados insuficientes para inclinacao das EMAs")
                return False
            min_cfg = slope_cfg.get("min_slope_points", {}) or {}
            default_slope = min_cfg.get("default", {}) or {}
            timeframe_slope = (min_cfg.get("by_timeframe", {}) or {}).get(tf, {}) or {}
            min_fast_slope = float(timeframe_slope.get(f"ema{fast}", default_slope.get(f"ema{fast}", 0)) or 0)
            min_mid_slope = float(timeframe_slope.get(f"ema{mid}", default_slope.get(f"ema{mid}", 0)) or 0)
            min_slow_slope = float(timeframe_slope.get(f"ema{slow}", default_slope.get(f"ema{slow}", 0)) or 0)
            fast_slope_points = (ema_fast_series.iloc[-1] - ema_fast_series.iloc[-1 - lookback]) / point_value
            mid_slope_points = (ema_mid_series.iloc[-1] - ema_mid_series.iloc[-1 - lookback]) / point_value
            slow_slope_points = (ema_slow_series.iloc[-1] - ema_slow_series.iloc[-1 - lookback]) / point_value
            if pred == 2:
                fast_slope_points *= -1
                mid_slope_points *= -1
                slow_slope_points *= -1
            if (
                fast_slope_points < min_fast_slope
                or mid_slope_points < min_mid_slope
                or slow_slope_points < min_slow_slope
            ):
                self.logger.info(
                    f"{strategy_name.upper()} {sym_ia} {tf} {direction} bloqueada por inclinacao das EMAs: "
                    f"EMA{fast}={fast_slope_points:.1f}p min={min_fast_slope:.1f}p | "
                    f"EMA{mid}={mid_slope_points:.1f}p min={min_mid_slope:.1f}p | "
                    f"EMA{slow}={slow_slope_points:.1f}p min={min_slow_slope:.1f}p | "
                    f"lookback={lookback} candles"
                )
                return False
        if not self._ema_lower_timeframes_direction_ok(
            strategy_name=strategy_name,
            pred=pred,
            broker_sym=broker_sym,
            sym_ia=sym_ia,
            signal_tf=tf,
            direction=direction,
            periods=[fast, mid, slow],
            start_pos=start_pos,
        ):
            return False
        if bool(cfg.get("log_passed_filter", False)):
            candle_ref = "fechado" if start_pos == 1 else "atual"
            slope_text = ""
            if bool(slope_cfg.get("enabled", False)) and "fast_slope_points" in locals():
                slope_text = (
                    f" | slope EMA{fast}/{mid}/{slow}="
                    f"{fast_slope_points:.1f}p/{mid_slope_points:.1f}p/{slow_slope_points:.1f}p"
                )
            self.logger.info(
                f"{strategy_name.upper()} {sym_ia} {tf} {direction} filtro EMA OK ({candle_ref}): "
                f"EMA{fast}={ema_fast:.5f} EMA{mid}={ema_mid:.5f} EMA{slow}={ema_slow:.5f} | "
                f"dist {fast_mid_points:.1f}p/{mid_slow_points:.1f}p min {min_fast_mid:.1f}p/{min_mid_slow:.1f}p"
                f"{slope_text} | point_value={point_value:g}"
            )
        return True

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
        cfg = self._runtime_filter_config(
            "ema_lower_timeframes_direction",
            self.config.get("entry_filters.ema_alignment.lower_timeframe_direction", {}) or {},
            sym_ia,
            signal_tf,
        )
        if not bool(cfg.get("enabled", False)):
            return True
        mode = str(cfg.get("mode", "block") or "block").lower()
        if mode == "shadow":
            return True
        if mt5 is None:
            self.logger.info(f"{strategy_name.upper()} {sym_ia} bloqueada: MT5 indisponivel para filtro M5/M15")
            return False

        tf_codes = {
            "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1
        }
        required_tfs = [str(item).upper() for item in (cfg.get("timeframes", ["M5", "M15"]) or ["M5", "M15"])]
        lookback = max(1, int(cfg.get("lookback_bars", 5) or 5))
        require_all = bool(cfg.get("require_all_periods", True))
        bars = max(max(periods) + lookback + 5, 80)

        for lower_tf in required_tfs:
            tf_code = tf_codes.get(lower_tf)
            if not tf_code:
                self.logger.info(f"{strategy_name.upper()} {sym_ia} bloqueada: timeframe {lower_tf} indisponivel para filtro M5/M15")
                return False
            rates_df = self._get_rates_frame(broker_sym, lower_tf, bars, start_pos=start_pos, min_rows=max(periods) + lookback + 1)
            if rates_df.empty or len(rates_df) <= max(periods) + lookback:
                self.logger.info(f"{strategy_name.upper()} {sym_ia} {lower_tf} bloqueada: dados insuficientes para direcao M5/M15")
                return False

            df = rates_df.copy()
            close = df["close"].astype(float)
            slopes = {}
            passed = []
            for period in periods:
                ema = close.ewm(span=period, adjust=False).mean()
                slope = float(ema.iloc[-1] - ema.iloc[-1 - lookback])
                slopes[period] = slope
                passed.append(slope > 0 if pred == 1 else slope < 0)

            ok = all(passed) if require_all else any(passed)
            if not ok:
                slope_text = " ".join(f"EMA{period}={slopes[period]:.5f}" for period in periods)
                expected = "subindo" if pred == 1 else "descendo"
                self.logger.info(
                    f"{strategy_name.upper()} {sym_ia} {lower_tf} {direction} bloqueada por direcao M5/M15: "
                    f"esperado medias {expected} | {slope_text} | lookback={lookback}"
                )
                return False

        return True

    def _strategy_candle_price_confirmation_ok(self, strategy_name: str, pred: int, broker_sym: str, sym_ia: str, tf: str) -> bool:
        cfg = self._runtime_filter_config(
            "candle_price_confirmation",
            self.config.get("entry_filters.candle_price_confirmation", {}) or {},
            sym_ia,
            tf,
        )
        if not bool(cfg.get("enabled", True)):
            return True
        mode = str(cfg.get("mode", "block") or "block").lower()
        if mode == "shadow":
            return True
        if mt5 is None:
            self.logger.info(f"{strategy_name.upper()} {sym_ia} {tf} bloqueada: MT5 indisponivel para filtro de preco/candle")
            return False
        bars = max(3, int(cfg.get("bars", 3) or 3))
        df = self._get_rates_frame(broker_sym, tf, bars, start_pos=0, min_rows=2)
        tick = mt5.symbol_info_tick(broker_sym)
        if df.empty or len(df) < 2 or tick is None:
            self.logger.info(f"{strategy_name.upper()} {sym_ia} {tf} bloqueada: dados insuficientes para filtro de preco/candle")
            return False
        df = df.copy()
        current = df.iloc[-1]
        previous = df.iloc[-2]
        current_open = float(current["open"])
        previous_open = float(previous["open"])
        previous_close = float(previous["close"])

        previous_type = "doji"
        if previous_close > previous_open:
            previous_type = "alta"
        elif previous_close < previous_open:
            previous_type = "baixa"

        use_bid_ask = bool(cfg.get("use_bid_ask", True))
        if pred == 1:
            price = float(tick.ask if use_bid_ask else tick.last or tick.ask)
            direction = "BUY"
            checks = [
                (price > current_open, f"preco {price:.5f} > abertura atual {current_open:.5f}"),
                (previous_type == "alta", f"candle anterior precisa ser alta, atual={previous_type}"),
            ]
        elif pred == 2:
            price = float(tick.bid if use_bid_ask else tick.last or tick.bid)
            direction = "SELL"
            checks = [
                (price < current_open, f"preco {price:.5f} < abertura atual {current_open:.5f}"),
                (previous_type == "baixa", f"candle anterior precisa ser baixa, atual={previous_type}"),
            ]
        else:
            return False

        failed = [label for passed, label in checks if not passed]
        if failed:
            self.logger.info(
                f"{strategy_name.upper()} {sym_ia} {tf} {direction} bloqueada por preco/candle: "
                f"candle_anterior={previous_type} | " + " | ".join(failed)
            )
            return False

        if bool(cfg.get("log_passed_filter", False)):
            self.logger.info(
                f"{strategy_name.upper()} {sym_ia} {tf} {direction} filtro preco/candle OK: "
                f"preco={price:.5f} abertura_atual={current_open:.5f} "
                f"candle_anterior={previous_type} abertura_anterior={previous_open:.5f} fechamento_anterior={previous_close:.5f}"
            )
        return True

    def _strategy4_insidebar_buy_allowed(self, broker_sym: str, sym_ia: str, tf: str) -> bool:
        self._last_strategy4_setup_reason = ""
        self._last_strategy4_setup_details = {}
        tf_code = {
            "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1
        }.get(tf)
        if not tf_code:
            self._last_strategy4_setup_reason = "setup_block:timeframe_invalido"
            return False

        rates_df = self._get_rates_frame(broker_sym, tf, 2, start_pos=1, min_rows=2)
        if rates_df.empty or len(rates_df) < 2:
            self._last_strategy4_setup_reason = "setup_block:sem_rates"
            return False

        df = rates_df.copy()
        mother = df.iloc[-2]
        inside = df.iloc[-1]
        tick = mt5.symbol_info_tick(broker_sym)
        if not tick:
            self._last_strategy4_setup_reason = "setup_block:sem_tick"
            return False

        cfg = self._strategy_config("strategy4")
        log_key = (sym_ia, tf, mother["time"])
        if bool(cfg.get("log_setup_details", False)) and self.gold_penultimate_log.get((sym_ia, tf)) != log_key:
            self.gold_penultimate_log[(sym_ia, tf)] = log_key
            self.logger.info(
                f"S4 GOLD {tf} candle mae registrado | "
                f"time={mother['time']} max={float(mother['high']):.2f} min={float(mother['low']):.2f} | "
                f"inside_time={inside['time']} inside_max={float(inside['high']):.2f} inside_min={float(inside['low']):.2f}"
            )

        is_inside = float(inside["high"]) < float(mother["high"]) and float(inside["low"]) > float(mother["low"])
        price_above_mother_high = float(tick.ask) >= float(mother["high"])
        self._last_strategy4_setup_details = {
            "mother_time": str(mother["time"]),
            "mother_high": float(mother["high"]),
            "mother_low": float(mother["low"]),
            "inside_time": str(inside["time"]),
            "inside_high": float(inside["high"]),
            "inside_low": float(inside["low"]),
            "ask": float(tick.ask),
            "is_inside": bool(is_inside),
            "price_above_mother_high": bool(price_above_mother_high),
        }
        if not is_inside:
            self._last_strategy4_setup_reason = "setup_block:insidebar_false"
            self.logger.info(
                f"S4 GOLD {tf} setup_block: insidebar=false | "
                f"mae_max={float(mother['high']):.2f} mae_min={float(mother['low']):.2f} "
                f"ultimo_max={float(inside['high']):.2f} ultimo_min={float(inside['low']):.2f}"
            )
            return False
        if not price_above_mother_high:
            self._last_strategy4_setup_reason = "setup_block:aguardando_rompimento_mae"
            self.logger.info(
                f"S4 GOLD {tf} setup_block: aguardando rompimento da maxima da mae | "
                f"ask={float(tick.ask):.2f} max_mae={float(mother['high']):.2f}"
            )
            return False
        self._last_strategy4_setup_reason = "setup_ok"
        return True

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

    @staticmethod
    def _engine_state_should_block(cfg: dict, output: EngineOutput) -> bool:
        states = cfg.get("block_states", []) or []
        if not states:
            return bool(output.negative_factors)
        normalized = {str(item).strip().lower() for item in states if str(item).strip()}
        return str(output.state or "").strip().lower() in normalized

    def _runtime_filter_config(self, filter_name: str, base_cfg: dict, symbol: str | None = None, timeframe: str | None = None) -> dict:
        """Apply hot runtime overrides for entry filters without mutating YAML config."""
        cfg = dict(base_cfg or {})
        runtime_cfg = self.runtime_control.section("filters")
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
        cfg = self.config.get("decision_engine", {}) or {}
        if not bool(cfg.get("enabled", True)):
            return correlation_id
        side = self._prediction_side(pred)
        candidate = SignalCandidate(
            symbol=sym_ia.upper(),
            broker_symbol=broker_sym,
            timeframe=tf,
            side=side,
            strategy=strategy_name,
            raw_prediction=pred,
            p_buy=float(p_buy or 0.0),
            p_sell=float(p_sell or 0.0),
        )
        policy_result = self.decision_orchestrator.policy.combine(candidate, self._decision_engine_outputs)
        result = DecisionResult(
            decision=decision,
            reason=reason,
            consensus_score=policy_result.consensus_score,
            conflict_score=policy_result.conflict_score,
            tradeability_score=policy_result.tradeability_score,
            position_multiplier=policy_result.position_multiplier,
            positive_factors=policy_result.positive_factors,
            negative_factors=policy_result.negative_factors,
            warnings=policy_result.warnings,
        )
        explanation = build_xai_explanation(
            candidate,
            result,
            list(self._decision_engine_outputs),
            top_n=int(cfg.get("xai_top_factors", 8) or 8),
        ) if bool(cfg.get("xai_enabled", True)) else {}
        if not correlation_id:
            correlation_id = self._active_signal_correlation_id or f"{sym_ia.upper()}:{tf}:{strategy_name}:{datetime.now().isoformat()}"
        event = DecisionEvent(
            candidate=candidate,
            result=result,
            engines=list(self._decision_engine_outputs),
            portfolio=extra or {},
            explanation=explanation,
            correlation_id=correlation_id,
        )
        self.decision_layers_state[(sym_ia.upper(), tf.upper())] = MT5DecisionLayersExporter.rows_from_outputs(
            tf,
            list(self._decision_engine_outputs),
            decision=decision,
            reason=reason,
        )
        try:
            self.decision_orchestrator.audit_logger.write(event)
        except Exception as exc:
            self.logger.warning(f"Falha ao gravar decision audit: {exc}")
        if bool((self.config.get("event_bus", {}) or {}).get("log_engine_results", True)):
            candidate_payload = candidate.__dict__.copy()
            for output in self._decision_engine_outputs:
                self._publish_event(
                    FusionEventType.ENGINE_RESULT,
                    {
                        "candidate": candidate_payload,
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
                    },
                    source=str(output.engine or "Engine"),
                    correlation_id=correlation_id,
                )
        self._publish_event(
            FusionEventType.DECISION,
            event.to_dict(),
            correlation_id=correlation_id,
        )
        return correlation_id

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
        frame = self._get_rates_frame(broker_sym, tf, bars, start_pos=0, min_rows=60)
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

    def _volatility_engine_check(self, strategy_name: str, broker_sym: str, sym_ia: str, tf: str) -> bool:
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

    def _macro_flow_gate(self, strategy_name: str, pred: int, sym_ia: str, tf: str) -> bool:
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
        cfg = self.config.get("trading.manual_approval", {}) or {}
        runtime_cfg = self._runtime_section("manual_approval")
        runtime_enabled = self.runtime_control.get("trading.manual_approval_enabled")
        if runtime_enabled is None:
            runtime_enabled = runtime_cfg.get("enabled")
        return {
            "enabled": bool(cfg.get("enabled", True) if runtime_enabled is None else runtime_enabled),
            "request_file": str(
                runtime_cfg.get("request_file", cfg.get("request_file", "fusion_manual_order_request.csv"))
                or "fusion_manual_order_request.csv"
            ),
            "response_file": str(
                runtime_cfg.get("response_file", cfg.get("response_file", "fusion_manual_order_response.csv"))
                or "fusion_manual_order_response.csv"
            ),
            "timeout_seconds": float(runtime_cfg.get("timeout_seconds", cfg.get("timeout_seconds", 45)) or 45),
        }

    def _mt5_execution_control(self) -> dict:
        # Legado do bridge/CSV removido do fluxo ativo.
        # O runtime agora usa somente config YAML + fusion_runtime_control.json.
        return {}

    def _fusion_orders_allowed(self) -> tuple[bool, str]:
        runtime_allow = self.runtime_control.get("trading.allow_new_orders")
        if runtime_allow is not None:
            if not bool(runtime_allow):
                return False, "runtime_allow_new_orders_false"
            return True, "runtime_allow_new_orders"
        if not bool(self.config.get("trading.allow_new_orders", True)):
            return False, "allow_new_orders_false"
        return True, "yaml_allow_new_orders"

    def _normalize_execution_mode(self, value) -> str:
        mode = str(value or "").strip().lower()
        if mode in {"auto", "automatic", "automatico", "automÃ¡tico"}:
            return "automatic"
        if mode in {"manual", "confirm", "confirmation", "confirmacao", "confirmaÃ§Ã£o"}:
            return "manual"
        return ""

    def _execution_mode(self) -> str:
        mode = self._normalize_execution_mode(self.runtime_control.get("trading.execution_mode", ""))
        if mode:
            return mode
        mode = self._normalize_execution_mode(self.config.get("trading.execution_mode", ""))
        if mode:
            return mode
        return "automatic"

    def _manual_order_approval_required(self) -> bool:
        cfg = self._manual_order_approval_cfg()
        if bool(cfg.get("enabled", False)):
            return True
        return self._execution_mode() == "manual"
    def _read_manual_order_response(self, request_id: str) -> str:
        _request_path, response_path = self._manual_order_approval_paths()
        if not response_path.exists():
            return ""
        try:
            with response_path.open("r", newline="", encoding="utf-8") as handle:
                for row in csv.DictReader(handle):
                    if str(row.get("request_id", "")) == request_id:
                        return str(row.get("response", "") or "").upper()
        except Exception as exc:
            self.logger.warning(f"[MANUAL_APPROVAL] Falha ao ler resposta: {exc}")
        return ""

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
        if not self._manual_order_approval_required():
            return True

        cfg = self._manual_order_approval_cfg()
        timeout_seconds = max(1.0, float(cfg.get("timeout_seconds", 45) or 45))
        self._write_manual_order_request(
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
        self.logger.warning(
            f"[MANUAL_APPROVAL] Aguardando aprovacao no MT5: {sym_ia} {tf} {side} "
            f"timeout={timeout_seconds:.0f}s"
        )
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            response = self._read_manual_order_response(request_id)
            if response in {"APPROVED", "YES", "SIM"}:
                self.logger.info(f"[MANUAL_APPROVAL] Aprovado no MT5: {sym_ia} {tf} {side}")
                return True
            if response in {"REJECTED", "NO", "NAO", "NÃƒO", "CANCELLED", "CANCELED"}:
                self.logger.info(f"[MANUAL_APPROVAL] Rejeitado no MT5: {sym_ia} {tf} {side}")
                self._last_execution_block_reason = "manual_approval_rejected"
                return False
            time.sleep(0.5)

        self._last_execution_block_reason = "manual_approval_timeout"
        self.logger.warning(f"[MANUAL_APPROVAL] Timeout sem resposta: {sym_ia} {tf} {side}")
        return False

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
        frame = self._get_rates_frame(broker_sym, tf_name, bars, start_pos=0, min_rows=80)
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
            df = self._get_rates_frame(broker_symbol, tf, 90, start_pos=0, min_rows=55)
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
            self.logger.info(
                f"{strategy_name.upper()} {sym_ia} {tf} ai_advisor {mode}: "
                f"state={output.state} conf={output.confidence:.2f} "
                f"factors={','.join((output.negative_factors or output.positive_factors or output.warnings)[:2])}"
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
            factors = output.negative_factors or output.warnings or output.positive_factors or [output.state]
            self.logger.info(
                f"{strategy_name.upper()} {sym_ia} {tf} context_brain {mode}: "
                f"label={label} state={output.state} score={output.score:.2f} "
                f"conf={output.confidence:.2f} factors={','.join(factors[:3])}"
            )
        if mode == "shadow":
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
        reason_code = str(cfg.get("reason_code", "opportunity_engine") or "opportunity_engine")
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
            factors = output.negative_factors or output.warnings or ["briefing"]
            self._last_market_briefing_reason = f"MB:shadow:{output.state}:{factors[0]}"
        if bool(cfg.get("log_each_check", True)) and output.state != "ok":
            factors = output.negative_factors or output.warnings or ["ok"]
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
            reason_code = str(cfg.get("reason_code", "entry_timing") or "entry_timing")
            factor = "comprar_topo_sem_rompimento_validado" if buy_at_top else "vender_fundo_sem_rompimento_validado"
            self._last_execution_block_reason = f"{reason_code}:{factor}"
            self.logger.info(
                f"{strategy_name.upper()} {sym_ia} {tf} bloqueada por extremo sem rompimento validado: "
                f"{factor} state={output.state}"
            )
            return mode == "shadow"
        if bool(cfg.get("log_each_check", True)) and output.state not in {"ok", "validated_breakout_buy", "validated_breakout_sell"}:
            factors = output.negative_factors or output.warnings or [output.state]
            self.logger.info(
                f"{strategy_name.upper()} {sym_ia} {tf} entry_timing {mode}: "
                f"state={output.state} score={output.score:.2f} factors={','.join(factors[:2])}"
            )
        if mode == "shadow" or not output.negative_factors:
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
            factors = output.negative_factors or output.warnings or [output.state]
            self.logger.info(
                f"{strategy_name.upper()} {sym_ia} {tf} execution_engine {mode}: "
                f"state={output.state} score={output.score:.2f} factors={','.join(factors[:2])}"
            )
        if mode == "shadow" or not output.negative_factors:
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
        self._decision_engine_outputs.append(output)
        if bool(cfg.get("log_each_check", True)) and output.state != "normal_risk":
            factors = output.negative_factors or output.warnings or [output.state]
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
        cfg = self._strategy_config(strategy_name)
        exposure_cfg = cfg.get("exposure_groups", {}) or {}
        if not bool(cfg.get("use_exposure_groups", False)) or not exposure_cfg:
            return True

        candidate_symbol = sym_ia.upper()
        candidate_direction = 1 if pred == 1 else -1
        strategy_magics = set(self._strategy_magic_group(strategy_name))
        positions = mt5.positions_get()
        positions = list(positions) if positions else []

        for group_name, group in exposure_cfg.items():
            symbols_cfg = group.get("symbols", {}) or {}
            if candidate_symbol not in symbols_cfg:
                continue

            max_units = float(group.get("max_units", 2.0))
            offset_credit = float(group.get("opposite_direction_credit", 0.5))
            current_units = 0.0
            opposite_units = 0.0

            for pos in positions:
                if int(pos.magic) not in strategy_magics:
                    continue
                pos_symbol = self._broker_symbol_to_base(pos.symbol)
                if pos_symbol not in symbols_cfg:
                    continue
                pos_weight = float(symbols_cfg[pos_symbol].get("weight", 1.0))
                pos_bias = int(symbols_cfg[pos_symbol].get("bias", 1))
                pos_direction = 1 if pos.type == mt5.ORDER_TYPE_BUY else -1
                exposure_direction = pos_direction * pos_bias
                candidate_exposure_direction = candidate_direction * int(symbols_cfg[candidate_symbol].get("bias", 1))
                if exposure_direction == candidate_exposure_direction:
                    current_units += pos_weight
                else:
                    opposite_units += pos_weight

            candidate_weight = float(symbols_cfg[candidate_symbol].get("weight", 1.0))
            projected_units = current_units + candidate_weight - (opposite_units * offset_credit)
            if projected_units > max_units:
                self.logger.info(
                    f"{strategy_name.upper()} bloqueada por grupo {group_name}: "
                    f"{candidate_symbol} projetado={projected_units:.2f} limite={max_units:.2f}"
                )
                return False

        return True

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
        frame = self._get_rates_frame(broker_sym, tf, bars, start_pos=0, min_rows=50)
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

    def _market_structure_gate(self, strategy_name: str, pred: int, broker_sym: str, sym_ia: str, tf: str) -> bool:
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
        if not self._meta_model_ensemble_check(
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
        ):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "meta_model_ensemble"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._market_briefing_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "market_briefing"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._market_regime_check(strategy_name, pred, broker_sym, sym_ia, tf):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "regime_bloqueado"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._volatility_engine_check(strategy_name, broker_sym, sym_ia, tf):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "volatility_engine"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._session_context_check(strategy_name, pred, sym_ia, tf):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "session_context"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._macro_flow_gate(strategy_name, pred, sym_ia, tf):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "macro_fluxo_contra"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._market_alignment_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "market_alignment"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._timeframe_consensus_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "timeframe_consensus"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._portfolio_exposure_check(strategy_name, pred, sym_ia):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "portfolio_exposure"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._portfolio_correlation_allowed(strategy_name, sym_ia, pred):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "correlacao_prejuizo"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._market_structure_gate(strategy_name, pred, broker_sym, sym_ia, tf):
            self._last_execution_block_reason = "market_structure_block"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._feature_engineering_check(strategy_name, broker_sym, sym_ia, tf):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "feature_engineering"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._entry_timing_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "entry_timing"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._execution_engine_check(strategy_name, pred, broker_sym, sym_ia, tf):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "execution_engine"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._risk_engine_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "risk_engine"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._strategy_candle_price_confirmation_ok(strategy_name, pred, broker_sym, sym_ia, tf):
            self._last_execution_block_reason = "preco_candle_nao_confirmado"
            self._record_engine_output(
                engine="candle_price",
                direction="SELL" if pred == 1 else "BUY",
                score=1.0,
                confidence=0.80,
                state="blocked",
                negative_factors=["preco_candle_nao_confirmado"],
            )
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
        if not self._strategy_ema_alignment_ok(strategy_name, pred, broker_sym, sym_ia, tf):
            self._last_execution_block_reason = "ema_nao_alinhada"
            self._record_engine_output(
                engine="ema_alignment",
                direction="SELL" if pred == 1 else "BUY",
                score=1.0,
                confidence=0.85,
                state="blocked",
                negative_factors=["ema_nao_alinhada"],
            )
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

        if not self._context_engine_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "context_engine"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._confidence_calibration_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "confidence_calibration"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._consensus_engine_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "consensus_engine"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._opportunity_engine_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell):
            if not self._last_execution_block_reason:
                self._last_execution_block_reason = "opportunity_engine"
            self._audit_block_with_shadow(strategy_name, pred, broker_sym, sym_ia, tf, self._last_execution_block_reason, p_buy, p_sell)
            return None
        if not self._context_brain_check(strategy_name, pred, broker_sym, sym_ia, tf, p_buy, p_sell):
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
                metadata={"tp_points": tp_points, "sl_points": sl_points, "p_buy": p_buy, "p_sell": p_sell},
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
                metadata={"tp_points": tp_points, "sl_points": sl_points, "p_buy": p_buy, "p_sell": p_sell},
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
            self.actionable_signal_state[(sym_ia.upper(), tf.upper())] = {
                "signal": pred,
                "p_buy": p_buy,
                "p_sell": p_sell,
                "strategy": strategy_name,
                "reason": result_message or "pre_order_checks_ok",
                "timestamp": datetime.now().isoformat(),
            }
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
                        X = self._calculate_features(broker_sym, tf)
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
                X = self._calculate_features(broker_sym, tf)
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

        while True:
            loop_started = time.perf_counter()
            now = datetime.now()
            now_time = time.time()
            min_cycle_seconds = max(1, int(self.runtime_control.get("loop.min_cycle_seconds", 60) or 60))
            
            # Limpar cache expirado periodicamente
            if now_time - last_cache_cleanup > CACHE_CLEANUP_INTERVAL:
                cleanup_started = time.perf_counter()
                expired_keys = []
                for key, (_, timestamp) in self.features_cache.items():
                    if now_time - timestamp > self.features_cache_ttl + 10:
                        expired_keys.append(key)
                
                for key in expired_keys:
                    del self.features_cache[key]
                
                if expired_keys:
                    self.logger.info(
                        f"[CACHE] Limpeza: removidos {len(expired_keys)} itens "
                        f"(hits={self.features_cache_hits} misses={self.features_cache_misses})"
                    )

                expired_rate_keys = []
                for key, (_, timestamp, _) in self.rates_cache.items():
                    if now_time - timestamp > self.rates_cache_ttl + 10:
                        expired_rate_keys.append(key)
                for key in expired_rate_keys:
                    del self.rates_cache[key]
                if expired_rate_keys:
                    self.logger.info(
                        f"[CACHE][RATES] Limpeza: removidos {len(expired_rate_keys)} itens "
                        f"(hits={self.rates_cache_hits} misses={self.rates_cache_misses})"
                    )
                 
                # Reset stats a cada limpeza
                self.features_cache_hits = 0
                self.features_cache_misses = 0
                self.rates_cache_hits = 0
                self.rates_cache_misses = 0
                last_cache_cleanup = now_time
                self._log_timing(
                    "loop.cache_cleanup",
                    cleanup_started,
                    extra=(
                        f"removidos_features={len(expired_keys)} removidos_rates={len(expired_rate_keys)} "
                        f"hits_features={self.features_cache_hits} misses_features={self.features_cache_misses} "
                        f"hits_rates={self.rates_cache_hits} misses_rates={self.rates_cache_misses}"
                    )
                )

            # Inicializa fila apenas quando o ciclo anterior terminou e o tempo minimo foi respeitado
            cycle_ready = False
            if not self.processing_queue_initialized:
                if self.processing_cycle_started_at <= 0.0:
                    cycle_ready = True
                elif self.processing_cycle_completed_at > 0.0 and (now_time - self.processing_cycle_completed_at) >= min_cycle_seconds:
                    cycle_ready = True

            if cycle_ready:
                cycle_started = time.perf_counter()
                self.processing_cycle_started_at = now_time
                self.processing_cycle_completed_at = 0.0
                self.logger.info(
                    f"[LOOP] Novo ciclo: {now.strftime('%H:%M:%S')} - Inicializando fila de processamento "
                    f"(min_cycle={min_cycle_seconds}s)..."
                )
                reload_started = time.perf_counter()
                self.config.reload()
                self._log_timing("loop.config_reload", reload_started)
                self._refresh_oms_state()
                self.actionable_signal_state = {}
                self.final_signal_state = {}
                self.cycle_order_symbols = set()

                # Inicializa fila com todos (symbol, broker_sym, tf) combinations
                self.processing_queue = []
                for broker_sym, sym_ia in self.sync_dict.items():
                    runtime_symbol_ok, runtime_symbol_reason = self._runtime_symbol_allowed(sym_ia)
                    if not runtime_symbol_ok:
                        for tf in self.TIMEFRAMES:
                            self.monitor_state[(sym_ia, tf)] = {
                                "signal": 0,
                                "p_buy": 0.0,
                                "p_sell": 0.0,
                                "status": "RUNTIME_BLOCK",
                                "reason": runtime_symbol_reason,
                            }
                    else:
                        for tf in self.TIMEFRAMES:
                            self.processing_queue.append((broker_sym, sym_ia, tf))

                self.processing_queue_initialized = True
                self._log_timing(
                    "loop.queue_init",
                    cycle_started,
                    extra=f"ativos={len(self.sync_dict)} tf_por_ativo={len(self.TIMEFRAMES)} itens_fila={len(self.processing_queue)}"
                )

            if self.processing_queue_initialized and self.processing_queue:
                batch_size = max(8, min(32, len(self.processing_queue) // 6 or 8))
                batch_start = time.perf_counter()
                processed = 0
                while self.processing_queue and processed < batch_size:
                    broker_sym, sym_ia, tf = self.processing_queue.pop(0)
                    self._process_symbol_timeframe(broker_sym, sym_ia, tf, now, self.cycle_order_symbols, last_trade_time)
                    processed += 1
                    if processed >= 8 and (time.perf_counter() - batch_start) > 0.35:
                        break
                self._log_timing(
                    "loop.batch_process",
                    batch_start,
                    extra=f"processados={processed} restantes={len(self.processing_queue)} batch_size={batch_size}"
                )

            # Quando fila esvazia, finaliza o ciclo
            if self.processing_queue_initialized and not self.processing_queue:
                finalize_started = time.perf_counter()
                self._annotate_currency_strength_directional_signals()
                self._annotate_currency_strength_neutrals()
                self._build_final_signal_state()
                self._print_dashboard_premium()
                self._write_currency_strength_map()
                self.mt5_signal_panel.export(
                    self.monitor_state,
                    symbols=[str(sym_ia).upper() for sym_ia in self.sync_dict.values()],
                    timeframes=self.TIMEFRAMES,
                    actionable_state=self.actionable_signal_state,
                    final_state=self.final_signal_state,
                )
                self.mt5_trade_zones.export(
                    self.monitor_state,
                    symbol_map={str(broker): str(symbol).upper() for broker, symbol in self.sync_dict.items()},
                    timeframes=self.TIMEFRAMES,
                    mt5_module=mt5,
                )
                self.mt5_decision_layers.export(
                    self.decision_layers_state,
                    symbols=[str(sym_ia).upper() for sym_ia in self.sync_dict.values()],
                )
                self.processing_queue_initialized = False
                self.processing_cycle_completed_at = now_time
                self.cycle_order_symbols = set()
                self._log_timing("loop.finalizacao_ciclo", finalize_started, extra=f"ativos={len(self.sync_dict)}")

            if not self.processing_queue and now_time - last_idle_log >= 5.0:
                last_idle_log = now_time
                self._log_timing("loop.idle", loop_started, extra=f"fila={len(self.processing_queue)}")
            time.sleep(0.2)

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
                            X = self._calculate_features(broker_sym, tf)
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
                        
                        X = self._calculate_features(broker_sym, tf)
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
                display = "GOLD" if sym == "XAUUSD" else sym
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
            self._run_signals()
            
            
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


