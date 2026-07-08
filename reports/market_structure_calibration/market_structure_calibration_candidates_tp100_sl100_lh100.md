# Market Structure Calibration Candidates

Candidatos offline para calibracao. Nenhuma regra daqui e aplicada automaticamente no robo.

## Filtros

- Min samples: 300
- Min win rate: 60.00%
- Min edge score: 0.500
- Top por ativo/timeframe/lado: 5

- Ativos com candidatos: 27
- Combinacoes ativo/timeframe/lado: 66
- Regras candidatas: 218

## Top candidatos

| symbol | timeframe | side | feature | bucket | samples | win_rate | edge_score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| NZDCHF | H1 | sell | hour | (17.0, 23.0] | 1248 | 84.21% | 2.4395 |
| NZDCHF | H1 | sell | session | after_hours | 1248 | 84.21% | 2.4395 |
| AUDCHF | H1 | sell | day_of_week | (4.0, 6.0] | 1440 | 83.33% | 2.4244 |
| NZDCHF | H1 | sell | day_of_week | (4.0, 6.0] | 1440 | 83.26% | 2.4193 |
| NZDCHF | H1 | sell | overlap_ratio_10 | (0.711, 1.0] | 1541 | 80.92% | 2.2699 |
| NZDCHF | H1 | sell | volume_ratio | (-0.001, 0.381] | 1586 | 80.64% | 2.2583 |
| AUDCHF | H1 | sell | overlap_ratio_10 | (0.711, 1.0] | 1480 | 80.88% | 2.2543 |
| AUDCHF | H1 | sell | delta_proxy | (-0.0702, -0.0] | 1775 | 79.38% | 2.1983 |
| AUDCHF | H1 | sell | regime_reversal_risk | 1 | 312 | 87.82% | 2.1732 |
| AUDCHF | H1 | sell | hour | (17.0, 23.0] | 1248 | 80.45% | 2.1710 |
| CADCHF | H1 | sell | hour | (17.0, 23.0] | 1248 | 79.41% | 2.0968 |
| CADCHF | H1 | sell | session | after_hours | 1248 | 79.41% | 2.0968 |
| NZDCAD | H1 | sell | day_of_week | (4.0, 6.0] | 1427 | 76.73% | 1.9420 |
| CADCHF | H1 | sell | day_of_week | (4.0, 6.0] | 1440 | 76.67% | 1.9395 |
| GBPCHF | M5 | sell | hour | (17.0, 23.0] | 1224 | 77.21% | 1.9345 |
| GBPCHF | M5 | sell | session | after_hours | 1224 | 77.21% | 1.9345 |
| AUDCAD | H1 | sell | day_of_week | (4.0, 6.0] | 1427 | 76.45% | 1.9216 |
| NZDCAD | H1 | sell | overlap_ratio_10 | (0.711, 1.0] | 1526 | 75.69% | 1.8832 |
| GBPAUD | M15 | buy | day_of_week | (4.0, 6.0] | 1536 | 75.33% | 1.8583 |
| NZDCAD | H1 | sell | range_contraction | 1 | 1206 | 76.04% | 1.8475 |
| CADCHF | H1 | sell | close_position | (-0.001, 0.164] | 1358 | 75.55% | 1.8435 |
| CADCHF | H1 | sell | lower_wick_to_range | (-0.001, 0.074] | 1200 | 75.75% | 1.8259 |
| NZDCAD | H1 | sell | atr_ratio_5_50 | (-0.001, 0.752] | 1469 | 75.02% | 1.8245 |
| AUDCAD | H1 | sell | delta_proxy | (-0.0702, -0.0] | 1570 | 74.78% | 1.8235 |
| NZDCAD | H1 | sell | delta_proxy | (-0.0702, -0.0] | 1636 | 73.90% | 1.7687 |
| CADCHF | M5 | sell | hour | (17.0, 23.0] | 1224 | 74.59% | 1.7486 |
| CADCHF | M5 | sell | session | after_hours | 1224 | 74.59% | 1.7486 |
| NZDSGD | H1 | sell | hour | (17.0, 23.0] | 1248 | 74.44% | 1.7425 |
| NZDSGD | H1 | sell | session | after_hours | 1248 | 74.44% | 1.7425 |
| GBPNZD | M15 | buy | close_position | (-0.001, 0.164] | 1203 | 74.48% | 1.7365 |
| GBPAUD | M15 | buy | close_position | (-0.001, 0.164] | 1614 | 73.48% | 1.7346 |
| GBPCHF | H1 | sell | hour | (17.0, 23.0] | 1248 | 74.28% | 1.7311 |
| GBPCHF | H1 | sell | session | after_hours | 1248 | 74.28% | 1.7311 |
| NZDCAD | M5 | sell | hour | (17.0, 23.0] | 1292 | 73.45% | 1.6803 |
| NZDCAD | M5 | sell | session | after_hours | 1292 | 73.45% | 1.6803 |
| AUDJPY | H1 | sell | day_of_week | (4.0, 6.0] | 1427 | 73.09% | 1.6773 |
| AUDCAD | H1 | sell | overlap_ratio_10 | (0.711, 1.0] | 1541 | 72.68% | 1.6649 |
| AUDCAD | H1 | sell | range_contraction | 1 | 1348 | 73.07% | 1.6628 |
| AUDJPY | H1 | sell | delta_proxy | (-0.0702, -0.0] | 1477 | 72.65% | 1.6529 |
| AUDCAD | H1 | sell | atr_ratio_5_50 | (-0.001, 0.752] | 1571 | 72.18% | 1.6327 |
| CADCHF | M15 | sell | bars_since_breakout_down | (64.0, 448.0] | 1352 | 72.41% | 1.6159 |
| GBPCHF | H1 | sell | bars_since_breakout_down | (64.0, 448.0] | 1354 | 72.38% | 1.6138 |
| GBPCAD | H1 | buy | lower_wick_to_range | (-0.001, 0.074] | 1337 | 71.80% | 1.5696 |
| GBPAUD | M15 | buy | volume_ratio | (-0.001, 0.381] | 1793 | 70.78% | 1.5565 |
| GBPAUD | M15 | buy | kaufman_er_10 | (-0.001, 0.0429] | 1852 | 69.82% | 1.4911 |
| GBPAUD | M15 | buy | distance_to_swing_low_atr | (-12.828999999999999, 0.643] | 1994 | 69.41% | 1.4747 |
| AUDJPY | H1 | sell | overlap_ratio_10 | (0.711, 1.0] | 1466 | 69.99% | 1.4572 |
| GBPCHF | H1 | sell | day_of_week | (4.0, 6.0] | 1440 | 70.00% | 1.4546 |
| AUDJPY | H1 | sell | range_contraction | 1 | 1451 | 69.75% | 1.4376 |
| AUDJPY | H1 | sell | volume_ratio | (-0.001, 0.381] | 1800 | 68.50% | 1.3868 |
| GBPCAD | H1 | buy | close_position | (-0.001, 0.164] | 1422 | 68.99% | 1.3786 |
| GBPCHF | M5 | sell | bars_since_volume_climax | (34.0, 248.0] | 949 | 69.97% | 1.3691 |
| EURGBP | M15 | sell | ema21_slope_atr | (0.337, 33191153721.958] | 746 | 70.51% | 1.3569 |
| EURGBP | M15 | sell | distance_to_swing_low_atr | (4.642, 463989257812.5] | 798 | 70.30% | 1.3568 |
| USDCHF | H1 | sell | ema21_slope_atr | (-1.71e-07, 0.337] | 1152 | 69.18% | 1.3525 |
| AUDNZD | H1 | sell | range_contraction | 1 | 710 | 70.56% | 1.3503 |
| GBPCHF | M15 | sell | bars_since_breakout_down | (64.0, 448.0] | 1232 | 68.91% | 1.3460 |
| NZDSGD | H1 | sell | upper_wick_to_range | (0.231, 0.407] | 1202 | 68.97% | 1.3453 |
| NZDSGD | H1 | sell | range_zscore_20 | (-4.25, -0.639] | 1050 | 69.24% | 1.3385 |
| AUDCHF | M5 | sell | hour | (17.0, 23.0] | 1224 | 68.71% | 1.3304 |
| AUDCHF | M5 | sell | session | after_hours | 1224 | 68.71% | 1.3304 |
| EURGBP | M15 | sell | distance_to_swing_high_atr | (-9.442, 0.838] | 697 | 70.16% | 1.3200 |
| GBPNZD | M15 | buy | distance_to_swing_high_atr | (0.838, 1.784] | 1163 | 68.62% | 1.3142 |
| USDCHF | H1 | sell | price_extension_atr | (-3.15e-07, 0.711] | 1155 | 68.57% | 1.3098 |
| GBPCHF | H1 | sell | delta_proxy | (-0.0702, -0.0] | 1606 | 67.68% | 1.3054 |
| AUDNZD | H1 | sell | hour | (17.0, 23.0] | 1248 | 68.27% | 1.3026 |
| AUDNZD | H1 | sell | session | after_hours | 1248 | 68.27% | 1.3026 |
| AUDCAD | M5 | sell | hour | (17.0, 23.0] | 1292 | 67.96% | 1.2865 |
| AUDCAD | M5 | sell | session | after_hours | 1292 | 67.96% | 1.2865 |
| CHFJPY | M15 | buy | movement_efficiency | (0.471, 0.689] | 1433 | 67.62% | 1.2807 |
| CHFJPY | M15 | buy | body_to_range | (0.471, 0.689] | 1433 | 67.62% | 1.2807 |
| EURGBP | M15 | sell | price_extension_atr | (0.711, 54366273643.438] | 767 | 68.84% | 1.2517 |
| GBPNZD | M15 | buy | lower_wick_to_range | (-0.001, 0.074] | 1040 | 67.98% | 1.2493 |
| NZDSGD | H1 | sell | atr_ratio_5_50 | (0.752, 0.978] | 1763 | 66.31% | 1.2190 |
| EURCHF | H1 | sell | upper_wick_to_range | (0.231, 0.407] | 1480 | 66.69% | 1.2184 |
| USDCAD | H1 | sell | regime_reversal_risk | 1 | 440 | 70.00% | 1.2178 |
| GBPCAD | H1 | sell | regime_reversal_risk | 1 | 385 | 70.39% | 1.2144 |
| EURCAD | M15 | buy | bars_since_breakout_up | (58.0, 605.0] | 1931 | 66.03% | 1.2127 |
| EURCHF | H1 | sell | day_of_week | (4.0, 6.0] | 1440 | 66.67% | 1.2122 |
| USDCHF | H1 | sell | day_of_week | (4.0, 6.0] | 1440 | 66.67% | 1.2122 |