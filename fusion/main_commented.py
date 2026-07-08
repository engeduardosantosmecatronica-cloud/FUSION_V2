"""
FUSION_V2 - Main Entry Point
=============================
Sistema unificado com modelos por ATIVO/TIMEFRAME
"""

# ============================================
# IMPORTS
# ============================================

import sys                      # Sys utilities (exit, path)
import time                     # Time sleep
import threading                # Threading for trailing
import MetaTrader5 as mt5       # MT5 API connection
import numpy as np              # Numerical operations
import pandas as pd             # Data manipulation
from datetime import datetime    # Date/time utilities
from pathlib import Path         # Path manipulation

# ============================================
# FUSION MODULES
# ============================================

from fusion.core.config import get_config, FusionConfig  # Config system
from fusion.core.logger import get_logger               # Logging system
from fusion.data.pipeline import MT5Connector           # MT5 connector
from fusion.features.engine import FeatureEngine, AlphaMiner, RSI, EMA  # Feature engine
from fusion.execution.trading import TradingExecutor    # Order execution
from fusion.execution.trailing import TrailingManager   # Trailing stop


# ============================================
# SINGLE MODEL CLASS
# ============================================

class SingleModel:
    """Modelo individual para um símbolo/timeframe."""
    
    def __init__(self, model_path, scaler_path, meta_path):
        """Carrega modelo, scaler e meta de arquivos."""
        import joblib
        
        self.model = joblib.load(model_path)           # Modelo treinado
        self.scaler = joblib.load(scaler_path)         # Scaler para normalização
        self.meta = joblib.load(meta_path)              # Metadados (thresholds, features)
        
        # Extrai configurações do meta
        self.feature_cols = self.meta.get('feature_columns', [])  # Colunas do modelo
        self.buy_thresh = self.meta.get('buy_threshold', 0.55)     # Threshold BUY
        self.sell_thresh = self.meta.get('sell_threshold', 0.55) # Threshold SELL
    
    def predict(self, features_df):
        """Prediz direção: 0=hold, 1=buy, 2=sell."""
        
        # Seleciona features e normaliza
        X = features_df[self.feature_cols].values
        X_scaled = self.scaler.transform(X)
        
        # Prediz probabilidades
        probs = self.model.predict_proba(X_scaled)
        
        # Extrai probs de BUY e SELL (classe 1 e 2)
        p_buy = float(probs[0, 1]) if self.model.classes_[0] == 1 else float(probs[0, 2])
        p_sell = float(probs[0, 2]) if self.model.classes_[0] == 1 else float(probs[0, 1])
        
        # Caso tenha mais de 2 classes, ajusta
        if len(self.model.classes_) > 2:
            for i, cls in enumerate(self.model.classes_):
                if cls == 1: 
                    p_buy = float(probs[0, i])
                elif cls == 2: 
                    p_sell = float(probs[0, i])
        
        # Compara com thresholds
        if p_buy > self.buy_thresh: 
            return 1, p_buy          # BUY
        if p_sell > self.sell_thresh: 
            return 2, p_sell          # SELL
        return 0, max(p_buy, p_sell) # NEUTRO


# ============================================
# FUSIONV2 MAIN CLASS
# ============================================

class FusionV2:
    """Sistema principal FUSION_V2."""
    
    # Cores para terminal
    RED = "\033[91m"    # Vermelho
    GREEN = "\033[92m"  # Verde
    YELLOW = "\033[93m" # Amarelo
    RESET = "\033[0m"   # Reset cor
    
    def __init__(self):
        """Inicializa componentes do sistema."""
        
        self.logger = get_logger("FusionV2")           # Logger
        self.config = get_config()                      # Config
        self.trading = TradingExecutor()                # Executor de ordens
        self.trailing = TrailingManager()               # Gerenciador trailing
        self.models: dict = {}                          # Modelos carregados {(symbol, tf): model}
        self.sync_dict: dict = {}                       # Mapeamento broker -> simbolo
        self.monitor_state: dict = {}                  # Estado de cada par/TF
        self.TIMEFRAMES = ["M5", "M15", "M30", "H1", "H4", "D1"]  # TFs monitorados
        self.TF_MINUTES = {"M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440}  # Minutos por TF
        self.TF_MAP = {                                 # Mapa MT5
            "M5": 5, "M15": 15, "M30": 30,
            "H1": 60, "H4": 240, "D1": 1440
        }
        self.SETUPS = {}                               # Configurações de setup
    
    def initialize(self) -> bool:
        """Inicializa MT5 e carrega modelos."""
        
        self.logger.info("=" * 60)
        self.logger.info("FUSION_V2 - SISTEMA DE TRADING IA")
        self.logger.info("=" * 60)
        
        # Inicializa MT5
        if not MT5Connector.initialize():
            self.logger.critical("Falha ao inicializar MT5")
            return False
        
        # Mostra info da conta
        acc = mt5.account_info()
        if acc:
            self.logger.info(f"MT5 Conectado | Conta: {acc.login} | Saldo: {acc.balance:.2f} {acc.currency}")
        
        # Carrega modelos e sincroniza símbolos
        self._load_all_models()
        self._sync_symbols()
        
        return True
    
    def _load_all_models(self):
        """Carrega todos os modelos por símbolo/timeframe."""
        
        import joblib
        from pathlib import Path
        
        # Diretório do projeto e modelos
        project_dir = Path(__file__).resolve().parent.parent
        models_dir = project_dir / "models"
        
        # Verifica se diretório existe
        if not models_dir.exists():
            self.logger.error(f"Diretório de modelos não encontrado: {models_dir}")
            return
        
        loaded = 0
        
        # Itera por cada diretório de símbolo
        for sym_dir in models_dir.iterdir():
            if not sym_dir.is_dir():
                continue
            symbol = sym_dir.name
            
            # Itera por cada diretório de timeframe
            for tf_dir in sym_dir.iterdir():
                if not tf_dir.is_dir():
                    continue
                tf = tf_dir.name
                
                # Paths dos arquivos do modelo
                model_path = tf_dir / "model.pkl"
                scaler_path = tf_dir / "scaler.pkl"
                meta_path = tf_dir / "meta.pkl"
                
                # Se todos existem, carrega
                if all(p.exists() for p in [model_path, scaler_path, meta_path]):
                    try:
                        self.models[(symbol, tf)] = SingleModel(model_path, scaler_path, meta_path)
                        loaded += 1
                    except Exception as e:
                        self.logger.warning(f"Erro ao carregar {symbol}/{tf}: {e}")
        
        self.logger.info(f"Modelos carregados: {loaded}")
    
    def _sync_symbols(self):
        """Sincroniza símbolos do broker com nomes internos."""
        
        # Cria dict com todos os símbolos do broker em uppercase
        broker_symbols = {s.name.upper(): s.name for s in mt5.symbols_get()}
        
        # Lista de símbolos padrão
        default_symbols = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "GBPJPY", 
                          "AUDUSD", "USDCAD", "USDCHF", "EURGBP", "EURJPY", "NZDUSD"]
        
        # Para cada símbolo padrão
        for sym in default_symbols:
            sym_upper = sym.upper()
            if sym_upper in broker_symbols:
                # Nome correto no broker
                real = broker_symbols[sym_upper]
                mt5.symbol_select(real, True)
                self.sync_dict[real] = sym
            elif sym == "XAUUSD":
                # Special case for GOLD
                for name in broker_symbols:
                    if "XAUUSD" in name or "GOLD" in name.upper():
                        mt5.symbol_select(broker_symbols[name], True)
                        self.sync_dict[broker_symbols[name]] = "XAUUSD"
                        break
        
        # Aplica mapeamentos da config
        for sym, mapped in self.config.data.symbol_mapping.items():
            mapped_upper = mapped.upper()
            if mapped_upper in broker_symbols:
                real = broker_symbols[mapped_upper]
                mt5.symbol_select(real, True)
                self.sync_dict[real] = sym
        
        self.logger.info(f"FUSION_V2 Online | {len(self.sync_dict)} Ativos Sincronizados")
    
    def _calculate_features(self, symbol: str, tf: str) -> dict:
        """Calcula features para símbolo/timeframe."""
        
        # Mapa de timeframes MT5
        tf_code = {
            "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1
        }[tf]
        
        # Busca dados do MT5 (últimas 100 barras)
        rates = mt5.copy_rates_from_pos(symbol, tf_code, 0, 100)
        if rates is None:
            return {}
        
        # Converte para DataFrame
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        
        # Mínimo de dados
        if len(df) < 100:
            return {}
        
        # Inicializa features
        features = pd.DataFrame(index=df.index)
        close = df['close']
        high = df['high']
        low = df['low']
        
        # ========================================
        # RETORNOS
        # ========================================
        ret = np.log(close / close.shift(1))            # Retorno logarítmico
        features['ret'] = ret                            # Retorno atual
        features['ret_5'] = ret.rolling(5).sum()       # Retorno acumulado 5
        features['ret_10'] = ret.rolling(10).sum()      # Retorno acumulado 10
        features['ret_20'] = ret.rolling(20).sum()      # Retorno acumulado 20
        
        # ========================================
        # RSI
        # ========================================
        rsi14 = RSI.calculate(df, 14)                   # RSI 14 períodos
        rsi28 = RSI.calculate(df, 28)                   # RSI 28 períodos
        features['rsi14'] = rsi14                       # RSI 14
        features['rsi28'] = rsi28                       # RSI 28
        features['rsi_diff'] = rsi14 - rsi28           # Diferença entre RSIs
        features['rsi_ma5'] = rsi14.rolling(5).mean()   # Média RSI
        features['rsi_gap'] = rsi14 - rsi14.rolling(10).mean()  # Gap RSI
        
        # ========================================
        # EMAs
        # ========================================
        ema8 = EMA.calculate(df, 8)                     # EMA rápida
        ema21 = EMA.calculate(df, 21)                   # EMA 21
        ema50 = EMA.calculate(df, 50)                  # EMA 50
        ema200 = EMA.calculate(df, 200)                # EMA 200
        
        features['ema8'] = ema8
        features['ema21'] = ema21
        features['ema50'] = ema50
        features['ema200'] = ema200
        
        # Distância do preço às EMAs (normalizado)
        features['dist_ema8'] = (close / ema8) - 1
        features['dist_ema21'] = (close / ema21) - 1
        features['dist_ema50'] = (close / ema50) - 1
        features['dist_ema200'] = (close / ema200) - 1
        
        # ========================================
        # VOLATILIDADE / RANGE
        # ========================================
        range_pct = (high - low) / close                # Range % do candle
        features['range_pct'] = range_pct
        features['range_ma10'] = range_pct.rolling(10).mean()  # Média do range
        
        # Posição do preço no range 20
        features['high_20'] = high.rolling(20).max()
        features['low_20'] = low.rolling(20).min()
        features['position_in_range'] = (close - features['low_20']) / (features['high_20'] - features['low_20'] + 1e-9)
        
        # Ratio de volatilidade (curta vs longa)
        vol5 = ret.rolling(5).std()
        vol20 = ret.rolling(20).std()
        features['vol_ratio'] = vol5 / (vol20 + 1e-9)
        
        # ========================================
        # MACD
        # ========================================
        ema_fast = close.ewm(span=12).mean()           # EMA 12
        ema_slow = close.ewm(span=26).mean()           # EMA 26
        macd_line = ema_fast - ema_slow               # MACD line
        signal_line = macd_line.ewm(span=9).mean()     # Signal line
        features['macd'] = macd_line
        features['macd_signal'] = signal_line
        features['macd_hist'] = macd_line - signal_line
        
        # ========================================
        # BOLLINGER BANDS
        # ========================================
        features['upper_bb'] = ema21 + (ret.rolling(20).std() * 2)
        features['lower_bb'] = ema21 - (ret.rolling(20).std() * 2)
        features['bb_width'] = features['upper_bb'] - features['lower_bb']
        
        # ========================================
        # ALPHAS (Features mineradas)
        # ========================================
        features['alpha_vam'] = AlphaMiner.vam(df, 20)          # Volume-Adjusted Momentum
        features['alpha_effort'] = AlphaMiner.effort(df, 50)   # Effort Ratio
        features['alpha_mrs'] = AlphaMiner.mrs(df, 20)         # Mean Reversion Signal
        features['alpha_rsi_gap'] = AlphaMiner.rsi_gap(df, 14) # RSI Gap
        
        # ========================================
        # TREND ALIGNMENT
        # ========================================
        # Conta quantos indicadores confirmam alta (RSI>50 + preço>EMA)
        trend_alignment = (rsi14 > 50).astype(int)
        for period in [5, 10, 20]:
            ma_trend = (close > EMA.calculate(df, period)).astype(int)
            trend_alignment = trend_alignment + ma_trend
        features['trend_alignment'] = trend_alignment
        
        # Retorna última linha com features calculadas
        return features.dropna().iloc[[-1]]
    
    def _run_signals(self):
        """Loop principal de sinais e execução."""
        
        last_min = -1                                   # Minuto anterior
        last_trade_time: dict = {}                      # Timestamp últimas ordens
        cooldown_seconds = 300                          # 5 min entre ordens
        
        while True:
            now = datetime.now()
            
            # Executa a cada minuto
            if now.minute != last_min:
                # Para cada símbolo sincronizado
                for broker_sym, sym_ia in self.sync_dict.items():
                    for tf in self.TIMEFRAMES:
                        key = (sym_ia, tf)
                        
                        # Busca modelo para esse par/TF
                        model = self.models.get(key)
                        if not model:
                            self.monitor_state[key] = {"signal": 0, "status": "SEM_MODELO"}
                            continue
                        
                        # ========================================
                        # SE TEM POSIÇÃO ABERTA
                        # ========================================
                        if self.trading.is_position_open(broker_sym, 0):
                            # Calcula features mesmo com posição
                            X = self._calculate_features(broker_sym, tf)
                            if not X.empty:
                                try:
                                    pred, prob = model.predict(X)
                                    if pred == 1:
                                        status = f"BUY ({prob:.2f})"
                                    elif pred == 2:
                                        status = f"SELL ({prob:.2f})"
                                    else:
                                        status = "NEUTRO"
                                    self.monitor_state[key] = {"signal": prob, "status": status}
                                except:
                                    self.monitor_state[key] = {"signal": 0, "status": "EM_POSICAO"}
                            else:
                                self.monitor_state[key] = {"signal": 0, "status": "EM_POSICAO"}
                            continue
                        
                        # ========================================
                        # COOLDOWN
                        # ========================================
                        cooldown_key = f"{sym_ia}_{tf}"
                        if cooldown_key in last_trade_time:
                            if (now - last_trade_time[cooldown_key]).seconds < cooldown_seconds:
                                continue
                        
                        # ========================================
                        # CALCULA FEATURES
                        # ========================================
                        X = self._calculate_features(broker_sym, tf)
                        if X.empty:
                            self.monitor_state[key] = {"signal": 0, "status": "ERRO_DADOS"}
                            continue
                        
                        # ========================================
                        # PREDIÇÃO
                        # ========================================
                        try:
                            pred, prob = model.predict(X)
                            
                            # BUY
                            if pred == 1:
                                self.logger.info(f"SINAL BUY: {sym_ia} {tf} | Prob: {prob:.2f} | Thresh: {model.buy_thresh:.2f}")
                                result = self.trading.execute_buy(broker_sym, self.TF_MINUTES.get(tf, 5), mode=f"FUSION_{tf}")
                                if result.success:
                                    last_trade_time[cooldown_key] = now
                                    self.logger.info(f"ORDEM BUY EXECUTADA: {broker_sym} #{result.ticket}")
                                status = f"BUY ({prob:.2f})"
                            
                            # SELL
                            elif pred == 2:
                                self.logger.info(f"SINAL SELL: {sym_ia} {tf} | Prob: {prob:.2f} | Thresh: {model.sell_thresh:.2f}")
                                result = self.trading.execute_sell(broker_sym, self.TF_MINUTES.get(tf, 5), mode=f"FUSION_{tf}")
                                if result.success:
                                    last_trade_time[cooldown_key] = now
                                    self.logger.info(f"ORDEM SELL EXECUTADA: {broker_sym} #{result.ticket}")
                                status = f"SELL ({prob:.2f})"
                            else:
                                status = "NEUTRO"
                            
                            self.monitor_state[key] = {"signal": prob, "status": status}
                        
                        except Exception as e:
                            self.monitor_state[key] = {"signal": 0, "status": f"ERRO: {str(e)[:15]}"}
                
                # Atualiza dashboard a cada minuto
                self._print_dashboard()
                last_min = now.minute
            
            # Sleep 1 segundo
            time.sleep(1)
    
    def _print_dashboard(self):
        """Imprime dashboard de status."""
        
        import os
        os.system('cls' if os.name == 'nt' else 'clear')  # Limpa tela
        
        now = datetime.now().strftime('%H:%M:%S')
        try:
            # Header
            print(f"\n{'='*120}")
            print(f" FUSION_V2 DASHBOARD | {now} | STATUS: OPERACIONAL | Modelos: {len(self.models)}")
            print(f"{'='*120}")
            print(f"{'ATIVO':<8}|{'M5':^10}|{'M15':^10}|{'M30':^10}|{'H1':^10}|{'H4':^10}|{'D1':^10}|{'MOTIVO':^15}")
            print("-" * 120)
            
            # Lista símbolos
            symbols = list(set(k[0] for k in self.monitor_state.keys()))
            
            for sym in sorted(symbols):
                display = "GOLD" if sym == "XAUUSD" else sym
                cells_raw = []
                motivo = "-"  # Motivo do bloqueio
                
                # Para cada timeframe
                for tf in ["M5", "M15", "M30", "H1", "H4", "D1"]:
                    key = (sym, tf)
                    state = self.monitor_state.get(key, {})
                    model = self.models.get(key)
                    
                    sig = state.get('signal', 0)
                    st = state.get('status', '')
                    buy_th = model.buy_thresh if model else 0
                    sell_th = model.sell_thresh if model else 0
                    
                    # Verifica se tem posição
                    has_position = st == "EM_POSICAO"
                    if has_position:
                        if motivo == "-":
                            motivo = "POSICAO"
                    
                    # Monta célula
                    if has_position:
                        if sig > buy_th:
                            cell = f"B:{sig:.2f}/{buy_th:.2f}"
                        elif sig > sell_th:
                            cell = f"S:{sig:.2f}/{sell_th:.2f}"
                        else:
                            cell = f"N:{sig:.2f}/{buy_th:.2f}"
                    elif st == "SEM_MODELO":
                        cell = f"-/-"
                    elif "BUY" in st:
                        cell = f"B:{sig:.2f}/{buy_th:.2f}"
                    elif "SELL" in st:
                        cell = f"S:{sig:.2f}/{sell_th:.2f}"
                    else:
                        if model:
                            if sig > buy_th:
                                cell = f"B:{sig:.2f}/{buy_th:.2f}"
                            elif sig > sell_th:
                                cell = f"S:{sig:.2f}/{sell_th:.2f}"
                            else:
                                cell = f"N:{sig:.2f}/{buy_th:.2f}"
                        else:
                            cell = "-"
                    
                    cells_raw.append(cell)
                
                # Monta linha
                row = f"{display:<8}|"
                for cr in cells_raw:
                    row += f"{cr:^14}|"
                row += f"{motivo:^15}"
                print(row)
            
            # Footer
            print(f"{'='*120}")
            print(f" Legenda: B=BUY | S=SELL | N=NEUTRO |")
            print()
        except Exception:
            pass
    
    def start_trailing_loop(self):
        """Inicia loop de trailing em thread separada."""
        
        symbols = list(self.sync_dict.keys())
        trailing_thread = threading.Thread(
            target=self.trailing.start_background_loop,
            args=(symbols, 1),  # Check a cada 1 segundo
            daemon=True
        )
        trailing_thread.start()
    
    def run(self):
        """Executa sistema principal."""
        
        try:
            # Inicializa
            if not self.initialize():
                self.logger.error("Falha na inicialização")
                return
            
            # Inicia trailing
            self.start_trailing_loop()
            
            # Loop de sinais
            self._run_signals()
            
        except KeyboardInterrupt:
            self.logger.warning("Sistema pausado pelo usuário")
        finally:
            MT5Connector.shutdown()
            self.logger.info("FUSION_V2 encerrado")


# ============================================
# ENTRY POINT
# ============================================

if __name__ == "__main__":
    import MetaTrader5 as mt5
    import numpy as np
    import pandas as pd
    
    fusion = FusionV2()
    fusion.run()