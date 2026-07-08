# Item 11 - Opportunity Engine v2

## Objetivo

Separar de forma mais institucional a probabilidade direcional da qualidade operacional da oportunidade.

O sistema pode ter um sinal direcional bom, mas ainda assim a oportunidade pode ser ruim por execucao, risco, contexto, sessao, estrutura ou conflito entre motores.

## Implementado

- Expandido `fusion/engines/opportunity.py`.
- Criado `tools/check_opportunity_engine.py`.
- Atualizado `config/fusion_config.yaml`.
- O engine agora calcula sub-scores:
  - `direction_probability`;
  - `execution_score`;
  - `context_score`;
  - `risk_score`;
  - `model_quality_score`;
  - `consensus_score`.
- O score final agora recebe penalidades por:
  - conflitos severos;
  - fatores negativos;
  - warnings;
  - qualidade minima muito baixa em qualquer pilar.

## Estados

- `high_quality`: oportunidade forte, sem conflito severo.
- `tradable`: oportunidade aceitavel.
- `marginal`: oportunidade fraca, mas ainda observavel.
- `poor`: oportunidade ruim.
- `conflicted`: conflito alto entre motores.
- `insufficient_context`: sem componentes suficientes.

## Status

- Permanece em `shadow`.
- Nao bloqueia ordem.
- Nao altera lote.
- Serve para calibrar futuramente reducao de lote ou bloqueio por baixa qualidade operacional.

## Como Usar Na Analise

No `decision_audit`, observar:

- `features.tradeability_score`;
- `features.components.execution_score`;
- `features.components.context_score`;
- `features.components.risk_score`;
- `features.components.model_quality_score`;
- `features.quality_floor`;
- `features.penalty`;
- `features.severe_conflict_count`.

## Proxima Evolucao

Depois de alguns ciclos:

- medir ordens `ALLOW` por `state`;
- comparar `high_quality` vs `marginal` vs `poor`;
- definir se `poor` deve virar bloqueio;
- definir se `marginal` deve reduzir lote.
