"""
FUSION_V2 - Módulo de Configuração Central
===========================================
Sistema de configuração inspirado no NEXUS com YAML + override runtime
"""

import os
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    yaml = None
    YAML_AVAILABLE = False


BASE_DIR = Path(__file__).resolve().parent.parent.parent


@dataclass
class BrokerConfig:
    terminal_path: str = r"C:\Program Files\MetaTrader 5\terminal64.exe"
    login: int = 0
    password: str = ""
    server: str = ""
    startup_timeout: int = 30


@dataclass
class RiskConfig:
    max_risk_per_trade: float = 1.0
    max_daily_loss: float = 5.0
    max_positions: int = 5
    lot_step: float = 0.01
    min_lot: float = 0.01
    max_lot: float = 100.0


@dataclass
class SignalConfig:
    buy_threshold: float = 0.55
    sell_threshold: float = 0.55
    confidence_filter: float = 0.5
    min_signal_strength: float = 0.3
    invert_signals: bool = False
    inverted_signal_groups: list = field(default_factory=list)


@dataclass
class TrailingConfig:
    enabled: bool = True
    activation_pips: int = 10
    distance_pips: int = 5
    check_interval: int = 1


@dataclass
class DataConfig:
    data_dir: Path = field(default_factory=lambda: BASE_DIR / "data")
    parquet_dir: Path = field(default_factory=lambda: BASE_DIR / "data" / "parquet")
    timeframe_default: str = "M5"
    symbol_mapping: dict = field(default_factory=lambda: {
        "GOLD": "GOLD",
        "SILVER": "XAGUSD",
    })


@dataclass
class ModelConfig:
    model_dir: Path = field(default_factory=lambda: BASE_DIR / "models")
    global_model: str = "genesis_global_model.pkl"
    scaler: str = "genesis_scaler.pkl"
    meta: str = "genesis_model_meta.pkl"
    feature_columns: list = field(default_factory=lambda: [
        "rsi_m5", "rsi_m15", "rsi_m30", "rsi_h1", "rsi_h4", "rsi_d1",
        "dist_ema_m5", "dist_ema_m15", "dist_ema_m30", "dist_ema_h1",
        "alpha_vam_m5", "alpha_vam_h1", "alpha_vam_d1",
        "trend_alignment"
    ])


class FusionConfig:
    """Configuração central do FUSION_V2 com suporte a YAML e overrides."""
    
    _instance: Optional['FusionConfig'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self.broker = BrokerConfig()
        self.risk = RiskConfig()
        self.signal = SignalConfig()
        self.trailing = TrailingConfig()
        self.data = DataConfig()
        self.model = ModelConfig()
        
        self._yaml_config: dict = {}
        self._yaml_path = BASE_DIR / "config" / "fusion_config.yaml"
        self._yaml_mtime: float = 0.0
        self._load_yaml()
    
    def _load_yaml(self):
        config_path = self._yaml_path
        if config_path.exists() and YAML_AVAILABLE:
            with open(config_path, 'r', encoding='utf-8') as f:
                self._yaml_config = yaml.safe_load(f) or {}
            try:
                self._yaml_mtime = config_path.stat().st_mtime
            except OSError:
                self._yaml_mtime = 0.0
            self._apply_yaml_config()
    
    def _apply_yaml_config(self):
        """Aplica configurações do YAML aos dataclasses."""
        if 'broker' in self._yaml_config:
            for key, value in self._yaml_config['broker'].items():
                if hasattr(self.broker, key):
                    setattr(self.broker, key, value)
        
        if 'risk' in self._yaml_config:
            for key, value in self._yaml_config['risk'].items():
                if hasattr(self.risk, key):
                    setattr(self.risk, key, value)
        
        if 'signal' in self._yaml_config:
            for key, value in self._yaml_config['signal'].items():
                if hasattr(self.signal, key):
                    setattr(self.signal, key, value)
        
        if 'trailing' in self._yaml_config:
            for key, value in self._yaml_config['trailing'].items():
                if hasattr(self.trailing, key):
                    setattr(self.trailing, key, value)
        
        if 'data' in self._yaml_config:
            for key, value in self._yaml_config['data'].items():
                if hasattr(self.data, key):
                    setattr(self.data, key, value)
        
        if 'model' in self._yaml_config:
            for key, value in self._yaml_config['model'].items():
                if hasattr(self.model, key):
                    setattr(self.model, key, value)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Obtém configuração por caminho pontuado (ex: 'broker.login')."""
        keys = key.split('.')
        value = self._yaml_config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default
    
    def set(self, key: str, value: Any):
        """Define configuração por caminho pontuado."""
        keys = key.split('.')
        target = self._yaml_config
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
    
    def reload(self, force: bool = False):
        """Recarrega configuração do YAML quando o arquivo mudou."""
        config_path = self._yaml_path
        if not force and config_path.exists():
            try:
                mtime = config_path.stat().st_mtime
            except OSError:
                mtime = 0.0
            if mtime and mtime == self._yaml_mtime:
                return
        self._yaml_config = {}
        self._load_yaml()
    
    def to_dict(self) -> dict:
        """Retorna toda a configuração como dicionário."""
        return {
            'broker': self.broker.__dict__,
            'risk': self.risk.__dict__,
            'signal': self.signal.__dict__,
            'trailing': self.trailing.__dict__,
            'data': {k: str(v) if isinstance(v, Path) else v for k, v in self.data.__dict__.items()},
            'model': {k: str(v) if isinstance(v, Path) else v for k, v in self.model.__dict__.items()},
        }


_config = FusionConfig()


def get_config() -> FusionConfig:
    return _config


def reload_config():
    global _config
    _config = FusionConfig()
    return _config
