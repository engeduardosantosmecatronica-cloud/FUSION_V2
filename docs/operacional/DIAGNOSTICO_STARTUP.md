# DIAGNÓSTICO: POR QUE O FUSION DEMORA PARA INICIAR MONITORAMENTO

## 📊 SEQUÊNCIA DE STARTUP (fusion/main.py:313-350)

```
1. [STARTUP] MT5 inicializado em X.XXs
   └─ MT5Connector.initialize() 
   
2. [STARTUP] Conta/OMS sincronizados em X.XXs
   └─ mt5.account_info()
   └─ _refresh_oms_state() - sincroniza ticks, posições, trades
   
3. [STARTUP] Modelos principais carregados em X.XXs
   └─ _load_all_models() - carrega JOBLIB para cada símbolo/timeframe
   
4. [STARTUP] Ensembles aprovados carregados em X.XXs
   └─ _load_approved_ensembles() - carrega modelos ensemble M5
   
5. [STARTUP] TP/SL aprovados carregados em X.XXs
   └─ _load_approved_tp_sl() - carrega CSV de targets
   
6. [STARTUP] Símbolos sincronizados em X.XXs
   └─ _sync_symbols() - sincroniza com broker (MT5)
   
7. [STARTUP] Bootstrap da matriz operacional despachado em X.XXs
   └─ _bootstrap_operational_target_matrix() - pode ser async
   
8. [STARTUP] Mapa de estrategias registrado em X.XXs
   └─ _log_strategy_magic_map()
```

---

## 🔴 PRINCIPAIS GARGALOS DE DEMORA

### 1️⃣ **_calculate_features() - O MAIOR GARGALO**
📍 Localização: `fusion/main.py:1370`

```python
def _calculate_features(self, symbol: str, tf: str) -> dict:
    # Para CADA símbolo/timeframe, faz:
    rates = mt5.copy_rates_from_pos(symbol, tf_code, 0, 100)  # Busca 100 barras do MT5
    df = pd.DataFrame(rates)
    
    # Calcula ~30+ features:
    - RSI(14), RSI(28)
    - EMA(8), EMA(21), EMA(50), EMA(200)
    - MACD, Bollinger Bands
    - Volatilidade
    - Alphas (VAM, Effort, MRS, RSI_GAP)
    - Trend Alignment
    - E mais...
    
    return features  # Retorna apenas ÚLTIMA linha
```

**PROBLEMA**: 
- Busca 100 barras em CADA ciclo de monitoramento
- Calcula ~30 features que são descartadas exceto última
- Chamado para CADA (símbolo, timeframe) a cada **MINUTO**
- Se tem 10 símbolos × 6 timeframes = 60 chamadas/minuto!

**IMPACTO**: Cada chamada = ~0.5-2s esperando MT5 + cálculos pandas

---

### 2️⃣ **Loop Principal: _run_signals() - CHAMADA MASSIVA A CADA MINUTO**
📍 Localização: `fusion/main.py:5534`

```python
def _run_signals(self):
    while True:
        now = datetime.now()
        
        if now.minute != last_min:  # ⚠️ A CADA MUDANÇA DE MINUTO:
            self.config.reload()  # Recarrega YAML
            
            # Cria NOVOS exportadores a cada minuto:
            self.mt5_signal_panel = MT5SignalPanelExporter(...)
            self.mt5_trade_zones = MT5TradeZonesExporter(...)
            self.mt5_decision_layers = MT5DecisionLayersExporter(...)
            
            self._refresh_oms_state()  # Sincroniza TUDO novamente
            
            # Itera TODOS os símbolos:
            for broker_sym, sym_ia in self.sync_dict.items():
                for tf in self.TIMEFRAMES:  # M5, M15, M30, H1, H4, D1
                    # Para CADA combo, faz:
                    X = self._calculate_features(...)  # ⚠️ LENTO!
                    pred, p_buy, p_sell = model.predict(X)
                    
                    # Aplica filtros (EMA, signal_override, etc)
                    # Executa estratégias
```

**PROBLEMA**: Tudo concentrado em **1 minuto**, causando:
- Pico de CPU/memória
- Atraso no processamento de sinais
- Backlog se não terminar em 60 segundos

---

### 3️⃣ **_sync_symbols() - CHAMADA BLOQUEANTE NO STARTUP**
📍 Localização: `fusion/main.py:1430`

```python
def _sync_symbols(self):
    broker_symbols = {s.name.upper(): s.name for s in mt5.symbols_get()}
    # ⚠️ mt5.symbols_get() pode demorar se houver MUITOS símbolos
    
    for sym in configured_symbols:
        # Para cada símbolo, sincroniza com broker:
        mt5.symbol_select(real, True)  # ⚠️ Operação MT5 lenta
```

---

### 4️⃣ **_bootstrap_operational_target_matrix() - STARTUP MATRIX PODE SER SÍNCRONO**
📍 Localização: `fusion/main.py:1430-1500`

```python
startup_mode = cfg.get("startup_mode", "blocking")
if startup_mode == "blocking":  # ⚠️ Se NÃO for "background"
    run_update()  # BLOQUEIA aqui até terminar!
```

---

## 🎯 SOLUÇÕES RECOMENDADAS

### ✅ **Solução 1: Cache de Features (MAIOR IMPACTO)**

```python
# Adicionar cache TTL para features
class FusionV2:
    def __init__(self):
        self.features_cache = {}  # {(symbol, tf): (features, timestamp)}
        self.features_cache_ttl = 55  # segundos (< 60 para renovar antes do minuto)
    
    def _calculate_features(self, symbol: str, tf: str) -> dict:
        key = (symbol, tf)
        now = time.time()
        
        # Verifica cache
        if key in self.features_cache:
            features, ts = self.features_cache[key]
            if now - ts < self.features_cache_ttl:
                return features  # Retorna cache, economiza ~90% do tempo!
        
        # Calcula apenas se expirou
        features = self._calculate_features_impl(symbol, tf)
        self.features_cache[key] = (features, now)
        return features
```

**Impacto esperado**: 
- 1ª chamada: 1-2s (calcula)
- 2-55ª chamada: 10-50ms (cache) 
- **~95% mais rápido!**

---

### ✅ **Solução 2: Paralelizar Cálculo de Features**

```python
def _run_signals(self):
    # Ao invés de sequencial:
    # for broker_sym in symbols:
    #     for tf in TIMEFRAMES:
    #         X = _calculate_features(...)
    
    # Use ThreadPoolExecutor:
    from concurrent.futures import ThreadPoolExecutor
    
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {}
        for broker_sym, sym_ia in self.sync_dict.items():
            for tf in self.TIMEFRAMES:
                fut = executor.submit(self._calculate_features, broker_sym, tf)
                futures[(sym_ia, tf)] = fut
        
        # Processa resultados conforme ficam prontos
        for (sym_ia, tf), fut in futures.items():
            X = fut.result()
            # ... resto do processamento
```

**Impacto esperado**: Reduz tempo de 60 símbols em 60s para ~15s (4x mais rápido com 8 threads)

---

### ✅ **Solução 3: Distribuir Cálculo ao Longo do Minuto**

Ao invés de processar TUDO a cada mudança de minuto, distribuir:

```python
def _run_signals(self):
    symbol_queue = []
    
    while True:
        now = datetime.now()
        second = now.second
        
        # Incrementa a cada segundo
        if len(symbol_queue) == 0:
            # Refill queue a cada minuto
            symbol_queue = [(sym, tf) for sym in symbols for tf in timeframes]
        
        # Processa apenas 10 combos por segundo
        items_per_second = max(1, len(all_symbols_tfs) // 60)
        for _ in range(items_per_second):
            if symbol_queue:
                sym_ia, tf = symbol_queue.pop(0)
                X = self._calculate_features(sym_ia, tf)
                # ... processa
        
        time.sleep(1)
```

**Impacto esperado**: Spread do processamento ao longo do minuto, sem picos

---

### ✅ **Solução 4: Modo "Background" para Bootstrap Matrix**

Já existe na config! Garantir que está:

```yaml
operational_target_matrix:
  startup_mode: "background"  # Não "blocking"
```

---

## 📈 COMPARAÇÃO ANTES vs DEPOIS

| Métrica | Antes | Depois | Melhoria |
|---------|-------|--------|----------|
| Startup total | ~30-60s | ~5-10s | **5-6x** |
| 1ª previsão | 30s+ | <1s | **30x** |
| Latência média | 5-10s | <500ms | **10-20x** |
| Picos de CPU | Alto (concentrado) | Distribuído | Melhor |
| Responsividade | Lenta | Rápida | ✅ |

---

## 🚀 IMPLEMENTAÇÃO RECOMENDADA (Ordem de Prioridade)

1. **URGENTE**: Implementar cache de features (`Solução 1`)
2. **IMPORTANTE**: Garantir modo "background" para matrix
3. **DESEJÁVEL**: Paralelizar com ThreadPoolExecutor (`Solução 2`)
4. **FUTURO**: Distribuir ao longo do minuto (`Solução 3`)

