# Market Structure Calibration Candidates

Candidatos offline para calibracao. Nenhuma regra daqui e aplicada automaticamente no robo.

## Filtros

- Min samples: 300
- Min win rate: 60.00%
- Min edge score: 0.500
- Top por ativo/timeframe/lado: 5

- Ativos com candidatos: 2
- Combinacoes ativo/timeframe/lado: 4
- Regras candidatas: 19

## Top candidatos

| symbol | timeframe | side | feature | bucket | samples | win_rate | edge_score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| NZDSGD | H1 | sell | hour | (17.0, 23.0] | 1248 | 74.44% | 1.7425 |
| NZDSGD | H1 | sell | session | after_hours | 1248 | 74.44% | 1.7425 |
| XAUUSD | H1 | buy | regime_reversal_risk | 1 | 375 | 76.53% | 1.5733 |
| XAUUSD | H1 | buy | lower_wick_to_range | (0.074, 0.211] | 1144 | 70.72% | 1.4591 |
| XAUUSD | H1 | buy | bars_since_breakout_down | (64.0, 448.0] | 2026 | 68.11% | 1.3793 |
| NZDSGD | H1 | sell | upper_wick_to_range | (0.231, 0.407] | 1202 | 68.97% | 1.3453 |
| NZDSGD | H1 | sell | range_zscore_20 | (-4.25, -0.639] | 1050 | 69.24% | 1.3385 |
| XAUUSD | H1 | buy | ema_alignment_buy | 1 | 2758 | 66.57% | 1.3128 |
| XAUUSD | H1 | buy | movement_efficiency | (0.471, 0.689] | 1026 | 67.84% | 1.2368 |
| NZDSGD | H1 | sell | atr_ratio_5_50 | (0.752, 0.978] | 1763 | 66.31% | 1.2190 |
| XAUUSD | M15 | buy | upper_wick_to_range | (0.407, 1.0] | 1216 | 63.73% | 0.9757 |
| XAUUSD | H1 | sell | bars_since_breakout_down | (11.0, 30.0] | 929 | 63.83% | 0.9454 |
| XAUUSD | M15 | buy | close_position | (0.164, 0.44] | 1519 | 62.34% | 0.9044 |
| XAUUSD | M15 | buy | lower_wick_to_range | (0.074, 0.211] | 1331 | 62.36% | 0.8892 |
| XAUUSD | M15 | buy | movement_efficiency | (0.25, 0.471] | 1362 | 62.26% | 0.8850 |
| XAUUSD | M15 | buy | body_to_range | (0.25, 0.471] | 1362 | 62.26% | 0.8850 |
| XAUUSD | H1 | sell | volume_ratio | (0.381, 0.813] | 797 | 61.73% | 0.7839 |
| XAUUSD | H1 | sell | volume_ratio | (0.813, 1.206] | 1028 | 61.09% | 0.7692 |
| XAUUSD | H1 | sell | bars_since_breakout_up | (58.0, 605.0] | 717 | 60.81% | 0.7108 |