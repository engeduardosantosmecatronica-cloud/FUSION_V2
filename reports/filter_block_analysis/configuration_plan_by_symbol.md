# Configuration Plan By Symbol

This is a measurement-based plan. It does not change config automatically.

Legend:

- consider_relax: historical H3 outcome is positive and blocks are frequent.
- keep_or_tighten: historical H3 outcome is negative, so the current block is probably useful.
- review_market_alignment: recent structural blocks are high; inspect before relaxing.
- monitor: no enough matched outcome edge, or missing outcome sample.

## AUDCAD
Blocked total: 2399 (BUY 376, SELL 2023); main blocker: macro_fluxo_contra (73.1%).

| TF | Side | Blocks | MA blocks | Top blocker | H3 acc | H3 pts | Action |
|---|---|---:|---:|---|---:|---:|---|
| H1 | SELL | 1035 | 111 | macro_fluxo_contra | 34.98 | -31.24 | keep_or_tighten |
| M15 | SELL | 610 | 16 | macro_fluxo_contra | 33.93 | -17.89 | keep_or_tighten |
| M30 | BUY | 355 | 75 | risk_engine |  |  | review_market_alignment |
| M30 | SELL | 321 | 13 | macro_fluxo_contra |  |  | monitor |
| M5 | SELL | 57 | 0 | macro_fluxo_contra |  |  | monitor |
| M5 | BUY | 21 | 0 | ema_nao_alinhada |  |  | monitor |

## AUDCHF
Blocked total: 81 (BUY 0, SELL 81); main blocker: macro_fluxo_contra (100.0%).

| TF | Side | Blocks | MA blocks | Top blocker | H3 acc | H3 pts | Action |
|---|---|---:|---:|---|---:|---:|---|
| M30 | SELL | 81 | 10 | macro_fluxo_contra |  |  | monitor |

## AUDJPY
Blocked total: 1426 (BUY 0, SELL 1426); main blocker: macro_fluxo_contra (85.4%).

| TF | Side | Blocks | MA blocks | Top blocker | H3 acc | H3 pts | Action |
|---|---|---:|---:|---|---:|---:|---|
| H4 | SELL | 354 | 0 | macro_fluxo_contra | 20.00 | -87.50 | keep_or_tighten |
| M30 | SELL | 1067 | 0 | macro_fluxo_contra |  |  | monitor |
| M5 | SELL | 5 | 0 | macro_fluxo_contra |  |  | monitor |

## AUDNZD
Blocked total: 1258 (BUY 1068, SELL 190); main blocker: macro_fluxo_contra (51.7%).

| TF | Side | Blocks | MA blocks | Top blocker | H3 acc | H3 pts | Action |
|---|---|---:|---:|---|---:|---:|---|
| H4 | BUY | 351 | 0 | ema_nao_alinhada | 100.00 | 279.83 | consider_relax |
| H1 | BUY | 717 | 833 | macro_fluxo_contra | 19.09 | -109.08 | keep_or_tighten |
| M30 | SELL | 190 | 12 | macro_fluxo_contra |  |  | monitor |

## AUDSGD
Blocked total: 849 (BUY 12, SELL 837); main blocker: macro_fluxo_contra (100.0%).

| TF | Side | Blocks | MA blocks | Top blocker | H3 acc | H3 pts | Action |
|---|---|---:|---:|---|---:|---:|---|
| H4 | SELL | 264 | 327 | macro_fluxo_contra | 24.62 | -62.34 | keep_or_tighten |
| H1 | SELL | 201 | 93 | macro_fluxo_contra | 51.52 | -8.89 | keep_or_tighten |
| M30 | SELL | 372 | 0 | macro_fluxo_contra |  |  | monitor |
| M5 | BUY | 12 | 0 | macro_fluxo_contra |  |  | monitor |

## AUDUSD
Blocked total: 1771 (BUY 0, SELL 1771); main blocker: macro_fluxo_contra (76.9%).

| TF | Side | Blocks | MA blocks | Top blocker | H3 acc | H3 pts | Action |
|---|---|---:|---:|---|---:|---:|---|
| H1 | SELL | 1018 | 64 | macro_fluxo_contra | 25.00 | -52.96 | keep_or_tighten |
| M30 | SELL | 734 | 12 | macro_fluxo_contra |  |  | monitor |
| M15 | SELL | 19 | 0 | macro_fluxo_contra |  |  | monitor |

## CADCHF
Blocked total: 285 (BUY 78, SELL 207); main blocker: macro_fluxo_contra (60.0%).

| TF | Side | Blocks | MA blocks | Top blocker | H3 acc | H3 pts | Action |
|---|---|---:|---:|---|---:|---:|---|
| M15 | BUY | 30 | 27 | macro_fluxo_contra | 15.56 | -23.40 | keep_or_tighten |
| H4 | SELL | 204 | 87 | preco_candle_nao_confirmado | 44.21 | 13.42 | review_market_alignment |
| M30 | BUY | 48 | 74 | macro_fluxo_contra |  |  | review_market_alignment |
| M30 | SELL | 3 | 3 | risk_engine |  |  | monitor |

## CADJPY
Blocked total: 2765 (BUY 12, SELL 2753); main blocker: correlacao_prejuizo (74.0%).

| TF | Side | Blocks | MA blocks | Top blocker | H3 acc | H3 pts | Action |
|---|---|---:|---:|---|---:|---:|---|
| M15 | SELL | 1035 | 0 | correlacao_prejuizo | 42.68 | -15.67 | keep_or_tighten |
| H4 | SELL | 1044 | 834 | correlacao_prejuizo | 15.38 | 15.73 | review_market_alignment |
| M30 | SELL | 674 | 0 | correlacao_prejuizo |  |  | monitor |
| M15 | BUY | 12 | 0 | volatility_engine |  |  | monitor |

## CHFJPY
Blocked total: 395 (BUY 237, SELL 158); main blocker: macro_fluxo_contra (80.5%).

| TF | Side | Blocks | MA blocks | Top blocker | H3 acc | H3 pts | Action |
|---|---|---:|---:|---|---:|---:|---|
| M30 | BUY | 237 | 40 | macro_fluxo_contra |  |  | review_market_alignment |
| H1 | SELL | 158 | 56 | macro_fluxo_contra | 52.64 | 5.46 | review_market_alignment |

## EURAUD
Blocked total: 228 (BUY 0, SELL 228); main blocker: correlacao_prejuizo (46.1%).

| TF | Side | Blocks | MA blocks | Top blocker | H3 acc | H3 pts | Action |
|---|---|---:|---:|---|---:|---:|---|
| M30 | SELL | 228 | 9 | correlacao_prejuizo |  |  | monitor |

## EURCAD
Blocked total: 1047 (BUY 1047, SELL 0); main blocker: macro_fluxo_contra (69.3%).

| TF | Side | Blocks | MA blocks | Top blocker | H3 acc | H3 pts | Action |
|---|---|---:|---:|---|---:|---:|---|
| H4 | BUY | 1047 | 294 | macro_fluxo_contra | 31.16 | -86.33 | keep_or_tighten |

## EURCHF
Blocked total: 452 (BUY 452, SELL 0); main blocker: macro_fluxo_contra (90.3%).

| TF | Side | Blocks | MA blocks | Top blocker | H3 acc | H3 pts | Action |
|---|---|---:|---:|---|---:|---:|---|
| H4 | BUY | 372 | 0 | macro_fluxo_contra | 100.00 | 133.05 | consider_relax |
| M30 | BUY | 80 | 75 | volatility_engine |  |  | review_market_alignment |

## EURGBP
Blocked total: 110 (BUY 0, SELL 110); main blocker: preco_candle_nao_confirmado (97.3%).

| TF | Side | Blocks | MA blocks | Top blocker | H3 acc | H3 pts | Action |
|---|---|---:|---:|---|---:|---:|---|
| H4 | SELL | 110 | 105 | preco_candle_nao_confirmado | 92.63 | 58.10 | consider_relax |

## EURJPY
Blocked total: 1836 (BUY 126, SELL 1710); main blocker: preco_candle_nao_confirmado (41.3%).

| TF | Side | Blocks | MA blocks | Top blocker | H3 acc | H3 pts | Action |
|---|---|---:|---:|---|---:|---:|---|
| H4 | SELL | 879 | 60 | ema_nao_alinhada | 60.19 | 21.13 | consider_relax |
| H1 | SELL | 618 | 177 | preco_candle_nao_confirmado | 46.18 | -17.42 | keep_or_tighten |
| M30 | SELL | 213 | 33 | preco_candle_nao_confirmado |  |  | review_market_alignment |
| M30 | BUY | 126 | 63 | macro_fluxo_contra |  |  | review_market_alignment |

## EURNZD
Blocked total: 296 (BUY 0, SELL 296); main blocker: correlacao_prejuizo (70.3%).

| TF | Side | Blocks | MA blocks | Top blocker | H3 acc | H3 pts | Action |
|---|---|---:|---:|---|---:|---:|---|
| D1 | SELL | 296 | 0 | correlacao_prejuizo |  |  | monitor |

## EURUSD
Blocked total: 945 (BUY 513, SELL 432); main blocker: macro_fluxo_contra (41.6%).

| TF | Side | Blocks | MA blocks | Top blocker | H3 acc | H3 pts | Action |
|---|---|---:|---:|---|---:|---:|---|
| M15 | SELL | 432 | 0 | preco_candle_nao_confirmado | 48.63 | -0.03 | keep_or_tighten |
| H1 | BUY | 510 | 948 | macro_fluxo_contra | 54.49 | 16.27 | review_market_alignment |
| M5 | BUY | 3 | 0 | macro_fluxo_contra |  |  | monitor |

## GBPAUD
Blocked total: 201 (BUY 201, SELL 0); main blocker: macro_fluxo_contra (100.0%).

| TF | Side | Blocks | MA blocks | Top blocker | H3 acc | H3 pts | Action |
|---|---|---:|---:|---|---:|---:|---|
| M30 | BUY | 201 | 16 | macro_fluxo_contra |  |  | monitor |

## GBPCAD
Blocked total: 27 (BUY 27, SELL 0); main blocker: correlacao_prejuizo (100.0%).

| TF | Side | Blocks | MA blocks | Top blocker | H3 acc | H3 pts | Action |
|---|---|---:|---:|---|---:|---:|---|
| M5 | BUY | 27 | 0 | correlacao_prejuizo |  |  | monitor |

## GBPCHF
Blocked total: 159 (BUY 159, SELL 0); main blocker: preco_candle_nao_confirmado (66.0%).

| TF | Side | Blocks | MA blocks | Top blocker | H3 acc | H3 pts | Action |
|---|---|---:|---:|---|---:|---:|---|
| H1 | BUY | 117 | 60 | preco_candle_nao_confirmado | 54.69 | 18.39 | review_market_alignment |
| M15 | BUY | 42 | 0 | volatility_engine |  |  | monitor |

## GBPJPY
Blocked total: 441 (BUY 0, SELL 441); main blocker: macro_fluxo_contra (92.1%).

| TF | Side | Blocks | MA blocks | Top blocker | H3 acc | H3 pts | Action |
|---|---|---:|---:|---|---:|---:|---|
| H1 | SELL | 367 | 0 | macro_fluxo_contra | 24.01 | -51.09 | keep_or_tighten |
| H4 | SELL | 35 | 21 | risk_engine | 55.00 | -43.50 | keep_or_tighten |
| M30 | SELL | 39 | 0 | macro_fluxo_contra |  |  | monitor |

## GBPNZD
Blocked total: 237 (BUY 237, SELL 0); main blocker: macro_fluxo_contra (82.3%).

| TF | Side | Blocks | MA blocks | Top blocker | H3 acc | H3 pts | Action |
|---|---|---:|---:|---|---:|---:|---|
| M30 | BUY | 195 | 229 | macro_fluxo_contra |  |  | review_market_alignment |
| M15 | BUY | 42 | 0 | volatility_engine | 45.45 | 27.86 | monitor |

## GBPUSD
Blocked total: 9 (BUY 9, SELL 0); main blocker: macro_fluxo_contra (66.7%).

| TF | Side | Blocks | MA blocks | Top blocker | H3 acc | H3 pts | Action |
|---|---|---:|---:|---|---:|---:|---|
| M5 | BUY | 9 | 0 | macro_fluxo_contra |  |  | monitor |

## NZDCAD
Blocked total: 961 (BUY 725, SELL 236); main blocker: preco_candle_nao_confirmado (34.3%).

| TF | Side | Blocks | MA blocks | Top blocker | H3 acc | H3 pts | Action |
|---|---|---:|---:|---|---:|---:|---|
| H4 | BUY | 721 | 45 | preco_candle_nao_confirmado |  |  | review_market_alignment |
| M15 | SELL | 209 | 0 | macro_fluxo_contra | 55.25 | 1.44 | monitor |
| M5 | SELL | 27 | 0 | macro_fluxo_contra |  |  | monitor |
| H1 | BUY | 4 | 21 | correlacao_prejuizo | 65.69 | 46.81 | review_market_alignment |

## NZDCHF
Blocked total: 3 (BUY 3, SELL 0); main blocker: macro_fluxo_contra (100.0%).

| TF | Side | Blocks | MA blocks | Top blocker | H3 acc | H3 pts | Action |
|---|---|---:|---:|---|---:|---:|---|
| M30 | BUY | 3 | 3 | macro_fluxo_contra |  |  | monitor |

## NZDJPY
Blocked total: 2026 (BUY 0, SELL 2026); main blocker: macro_fluxo_contra (84.2%).

| TF | Side | Blocks | MA blocks | Top blocker | H3 acc | H3 pts | Action |
|---|---|---:|---:|---|---:|---:|---|
| M30 | SELL | 1017 | 136 | macro_fluxo_contra |  |  | review_market_alignment |
| M15 | SELL | 1009 | 0 | macro_fluxo_contra | 60.81 | 1.76 | monitor |

## NZDSGD
Blocked total: 519 (BUY 369, SELL 150); main blocker: correlacao_prejuizo (52.0%).

| TF | Side | Blocks | MA blocks | Top blocker | H3 acc | H3 pts | Action |
|---|---|---:|---:|---|---:|---:|---|
| H4 | BUY | 369 | 488 | correlacao_prejuizo | 56.35 | 194.30 | consider_relax |
| M30 | SELL | 123 | 9 | macro_fluxo_contra |  |  | monitor |
| M15 | SELL | 24 | 15 | macro_fluxo_contra |  |  | monitor |
| M5 | SELL | 3 | 0 | macro_fluxo_contra |  |  | monitor |

## NZDUSD
Blocked total: 138 (BUY 93, SELL 45); main blocker: macro_fluxo_contra (43.5%).

| TF | Side | Blocks | MA blocks | Top blocker | H3 acc | H3 pts | Action |
|---|---|---:|---:|---|---:|---:|---|
| M15 | BUY | 87 | 0 | portfolio_exposure | 34.48 | -7.52 | keep_or_tighten |
| M5 | SELL | 45 | 0 | macro_fluxo_contra |  |  | monitor |
| M5 | BUY | 6 | 0 | ordens_bloqueadas_config |  |  | monitor |

## USDCAD
Blocked total: 69 (BUY 12, SELL 57); main blocker: macro_fluxo_contra (82.6%).

| TF | Side | Blocks | MA blocks | Top blocker | H3 acc | H3 pts | Action |
|---|---|---:|---:|---|---:|---:|---|
| M15 | SELL | 54 | 6 | macro_fluxo_contra |  |  | monitor |
| H1 | BUY | 12 | 54 | portfolio_exposure | 51.22 | 9.06 | review_market_alignment |
| M5 | SELL | 3 | 0 | macro_fluxo_contra |  |  | monitor |

## USDCHF
Blocked total: 179 (BUY 13, SELL 166); main blocker: risk_engine (46.9%).

| TF | Side | Blocks | MA blocks | Top blocker | H3 acc | H3 pts | Action |
|---|---|---:|---:|---|---:|---:|---|
| H1 | BUY | 13 | 0 | macro_fluxo_contra | 52.70 | -104.42 | keep_or_tighten |
| M30 | SELL | 166 | 102 | risk_engine |  |  | review_market_alignment |

## USDJPY
Blocked total: 262 (BUY 262, SELL 0); main blocker: macro_fluxo_contra (59.9%).

| TF | Side | Blocks | MA blocks | Top blocker | H3 acc | H3 pts | Action |
|---|---|---:|---:|---|---:|---:|---|
| M30 | BUY | 246 | 0 | macro_fluxo_contra |  |  | monitor |
| M15 | BUY | 16 | 0 | macro_fluxo_contra |  |  | monitor |

## XAUUSD
Blocked total: 244 (BUY 126, SELL 118); main blocker: sell_ignored (48.4%).

| TF | Side | Blocks | MA blocks | Top blocker | H3 acc | H3 pts | Action |
|---|---|---:|---:|---|---:|---:|---|
| H1 | BUY | 51 | 0 | setup_block |  |  | monitor |
| H4 | SELL | 51 | 0 | sell_ignored |  |  | monitor |
| M15 | BUY | 42 | 0 | setup_block |  |  | monitor |
| M5 | SELL | 39 | 0 | sell_ignored |  |  | monitor |
| M30 | BUY | 32 | 0 | setup_block |  |  | monitor |
| M30 | SELL | 20 | 0 | sell_ignored |  |  | monitor |
| M15 | SELL | 8 | 0 | sell_ignored |  |  | monitor |
| M5 | BUY | 1 | 0 | setup_block |  |  | monitor |
