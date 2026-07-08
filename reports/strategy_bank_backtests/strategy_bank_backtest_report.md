# Relatorio Backtest Strategy Bank

## Configuracao

- Ativos: AUDCAD, AUDCHF, AUDJPY, AUDNZD, AUDSGD, AUDUSD, CADCHF, CADJPY, CHFJPY, EURAUD, EURCAD, EURCHF, EURGBP, EURJPY, EURNZD, EURUSD, GBPAUD, GBPCAD, GBPCHF, GBPJPY, GBPNZD, GBPUSD, NZDCAD, NZDCHF, NZDJPY, NZDSGD, NZDUSD, USDCAD, USDCHF, USDJPY, XAUUSD
- Periodo: ultimos 1 ano(s) do historico disponivel
- Janela maxima por trade: 80 candles
- Sinais: setups tecnicos do banco de estrategias
- Confirmacao de modelo: nao aplicada neste relatorio

## Resumo Geral

- Trades: 23950
- Wins: 4314
- Losses: 14870
- Timeouts: 4517
- Win rate: 18.01%
- PnL total: -419100.85 pontos
- PnL medio/trade: -17.50 pontos

## Top 30 Combinacoes

| asset | strategy_id | timeframe | trades | wins | losses | win_rate | pnl_points | avg_pnl_points |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GBPJPY | volatility_expansion_breakout | H1 | 1 | 1 | 0 | 100.0000 | 320.0000 | 320.0000 |
| USDJPY | daily_bias_intraday | M30 | 161 | 145 | 16 | 90.0621 | 72360.0000 | 449.4410 |
| USDJPY | trend_pullback_ema21 | M30 | 166 | 144 | 22 | 86.7470 | 61060.0000 | 367.8313 |
| USDCHF | trend_pullback_ema21 | M30 | 95 | 80 | 15 | 84.2105 | 33450.0000 | 352.1053 |
| USDCHF | daily_bias_intraday | M30 | 97 | 80 | 16 | 82.4742 | 38417.0025 | 396.0516 |
| NZDCAD | support_resistance_bounce | H1 | 75 | 60 | 15 | 80.0000 | 18225.0000 | 243.0000 |
| AUDCHF | support_resistance_bounce | M30 | 64 | 51 | 13 | 79.6875 | 15455.0000 | 241.4844 |
| CADCHF | daily_bias_intraday | H1 | 43 | 34 | 3 | 79.0698 | 16883.0076 | 392.6281 |
| CADCHF | trend_pullback_ema21 | H1 | 105 | 83 | 18 | 79.0476 | 34612.0022 | 329.6381 |
| NZDJPY | daily_bias_intraday | M30 | 108 | 85 | 22 | 78.7037 | 40020.0000 | 370.5556 |
| AUDSGD | daily_bias_intraday | M30 | 67 | 52 | 14 | 77.6119 | 24319.0006 | 362.9702 |
| CADJPY | daily_bias_intraday | M30 | 106 | 82 | 15 | 77.3585 | 41332.9839 | 389.9338 |
| USDJPY | trend_pullback_ema21 | H1 | 103 | 78 | 23 | 75.7282 | 30850.0000 | 299.5146 |
| AUDCAD | daily_bias_intraday | M30 | 81 | 60 | 13 | 74.0741 | 29369.0035 | 362.5803 |
| GBPCAD | daily_bias_intraday | H1 | 73 | 53 | 20 | 72.6027 | 23760.0000 | 325.4795 |
| USDJPY | daily_bias_intraday | H1 | 82 | 59 | 18 | 71.9512 | 26310.0000 | 320.8537 |
| AUDUSD | daily_bias_intraday | M30 | 100 | 69 | 18 | 69.0000 | 34392.9787 | 343.9298 |
| AUDUSD | trend_pullback_ema21 | M30 | 109 | 75 | 19 | 68.8073 | 32167.9850 | 295.1191 |
| AUDCAD | support_resistance_bounce | M30 | 62 | 42 | 19 | 67.7419 | 11580.9986 | 186.7903 |
| GBPNZD | daily_bias_intraday | H1 | 43 | 29 | 14 | 67.4419 | 12420.0000 | 288.8372 |
| AUDJPY | volatility_expansion_breakout | H1 | 3 | 2 | 1 | 66.6667 | 500.0000 | 166.6667 |
| AUDCAD | trend_pullback_ema21 | M30 | 96 | 62 | 29 | 64.5833 | 23173.0075 | 241.3855 |
| AUDSGD | support_resistance_bounce | M15 | 16 | 10 | 5 | 62.5000 | 2715.9961 | 169.7498 |
| AUDCHF | range_mean_reversion | M30 | 8 | 5 | 3 | 62.5000 | 840.0000 | 105.0000 |
| GBPCAD | trend_pullback_ema21 | H1 | 84 | 52 | 32 | 61.9048 | 17960.0000 | 213.8095 |
| EURCHF | range_mean_reversion | H1 | 13 | 8 | 5 | 61.5385 | 1320.0000 | 101.5385 |
| USDCHF | daily_bias_intraday | H1 | 47 | 28 | 18 | 59.5745 | 11262.0048 | 239.6171 |
| AUDCAD | support_resistance_bounce | M15 | 148 | 88 | 20 | 59.4595 | 27020.0000 | 182.5676 |
| USDCHF | trend_pullback_ema21 | H1 | 57 | 33 | 22 | 57.8947 | 11104.0038 | 194.8071 |
| NZDUSD | daily_bias_intraday | H1 | 21 | 12 | 9 | 57.1429 | 4530.0000 | 215.7143 |

## Piores 30 Combinacoes

| asset | strategy_id | timeframe | trades | wins | losses | win_rate | pnl_points | avg_pnl_points |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| XAUUSD | gold_impulse_pullback | M30 | 2 | 0 | 1 | 0.0000 | -1536.0000 | -768.0000 |
| XAUUSD | volatility_expansion_breakout | M15 | 3 | 0 | 0 | 0.0000 | -1008.0000 | -336.0000 |
| XAUUSD | gold_impulse_pullback | M15 | 1 | 0 | 1 | 0.0000 | -768.0000 | -768.0000 |
| XAUUSD | volatility_expansion_breakout | H1 | 2 | 0 | 0 | 0.0000 | -672.0000 | -336.0000 |
| EURAUD | volatility_expansion_breakout | M15 | 3 | 0 | 3 | 0.0000 | -420.0000 | -140.0000 |
| GBPAUD | volatility_expansion_breakout | H1 | 3 | 0 | 3 | 0.0000 | -420.0000 | -140.0000 |
| AUDUSD | volatility_expansion_breakout | H1 | 2 | 0 | 2 | 0.0000 | -280.0000 | -140.0000 |
| AUDUSD | volatility_expansion_breakout | M5 | 2 | 0 | 2 | 0.0000 | -280.0000 | -140.0000 |
| CADJPY | volatility_expansion_breakout | M30 | 2 | 0 | 2 | 0.0000 | -280.0000 | -140.0000 |
| GBPAUD | volatility_expansion_breakout | M15 | 2 | 0 | 2 | 0.0000 | -280.0000 | -140.0000 |
| GBPAUD | volatility_expansion_breakout | M5 | 2 | 0 | 2 | 0.0000 | -280.0000 | -140.0000 |
| GBPCAD | volatility_expansion_breakout | H1 | 2 | 0 | 2 | 0.0000 | -280.0000 | -140.0000 |
| NZDJPY | volatility_expansion_breakout | M15 | 2 | 0 | 2 | 0.0000 | -280.0000 | -140.0000 |
| NZDJPY | volatility_expansion_breakout | M30 | 2 | 0 | 2 | 0.0000 | -280.0000 | -140.0000 |
| AUDJPY | volatility_expansion_breakout | M15 | 1 | 0 | 1 | 0.0000 | -140.0000 | -140.0000 |
| AUDJPY | volatility_expansion_breakout | M30 | 1 | 0 | 1 | 0.0000 | -140.0000 | -140.0000 |
| AUDUSD | volatility_expansion_breakout | M30 | 1 | 0 | 1 | 0.0000 | -140.0000 | -140.0000 |
| CADJPY | volatility_expansion_breakout | H1 | 1 | 0 | 0 | 0.0000 | -140.0000 | -140.0000 |
| EURAUD | volatility_expansion_breakout | M30 | 1 | 0 | 1 | 0.0000 | -140.0000 | -140.0000 |
| EURAUD | volatility_expansion_breakout | M5 | 1 | 0 | 1 | 0.0000 | -140.0000 | -140.0000 |
| EURNZD | volatility_expansion_breakout | M15 | 1 | 0 | 1 | 0.0000 | -140.0000 | -140.0000 |
| EURNZD | volatility_expansion_breakout | M5 | 1 | 0 | 1 | 0.0000 | -140.0000 | -140.0000 |
| GBPAUD | volatility_expansion_breakout | M30 | 1 | 0 | 1 | 0.0000 | -140.0000 | -140.0000 |
| GBPCAD | volatility_expansion_breakout | M5 | 1 | 0 | 1 | 0.0000 | -140.0000 | -140.0000 |
| GBPJPY | volatility_expansion_breakout | M15 | 1 | 0 | 1 | 0.0000 | -140.0000 | -140.0000 |
| GBPJPY | volatility_expansion_breakout | M30 | 1 | 0 | 1 | 0.0000 | -140.0000 | -140.0000 |
| GBPJPY | volatility_expansion_breakout | M5 | 1 | 0 | 1 | 0.0000 | -140.0000 | -140.0000 |
| GBPNZD | volatility_expansion_breakout | M30 | 1 | 0 | 1 | 0.0000 | -140.0000 | -140.0000 |
| GBPNZD | volatility_expansion_breakout | M5 | 1 | 0 | 1 | 0.0000 | -140.0000 | -140.0000 |
| NZDJPY | volatility_expansion_breakout | H1 | 1 | 0 | 0 | 0.0000 | -140.0000 | -140.0000 |

## Melhor Combinacao Por Ativo

| asset | strategy_id | timeframe | trades | wins | losses | win_rate | pnl_points | avg_pnl_points |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| USDJPY | daily_bias_intraday | M30 | 161 | 145 | 16 | 90.0621 | 72360.0000 | 449.4410 |
| CADJPY | daily_bias_intraday | M30 | 106 | 82 | 15 | 77.3585 | 41332.9839 | 389.9338 |
| AUDCAD | daily_bias_intraday | M15 | 172 | 80 | 19 | 46.5116 | 40170.9996 | 233.5523 |
| NZDJPY | daily_bias_intraday | M30 | 108 | 85 | 22 | 78.7037 | 40020.0000 | 370.5556 |
| USDCHF | daily_bias_intraday | M30 | 97 | 80 | 16 | 82.4742 | 38417.0025 | 396.0516 |
| CADCHF | trend_pullback_ema21 | H1 | 105 | 83 | 18 | 79.0476 | 34612.0022 | 329.6381 |
| AUDUSD | daily_bias_intraday | M30 | 100 | 69 | 18 | 69.0000 | 34392.9787 | 343.9298 |
| GBPCHF | trend_pullback_ema21 | H1 | 175 | 99 | 76 | 56.5714 | 31630.0000 | 180.7429 |
| NZDCAD | trend_pullback_ema21 | M30 | 95 | 5 | 14 | 5.2632 | 27173.0288 | 286.0319 |
| AUDSGD | daily_bias_intraday | M30 | 67 | 52 | 14 | 77.6119 | 24319.0006 | 362.9702 |
| GBPCAD | daily_bias_intraday | H1 | 73 | 53 | 20 | 72.6027 | 23760.0000 | 325.4795 |
| AUDCHF | support_resistance_bounce | M15 | 163 | 56 | 10 | 34.3558 | 22453.0775 | 137.7489 |
| GBPJPY | daily_bias_intraday | M15 | 186 | 3 | 11 | 1.6129 | 18405.9580 | 98.9568 |
| EURJPY | daily_bias_intraday | H1 | 78 | 40 | 37 | 51.2821 | 13580.0000 | 174.1026 |
| GBPNZD | daily_bias_intraday | H1 | 43 | 29 | 14 | 67.4419 | 12420.0000 | 288.8372 |
| NZDCHF | trend_pullback_ema21 | H1 | 58 | 31 | 22 | 53.4483 | 10689.0008 | 184.2931 |
| EURGBP | daily_bias_intraday | H1 | 102 | 6 | 41 | 5.8824 | 9419.8172 | 92.3511 |
| AUDJPY | daily_bias_intraday | M30 | 35 | 16 | 14 | 45.7143 | 6027.9962 | 172.2285 |
| NZDUSD | daily_bias_intraday | H1 | 21 | 12 | 9 | 57.1429 | 4530.0000 | 215.7143 |
| AUDNZD | support_resistance_bounce | H4 | 34 | 17 | 17 | 50.0000 | 3315.0000 | 97.5000 |
| EURCHF | liquidity_sweep_reversal | H1 | 22 | 11 | 9 | 50.0000 | 2150.0033 | 97.7274 |
| EURCAD | daily_bias_intraday | M30 | 24 | 9 | 14 | 37.5000 | 2111.9938 | 87.9997 |
| GBPAUD | daily_bias_intraday | M15 | 22 | 8 | 10 | 36.3636 | 1895.9944 | 86.1816 |
| NZDSGD | support_resistance_bounce | M15 | 23 | 9 | 10 | 39.1304 | 1706.9827 | 74.2166 |
| GBPUSD | session_momentum_open | M5 | 10 | 3 | 6 | 30.0000 | 6.9976 | 0.6998 |
| EURUSD | trend_pullback_ema21 | H4 | 37 | 10 | 27 | 27.0270 | -90.0000 | -2.4324 |
| USDCAD | ema_cross_continuation | H1 | 12 | 3 | 9 | 25.0000 | -270.0000 | -22.5000 |
| EURNZD | inside_bar_breakout | M15 | 25 | 6 | 18 | 24.0000 | -459.9947 | -18.3998 |
| CHFJPY | ema_cross_continuation | H1 | 12 | 2 | 9 | 16.6667 | -700.0000 | -58.3333 |
| EURAUD | inside_bar_breakout | M15 | 21 | 4 | 16 | 19.0476 | -840.0053 | -40.0003 |
| XAUUSD | liquidity_sweep_reversal | H1 | 12 | 0 | 7 | 0.0000 | -3744.0000 | -312.0000 |

## Resumo Por Ativo

| asset | trades | wins | losses | timeouts | pnl_points | avg_pnl_points | win_rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| USDJPY | 972 | 527 | 338 | 98 | 200967.9962 | 206.7572 | 54.2181 |
| AUDCAD | 983 | 390 | 453 | 138 | 98265.9973 | 99.9654 | 39.6745 |
| USDCHF | 556 | 292 | 251 | 13 | 94747.0158 | 170.4083 | 52.5180 |
| GBPCHF | 1313 | 393 | 691 | 229 | 73180.1815 | 55.7351 | 29.9315 |
| AUDUSD | 736 | 243 | 328 | 165 | 69860.9330 | 94.9197 | 33.0163 |
| NZDJPY | 685 | 257 | 408 | 14 | 52868.0102 | 77.1796 | 37.5182 |
| CADCHF | 1325 | 239 | 599 | 487 | 44088.9035 | 33.2746 | 18.0377 |
| AUDCHF | 1189 | 245 | 436 | 508 | 40341.9081 | 33.9293 | 20.6056 |
| NZDCAD | 743 | 162 | 453 | 128 | 29604.0433 | 39.8439 | 21.8035 |
| AUDNZD | 316 | 87 | 207 | 22 | 283.9988 | 0.8987 | 27.5316 |
| GBPCAD | 565 | 147 | 406 | 4 | 229.0101 | 0.4053 | 26.0177 |
| CADJPY | 729 | 157 | 529 | 38 | -5990.1063 | -8.2169 | 21.5364 |
| AUDSGD | 576 | 104 | 343 | 129 | -7336.9979 | -12.7378 | 18.0556 |
| NZDUSD | 656 | 63 | 298 | 295 | -7509.6217 | -11.4476 | 9.6037 |
| EURGBP | 904 | 60 | 335 | 509 | -8285.5540 | -9.1654 | 6.6372 |
| NZDCHF | 807 | 112 | 452 | 243 | -13390.1131 | -16.5925 | 13.8786 |
| AUDJPY | 366 | 68 | 272 | 22 | -14233.9917 | -38.8907 | 18.5792 |
| EURCHF | 535 | 92 | 299 | 144 | -14385.0542 | -26.8880 | 17.1963 |
| GBPJPY | 919 | 34 | 525 | 348 | -21140.1230 | -23.0034 | 3.6997 |
| GBPNZD | 507 | 76 | 418 | 2 | -35276.9920 | -69.5799 | 14.9901 |
| EURCAD | 639 | 77 | 549 | 9 | -58976.0501 | -92.2943 | 12.0501 |
| GBPAUD | 536 | 37 | 476 | 5 | -68070.0021 | -126.9963 | 6.9030 |
| EURJPY | 807 | 96 | 677 | 26 | -68914.0376 | -85.3953 | 11.8959 |
| USDCAD | 1013 | 83 | 698 | 232 | -70481.1886 | -69.5767 | 8.1935 |
| NZDSGD | 875 | 69 | 651 | 155 | -77163.0213 | -88.1863 | 7.8857 |
| GBPUSD | 714 | 33 | 555 | 124 | -78735.0042 | -110.2731 | 4.6218 |
| EURUSD | 825 | 51 | 653 | 121 | -86527.9795 | -104.8824 | 6.1818 |
| CHFJPY | 755 | 40 | 631 | 27 | -99065.0000 | -131.2119 | 5.2980 |
| XAUUSD | 288 | 0 | 201 | 0 | -117216.0000 | -407.0000 | 0.0000 |
| EURAUD | 1020 | 41 | 853 | 118 | -130990.0053 | -128.4216 | 4.0196 |
| EURNZD | 1096 | 39 | 885 | 164 | -139852.0097 | -127.6022 | 3.5584 |

## Observacao

Este relatorio testa apenas a logica tecnica das estrategias. A etapa seguinte e aplicar a confirmacao dos modelos por ativo/timeframe para reduzir sinais ruins.
