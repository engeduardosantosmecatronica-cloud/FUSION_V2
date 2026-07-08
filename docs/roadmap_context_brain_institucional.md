# Roadmap Context Brain Institucional

Objetivo: transformar as camadas existentes do Fusion em uma leitura contextual unica, com score, direcao, risco e motivos claros por ativo/timeframe.

## Fase 1 - Orquestrador Context Brain

Status: iniciado.

- Criar `ContextBrainEngine` como camada final de leitura institucional.
- Consumir outputs ja existentes: `market_alignment`, `timeframe_consensus`, `macro_flow`, `market_structure`, `market_regime`, `volatility_engine`, `entry_timing`, `execution_engine`, `risk_engine`, `context_engine`, `consensus_engine` e `opportunity_engine`.
- Produzir classificacao: `FORTE BUY`, `BUY`, `NEUTRO`, `SELL`, `FORTE SELL`.
- Produzir estados: `institutional_aligned`, `mixed_context`, `weak_context`, `structural_conflict`, `blocked_context`.
- Rodar inicialmente em `shadow`, depois migrar para `block` quando estabilizado.

## Fase 2 - Ranking de Forca Relativa de Moedas

Status: parcial.

- Consolidar o `currency_strength` atual em ranking historico por moeda.
- Gerar scores normalizados por moeda: `NZD=8.7`, `EUR=2.1`, `JPY=3.0`.
- Salvar historico em `reports/currency_strength/`.
- Expor no dashboard textual e depois no painel MT5/plataforma.
- Usar diferenca `base_strength - quote_strength` como fator forte do Context Brain.

## Fase 3 - Estrutura Multi-Timeframe

Status: parcial.

- Consolidar BOS, CHOCH, HH/HL, LH/LL, liquidez, breakouts e compressao em uma leitura simples por timeframe.
- Gerar saida padrao: `bullish_structure`, `bearish_structure`, `pullback`, `reversal_risk`, `range`.
- Dar prioridade estrutural a H4/D1 e usar M15/M30 para timing.

## Fase 4 - Momentum e Exaustao

Status: parcial.

- Consolidar RSI, MACD, ADX, ATR, volume, delta proxy e candle pressure em `momentum_score`.
- Separar momentum de continuacao de momentum de exaustao.
- Criar alertas: `short_squeeze_risk`, `long_squeeze_risk`, `exhaustion_buy`, `exhaustion_sell`.

## Fase 5 - Regime e Selecao de Estrategia

Status: parcial.

- Usar `TREND`, `RANGE`, `EXPANSION`, `PANIC_VOLATILITY` e `TRANSITIONAL` para escolher tipo de estrategia.
- Em tendencia: priorizar continuacao/trend following.
- Em range: evitar rompimentos fracos e priorizar mean reversion apenas se estrategia permitir.
- Em panico/expansao extrema: reduzir lote ou bloquear.

## Fase 6 - Intermarket Real

Status: falta implementar.

- Incluir DXY, ouro, petroleo, indices, VIX, yields/bonds e crypto.
- Criar `intermarket_score`.
- Detectar ambiente `risk_on`, `risk_off`, `usd_flow`, `commodity_flow`, `crypto_flow`.
- Salvar logs em `reports/intermarket/`.

## Fase 7 - Probabilidade Contextual

Status: falta consolidar.

- Gerar probabilidades finais:
  - `trend_continuation_probability`
  - `pullback_probability`
  - `reversal_probability`
  - `squeeze_risk`
  - `tradeability`
- Trocar leitura binaria por leitura contextual:
  - direcao principal;
  - confianca;
  - risco;
  - motivo dominante;
  - condicao de invalidez.

## Fase 8 - Visualizacao e Auditoria

Status: falta implementar.

- Exportar Context Brain para CSV/JSON.
- Mostrar no dashboard textual.
- Enviar para painel MT5.
- Exibir na plataforma desktop como dock ou tela de analise.
- Comparar historicamente Context Brain vs resultado real do preco.

## Prioridade Atual

1. Implementar `ContextBrainEngine`.
2. Ligar em `entry_filters.context_brain`.
3. Rodar em `shadow`.
4. Validar logs por algumas horas.
5. Depois decidir se vira `block`.
