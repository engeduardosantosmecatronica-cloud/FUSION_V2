# Analise de Neutros Validados Manualmente - 2026-05-28

Casos abaixo consideram apenas linhas marcadas com `*`, onde a IA externa acertou o movimento, mas o Fusion ficou `neutro`.

- Oportunidades perdidas unicas: 92
- Neutros que evitaram erro da IA externa (`x`): 34

## Prioridade Por Ativo
- CHFDKK: 5 casos | M5=BUY, M15=BUY, M30=BUY, H1=BUY, D1=BUY
- NZDCHF: 5 casos | M5=BUY, M15=BUY, M30=BUY, H1=BUY, D1=BUY
- AUDJPY: 4 casos | M5=BUY, M15=BUY, H4=BUY, D1=BUY
- AUDNZD: 4 casos | M5=SELL, M15=SELL, H4=SELL, D1=SELL
- EURAUD: 4 casos | M5=SELL, M15=SELL, M30=SELL, H1=SELL
- EURCHF: 4 casos | M5=SELL, M15=SELL, M30=SELL, D1=SELL
- EURNZD: 4 casos | M5=SELL, M15=SELL, M30=SELL, D1=SELL
- EURPLN: 4 casos | M5=SELL, M15=SELL, M30=SELL, H1=SELL
- GBPAUD: 4 casos | M5=SELL, M15=SELL, M30=SELL, D1=SELL
- NZDUSD: 4 casos | M5=BUY, M15=BUY, M30=BUY, D1=BUY
- USDJPY: 4 casos | M5=BUY, M15=BUY, M30=BUY, D1=BUY
- AUDSEK: 3 casos | M5=SELL, M15=SELL, D1=SELL
- AUDSGD: 3 casos | M5=BUY, M15=BUY, M30=BUY
- AUDUSD: 3 casos | M5=BUY, M15=BUY, M30=BUY
- CADJPY: 3 casos | M5=SELL, M15=SELL, D1=BUY
- EURUSD: 3 casos | M5=BUY, M15=BUY, D1=SELL
- GBPCHF: 3 casos | M5=SELL, M15=SELL, H1=BUY
- GBPUSD: 3 casos | M5=BUY, M15=BUY, M30=BUY
- GOLD: 3 casos | M5=BUY, H4=SELL, D1=SELL
- NZDCAD: 3 casos | M5=BUY, M15=BUY, D1=BUY
- NZDJPY: 3 casos | M5=BUY, M30=BUY, D1=BUY
- NZDSGD: 3 casos | M5=BUY, M15=BUY, D1=BUY
- AUDNOK: 2 casos | M5=BUY, M15=BUY
- BTCUSD: 2 casos | M5=SELL, D1=BUY
- CHFNOK: 2 casos | M5=BUY, D1=BUY
- EURMXN: 2 casos | M5=SELL, D1=SELL
- EURNOK: 2 casos | M5=SELL, M15=SELL
- GBPJPY: 2 casos | M5=BUY, D1=BUY
- EURSEK: 1 casos | M5=SELL

## Recomendacoes de Liberacao de Neutro
- Nao liberar neutro isolado em M5/M15 sem confirmacao de M30/H1.
- Liberar neutro como direcional apenas se `timeframe_consensus` e `market_alignment` apontarem a mesma direcao validada.
- Para H4/D1 neutros, exigir `macro_flow` favoravel e `market_structure` sem conflito estrutural.
- Para ativos com 4+ oportunidades perdidas, reduzir neutralidade por ativo/timeframe via criterio recorrente, nao por inversao cega.
- Se o Fusion estiver neutro mas `Context Brain` classificar `strong_institutional_alignment`, permitir sinal experimental em shadow antes de block.

