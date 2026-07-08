# Item 9 - Meta-Model Ensemble Engine v1

## Objetivo

Adicionar uma camada institucional em `shadow` para avaliar a qualidade do modelo/ensemble que gerou o sinal, sem alterar predicao, lote, TP/SL, trailing ou envio de ordem.

## Implementado

- Criado `fusion/engines/meta_model.py`.
- Criado `MetaModelEnsembleEngine` com leitura do `approved_status` dos ensembles aprovados.
- O engine calcula:
  - quantidade de experts ativos;
  - peso BUY/SELL dos votos;
  - peso liquido do ensemble;
  - consenso do ensemble com a direcao candidata;
  - conflito entre experts;
  - concentracao em um unico expert;
  - confianca media dos experts ativos.
- Para modelos individuais sem ensemble, o engine registra `single_model` com score conservador.
- Integrado em `_execute_strategy_order(...)`, antes dos demais filtros globais.
- Integrado na estrategia base para passar `model`, `approved_model` e `approved_status`.
- Adicionado ao `context_engine`, `consensus_engine` e `opportunity_engine`.
- Atualizado `tools/build_shadow_engine_report.py` para reconhecer os novos estados.
- Criado `tools/check_meta_model_ensemble.py`.

## Estados

- `ensemble_ok`: votos ativos suficientes e alinhados com o sinal.
- `weak_ensemble`: poucos experts ativos ou score fraco.
- `conflicted_ensemble`: votos relevantes contra a direcao candidata.
- `no_active_votes`: ensemble presente, mas sem voto ativo aproveitavel.
- `single_model`: sinal veio de modelo unico, sem meta-ensemble.
- `no_model_context`: tentativa sem contexto de modelo.

## Configuracao

```yaml
entry_filters:
  meta_model_ensemble:
    enabled: true
    mode: "shadow"
    min_active_members: 2
    max_conflict_ratio: 0.35
    max_vote_concentration: 0.70
    min_avg_confidence: 0.45
    single_model_score: 0.45
```

## Status Operacional

- Permanece em `shadow`.
- Nao bloqueia ordens.
- Serve para medir se o sinal esta vindo de um ensemble robusto, fraco ou conflitado.

## Proximo Uso

Depois de uma sessao de observacao, gerar relatorio dos eventos `ALLOW` e `BLOCK` para comparar:

- sinais com `ensemble_ok`;
- sinais com `weak_ensemble`;
- sinais com `conflicted_ensemble`;
- resultado posterior por ativo/timeframe/estrategia.
