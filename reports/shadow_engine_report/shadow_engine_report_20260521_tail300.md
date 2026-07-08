# Shadow Engine Report

- Eventos: 300
- Ativos: 14
- Eventos com alerta shadow: 287
- Tradeability medio: 0.427

## Decisoes

- BLOCK: 298
- ALLOW: 2

## Alertas Por Engine

- portfolio_exposure / currency_overexposure: 260
- market_structure / shadow: 229
- opportunity_engine / tradable: 162
- consensus_engine / weak: 113
- context_engine / conflicted: 103
- consensus_engine / moderate: 80
- consensus_engine / conflicted: 52
- context_engine / weak: 52
- opportunity_engine / conflicted: 52
- market_regime / RANGE: 45
- opportunity_engine / marginal: 44
- market_regime / TREND: 42
- portfolio_exposure / currency_warning: 21
- entry_timing / avoid_selling_bottom: 14
- consensus_engine / strong_consensus: 13
- market_regime / PANIC_VOLATILITY: 12
- volatility_engine / PANIC_VOLATILITY: 12
- entry_timing / avoid_buying_top: 3
- market_regime / EXPANSION: 2

## Bloqueios Com Tradeability Alto

- 2026-05-21T14:12:28.915191 strategy1 AUDNZD H4 BUY: ema_nao_alinhada tradeability=0.619 shadow=portfolio_exposure,market_structure,consensus_engine,opportunity_engine
- 2026-05-21T14:14:40.322684 strategy1 AUDNZD H4 BUY: ema_nao_alinhada tradeability=0.619 shadow=portfolio_exposure,market_structure,consensus_engine,opportunity_engine
- 2026-05-21T14:17:07.764789 strategy1 AUDNZD H4 BUY: ema_nao_alinhada tradeability=0.619 shadow=portfolio_exposure,market_structure,consensus_engine,opportunity_engine
- 2026-05-21T14:19:19.505799 strategy1 AUDNZD H4 BUY: ema_nao_alinhada tradeability=0.609 shadow=portfolio_exposure,market_structure,consensus_engine,opportunity_engine
- 2026-05-21T14:22:03.653535 strategy1 AUDNZD H4 BUY: ema_nao_alinhada tradeability=0.609 shadow=portfolio_exposure,market_structure,consensus_engine,opportunity_engine
- 2026-05-21T14:12:52.151518 strategy3 CADJPY M30 SELL: correlacao_prejuizo:AUDJPY:SELL:profit=-4.23:corr=0.77:similaridade=0.77:sem_reversao=M5_candle+ema,M15_candle+ema tradeability=0.561 shadow=market_regime,portfolio_exposure,market_structure,consensus_engine,opportunity_engine
- 2026-05-21T14:12:47.443915 strategy1 CADJPY M30 SELL: correlacao_prejuizo:AUDJPY:SELL:profit=-4.27:corr=0.77:similaridade=0.77:sem_reversao=M5_candle+ema,M15_candle+ema tradeability=0.561 shadow=market_regime,portfolio_exposure,market_structure,consensus_engine,opportunity_engine
- 2026-05-21T14:12:50.322334 strategy2 CADJPY M30 SELL: correlacao_prejuizo:AUDJPY:SELL:profit=-4.25:corr=0.77:similaridade=0.77:sem_reversao=M5_candle+ema,M15_candle+ema tradeability=0.561 shadow=market_regime,portfolio_exposure,market_structure,consensus_engine,opportunity_engine

## Entradas Permitidas Com Alerta Shadow

- 2026-05-21T14:15:42.163819 strategy1 EURNZD D1 SELL: shadow=portfolio_exposure,market_structure,consensus_engine,opportunity_engine tradeability=0.434
- 2026-05-21T14:20:18.892006 strategy1 EURNZD D1 SELL: shadow=portfolio_exposure,market_structure,consensus_engine,opportunity_engine tradeability=0.445

## Calibracao

- Eventos calibrados: 15
- Delta medio calibrado-bruto: 0.1473
- Calibracao reduziu probabilidade em: 0 eventos