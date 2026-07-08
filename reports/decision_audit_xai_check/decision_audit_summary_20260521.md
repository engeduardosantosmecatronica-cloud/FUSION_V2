# Decision Audit Summary

- Eventos: 15152
- Ativos: 28
- Estrategias: 4
- Tradeability medio: 0.378

## Decisoes

- BLOCK: 15118
- ALLOW: 34

## Motivos

- preco_candle_nao_confirmado: 1836
- autotrading_desativado_terminal: 1332
- ema_nao_alinhada: 930
- macro_fluxo_contra:macro_neutro:score=0.033: 483
- macro_fluxo_contra:macro_contra:SELL:score=-0.790: 477
- macro_fluxo_contra:macro_contra:BUY:score=0.883: 344
- macro_fluxo_contra:macro_contra:SELL:score=-1.000: 336
- macro_fluxo_contra:macro_contra:BUY:score=0.930: 330
- macro_fluxo_contra:macro_neutro:score=0.173: 291
- macro_fluxo_contra:macro_contra:BUY:score=0.341: 283
- macro_fluxo_contra:macro_contra:BUY:score=0.450: 268
- macro_fluxo_contra:macro_contra:SELL:score=-0.850: 213
- macro_fluxo_contra:macro_neutro:score=-0.036: 207
- macro_fluxo_contra:macro_neutro:score=0.193: 201
- macro_fluxo_contra:macro_contra:BUY:score=1.000: 198
- macro_fluxo_contra:macro_contra:SELL:score=-0.750: 195
- macro_fluxo_contra:macro_contra:BUY:score=0.300: 192
- macro_fluxo_contra:macro_contra:BUY:score=0.201: 192
- macro_fluxo_contra:macro_contra:BUY:score=0.233: 184
- macro_fluxo_contra:macro_neutro:score=0.053: 177
- macro_fluxo_contra:macro_contra:BUY:score=0.828: 150
- macro_fluxo_contra:macro_contra:BUY:score=0.290: 144
- macro_fluxo_contra:macro_neutro:score=-0.014: 132
- macro_fluxo_contra:macro_contra:BUY:score=0.206: 132
- macro_fluxo_contra:macro_neutro:score=-0.067: 129
- macro_fluxo_contra:macro_neutro:score=0.147: 126
- macro_fluxo_contra:macro_neutro:score=-0.121: 123
- macro_fluxo_contra:macro_neutro:score=0.030: 120
- macro_fluxo_contra:macro_neutro:score=-0.150: 115
- macro_fluxo_contra:macro_neutro:score=-0.007: 114

## Engines

- candle_price BUY: 1464
- candle_price SELL: 1336
- confidence_calibration SELL: 3394
- confidence_calibration NEUTRAL: 1103
- confidence_calibration BUY: 526
- consensus_engine NEUTRAL: 3623
- consensus_engine SELL: 1174
- consensus_engine BUY: 393
- context_engine NEUTRAL: 2711
- context_engine SELL: 1328
- context_engine BUY: 1154
- ema_alignment BUY: 651
- ema_alignment SELL: 313
- entry_timing SELL: 3713
- entry_timing BUY: 1354
- execution_engine NEUTRAL: 3710
- execution_engine BUY: 172
- execution_engine SELL: 142
- feature_engineering NEUTRAL: 2839
- macro_flow SELL: 5560
- macro_flow BUY: 5325
- macro_flow NEUTRAL: 2933
- market_briefing NEUTRAL: 7194
- market_regime NEUTRAL: 9630
- market_regime SELL: 1150
- market_regime BUY: 947
- market_structure NEUTRAL: 6887
- meta_model_ensemble NEUTRAL: 3857
- opportunity_engine NEUTRAL: 3567
- opportunity_engine SELL: 1174
- opportunity_engine BUY: 449
- portfolio_correlation NEUTRAL: 2874
- portfolio_correlation BUY: 2127
- portfolio_correlation SELL: 479
- portfolio_exposure BUY: 4821
- portfolio_exposure SELL: 1508
- risk_engine NEUTRAL: 4024
- session_context NEUTRAL: 7841
- volatility_engine NEUTRAL: 7841

## Ultimos eventos

- 2026-05-21T18:19:13.192073 strategy1 CADJPY H4 SELL: BLOCK correlacao_prejuizo:AUDJPY:SELL:profit=-4.65:corr=0.77:similaridade=0.77:sem_reversao=M5_candle,M15_candle+ema tradeability=0.415
- 2026-05-21T18:19:10.462050 strategy3 CADJPY M15 SELL: BLOCK correlacao_prejuizo:AUDJPY:SELL:profit=-4.65:corr=0.77:similaridade=0.77:sem_reversao=M5_candle,M15_candle+ema tradeability=0.374
- 2026-05-21T18:19:07.890639 strategy2 CADJPY M15 SELL: BLOCK correlacao_prejuizo:AUDJPY:SELL:profit=-4.65:corr=0.77:similaridade=0.77:sem_reversao=M5_candle,M15_candle+ema tradeability=0.374
- 2026-05-21T18:19:06.030459 strategy1 CADJPY M15 SELL: BLOCK correlacao_prejuizo:AUDJPY:SELL:profit=-4.65:corr=0.77:similaridade=0.77:sem_reversao=M5_candle,M15_candle+ema tradeability=0.374
- 2026-05-21T18:19:02.215398 strategy3 AUDUSD H1 SELL: BLOCK macro_fluxo_contra:macro_neutro:score=0.033 tradeability=0.365
- 2026-05-21T18:18:59.783063 strategy2 AUDUSD H1 SELL: BLOCK macro_fluxo_contra:macro_neutro:score=0.033 tradeability=0.365
- 2026-05-21T18:18:57.269288 strategy1 AUDUSD H1 SELL: BLOCK macro_fluxo_contra:macro_neutro:score=0.033 tradeability=0.365
- 2026-05-21T18:18:54.281355 strategy1 AUDUSD M30 SELL: BLOCK macro_fluxo_contra:macro_contra:BUY:score=0.201 tradeability=0.335
- 2026-05-21T18:18:49.531483 strategy1 AUDNZD H4 BUY: BLOCK preco_candle_nao_confirmado tradeability=0.515
- 2026-05-21T18:18:47.184123 strategy3 AUDNZD H1 BUY: BLOCK macro_fluxo_contra:macro_neutro:score=-0.067 tradeability=0.454
- 2026-05-21T18:18:44.624404 strategy2 AUDNZD H1 BUY: BLOCK macro_fluxo_contra:macro_neutro:score=-0.067 tradeability=0.454
- 2026-05-21T18:18:41.731800 strategy1 AUDNZD H1 BUY: BLOCK macro_fluxo_contra:macro_neutro:score=-0.067 tradeability=0.454
- 2026-05-21T18:18:38.417773 strategy1 AUDJPY H4 SELL: BLOCK macro_fluxo_contra:macro_contra:BUY:score=0.883 tradeability=0.361
- 2026-05-21T18:18:35.777956 strategy3 AUDJPY M30 SELL: BLOCK macro_fluxo_contra:macro_contra:BUY:score=0.263 tradeability=0.330
- 2026-05-21T18:18:32.582654 strategy2 AUDJPY M30 SELL: BLOCK macro_fluxo_contra:macro_contra:BUY:score=0.263 tradeability=0.330
- 2026-05-21T18:18:30.285341 strategy1 AUDJPY M30 SELL: BLOCK macro_fluxo_contra:macro_contra:BUY:score=0.263 tradeability=0.330
- 2026-05-21T18:18:25.875795 strategy3 AUDCAD H1 SELL: BLOCK macro_fluxo_contra:macro_contra:BUY:score=0.293 tradeability=0.342
- 2026-05-21T18:18:23.396477 strategy2 AUDCAD H1 SELL: BLOCK macro_fluxo_contra:macro_contra:BUY:score=0.293 tradeability=0.342
- 2026-05-21T18:18:21.128621 strategy1 AUDCAD H1 SELL: BLOCK macro_fluxo_contra:macro_contra:BUY:score=0.293 tradeability=0.342
- 2026-05-21T18:18:18.296646 strategy3 AUDCAD M15 SELL: BLOCK macro_fluxo_contra:macro_contra:BUY:score=0.497 tradeability=0.309
- 2026-05-21T18:18:15.139311 strategy2 AUDCAD M15 SELL: BLOCK macro_fluxo_contra:macro_contra:BUY:score=0.497 tradeability=0.309
- 2026-05-21T18:18:12.343798 strategy1 AUDCAD M15 SELL: BLOCK macro_fluxo_contra:macro_contra:BUY:score=0.497 tradeability=0.309
- 2026-05-21T18:18:05.147972 strategy3 NZDJPY M30 SELL: BLOCK macro_fluxo_contra:macro_contra:BUY:score=0.852 tradeability=0.353
- 2026-05-21T18:18:02.423461 strategy2 NZDJPY M30 SELL: BLOCK macro_fluxo_contra:macro_contra:BUY:score=0.852 tradeability=0.353
- 2026-05-21T18:17:59.481232 strategy1 NZDJPY M30 SELL: BLOCK macro_fluxo_contra:macro_contra:BUY:score=0.852 tradeability=0.353
- 2026-05-21T18:17:56.081444 strategy3 NZDJPY M15 SELL: BLOCK macro_fluxo_contra:macro_contra:BUY:score=0.852 tradeability=0.423
- 2026-05-21T18:17:53.599989 strategy2 NZDJPY M15 SELL: BLOCK macro_fluxo_contra:macro_contra:BUY:score=0.852 tradeability=0.423
- 2026-05-21T18:17:51.246283 strategy1 NZDJPY M15 SELL: BLOCK macro_fluxo_contra:macro_contra:BUY:score=0.852 tradeability=0.423
- 2026-05-21T18:17:46.915691 strategy3 EURUSD M15 SELL: BLOCK preco_candle_nao_confirmado tradeability=0.422
- 2026-05-21T18:17:43.833795 strategy2 EURUSD M15 SELL: BLOCK preco_candle_nao_confirmado tradeability=0.422