# Roadmap: News Impact Engine

Objetivo: mapear eventos macro e noticias historicas que tiveram impacto relevante nos ativos, para que o FUSION consiga explicar movimentos, filtrar entradas em horarios perigosos e enriquecer o backtest real.

## 1. Fontes de eventos

- Calendario economico historico: CPI, NFP, FOMC, juros, PMI, PIB, retail sales, unemployment, discursos.
- Noticias nao programadas: geopolitica, crise bancaria, intervencao cambial, downgrade, sancoes, eventos de risco.
- Fontes candidatas: Trading Economics, Finnhub, Alpha Vantage, FRED, bancos centrais, calendario proprio importado por CSV.

## 2. Schema de evento

Campos minimos:

- timestamp
- country
- currency
- asset
- event_type
- title
- actual
- forecast
- previous
- surprise_score
- sentiment
- expected_direction
- observed_direction
- impact_strength
- confidence
- source

## 3. Medicao de impacto

Para cada evento, calcular impacto em janelas:

- 1m
- 5m
- 15m
- 1h
- 4h
- 1D

Metricas:

- retorno percentual
- retorno em pips/pontos
- range pos-noticia
- spike
- reversao
- volatilidade anormal
- rompimento estrutural
- sweep de liquidez

## 4. Classificacao macro

Gerar interpretacoes:

- bullish USD
- bearish USD
- bullish XAUUSD
- bearish XAUUSD
- risk-on
- risk-off
- hawkish
- dovish
- inflationary
- disinflationary

## 5. Integração com o Fusion

Criar:

- `fusion/engines/news_impact.py`
- `fusion/data/news_events.py`
- `data/news_events/`
- `reports/news_impact/`

Novos motivos explicaveis:

- `news_risk_high`
- `news_event_nearby`
- `news_direction_conflict`
- `post_news_spike`
- `post_news_reversal_risk`
- `macro_event_supports_trade`
- `macro_event_blocks_trade`

## 6. Backtest real

No replay historico, o motor deve:

- localizar eventos proximos ao candle atual
- medir se o ativo reagiu conforme esperado
- anexar evento ao `DecisionAudit`
- permitir comparar trades com e sem filtro de noticia

## 7. Dashboard/terminal

Exibir no grafico:

- marcador vertical da noticia
- titulo resumido
- moeda afetada
- impacto esperado
- impacto observado
- score de risco

## 8. Cuidados estatisticos

- Nao afirmar causalidade absoluta.
- Usar "evento temporalmente associado".
- Evitar lookahead: no backtest, a noticia so pode ser conhecida a partir do timestamp real.
- Separar evento programado de noticia inesperada.
- Manter fonte e timestamp auditaveis.

