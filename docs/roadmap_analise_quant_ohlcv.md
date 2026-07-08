# Roadmap De Analise Quant OHLCV

Este roadmap organiza o projeto em etapas para sair de indicadores isolados e
chegar a estrategias mais assertivas, usando:

- dados OHLCV existentes em `data`
- indicadores existentes nas pastas `*_feature`
- metricas e analises criadas em `lab`
- projetos auxiliares reunidos em `repositorio`

## Principio Central

O edge provavelmente nao esta em um unico indicador.

Ele tende a surgir da combinacao:

```text
estrutura do candle
volatilidade
volume relativo
regime de mercado
contexto multi-timeframe
horario
gestao de risco
```

Indicadores classicos como RSI, MACD e cruzamentos de media devem ser tratados
como features secundarias ou filtros, nao como verdade isolada.

## Inventario Inicial Do Repositorio

Pasta analisada:

```text
repositorio
```

Resumo:

```text
33 projetos
1495 arquivos Python
373 arquivos Markdown
23 notebooks
varios projetos de backtest, ML, agentes, estrategias e dados
```

Projetos inicialmente mais promissores:

| Projeto | Possivel uso |
|---|---|
| `qlib-main` | Pipeline quantitativo, datasets, modelos, validacao, portfolio |
| `pyrust-bt-main` | Ideias de backtest/performance |
| `QuantForex-master` / `Quant_Forex-master` | Estrutura forex, portfolio, risco, execucao |
| `quant-ohlcv-feature-master` | Ideias adicionais de features OHLCV |
| `QuantML-main` | Factor zoo, model zoo, recursos de ML |
| `Kronos-master` | Modelos temporais/forecasting |
| `quant-trading-strategy-templates-main` | Templates de estrategias por ativo |
| `AI-Kline-main` | Visualizacao e analise de candle/indicadores |

Regra:

```text
Nao copiar tudo.
Aproveitar apenas padroes, ideias, funcoes e arquitetura que melhoram o pipeline.
```

## Fase 1 - Base De Dados E Normalizacao

Objetivo:

```text
Garantir que todos os ativos e timeframes tenham colunas padronizadas.
```

Colunas esperadas:

```text
Timestamp
open
high
low
close
volume
decimals / decimais
point_value
spread, se existir
symbol
```

Tarefas:

- padronizar `date` para `Timestamp`
- usar `tick_volume` como `volume` quando necessario
- respeitar `point_value` de cada ativo
- respeitar `spread` quando existir
- manter fallback de spread apenas quando a coluna nao existir
- gerar inventario de arquivos disponiveis por ativo/timeframe

Entrega:

```text
data_loader robusto
relatorio de disponibilidade por ativo/timeframe
```

## Fase 2 - Estrutura Do Candle

Objetivo:

```text
Extrair informacoes de forca, rejeicao, absorcao, continuidade e exaustao.
```

Features:

```text
body = abs(close - open)
range = high - low
upper_wick = high - max(open, close)
lower_wick = min(open, close) - low
body_ratio = body / range
upper_wick_ratio = upper_wick / range
lower_wick_ratio = lower_wick / range
close_position = (close - low) / range
efficiency = abs(close - open) / range
```

Interpretacao:

- corpo grande: impulso
- corpo pequeno: indecisao
- wick superior longa: rejeicao vendedora
- wick inferior longa: rejeicao compradora
- fechamento perto da maxima: pressao compradora
- fechamento perto da minima: pressao vendedora

Entrega:

```text
features/candle_structure.py
lab/candle_structure_report.csv
```

## Fase 3 - Estrutura Sequencial

Objetivo:

```text
Medir contexto e comportamento repetitivo.
```

Features:

```text
consecutive_bullish_count
consecutive_bearish_count
rolling_body_mean
rolling_range_mean
body_expansion_ratio
body_contraction_ratio
velocity_n = close_t - close_t-n
acceleration = velocity_t - velocity_t-1
```

Leituras:

- muitos candles verdes seguidos podem indicar exaustao
- corpos diminuindo indicam perda de momentum
- velocidade crescente indica continuidade
- aceleracao diminuindo indica cansaco

Entrega:

```text
features/sequential_structure.py
ranking de sequencias que precedem alvo/stop
```

## Fase 4 - Volatilidade

Objetivo:

```text
Detectar regime de range, compressao e expansao.
```

Features:

```text
true_range
ATR
ATR_percent
range_vs_ATR
rolling_range_percentile
volatility_compression_score
volatility_expansion_score
```

Regras:

- sem volatilidade nao existe alvo viavel
- compressao seguida de expansao e uma das estruturas mais importantes
- stop e alvo devem respeitar range/ATR do ativo e timeframe

Entrega:

```text
features/volatility_regime.py
relatorio por ativo/timeframe de compressao -> expansao
```

## Fase 5 - Volume E Effort Vs Result

Objetivo:

```text
Medir se o movimento tem suporte de volume ou se ha absorcao.
```

Features:

```text
volume_ratio = volume / rolling_volume_mean
volume_zscore
effort_result = volume_ratio / abs_return
high_volume_small_body
high_volume_long_wick
breakout_with_volume
breakout_without_volume
volume_climax
```

Interpretação:

- candle forte + volume alto: movimento mais confiavel
- candle forte + volume baixo: movimento suspeito
- muito volume + pouco deslocamento: absorcao
- volume extremo: possivel climax

Entrega:

```text
features/volume_effort_result.py
ranking de setups com volume relativo
```

## Fase 6 - Tendencia

Objetivo:

```text
Medir direcao, forca, inclinacao e estabilidade.
```

Features:

```text
ma_slope
ema_slope
price_distance_to_ma
ma_expansion
trend_persistence
overlap_ratio
directional_range_ratio
```

Indicadores ja encontrados como candidatos:

```text
D1: Mac_v3[55]
H4: PjcDistance[14]
H1: Vidya_v3[14]
M30: Vidya_v4[14]
M15: Vidya_v5[21]
M5: Mac_v3[14], com cautela
```

Entrega:

```text
features/trend_context.py
ranking por ativo/timeframe
```

## Fase 7 - Microestrutura Via OHLCV

Objetivo:

```text
Inferir absorcao, defesa de preco e desequilibrio sem livro de ofertas.
```

Features:

```text
absorption_score = volume_zscore * wick_ratio * (1 - body_ratio)
rejection_up_score
rejection_down_score
effort_without_result
result_without_effort
false_breakout_score
```

Exemplos:

- wick enorme + volume alto + pouco deslocamento: absorcao
- rompimento sem volume: falso rompimento provavel
- pouco volume + deslocamento grande: mercado vazio

Entrega:

```text
features/ohlcv_microstructure.py
```

## Fase 8 - Regime De Mercado

Objetivo:

```text
Classificar o mercado atual.
```

Classes iniciais:

```text
tendencia_alta
tendencia_baixa
lateralizacao
compressao
expansao
reversao_possivel
```

Features de regime:

```text
ATR_percentile
ADX/DI ou substitutos
range_overlap
ma_slope
efficiency
volume_regime
```

Entrega:

```text
features/market_regime.py
regime_label por candle
```

## Fase 9 - Suporte E Resistencia Estatisticos

Objetivo:

```text
Detectar zonas relevantes sem depender de desenho manual.
```

Features:

```text
local_high
local_low
touch_count
distance_to_nearest_resistance
distance_to_nearest_support
breakout_distance
retest_count
```

Uso:

- evitar compra direto em resistencia estatistica
- evitar venda direto em suporte estatistico
- detectar rompimento e reteste

Entrega:

```text
features/statistical_support_resistance.py
```

## Fase 10 - Multi-Timeframe

Objetivo:

```text
Combinar contexto maior com gatilho menor.
```

Timeframes:

```text
M5
M15
M30
H1
H4
D1
```

Exemplo:

```text
D1 define direcao macro
H4 confirma regime
H1/M30 define zona
M15/M5 executa gatilho
```

Features:

```text
higher_tf_trend
higher_tf_regime
higher_tf_atr_percentile
lower_tf_trigger
conflict_score
alignment_score
```

Entrega:

```text
features/multi_timeframe_context.py
```

## Fase 11 - Estatisticas Avancadas

Objetivo:

```text
Medir distribuicao, caos e eventos extremos.
```

Features:

```text
log_return
rolling_skewness
rolling_kurtosis
rolling_entropy
zscore_return
tail_event_score
```

Uso:

- detectar assimetria
- detectar risco de explosao
- medir previsibilidade/ruido

Entrega:

```text
features/statistical_features.py
```

## Fase 12 - Horario, Sessao E Dia Da Semana

Objetivo:

```text
Capturar padroes ocultos de fluxo.
```

Features:

```text
hour_broker
hour_local
weekday
session_asia
session_london
session_new_york
session_overlap
weekday_hour_bias_score
```

Regra de horario:

```text
hora_local = hora_corretora - 6
```

Entrega ja existente:

```text
lab/assets_m5_weekday_hour_bias.csv
lab/asset_correlations_summary.md
```

## Fase 13 - Lags E Janelas

Objetivo:

```text
Dar memoria curta ao modelo.
```

Features:

```text
return_1
return_3
return_5
volume_sum_10
range_mean_20
atr_14
acceleration_5
efficiency_mean_10
```

Entrega:

```text
features/rolling_lag_features.py
```

## Fase 14 - Alvos E Labels

Objetivo:

```text
Parar de prever preco exato e prever probabilidade/cenario.
```

Labels sugeridos:

```text
alta_forte
alta_fraca
neutro
queda_fraca
queda_forte
```

Labels operacionais:

```text
target_hit_before_stop
stop_hit_before_target
max_favorable_excursion
max_adverse_excursion
bars_to_target
bars_to_stop
```

Entrega:

```text
labels/target_stop_labels.py
```

## Fase 15 - Backtest Correto

Objetivo:

```text
Validar sinal com alvo, stop, spread, point_value e correlacao.
```

Obrigatorio:

- usar `point_value`
- usar `spread` se existir
- testar sinal normal
- testar sinal invertido
- testar `auto_by_asset` apenas escolhendo pelo treino
- separar treino/teste por tempo
- medir alvo ou stop primeiro
- medir drawdown
- medir sequencia de perdas
- filtrar ativos correlacionados

Entrega ja iniciada:

```text
lab/backtest_strategy_validation.py
lab/run_backtests_all_assets_by_timeframe.py
```

## Fase 16 - Correlacao E Exposicao

Objetivo:

```text
Evitar operar a mesma ideia repetida em varios pares.
```

Features:

```text
correlation_cluster
usd_exposure
eur_exposure
jpy_exposure
gbp_exposure
aud_exposure
nzd_exposure
cad_exposure
chf_exposure
```

Regra:

```text
Sinais correlacionados nao sao oportunidades independentes.
```

Entrega ja existente:

```text
lab/asset_correlation_matrix_*.csv
lab/asset_correlation_pairs_all_timeframes.csv
```

## Fase 17 - Modelagem

Objetivo:

```text
Prever probabilidade, direcao, regime e continuacao/reversao.
```

Modelos iniciais:

```text
LogisticRegression
RandomForest
LightGBM / XGBoost, se disponivel
MLP simples
```

Projetos de referencia:

```text
qlib-main
QuantML-main
Kronos-master
```

Ordem:

```text
1. baseline estatistico simples
2. modelo tabular
3. modelo temporal
4. ensemble
```

## Fase 18 - Portfolio E Risco

Objetivo:

```text
Transformar sinais bons em estrategia operavel.
```

Metrica minima:

```text
win_rate
expectancy
profit_factor
max_drawdown
max_loss_streak
exposure_by_currency
trades_by_session
trades_by_asset
```

Projetos de referencia:

```text
QuantForex-master
pyrust-bt-main
qlib-main/examples/portfolio
```

## Fase 19 - Organizacao Do Projeto

Estrutura recomendada:

```text
features/
  candle_structure.py
  sequential_structure.py
  volatility_regime.py
  volume_effort_result.py
  market_regime.py
  multi_timeframe_context.py
labels/
  target_stop_labels.py
backtests/
  engine.py
  risk.py
models/
  train_classifier.py
  evaluate_model.py
lab/
  relatorios e experimentos
repositorio/
  referencias externas
```

## Fase 20 - Criterio De Aceite

Uma estrategia so avanca se:

```text
1. Funciona fora do treino.
2. Sobrevive ao sinal invertido.
3. Nao depende de um unico ativo.
4. Nao depende de um unico horario estranho.
5. Respeita spread e point_value.
6. Tem drawdown aceitavel.
7. Nao duplica risco em pares correlacionados.
8. Explica em qual regime funciona.
```

## Ordem Pratica De Execucao

### Etapa 1

Criar features estruturais:

```text
candle
sequencia
volatilidade
volume
effort vs result
```

### Etapa 2

Criar labels operacionais:

```text
target antes do stop
stop antes do target
tempo ate alvo
tempo ate stop
```

### Etapa 3

Rodar ranking de features:

```text
por ativo
por timeframe
por regime
por horario
```

### Etapa 4

Criar estrategias simples:

```text
direcao maior + contexto + gatilho + risco
```

### Etapa 5

Backtest completo:

```text
normal
invertido
auto_by_asset
treino/teste
correlacao
drawdown
```

### Etapa 6

Modelo probabilistico:

```text
alta forte
alta fraca
neutro
queda fraca
queda forte
```

## Proxima Acao Recomendada

Implementar primeiro:

```text
features/candle_structure.py
features/volatility_regime.py
features/volume_effort_result.py
labels/target_stop_labels.py
```

Essas quatro pecas criam a base real para estrategias melhores do que
indicadores isolados.

## Status Atual No FUSION_V2

Atualizado em 2026-05-21.

### Implementado

```text
features estruturais OHLCV
volatilidade relativa
compressao / expansao
volume relativo
effort vs result
delta/pressure proxy
overlap entre candles
Kaufman Efficiency Ratio
entropia rolling
swing high / swing low
break of structure
change of character
liquidity grab
bars since events
labels target/stop/tempo
ranking de features
shadow mode global
dashboard inicial
```

Arquivos principais:

```text
fusion/features/market_structure.py
tools/generate_market_structure_features.py
tools/rebuild_market_structure_manifest.py
tools/build_market_structure_labels_and_ranking.py
tools/summarize_market_structure_ranking.py
tools/summarize_market_structure_shadow.py
dashboard/fusion_dashboard.py
```

Artefatos principais:

```text
reports/market_structure/*.csv
reports/market_structure/manifest.json
reports/market_structure_labels/market_structure_labels_tp100_sl100_lh100.csv
reports/market_structure_labels/market_structure_feature_ranking_tp100_sl100_lh100.csv
reports/market_structure_labels/market_structure_labels_optimized_lh100.csv
reports/market_structure_labels/market_structure_feature_ranking_optimized_lh100.csv
reports/market_structure_shadow/*
```

### Em Shadow Mode

A camada global OHLCV roda antes da execucao das estrategias, mas ainda nao
bloqueia ordens:

```text
entry_filters.market_structure.mode: shadow
```

Motivo:

```text
os primeiros relatorios mostram que o filtro ainda ficaria restritivo demais.
```

### Proxima Etapa Profissional

Antes de ativar qualquer bloqueio real por OHLCV:

```text
1. cruzar eventos shadow com resultado posterior
2. calibrar thresholds por ativo/timeframe
3. validar em forward/paper
4. comparar normal vs invertido
5. aplicar walk-forward temporal
```

### Atualizacao De Rastreabilidade Shadow

Implementado:

```text
signal_candle_time nos eventos Market Structure shadow
candle_time por timeframe analisado
exportacao desses campos no sumarizador
relatorio de outcomes por motivo e score
```

Ferramenta criada:

```text
tools/analyze_market_structure_shadow_outcomes.py
```

Uso recomendado:

```text
1. deixar o robo rodar em shadow mode
2. gerar novos eventos em logs/market_structure_shadow
3. cruzar com labels otimizados
4. avaliar win rate posterior por motivo e score
5. so depois calibrar ou bloquear entradas
```

Observacao:

```text
os eventos shadow antigos nao possuem signal_candle_time,
entao nao devem ser usados para medir performance posterior por candle.
```

## Roadmap Profissional Incorporado

### Nivel 1 - Features De Mercado

Concluido como camada observacional:

```text
estrutura do candle
estrutura sequencial
volatilidade relativa
volume relativo
microestrutura OHLCV
eficiencia / ruido
regime basico
suporte/resistencia estatistico
eventos estruturais
```

### Nivel 2 - Labeling

Concluido como camada offline:

```text
target antes do stop
stop antes do target
tempo ate evento
MFE / MAE
TP/SL fixo
TP/SL otimizado por ativo/timeframe
filtro de outlier de TP/SL
barreiras dinamicas por ATR
fallback quando ATR ainda nao existe
```

Ainda falta:

```text
meta-labeling sobre sinais reais das estrategias
labels probabilisticos de regime/continuidade/reversao
triple barrier com barreira vertical calibrada por timeframe/sessao
```

Arquivos gerados:

```text
market_structure_labels_atr1.5_slatr1_lh100.csv
market_structure_feature_ranking_atr1.5_slatr1_lh100.csv
market_structure_ranking_summary_atr1.5_slatr1_lh100.md
```

### Nivel 3 - Validacao

Concluido como primeira camada offline:

```text
ranking por ativo/timeframe/feature
ranking por horario/sessao
ranking por regime
calibracao candidata por ativo/timeframe/lado
relatorio de candidatos sem aplicar bloqueio real
```

Ainda falta:

```text
walk-forward formal
comparacao normal vs invertido
validacao por periodo fora do treino
robustez por multiplos anos
analise de correlacao aplicada a portfolio
```

Arquivos gerados:

```text
reports/market_structure_calibration/market_structure_calibration_candidates_atr1.5_slatr1_lh100.csv
reports/market_structure_calibration/market_structure_calibration_candidates_atr1.5_slatr1_lh100.md
reports/market_structure_calibration/market_structure_calibration_preview_atr1.5_slatr1_lh100.json
reports/market_structure_calibration/market_structure_calibration_comparison.md
```

Conclusao operacional desta etapa:

```text
usar ATR dinamico como base inicial de calibracao;
manter tudo em shadow/forward;
nao transformar ranking fixo 100/100 em bloqueio direto;
nao promover calibracao otimizada sem validar concentracao por ativo.
```

### Nivel 4 - Modelagem

Ainda nao promover para producao.

Ordem recomendada:

```text
1. logistic regression baseline
2. random forest / gradient boosting
3. feature selection
4. calibracao probabilistica
5. meta-labeling
6. ensembles por regime
```

Evitar por enquanto:

```text
LSTM
Transformers
deep learning sem baseline tabular
random split
feature leakage
```

### Nivel 5 - Execucao E Risco

Ja existe no sistema:

```text
magic number por estrategia/timeframe
SL padrao
trailing separado
limite de posicao
filtro de candle/preco
filtro de EMAs
exposure groups na S3
filtro global de correlacao entre ativos
```

Ainda falta:

```text
position sizing por volatilidade
controle de drawdown por estrategia
limite de risco agregado por moeda
portfolio intelligence
ativacao OHLCV em modo gate apos calibracao
```

### Filtro De Correlacao Entre Ativos

Implementado como protecao de banca:

```text
se existe uma posicao em prejuizo,
e uma nova ordem teria exposicao estatisticamente semelhante,
o sistema bloqueia a nova ordem.
```

Regras:

```text
correlacao positiva forte + mesma direcao = acumula risco
correlacao negativa forte + direcao oposta = acumula risco
correlacao positiva forte + direcao oposta = hedge potencial
correlacao negativa forte + mesma direcao = hedge potencial
```

Alivio por possivel reversao:

```text
antes de bloquear, o sistema verifica o ativo que esta negativo;
se M5 e M15 confirmarem recuperacao a favor da posicao aberta,
o bloqueio por correlacao e liberado.
```

Confirmacao inicial:

```text
BUY negativo: preco/candle de compra + EMAs alinhadas para compra
SELL negativo: preco/candle de venda + EMAs alinhadas para venda
timeframes: M5 e M15
min_confirmations: 2
```

Arquivos:

```text
tools/build_asset_correlations.py
reports/correlation/correlation_matrix_H1.json
reports/correlation/correlation_report_H1.md
```

Configuracao:

```text
entry_filters.portfolio_correlation.enabled: true
entry_filters.portfolio_correlation.mode: block
entry_filters.portfolio_correlation.min_abs_correlation: 0.70
entry_filters.portfolio_correlation.position_scope: all
entry_filters.portfolio_correlation.reversal_relief.enabled: true
```

### Filtro De Fluxo Macro Dominante

Implementado em shadow mode para diagnosticar a direcao macro antes da ordem.

O filtro calcula:

```text
fluxo H1
fluxo H4
fluxo D1
forca relativa da moeda base vs moeda cotada
score macro agregado
```

Componentes por timeframe:

```text
EMA21 vs EMA50
preco vs EMA50
inclinacao das medias
momentum normalizado por ATR
```

Configuracao:

```text
entry_filters.macro_flow.enabled: true
entry_filters.macro_flow.mode: block
entry_filters.macro_flow.aggregation: weighted_majority
entry_filters.macro_flow.timeframes: ["H1", "H4", "D1"]
entry_filters.macro_flow.min_score: 0.20
```

Hierarquia aplicada:

```text
entrada M5  -> fluxo H1/H4/D1
entrada M15 -> fluxo H1/H4/D1
entrada M30 -> fluxo H1/H4/D1
entrada H1  -> fluxo H4/D1
entrada H4  -> fluxo D1
entrada D1  -> fluxo D1
```

Regra operacional:

```text
maioria ponderada de alta permite BUY e bloqueia SELL
maioria ponderada de baixa permite SELL e bloqueia BUY
fluxo neutro bloqueia em modo block ate calibracao futura
```

Script manual:

```text
tools/check_macro_flow.py
```

Exemplo:

```text
.\venv\Scripts\python.exe tools\check_macro_flow.py --symbol EURUSD --direction BUY
```
