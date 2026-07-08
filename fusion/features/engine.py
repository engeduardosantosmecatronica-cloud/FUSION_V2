"""
FUSION_V2 - Feature Engine
==========================
Inspirado em ALPHAEDU: feature builder, expressions, registry
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class AlphaConfig:
    name: str
    params: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


class FeatureRegistry:
    """Registro centralizado de features/alphas."""
    
    _features: Dict[str, callable] = {}
    _expressions: Dict[str, str] = {}
    
    @classmethod
    def register(cls, name: str, func: callable, expression: Optional[str] = None):
        cls._features[name] = func
        if expression:
            cls._expressions[name] = expression
    
    @classmethod
    def get(cls, name: str) -> Optional[callable]:
        return cls._features.get(name)
    
    @classmethod
    def list_features(cls) -> List[str]:
        return list(cls._features.keys())


class RSI:
    """RSI (Relative Strength Index) - inspirado em NEXUS/OMNIS."""
    
    @staticmethod
    def calculate(df: pd.DataFrame, period: int = 14) -> pd.Series:
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / (loss + 1e-9)
        return 100 - (100 / (1 + rs))


class EMA:
    """EMA (Exponential Moving Average)."""
    
    @staticmethod
    def calculate(df: pd.DataFrame, period: int) -> pd.Series:
        return df['close'].ewm(span=period, adjust=False).mean()


class ATR:
    """ATR (Average True Range)."""
    
    @staticmethod
    def calculate(df: pd.DataFrame, period: int = 14) -> pd.Series:
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return true_range.rolling(period).mean()


class BollingerBands:
    """Bollinger Bands."""
    
    @staticmethod
    def calculate(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> Dict[str, pd.Series]:
        ema = df['close'].ewm(span=period).mean()
        std = df['close'].rolling(period).std()
        return {
            'bb_upper': ema + (std * std_dev),
            'bb_middle': ema,
            'bb_lower': ema - (std * std_dev),
        }


class MACD:
    """MACD (Moving Average Convergence Divergence)."""
    
    @staticmethod
    def calculate(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9):
        ema_fast = df['close'].ewm(span=fast).mean()
        ema_slow = df['close'].ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        return {
            'macd': macd_line,
            'macd_signal': signal_line,
            'macd_hist': histogram,
        }


class AlphaMiner:
    """Alpha Miner - inspirado em ALPHAEDU para extrair features preditivas."""
    
    @staticmethod
    def vam(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Volume-Adjusted Momentum."""
        ret = np.log(df['close'] / df['close'].shift(1))
        range_pct = (df['high'] - df['low']) / df['close']
        return ret.rolling(period).mean() / (range_pct.rolling(period).std() + 1e-9)
    
    @staticmethod
    def effort(df: pd.DataFrame, period: int = 50) -> pd.Series:
        """Effort Ratio - energia do movimento."""
        range_pct = (df['high'] - df['low']) / df['close']
        return range_pct / (range_pct.rolling(period).mean() + 1e-9)
    
    @staticmethod
    def mrs(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Mean Reversion Signal."""
        ema21 = df['close'].ewm(span=21).mean()
        dist_ema = (df['close'] / ema21) - 1
        range_pct = (df['high'] - df['low']) / df['close']
        return dist_ema / (range_pct.rolling(period).mean() + 1e-9)
    
    @staticmethod
    def rsi_gap(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """RSI Gap - mudança no momentum."""
        rsi = RSI.calculate(df, period)
        return rsi - rsi.rolling(10).mean()


class FeatureEngine:
    """Motor de features inspirado em ALPHAEDU."""
    
    def __init__(self):
        self.registry = FeatureRegistry
        self._register_default_features()
    
    def _register_default_features(self):
        self.registry.register('rsi', RSI.calculate, 'RSI(close, period=14)')
        self.registry.register('ema21', lambda df: EMA.calculate(df, 21), 'EMA(close, period=21)')
        self.registry.register('ema50', lambda df: EMA.calculate(df, 50), 'EMA(close, period=50)')
        self.registry.register('ema200', lambda df: EMA.calculate(df, 200), 'EMA(close, period=200)')
        self.registry.register('atr', ATR.calculate, 'ATR(high, low, close, period=14)')
        self.registry.register('macd', MACD.calculate, 'MACD(close)')
        self.registry.register('alpha_vam', AlphaMiner.vam, 'VAM(ret, range)')
        self.registry.register('alpha_effort', AlphaMiner.effort, 'EFFORT(range)')
        self.registry.register('alpha_mrs', AlphaMiner.mrs, 'MRS(dist_ema, range)')
        self.registry.register('alpha_rsi_gap', AlphaMiner.rsi_gap, 'RSI_GAP(rsi)')
    
    def calculate(self, df: pd.DataFrame, features: List[str]) -> pd.DataFrame:
        """Calcula múltiplas features em um DataFrame."""
        if len(df) < 50:
            return pd.DataFrame()
        
        result = pd.DataFrame(index=df.index)
        
        for feat in features:
            if feat == 'rsi':
                result['rsi'] = RSI.calculate(df)
            elif feat == 'ema21':
                result['ema21'] = EMA.calculate(df, 21)
            elif feat == 'ema50':
                result['ema50'] = EMA.calculate(df, 50)
            elif feat == 'ema200':
                result['ema200'] = EMA.calculate(df, 200)
            elif feat == 'atr':
                result['atr'] = ATR.calculate(df)
            elif feat == 'macd':
                macd = MACD.calculate(df)
                result['macd'] = macd['macd']
                result['macd_signal'] = macd['macd_signal']
                result['macd_hist'] = macd['macd_hist']
            elif feat == 'alpha_vam':
                result['alpha_vam'] = AlphaMiner.vam(df)
            elif feat == 'alpha_effort':
                result['alpha_effort'] = AlphaMiner.effort(df)
            elif feat == 'alpha_mrs':
                result['alpha_mrs'] = AlphaMiner.mrs(df)
            elif feat == 'alpha_rsi_gap':
                result['alpha_rsi_gap'] = AlphaMiner.rsi_gap(df)
            elif feat == 'dist_ema':
                ema21 = EMA.calculate(df, 21)
                result['dist_ema'] = (df['close'] / ema21) - 1
            elif feat == 'range_pct':
                result['range_pct'] = (df['high'] - df['low']) / df['close']
            elif feat == 'ret':
                result['ret'] = np.log(df['close'] / df['close'].shift(1))
        
        return result.dropna()
    
    def calculate_multi_tf(self, dfs: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Calcula features para múltiplos timeframes e concatena."""
        all_features = []
        
        for tf, df in dfs.items():
            feats = self.calculate(df, ['rsi', 'dist_ema', 'ret', 'range_pct',
                                        'alpha_vam', 'alpha_effort', 'alpha_mrs', 'alpha_rsi_gap'])
            if feats is not None and not feats.empty:
                feats = feats.add_suffix(f'_{tf}')
                all_features.append(feats.reset_index(drop=True))
        
        if not all_features:
            return pd.DataFrame()
        
        result = pd.concat(all_features, axis=1)
        result = result.iloc[[-1]]
        return result