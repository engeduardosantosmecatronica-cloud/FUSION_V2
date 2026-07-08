# FUSION_V2 Refatorado

Esta pasta consolida o melhor material encontrado em `BACKUP` para evoluir o FUSION_V2 sem misturar codigo legado, ambientes virtuais, copias completas do QLib ou modelos soltos.

## O que foi extraido

- `ALPHAEDU`: expressoes Alpha158/Forex, operadores, scanners de parametros e especialistas por regime, momentum, liquidez, microestrutura, estrutura e volatilidade.
- `BUILD_MODELS`: treino massivo por shards, modelos prontos por grupo de ativos/timeframe e datasets parquet ja agrupados.
- `NEXUS`: treino de 4 familias de modelos, handlers Forex, backtests e integracao QLib.
- `OMNIS`: arquitetura de experts, estrategias, filtros de entrada, risco, execution/trailing e loaders de modelos.
- `QLIB/PROJETO_QLIB_FINAL`: scripts uteis de preparacao, mineracao Alpha158, treino e uso de modelo, sem trazer a copia completa do framework.

## Estrutura

- `docs/backup_inventory.md`: mapa do que vale reaproveitar.
- `docs/architecture.md`: proposta de arquitetura para transformar o FUSION_V2 no nucleo principal.
- `fusion_best/features.py`: biblioteca unificada de features derivada de ALPHAEDU, NEXUS e BUILD_MODELS.
- `fusion_best/specialists.py`: especialistas causais reaproveitados de ALPHAEDU/OMNIS.
- `fusion_best/training.py`: treino de um modelo por ativo/timeframe.
- `fusion_best/experts.py`: treino de multiplos experts por shard/grupo de ativos.
- `fusion_best/model_registry.py`: padrao de salvamento, indice e leitura de modelos.
- `fusion_best/signals.py`: sinal estruturado com direcao, confianca e componentes.
- `fusion_best/risk.py`: versao limpa do gestor de risco OMNIS sem dependencia obrigatoria de MT5.
- `fusion_best/backtesting.py`: harness simples para validar sinais de forma causal.
- `fusion_best/legacy_inventory.py`: inventario de modelos prontos do BACKUP.

## Caminho recomendado

1. Rodar os presets de `pipelines/` em modo `--dry-run` para validar cada dataset.
2. Usar `pipelines/train_single_model.py` para criar o baseline por ativo/timeframe.
3. Usar `pipelines/train_experts.py` para treinar os especialistas de trend, volatility, candles, orderflow, risk e demais experts.
4. Usar `pipelines/train_fusion_ensemble.py` para gerar a configuracao inicial do ensemble.
5. Promover os melhores artefatos para producao apenas depois de backtest out-of-sample.

## Presets criados

- `pipelines/registry_inventory.py`: inventario consolidado de modelos, dados, docs e configs.
- `pipelines/train_single_model.py`: treino/dry-run de modelo unico.
- `pipelines/train_experts.py`: treino/dry-run de multiplos experts.
- `pipelines/train_fusion_ensemble.py`: cria preset inicial de ensemble a partir dos modelos disponiveis.

Validacoes feitas:

- `EURUSD_M5.csv` com 800 linhas em dry-run de modelo unico.
- `trend`, `volatility`, `candles`, `orderflow`, `risk` em dry-run de experts.
- Treino real completo de baseline single salvo em `models/fusion_single/EURUSD/M5`.
- Treino real completo dos 9 experts salvos em `models/fusion_experts/EURUSD/M5`:
  `trend`, `volatility`, `candles`, `orderflow`, `risk`, `sr`, `reversal`, `pullback`, `quant`.
- Ensemble inicial atualizado para priorizar modelos com metricas reais antes dos candidatos legados sem metadados.
- Backtest/calibracao EURUSD M5 criado em `reports/fusion_backtests/EURUSD/M5`.
- Ensemble calibrado aplicado em `models/fusion_ensemble/ensemble_config.json` com pesos atuais:
  `trend` 0.7172, `sr` 0.1377, `quant` 0.0923, `pullback` 0.0529; demais experts ficaram com peso zero nesta fatia.
- Walk-forward temporal criado em `reports/fusion_walkforward/EURUSD/M5` e modelos isolados em `models/fusion_walkforward/EURUSD/M5`.
- Ensemble walk-forward separado salvo em `models/fusion_ensemble/ensemble_walkforward_config.json`; nele apenas `trend` invertido passou com peso 1.0, ainda com baixo volume de trades.
- Lote M5 dos 23 simbolos solicitados concluido a partir de `data/parquet/M5`.
- Relatorio consolidado do lote: `reports/batch_runs/m5_requested_symbols_consolidated.csv`.
- Ensembles walk-forward por simbolo: `models/fusion_ensemble/*_M5_ensemble_walkforward_config.json`.
- Selecao conservadora de staging M5 criada em `reports/production_selection/M5_production_candidates.csv`.
- Registry de staging M5 criado em `models/production_registry/M5_approved_ensembles.json` com 7 ensembles aprovados.

## Observacao

Esta pasta nao substitui automaticamente o `fusion/` atual. Ela e uma area de staging/refatoracao para que os melhores blocos sejam incorporados com controle.
