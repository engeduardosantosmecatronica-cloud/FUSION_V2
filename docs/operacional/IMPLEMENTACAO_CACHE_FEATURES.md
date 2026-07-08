# IMPLEMENTAÇÃO: CACHE DE FEATURES

## Problema
A função `_calculate_features()` é chamada **60+ vezes/minuto** (10 símbolos × 6 timeframes).
Cada chamada busca 100 barras do MT5 e recalcula 30+ features.
**Resultado**: ~95% do tempo é gasto recalculando dados que não mudaram!

---

## Solução: Feature Cache TTL

### Passo 1: Adicionar Cache ao __init__ 

**Arquivo**: `fusion/main.py` - Na função `__init__()` (após linha ~140)

```python
# Adicione após self.models = {}:

# Cache de features com TTL
self.features_cache = {}  # {(symbol, tf): (features_df, timestamp)}
self.features_cache_ttl = 55  # segundos (< 60 para renovar antes do minuto)
self.features_cache_hits = 0  # Estatísticas
self.features_cache_misses = 0  # Estatísticas
```

---

### Passo 2: Modificar _calculate_features() para usar cache

**Arquivo**: `fusion/main.py` - Função `_calculate_features()` (linha ~1370)

**ANTES:**
```python
def _calculate_features(self, symbol: str, tf: str) -> dict:
    """Calcula features para símbolo/timeframe."""
    tf_code = {
        "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15, ...
    }[tf]
    
    rates = mt5.copy_rates_from_pos(symbol, tf_code, 0, 100)
    if rates is None:
        return pd.DataFrame()
    
    df = pd.DataFrame(rates)
    # ... calculos de features ...
    return features.dropna().iloc[[-1]]
```

**DEPOIS:**
```python
def _calculate_features(self, symbol: str, tf: str) -> dict:
    """Calcula features para símbolo/timeframe com cache TTL."""
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
    
    # 2. Se não está em cache ou expirou, calcula
    self.features_cache_misses += 1
    
    tf_code = {
        "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1
    }[tf]
    
    rates = mt5.copy_rates_from_pos(symbol, tf_code, 0, 100)
    if rates is None:
        return pd.DataFrame()
    
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    
    if len(df) < 100:
        return pd.DataFrame()
    
    # [TODO: Manter todo o código de cálculo de features igual...]
    features = pd.DataFrame(index=df.index)
    # ... resto do cálculo ...
    
    result = features.dropna().iloc[[-1]]
    
    # 3. Armazena em cache
    self.features_cache[key] = (result, now)
    
    return result
```

---

### Passo 3: Limpar cache expirado periodicamente

**Arquivo**: `fusion/main.py` - Função `_run_signals()` (linha ~5534)

Adicione isto **dentro do loop principal** (a cada minuto):

```python
def _run_signals(self):
    last_min = -1
    last_cache_cleanup = time.time()
    CACHE_CLEANUP_INTERVAL = 60  # A cada 60 segundos
    
    while True:
        now = datetime.now()
        now_time = time.time()
        
        # Limpar cache expirado periodicamente
        if now_time - last_cache_cleanup > CACHE_CLEANUP_INTERVAL:
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
            
            # Reset stats a cada limpeza
            self.features_cache_hits = 0
            self.features_cache_misses = 0
            last_cache_cleanup = now_time
        
        if now.minute != last_min:
            # ... resto do código ...
```

---

## 📊 Resultados Esperados

### Linha de Base (SEM CACHE)
```
Ciclo 1 (início do minuto):
  - EURUSD M5: 1.2s (busca + calcula)
  - EURUSD M15: 1.1s
  - GBPUSD M5: 1.0s
  - GBPUSD M15: 1.1s
  ... total: ~60 chamadas em ~60+ segundos
  
RESULTADO: 1ª previsão após 60+ segundos
```

### COM CACHE (após 1ª previsão)
```
Ciclo 2 (mesmo minuto, 30 segundos depois):
  - EURUSD M5: 5ms (cache hit!)
  - EURUSD M15: 5ms (cache hit!)
  - GBPUSD M5: 5ms (cache hit!)
  - GBPUSD M15: 5ms (cache hit!)
  ... total: ~60 chamadas em ~0.3 segundos
  
RESULTADO: Previsões múltiplas por minuto, ~95% mais rápido
```

### Estatísticas do Cache
```
[CACHE] Limpeza: removidos 12 itens (hits=420 misses=12)
↑ Hit rate: 420/432 = 97.2% de acertos!
```

---

## 🔧 Configuração (Opcional)

Adicione ao `config/fusion_config.yaml`:

```yaml
# Feature Caching
features:
  cache_enabled: true
  cache_ttl_seconds: 55      # Renovar antes de 60s virar 61s
  cache_max_items: 1000      # Limpar se crescer demais
  cache_cleanup_interval: 60  # Limpar a cada 60s
```

Depois adapt o código para ler:
```python
cache_cfg = self.config.get("features", {}) or {}
self.features_cache_ttl = float(cache_cfg.get("cache_ttl_seconds", 55) or 55)
```

---

## ⚠️ Considerações Importantes

### 1. **TTL de 55 segundos**
- Renova antes do minuto virar 61 segundos
- Garante que dados estão frescos (máximo 55s de latência)
- Suficiente para maioria dos casos de trading

### 2. **Cache por (symbol, timeframe)**
- Cada combinação tem seu próprio TTL independente
- Se um símbolo ficar indisponível, seu cache expira
- Mantém cache de cada timeframe separado

### 3. **Limpeza Automática**
- Remove itens >expirados após 10s (ttl + 10)
- Previne memory leak
- Executa a cada 60 segundos

### 4. **Sem Invalidação Manual**
- Usa apenas TTL (time-to-live)
- Simples, nenhuma sincronização de estado
- Perfeito para dados que mudam a cada minuto

---

## ✅ Implementação Stepwise

1. Adicionar variáveis de cache no `__init__`
2. Wrap `_calculate_features()` com lógica de cache
3. Adicionar limpeza periódica no `_run_signals()`
4. **Testar e medir melhoria**
5. Ajustar `cache_ttl` conforme necessário

**Tempo de implementação**: ~15 minutos
**Impacto**: ~95% redução no tempo de cálculo de features

