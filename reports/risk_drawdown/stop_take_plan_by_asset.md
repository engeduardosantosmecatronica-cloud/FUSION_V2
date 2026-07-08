# Plano de SL/TP por ativo baseado em drawdown

Regra operacional: stop menor que 15 pontos e inviavel (`MIN_OPERABLE_SL = 15`). Qualquer otimizacao com `SL < 15` foi descartada da recomendacao operacional.

`conservative_sl_from_p95_points` = max(15, P95 do drawdown liquido do ativo + 10%), arredondado para cima em blocos de 5 pontos.
`disaster_sl_from_worst_points` = pior drawdown observado + 5%, arredondado para cima, nunca menor que o SL conservador. Use como limite maximo de emergencia, nao como stop normal.

| Ativo | Sinais | Pior DD | P95 DD | SL conservador | SL desastre | Melhor grupo operavel | TP opt | SL opt | Descartou SL<15? | Recomendado? | Nota |
|---|---:|---:|---:|---:|---:|---|---:|---:|---|---|---|
| AUDJPY | 18 | 149.0 | 149.0 | 165 | 165 | H1 BUY | 5.0 | 15.0 | True | False | Melhor antigo usava SL < 15 e foi descartado; alternativa operavel ainda nao passou criterios |
| CADCHF | 9 | 64.0 | 64.0 | 75 | 75 |  |  |  | False | False | Nao passou criterios; usar apenas como limite de risco ou exigir confirmacao extra |
| CHFJPY | 32 | 90.0 | 87.0 | 100 | 100 | M15 BUY | 5.0 | 100.0 | False | False | Nao passou criterios; usar apenas como limite de risco ou exigir confirmacao extra |
| EURCAD | 126 | 263.0 | 243.0 | 270 | 280 | H4 BUY | 30.0 | 40.0 | True | False | Melhor antigo usava SL < 15 e foi descartado; alternativa operavel ainda nao passou criterios |
| EURGBP | 26 | 52.0 | 51.25 | 60 | 60 | H4 SELL | 30.0 | 70.0 | False | True | OK para shadow/validacao com SL operavel |
| EURNZD | 16 | 96.0 | 96.0 | 110 | 110 | H1 BUY | 5.0 | 15.0 | True | False | Melhor antigo usava SL < 15 e foi descartado; alternativa operavel ainda nao passou criterios |
| EURUSD | 41 | 107.0 | 103.0 | 115 | 115 | H1 BUY | 25.0 | 15.0 | True | False | Melhor antigo usava SL < 15 e foi descartado; alternativa operavel ainda nao passou criterios |
| GBPCHF | 3 | 25.0 | 25.0 | 30 | 30 |  |  |  | False | False | Nao passou criterios; usar apenas como limite de risco ou exigir confirmacao extra |
| GBPUSD | 46 | 126.0 | 125.0 | 140 | 140 | H1 BUY | 15.0 | 15.0 | True | False | Melhor antigo usava SL < 15 e foi descartado; alternativa operavel ainda nao passou criterios |
| NZDCHF | 6 | 68.0 | 68.0 | 75 | 75 |  |  |  | False | False | Nao passou criterios; usar apenas como limite de risco ou exigir confirmacao extra |
| NZDSGD | 6 | 67.0 | 67.0 | 75 | 75 |  |  |  | False | False | Nao passou criterios; usar apenas como limite de risco ou exigir confirmacao extra |
| NZDUSD | 35 | 108.0 | 89.8 | 100 | 115 | H1 BUY | 5.0 | 15.0 | True | False | Melhor antigo usava SL < 15 e foi descartado; alternativa operavel ainda nao passou criterios |
| USDCHF | 3 | 36.0 | 36.0 | 40 | 40 |  |  |  | False | False | Nao passou criterios; usar apenas como limite de risco ou exigir confirmacao extra |
