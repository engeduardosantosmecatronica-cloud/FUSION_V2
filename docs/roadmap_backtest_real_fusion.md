# Roadmap: Backtest Real do Fusion

Objetivo: executar o mesmo processo decisorio do robo ao vivo em modo historico, usando modelos reais, features reais, estrategias reais e filtros institucionais, mas com ordens e posicoes simuladas.

## Fase 1 - Contratos e adaptadores

Status: iniciado.

Criar interfaces reutilizaveis:

- `BrokerAdapter`
- `BacktestBrokerAdapter`
- `MarketDataProvider`
- `HistoricalMarketDataProvider`
- `BacktestOMS`
- `BacktestContext`

Arquivos iniciais:

- `fusion/backtest/adapters.py`
- `fusion/backtest/context.py`
- `fusion/backtest/market_data.py`
- `fusion/backtest/oms.py`

Concluido nesta fase:

- contratos de configuracao e contexto
- broker adapter abstrato
- broker adapter de backtest
- OMS simulado inicial
- provider historico inicial

## Fase 2 - Provider historico multi-timeframe

Status: iniciado.

Implementar leitura sincronizada de:

- M5
- M15
- M30
- H1
- H4
- D1

Regras:

- nao usar candle futuro
- timeframe maior so atualiza quando candle maior fecha
- permitir CSV historico + complemento MT5
- remover candles de fim de semana quando nao houver mercado real

Concluido nesta fase:

- leitura da estrutura `data/csv/TF/ano/mes/SYMBOL.csv`
- `get_bars_until` para buscar candles ate o timestamp atual
- `get_aligned_bars` para entregar janelas M5/M15/M30/H1/H4/D1 sem olhar candle futuro
- `MultiTimeframeReplayCursor` para iterar candle por candle no timeframe base

## Fase 3 - Replay de features

Status: iniciado.

Para cada candle historico:

- calcular as mesmas features do Fusion
- gerar snapshots por ativo/timeframe
- preservar somente dados disponiveis ate aquele candle
- evitar lookahead bias

Concluido nesta fase:

- `BacktestFeatureReplay` para calcular features por timeframe usando somente candles alinhados ate o timestamp atual
- `FeatureSnapshot` com status, quantidade de barras, timestamp e features
- `FeatureReplayRunner` unindo cursor multi-timeframe e snapshots de features
- fallback legado equivalente ao `_calculate_features` do robo

## Fase 4 - Replay de modelos

Status: iniciado.

Carregar modelos reais e gerar:

- `p_buy`
- `p_sell`
- predicao
- modelo usado
- status do modelo
- confianca

Concluido nesta fase:

- `BacktestSingleModel` para carregar `model.pkl`, `scaler.pkl`, `meta.pkl`
- `BacktestModelRegistry` para carregar modelos por `symbol/timeframe`
- `ModelPredictionSnapshot` com `p_buy`, `p_sell`, prediction e status
- `ModelReplayRunner` para aplicar os modelos sobre `FeatureReplayFrame`

## Fase 5 - Replay das estrategias reais

Executar:

- strategy1
- strategy2
- strategy3
- strategy4
- strategy5
- strategy6

Cada estrategia deve receber:

- contexto historico
- features disponiveis
- approved model quando aplicavel
- cooldown simulado
- posicoes simuladas
- exposure simulada

## Fase 6 - Replay dos filtros institucionais

Executar no historico:

- EMA
- candle/preco
- macro fluxo
- market regime
- market structure
- volatility
- session
- context
- portfolio exposure
- correlacao
- risk engine
- consensus
- opportunity
- AI advisor opcional/mock

## Fase 7 - Execucao simulada

Quando a decisao final for `ALLOW`:

- abrir ordem simulada
- preencher ordem conforme OHLC
- aplicar spread/slippage/comissao
- acompanhar SL/TP/trailing
- fechar por stop, alvo, trailing, sinal oposto ou fim do periodo

## Fase 8 - Auditoria de decisao

Cada candle deve gerar eventos:

- `SIGNAL`
- `DECISION`
- `ORDER_REQUEST`
- `ORDER_RESULT`
- `POSITION_UPDATE`
- `RISK_ALERT`
- `ENGINE_RESULT`

Cada decisao deve registrar:

- fatores positivos
- fatores negativos
- warnings
- engines alinhadas
- engines conflitantes
- motivo de bloqueio
- motivo de liberacao

## Fase 9 - Integracao Qt

Adicionar modo:

- `Ferramentas > Backtest Real do Fusion`

Visualizar:

- candles em replay
- probabilidades reais por timeframe
- decisoes `ALLOW/BLOCK`
- motivos
- ordens simuladas
- trailing
- metricas
- camadas institucionais
- eventos de noticia

## Fase 10 - Metricas

Calcular:

- lucro/prejuizo
- win rate
- payoff
- profit factor
- drawdown
- max consecutive loss
- exposure medio
- expectativa por trade
- resultado por ativo
- resultado por estrategia
- resultado por timeframe
- resultado por regime
- resultado por evento/noticia

## Fase 11 - Comparacao em massa

Permitir testar:

- uma estrategia
- todas as estrategias
- um ativo
- todos os ativos
- um timeframe
- todos os timeframes
- ranking por performance

## Fase 12 - Substituir proxies

Depois que o motor real estiver validado:

- manter proxies apenas como modo didatico
- usar backtest real como padrao
- comparar proxy vs real para detectar divergencia
