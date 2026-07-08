# Decision Audit Summary

- Eventos: 17175
- Ativos: 28
- Estrategias: 4
- Tradeability medio: 0.379

## Decisoes

- BLOCK: 17141
- ALLOW: 34

## Motivos

- preco_candle_nao_confirmado: 1905
- ordens_bloqueadas_config: 1369
- autotrading_desativado_terminal: 1332
- ema_nao_alinhada: 938
- macro_fluxo_contra:macro_neutro:score=0.033: 525
- macro_fluxo_contra:macro_contra:SELL:score=-0.790: 522
- macro_fluxo_contra:macro_contra:BUY:score=0.883: 358
- macro_fluxo_contra:macro_contra:SELL:score=-1.000: 336
- macro_fluxo_contra:macro_contra:BUY:score=0.930: 330
- macro_fluxo_contra:macro_neutro:score=0.173: 291
- macro_fluxo_contra:macro_contra:BUY:score=0.341: 283
- macro_fluxo_contra:macro_contra:BUY:score=0.450: 268
- macro_fluxo_contra:macro_contra:BUY:score=0.201: 222
- macro_fluxo_contra:macro_contra:SELL:score=-0.850: 213
- macro_fluxo_contra:macro_neutro:score=-0.036: 207
- macro_fluxo_contra:macro_neutro:score=0.193: 201
- macro_fluxo_contra:macro_contra:BUY:score=1.000: 198
- macro_fluxo_contra:macro_contra:SELL:score=-0.750: 195
- macro_fluxo_contra:macro_contra:BUY:score=0.300: 192
- macro_fluxo_contra:macro_contra:BUY:score=0.233: 184
- macro_fluxo_contra:macro_neutro:score=0.053: 177
- macro_fluxo_contra:macro_neutro:score=-0.067: 168
- macro_fluxo_contra:macro_contra:BUY:score=0.828: 150
- macro_fluxo_contra:macro_contra:BUY:score=0.290: 144
- macro_fluxo_contra:macro_neutro:score=-0.014: 132
- macro_fluxo_contra:macro_contra:BUY:score=0.206: 132
- macro_fluxo_contra:macro_neutro:score=0.147: 126
- macro_fluxo_contra:macro_neutro:score=-0.121: 123
- macro_fluxo_contra:macro_neutro:score=0.030: 120
- macro_fluxo_contra:macro_neutro:score=-0.150: 115

## XAI - Faixa de Confianca

- baixa: 1317
- fraca: 52

## Engines

- candle_price BUY: 1519
- candle_price SELL: 1358
- confidence_calibration SELL: 5105
- confidence_calibration NEUTRAL: 1103
- confidence_calibration BUY: 838
- consensus_engine NEUTRAL: 5539
- consensus_engine SELL: 1281
- consensus_engine BUY: 393
- context_engine NEUTRAL: 4626
- context_engine SELL: 1436
- context_engine BUY: 1154
- ema_alignment BUY: 659
- ema_alignment SELL: 313
- entry_timing SELL: 5196
- entry_timing BUY: 1894
- execution_engine NEUTRAL: 5730
- execution_engine BUY: 175
- execution_engine SELL: 142
- feature_engineering NEUTRAL: 4862
- macro_flow SELL: 5854
- macro_flow BUY: 5603
- macro_flow NEUTRAL: 3015
- market_briefing NEUTRAL: 9217
- market_regime NEUTRAL: 11538
- market_regime SELL: 1183
- market_regime BUY: 1029
- market_structure NEUTRAL: 8910
- meta_model_ensemble NEUTRAL: 5880
- opportunity_engine NEUTRAL: 5590
- opportunity_engine SELL: 1174
- opportunity_engine BUY: 449
- portfolio_correlation NEUTRAL: 2951
- portfolio_correlation BUY: 2268
- portfolio_correlation SELL: 479
- portfolio_exposure BUY: 6342
- portfolio_exposure SELL: 2010
- risk_engine NEUTRAL: 6047
- session_context NEUTRAL: 9864
- volatility_engine NEUTRAL: 9864

## Ultimos eventos

- 2026-05-21T19:41:25.994822 strategy3 CADJPY M15 SELL: BLOCK ordens_bloqueadas_config tradeability=0.424
  - XAI: BLOCK CADJPY M15 SELL: tradeability=0.424, consensus=0.179, conflito=0.086. Bloqueio dominante: context_engine:contexto_fraco:0.34.
- 2026-05-21T19:41:24.031302 strategy2 CADJPY M15 SELL: BLOCK ordens_bloqueadas_config tradeability=0.424
  - XAI: BLOCK CADJPY M15 SELL: tradeability=0.424, consensus=0.179, conflito=0.086. Bloqueio dominante: context_engine:contexto_fraco:0.34.
- 2026-05-21T19:41:22.284970 strategy1 CADJPY M15 SELL: BLOCK ordens_bloqueadas_config tradeability=0.424
  - XAI: BLOCK CADJPY M15 SELL: tradeability=0.424, consensus=0.179, conflito=0.086. Bloqueio dominante: context_engine:contexto_fraco:0.34.
- 2026-05-21T19:41:19.270154 strategy3 AUDUSD H1 SELL: BLOCK ordens_bloqueadas_config tradeability=0.348
  - XAI: BLOCK AUDUSD H1 SELL: tradeability=0.348, consensus=0.139, conflito=0.091. Bloqueio dominante: context_engine:contexto_fraco:0.33.
- 2026-05-21T19:41:17.108125 strategy2 AUDUSD H1 SELL: BLOCK ordens_bloqueadas_config tradeability=0.348
  - XAI: BLOCK AUDUSD H1 SELL: tradeability=0.348, consensus=0.139, conflito=0.091. Bloqueio dominante: context_engine:contexto_fraco:0.33.
- 2026-05-21T19:41:14.555458 strategy1 AUDUSD H1 SELL: BLOCK ordens_bloqueadas_config tradeability=0.348
  - XAI: BLOCK AUDUSD H1 SELL: tradeability=0.348, consensus=0.139, conflito=0.091. Bloqueio dominante: context_engine:contexto_fraco:0.33.
- 2026-05-21T19:41:12.099457 strategy3 AUDUSD M30 SELL: BLOCK ordens_bloqueadas_config tradeability=0.328
  - XAI: BLOCK AUDUSD M30 SELL: tradeability=0.328, consensus=0.139, conflito=0.091. Bloqueio dominante: context_engine:contexto_fraco:0.33.
- 2026-05-21T19:41:09.776517 strategy2 AUDUSD M30 SELL: BLOCK ordens_bloqueadas_config tradeability=0.328
  - XAI: BLOCK AUDUSD M30 SELL: tradeability=0.328, consensus=0.139, conflito=0.091. Bloqueio dominante: context_engine:contexto_fraco:0.33.
- 2026-05-21T19:41:07.575696 strategy1 AUDUSD M30 SELL: BLOCK ordens_bloqueadas_config tradeability=0.328
  - XAI: BLOCK AUDUSD M30 SELL: tradeability=0.328, consensus=0.139, conflito=0.091. Bloqueio dominante: context_engine:contexto_fraco:0.33.
- 2026-05-21T19:41:04.149103 strategy1 AUDNZD H4 BUY: BLOCK ordens_bloqueadas_config tradeability=0.474
  - XAI: BLOCK AUDNZD H4 BUY: tradeability=0.474, consensus=0.093, conflito=0.169. Bloqueio dominante: confidence_calibration:probabilidade_calibrada_menor.
- 2026-05-21T19:41:02.071933 strategy3 AUDNZD H1 BUY: BLOCK ordens_bloqueadas_config tradeability=0.485
  - XAI: BLOCK AUDNZD H1 BUY: tradeability=0.485, consensus=0.257, conflito=0.080. Bloqueio dominante: context_engine:contexto_fraco:0.46.
- 2026-05-21T19:40:59.869649 strategy2 AUDNZD H1 BUY: BLOCK ordens_bloqueadas_config tradeability=0.485
  - XAI: BLOCK AUDNZD H1 BUY: tradeability=0.485, consensus=0.257, conflito=0.080. Bloqueio dominante: context_engine:contexto_fraco:0.46.
- 2026-05-21T19:40:57.870825 strategy1 AUDNZD H1 BUY: BLOCK ordens_bloqueadas_config tradeability=0.485
  - XAI: BLOCK AUDNZD H1 BUY: tradeability=0.485, consensus=0.257, conflito=0.080. Bloqueio dominante: context_engine:contexto_fraco:0.46.
- 2026-05-21T19:40:55.679445 strategy1 AUDNZD M30 SELL: BLOCK ordens_bloqueadas_config tradeability=0.307
  - XAI: BLOCK AUDNZD M30 SELL: tradeability=0.307, consensus=0.176, conflito=0.084. Bloqueio dominante: context_engine:contexto_fraco:0.34.
- 2026-05-21T19:40:53.334946 strategy1 AUDJPY H4 SELL: BLOCK ordens_bloqueadas_config tradeability=0.368
  - XAI: BLOCK AUDJPY H4 SELL: tradeability=0.368, consensus=0.184, conflito=0.087. Bloqueio dominante: context_engine:contexto_fraco:0.33.
- 2026-05-21T19:40:50.967461 strategy3 AUDJPY M30 SELL: BLOCK ordens_bloqueadas_config tradeability=0.328
  - XAI: BLOCK AUDJPY M30 SELL: tradeability=0.328, consensus=0.181, conflito=0.086. Bloqueio dominante: context_engine:contexto_fraco:0.32.
- 2026-05-21T19:40:48.521963 strategy2 AUDJPY M30 SELL: BLOCK ordens_bloqueadas_config tradeability=0.328
  - XAI: BLOCK AUDJPY M30 SELL: tradeability=0.328, consensus=0.181, conflito=0.086. Bloqueio dominante: context_engine:contexto_fraco:0.32.
- 2026-05-21T19:40:46.264406 strategy1 AUDJPY M30 SELL: BLOCK ordens_bloqueadas_config tradeability=0.328
  - XAI: BLOCK AUDJPY M30 SELL: tradeability=0.328, consensus=0.181, conflito=0.086. Bloqueio dominante: context_engine:contexto_fraco:0.32.
- 2026-05-21T19:40:43.085534 strategy3 AUDCAD H1 SELL: BLOCK ordens_bloqueadas_config tradeability=0.344
  - XAI: BLOCK AUDCAD H1 SELL: tradeability=0.344, consensus=0.187, conflito=0.087. Bloqueio dominante: context_engine:contexto_fraco:0.35.
- 2026-05-21T19:40:40.981341 strategy2 AUDCAD H1 SELL: BLOCK ordens_bloqueadas_config tradeability=0.344
  - XAI: BLOCK AUDCAD H1 SELL: tradeability=0.344, consensus=0.187, conflito=0.087. Bloqueio dominante: context_engine:contexto_fraco:0.35.
- 2026-05-21T19:40:38.548094 strategy1 AUDCAD H1 SELL: BLOCK ordens_bloqueadas_config tradeability=0.344
  - XAI: BLOCK AUDCAD H1 SELL: tradeability=0.344, consensus=0.187, conflito=0.087. Bloqueio dominante: context_engine:contexto_fraco:0.35.
- 2026-05-21T19:40:36.324415 strategy3 AUDCAD M30 BUY: BLOCK ordens_bloqueadas_config tradeability=0.393
  - XAI: BLOCK AUDCAD M30 BUY: tradeability=0.393, consensus=0.182, conflito=0.087. Bloqueio dominante: context_engine:contexto_fraco:0.35.
- 2026-05-21T19:40:34.152306 strategy2 AUDCAD M30 BUY: BLOCK ordens_bloqueadas_config tradeability=0.393
  - XAI: BLOCK AUDCAD M30 BUY: tradeability=0.393, consensus=0.182, conflito=0.087. Bloqueio dominante: context_engine:contexto_fraco:0.35.
- 2026-05-21T19:40:32.087321 strategy1 AUDCAD M30 BUY: BLOCK ordens_bloqueadas_config tradeability=0.393
  - XAI: BLOCK AUDCAD M30 BUY: tradeability=0.393, consensus=0.182, conflito=0.087. Bloqueio dominante: context_engine:contexto_fraco:0.35.
- 2026-05-21T19:40:30.006933 strategy3 AUDCAD M15 SELL: BLOCK ordens_bloqueadas_config tradeability=0.318
  - XAI: BLOCK AUDCAD M15 SELL: tradeability=0.318, consensus=0.184, conflito=0.086. Bloqueio dominante: context_engine:contexto_fraco:0.35.
- 2026-05-21T19:40:28.309639 strategy2 AUDCAD M15 SELL: BLOCK ordens_bloqueadas_config tradeability=0.318
  - XAI: BLOCK AUDCAD M15 SELL: tradeability=0.318, consensus=0.184, conflito=0.086. Bloqueio dominante: context_engine:contexto_fraco:0.35.
- 2026-05-21T19:40:26.561051 strategy1 AUDCAD M15 SELL: BLOCK ordens_bloqueadas_config tradeability=0.318
  - XAI: BLOCK AUDCAD M15 SELL: tradeability=0.318, consensus=0.184, conflito=0.086. Bloqueio dominante: context_engine:contexto_fraco:0.35.
- 2026-05-21T19:40:20.735723 strategy3 NZDJPY M30 SELL: BLOCK ordens_bloqueadas_config tradeability=0.352
  - XAI: BLOCK NZDJPY M30 SELL: tradeability=0.352, consensus=0.180, conflito=0.087. Bloqueio dominante: context_engine:contexto_fraco:0.35.
- 2026-05-21T19:40:17.914187 strategy2 NZDJPY M30 SELL: BLOCK ordens_bloqueadas_config tradeability=0.352
  - XAI: BLOCK NZDJPY M30 SELL: tradeability=0.352, consensus=0.180, conflito=0.087. Bloqueio dominante: context_engine:contexto_fraco:0.35.
- 2026-05-21T19:40:15.654199 strategy1 NZDJPY M30 SELL: BLOCK ordens_bloqueadas_config tradeability=0.352
  - XAI: BLOCK NZDJPY M30 SELL: tradeability=0.352, consensus=0.180, conflito=0.087. Bloqueio dominante: context_engine:contexto_fraco:0.35.