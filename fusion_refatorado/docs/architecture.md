# Arquitetura Proposta

## Objetivo

Transformar o FUSION_V2 em um nucleo unico com:

- treino por ativo/timeframe;
- treino por experts/shards;
- features Alpha/Forex unificadas;
- modelos versionados com metadata;
- compatibilidade com backtest e execucao MT5.

## Camadas

1. Dados
   - Entrada: `data/parquet/<timeframe>/<symbol>.parquet`.
   - Alternativa: shards em `BACKUP/BUILD_MODELS/shards_v4` e `BACKUP/data_csv/SHARD_*.parquet`.
   - Padrao minimo: `open`, `high`, `low`, `close`, `tick_volume` ou `volume`.

2. Features
   - `fusion_best.features.build_feature_matrix`.
   - `fusion_best.specialists.build_specialist_features`.
   - Familias: returns, trend, volatility, volume/liquidity, range/structure, candle, alpha/technical.
   - Especialistas: liquidity, microstructure, momentum, regime, structure, volatility.
   - Sem dependencia obrigatoria de QLib.

3. Targets
   - Classificacao multiclass: `0=hold`, `1=buy`, `2=sell`.
   - Threshold por volatilidade/ativo/timeframe.
   - Split temporal, nunca shuffle.

4. Treinamento
   - `training.train_single_symbol_timeframe`: modelo unico para um ativo/timeframe.
   - `experts.train_shard_experts`: modelos por shard/grupo de ativos.
   - Modelo default: LightGBM com early stopping, class_weight balanced e metadata.

5. Registro de Modelos
   - Pasta por modelo.
   - Artefatos: `model.pkl`, `scaler.pkl`, `meta.json`.
   - Indice consolidado: `models_index.csv`.

6. Sinal
   - Previsao retorna direcao, probabilidade, confidence e thresholds.
   - `fusion_best.signals.TradingSignal` padroniza direcao, confidence, componentes, SL e TP.
   - `fusion_best.risk.RiskManager` aplica RR, EV, limite de risco e lote em modo staging/backtest.
   - Camada futura: filtros OMNIS de tendencia, fibonacci, inside bar e trailing MT5.

7. Validacao
   - `fusion_best.backtesting.simple_signal_backtest` faz teste causal simples por horizonte fixo.
   - `legacy_models_inventory.csv` lista modelos prontos para priorizar importacao e comparacao.

## Decisao sobre modelos prontos

Os modelos prontos do BACKUP sao valiosos como baselines, mas devem entrar como `imported_models/` ou serem registrados com metadata antes de uso real. O melhor fluxo e retreinar/validar com os dados atuais do FUSION_V2 e promover apenas os vencedores.
