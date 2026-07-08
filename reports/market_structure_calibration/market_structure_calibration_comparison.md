# Market Structure Calibration Comparison

## Resumo

| calibration | rules | assets | groups | avg_win_rate | max_win_rate | avg_edge |
| --- | --- | --- | --- | --- | --- | --- |
| tp100_sl100_lh100 | 218 | 27 | 66 | 0.6652 | 0.8782 | 1.1761 |
| atr1.5_slatr1_lh100 | 46 | 11 | 13 | 0.6581 | 0.7773 | 1.1216 |
| optimized_lh100 | 19 | 2 | 4 | 0.6650 | 0.7653 | 1.1630 |

## Por lado

| calibration | side | rules | avg_win_rate | avg_edge |
| --- | --- | --- | --- | --- |
| atr1.5_slatr1_lh100 | sell | 46 | 0.6581 | 1.1216 |
| optimized_lh100 | buy | 10 | 0.6627 | 1.1500 |
| optimized_lh100 | sell | 9 | 0.6676 | 1.1775 |
| tp100_sl100_lh100 | sell | 155 | 0.6737 | 1.2299 |
| tp100_sl100_lh100 | buy | 63 | 0.6442 | 1.0440 |

## Grupos que aparecem em mais de uma calibracao

| symbol | timeframe | side | calibrations | rules | best_win_rate |
| --- | --- | --- | --- | --- | --- |
| AUDCHF | H1 | sell | atr1.5_slatr1_lh100, tp100_sl100_lh100 | 10 | 0.8782 |
| NZDCHF | H1 | sell | atr1.5_slatr1_lh100, tp100_sl100_lh100 | 10 | 0.8421 |
| CADCHF | H1 | sell | atr1.5_slatr1_lh100, tp100_sl100_lh100 | 10 | 0.7941 |
| USDCAD | H1 | sell | atr1.5_slatr1_lh100, tp100_sl100_lh100 | 2 | 0.7773 |
| NZDCAD | H1 | sell | atr1.5_slatr1_lh100, tp100_sl100_lh100 | 10 | 0.7673 |
| AUDCAD | H1 | sell | atr1.5_slatr1_lh100, tp100_sl100_lh100 | 10 | 0.7645 |
| NZDSGD | H1 | sell | optimized_lh100, tp100_sl100_lh100 | 10 | 0.7444 |
| GBPCHF | H1 | sell | atr1.5_slatr1_lh100, tp100_sl100_lh100 | 9 | 0.7428 |
| AUDJPY | H1 | sell | atr1.5_slatr1_lh100, tp100_sl100_lh100 | 10 | 0.7309 |
| CADCHF | M15 | sell | atr1.5_slatr1_lh100, tp100_sl100_lh100 | 6 | 0.7241 |
| GBPCAD | H1 | sell | atr1.5_slatr1_lh100, tp100_sl100_lh100 | 2 | 0.7039 |
| EURCHF | H1 | sell | atr1.5_slatr1_lh100, tp100_sl100_lh100 | 10 | 0.6804 |
| EURCHF | M15 | sell | atr1.5_slatr1_lh100, tp100_sl100_lh100 | 4 | 0.6559 |
| XAUUSD | M15 | buy | optimized_lh100, tp100_sl100_lh100 | 6 | 0.6407 |
| GBPJPY | H1 | sell | atr1.5_slatr1_lh100, tp100_sl100_lh100 | 5 | 0.6395 |

## Top geral

| calibration | symbol | timeframe | side | feature | bucket | samples | win_rate | edge_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tp100_sl100_lh100 | NZDCHF | H1 | sell | hour | (17.0, 23.0] | 1248 | 0.8421 | 2.4395 |
| tp100_sl100_lh100 | NZDCHF | H1 | sell | session | after_hours | 1248 | 0.8421 | 2.4395 |
| tp100_sl100_lh100 | AUDCHF | H1 | sell | day_of_week | (4.0, 6.0] | 1440 | 0.8333 | 2.4244 |
| tp100_sl100_lh100 | NZDCHF | H1 | sell | day_of_week | (4.0, 6.0] | 1440 | 0.8326 | 2.4193 |
| tp100_sl100_lh100 | NZDCHF | H1 | sell | overlap_ratio_10 | (0.711, 1.0] | 1541 | 0.8092 | 2.2699 |
| tp100_sl100_lh100 | NZDCHF | H1 | sell | volume_ratio | (-0.001, 0.381] | 1586 | 0.8064 | 2.2583 |
| tp100_sl100_lh100 | AUDCHF | H1 | sell | overlap_ratio_10 | (0.711, 1.0] | 1480 | 0.8088 | 2.2543 |
| tp100_sl100_lh100 | AUDCHF | H1 | sell | delta_proxy | (-0.0702, -0.0] | 1775 | 0.7938 | 2.1983 |
| tp100_sl100_lh100 | AUDCHF | H1 | sell | regime_reversal_risk | 1 | 312 | 0.8782 | 2.1732 |
| tp100_sl100_lh100 | AUDCHF | H1 | sell | hour | (17.0, 23.0] | 1248 | 0.8045 | 2.1710 |
| tp100_sl100_lh100 | CADCHF | H1 | sell | hour | (17.0, 23.0] | 1248 | 0.7941 | 2.0968 |
| tp100_sl100_lh100 | CADCHF | H1 | sell | session | after_hours | 1248 | 0.7941 | 2.0968 |
| tp100_sl100_lh100 | NZDCAD | H1 | sell | day_of_week | (4.0, 6.0] | 1427 | 0.7673 | 1.9420 |
| tp100_sl100_lh100 | CADCHF | H1 | sell | day_of_week | (4.0, 6.0] | 1440 | 0.7667 | 1.9395 |
| tp100_sl100_lh100 | GBPCHF | M5 | sell | hour | (17.0, 23.0] | 1224 | 0.7721 | 1.9345 |
| tp100_sl100_lh100 | GBPCHF | M5 | sell | session | after_hours | 1224 | 0.7721 | 1.9345 |
| tp100_sl100_lh100 | AUDCAD | H1 | sell | day_of_week | (4.0, 6.0] | 1427 | 0.7645 | 1.9216 |
| tp100_sl100_lh100 | NZDCAD | H1 | sell | overlap_ratio_10 | (0.711, 1.0] | 1526 | 0.7569 | 1.8832 |
| tp100_sl100_lh100 | GBPAUD | M15 | buy | day_of_week | (4.0, 6.0] | 1536 | 0.7533 | 1.8583 |
| tp100_sl100_lh100 | NZDCAD | H1 | sell | range_contraction | 1 | 1206 | 0.7604 | 1.8475 |
| tp100_sl100_lh100 | CADCHF | H1 | sell | close_position | (-0.001, 0.164] | 1358 | 0.7555 | 1.8435 |
| tp100_sl100_lh100 | CADCHF | H1 | sell | lower_wick_to_range | (-0.001, 0.074] | 1200 | 0.7575 | 1.8259 |
| tp100_sl100_lh100 | NZDCAD | H1 | sell | atr_ratio_5_50 | (-0.001, 0.752] | 1469 | 0.7502 | 1.8245 |
| tp100_sl100_lh100 | AUDCAD | H1 | sell | delta_proxy | (-0.0702, -0.0] | 1570 | 0.7478 | 1.8235 |
| tp100_sl100_lh100 | NZDCAD | H1 | sell | delta_proxy | (-0.0702, -0.0] | 1636 | 0.7390 | 1.7687 |
| tp100_sl100_lh100 | CADCHF | M5 | sell | hour | (17.0, 23.0] | 1224 | 0.7459 | 1.7486 |
| tp100_sl100_lh100 | CADCHF | M5 | sell | session | after_hours | 1224 | 0.7459 | 1.7486 |
| optimized_lh100 | NZDSGD | H1 | sell | hour | (17.0, 23.0] | 1248 | 0.7444 | 1.7425 |
| optimized_lh100 | NZDSGD | H1 | sell | session | after_hours | 1248 | 0.7444 | 1.7425 |
| tp100_sl100_lh100 | NZDSGD | H1 | sell | hour | (17.0, 23.0] | 1248 | 0.7444 | 1.7425 |
| tp100_sl100_lh100 | NZDSGD | H1 | sell | session | after_hours | 1248 | 0.7444 | 1.7425 |
| tp100_sl100_lh100 | GBPNZD | M15 | buy | close_position | (-0.001, 0.164] | 1203 | 0.7448 | 1.7365 |
| tp100_sl100_lh100 | GBPAUD | M15 | buy | close_position | (-0.001, 0.164] | 1614 | 0.7348 | 1.7346 |
| tp100_sl100_lh100 | GBPCHF | H1 | sell | hour | (17.0, 23.0] | 1248 | 0.7428 | 1.7311 |
| tp100_sl100_lh100 | GBPCHF | H1 | sell | session | after_hours | 1248 | 0.7428 | 1.7311 |
| atr1.5_slatr1_lh100 | USDCAD | H1 | sell | regime_reversal_risk | 1 | 440 | 0.7773 | 1.6883 |
| tp100_sl100_lh100 | NZDCAD | M5 | sell | hour | (17.0, 23.0] | 1292 | 0.7345 | 1.6803 |
| tp100_sl100_lh100 | NZDCAD | M5 | sell | session | after_hours | 1292 | 0.7345 | 1.6803 |
| atr1.5_slatr1_lh100 | NZDCHF | H1 | sell | hour | (17.0, 23.0] | 1248 | 0.7356 | 1.6797 |
| atr1.5_slatr1_lh100 | NZDCHF | H1 | sell | session | after_hours | 1248 | 0.7356 | 1.6797 |
| tp100_sl100_lh100 | AUDJPY | H1 | sell | day_of_week | (4.0, 6.0] | 1427 | 0.7309 | 1.6773 |
| tp100_sl100_lh100 | AUDCAD | H1 | sell | overlap_ratio_10 | (0.711, 1.0] | 1541 | 0.7268 | 1.6649 |
| tp100_sl100_lh100 | AUDCAD | H1 | sell | range_contraction | 1 | 1348 | 0.7307 | 1.6628 |
| tp100_sl100_lh100 | AUDJPY | H1 | sell | delta_proxy | (-0.0702, -0.0] | 1477 | 0.7265 | 1.6529 |
| tp100_sl100_lh100 | AUDCAD | H1 | sell | atr_ratio_5_50 | (-0.001, 0.752] | 1571 | 0.7218 | 1.6327 |
| atr1.5_slatr1_lh100 | AUDCHF | H1 | sell | day_of_week | (4.0, 6.0] | 1440 | 0.7236 | 1.6263 |
| tp100_sl100_lh100 | CADCHF | M15 | sell | bars_since_breakout_down | (64.0, 448.0] | 1352 | 0.7241 | 1.6159 |
| tp100_sl100_lh100 | GBPCHF | H1 | sell | bars_since_breakout_down | (64.0, 448.0] | 1354 | 0.7238 | 1.6138 |
| optimized_lh100 | XAUUSD | H1 | buy | regime_reversal_risk | 1 | 375 | 0.7653 | 1.5733 |
| tp100_sl100_lh100 | GBPCAD | H1 | buy | lower_wick_to_range | (-0.001, 0.074] | 1337 | 0.7180 | 1.5696 |
| tp100_sl100_lh100 | GBPAUD | M15 | buy | volume_ratio | (-0.001, 0.381] | 1793 | 0.7078 | 1.5565 |
| tp100_sl100_lh100 | GBPAUD | M15 | buy | kaufman_er_10 | (-0.001, 0.0429] | 1852 | 0.6982 | 1.4911 |
| tp100_sl100_lh100 | GBPAUD | M15 | buy | distance_to_swing_low_atr | (-12.828999999999999, 0.643] | 1994 | 0.6941 | 1.4747 |
| optimized_lh100 | XAUUSD | H1 | buy | lower_wick_to_range | (0.074, 0.211] | 1144 | 0.7072 | 1.4591 |
| tp100_sl100_lh100 | AUDJPY | H1 | sell | overlap_ratio_10 | (0.711, 1.0] | 1466 | 0.6999 | 1.4572 |
| tp100_sl100_lh100 | GBPCHF | H1 | sell | day_of_week | (4.0, 6.0] | 1440 | 0.7000 | 1.4546 |
| atr1.5_slatr1_lh100 | NZDCHF | H1 | sell | range_contraction | 1 | 933 | 0.7117 | 1.4478 |
| tp100_sl100_lh100 | AUDJPY | H1 | sell | range_contraction | 1 | 1451 | 0.6975 | 1.4376 |
| atr1.5_slatr1_lh100 | AUDCHF | H1 | sell | hour | (17.0, 23.0] | 1248 | 0.6979 | 1.4112 |
| atr1.5_slatr1_lh100 | AUDCHF | H1 | sell | session | after_hours | 1248 | 0.6979 | 1.4112 |
| atr1.5_slatr1_lh100 | AUDCAD | H1 | sell | day_of_week | (4.0, 6.0] | 1427 | 0.6931 | 1.4024 |
| tp100_sl100_lh100 | AUDJPY | H1 | sell | volume_ratio | (-0.001, 0.381] | 1800 | 0.6850 | 1.3868 |
| atr1.5_slatr1_lh100 | AUDCHF | H1 | sell | overlap_ratio_10 | (0.711, 1.0] | 1480 | 0.6899 | 1.3861 |
| optimized_lh100 | XAUUSD | H1 | buy | bars_since_breakout_down | (64.0, 448.0] | 2026 | 0.6811 | 1.3793 |
| tp100_sl100_lh100 | GBPCAD | H1 | buy | close_position | (-0.001, 0.164] | 1422 | 0.6899 | 1.3786 |
| atr1.5_slatr1_lh100 | AUDCHF | H1 | sell | delta_proxy | (-0.0702, -0.0] | 1775 | 0.6834 | 1.3721 |
| tp100_sl100_lh100 | GBPCHF | M5 | sell | bars_since_volume_climax | (34.0, 248.0] | 949 | 0.6997 | 1.3691 |
| atr1.5_slatr1_lh100 | AUDCAD | H1 | sell | bars_since_breakout_up | (58.0, 605.0] | 873 | 0.7010 | 1.3616 |
| tp100_sl100_lh100 | EURGBP | M15 | sell | ema21_slope_atr | (0.337, 33191153721.958] | 746 | 0.7051 | 1.3569 |
| tp100_sl100_lh100 | EURGBP | M15 | sell | distance_to_swing_low_atr | (4.642, 463989257812.5] | 798 | 0.7030 | 1.3568 |
| tp100_sl100_lh100 | USDCHF | H1 | sell | ema21_slope_atr | (-1.71e-07, 0.337] | 1152 | 0.6918 | 1.3525 |
| tp100_sl100_lh100 | AUDNZD | H1 | sell | range_contraction | 1 | 710 | 0.7056 | 1.3503 |
| tp100_sl100_lh100 | GBPCHF | M15 | sell | bars_since_breakout_down | (64.0, 448.0] | 1232 | 0.6891 | 1.3460 |
| optimized_lh100 | NZDSGD | H1 | sell | upper_wick_to_range | (0.231, 0.407] | 1202 | 0.6897 | 1.3453 |
| tp100_sl100_lh100 | NZDSGD | H1 | sell | upper_wick_to_range | (0.231, 0.407] | 1202 | 0.6897 | 1.3453 |
| optimized_lh100 | NZDSGD | H1 | sell | range_zscore_20 | (-4.25, -0.639] | 1050 | 0.6924 | 1.3385 |
| tp100_sl100_lh100 | NZDSGD | H1 | sell | range_zscore_20 | (-4.25, -0.639] | 1050 | 0.6924 | 1.3385 |
| atr1.5_slatr1_lh100 | CADCHF | H1 | sell | hour | (17.0, 23.0] | 1248 | 0.6867 | 1.3312 |
| atr1.5_slatr1_lh100 | CADCHF | H1 | sell | session | after_hours | 1248 | 0.6867 | 1.3312 |
| tp100_sl100_lh100 | AUDCHF | M5 | sell | hour | (17.0, 23.0] | 1224 | 0.6871 | 1.3304 |

## Leitura recomendada

- `tp100_sl100_lh100` tende a gerar muitos candidatos; bom para exploracao, mas ruim para virar gate direto.
- `optimized_lh100` e mais seletivo; bom para validar ativos especificos, mas pode ficar concentrado demais.
- `atr1.5_slatr1_lh100` e o melhor ponto de partida para calibracao geral porque respeita volatilidade por candle.
- A proxima promocao deve ser somente para shadow/forward por ativo/timeframe/lado, nao para bloqueio global.