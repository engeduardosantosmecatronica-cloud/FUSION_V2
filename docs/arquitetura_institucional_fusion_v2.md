# Arquitetura Institucional FUSION_V2

Este documento define a evolucao do FUSION_V2 para um decision engine institucional:
modular, interpretavel, orientado a contexto de mercado, regime-aware e com risco de
portfolio como primeira classe.

O objetivo nao e apenas prever direcao. O objetivo e decidir se existe uma oportunidade
operacional com expectativa positiva, risco aceitavel, contexto favoravel e execucao
adequada.

## Principios

```text
separar direcao de execucao
separar sinal de oportunidade
separar modelo de decisao final
separar risco local de risco de portfolio
evitar trades redundantes
calibrar probabilidade antes de confiar nela
validar por tempo, regime e ativo
registrar cada decisao de forma auditavel
```

## Arquitetura Alvo

```text
data layer
  -> feature layer
  -> independent engines
  -> consensus engine
  -> risk/portfolio gate
  -> execution engine
  -> exit engine
  -> audit/performance layer
```

Engines independentes:

```text
Market Regime Engine
Market Structure Engine
Execution Engine
Context Engine
Risk Engine
Portfolio Exposure Engine
Exit Engine
Confidence Calibration Engine
Consensus Engine
Volatility Engine
Session Engine
Opportunity Engine
Meta-Model Ensemble
XAI/Audit Engine
```

## Organizacao De Pastas

Proposta incremental, preservando o sistema atual:

```text
fusion/
  engines/
    regime.py
    structure.py
    execution_quality.py
    context.py
    risk.py
    portfolio.py
    exit.py
    calibration.py
    consensus.py
    volatility.py
    session.py
    opportunity.py
  decision/
    schema.py
    orchestrator.py
    audit.py
    policy.py
  features/
    market_structure.py
    macro_flow.py
    microstructure.py
    volatility.py
    session.py
    portfolio.py
  training/
    labels.py
    walk_forward.py
    calibration.py
    meta_labeling.py
  validation/
    regime_validation.py
    leakage_checks.py
    reliability.py
  risk/
    sizing.py
    exposure.py
    drawdown.py
  dashboard/
    institutional_dashboard.py
  schemas/
    decision_event.schema.json
```

## Contrato Padrao Dos Engines

Todo engine deve retornar um objeto interpretavel:

```python
{
    "engine": "market_regime",
    "direction": "BUY | SELL | NEUTRAL",
    "score": 0.0,
    "confidence": 0.0,
    "state": "TREND | RANGE | COMPRESSION | EXPANSION",
    "positive_factors": [],
    "negative_factors": [],
    "warnings": [],
    "features": {},
    "timestamp": "...",
}
```

Nenhum engine deve abrir ordem diretamente. Engines avaliam contexto; o
`DecisionOrchestrator` decide.

## Pipeline De Inferencia

```text
1. receber candidato de sinal
2. carregar OHLCV multi-timeframe
3. calcular features incrementais/cacheadas
4. executar engines independentes
5. calibrar probabilidade do modelo
6. calcular consenso
7. aplicar risk gate
8. aplicar portfolio gate
9. avaliar qualidade de execucao
10. gerar decisao final
11. registrar auditoria
12. enviar ordem ou registrar bloqueio
```

Pseudo-codigo:

```python
candidate = SignalCandidate(symbol, timeframe, side, model_probs)

features = feature_store.get_context(candidate)

engine_outputs = {
    "regime": regime_engine.evaluate(features),
    "structure": structure_engine.evaluate(features),
    "execution": execution_engine.evaluate(features),
    "context": context_engine.evaluate(features),
    "volatility": volatility_engine.evaluate(features),
    "session": session_engine.evaluate(features),
    "portfolio": portfolio_engine.evaluate(candidate, open_positions),
}

calibrated_prob = calibration_engine.calibrate(candidate.model_probs, engine_outputs)
consensus = consensus_engine.combine(candidate, engine_outputs, calibrated_prob)
risk = risk_engine.evaluate(candidate, consensus, account_state)

decision = policy.decide(candidate, consensus, risk)
audit.write(decision)
```

## Decision Score

Separar scores:

```text
direction_score      = probabilidade/direcao do modelo
regime_score         = favorabilidade do regime
structure_score      = qualidade estrutural
entry_quality_score  = timing de entrada
context_score        = alinhamento macro/multi-timeframe
volatility_score     = estado de volatilidade
portfolio_score      = impacto em exposicao global
risk_score           = risco local e global
consensus_score      = alinhamento entre engines
conflict_score       = divergencia entre engines
tradeability_score   = qualidade operacional final
```

Formula inicial:

```text
tradeability_score =
  0.20 * calibrated_direction_score
+ 0.15 * regime_score
+ 0.15 * structure_score
+ 0.15 * entry_quality_score
+ 0.15 * context_score
+ 0.10 * volatility_score
+ 0.10 * portfolio_score
- 0.20 * conflict_score
```

Pesos devem ser calibrados por walk-forward, nao escolhidos definitivamente a mao.

## 1. Market Regime Engine

Estados:

```text
TREND
RANGE
COMPRESSION
EXPANSION
PANIC_VOLATILITY
ILLIQUID
TRANSITIONAL
```

Features:

```text
ATR percentile
ATR ratio curto/longo
rolling volatility
volatility clustering
ADX
Hurst exponent
entropy
Kaufman efficiency ratio
momentum persistence
directional efficiency
range overlap
candle spread abnormal
```

Saida:

```text
market_regime
regime_confidence
regime_transition_probability
allowed_model_family
```

Uso:

```text
trend models so ganham peso em TREND
mean reversion so ganha peso em RANGE
breakout models ganham peso em COMPRESSION -> EXPANSION
risco reduzido em PANIC_VOLATILITY e ILLIQUID
```

## 2. Market Structure Engine

Detectar:

```text
HH, HL, LH, LL
BOS
CHOCH
liquidity sweep/grab
displacement candle
imbalance
fair value gap
mitigation
breaker block
order block
inefficiency
stop hunt
```

Score:

```text
structure_score =
  break_quality
+ displacement_quality
+ liquidity_context
+ continuation_quality
- fake_breakout_risk
- chop_penalty
```

Saida:

```text
structure_bias = BULLISH | BEARISH | MIXED
structure_score = 0..1
active_zones = [...]
recent_events = [...]
```

## 3. Execution Engine

Responsavel por timing, nao por direcao.

Detectar:

```text
pullback quality
candle rejection
absorption
breakout quality
fake breakout
momentum ignition
delta imbalance proxy
exhaustion candle
volume spike
liquidity absorption
continuation probability
```

Pergunta central:

```text
a direcao pode estar correta, mas a entrada agora e boa?
```

Saida:

```text
entry_quality_score
entry_timing_state
entry_block_reason
```

## 4. Context Engine

Analisa contexto global:

```text
multi-timeframe alignment
fluxo macro H1/H4/D1
correlacao entre ativos
forca relativa entre moedas
sessao forex
distancia da media
reversao/extensao
volatilidade contextual
```

Ja existem bases no sistema:

```text
macro_flow
portfolio_correlation
EMA alignment
market_structure shadow
```

Alvo:

```text
context_score
context_bias
context_conflicts
```

## 5. Portfolio Exposure Engine

Controlar risco agregado:

```text
exposicao sintetica por moeda
cluster risk
correlacao dinamica
heatmap de exposicao
exposicao liquida e bruta
trades redundantes
```

Exemplo:

```text
USD exposure = +4.2
JPY exposure = -7.8
AUD exposure = -3.1
```

Regra:

```text
se nova ordem aumenta exposicao perdedora correlacionada, bloquear ou reduzir lote
se nova ordem reduz exposicao liquida, permitir com menor penalidade
```

## 6. Confidence Calibration Engine

Probabilidades precisam significar probabilidade real.

Implementar:

```text
Platt scaling
isotonic regression
reliability diagram
expected calibration error
Brier score
calibracao por ativo/timeframe/regime
```

Saida:

```text
raw_probability
calibrated_probability
calibration_error
confidence_bucket
```

Regra:

```text
BUY=0.70 deve acertar aproximadamente 70% em historico fora da amostra.
```

## 7. Consensus Engine

Combina engines:

```text
model_engine = BUY
regime_engine = BUY
structure_engine = BUY
execution_engine = SELL
context_engine = BUY
risk_engine = NEUTRAL
```

Saida:

```text
consensus_direction
consensus_score
conflict_score
position_multiplier
decision_reasons
```

Politica:

```text
alto consenso + baixo conflito = trade normal
medio consenso + risco baixo = lote reduzido
alto conflito = bloquear ou aguardar
```

## 8. Volatility Engine

Detectar:

```text
compression
expansion
volatility anomaly
ATR spike
abnormal candle spread
session volatility
volatility trap
```

Uso:

```text
ajustar stop/take/trailing
reduzir risco em volatilidade anomala
favorecer breakout apos compressao validada
bloquear entrada em trap/illiquid
```

## 9. Session Engine

Sessao importa em Forex.

Estados:

```text
Asia
London open
London session
NY open
London/NY overlap
NY afternoon
rollover
low liquidity
```

Saida:

```text
session_state
session_volatility_expected
session_edge_profile
avoid_session
```

## 10. Opportunity Engine

Separar previsao de oportunidade:

```text
direction_score = 0.81
tradeability_score = 0.22
```

Conclusao:

```text
direcao boa, oportunidade ruim -> nao operar
direcao media, oportunidade excelente, risco baixo -> operar lote reduzido
```

## 11. Meta-Model Ensemble

Familias:

```text
Logistic Regression
Random Forest
XGBoost
LightGBM
CatBoost
HMM/GMM regimes
Temporal CNN
LSTM
Transformer time series
Bayesian models
```

Ordem profissional:

```text
1. baseline tabular robusto
2. calibracao probabilistica
3. meta-labeling
4. especialistas por regime
5. deep learning apenas depois de baseline estavel
```

## 12. Feature Engineering

Expandir para:

```text
microestrutura OHLCV
candle anatomy
volatility state
liquidity behavior
regime features
structure features
correlation features
execution quality
session features
macro alignment
rolling statistics
statistical anomalies
```

Cuidados:

```text
evitar leakage
normalizar por ativo/timeframe
usar point_value correto
validar estabilidade temporal
remover features redundantes
```

## 13. Risk Engine

Implementar:

```text
dynamic sizing
volatility-adjusted risk
drawdown protection
regime-adjusted risk
partial Kelly
adaptive stop
adaptive take profit
contextual trailing
portfolio VAR
```

Sizing inicial:

```text
position_size =
  base_risk
* consensus_multiplier
* regime_multiplier
* volatility_multiplier
* drawdown_multiplier
* portfolio_multiplier
```

## 14. Dashboard Institucional

Estilo:

```text
Bloomberg
TradingView institutional
prop desk terminal
quant terminal
```

Componentes:

```text
regime map
exposure heatmap
correlation matrix
confidence gauge
structure map
volatility state
session analysis
conflict indicators
decision audit table
engine contribution chart
```

## 15. XAI E Auditoria

Cada decisao deve registrar:

```text
fatores positivos
fatores negativos
engines alinhados
engines conflitantes
score final
probabilidade calibrada
risco local
risco de portfolio
motivo final
```

Evento de auditoria:

```json
{
  "symbol": "EURUSD",
  "timeframe": "M5",
  "side": "BUY",
  "decision": "BLOCK",
  "reason": "macro_fluxo_contra",
  "scores": {
    "direction": 0.63,
    "context": 0.28,
    "portfolio": 0.91,
    "tradeability": 0.34
  },
  "engines": {}
}
```

## Pipeline De Treinamento

```text
1. carregar dados historicos
2. gerar features causais
3. gerar labels por triple barrier
4. separar walk-forward
5. treinar modelos base
6. calibrar probabilidades
7. treinar meta-labeler
8. avaliar por ativo/timeframe/regime
9. promover para registry
10. monitorar drift
```

## Pipeline De Validacao

Obrigatorio:

```text
walk-forward validation
purged/embargoed splits
regime-aware validation
out-of-sample por ano
out-of-sample por ativo
stress test por volatilidade
slippage/spread simulation
correlation/exposure simulation
```

Metricas:

```text
expectancy
profit factor
max drawdown
calmar
sharpe/sortino
hit rate por regime
payoff ratio
tail risk
ECE/Brier score
turnover
exposure concentration
```

## Backtesting Institucional

Requisitos:

```text
sem random split
sem olhar candle futuro
spread variavel
slippage
latencia simulada
ambiguidade OHLC tratada conservadoramente
custos por ativo
rollover/swap se aplicavel
execucao por bid/ask
```

## Roadmap Evolutivo

### Fase 1 - Foundation

```text
DecisionEvent schema
DecisionOrchestrator
engine interfaces
audit JSONL
dashboard de auditoria
```

### Fase 2 - Engines Basicos

```text
Regime Engine v1
Volatility Engine v1
Session Engine v1
Portfolio Exposure Engine v1
Context Engine v1
```

Status atual:

```text
Regime Engine v1: implementado em shadow via entry_filters.market_regime
Volatility Engine v1: implementado em shadow via entry_filters.volatility_engine
Session Engine v1: implementado em shadow via entry_filters.session_context
Portfolio Exposure Engine v1: implementado em shadow via entry_filters.portfolio_exposure
Context Engine v1: implementado em shadow via entry_filters.context_engine
Confidence Calibration Engine v1: implementado em shadow via entry_filters.confidence_calibration
AI Advisor Engine: implementado como pre-ordem opcional via entry_filters.ai_advisor
AI Review Agent: implementado como auditor offline em ai_review_agent
Market Briefing Overlay: implementado em shadow via entry_filters.market_briefing
Macro Flow: implementado como gate em block
Portfolio Correlation: implementado como gate em block com alivio por reversao
Market Structure/OHLCV: implementado em shadow
```

### Fase 3 - Validacao E Calibracao

```text
triple barrier final
walk-forward formal
probability calibration
reliability diagrams
meta-labeling inicial
```

### Fase 4 - Consensus E Opportunity

```text
Consensus Engine
Opportunity Engine
tradeability_score
conflict_score
position multiplier
```

### Fase 5 - Risco Institucional

```text
dynamic sizing
drawdown governor
VAR simples
exposure heatmap
regime-adjusted risk
```

### Fase 6 - Modelos Avancados

```text
LightGBM/XGBoost/CatBoost
especialistas por regime
HMM/GMM regimes
deep learning somente apos baseline estavel
```

## Padroes Profissionais

```text
cada engine testavel isoladamente
cada decisao auditavel
cada modelo com versao e registry
cada feature com contrato causal
cada promocao com relatorio out-of-sample
cada filtro com modo shadow antes de block
cada alteracao de risco documentada
```

## Proxima Implementacao Recomendada

Evoluir para a ponte local de IA `/advice` e `/review`, conectando Puter.js ou
outro provedor ao:

```text
AI Advisor pre-ordem
AI Review Agent pos-decisao
Market Briefing Overlay diario
```

O objetivo e manter a IA como camada de confirmacao e auditoria, nao como
executor direto de ordem.
