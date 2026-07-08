# Inventario do BACKUP

## ALPHAEDU

Melhor conteudo:

- `expressions/alpha158_optimized.py`: dicionario de 158 features com retornos, medias, volatilidade, correlacao com volume, high/low rolling, candle anatomy, ATR e lags.
- `06_feature_parameter_scan.py`: ideia boa para varrer janelas por familia de feature e medir impacto incremental com LightGBM.
- `models/*/*_model.py`: especialistas por dominio: liquidez, microestrutura, momentum, regime, estrutura e volatilidade.
- `04_leakage_check.py`, `backtest_top30.py`, `compare_feature_sets.py`: validacao, comparacao e controle contra leakage.

Uso no FUSION_V2:

- Manter as expressoes como catalogo de features.
- Usar a varredura de parametros para otimizar janelas por ativo/timeframe.
- Transformar especialistas em feature families ou modelos experts.

## BUILD_MODELS

Melhor conteudo:

- `tools/treino_majors.py`: treino massivo de especialistas por shard com LightGBM multiclass, `class_weight=balanced`, early stopping e split temporal.
- `shards_v4/SHARD_*.parquet`: datasets prontos por grupo de ativos e timeframe.
- `models_pkl/model_SHARD_*.pkl`: modelos prontos por grupo/timeframe.
- `genesis_global_model.pkl`, `genesis_scaler.pkl`, `genesis_model_meta.pkl`: modelo global ja serializado.

Uso no FUSION_V2:

- Adotar o conceito de expert por shard para criar modelos por familia: majors, crosses, metals, indexes, crypto, exotics.
- Salvar sempre modelo + scaler + metadata + indice.
- Evitar hardcode de `D:\Projeto_Python`; parametrizar caminhos.

Modelos encontrados no inventario gerado:

- 21 modelos `build_models_shard`.
- Shards grandes em parquet devem ser usados como fonte de retreino/validacao, nao copiados para o pacote Python.

## NEXUS

Melhor conteudo:

- `treinamento/01_principal_trainer.py`: treino de RandomForest, LightGBM, XGBoost e Ensemble.
- `treinamento_qlib/04_treinar_4_modelos.py`: quatro conjuntos: Alpha158, Alpha360, ExpressionEngine e FullIndicators.
- `nexus/features/features.py`: features Forex e engenharia de dados.
- `nexus/backtest/*`: estrategias de backtest comparaveis.
- `models/alpha158_best.joblib`: artefato pronto possivelmente util como baseline.

Uso no FUSION_V2:

- Incorporar treino multi-modelo como modo experimental.
- Usar Ensemble apenas quando o ganho for comprovado por backtest.
- Reaproveitar Alpha158/Alpha360 como conjuntos de features, nao como dependencia pesada de QLib.

Modelos encontrados no inventario gerado:

- 146 modelos `nexus_by_symbol`.
- 128 modelos `nexus_global_strategy`.

## OMNIS

Melhor conteudo:

- `trading_strategies/trading_strategies.py`: orquestracao de estrategias com Signal, confidence, stop loss/take profit e componentes.
- `utils/indicators.py`, `utils/fibonacci_filter.py`, `utils/insidebar_detector.py`, `utils/trend_alignment.py`: filtros praticos de trading.
- `utils/multiasset_model_loader.py`: ideia de loader multiativo.
- `training/train_all_models.py`: separacao por experts: volatilidade, trend, orderflow, suporte/resistencia, risco, reversal e meta-decision.
- `LOGICA_DE_TRADING.md`: regras de decisao e arquitetura operacional.

Uso no FUSION_V2:

- Usar o padrao de sinal estruturado e confidence.
- Separar modelo principal, filtros de entrada, risco e execution.
- Aproveitar experts como camadas de confirmacao e nao como scripts soltos.

## QLIB e PROJETO_QLIB_FINAL

Melhor conteudo:

- `03_treinar_modelo.py`, `04_treinamento_alpha158.py`, `treinar_modelo_balanceado.py`.
- `modelo_alpha158_sucesso.pkl`, `modelo_balanceado_lightgbm.pkl`, `omnis_model_eurusd_m5.pkl`.
- Scripts de preparacao e checagem de dados QLib.

Uso no FUSION_V2:

- Guardar scripts adaptados como referencia.
- Nao copiar `qlib-main` completo para o core do projeto.
- Preferir implementacao local das features essenciais.

## Inventario de Modelos

Foi gerado `docs/legacy_models_inventory.csv` com 1.042 artefatos de modelo:

- `data_hub_symbol`: 170
- `nexus_by_symbol`: 146
- `nexus_global_strategy`: 128
- `genesis_global`: 26
- `build_models_shard`: 21
- `qlib_baseline`: 16
- `unknown`: 535, ainda pendentes de classificacao fina
