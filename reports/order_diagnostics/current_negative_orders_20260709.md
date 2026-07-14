# Diagnostico das ordens negativas abertas

Base consultada:
- `logs/oms/oms_snapshot_20260709.json`
- `logs/order_lifecycle/order_lifecycle_20260707.jsonl`
- `logs/order_lifecycle/order_lifecycle_20260708.jsonl`
- `logs/order_lifecycle/order_lifecycle_20260709.jsonl`
- `logs/decision_audit/decision_audit_20260707.jsonl`
- `logs/decision_audit/decision_audit_20260708.jsonl`
- `runtime/market_data/latest_candles/GBPJPY_M15.json`
- `runtime/market_data/latest_candles/EURUSD_H4.json`

Snapshot analisado: `2026-07-09T13:45:34`.

## Resumo

| Posicao | Ativo | Direcao | Timeframe | Abertura | Preco entrada | Preco snapshot | PnL snapshot | Diagnostico curto |
|---|---|---:|---:|---|---:|---:|---:|---|
| 82415422 | GBPJPY | SELL | M15 | 2026-07-07 21:09:50 | 216.668 | 217.662 | -6.12 | Entrada permitida apesar de confianca baixa, conflitos macro/estruturais contra SELL e alerta alto de JPY carry/intervencao. |
| 82560900 | EURUSD | SELL | H4 | 2026-07-08 12:45:05 | 1.13922 | 1.14414 | -4.92 | Entrada vendida no fundo/rompimento, com macro alinhado para SELL, mas havia consenso de timeframes contra BUY e aviso de 3 posicoes negativas. |

## GBPJPY SELL M15 - posicao 82415422

### Linha do tempo

- `2026-07-07T21:09:50.410940`: `ORDER_REQUEST` para `GBPJPY M15 strategy1 SELL`, motivo `pre_order_checks_ok`.
- `2026-07-07T21:09:50.898827`: `ORDER_RESULT FILLED`, preco `216.668`, motivo `ORDEM_EXECUTADA`, magic `1015`.
- `2026-07-07T21:09:50.899827`: primeira atualizacao de posicao, PnL `-0.20`.
- `2026-07-08T10:32:01`: PnL ja estava em `-3.35`.
- `2026-07-08T12:45:05`: PnL estava em `-4.36`.
- `2026-07-09T13:45:34`: PnL estava em `-6.12`.

### Decisao que abriu a ordem

- Decisao: `ALLOW`.
- Motivo: `pre_order_checks_ok`.
- Probabilidades do modelo: `p_sell=0.6481`, `p_buy=0.1372`.
- Score final XAI: `0.5428`.
- Banda de confianca: `baixa`.
- Tradeability: `0.5487`.
- Consenso: `0.3325`.
- Conflito: `0.2601`.
- Multiplicador de posicao: `0.5`.

### O que favorecia a entrada

- `timeframe_consensus:consenso_alinhado:SELL`.
- `risk_engine:risco_operacional_normal`.
- `ema_alignment:emas_alinhadas`.
- `candle_price:preco_candle_confirmado`.
- `entry_timing:entrada_sem_extremo_topo_fundo`.
- `portfolio_exposure:exposicao_portfolio_ok`.
- `market_structure:market_structure_ok`.
- `feature_engineering:feature_quality_ok`.

### O que dizia para tomar cuidado ou nao entrar

- `macro_flow:macro_contra:BUY`.
- `market_alignment:fluxo_contra:BUY`.
- `market_alignment:estrutura_h4_d1_contra`.
- `market_alignment:h1_h4_nao_confirma`.
- `market_alignment:pullback_contra_estrutura`.
- `confidence_calibration:probabilidade_calibrada_menor`.
- `context_brain:conflito_estrutural:macro_flow+market_alignment`.
- Briefing expirado.
- `jpy_carry_intervention_watch:ALTO`.
- `market_regime:regime_transicional`.
- Sessao Asia/transicao de sessao.
- Ativo ruidoso para scalping.
- `execution_engine:corpo_fraco`.

### Topo ou fundo

Pela auditoria do proprio motor, nao foi classificada como topo/fundo: `entry_timing:entrada_sem_extremo_topo_fundo`.

Observacao: no cache `GBPJPY_M15`, ha indicio de desalinhamento de horario entre candle e evento, porque o preco executado `216.668` nao cabe no candle marcado `2026-07-07 21:00:00`. Entao a classificacao mais confiavel aqui e a do proprio `entry_timing` gravado na decisao.

### Por que ficou negativa

A venda pegou um movimento de alta contra a posicao. Do preco de entrada `216.668` ao snapshot `217.662`, o mercado andou aproximadamente `0.994` contra o SELL. O risco principal ja estava visivel na abertura: SELL liberado com confianca baixa, conflito macro/estrutura contra BUY, regime transicional e alerta alto em JPY.

## EURUSD SELL H4 - posicao 82560900

### Linha do tempo

- `2026-07-08T12:45:05.091035`: `ORDER_REQUEST` para `EURUSD H4 strategy1 SELL`, motivo `pre_order_checks_ok`.
- `2026-07-08T12:45:05.299379`: `ORDER_RESULT FILLED`, preco `1.13922`, motivo `ORDEM_EXECUTADA`, magic `10240`.
- `2026-07-08T12:45:05.300379`: primeira atualizacao de posicao, PnL `-0.15`.
- `2026-07-08T23:02:33`: PnL estava em `-3.46`.
- `2026-07-09T13:03:09`: PnL estava em `-4.84`.
- `2026-07-09T13:45:34`: PnL estava em `-4.92`.

### Decisao que abriu a ordem

- Decisao: `ALLOW`.
- Motivo: `pre_order_checks_ok`.
- Probabilidades do modelo: `p_sell=0.6371`, `p_buy=0.3562`.
- Score final XAI: `0.6664`.
- Banda de confianca: `media`.
- Tradeability: `0.6336`.
- Consenso: `0.5263`.
- Conflito: `0.0699`.
- Multiplicador de posicao: `1.0`.

### O que favorecia a entrada

- `market_briefing:macro_bias:SELL`.
- `macro_flow:macro_alinhado:SELL`.
- `market_alignment:fluxo_alinhado:SELL`.
- `entry_timing:venda_fundo_permitida_por_bos_ou_breakout`.
- `execution_engine:breakout_quality_ok`.
- `execution_engine:candle_rejection_aligned`.
- `candle_price:preco_candle_confirmado`.
- `ema_alignment:emas_alinhadas`.
- `confidence_calibration:probabilidade_calibrada_melhor_ou_igual`.
- `feature_engineering:feature_quality_ok`.

### O que dizia para tomar cuidado ou nao entrar

- `timeframe_consensus:consenso_contra:BUY`.
- `timeframe_consensus:estrutura_h4_d1_contra`.
- `timeframe_consensus:h1_h4_nao_confirma`.
- `risk_engine:muitas_posicoes:3`.
- `risk_engine:muitas_posicoes_negativas:3`.
- `portfolio_exposure:posicoes_negativas:3`.
- `context_brain:conflito_estrutural:timeframe_consensus`.
- Briefing expirado.
- Regime transicional.
- `execution_engine:corpo_fraco`.

### Topo ou fundo

Foi uma venda perto do fundo recente, mas o motor permitiu por interpretar como BOS/breakout:

- Fator registrado: `entry_timing:venda_fundo_permitida_por_bos_ou_breakout`.
- Candle H4 de entrada no cache: `2026-07-08 09:00`, `high=1.14141`, `low=1.13923`, `close=1.13955`.
- Entrada: `1.13922`, praticamente no fundo do candle/estrutura local.
- Range de 24h consultado: `low=1.13906`, `high=1.14413`.
- Posicao relativa da entrada no range: aproximadamente `3.2%` acima da minima.

### Por que ficou negativa

A entrada vendeu muito perto da minima local esperando continuidade de rompimento. O mercado reverteu/subiu depois: de `1.13922` para `1.14414` no snapshot, movimento adverso de aproximadamente `0.00492` contra o SELL. O sinal tecnico/macro estava razoavelmente alinhado, mas havia um alerta importante que nao bloqueou a ordem: o sistema ja reconhecia `3` posicoes negativas e consenso multi-timeframe contra BUY.

## Conclusao operacional

As duas ordens foram abertas porque passaram em `pre_order_checks_ok`, mas os alertas eram diferentes:

- `GBPJPY`: entrada mais fraca. O proprio XAI marcou confianca baixa, muitos conflitos contra SELL e alerta alto de JPY. A ordem parece ter sido liberada por sinais locais/EMA/risco, apesar do contexto maior ruim.
- `EURUSD`: entrada tecnicamente mais justificavel, mas agressiva. Foi uma venda no fundo autorizada como breakout/BOS. O problema foi reversao logo depois, com agravante de exposicao: ja havia muitas posicoes e posicoes negativas.

Pontos para revisar no robo:

1. Bloquear ou reduzir mais quando `confidence_band=baixa` e houver `macro_flow` + `market_alignment` contra a direcao.
2. Transformar `jpy_carry_intervention_watch:ALTO` em bloqueio ou lote minimo para pares JPY.
3. Bloquear novas ordens quando `risk_engine:muitas_posicoes_negativas` estiver ativo.
4. Exigir confirmacao extra quando `entry_timing` permitir `venda_fundo_permitida_por_bos_ou_breakout`, porque esse tipo de entrada pode ser falso rompimento.
5. Atualizar/validar o `market_briefing`, pois as duas entradas tinham aviso de briefing expirado.
