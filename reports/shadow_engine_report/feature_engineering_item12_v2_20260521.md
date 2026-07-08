# Item 12 - Feature Engineering v2

## Objetivo

Criar uma camada institucional de qualidade e auditoria de features, sem alterar sinais ou envio de ordens.

Esta etapa organiza a engenharia de features como um componente observavel do motor de decisao, em vez de deixar as features apenas espalhadas em modelos, backtests e filtros.

## Implementado

- Criado `fusion/engines/feature_engineering.py`.
- Criado `tools/check_feature_engineering.py`.
- Integrado em `_execute_strategy_order(...)` apos `market_structure` e antes de `entry_timing`.
- Integrado em `_run_shadow_diagnostics(...)`.
- Adicionado ao `context_engine`, `consensus_engine` e `opportunity_engine`.
- Atualizado `config/fusion_config.yaml`.
- Atualizado `tools/build_shadow_engine_report.py`.

## Familias Auditadas

- `candle_anatomy`
- `volatility`
- `volume_microstructure`
- `trend_momentum`
- `structure`
- `statistical`
- `temporal`

## Medidas Geradas

- `feature_coverage`
- `numeric_feature_count`
- `valid_numeric_feature_count`
- `family_scores`
- `family_floor`
- `weak_families`
- `critical_missing`
- `critical_score`
- `anomaly_flags`
- `latest_feature_time`

## Anomalias Detectadas

- volume climax;
- absorcao;
- empty market move;
- stop hunt;
- compressao/expansao;
- structure transition;
- reversal risk.

## Estados

- `feature_quality_ok`
- `feature_anomaly_context`
- `feature_quality_weak`
- `insufficient_features`
- `insufficient_data`

## Status

- Permanece em `shadow`.
- Nao bloqueia ordem.
- Nao altera modelo, lote, TP/SL ou trailing.

## Proxima Evolucao

- Criar catalogo persistente de features por familia.
- Medir feature coverage por ativo/timeframe.
- Usar `feature_quality_weak` para evitar inferencia em candles com dados ruins quando houver estatistica suficiente.
