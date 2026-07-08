# Item 3 - Decisao de Promocao Shadow -> Block

Base:

- Fonte: `reports/shadow_engine_report/shadow_engine_events_20260521_tail300.csv`
- Fonte auxiliar: `reports/shadow_engine_report/shadow_engine_engines_20260521_tail300.csv`
- Eventos: 300
- Decisoes:
  - BLOCK: 298
  - ALLOW: 2
- Tradeability medio: 0.427

## Decisao Geral

Nenhum engine novo deve sair de `shadow` para `block` neste momento.

Motivo:

- A amostra recente tem somente 2 entradas permitidas.
- Ainda nao existe resultado posterior suficiente para provar que os alertas shadow melhoram expectativa.
- `opportunity_engine` marcou muitos eventos como `tradable`, mas varios tinham risco forte de portfolio, macro ou correlacao.
- `market_structure` esta gerando muitos alertas e precisa calibracao por ativo/timeframe.
- `confidence_calibration` ainda aparece majoritariamente como `no_profile`.

## Decisao Por Engine

### market_structure

Status recomendado: manter `shadow`.

Evidencia:

- 268 eventos com engine registrado.
- 229 alertas em `shadow`.
- Motivos recorrentes: consolidacao, compressao, volatilidade baixa.

Risco de promover agora:

- Bloquearia eventos demais sem prova de ganho.
- Precisa calibracao por ativo/timeframe antes.

### market_regime

Status recomendado: manter `shadow`.

Evidencia:

- Estados principais:
  - TRANSITIONAL: 158
  - TREND: 54
  - RANGE: 45
  - EXPANSION: 31
  - PANIC_VOLATILITY: 12

Risco de promover agora:

- Regime ainda esta mais informativo do que decisorio.
- Precisa validar por resultado posterior.

### volatility_engine

Status recomendado: manter `shadow`.

Evidencia:

- Estados principais:
  - NORMAL: 142
  - LOW_INTRABAR_RANGE: 69
  - EXPANSION: 44
  - COMPRESSION: 33
  - PANIC_VOLATILITY: 12

Risco de promover agora:

- Volatilidade deve modular risco/tamanho, nao bloquear diretamente sem calibracao.

### session_context

Status recomendado: manter `shadow`.

Evidencia:

- 300 eventos em sessao New York.
- Nao ha diversidade suficiente de sessoes neste recorte.

Risco de promover agora:

- Sem comparacao com Asia, London, rollover e baixa liquidez.

### portfolio_exposure

Status recomendado: manter `shadow`, mas e o principal candidato a virar protecao real depois de calibracao.

Evidencia:

- `currency_overexposure`: 260
- `currency_warning`: 21
- Muitos eventos apontam exposicao AUD elevada e varias posicoes negativas.

Risco de promover agora:

- Pode bloquear praticamente tudo enquanto a carteira estiver concentrada.
- Antes precisa definir limites por moeda, cluster e direcao.

### market_briefing

Status recomendado: manter `shadow`.

Evidencia:

- 300 eventos `ok`.
- Neste recorte nao houve restricao ativa relevante.

Risco de promover agora:

- Sem eventos suficientes de bloqueio/moderacao para validar.

### entry_timing

Status recomendado: manter `shadow`.

Evidencia:

- `ok`: 236
- `validated_breakout_buy`: 15
- `avoid_selling_bottom`: 14
- `avoid_buying_top`: 3

Risco de promover agora:

- Parece promissor, mas ainda faltam exemplos suficientes de topo/fundo evitado e resultado posterior.

### context_engine

Status recomendado: manter `shadow`.

Evidencia:

- `conflicted`: 103
- `mixed`: 103
- `weak`: 52

Risco de promover agora:

- Ficaria restritivo demais com o estado atual do portfolio.

### confidence_calibration

Status recomendado: manter `shadow`.

Evidencia:

- `no_profile`: 243
- `calibrated`: 15

Risco de promover agora:

- Cobertura historica insuficiente.
- Precisa gerar mais perfis por ativo/timeframe/side.

### consensus_engine

Status recomendado: manter `shadow`.

Evidencia:

- `weak`: 113
- `moderate`: 80
- `conflicted`: 52
- `strong_consensus`: 13

Risco de promover agora:

- Ainda e agregador diagnostico.
- Precisa calibrar pesos antes de virar bloqueio.

### opportunity_engine

Status recomendado: manter `shadow`.

Evidencia:

- `tradable`: 162
- `conflicted`: 52
- `marginal`: 44

Risco de promover agora:

- Esta permissivo demais em alguns cenarios de risco.
- Deve penalizar mais `portfolio_exposure`, `portfolio_correlation`, `macro_flow` e `context_engine`.

## Candidatos Para Promocao Futura

Ordem recomendada:

1. `portfolio_exposure`
   - Primeiro como limite parcial ou reducao de tamanho.
   - Nao como bloqueio absoluto imediato.

2. `entry_timing`
   - Bloquear apenas `avoid_buying_top` e `avoid_selling_bottom` quando nao houver BOS/breakout validado.

3. `market_briefing`
   - Promover apenas regras de risco `EXTREMO`, com validade diaria e revisao manual.

4. `consensus_engine`
   - Usar inicialmente para reduzir lote quando `conflicted`, nao bloquear.

5. `opportunity_engine`
   - So promover depois de recalibrar pesos e validar forward.

## Conclusao do Item 3

Item 3 concluido.

Decisao: manter todos os engines novos em `shadow`.

Proximo passo recomendado:

- Calibrar o `opportunity_engine` para reduzir falso `tradable` quando portfolio, correlacao, macro fluxo ou contexto estiverem ruins.

