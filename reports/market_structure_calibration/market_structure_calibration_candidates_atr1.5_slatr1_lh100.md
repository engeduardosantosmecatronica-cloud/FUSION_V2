# Market Structure Calibration Candidates

Candidatos offline para calibracao. Nenhuma regra daqui e aplicada automaticamente no robo.

## Filtros

- Min samples: 300
- Min win rate: 60.00%
- Min edge score: 0.500
- Top por ativo/timeframe/lado: 5

- Ativos com candidatos: 11
- Combinacoes ativo/timeframe/lado: 13
- Regras candidatas: 46

## Top candidatos

| symbol | timeframe | side | feature | bucket | samples | win_rate | edge_score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| USDCAD | H1 | sell | regime_reversal_risk | 1 | 440 | 77.73% | 1.6883 |
| NZDCHF | H1 | sell | hour | (17.0, 23.0] | 1248 | 73.56% | 1.6797 |
| NZDCHF | H1 | sell | session | after_hours | 1248 | 73.56% | 1.6797 |
| AUDCHF | H1 | sell | day_of_week | (4.0, 6.0] | 1440 | 72.36% | 1.6263 |
| NZDCHF | H1 | sell | range_contraction | 1 | 933 | 71.17% | 1.4478 |
| AUDCHF | H1 | sell | hour | (17.0, 23.0] | 1248 | 69.79% | 1.4112 |
| AUDCHF | H1 | sell | session | after_hours | 1248 | 69.79% | 1.4112 |
| AUDCAD | H1 | sell | day_of_week | (4.0, 6.0] | 1427 | 69.31% | 1.4024 |
| AUDCHF | H1 | sell | overlap_ratio_10 | (0.711, 1.0] | 1480 | 68.99% | 1.3861 |
| AUDCHF | H1 | sell | delta_proxy | (-0.0702, -0.0] | 1775 | 68.34% | 1.3721 |
| AUDCAD | H1 | sell | bars_since_breakout_up | (58.0, 605.0] | 873 | 70.10% | 1.3616 |
| CADCHF | H1 | sell | hour | (17.0, 23.0] | 1248 | 68.67% | 1.3312 |
| CADCHF | H1 | sell | session | after_hours | 1248 | 68.67% | 1.3312 |
| AUDCAD | H1 | sell | delta_proxy | (-0.0702, -0.0] | 1570 | 67.13% | 1.2610 |
| NZDCHF | H1 | sell | atr_ratio_5_50 | (-0.001, 0.752] | 1219 | 67.43% | 1.2388 |
| CADCHF | H1 | sell | day_of_week | (4.0, 6.0] | 1440 | 66.67% | 1.2122 |
| AUDJPY | H1 | sell | day_of_week | (4.0, 6.0] | 1427 | 66.36% | 1.1886 |
| AUDCAD | H1 | sell | regime_reversal_risk | 1 | 374 | 70.05% | 1.1886 |
| NZDCHF | H1 | sell | price_extension_atr | (-3.15e-07, 0.711] | 1205 | 66.72% | 1.1864 |
| EURCHF | H1 | sell | bars_since_volume_climax | (34.0, 248.0] | 801 | 67.67% | 1.1813 |
| EURCHF | H1 | sell | day_of_week | (4.0, 6.0] | 1440 | 66.04% | 1.1667 |
| AUDJPY | H1 | sell | delta_proxy | (-0.0702, -0.0] | 1477 | 65.88% | 1.1588 |
| AUDCAD | H1 | sell | overlap_ratio_10 | (0.711, 1.0] | 1541 | 65.67% | 1.1504 |
| GBPCAD | H1 | sell | regime_reversal_risk | 1 | 385 | 68.31% | 1.0906 |
| NZDCAD | H1 | sell | day_of_week | (4.0, 6.0] | 1427 | 64.33% | 1.0410 |
| GBPJPY | H1 | sell | delta_proxy | (-0.0702, -0.0] | 1470 | 63.95% | 1.0171 |
| CADCHF | H1 | sell | overlap_ratio_10 | (0.711, 1.0] | 1601 | 63.71% | 1.0117 |
| CADCHF | H1 | sell | volume_ratio | (-0.001, 0.381] | 1687 | 63.54% | 1.0066 |
| GBPJPY | H1 | sell | day_of_week | (4.0, 6.0] | 1427 | 63.42% | 0.9748 |
| EURCHF | H1 | sell | kaufman_er_10 | (-0.001, 0.0429] | 1537 | 63.04% | 0.9573 |
| AUDJPY | H1 | sell | range_contraction | 1 | 1451 | 63.06% | 0.9509 |
| GBPCHF | H1 | sell | price_extension_atr | (-3.15e-07, 0.711] | 1308 | 62.84% | 0.9218 |
| EURCHF | H1 | sell | range_to_atr | (1.0, 1.125] | 1437 | 62.42% | 0.9032 |
| NZDCAD | H1 | sell | overlap_ratio_10 | (0.711, 1.0] | 1526 | 62.12% | 0.8888 |
| AUDJPY | H1 | sell | kaufman_er_10 | (-0.001, 0.0429] | 1495 | 62.07% | 0.8826 |
| EURCHF | H1 | sell | kaufman_er_20 | (-0.001, 0.0405] | 1376 | 61.99% | 0.8667 |
| AUDJPY | H1 | sell | overlap_ratio_10 | (0.711, 1.0] | 1466 | 61.87% | 0.8654 |
| GBPJPY | H1 | sell | range_contraction | 1 | 1441 | 61.76% | 0.8556 |
| EURCHF | M15 | sell | price_extension_atr | (-3.15e-07, 0.711] | 1110 | 62.16% | 0.8529 |
| NZDCAD | H1 | sell | delta_proxy | (-0.0702, -0.0] | 1636 | 61.43% | 0.8459 |
| NZDCAD | H1 | sell | volume_ratio | (-0.001, 0.381] | 1668 | 61.39% | 0.8452 |
| NZDCAD | H1 | sell | range_to_atr | (1.0, 1.125] | 1381 | 61.12% | 0.8038 |
| GBPCHF | H1 | sell | ema21_slope_atr | (-1.71e-07, 0.337] | 1340 | 60.67% | 0.7685 |
| CADCHF | M15 | sell | bars_since_breakout_down | (64.0, 448.0] | 1352 | 60.13% | 0.7306 |
| GBPCHF | H1 | sell | hour | (17.0, 23.0] | 1248 | 60.18% | 0.7256 |
| GBPCHF | H1 | sell | session | after_hours | 1248 | 60.18% | 0.7256 |