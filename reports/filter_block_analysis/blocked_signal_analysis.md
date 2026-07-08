# Filter Block Analysis

Generated at: 2026-06-10T14:45:20

## Scope

- Decision-audit blocked signals: 21618
- Symbols with blocked signals: 31
- Symbol/timeframe/side groups: 82

## Top Blocked Symbols

| Symbol | Total | BUY | SELL | Top TF | Top blocker | Pct |
|---|---:|---:|---:|---|---|---:|
| CADJPY | 2765 | 12 | 2753 | M15 | correlacao_prejuizo | 74.0 |
| AUDCAD | 2399 | 376 | 2023 | H1 | macro_fluxo_contra | 73.1 |
| NZDJPY | 2026 | 0 | 2026 | M30 | macro_fluxo_contra | 84.2 |
| EURJPY | 1836 | 126 | 1710 | H4 | preco_candle_nao_confirmado | 41.3 |
| AUDUSD | 1771 | 0 | 1771 | H1 | macro_fluxo_contra | 76.9 |
| AUDJPY | 1426 | 0 | 1426 | M30 | macro_fluxo_contra | 85.4 |
| AUDNZD | 1258 | 1068 | 190 | H1 | macro_fluxo_contra | 51.7 |
| EURCAD | 1047 | 1047 | 0 | H4 | macro_fluxo_contra | 69.3 |
| NZDCAD | 961 | 725 | 236 | H4 | preco_candle_nao_confirmado | 34.3 |
| EURUSD | 945 | 513 | 432 | H1 | macro_fluxo_contra | 41.6 |
| AUDSGD | 849 | 12 | 837 | M30 | macro_fluxo_contra | 100.0 |
| NZDSGD | 519 | 369 | 150 | H4 | correlacao_prejuizo | 52.0 |
| EURCHF | 452 | 452 | 0 | H4 | macro_fluxo_contra | 90.3 |
| GBPJPY | 441 | 0 | 441 | H1 | macro_fluxo_contra | 92.1 |
| CHFJPY | 395 | 237 | 158 | M30 | macro_fluxo_contra | 80.5 |
| EURNZD | 296 | 0 | 296 | D1 | correlacao_prejuizo | 70.3 |
| CADCHF | 285 | 78 | 207 | H4 | macro_fluxo_contra | 60.0 |
| USDJPY | 262 | 262 | 0 | M30 | macro_fluxo_contra | 59.9 |
| XAUUSD | 244 | 126 | 118 | M30 | sell_ignored | 48.4 |
| GBPNZD | 237 | 237 | 0 | M30 | macro_fluxo_contra | 82.3 |

## Top Blocked Symbol/Timeframe/Side

| Symbol | TF | Side | Blocked | Top blocker | Pct | Avg tradeability | Avg conflict | Avg consensus |
|---|---|---|---:|---|---:|---:|---:|---:|
| AUDJPY | M30 | SELL | 1067 | macro_fluxo_contra | 85.4 | 0.315 | 0.173 | 0.139 |
| EURCAD | H4 | BUY | 1047 | macro_fluxo_contra | 69.3 | 0.495 | 0.314 | 0.161 |
| CADJPY | H4 | SELL | 1044 | correlacao_prejuizo | 77.3 | 0.452 | 0.205 | 0.354 |
| AUDCAD | H1 | SELL | 1035 | macro_fluxo_contra | 84.9 | 0.326 | 0.163 | 0.149 |
| CADJPY | M15 | SELL | 1035 | correlacao_prejuizo | 72.2 | 0.454 | 0.237 | 0.313 |
| AUDUSD | H1 | SELL | 1018 | macro_fluxo_contra | 84.7 | 0.363 | 0.052 | 0.119 |
| NZDJPY | M30 | SELL | 1017 | macro_fluxo_contra | 84.1 | 0.338 | 0.222 | 0.135 |
| NZDJPY | M15 | SELL | 1009 | macro_fluxo_contra | 84.2 | 0.377 | 0.247 | 0.143 |
| EURJPY | H4 | SELL | 879 | ema_nao_alinhada | 40.4 | 0.440 | 0.150 | 0.351 |
| AUDUSD | M30 | SELL | 734 | macro_fluxo_contra | 65.5 | 0.351 | 0.175 | 0.159 |
| NZDCAD | H4 | BUY | 721 | preco_candle_nao_confirmado | 45.8 | 0.478 | 0.179 | 0.324 |
| AUDNZD | H1 | BUY | 717 | macro_fluxo_contra | 78.2 | 0.452 | 0.039 | 0.150 |
| CADJPY | M30 | SELL | 674 | correlacao_prejuizo | 73.0 | 0.498 | 0.277 | 0.268 |
| EURJPY | H1 | SELL | 618 | preco_candle_nao_confirmado | 48.5 | 0.460 | 0.183 | 0.369 |
| AUDCAD | M15 | SELL | 610 | macro_fluxo_contra | 87.2 | 0.321 | 0.204 | 0.180 |
| EURUSD | H1 | BUY | 510 | macro_fluxo_contra | 76.5 | 0.422 | 0.404 | 0.113 |
| EURUSD | M15 | SELL | 432 | preco_candle_nao_confirmado | 57.6 | 0.419 | 0.166 | 0.298 |
| AUDSGD | M30 | SELL | 372 | macro_fluxo_contra | 100.0 | 0.263 | 0.068 | 0.088 |
| EURCHF | H4 | BUY | 372 | macro_fluxo_contra | 100.0 | 0.356 | 0.489 | 0.095 |
| NZDSGD | H4 | BUY | 369 | correlacao_prejuizo | 73.2 | 0.420 | 0.225 | 0.422 |
| GBPJPY | H1 | SELL | 367 | macro_fluxo_contra | 100.0 | 0.318 | 0.047 | 0.094 |
| AUDCAD | M30 | BUY | 355 | risk_engine | 24.5 | 0.442 | 0.167 | 0.321 |
| AUDJPY | H4 | SELL | 354 | macro_fluxo_contra | 85.3 | 0.357 | 0.301 | 0.152 |
| AUDNZD | H4 | BUY | 351 | ema_nao_alinhada | 37.6 | 0.566 | 0.188 | 0.281 |
| AUDCAD | M30 | SELL | 321 | macro_fluxo_contra | 88.8 | 0.178 | 0.428 | 0.039 |

## Recent Market Alignment Blocks

| Symbol | TF | Side | Blocks | State | Reason | Avg align | Avg structural |
|---|---|---|---:|---|---|---:|---:|
| CADCHF | H1 | BUY | 992 | structural_conflict | estrutura_h4_d1_contra | -0.227 | -0.560 |
| EURUSD | H1 | BUY | 948 | structural_conflict | estrutura_h4_d1_contra | -0.489 | -0.595 |
| CADCHF | H4 | BUY | 893 | structural_conflict | estrutura_h4_d1_contra | -0.249 | -0.581 |
| GBPUSD | H4 | SELL | 886 | structural_conflict | h1_h4_nao_confirma | -0.255 | 0.300 |
| EURCHF | H4 | SELL | 880 | structural_conflict | h1_h4_nao_confirma | -0.465 | 0.287 |
| NZDJPY | H4 | SELL | 856 | structural_conflict | estrutura_h4_d1_contra | -0.318 | 0.785 |
| GBPAUD | H4 | BUY | 852 | structural_conflict | estrutura_h4_d1_contra | -0.421 | -0.668 |
| CADJPY | H4 | SELL | 834 | structural_conflict | h1_h4_nao_confirma | -0.414 | 0.591 |
| AUDNZD | H1 | BUY | 833 | structural_conflict | estrutura_h4_d1_contra | -0.100 | -0.383 |
| GBPCHF | H4 | SELL | 793 | structural_conflict | h1_h4_nao_confirma | -0.598 | 0.485 |
| EURCHF | H1 | SELL | 693 | structural_conflict | h1_h4_nao_confirma | -0.380 | 0.185 |
| USDCAD | H4 | SELL | 669 | structural_conflict | estrutura_h4_d1_contra | -0.713 | 0.850 |
| GBPCAD | H4 | SELL | 639 | structural_conflict | estrutura_h4_d1_contra | -0.594 | 0.932 |
| NZDJPY | H1 | SELL | 560 | structural_conflict | estrutura_h4_d1_contra | -0.314 | 0.736 |
| EURNZD | H4 | SELL | 507 | chop | h1_h4_nao_confirma | -0.066 | -0.451 |
| CADJPY | H1 | BUY | 501 | structural_conflict | h1_h4_nao_confirma | -0.329 | -0.103 |
| NZDSGD | H4 | BUY | 488 | chop | h1_h4_nao_confirma | -0.043 | 0.466 |
| EURGBP | H1 | BUY | 465 | structural_conflict | estrutura_h4_d1_contra | -0.611 | -0.826 |
| GBPNZD | H4 | SELL | 465 | chop | h1_h4_nao_confirma | -0.175 | -0.289 |
| NZDCAD | H1 | SELL | 446 | structural_conflict | estrutura_h4_d1_contra | -0.234 | 0.704 |
| USDJPY | H1 | SELL | 441 | structural_conflict | estrutura_h4_d1_contra | -0.714 | 0.960 |
| NZDSGD | H1 | SELL | 440 | structural_conflict | estrutura_h4_d1_contra | -0.031 | 0.517 |
| CHFJPY | H1 | BUY | 434 | chop | h1_h4_nao_confirma | -0.154 | 0.274 |
| GBPAUD | H1 | BUY | 426 | structural_conflict | estrutura_h4_d1_contra | -0.493 | -0.701 |
| EURUSD | H4 | SELL | 412 | countertrend | h1_h4_nao_confirma | -0.129 | -0.013 |

## Text Log Guard Blocks

| Symbol | TF | Side | Guard | State | Count |
|---|---|---|---|---|---:|
| CADJPY | NA | SELL | correlation_guard |  | 2457 |
| EURJPY | H4 | SELL | price_candle_guard |  | 1617 |
| NZDCAD | H4 | BUY | price_candle_guard |  | 1371 |
| GBPJPY | H1 | SELL | price_candle_guard |  | 1369 |
| AUDUSD | H1 | SELL | price_candle_guard |  | 1234 |
| AUDCAD | NA | BUY | correlation_guard |  | 1230 |
| AUDJPY | M30 | SELL | price_candle_guard |  | 1162 |
| EURCHF | H4 | BUY | price_candle_guard |  | 1148 |
| AUDSGD | H4 | SELL | price_candle_guard |  | 1131 |
| AUDCAD | H1 | SELL | price_candle_guard |  | 1078 |
| NZDJPY | M30 | SELL | price_candle_guard |  | 1050 |
| AUDSGD | M30 | SELL | price_candle_guard |  | 1008 |
| CADCHF | H4 | SELL | price_candle_guard |  | 956 |
| EURAUD | NA | SELL | correlation_guard |  | 950 |
| AUDUSD | M30 | SELL | price_candle_guard |  | 947 |
| AUDCAD | NA | SELL | correlation_guard |  | 934 |
| AUDUSD | NA | SELL | correlation_guard |  | 920 |
| CADJPY | M30 | SELL | price_candle_guard |  | 881 |
| CADJPY | M15 | SELL | price_candle_guard |  | 853 |
| EURCAD | H4 | BUY | price_candle_guard |  | 812 |
| CADJPY | H4 | SELL | price_candle_guard |  | 791 |
| CADCHF | H1 | BUY | market_alignment | structural_conflict | 774 |
| CADCHF | H4 | BUY | market_alignment | structural_conflict | 725 |
| NZDJPY | H4 | SELL | market_alignment | structural_conflict | 696 |
| AUDSGD | H1 | SELL | price_candle_guard |  | 689 |

## Candidate Relaxations

| Symbol | TF | Side | Blocked | MA blocks | Top blocker | H3 acc | H3 avg pts |
|---|---|---|---:|---:|---|---:|---:|
| EURJPY | H4 | SELL | 879 | 60 | ema_nao_alinhada | 60.19 | 21.13 |
| EURCHF | H4 | BUY | 372 | 0 | macro_fluxo_contra | 100.00 | 133.05 |
| NZDSGD | H4 | BUY | 369 | 488 | correlacao_prejuizo | 56.35 | 194.30 |
| AUDNZD | H4 | BUY | 351 | 0 | ema_nao_alinhada | 100.00 | 279.83 |
| EURGBP | H4 | SELL | 110 | 105 | preco_candle_nao_confirmado | 92.63 | 58.10 |

## Candidate Keep/Tighten

| Symbol | TF | Side | Blocked | Top blocker | H3 acc | H3 avg pts |
|---|---|---|---:|---|---:|---:|
| EURCAD | H4 | BUY | 1047 | macro_fluxo_contra | 31.16 | -86.33 |
| AUDCAD | H1 | SELL | 1035 | macro_fluxo_contra | 34.98 | -31.24 |
| CADJPY | M15 | SELL | 1035 | correlacao_prejuizo | 42.68 | -15.67 |
| AUDUSD | H1 | SELL | 1018 | macro_fluxo_contra | 25.00 | -52.96 |
| AUDNZD | H1 | BUY | 717 | macro_fluxo_contra | 19.09 | -109.08 |
| EURJPY | H1 | SELL | 618 | preco_candle_nao_confirmado | 46.18 | -17.42 |
| AUDCAD | M15 | SELL | 610 | macro_fluxo_contra | 33.93 | -17.89 |
| EURUSD | M15 | SELL | 432 | preco_candle_nao_confirmado | 48.63 | -0.03 |
| GBPJPY | H1 | SELL | 367 | macro_fluxo_contra | 24.01 | -51.09 |
| AUDJPY | H4 | SELL | 354 | macro_fluxo_contra | 20.00 | -87.50 |
| AUDSGD | H4 | SELL | 264 | macro_fluxo_contra | 24.62 | -62.34 |
| AUDSGD | H1 | SELL | 201 | macro_fluxo_contra | 51.52 | -8.89 |
| NZDUSD | M15 | BUY | 87 | portfolio_exposure | 34.48 | -7.52 |
| GBPJPY | H4 | SELL | 35 | risk_engine | 55.00 | -43.50 |
| CADCHF | M15 | BUY | 30 | macro_fluxo_contra | 15.56 | -23.40 |
| USDCHF | H1 | BUY | 13 | macro_fluxo_contra | 52.70 | -104.42 |
