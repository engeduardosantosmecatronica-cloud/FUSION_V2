#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CONFIGURAÇÕES CENTRALIZADAS DO PROJETO OMNIS
Gerencia todos os parâmetros de configuração
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv
from datetime import datetime

# Carrega variáveis de ambiente
load_dotenv()

# ============================================
# CAMINHOS DO PROJETO
# ============================================

# Diretório raiz (2 níveis acima deste arquivo)
BASE_DIR = Path(__file__).parent
PROJECT_ROOT = BASE_DIR.parent

# Diretórios principais
MODEL_DIR = PROJECT_ROOT / "models"
LOG_DIR = PROJECT_ROOT / "logs"
RESULTADOS_DIR = PROJECT_ROOT / "resultados"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
CONFIG_DIR = PROJECT_ROOT / "config"

# Diretório de dados históricos
HISTORICO_DIR = BASE_DIR / "HISTORICO_FOREX"

# Criar diretórios se não existirem
for dir_path in [MODEL_DIR, LOG_DIR, RESULTADOS_DIR, OUTPUT_DIR, CONFIG_DIR, HISTORICO_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# ============================================
# CONFIGURAÇÕES DE ATIVOS
# ============================================

# Símbolos disponíveis (principais)
SIMBOLOS_PRINCIPAIS: List[str] = [
    "EURUSD",
    "GBPUSD",
    "AUDUSD",
    "USDJPY",
    "USDCAD",
    "USDCHF",
    "NZDUSD",
]

# Símbolos secundários (opcionais)
SIMBOLOS_SECUNDARIOS: List[str] = [
    "EURGBP",
    "EURJPY",
    "GBPJPY",
    "AUDJPY",
    "XAUUSD",  # Ouro
    "BTCUSD",  # Bitcoin
    "ETHUSD",  # Ethereum
]

# Todos os símbolos
SIMBOLOS: List[str] = SIMBOLOS_PRINCIPAIS + SIMBOLOS_SECUNDARIOS

# ============================================
# CONFIGURAÇÕES DE TIMEFRAMES
# ============================================

# Timeframes disponíveis (string -> descrição)
TIMEFRAMES: Dict[str, str] = {
    "M1": "1 minuto",
    "M5": "5 minutos",
    "M15": "15 minutos",
    "M30": "30 minutos",
    "H1": "1 hora",
    "H2": "2 horas",
    "H3": "3 horas",
    "H4": "4 horas",
    "H6": "6 horas",
    "H8": "8 horas",
    "H12": "12 horas",
    "D1": "1 dia",
    "W1": "1 semana",
    "MN1": "1 mês",
}

# Timeframes para treinamento (os mais usados)
TIMEFRAMES_TREINO: List[str] = ["M5", "M15", "M30", "H1", "H4"]

# Mapeamento para MT5 (será preenchido em runtime)
MT5_TIMEFRAMES: Dict[str, int] = {
    "M1": 1,      # TIMEFRAME_M1
    "M5": 5,      # TIMEFRAME_M5
    "M15": 15,    # TIMEFRAME_M15
    "M30": 30,    # TIMEFRAME_M30
    "H1": 60,     # TIMEFRAME_H1
    "H2": 120,    # TIMEFRAME_H2
    "H3": 180,    # TIMEFRAME_H3
    "H4": 240,    # TIMEFRAME_H4
    "H6": 360,    # TIMEFRAME_H6
    "H8": 480,    # TIMEFRAME_H8
    "H12": 720,   # TIMEFRAME_H12
    "D1": 1440,   # TIMEFRAME_D1
    "W1": 10080,  # TIMEFRAME_W1
    "MN1": 43200, # TIMEFRAME_MN1
}

# ============================================
# CONFIGURAÇÕES DE HORIZONTES (NOVO!)
# ============================================

# Horizontes de previsão por timeframe (N candles à frente)
HORIZONTES: Dict[str, List[int]] = {
    "M5":  [3, 5, 10, 20],     # 15min, 25min, 50min, 100min
    "M15": [3, 5, 10],          # 45min, 75min, 150min
    "M30": [3, 5, 10, 20],      # 90min, 150min, 300min, 600min
    "H1":  [3, 5, 10],          # 3h, 5h, 10h
    "H4":  [3, 5, 10],          # 12h, 20h, 40h
}

# ============================================
# CONFIGURAÇÕES DE OBJETIVOS
# ============================================

# Objetivos de treinamento
OBJETIVOS: List[str] = [
    "tendencia",
    "candles",
    "volatilidade",
    "risco",
    "reversao",
]

# Descrição dos objetivos
OBJETIVOS_DESC: Dict[str, str] = {
    "tendencia": "Previsão de direção do preço (sobe/desce)",
    "candles": "Classificação de padrões de candle (doji, martelo, engulfing)",
    "volatilidade": "Previsão de níveis de volatilidade (alta/baixa)",
    "risco": "Avaliação de risco do ativo (drawdown)",
    "reversao": "Previsão de reversão de tendência",
}

# ============================================
# CONFIGURAÇÕES DE MODELOS
# ============================================

# Modelos ativos (que vamos usar)
MODELOS_ATIVOS: List[str] = ["lightgbm", "xgboost", "random_forest"]

# Modelos completos (todos disponíveis)
MODELOS_COMPLETOS: List[str] = [
    "lightgbm",
    "xgboost",
    "random_forest",
    "catboost",
    "sklearn",
]

# Pesos para ensemble (baseado em performance)
PESOS_ENSEMBLE: Dict[str, float] = {
    "lightgbm": 0.5,
    "xgboost": 0.3,
    "random_forest": 0.2,
}

# Extensões de arquivo por modelo
MODELO_EXTENSOES: Dict[str, str] = {
    "lightgbm": ".pkl",
    "xgboost": ".pkl",
    "random_forest": ".pkl",
    "catboost": ".cbm",
    "sklearn": ".pkl",
}

# ============================================
# CONFIGURAÇÕES DE FEATURES
# ============================================

# Features base (comuns a todos os objetivos)
FEATURES_BASE: List[str] = [
    # Retornos
    'ret_1', 'ret_5', 'ret_10', 'ret_20',
    # Médias Simples
    'sma_10', 'sma_20', 'sma_50',
    # EMAs
    'ema_9', 'ema_12', 'ema_21', 'ema_26', 'ema_50',
    # Distância das médias
    'dist_sma20', 'dist_sma50',
    # RSI
    'rsi',
    # MACD
    'macd', 'macd_signal', 'macd_hist',
    # Volatilidade
    'vol_10', 'vol_20', 'vol_50',
    # ATR
    'atr',
    # Temporais
    'hora', 'dia_semana', 'dia_mes',
    # Alinhamento EMA
    'alinhamento_alta', 'alinhamento_baixa',
    # Crossovers
    'crossover_9_21_alta', 'crossover_9_21_baixa',
    'crossover_21_50_alta', 'crossover_21_50_baixa',
]

# Features específicas por objetivo
FEATURES_POR_OBJETIVO: Dict[str, List[str]] = {
    "tendencia": FEATURES_BASE,  # Usa todas
    "candles": [
        'ret_1', 'ret_5',
        'body', 'body_pct', 'upper_shadow', 'lower_shadow',
        'body_range_ratio', 'close_position',
        'vol_10', 'hora',
    ],
    "volatilidade": [
        'ret_1', 'ret_5', 'ret_10',
        'vol_5', 'vol_10', 'vol_20', 'vol_50',
        'atr', 'atr_pct',
        'hora', 'dia_semana',
    ],
    "risco": [
        'ret_1', 'ret_5', 'ret_10',
        'vol_20', 'vol_50', 'atr',
        'max_20', 'drawdown_20',
        'hora', 'dia_semana',
    ],
    "reversao": [
        'ret_1', 'ret_5', 'ret_10',
        'rsi', 'macd_hist',
        'dist_sma20', 'dist_sma50',
        'vol_10', 'vol_20',
        'hora',
    ],
}

# ============================================
# CONFIGURAÇÕES DE TREINAMENTO
# ============================================

# Parâmetros padrão de treinamento
TRAIN_CONFIG = {
    "test_size": 0.2,
    "val_size": 0.1,
    "random_state": 42,
    "threshold_mult": 1.2,  # Multiplicador da volatilidade para target
    "min_samples": 500,      # Mínimo de amostras para treinar
    "use_early_stopping": True,
    "early_stopping_rounds": 20,
    "n_jobs": -1,            # Usar todos os cores
}

# ============================================
# CONFIGURAÇÕES DE OTIMIZAÇÃO
# ============================================

# Grid de hiperparâmetros para LightGBM
LGB_PARAMS_GRID = {
    'num_leaves': [31, 41, 51],
    'learning_rate': [0.01, 0.05, 0.1],
    'feature_fraction': [0.7, 0.8, 0.9],
    'bagging_fraction': [0.7, 0.8, 0.9],
    'min_child_samples': [20, 30, 40],
}

# Grid para XGBoost
XGB_PARAMS_GRID = {
    'max_depth': [4, 6, 8],
    'learning_rate': [0.01, 0.05, 0.1],
    'subsample': [0.7, 0.8, 0.9],
    'colsample_bytree': [0.7, 0.8, 0.9],
    'min_child_weight': [1, 3, 5],
}

# Grid para Random Forest
RF_PARAMS_GRID = {
    'n_estimators': [100, 200, 300],
    'max_depth': [10, 15, 20],
    'min_samples_split': [5, 10, 15],
    'min_samples_leaf': [2, 4, 6],
}

# ============================================
# CONFIGURAÇÕES DE RISCO
# ============================================

RISK_CONFIG = {
    "max_risk_per_trade": 0.02,      # 2% do capital por trade
    "max_daily_risk": 0.05,           # 5% de perda máxima diária
    "max_open_positions": 3,           # Máximo de posições simultâneas
    "stop_loss_atr_mult": 2.0,         # Stop loss = 2x ATR
    "take_profit_atr_mult": 3.0,       # Take profit = 3x ATR
    "min_confidence": 0.52,             # Confiança mínima para entrar
}

# ============================================
# CONFIGURAÇÕES DE THRESHOLDS
# ============================================

THRESHOLDS = {
    "compra_forte": 0.55,
    "compra_moderada": 0.52,
    "neutro_superior": 0.52,
    "neutro_inferior": 0.48,
    "venda_moderada": 0.48,
    "venda_forte": 0.45,
}

# ============================================
# CONFIGURAÇÕES DE LOGGING
# ============================================

LOG_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "datefmt": "%Y-%m-%d %H:%M:%S",
}

# ============================================
# CONFIGURAÇÕES DE MT5
# ============================================

MT5_CONFIG = {
    "login": int(os.getenv("MT5_LOGIN", 0)),
    "password": os.getenv("MT5_PASSWORD", ""),
    "server": os.getenv("MT5_SERVER", ""),
    "path": os.getenv("MT5_PATH", ""),
    "timeout": 60000,
}

# ============================================
# FUNÇÕES UTILITÁRIAS
# ============================================

def get_mt5_timeframe(timeframe: str) -> int:
    """Retorna código MT5 para o timeframe"""
    return MT5_TIMEFRAMES.get(timeframe, 60)  # default H1

def get_horizontes(timeframe: str) -> List[int]:
    """Retorna horizontes para o timeframe"""
    return HORIZONTES.get(timeframe, [5])  # default 5 candles

def get_threshold(confianca: float) -> str:
    """Classifica o nível de confiança"""
    if confianca > THRESHOLDS["compra_forte"]:
        return "COMPRA_FORTE"
    elif confianca > THRESHOLDS["compra_moderada"]:
        return "COMPRA_MODERADA"
    elif confianca < THRESHOLDS["venda_forte"]:
        return "VENDA_FORTE"
    elif confianca < THRESHOLDS["venda_moderada"]:
        return "VENDA_MODERADA"
    else:
        return "NEUTRO"


# ============================================
# DATACLASS DE CONFIGURAÇÃO (opcional)
# ============================================

@dataclass
class Config:
    """Classe de configuração completa"""
    
    # Ativos
    simbolos: List[str] = field(default_factory=lambda: SIMBOLOS)
    simbolos_principais: List[str] = field(default_factory=lambda: SIMBOLOS_PRINCIPAIS)
    
    # Timeframes
    timeframes: List[str] = field(default_factory=lambda: TIMEFRAMES_TREINO)
    horizontes: Dict[str, List[int]] = field(default_factory=lambda: HORIZONTES)
    
    # Modelos
    modelos_ativos: List[str] = field(default_factory=lambda: MODELOS_ATIVOS)
    pesos_ensemble: Dict[str, float] = field(default_factory=lambda: PESOS_ENSEMBLE)
    
    # Features
    features_base: List[str] = field(default_factory=lambda: FEATURES_BASE)
    
    # Diretórios
    model_dir: Path = MODEL_DIR
    log_dir: Path = LOG_DIR
    resultados_dir: Path = RESULTADOS_DIR
    historico_dir: Path = HISTORICO_DIR
    
    # Configurações
    train_config: Dict[str, Any] = field(default_factory=lambda: TRAIN_CONFIG)
    risk_config: Dict[str, Any] = field(default_factory=lambda: RISK_CONFIG)
    thresholds: Dict[str, float] = field(default_factory=lambda: THRESHOLDS)


# Instância global (para importar em outros arquivos)
config = Config()

# ============================================
# EXPORTAÇÕES
# ============================================

__all__ = [
    # Caminhos
    'BASE_DIR', 'PROJECT_ROOT', 'MODEL_DIR', 'LOG_DIR',
    'RESULTADOS_DIR', 'OUTPUT_DIR', 'CONFIG_DIR', 'HISTORICO_DIR',
    
    # Ativos
    'SIMBOLOS', 'SIMBOLOS_PRINCIPAIS', 'SIMBOLOS_SECUNDARIOS',
    
    # Timeframes
    'TIMEFRAMES', 'TIMEFRAMES_TREINO', 'MT5_TIMEFRAMES',
    'HORIZONTES',
    
    # Objetivos
    'OBJETIVOS', 'OBJETIVOS_DESC',
    
    # Modelos
    'MODELOS_ATIVOS', 'MODELOS_COMPLETOS', 'PESOS_ENSEMBLE',
    'MODELO_EXTENSOES',
    
    # Features
    'FEATURES_BASE', 'FEATURES_POR_OBJETIVO',
    
    # Configurações
    'TRAIN_CONFIG', 'RISK_CONFIG', 'THRESHOLDS',
    'LGB_PARAMS_GRID', 'XGB_PARAMS_GRID', 'RF_PARAMS_GRID',
    'LOG_CONFIG', 'MT5_CONFIG',
    
    # Funções
    'get_mt5_timeframe', 'get_horizontes', 'get_threshold',
    
    # Classe Config
    'Config', 'config',
]


# Fuso horário para os dados retornados
TIMEZONE_FINAL: str = "America/Sao_Paulo"  # NÃO UTILIZADO

DATA_INICIO: datetime = datetime(2000, 1, 1)  # NÃO UTILIZADO
DATA_FIM: datetime = datetime(2026, 2, 28)  # NÃO UTILIZADO

# Modo de execução: "BACKTEST" ou "REALTIME"
MODO_EXECUCAO = "REALTIME"  # ou "BACKTEST"  # NÃO UTILIZADO

# arquivado/config.py

DICIONARIO_FEATURES = {
    "tendencia": ["ema_fast", "ema_slow", "dist_ema", "close"],
    "momentum": ["rsi", "close"],
    "volatilidade": ["atr", "std", "bb_up", "bb_low", "tr", "close"],
    "candles": ["corpo", "sombra_sup", "sombra_inf", "open", "high", "low", "close"],
    "reversao": ["rsi", "bb_up", "bb_low", "dist_ema", "close"],
    "risco": ["atr", "std", "close"],
    "sr": ["high", "low", "close"], # Suporte e Resistência base
    "orderflow": ["tr", "corpo", "close"], # Proxy de volume/força
    "quant": ["dist_ema", "rsi", "std", "close"]
}

# Configurações de Treino
TIMEFRAMES_TREINO = ["M1", "M5", "M15", "M30", "H1", "H4", "D1"]
SIMBOLOS = ["EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "ETHUSD", "GOLD"] # Seus principais