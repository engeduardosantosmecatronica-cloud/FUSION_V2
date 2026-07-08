# Manifesto de Extracao do BACKUP

Este arquivo registra quais arquivos do `BACKUP` foram revisados, o que foi reaproveitado e se o original foi removido.

## Lote 1 - Especialistas ALPHAEDU

Extraido para:

- `fusion_refatorado/fusion_best/specialists.py`

Arquivos consumidos:

- `BACKUP/ALPHAEDU/models/liquidity/liquidity_model.py`
  - Reaproveitado: `liq_range`, `liq_sweep`, `liq_cluster`, `liq_pressure`.
  - Status: extraido, pronto para remover.
- `BACKUP/ALPHAEDU/models/microstructure/microstructure_model.py`
  - Reaproveitado: `spread_norm`, `tick_pressure`, `micro_vol`, `imbalance`.
  - Status: extraido, pronto para remover.
- `BACKUP/ALPHAEDU/models/momentum/momentum_model.py`
  - Reaproveitado: momentum multi-janela, momentum normalizado, aceleracao, ROC, impulse ratio e divergencia.
  - Status: extraido, pronto para remover.
- `BACKUP/ALPHAEDU/models/regime/regime_model.py`
  - Reaproveitado: volatilidade, trend score, range score e classificacao simples de regime.
  - Status: extraido, pronto para remover.
- `BACKUP/ALPHAEDU/models/structure/structure_model.py`
  - Reaproveitado: pivots causais, structure signal, trend, strength e break.
  - Ajuste feito: removido uso fragil de `df.loc[i]`, trocado por arrays/Series index-safe.
  - Status: extraido, pronto para remover.
- `BACKUP/ALPHAEDU/models/volatility/volatility_model.py`
  - Reaproveitado: ATR, z-score de volatilidade, regime, squeeze, expansao/contracao e score.
  - Status: extraido, pronto para remover.

## Lote 2 - Infraestrutura ja absorvida parcialmente

Extraido para:

- `fusion_refatorado/fusion_best/signals.py`
- `fusion_refatorado/fusion_best/risk.py`
- `fusion_refatorado/fusion_best/backtesting.py`
- `fusion_refatorado/fusion_best/legacy_inventory.py`

Arquivos usados como fonte de arquitetura, ainda nao removidos porque ha mais logica a extrair:

- `BACKUP/OMNIS_v1_20260304_134715/core/experts/base_expert.py`
- `BACKUP/OMNIS_v1_20260304_134715/core/experts/trend_master.py`
- `BACKUP/OMNIS_v1_20260304_134715/core/experts/volatility_gauge.py`
- `BACKUP/OMNIS_v1_20260304_134715/core/risk/risk_manager.py`
- `BACKUP/OMNIS_v1_20260304_134715/core/decision/decision_engine.py`
- `BACKUP/OMNIS_Copia/trading_strategies/trading_strategies.py`

## Lote 7 - Experts OMNIS

Extraido para:

- `fusion_refatorado/fusion_best/omnis_experts.py`
- `fusion_refatorado/fusion_best/dataset_builder.py`
- `fusion_refatorado/fusion_best/__init__.py`

Arquivos consumidos:

- `BACKUP/OMNIS_v1_20260304_134715/core/experts/base_expert.py`
  - Reaproveitado: contrato de especialista com `transform`, sinal e confianca por modulo, mas sem acoplamento ao pacote antigo.
- `BACKUP/OMNIS_v1_20260304_134715/core/experts/trend_master.py`
  - Reaproveitado: pilha de EMAs, distancia para medias, ADX/DI, RSI, MACD, `trend_signal` e `trend_confidence`.
- `BACKUP/OMNIS_v1_20260304_134715/core/experts/volatility_gauge.py`
  - Reaproveitado: ATR percentual, Bollinger/Keltner, squeeze, z-score de volatilidade, regimes e confianca.
- `BACKUP/OMNIS_v1_20260304_134715/core/experts/stats_quant.py`
  - Reaproveitado: media/desvio rolling, z-score, percentil rolling, probabilidade de tendencia e bias por hora.
- `BACKUP/OMNIS_v1_20260304_134715/core/experts/zone_mapper.py`
  - Reaproveitado: pivots, suporte/resistencia em 20/50/100, posicao no range, distancia de zonas e VWAP de zona.
- `BACKUP/OMNIS_v1_20260304_134715/core/experts/pullback_hunter.py`
  - Reaproveitado: pullback por EMA 9/21, Keltner, retracoes 38.2/50/61.8 e sinal de pullback.
- `BACKUP/OMNIS_v1_20260304_134715/core/experts/exhaustion_detector.py`
  - Reaproveitado: RSI, stochastic, MACD, sobrecompra/sobrevenda, divergencias, gaps, candles extremos e score de exaustao.
- `BACKUP/OMNIS_v1_20260304_134715/core/experts/flow_aggressor.py`
  - Reaproveitado: delta de candle, delta acumulado, z-score de delta, desequilibrio de volume, VWAP, agressao buy/sell e fluxo.
- `BACKUP/OMNIS_v1_20260304_134715/core/experts/pattern_trigger.py`
  - Reaproveitado: propriedades de candle, hammer, shooting star, engolfos, morning/evening star, piercing/dark cloud, inside/outside bar, doji, spinning top, score e confianca.
- `BACKUP/OMNIS_v1_20260304_134715/core/experts/risk_guardian.py`
  - Reaproveitado: VaR/CVaR, drawdown, Sharpe/Sortino/Calmar, MAE/MFE, eficiencia, win rate, expectancy, Kelly, position sizing e veto de trade.

Status: extraidos e validados em parquet real. `include_omnis_experts=True` agora ativa 141 features OMNIS no dataset final.

## Lote 8 - Decisao, confluencia e risco OMNIS

Extraido para:

- `fusion_refatorado/fusion_best/decision.py`
- `fusion_refatorado/fusion_best/risk.py`
- `fusion_refatorado/fusion_best/signals.py`
- `fusion_refatorado/fusion_best/__init__.py`

Arquivos consumidos:

- `BACKUP/OMNIS_v1_20260304_134715/core/decision/confluence_scorer.py`
  - Reaproveitado: confluencia por Fibonacci, suporte/resistencia, EMA200 e VWAP.
- `BACKUP/OMNIS_v1_20260304_134715/core/decision/decision_engine.py`
  - Reaproveitado: safe predict, alinhamento de features esperadas, voto ponderado por timeframe, veto por risco e filtro de melhoria de preco.
- `BACKUP/OMNIS_v1_20260304_134715/core/risk/risk_manager.py`
  - Reaproveitado: RR, EV, risco diario, lote minimo/maximo e bloqueios de trade sem dependencia do MetaTrader5.
- `BACKUP/OMNIS_v1_20260304_134715/core/risk/sl_tp_engine.py`
  - Reaproveitado: SL/TP fixo com stop-level e SL/TP dinamico por ATR.

Melhoria adicional:

- `fusion_best/__init__.py` passou a usar exports preguicosos para evitar importacao pesada quando somente um modulo especifico e necessario.

Status: extraidos e validados com teste integrado de sinal, voto meta, SL/TP e risco.

## Lote 9 - Treino por experts OMNIS

Extraido para:

- `fusion_refatorado/fusion_best/expert_training.py`
- `fusion_refatorado/fusion_best/__init__.py`

Arquivos consumidos:

- `BACKUP/OMNIS_v1_20260304_134715/training/objectives/train_trend.py`
  - Reaproveitado: target de tendencia, pesos/classes e parametros LightGBM.
- `BACKUP/OMNIS_v1_20260304_134715/training/objectives/train_volatility.py`
  - Reaproveitado: target de baixa/media/alta volatilidade.
- `BACKUP/OMNIS_v1_20260304_134715/training/objectives/train_candles.py`
  - Reaproveitado: target por padroes bullish/bearish confirmados por retorno futuro.
- `BACKUP/OMNIS_v1_20260304_134715/training/objectives/train_orderflow.py`
  - Reaproveitado: target por delta acumulado/pressao compradora-vendedora.
- `BACKUP/OMNIS_v1_20260304_134715/training/objectives/train_pullback.py`
  - Reaproveitado: target por pullback buy/sell confirmado por retorno futuro.
- `BACKUP/OMNIS_v1_20260304_134715/training/objectives/train_quant.py`
  - Reaproveitado: target estatistico por z-score, percentil e sazonalidade.
- `BACKUP/OMNIS_v1_20260304_134715/training/objectives/train_reversal.py`
  - Reaproveitado: target binario de reversao com exaustao/divergencia.
- `BACKUP/OMNIS_v1_20260304_134715/training/objectives/train_risk.py`
  - Reaproveitado: target binario de risco.
- `BACKUP/OMNIS_v1_20260304_134715/training/objectives/train_sr.py`
  - Reaproveitado: target por reacao em suporte/resistencia.
- `BACKUP/OMNIS_v1_20260304_134715/training/train_all_models.py`
  - Reaproveitado: ordem de treinamento multi-expert.
- `BACKUP/OMNIS_v1_20260304_134715/training/train_model.py`
  - Reaproveitado: intencao de trainer especializado; o arquivo estava duplicado/contaminado com conteudo de trend e foi substituido por specs limpas.

Melhoria adicional:

- Os targets foram normalizados para usar retorno futuro explicito `(close.shift(-horizon) - close) / close`, evitando o calculo antigo com `pct_change` apos `shift`.

Status: extraidos e validados em parquet real. Foram gerados datasets para 9 experts:

- trend: 623 x 25
- volatility: 623 x 12
- candles: 623 x 21
- orderflow: 623 x 16
- pullback: 623 x 15
- quant: 623 x 9
- reversal: 623 x 17
- risk: 623 x 23
- sr: 623 x 17

## Lote 10 - Contexto, filtros, regime e divergencia OMNIS

Extraido para:

- `fusion_refatorado/fusion_best/market_context.py`
- `fusion_refatorado/fusion_best/decision.py`
- `fusion_refatorado/fusion_best/omnis_experts.py`
- `fusion_refatorado/fusion_best/__init__.py`

Arquivos consumidos:

- `BACKUP/OMNIS_v1_20260304_134715/core/brain/confidence_engine.py`
  - Reaproveitado: pesos institucionais, score final, componentes ponderados e alinhamento multi-timeframe.
- `BACKUP/OMNIS_v1_20260304_134715/core/brain/voting.py`
  - Reaproveitado: ideia de ensemble/voto ponderado, ja consolidada em `decision.py` e `signals.py`.
- `BACKUP/OMNIS_v1_20260304_134715/core/confirmation/orderflow.py`
  - Reaproveitado: delta direcional, intensidade, regime de orderflow, VWAP e distancia do VWAP.
- `BACKUP/OMNIS_v1_20260304_134715/core/confirmation/quant.py`
  - Reaproveitado: logica estatistica ja consolidada em `omnis_experts.py` e `expert_training.py`.
- `BACKUP/OMNIS_v1_20260304_134715/core/context/quant.py`
  - Reaproveitado: duplicata/variante quant consolidada.
- `BACKUP/OMNIS_v1_20260304_134715/core/context/sr.py`
  - Reaproveitado: pivots sem lookahead, zonas dinamicas, distancia de suporte/resistencia, forca e recencia.
- `BACKUP/OMNIS_v1_20260304_134715/core/context/trend.py`
  - Reaproveitado: EMAs, slopes, alinhamentos, retornos, RSI, ADX, ATR, MACD, Bollinger, volume e score de tendencia.
- `BACKUP/OMNIS_v1_20260304_134715/core/context/volatility.py`
  - Reaproveitado: ATR curto/longo, range normalizado, ratio de ATR e regime de volatilidade.
- `BACKUP/OMNIS_v1_20260304_134715/core/divergence/detector_pro.py`
  - Reaproveitado: detector multi-oscilador de divergencias, pivots, sinal e confianca.
- `BACKUP/OMNIS_v1_20260304_134715/core/filters/insidebar_filter.py`
  - Reaproveitado: deteccao de insidebar, breakout e niveis de filtro/confirmador/gatilho.
- `BACKUP/OMNIS_v1_20260304_134715/core/filters/pullback_filter.py`
  - Reaproveitado: pullback macro/micro multi-timeframe e diagnostico de divergencia temporal.
- `BACKUP/OMNIS_v1_20260304_134715/core/market/market_regime.py`
  - Reaproveitado: regime por ADX com fallback de ultimo regime.

Status: extraidos e validados em parquet real. Testado regime, orderflow, volatilidade, S/R, insidebar, divergencia e confidence score.

## Lote 11 - Features de execucao e filtro de entrada OMNIS

Extraido para:

- `fusion_refatorado/fusion_best/execution_features.py`
- `fusion_refatorado/fusion_best/market_context.py`
- `fusion_refatorado/fusion_best/omnis_experts.py`
- `fusion_refatorado/fusion_best/__init__.py`

Arquivos consumidos:

- `BACKUP/OMNIS_v1_20260304_134715/core/execution/candles.py`
- `BACKUP/OMNIS_v1_20260304_134715/features/patterns/candles.py`
  - Reaproveitado: candle range/body, wicks, candle direction, candle strength, close position, range/body norm, impulse, doji, pinbar, engulfing, inside bar e impulso ajustado por volume.
- `BACKUP/OMNIS_v1_20260304_134715/core/execution/reversal.py`
- `BACKUP/OMNIS_v1_20260304_134715/features/patterns/reversal.py`
  - Reaproveitado: divergencia RSI, volume declining, EMA velocity, candle size trend, close position range e sequential closes.
- `BACKUP/OMNIS_v1_20260304_134715/core/execution/pullback.py`
  - Reaproveitado: filtro MTF de pullback ja consolidado em `market_context.py`.
- `BACKUP/OMNIS_v1_20260304_134715/features/entry_filter.py`
  - Reaproveitado: filtro M15 por EMA21, candle strength, distancia da EMA e regime.
- `BACKUP/OMNIS_v1_20260304_134715/features/base/feature_cache.py`
  - Reaproveitado: cache TTL de features sem logs ruidosos.
- `BACKUP/OMNIS_v1_20260304_134715/features/base/feature_engine.py`
  - Reaproveitado: pipeline modular completo de features.
- `BACKUP/OMNIS_v1_20260304_134715/features/patterns/sr.py`
- `BACKUP/OMNIS_v1_20260304_134715/features/technical/orderflow.py`
- `BACKUP/OMNIS_v1_20260304_134715/features/technical/risk.py`
- `BACKUP/OMNIS_v1_20260304_134715/features/technical/volatility.py`
  - Reaproveitado: SR causal, orderflow, risco operacional e volatilidade ja consolidados nos modulos refatorados.

Status: extraidos e validados em parquet real. `run_execution_feature_pipeline` gerou 623 x 351 colunas no recorte testado.

## Lote 12 - Model IO, meta learner, data loader e utilitarios OMNIS

Extraido para:

- `fusion_refatorado/fusion_best/model_io.py`
- `fusion_refatorado/fusion_best/meta_learning.py`
- `fusion_refatorado/fusion_best/data_io.py`
- `fusion_refatorado/fusion_best/market_context.py`
- `fusion_refatorado/fusion_best/__init__.py`

Arquivos consumidos:

- `BACKUP/OMNIS_v1_20260304_134715/models/base/base_catboost.py`
- `BACKUP/OMNIS_v1_20260304_134715/models/base/base_lightgbm.py`
- `BACKUP/OMNIS_v1_20260304_134715/models/base/base_random_forest.py`
- `BACKUP/OMNIS_v1_20260304_134715/models/base/base_xgboost.py`
  - Reaproveitado: intencao de wrappers base; substituido por interfaces leves e registry.
- `BACKUP/OMNIS_v1_20260304_134715/models/ensemble/meta_learner.py`
  - Reaproveitado: target meta operar/bloquear, features meta e parametros LightGBM.
- `BACKUP/OMNIS_v1_20260304_134715/utils/model_loader.py`
  - Reaproveitado: load model + features JSON + metadata, compatibilidade de features e predict seguro.
- `BACKUP/OMNIS_v1_20260304_134715/utils/consistency.py`
  - Reaproveitado: consistencia de posicao, limite por direcao, confianca minima e multiplicador de lote.
- `BACKUP/OMNIS_v1_20260304_134715/utils/trend_alignment.py`
  - Reaproveitado: alinhamento forte de EMA9/EMA21/EMA50 e score -1 a 1.
- `BACKUP/OMNIS_v1_20260304_134715/utils/fibonacci_filter.py`
  - Reaproveitado: swing recente, niveis Fibonacci, score por proximidade e pesos por nivel.
- `BACKUP/OMNIS_v1_20260304_134715/utils/indicators.py`
  - Reaproveitado: indicadores ja distribuidos entre `features.py`, `omnis_experts.py`, `market_context.py` e `execution_features.py`.
- `BACKUP/OMNIS_v1_20260304_134715/utils/insidebar_detector.py`
  - Reaproveitado: insidebar ja consolidado em `market_context.py`.
- `BACKUP/OMNIS_v1_20260304_134715/utils/log_filter.py`
- `BACKUP/OMNIS_v1_20260304_134715/utils/logger.py`
  - Reaproveitado: ideia de reduzir ruido; modulos novos evitam logs temporarios.
- `BACKUP/OMNIS_v1_20260304_134715/data/loader/csv_loader.py`
  - Reaproveitado: loader CSV/Parquet OHLCV normalizado.
- `BACKUP/OMNIS_v1_20260304_134715/data/loader/mt5_connector.py`
  - Reaproveitado: contrato de provider desacoplado; a implementacao MT5 antiga nao foi copiada para nao afetar execucao.

Status: extraidos e validados. Testado compile, meta dataset, Fibonacci, EMA alignment e consistency check.

## Lote 13 - Trading, trailing e logging OMNIS

Extraido para:

- `fusion_refatorado/fusion_best/trading_ops.py`
- `fusion_refatorado/fusion_best/decision.py`
- `fusion_refatorado/fusion_best/risk.py`
- `fusion_refatorado/fusion_best/__init__.py`

Arquivos consumidos:

- `BACKUP/OMNIS_v1_20260304_134715/trading/execution/trade_executor.py`
  - Reaproveitado: validacao de simbolo/tick, montagem de ordem, SL/TP opcional, filtro de tendencia M15 e resultado padronizado.
- `BACKUP/OMNIS_v1_20260304_134715/trading/execution/mt5_trade_executor.py`
  - Reaproveitado: payload esperado para ordem, magic/deviation e contrato de executor.
- `BACKUP/OMNIS_v1_20260304_134715/trading/execution/trade_adapter.py`
  - Reaproveitado: camada unica de execucao sem decidir trade.
- `BACKUP/OMNIS_v1_20260304_134715/trading/execution/trailing_stop.py`
  - Reaproveitado: trailing fixo, trailing por ATR, lock, step, anti-spam e conversao de pontos.
- `BACKUP/OMNIS_v1_20260304_134715/trading/live/live_trading_loop.py`
  - Reaproveitado: arquitetura de loop live como referencia; logica principal ja foi separada em decision/risk/features/trading ops.
- `BACKUP/OMNIS_v1_20260304_134715/trading/logging/trade_logger.py`
  - Reaproveitado: CSV de abertura/fechamento de trades e headers padronizados.
- `BACKUP/OMNIS_v1_20260304_134715/trading/logging/telegram_sender.py`
  - Reaproveitado: envio Telegram nao-bloqueante, agora opcional e desacoplado de settings.

Status: extraidos e validados localmente com request, SL/TP, trailing e adapter injetavel.

## Lote 14 - Configuracao, runtime, scripts auxiliares e documentos OMNIS

Extraido para:

- `fusion_refatorado/fusion_best/runtime_config.py`
- `fusion_refatorado/fusion_best/runtime.py`
- `fusion_refatorado/fusion_best/project_audit.py`
- `fusion_refatorado/fusion_best/data_io.py`
- `fusion_refatorado/fusion_best/__init__.py`
- `plan.md`

Arquivos consumidos:

- `BACKUP/OMNIS_v1_20260304_134715/config/settings.py`
  - Reaproveitado: simbolos alvo, pesos por timeframe, configuracao por ativo, SL/TP fixo, distancias minimas, trailing fixo/ATR, multiplicadores de SL/TP por ATR, limites de posicao, cooldowns, risco, Fibonacci, insidebar, price improvement, thresholds, paths de modelos e helpers de acesso.
  - Nao reaproveitado: dependencia direta de `MetaTrader5` e tokens Telegram hard-coded. A configuracao refatorada usa variaveis de ambiente `FUSION_TELEGRAM_TOKEN` e `FUSION_TELEGRAM_CHAT_ID`.
- `BACKUP/OMNIS_v1_20260304_134715/main.py`
  - Reaproveitado: lifecycle de inicializacao, logging UTF-8, notificacao start/stop, shutdown em `finally` e tratamento de erro critico, agora com hooks injetaveis.
- `BACKUP/OMNIS_v1_20260304_134715/scripts/check_config_imports.py`
  - Reaproveitado: auditoria AST de imports removidos/renomeados em `project_audit.py`.
- `BACKUP/OMNIS_v1_20260304_134715/scripts/test_imports.py`
  - Reaproveitado: intencao de contrato de imports; substituido pelos exports lazy e validacoes locais do `fusion_best`.
- `BACKUP/OMNIS_v1_20260304_134715/scripts/gerar_arvore.py`
  - Reaproveitado: geracao de arvore de projeto com filtros, agora sem escrita automatica em arquivo.
- `BACKUP/OMNIS_v1_20260304_134715/scripts/diagnostico_mt5.py`
  - Reaproveitado: checklist de diagnostico MT5 e mapeamento de estados; removida qualquer execucao de ordem real/interativa.
- `BACKUP/OMNIS_v1_20260304_134715/scripts/final_cleanup.py`
  - Reaproveitado: conceito de limpeza estrutural; nao copiado o uso de `mklink`/shell.
- `BACKUP/OMNIS_v1_20260304_134715/scripts/test_encoding.py`
  - Reaproveitado: necessidade de stdout/stderr UTF-8 em `runtime.py`.
- `BACKUP/OMNIS_v1_20260304_134715/LOGICA_DE_TRADING.md`
  - Reaproveitado: arquitetura decisao -> 9 filtros de execucao, ja refletida em `decision.py`, `market_context.py`, `risk.py`, `trading_ops.py` e plano.
- `BACKUP/OMNIS_v1_20260304_134715/PROJECT_STATUS.md`
  - Reaproveitado: roadmap historico de experts, treino por modelo unico, ensemble, MTF e producao.
- `BACKUP/OMNIS_v1_20260304_134715/estrutura_limpa.txt`
  - Reaproveitado: referencia estrutural do projeto antigo.
- `BACKUP/OMNIS_v1_20260304_134715/.env`
  - Revisado e descartado por conter credenciais/ambiente antigo. Segredos nao foram copiados.
- `BACKUP/OMNIS_v1_20260304_134715/tests/*.py`
  - Revisados: todos estavam vazios, sem codigo util.
- `BACKUP/OMNIS_v1_20260304_134715/package.json`, `package-lock.json`, `clean_pycache.bat`, `consolidar_projeto.py`
  - Revisados: sem logica superior ao que foi extraido para auditoria/runtime/docs.

Dados de treino identificados:

- `BACKUP/OMNIS_v1_20260304_134715/data/historical`
  - `inventory_historical_data` encontrou 123 arquivos historicos, cerca de 379 MB.
  - Cobertura por simbolo: AUDJPY 5; AUDUSD, BTCUSD, ETHUSD, EURCHF, EURGBP, EURJPY, GBPJPY, GBPUSD, GOLD, NZDUSD, USDCAD, USDCHF e USDJPY 7 cada; EURCAD 6; EURUSD 21.
  - Cobertura por timeframe: D1 15; H1 14; H4, M1, M15, M30 e M5 16 cada; timeframes especiais EURUSD H12/H2/H3/H6/H8/M10/M12/M2/M20/M3/M4/M6/MN1/W1 com 1 cada.
  - Estes dados foram indexados via funcao refatorada, mas nao devem ser apagados ainda sem definir destino limpo para datasets de treino.

Status: codigo extraido, compilado e validado por import. Arquivos de codigo/documentacao/ambiente deste lote foram removidos; dados historicos ficam pendentes de migracao/decisao.

## Lote 15 - Experts extras OMNIS_Copia

Extraido para:

- `fusion_refatorado/fusion_best/extended_experts.py`
- `fusion_refatorado/fusion_best/dataset_builder.py`
- `fusion_refatorado/fusion_best/__init__.py`

Arquivos consumidos:

- `BACKUP/OMNIS_Copia/modelos_trading/experts/fibonacci_expert.py`
  - Reaproveitado: niveis Fibonacci por range recente e distancia percentual do preco.
- `BACKUP/OMNIS_Copia/modelos_trading/experts/ichimoku_expert.py`
  - Reaproveitado: Tenkan, Kijun e expandido com cloud atual sem deslocamento futuro.
- `BACKUP/OMNIS_Copia/modelos_trading/experts/volume_expert.py`
  - Reaproveitado: medias/ratios de volume, OBV e oscilador de volume.
- `BACKUP/OMNIS_Copia/modelos_trading/experts/gap_expert.py`
  - Reaproveitado: gap up/down, tamanho, ATR ratio e posicao no range. As antigas features `gap_filled_*` usavam futuro e nao foram copiadas para evitar leakage.
- `BACKUP/OMNIS_Copia/modelos_trading/experts/hvn_expert.py`
  - Reaproveitado: HVN/LVN e forca por desvio de volume.
- `BACKUP/OMNIS_Copia/modelos_trading/experts/stochastic_expert.py`
  - Reaproveitado: stochastic K/D, diferenca, sobrecompra/sobrevenda e cruzamentos.
- `BACKUP/OMNIS_Copia/modelos_trading/experts/seasonality_expert.py`
  - Reaproveitado: hora, dia da semana, sessoes Asia/Londres/NY/overlap e inicio/fim de mes.
- `BACKUP/OMNIS_Copia/modelos_trading/experts/correlation_expert.py`
  - Reaproveitado: autocorrelacao e correlacao rolling opcional com outros ativos.
- `BACKUP/OMNIS_Copia/modelos_trading/experts/momentum_expert.py`
  - Reaproveitado: momentum rapido/lento, aceleracao, medias, cruzamento, regime, forca, score e sinal.
- `BACKUP/OMNIS_Copia/modelos_trading/experts/swing_expert.py`
  - Reaproveitado: swing high/low, distancia e range. A versao antiga usava rolling centralizado; foi trocada por logica causal com `shift(1)`.
- `BACKUP/OMNIS_Copia/modelos_trading/experts/market_microstructure_expert.py`
  - Reaproveitado: spread, spread ratio, tick volume ratio e bid/ask quando disponivel.
- `BACKUP/OMNIS_Copia/modelos_trading/experts/microstructure_expert.py`
  - Reaproveitado: volume flow, bull/bear volume ratio, volume efficiency, spikes, dry volume, expansao/contracao, momentum/aceleracao de volume, VWAP, OBV, VPT, sessoes e volume profile/POC causal.
- `BACKUP/OMNIS_Copia/modelos_trading/experts/volatility_gauge.py`
  - Reaproveitado: ATR ratio/change/percentil, Bollinger/Keltner, squeeze release/tightness/direction, regime de volatilidade, movimento projetado, distancia ate bandas e clusters de volatilidade.
- `BACKUP/OMNIS_Copia/modelos_trading/experts/candlestick_expert.py`
  - Reaproveitado: dragonfly/gravestone doji, hammer, shooting star, inverted hammer, hanging man, engulfing, harami, piercing/dark cloud, morning/evening star, soldiers/crows, inside/outside bar, marubozu e spinning top.
- `BACKUP/OMNIS_Copia/modelos_trading/experts/ml_expert.py`
  - Reaproveitado: z-score de retorno, flag de anomalia, regime por SMA 20/50 e ratio de volatilidade.
- `BACKUP/OMNIS_Copia/modelos_trading/experts/divergence_expert.py`
  - Revisado: placeholder sem divergencia implementada; nao havia codigo util alem de RSI simples ja existente em outros modulos.

Melhorias:

- `dataset_builder.py` ganhou `include_extended_experts`.
- Os nomes das features receberam prefixo `ext_` para evitar colisao com Alpha/Specialists/OMNIS.

Status: compilado e validado em parquet real. A primeira extracao gerou 700 x 65 features; apos microestrutura/volatilidade/candles/anomalias, `build_extended_expert_features` gerou 700 x 177 features e o dataset Fusion completo com OMNIS + extended experts gerou 623 x 517 colunas.

## Lote 16 - Contrato de experts e risco operacional OMNIS_Copia

Extraido para:

- `fusion_refatorado/fusion_best/expert_contracts.py`
- `fusion_refatorado/fusion_best/risk.py`
- `fusion_refatorado/fusion_best/__init__.py`

Arquivos consumidos/revisados:

- `BACKUP/OMNIS_Copia/modelos_trading/experts/base_expert.py`
  - Reaproveitado: contrato padronizado de expert, retorno com `signal/confidence/features`, cache LRU leve, validacao OHLC, estatisticas de uso e wrapper chamavel.
- `BACKUP/OMNIS_Copia/modelos_trading/experts/risk_guardian.py`
  - Reaproveitado: gate operacional de risco com RR minimo, risco diario, maximo de posicoes, maximo por direcao, position size e reset diario.
- `BACKUP/OMNIS_Copia/modelos_trading/experts/pattern_trigger.py`
  - Revisado: padroes uteis ja estavam cobertos por `omnis_experts.py` e foram ampliados no Lote 15 via `CandlestickPatternExpert`.
- `BACKUP/OMNIS_Copia/modelos_trading/experts/pullback_hunter.py`
  - Revisado: continha boa intencao de pullback por EMA/Keltner/Fibonacci, mas usava swing centralizado e calculo global de fib no ultimo candle. A parte segura ja esta coberta por `market_context.py`, `omnis_experts.py` e `extended_experts.py` com swing causal.
- `BACKUP/OMNIS_Copia/modelos_trading/experts/zone_mapper.py`
  - Revisado: versao simples de pivots/SR; conteudo ja coberto por `omnis_experts.py`, `market_context.py` e `extended_experts.py`.

Status: compilado e validado. `TradeRiskGate` aprovou uma ordem simulada valida e `ExpertContract` importou via export lazy.

## Lote 17 - Experts finais OMNIS_Copia

Extraido para:

- `fusion_refatorado/fusion_best/extended_experts.py`

Arquivos consumidos/revisados:

- `BACKUP/OMNIS_Copia/modelos_trading/experts/exhaustion_detector.py`
  - Reaproveitado: RSI extremo, stochastic extremo, volume spike/dry, perda de momentum MACD, toque em Bollinger, momentum loss, aceleracao e setups de reversao bullish/bearish.
  - Ajuste: swing centralizado da origem nao foi copiado para evitar lookahead.
- `BACKUP/OMNIS_Copia/modelos_trading/experts/flow_aggressor.py`
  - Revisado: delta, imbalance, flow score e confidence ja estavam cobertos por `omnis_experts.py` e pela microestrutura de volume adicionada no Lote 15.
- `BACKUP/OMNIS_Copia/modelos_trading/experts/stats_quant.py`
  - Reaproveitado: regime estatistico rolling com z-score, skew/kurtosis, ranges, extremos, autocorrelacao, mean reversion score, momentum score, volatility score e confidence.
  - Ajuste: agregacoes por hora/dia da versao antiga nao foram copiadas porque podiam usar a amostra inteira; a versao refatorada usa rolling causal.
- `BACKUP/OMNIS_Copia/modelos_trading/experts/trend_master.py`
  - Revisado: EMAs, ADX, RSI, MACD, Bollinger, squeeze e Ichimoku ja estavam cobertos por `omnis_experts.py`, `market_context.py` e `extended_experts.py`.
  - Ajuste: trecho antigo com `chikou = shift(-26)` nao foi copiado para evitar vazamento de futuro.

Status: compilado e validado em parquet real. `build_extended_expert_features` gerou 700 x 226 features e o dataset completo com OMNIS + extended experts gerou 623 x 566 colunas.

## Lote 18 - Modelos prontos OMNIS_Copia

Extraido para:

- `fusion_refatorado/fusion_best/legacy_model_inventory.py`
- `fusion_refatorado/fusion_best/model_io.py`
- `fusion_refatorado/docs/omnis_copia_model_inventory.csv`
- `fusion_refatorado/docs/omnis_copia_best_models.csv`
- `fusion_refatorado/models/omnis_copia_best/`

Arquivos consumidos:

- `BACKUP/OMNIS_Copia/modelos_trading/models/training_summary.json`
  - Reaproveitado: ranking de 115 modelos, 23 experts, metricas accuracy/precision/recall/f1/auc, tempo de treino e amostras.
- `BACKUP/OMNIS_Copia/modelos_trading/models/*.pkl`
  - Reaproveitado: os 23 melhores modelos por expert foram copiados para `fusion_refatorado/models/omnis_copia_best`.
  - O restante foi revisado pelo inventario e descartado como versao inferior/duplicada.
- `BACKUP/OMNIS_Copia/modelos_trading/predictor.py`
  - Reaproveitado: carregamento de pacote legado com `model`, `scaler`, `features_list`, `metrics`, preparacao de features e predicao probabilistica.

Destaques do ranking:

- Melhor geral: `ichimoku_expert_random_forest.pkl`, AUC 0.642016, F1 0.502564, accuracy 0.605982.
- Segundo: `fibonacci_expert_random_forest.pkl`, AUC 0.623760, F1 0.469216, accuracy 0.579608.
- Foram preservados 23 campeoes por expert em `fusion_refatorado/models/omnis_copia_best`.

Status: inventario gerado, 23 modelos copiados, manifesto dos modelos copiado junto dos `.pkl`. `load_legacy_model_package` carregou o melhor modelo como `RandomForestClassifier` com 2 features e AUC 0.642016.

## Lote Especial - `__init__.py`

Regra do usuario: arquivos `__init__.py` do `BACKUP` podem ser deletados.

Status: limpeza autorizada.

Execucao: `__init__.py` filtrados do `BACKUP` foram removidos.

## Lote 3 - Validacao ALPHAEDU

Extraido para:

- `fusion_refatorado/fusion_best/validation.py`

Arquivos consumidos:

- `BACKUP/ALPHAEDU/02_train_feature_importance.py`
  - Reaproveitado: ranking de importancia LightGBM com split temporal.
  - Status: extraido, pronto para remover.
- `BACKUP/ALPHAEDU/04_leakage_check.py`
  - Reaproveitado: avaliacao por familias de features e remocao de grupos.
  - Status: extraido, pronto para remover.
- `BACKUP/ALPHAEDU/04_2_ablation_specialists.py`
  - Reaproveitado: ablation incremental de grupos especialistas contra baseline alpha.
  - Status: extraido, pronto para remover.
- `BACKUP/ALPHAEDU/compare_feature_sets.py`
  - Reaproveitado: comparacao full vs top N features.
  - Status: extraido, pronto para remover.
- `BACKUP/ALPHAEDU/backtest_top30.py`
  - Reaproveitado: backtest por probabilidade, confidence e custo de spread.
  - Status: extraido, pronto para remover.
- `BACKUP/ALPHAEDU/06_feature_parameter_scan.py`
  - Reaproveitado: geracao de janelas candidatas por familia de feature e scan por LightGBM.
  - Status: extraido, pronto para remover.

## Lote 5 - Ajuste final de features ALPHAEDU

Extraido para:

- `fusion_refatorado/fusion_best/feature_selection.py`
- `fusion_refatorado/fusion_best/visualization.py`

Arquivos consumidos:

- `BACKUP/ALPHAEDU/07_apply_best_parameters.py`
  - Reaproveitado: extracao de melhores janelas por scan e substituicao pura de listas de windows.
  - Status: extraido, pronto para remover.
- `BACKUP/ALPHAEDU/alpha_final.py`
  - Reaproveitado: regras finais de selecao alpha core + regime + liquidez, removendo grupos ruins.
  - Status: extraido, pronto para remover.
- `BACKUP/ALPHAEDU/plot_trading_signals.py`
  - Reaproveitado: plot candlestick com BUY/SELL e linhas TP/SL.
  - Status: extraido, pronto para remover.

## Lote 6 - Expressoes e operadores ALPHAEDU

Extraido para:

- `fusion_refatorado/fusion_best/expression_catalog.py`
- `fusion_refatorado/fusion_best/features.py`
- `fusion_refatorado/fusion_best/feature_selection.py`

Arquivos consumidos:

- `BACKUP/ALPHAEDU/expressions/forex_basic.py`
- `BACKUP/ALPHAEDU/expressions/alpha158_basic.py`
- `BACKUP/ALPHAEDU/expressions/alpha158_full.py`
- `BACKUP/ALPHAEDU/expressions/alpha158_full_backup.py`
- `BACKUP/ALPHAEDU/expressions/alpha158_optimized.py`
- `BACKUP/ALPHAEDU/expressions/alpha_from_importance.py`
- `BACKUP/ALPHAEDU/operators/ranking.py`
- `BACKUP/ALPHAEDU/operators/reference.py`
- `BACKUP/ALPHAEDU/operators/rolling.py`
- `BACKUP/ALPHAEDU/operators/statistics.py`
- `BACKUP/ALPHAEDU/operators/transforms.py`

Status: extraidos, pasta `BACKUP/ALPHAEDU` pronta para remocao completa.

Execucao: `BACKUP/ALPHAEDU` foi removida por completo apos extracao.

## Lote 4 - Orquestracao e comparacoes ALPHAEDU

Extraido para:

- `fusion_refatorado/fusion_best/dataset_builder.py`
- `fusion_refatorado/fusion_best/validation.py`

Arquivos consumidos:

- `BACKUP/ALPHAEDU/01_feature_orchestrator_160.py`
  - Reaproveitado: pipeline Alpha + especialistas + target + dataset final.
  - Status: extraido, pronto para remover.
- `BACKUP/ALPHAEDU/03_compare_alpha_vs_specialists.py`
  - Reaproveitado: comparacao `alpha_only`, `alpha_plus_specialists`, `specialists_only`.
  - Status: extraido, pronto para remover.
- `BACKUP/ALPHAEDU/05_compare_specialists_individual.py`
  - Reaproveitado: comparacao incremental de especialistas individuais.
  - Status: extraido, pronto para remover.
- `BACKUP/ALPHAEDU/scan_targets.py`
  - Reaproveitado: varredura de horizontes/targets por retorno de estrategia.
  - Status: extraido, pronto para remover.
- `BACKUP/ALPHAEDU/select_top_features.py`
  - Reaproveitado: geracao de dataset com top-N features.
  - Status: extraido, pronto para remover.

## Lote 19 - OMNIS_Copia backtests e estrategias

Extraido para:

- `fusion_refatorado/fusion_best/backtest_reports.py`
- `fusion_refatorado/fusion_best/strategy_ensemble.py`
- `fusion_refatorado/docs/omnis_copia_expert_backtest_features.csv`
- `fusion_refatorado/docs/omnis_copia_top_expert_backtest_features.csv`
- `fusion_refatorado/docs/omnis_copia_model_backtest_results.csv`
- `fusion_refatorado/docs/omnis_copia_ranked_model_backtests.csv`
- `fusion_refatorado/docs/omnis_copia_strategy_top_models.csv`

Arquivos/pastas fonte revisados:

- `BACKUP/OMNIS_Copia/backtest_results`
  - Reaproveitado: flatten e ranking de features por expert/simbolo/timeframe, com Sharpe, win rate, threshold e amostras.
- `BACKUP/OMNIS_Copia/model_backtest_results`
  - Reaproveitado: flatten e ranking de walk-forward por expert/modelo/simbolo/timeframe, com AUC, accuracy, Sharpe, drawdown e retorno.
- `BACKUP/OMNIS_Copia/trading_strategies`
  - Reaproveitado: top models, pesos por AUC e logica de ensemble em forma generica.
- `BACKUP/OMNIS_Copia/backtest_experts.py`
  - Reaproveitado: metodologia de ranking individual de features por thresholds/Sharpe.
- `BACKUP/OMNIS_Copia/backtest_models.py`
  - Reaproveitado: schema de resultados de backtest walk-forward e metricas de estrategia.
- `BACKUP/OMNIS_Copia/create_trading_strategies.py`
  - Reaproveitado: selecao top-N por metrica e ensemble ponderado.
- `BACKUP/OMNIS_Copia/test_strategies.py`
  - Revisado: fluxo manual substituido pelo loader/ensemble legado.
- `BACKUP/OMNIS_Copia/analyze_features.py` e `summarize_features.py`
  - Reaproveitado: consolidacao e resumo de relatorios de features.

Insights preservados:

- Top por AUC salvo em estrategia: `ichimoku_expert_random_forest` (AUC 0.6420), `ichimoku_expert_gradient_boosting`, `fibonacci_expert_random_forest`, `fibonacci_expert_gradient_boosting`, `ichimoku_expert_xgboost`.
- Top features por backtest bruto concentraram sinais de swing em `USDJPY_H4`, incluindo `swing_low_value`, `swing_low`, `swing_low_strength`, `swing_high` e `swing_high_strength`.
- Ranking walk-forward mostrou casos fortes em `GOLD_H4` para `volatility_gauge`, `correlation_expert` e `market_microstructure_expert`, mas com drawdown extremo em alguns registros; usar como candidato, nao como aprovacao operacional automatica.

Validado:

- `python -m compileall fusion_refatorado\fusion_best`
- Import rapido de `flatten_model_backtest_results`, `rank_model_backtests`, `LegacyAucEnsemble` e `top_model_paths_from_manifest`.

Status: fontes consumidas deste lote prontas para remocao.

## Lote 20 - OMNIS_Copia utils, loaders, treino e dados

Extraido para:

- `fusion_refatorado/fusion_best/technical_indicators.py`
- `fusion_refatorado/fusion_best/trade_filters.py`
- `fusion_refatorado/fusion_best/model_io.py`
- `fusion_refatorado/fusion_best/data_io.py`
- `fusion_refatorado/fusion_best/expert_training.py`
- `fusion_refatorado/fusion_best/runtime.py`
- `fusion_refatorado/fusion_best/project_audit.py`
- `fusion_refatorado/docs/omnis_copia_historical_inventory.csv`
- `fusion_refatorado/docs/omnis_copia_prepared_inventory.csv`
- `fusion_refatorado/docs/omnis_copia_historical_quality.csv`

Arquivos/pastas fonte revisados:

- `BACKUP/OMNIS_Copia/utils/indicators.py`
  - Reaproveitado: SMA, EMA, WMA, HMA, RSI, stochastic, Williams %R, CCI, ROC, Ultimate Oscillator, MACD, ATR, Bollinger, Keltner, historical volatility, ADX, Ichimoku, Parabolic SAR, OBV, MFI, VWAP, volume profile, pivots, Fibonacci, zscore, correlacao e entropia.
- `BACKUP/OMNIS_Copia/utils/entry_filter.py`
  - Reaproveitado: score M15 por EMA, candle strength, distancia da EMA21 e regime.
- `BACKUP/OMNIS_Copia/utils/fibonacci_filter.py`
  - Reaproveitado: score e validacao de entrada por niveis Fibonacci.
- `BACKUP/OMNIS_Copia/utils/trend_alignment.py`
  - Reaproveitado: score de alinhamento EMA9/EMA21/EMA50.
- `BACKUP/OMNIS_Copia/utils/insidebar_detector.py`
  - Reaproveitado: deteccao de insidebar e rompimento.
- `BACKUP/OMNIS_Copia/utils/multiasset_model_loader.py`
  - Reaproveitado: loader/cache multiativo e predicao batch.
- `BACKUP/OMNIS_Copia/utils/logger.py`, `log_filter.py`, `summary_table.py`
  - Revisado: log antigo/visual descartado ou coberto por runtime/relatorios atuais.
- `BACKUP/OMNIS_Copia/data/loader/data_loader.py`
  - Reaproveitado: loader robusto para CSV bruto MT5.
- `BACKUP/OMNIS_Copia/data/loader/mt5_connector.py`
  - Reaproveitado: conceito de diagnostico/conexao; credenciais nao migradas.
- `BACKUP/OMNIS_Copia/train_models.py`
  - Reaproveitado: alvo binario futuro e conjunto de modelos candidatos legado.
- `BACKUP/OMNIS_Copia/main.py`
  - Reaproveitado: validacao de diretorio, notificacao segura e runtime lifecycle.
- `BACKUP/OMNIS_Copia/consolidar_projeto.py` e `gerar_arvore.py`
  - Reaproveitado: snapshot consolidado de fontes e arvore de projeto.
- `BACKUP/OMNIS_Copia/.env`
  - Revisado e descartado por conter credenciais locais; nenhum segredo foi copiado.
- `BACKUP/OMNIS_Copia/data/historical` e `data/prepared`
  - Inventariados, ainda mantidos para migracao/compactacao posterior.

Validado:

- `python -m compileall fusion_refatorado\fusion_best`
- Smoke test de indicadores, filtros, loader multiativo, inventario de qualidade e factories de treino.

Observacoes:

- `historical`: 80 arquivos, ~221 MB.
- `prepared`: 81 arquivos, ~220 MB.
- Divergencia detectada: `BACKUP/OMNIS_Copia/data/historical/eurcad/ETHUSD_H1.csv` esta em pasta de outro ativo.

Status: fontes de codigo/config consumidas deste lote prontas para remocao; dados permanecem pendentes.

## Lote 21 - BUILD_MODELS Genesis, shards e Qlib

Extraido para:

- `fusion_refatorado/fusion_best/training.py`
- `fusion_refatorado/fusion_best/data_io.py`
- `fusion_refatorado/fusion_best/backtesting.py`
- `fusion_refatorado/fusion_best/qlib_integration.py`
- `fusion_refatorado/models/build_models`
- `fusion_refatorado/config/build_models_qlib_task_config.yaml`
- `fusion_refatorado/docs/build_models_artifact_inventory.csv`

Arquivos/pastas fonte revisados:

- `BACKUP/BUILD_MODELS/genesis_global_model.pkl`, `genesis_scaler.pkl`, `genesis_model_meta.pkl`
  - Copiados para `fusion_refatorado/models/build_models`.
- `BACKUP/BUILD_MODELS/models_pkl`
  - 21 modelos por shard copiados para `fusion_refatorado/models/build_models/models_pkl`.
- `BACKUP/BUILD_MODELS/src/models/ml_forex.py`
  - Reaproveitado: labels automaticos 0/neutro, 1/compra, 2/venda; shift de seguranca; filtro de preco; thresholds BUY/SELL; filtro por volatilidade; resumo de retornos.
- `BACKUP/BUILD_MODELS/src/data_prep.py`
  - Reaproveitado: RobustScaler e remocao de constantes.
- `BACKUP/BUILD_MODELS/src/engineering/genesis_data_fusion.py`
  - Reaproveitado: alphas Genesis MTF, merge_asof e target M15.
- `BACKUP/BUILD_MODELS/tools/Genesis_Sharder_V3.py`
  - Reaproveitado: padronizacao de mercado, categorias de shards e alphas por bloco.
- `BACKUP/BUILD_MODELS/tools/backtest.py`
  - Reaproveitado: avaliacao OOS por shard, pips/points, win rate e modo NORMAL/INVERT.
- `BACKUP/BUILD_MODELS/tools/analyze_gold_excursion.py`, `analyze_silver_excursion.py`, `batch_excursion_analyzer.py`
  - Reaproveitado: MAE/MFE, percentis 80/95 e sugestoes para SL/trailing.
- `BACKUP/BUILD_MODELS/src/engineering/gerador_tf.py`
  - Reaproveitado: resample OHLCV.
- `BACKUP/BUILD_MODELS/qlib_scripts`
  - Reaproveitado: preparo CSV Qlib, FileDataDumper config e YAML de task.
- `BACKUP/BUILD_MODELS/extração_alpha158.py`
  - Reaproveitado: ranking Information Coefficient por Spearman.
- Demais scripts de auditoria/conversao/documentacao
  - Revisados; conteudo coberto pelos novos helpers ou registrado no inventario.

Validado:

- `python -m compileall fusion_refatorado\fusion_best`
- Smoke tests de Genesis alphas, shard category, OOS setups, sinais por probabilidade e Qlib helpers.

Status: codigo, config e modelos consumidos prontos para remocao; `shards_v4` permanece pendente por conter datasets parquet grandes.

## Lote 22 - FEATURE_STORE Genesis V1

Extraido para:

- `fusion_refatorado/fusion_best/data_io.py`
- `fusion_refatorado/fusion_best/backtesting.py`
- `fusion_refatorado/fusion_best/training.py`
- `fusion_refatorado/models/feature_store/modelo_genesis_v1.pkl`
- `fusion_refatorado/docs/ranking_features_global.csv`
- `fusion_refatorado/docs/ranking_features_oficial.csv`
- `fusion_refatorado/docs/resultado_final_com_spread.csv`
- `fusion_refatorado/docs/resultado_mega_backtest.csv`

Arquivos fonte revisados:

- `01_feature_importance.py`
  - Reaproveitado: importancia global por ativo com XGBoost e media acumulada.
- `02_train_lightgbm_baseline.py`
  - Reaproveitado: top features por ranking, split temporal e checkpoint com features/target.
- `03_backtest_visual.py`, `04_mega_backtest_99_ativos.py`, `05_backtest_pessimista.py`, `05_backtest_ultra_realista.py`
  - Reaproveitado: avaliacao temporal, threshold de previsao, custo de spread real e resultados agregados.
- `06_genesis_live_bridge.py`
  - Reaproveitado: geracao live de features Genesis por timeframe e alinhamento a features esperadas.
- `modelo_genesis_v1.pkl`
  - Copiado para modelos refatorados.
- Rankings/resultados CSV
  - Copiados para docs.

Validado:

- `python -m compileall fusion_refatorado\fusion_best`
- Smoke test de `build_genesis_live_features` e `spread_realistic_backtest`.

Status: pasta pronta para remocao apos preservacao.

## Lote 28 - NEXUS_backup

Extraido para:

- `fusion_refatorado/fusion_best/nexus_ensemble.py`
- `fusion_refatorado/fusion_best/nexus_features.py`
- `fusion_refatorado/models/nexus_backup`
- `fusion_refatorado/data/nexus_backup`
- `fusion_refatorado/docs/nexus_backup_model_inventory.csv`
- `fusion_refatorado/docs/nexus_backup_data_inventory.csv`

Arquivos fonte revisados:

- `nexus/brain/consensus.py`, `hybrid_consensus.py`, `confidence.py`
  - Reaproveitado: votos por expert, pesos por regime, camadas C0/C1/C2/C3, consenso hibrido regra+ML e score hierarquico de confianca.
- `nexus/intelligence/blender.py`, `fusion_predictor.py`, `models/loader.py`
  - Reaproveitado: preparo tolerante de features, safe predict, predictor global/por simbolo e blender de modelos por regime.
- `nexus/analysis/features/engine.py`
  - Reaproveitado: feature engine tecnico com SMA/EMA/RSI/MACD/Stochastic/ATR/Bollinger/Ichimoku, alinhamento e momentum score.
- `nexus/analysis/patterns/detector.py`
  - Reaproveitado em versao corrigida: doji, hammer, shooting star e engulfings como sinais reutilizaveis.
- `nexus/analysis/orderflow/analyzer.py`
  - Reaproveitado: perfil de volume por ticks e resumo de book com spread, mid, profundidade e imbalance.
- `data/models`
  - Copiado integralmente: 285 arquivos, ~8.04 GB, incluindo 274 modelos `.pkl`, modelos globais, por simbolo EURUSD, metadados e scripts experimentais.
- `data/features` e `data/raw`
  - Copiados integralmente: 164 arquivos, ~2.14 GB, incluindo feature CSV MTF de ~1.39 GB, JSONs de features fusion/MTF e 155 CSVs raw.
- `README.md`, `FEATURES_ANALYSIS.md`, `NEXUS_FEATURES.md`, testes e scripts de dashboard/orquestracao
  - Revisados; conteudo arquitetural util incorporado nos modulos refatorados e nos inventarios.

Validado:

- `python -m compileall fusion_refatorado\fusion_best`
- Smoke test de `ExpertConsensus`, `HybridConsensus`, `HierarchicalConfidence`, `build_nexus_feature_frame`, `detect_latest_candle_patterns` e `summarize_order_book`.
- Conferencia de copia: `models/nexus_backup` manteve 285 arquivos / 8,038,905,543 bytes; `data/nexus_backup` manteve 164 arquivos / 2,142,869,115 bytes.

Status: pasta pronta para remocao apos copia/inventario.

## Lote 32 - Migracao final de dados massivos

Movido para:

- `fusion_refatorado/data/backup_migrated/build_models_shards_v4`
- `fusion_refatorado/data/backup_migrated/data_hub_full`
- `fusion_refatorado/data/backup_migrated/data_csv_full`
- `fusion_refatorado/data/backup_migrated/omnis_copia_data`
- `fusion_refatorado/data/backup_migrated/omnis_v1_data`
- `fusion_refatorado/docs/backup_migrated_data_inventory.csv`

Fontes movidas:

- `BACKUP/BUILD_MODELS/shards_v4`: 21 arquivos / 4,219,273,240 bytes.
- `BACKUP/DATA_HUB`: 1,406 arquivos / 31,254,259,667 bytes.
- `BACKUP/data_csv`: 4,830 arquivos / 40,467,031,262 bytes.
- `BACKUP/OMNIS_Copia/data`: 162 arquivos / 440,923,625 bytes.
- `BACKUP/OMNIS_v1_20260304_134715/data`: 123 arquivos / 378,975,779 bytes.

Observacao:

- `DATA_HUB` e `data_csv` foram movidos, nao copiados, para evitar duplicacao de dezenas de GB.
- Parciais incompletos de copia anterior foram removidos antes do `Move-Item`.

Status: origens removidas apos conferencia.

## Lote 33 - Scripts raiz restantes do BACKUP

Extraido para:

- `fusion_refatorado/fusion_best/data_io.py`
- `fusion_refatorado/fusion_best/qlib_integration.py`

Arquivos fonte revisados:

- `BACKUP/minerador_tiingo.py`
  - Reaproveitado: construcao de URL Tiingo FX por bloco, normalizacao OHLCV 15min e merge sem duplicatas.
  - Chave de API hardcoded foi descartada e nao foi migrada.
- `BACKUP/ver_lucro.py`
  - Reaproveitado: campos Qlib scalper 15min, label de retorno futuro e avaliacao de retorno por predição acima da media.

Validado:

- `python -m compileall fusion_refatorado\fusion_best`
- Smoke test de `tiingo_fx_price_url`, `normalize_tiingo_fx_prices`, `merge_ohlcv_without_duplicates`, `qlib_scalper_15m_fields`, `qlib_forward_return_label` e `evaluate_prediction_strategy_returns`.

Status: arquivos prontos para remocao.

## Lote 31 - omnis_backup_

Extraido para:

- `fusion_refatorado/fusion_best/training.py`
- `fusion_refatorado/data/omnis_backup`
- `fusion_refatorado/models/omnis_backup`
- `fusion_refatorado/config/omnis_backup_config.py`
- `fusion_refatorado/docs/omnis_backup_data_inventory.csv`
- `fusion_refatorado/docs/omnis_backup_model_inventory.csv`
- `fusion_refatorado/docs/omnis_backup_LOGICA_DE_TRADING.md`
- `fusion_refatorado/docs/omnis_backup_PROJECT_STATUS.md`

Arquivos fonte revisados:

- `train_models/train_*.py`
  - Reaproveitado: target por movimento futuro em ATR, metatarget de decisao, treino meta LightGBM e preparo tolerante de features obrigatorias.
- `features copy/*`
  - Revisado: pipeline modular trend/SR/orderflow/candles/volatilidade/risco/reversao ja coberto pelos modulos `extended_experts.py`, `nexus_features.py`, `training.py` e `data_io.py`.
- `core/*`
  - Revisado: confidence, confluence, insidebar, pullback, risk e trade adapter ja cobertos pelos lotes OMNIS/OMNIS_v1/OMNIS_Copia e `trade_filters.py`, `decision.py`, `risk.py`, `trading_ops.py`.
- `dados`
  - Copiado integralmente: 123 CSVs, ~379 MB.
- `models` e `modelos`
  - Copiados integralmente: 97 arquivos, ~62 MB, incluindo 30 `.pkl`, metamodelos e metadados.
- `LOGICA_DE_TRADING.md`, `PROJECT_STATUS.md`, `config.py`, `runtime`
  - Preservados em docs/config para manter arquitetura, filtros e parametros.
- `.env` e `.env copy`
  - Revisados e descartados por conterem configuracao/segredos locais.

Validado:

- `python -m compileall fusion_refatorado\fusion_best`
- Smoke test de `create_atr_direction_target`, `create_meta_decision_target`, `train_meta_decision_model` e `prepare_required_feature_frame`.
- Conferencia de copia: dados 123 arquivos / 378,975,779 bytes; modelos 97 arquivos / 62,322,009 bytes.

Status: pasta pronta para remocao apos copia/inventario.

## Lote 30 - OMNIS legacy

Extraido para:

- `fusion_refatorado/fusion_best/decision.py`
- `fusion_refatorado/fusion_best/trading_ops.py`
- `fusion_refatorado/fusion_best/data_io.py`
- `fusion_refatorado/models/omnis_legacy`
- `fusion_refatorado/models/omnis_legacy_mlruns`
- `fusion_refatorado/data/omnis_legacy`
- `fusion_refatorado/config/omnis_legacy`
- `fusion_refatorado/docs/omnis_legacy_data_inventory.csv`
- `fusion_refatorado/docs/omnis_legacy_model_inventory.csv`

Arquivos fonte revisados:

- `EXECUÇÃO/src/core/decision/adaptive_threshold.py`, `decision_engine.py`
  - Reaproveitado: threshold adaptativo por z-score, historico por ativo, alerta de volatilidade e decisao hierarquica C1/C2/C3.
- `EXECUÇÃO/src/core/trading/live_orchestrator.py`, `executor.py`, `trailing.py`, `filters.py`
  - Reaproveitado: funil operacional F0/F1/F2/F3/F4/F6, SL/TP ciente de spread por classe de ativo e parametros de trailing por pip/ATR.
- `EXECUÇÃO/src/features/genesis_calculator.py`
  - Reaproveitado: score Genesis por simbolo/timestamp/timeframe, alinhamento M15/H1/D1 e fatores de risco Genesis.
- `EXECUÇÃO/src/models/loader.py`
  - Revisado: carregamento hierarquico e V2 coberto por loaders e predictors refatorados (`model_io.py`, `nexus_ensemble.py`).
- `EXECUÇÃO/src/qlib`
  - Revisado: preparo/treino Qlib ja coberto pelos helpers `qlib_integration.py`, `training.py` e lotes QLIB/PROJETO_QLIB_FINAL.
- `EXECUÇÃO/config`
  - Copiado para preservar parametros de modelo, strategy, simbolos, Qlib e risco.
- `DADOS`
  - Copiado integralmente: 156 CSVs, ~2.14 GB.
- `EXECUÇÃO/models`
  - Copiado integralmente: 655 arquivos, ~133 MB, incluindo 369 modelos `.pkl`, metadados e modelos V2/QLib.
- `TREINAMENTO/mlruns`
  - Copiado integralmente para preservar rastreabilidade de treino.
- `.env` e `.env.bybit`
  - Revisados e descartados por conterem configuracao/segredos locais.
- `EXECUÇÃO/node_modules`, `frontend/node_modules`, `qlib`/UI antiga, scripts de comentarios/docs
  - Revisados; nao migrados por serem dependencias vendorizadas, dashboard antigo ou documentacao gerada inferior ao plano/manifesto.

Validado:

- `python -m compileall fusion_refatorado\fusion_best`
- Smoke test de `AdaptiveThreshold`, `hierarchical_model_decision`, `trailing_params_for_symbol`, `calculate_spread_aware_sl_tp`, `evaluate_trade_filter_funnel` e `genesis_signal_strength_at`.
- Conferencia de copia: dados 156 arquivos / 2,142,864,022 bytes; modelos 655 arquivos / 133,345,626 bytes; MLflow 144 arquivos / 12,726 bytes.

Status: pasta pronta para remocao apos copia/inventario.

## Lote 29 - PROJETO_QLIB_FINAL

Extraido para:

- `fusion_refatorado/fusion_best/qlib_integration.py`
- `fusion_refatorado/fusion_best/training.py`
- `fusion_refatorado/models/projeto_qlib_final/omnis_model_eurusd_m5.pkl`
- `fusion_refatorado/data/projeto_qlib_final`
- `fusion_refatorado/docs/projeto_qlib_final_data_inventory.csv`
- `fusion_refatorado/docs/projeto_qlib_final_model_inventory.csv`

Arquivos fonte revisados:

- `01_preparar_dados.py`
  - Reaproveitado: conversao manual OHLCV/parquet para layout Qlib binario com calendario `5min.txt` e features `.bin`.
- `02_minerar_alphas.py`
  - Reaproveitado: alphas elite `roc_5`, `rsv_20`, `j_indicator`, `persistence`, `vstd_20` e ranking por IC Spearman contra retorno futuro.
- `03_treinar_modelo.py`
  - Reaproveitado: treino temporal RandomForest EURUSD M5 com `max_depth=6`, `min_samples_leaf=50`, features vencedoras e metricas/feature importance.
- `04_omnis_live.py`
  - Reaproveitado: threshold de confianca para filtrar sinais fracos e uso live das mesmas features elite.
- `omnis_model_eurusd_m5.pkl`
  - Copiado como modelo pronto.
- `data/EURUSD.parquet` e `data_qlib`
  - Copiados integralmente: 701 arquivos, ~1.27 GB, incluindo base Qlib 5min multiativo.
- `qlib-main`
  - Revisado como dependencia vendorizada do Microsoft Qlib; sem migracao de codigo fonte para evitar duplicar biblioteca externa no FUSION.

Validado:

- `python -m compileall fusion_refatorado\fusion_best`
- Smoke test de `build_omnis_elite_alphas`, `rank_omnis_elite_alphas` e `train_omnis_elite_random_forest`.
- Conferencia de copia: modelo preservado com 1,509,385 bytes; dados preservados com 701 arquivos / 1,272,506,047 bytes.

Status: pasta pronta para remocao apos copia/inventario.

## Lote 25 - DATA_HUB Genesis/Fusion

Extraido para:

- `fusion_refatorado/fusion_best/data_io.py`
- `fusion_refatorado/fusion_best/training.py`
- `fusion_refatorado/fusion_best/model_io.py`
- `fusion_refatorado/models/data_hub`
- `fusion_refatorado/docs/data_hub_data_inventory.csv`
- Relatorios e schema DATA_HUB copiados para `fusion_refatorado/docs`

Arquivos fonte revisados:

- `00_master_pipeline.py`
  - Reaproveitado: sequencia operacional do pipeline.
- `07_genesis_fusion.py`
  - Reaproveitado: fusao MTF por `merge_asof`, base M15 e target `target_ret`.
- `qlib_fusion_trainer.py`
  - Reaproveitado: limpeza de features, modelos Ridge/GBR/RF, ranking por Information Coefficient e wrapper com pipeline.
- `schema_genesis.json`
  - Preservado em docs.
- `modelos`
  - 328 arquivos copiados para `fusion_refatorado/models/data_hub`.
- Relatorios de auditoria/status/spread/erros/ativos
  - Copiados para docs.
- `FUSION`, `01_RAW_MT5`, `02_Organizado_MT5`, `03_M5_Sincronizado_Final`, `04_MultiTimeframe`, `SUPER_MATRIZ_GENESIS.parquet`
  - Inventariados como dados grandes pendentes.

Validado:

- `python -m compileall fusion_refatorado\fusion_best`
- Smoke test de `clean_fusion_regression_frame` e `QlibModelWrapper`.

Status: codigo/modelos/relatorios consumidos prontos para remocao; dados grandes permanecem pendentes.

## Lote 26 - GENESIS_ALPHA

Extraido para:

- `fusion_refatorado/models/genesis_alpha`
- `fusion_refatorado/data/genesis_alpha/qlib_data`
- `fusion_refatorado/docs/genesis_alpha_inventory.csv`
- `fusion_refatorado/fusion_best/qlib_integration.py`

Arquivos fonte revisados:

- `genesis_global_model.pkl`, `genesis_scaler.pkl`
  - Copiados como artefatos prontos.
- `genesis_config.yaml`
  - Copiado com task Qlib M15, features custom e backtest TopK.
- `mlruns`
  - Copiado para preservar runs, pred/label e artefatos MLflow.
- `qlib_data`
  - Copiado como base Qlib Genesis.
- `scripts_genesis/rodar_genesis.py`
  - Reaproveitado: preparo de `PortAnaRecord`, benchmark nulo para Forex, backtest 15min e TopkDropoutStrategy.
- `scripts_genesis/ver_lucro.py`
  - Reaproveitado: localizacao de pred/label mais recente, cobertura de pred positivo, correlacao e retorno TopK.
- `.env`
  - Revisado e descartado por ser configuracao local.

Validado:

- `python -m compileall fusion_refatorado\fusion_best`
- Smoke test de `prepare_qlib_port_config` e `summarize_qlib_predictions`.

Status: pasta pronta para remocao apos copia/inventario.

## Lote 27 - NEXUS

Extraido para:

- `fusion_refatorado/fusion_best/alpha158_live.py`
- `fusion_refatorado/models/nexus/alpha158_best.joblib`
- `fusion_refatorado/data/nexus`
- `fusion_refatorado/docs/nexus_inventory.csv`
- `fusion_refatorado/docs/nexus_backtest_equity_curve.csv`

Arquivos fonte revisados:

- `nexus/features/alpha158_live.py`
  - Reaproveitado: calculo Alpha158 completo com 144 features e fetch live MT5 lazy.
- `models/alpha158_best.joblib`
  - Copiado como modelo pronto.
- `qlib_data_novo` e `data/raw`
  - Copiados como dados de treino/teste NEXUS.
- `backtest_equity_curve.csv`
  - Copiado para docs.
- `nexus/backtest`, `nexus/execution`, `nexus/models`, `treinamento`, `treinamento_qlib`
  - Revisados; conceitos uteis ja cobertos por modulos refatorados de backtest, risco, registry, Qlib e Alpha158.
- `README.md`, `PROJETO_CONSOLIDADO.txt`, scripts de arvore/consolidacao
  - Revisados; sem conteudo superior ao manifesto/plano atuais.

Validado:

- `python -m compileall fusion_refatorado\fusion_best`
- `calculate_alpha158_features` gerou 144 features em dados sinteticos.

Status: pasta pronta para remocao apos copia/inventario.

## Lote 23 - FOREX EURUSD M5 Qlib

Extraido para:

- `fusion_refatorado/data/forex_m5_eurusd`
- `fusion_refatorado/docs/forex_m5_eurusd_inventory.csv`

Arquivos fonte revisados:

- `BACKUP/FOREX/csv/M5/eurusd.csv`
  - Copiado como dataset bruto EURUSD M5.
- `BACKUP/FOREX/qlib_data_m5`
  - Copiado como base binaria Qlib pronta, incluindo calendario, instrumentos e features open/high/low/close/volume/spread/decimals/point_value.
- `BACKUP/FOREX/resample_forex.py`
  - Revisado: logica coberta por `resample_ohlcv`.
- `BACKUP/FOREX/test_qlib_load.py`
  - Revisado: logica coberta por `qlib_integration.py`.

Status: pasta pronta para remocao apos copia/inventario.

## Lote 24 - QLIB Alpha158 EURUSD

Extraido para:

- `fusion_refatorado/fusion_best/qlib_integration.py`
- `fusion_refatorado/fusion_best/backtesting.py`
- `fusion_refatorado/models/qlib/modelo_alpha158_sucesso.pkl`
- `fusion_refatorado/models/qlib/modelo_balanceado_lightgbm.pkl`

Arquivos fonte revisados:

- `04_treinamento_alpha158.py`
  - Reaproveitado: config Alpha158 EURUSD M15, horizonte de 4 candles e split temporal 2020-2024/2025-2026.
- `treinar_modelo_balanceado.py`
  - Reaproveitado: binarizacao por retorno positivo, class weights, LightGBM balanceado e predicoes recentes.
- `analisar_probabilidades.py`
  - Reaproveitado: diagnostico de probabilidades por faixas e thresholds.
- `avaliar_resultados.py`
  - Reaproveitado: busca flexivel de label e metricas de classificacao.
- `backtest_simples.py`
  - Reaproveitado: backtest long-only com capital, trades, win rate e drawdown.
- `mt5_qlib_integracao.py`, `fazer_predicoes.py`, `carregar_e_usar_modelo.py`
  - Reaproveitado: sinal BUY/SELL/NEUTRAL por probabilidade e uso do modelo em runtime.
- `conexao_mt5.py`, `diagnosticar_e_corrigir.py`, `00_verificar_csv.py`, `02_testar_qlib.py`, `03_testar_alpha158.py`
  - Revisados; cobertos por helpers de dados/Qlib/runtime ja extraidos.

Validado:

- `python -m compileall fusion_refatorado\fusion_best`
- Smoke tests de `alpha158_handler_config`, `probability_diagnostics`, `binary_signal_from_probability` e `long_only_equity_backtest`.

Status: pasta pronta para remocao apos preservacao.
