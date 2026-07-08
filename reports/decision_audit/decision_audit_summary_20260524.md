# Decision Audit Summary

- Eventos: 4477
- Ativos: 28
- Estrategias: 4
- Tradeability medio: 0.418

## Decisoes

- BLOCK: 4477

## Motivos

- portfolio_exposure:losing_currency_overexposure: 710
- macro_fluxo_contra:macro_contra:BUY:score=1.000: 576
- volatility_engine:PANIC_VOLATILITY: 352
- macro_fluxo_contra:macro_contra:SELL:score=-1.000: 221
- macro_fluxo_contra:macro_contra:BUY:score=0.421: 121
- sell_ignored:gold_s4_buy_only: 118
- macro_fluxo_contra:macro_neutro:score=0.064: 97
- setup_block:insidebar_false: 84
- macro_fluxo_contra:macro_neutro:score=0.017: 78
- macro_fluxo_contra:macro_contra:BUY:score=0.910: 78
- macro_fluxo_contra:macro_neutro:score=0.277: 75
- macro_fluxo_contra:macro_contra:BUY:score=0.454: 74
- macro_fluxo_contra:macro_neutro:score=-0.189: 66
- macro_fluxo_contra:macro_contra:BUY:score=0.803: 65
- macro_fluxo_contra:macro_neutro:score=-0.050: 48
- macro_fluxo_contra:macro_contra:BUY:score=0.964: 45
- macro_fluxo_contra:macro_contra:BUY:score=0.887: 45
- macro_fluxo_contra:macro_contra:BUY:score=0.950: 43
- macro_fluxo_contra:macro_neutro:score=-0.006: 42
- macro_fluxo_contra:macro_contra:BUY:score=0.472: 42
- macro_fluxo_contra:macro_neutro:score=-0.194: 33
- macro_fluxo_contra:macro_contra:BUY:score=0.843: 30
- macro_fluxo_contra:macro_contra:SELL:score=-0.217: 30
- macro_fluxo_contra:macro_contra:BUY:score=0.881: 30
- macro_fluxo_contra:macro_neutro:score=-0.217: 30
- setup_block:aguardando_rompimento_mae: 27
- macro_fluxo_contra:macro_contra:BUY:score=0.433: 27
- macro_fluxo_contra:macro_contra:BUY:score=0.320: 26
- macro_fluxo_contra:macro_contra:BUY:score=0.487: 23
- macro_fluxo_contra:macro_contra:SELL:score=-0.228: 21

## XAI - Faixa de Confianca

- baixa: 3144
- fraca: 776
- media: 557

## Engines

- confidence_calibration SELL: 3297
- confidence_calibration BUY: 1180
- consensus_engine NEUTRAL: 2804
- consensus_engine SELL: 957
- consensus_engine BUY: 716
- context_engine NEUTRAL: 1623
- context_engine BUY: 1520
- context_engine SELL: 1334
- entry_timing SELL: 3038
- entry_timing BUY: 1439
- execution_engine NEUTRAL: 4184
- execution_engine SELL: 159
- execution_engine BUY: 134
- feature_engineering NEUTRAL: 4477
- macro_flow BUY: 2144
- macro_flow SELL: 1175
- macro_flow NEUTRAL: 577
- market_briefing NEUTRAL: 4477
- market_regime NEUTRAL: 2897
- market_regime BUY: 1225
- market_regime SELL: 355
- market_structure NEUTRAL: 4477
- meta_model_ensemble NEUTRAL: 4477
- portfolio_correlation NEUTRAL: 446
- portfolio_correlation BUY: 280
- portfolio_correlation SELL: 108
- portfolio_exposure BUY: 2008
- portfolio_exposure SELL: 1049
- risk_engine NEUTRAL: 446
- session_context NEUTRAL: 4477
- volatility_engine NEUTRAL: 4248

## Ultimos eventos

- 2026-05-24T22:14:42.632233 strategy2 AUDCAD H1 SELL: BLOCK macro_fluxo_contra:macro_contra:BUY:score=1.000 tradeability=0.344
  - XAI: BLOCK AUDCAD H1 SELL: tradeability=0.344, consensus=0.180, conflito=0.341. Bloqueio dominante: macro_flow:macro_contra:BUY.
- 2026-05-24T22:14:39.801737 strategy1 AUDCAD H1 SELL: BLOCK macro_fluxo_contra:macro_contra:BUY:score=1.000 tradeability=0.344
  - XAI: BLOCK AUDCAD H1 SELL: tradeability=0.344, consensus=0.180, conflito=0.341. Bloqueio dominante: macro_flow:macro_contra:BUY.
- 2026-05-24T22:14:36.793552 strategy3 AUDCAD M30 BUY: BLOCK risk_engine:perda_flutuante_critica:15.35% tradeability=0.525
  - XAI: BLOCK AUDCAD M30 BUY: tradeability=0.525, consensus=0.417, conflito=0.065. Bloqueio dominante: risk_engine:perda_flutuante_critica:15.35%.
- 2026-05-24T22:14:34.014957 strategy2 AUDCAD M30 BUY: BLOCK risk_engine:perda_flutuante_critica:15.38% tradeability=0.525
  - XAI: BLOCK AUDCAD M30 BUY: tradeability=0.525, consensus=0.417, conflito=0.065. Bloqueio dominante: risk_engine:perda_flutuante_critica:15.38%.
- 2026-05-24T22:14:31.114684 strategy1 AUDCAD M30 BUY: BLOCK risk_engine:perda_flutuante_critica:15.36% tradeability=0.525
  - XAI: BLOCK AUDCAD M30 BUY: tradeability=0.525, consensus=0.417, conflito=0.065. Bloqueio dominante: risk_engine:perda_flutuante_critica:15.36%.
- 2026-05-24T22:14:28.311955 strategy3 AUDCAD M15 SELL: BLOCK macro_fluxo_contra:macro_contra:BUY:score=1.000 tradeability=0.326
  - XAI: BLOCK AUDCAD M15 SELL: tradeability=0.326, consensus=0.173, conflito=0.333. Bloqueio dominante: macro_flow:macro_contra:BUY.
- 2026-05-24T22:14:25.463295 strategy2 AUDCAD M15 SELL: BLOCK macro_fluxo_contra:macro_contra:BUY:score=1.000 tradeability=0.326
  - XAI: BLOCK AUDCAD M15 SELL: tradeability=0.326, consensus=0.173, conflito=0.333. Bloqueio dominante: macro_flow:macro_contra:BUY.
- 2026-05-24T22:14:23.605701 strategy1 AUDCAD M15 SELL: BLOCK macro_fluxo_contra:macro_contra:BUY:score=1.000 tradeability=0.326
  - XAI: BLOCK AUDCAD M15 SELL: tradeability=0.326, consensus=0.173, conflito=0.333. Bloqueio dominante: macro_flow:macro_contra:BUY.
- 2026-05-24T22:14:19.181594 strategy4 XAUUSD H4 SELL: BLOCK sell_ignored:gold_s4_buy_only tradeability=0.382
  - XAI: BLOCK XAUUSD H4 SELL: tradeability=0.382, consensus=0.206, conflito=0.107. Bloqueio dominante: context_engine:contexto_fraco:0.46.
- 2026-05-24T22:14:17.113487 strategy4 XAUUSD H1 BUY: BLOCK setup_block:aguardando_rompimento_mae tradeability=0.443
  - XAI: BLOCK XAUUSD H1 BUY: tradeability=0.443, consensus=0.208, conflito=0.098. Bloqueio dominante: context_engine:contexto_fraco:0.46.
- 2026-05-24T22:14:15.000895 strategy4 XAUUSD M30 BUY: BLOCK setup_block:insidebar_false tradeability=0.441
  - XAI: BLOCK XAUUSD M30 BUY: tradeability=0.441, consensus=0.334, conflito=0.193. Bloqueio dominante: market_structure:M5:consolidacao.
- 2026-05-24T22:14:12.891625 strategy4 XAUUSD M15 BUY: BLOCK setup_block:insidebar_false tradeability=0.401
  - XAI: BLOCK XAUUSD M15 BUY: tradeability=0.401, consensus=0.192, conflito=0.093. Bloqueio dominante: context_engine:contexto_fraco:0.46.
- 2026-05-24T22:14:11.171382 strategy4 XAUUSD M5 SELL: BLOCK sell_ignored:gold_s4_buy_only tradeability=0.357
  - XAI: BLOCK XAUUSD M5 SELL: tradeability=0.357, consensus=0.188, conflito=0.097. Bloqueio dominante: context_engine:contexto_fraco:0.45.
- 2026-05-24T22:14:07.965843 strategy3 USDCHF M30 SELL: BLOCK risk_engine:perda_flutuante_critica:15.40% tradeability=0.421
  - XAI: BLOCK USDCHF M30 SELL: tradeability=0.421, consensus=0.358, conflito=0.146. Bloqueio dominante: entry_timing:vender_fundo_sem_rompimento_validado.
- 2026-05-24T22:14:05.973705 strategy2 USDCHF M30 SELL: BLOCK risk_engine:perda_flutuante_critica:15.40% tradeability=0.421
  - XAI: BLOCK USDCHF M30 SELL: tradeability=0.421, consensus=0.358, conflito=0.146. Bloqueio dominante: entry_timing:vender_fundo_sem_rompimento_validado.
- 2026-05-24T22:14:03.232140 strategy1 USDCHF M30 SELL: BLOCK risk_engine:perda_flutuante_critica:15.24% tradeability=0.421
  - XAI: BLOCK USDCHF M30 SELL: tradeability=0.421, consensus=0.358, conflito=0.146. Bloqueio dominante: entry_timing:vender_fundo_sem_rompimento_validado.
- 2026-05-24T22:13:59.975349 strategy3 NZDSGD H4 BUY: BLOCK correlacao_prejuizo:EURNZD:SELL:profit=-3.44:corr=-0.74:similaridade=0.74:sem_reversao=M5_candle+ema,M15_ema tradeability=0.392
  - XAI: BLOCK NZDSGD H4 BUY: tradeability=0.392, consensus=0.376, conflito=0.150. Bloqueio dominante: portfolio_correlation:correlacao_prejuizo.
- 2026-05-24T22:13:57.789175 strategy2 NZDSGD H4 BUY: BLOCK correlacao_prejuizo:EURNZD:SELL:profit=-3.48:corr=-0.74:similaridade=0.74:sem_reversao=M5_candle+ema,M15_ema tradeability=0.392
  - XAI: BLOCK NZDSGD H4 BUY: tradeability=0.392, consensus=0.376, conflito=0.150. Bloqueio dominante: portfolio_correlation:correlacao_prejuizo.
- 2026-05-24T22:13:55.125667 strategy1 NZDSGD H4 BUY: BLOCK correlacao_prejuizo:EURNZD:SELL:profit=-3.45:corr=-0.74:similaridade=0.74:sem_reversao=M5_candle+ema,M15_ema tradeability=0.392
  - XAI: BLOCK NZDSGD H4 BUY: tradeability=0.392, consensus=0.376, conflito=0.150. Bloqueio dominante: portfolio_correlation:correlacao_prejuizo.
- 2026-05-24T22:13:52.738499 strategy3 NZDSGD M30 SELL: BLOCK volatility_engine:PANIC_VOLATILITY tradeability=0.353
  - XAI: BLOCK NZDSGD M30 SELL: tradeability=0.353, consensus=0.178, conflito=0.084. Bloqueio dominante: context_engine:contexto_fraco:0.47.
- 2026-05-24T22:13:50.221425 strategy2 NZDSGD M30 SELL: BLOCK volatility_engine:PANIC_VOLATILITY tradeability=0.353
  - XAI: BLOCK NZDSGD M30 SELL: tradeability=0.353, consensus=0.178, conflito=0.084. Bloqueio dominante: context_engine:contexto_fraco:0.47.
- 2026-05-24T22:13:47.519848 strategy1 NZDSGD M30 SELL: BLOCK volatility_engine:PANIC_VOLATILITY tradeability=0.353
  - XAI: BLOCK NZDSGD M30 SELL: tradeability=0.353, consensus=0.178, conflito=0.084. Bloqueio dominante: context_engine:contexto_fraco:0.47.
- 2026-05-24T22:13:40.041636 strategy3 NZDJPY M30 SELL: BLOCK macro_fluxo_contra:macro_contra:BUY:score=0.472 tradeability=0.388
  - XAI: BLOCK NZDJPY M30 SELL: tradeability=0.388, consensus=0.182, conflito=0.143. Bloqueio dominante: market_structure:M5:consolidacao.
- 2026-05-24T22:13:37.788249 strategy2 NZDJPY M30 SELL: BLOCK macro_fluxo_contra:macro_contra:BUY:score=0.472 tradeability=0.388
  - XAI: BLOCK NZDJPY M30 SELL: tradeability=0.388, consensus=0.182, conflito=0.143. Bloqueio dominante: market_structure:M5:consolidacao.
- 2026-05-24T22:13:35.251592 strategy1 NZDJPY M30 SELL: BLOCK macro_fluxo_contra:macro_contra:BUY:score=0.472 tradeability=0.388
  - XAI: BLOCK NZDJPY M30 SELL: tradeability=0.388, consensus=0.182, conflito=0.143. Bloqueio dominante: market_structure:M5:consolidacao.
- 2026-05-24T22:13:32.148710 strategy3 NZDJPY M15 SELL: BLOCK macro_fluxo_contra:macro_contra:BUY:score=0.501 tradeability=0.450
  - XAI: BLOCK NZDJPY M15 SELL: tradeability=0.450, consensus=0.242, conflito=0.144. Bloqueio dominante: context_engine:contexto_fraco:0.55.
- 2026-05-24T22:13:29.233862 strategy2 NZDJPY M15 SELL: BLOCK macro_fluxo_contra:macro_contra:BUY:score=0.501 tradeability=0.450
  - XAI: BLOCK NZDJPY M15 SELL: tradeability=0.450, consensus=0.242, conflito=0.144. Bloqueio dominante: context_engine:contexto_fraco:0.55.
- 2026-05-24T22:13:27.399645 strategy1 NZDJPY M15 SELL: BLOCK macro_fluxo_contra:macro_contra:BUY:score=0.501 tradeability=0.450
  - XAI: BLOCK NZDJPY M15 SELL: tradeability=0.450, consensus=0.242, conflito=0.144. Bloqueio dominante: context_engine:contexto_fraco:0.55.
- 2026-05-24T22:13:23.750645 strategy3 NZDCAD M15 SELL: BLOCK macro_fluxo_contra:macro_contra:BUY:score=1.000 tradeability=0.353
  - XAI: BLOCK NZDCAD M15 SELL: tradeability=0.353, consensus=0.223, conflito=0.266. Bloqueio dominante: macro_flow:macro_contra:BUY.
- 2026-05-24T22:13:21.994343 strategy2 NZDCAD M15 SELL: BLOCK macro_fluxo_contra:macro_contra:BUY:score=1.000 tradeability=0.353
  - XAI: BLOCK NZDCAD M15 SELL: tradeability=0.353, consensus=0.223, conflito=0.266. Bloqueio dominante: macro_flow:macro_contra:BUY.