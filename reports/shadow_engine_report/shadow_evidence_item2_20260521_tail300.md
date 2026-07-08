# Item 2 - Analise de Evidencia dos Engines Shadow

Base analisada:

- Fonte: `logs/decision_audit/decision_audit_20260521.jsonl`
- Recorte: ultimos 300 eventos
- Relatorio base: `reports/shadow_engine_report/shadow_engine_report_20260521_tail300.md`
- Eventos: 300
- Ativos: 14
- Engines analisados: 3049
- Decisoes:
  - BLOCK: 298
  - ALLOW: 2
- Eventos com alerta shadow: 287
- Tradeability medio: 0.427

## Principais Alertas

- `portfolio_exposure / currency_overexposure`: 260
- `market_structure / shadow`: 229
- `opportunity_engine / tradable`: 162
- `consensus_engine / weak`: 113
- `context_engine / conflicted`: 103
- `consensus_engine / moderate`: 80
- `consensus_engine / conflicted`: 52
- `context_engine / weak`: 52
- `opportunity_engine / conflicted`: 52
- `opportunity_engine / marginal`: 44

## Leituras Importantes

1. O sistema esta bloqueando quase tudo pelos filtros operacionais atuais.
   - 298 de 300 eventos foram `BLOCK`.
   - Principais motivos: macro fluxo, correlacao, candle, EMA e sem feature.

2. O portfolio esta em estado de risco elevado.
   - `portfolio_exposure` acusou `currency_overexposure` em 260 eventos.
   - Ha concentracao relevante em AUD e varias posicoes negativas simultaneas.
   - Esse engine parece ser o candidato mais importante para evolucao, mas precisa ser calibrado antes de virar bloqueio forte.

3. O `market_structure` ainda esta barulhento.
   - 229 alertas em 300 eventos.
   - Ele esta sinalizando muita compressao/consolidacao/volatilidade baixa.
   - Ainda nao deve virar `block` sem calibracao por ativo/timeframe.

4. O `consensus_engine` esta fazendo leitura util.
   - `weak`: 113
   - `moderate`: 80
   - `conflicted`: 52
   - `strong_consensus`: 13
   - Isso confirma que ele esta separando bem consenso fraco, moderado e conflito.

5. O `opportunity_engine` precisa de calibracao.
   - `tradable`: 162 eventos, mas muitos desses ainda foram bloqueados por macro/correlacao/EMA.
   - Isso indica que o score de oportunidade ainda esta valorizando timing/local de entrada mais do que risco de portfolio/macro.
   - Nao deve virar bloqueio nem liberador de ordem ainda.

6. Entradas permitidas com alerta shadow:
   - 2 entradas `ALLOW`, ambas em `EURNZD D1 SELL`.
   - Tradeability:
     - 0.434
     - 0.445
   - Ambas tiveram alertas de `portfolio_exposure`, `market_structure`, `consensus_engine` e `opportunity_engine`.
   - Isso pede acompanhamento posterior do resultado dessas ordens antes de promover filtros.

7. Bloqueios com tradeability alto:
   - 8 bloqueios com `tradeability_score >= 0.55`.
   - Principais casos:
     - `AUDNZD H4 BUY` bloqueado por `ema_nao_alinhada`.
     - `CADJPY M30 SELL` bloqueado por `correlacao_prejuizo`.
   - Esses casos nao indicam erro do bloqueio. Pelo contrario: mostram que oportunidade local pode parecer boa enquanto risco de contexto/portfolio ainda e ruim.

## Conclusao do Item 2

Item 2 concluido.

Nenhum engine novo deve sair de `shadow` agora.

Ordem recomendada de evolucao:

1. Manter tudo em `shadow`.
2. Melhorar calibracao do `opportunity_engine`, aumentando penalidade para:
   - `portfolio_exposure`;
   - `portfolio_correlation`;
   - `macro_flow`;
   - `context_engine conflicted/weak`.
3. Criar analise posterior das 2 ordens `ALLOW` em EURNZD D1.
4. Criar relatorio por ativo/timeframe para saber onde `market_structure` e confiavel.
5. So depois considerar promover algum filtro para `block`.

