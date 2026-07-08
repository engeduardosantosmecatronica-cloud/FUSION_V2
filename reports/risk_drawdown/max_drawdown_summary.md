# Maior drawdown por ativo
Fonte: `reports\signal_path_outcomes_m1_spread_targets\signal_path_outcomes_20260524_20260525_20260526_20260527_20260528_20260529_20260524_000000_to_20260529_101500_mt5offset6h_M15_H1_H4_path.csv`
Gerado em: 2026-07-08T00:57:29

Interpretacao: drawdown aqui = maior MAE liquido (`w1p0_net_mae_points`) observado apos entrada, em pontos, ja considerando spread. Para stop operacional, prefira `p95` + margem em vez do pior absoluto, porque o pior absoluto pode ser outlier.

## Resumo por ativo
| Ativo | Sinais | Pior DD pts | P95 DD pts | Grupo ref | SL sugerido | TP sugerido |
|---|---:|---:|---:|---|---:|---:|
| AUDJPY | 18 | 149.0 | 149.0 | H1 BUY | 165.0 | 5.0 |
| CADCHF | 9 | 64.0 | 64.0 | M15 BUY | 75.0 | 5.0 |
| CHFJPY | 32 | 90.0 | 87.0 | M15 BUY | 100.0 | 5.0 |
| EURCAD | 126 | 263.0 | 243.0 | H4 BUY | 270.0 | 30.0 |
| EURGBP | 26 | 52.0 | 51.25 | H4 SELL | 60.0 | 35.0 |
| EURNZD | 16 | 96.0 | 96.0 | H1 BUY | 110.0 | 5.0 |
| EURUSD | 41 | 107.0 | 103.0 | H1 BUY | 115.0 | 5.0 |
| GBPCHF | 3 | 25.0 | 25.0 | H1 SELL | 30.0 | 20.0 |
| GBPUSD | 46 | 126.0 | 125.0 | H1 BUY | 140.0 | 15.0 |
| NZDCHF | 6 | 68.0 | 68.0 | H1 BUY | 55.0 | 5.0 |
| NZDSGD | 6 | 67.0 | 67.0 | H1 BUY | 75.0 | 5.0 |
| NZDUSD | 35 | 108.0 | 89.8 | H1 BUY | 100.0 | 5.0 |
| USDCHF | 3 | 36.0 | 36.0 | H1 SELL | 40.0 | 20.0 |

## Top grupos por pior drawdown
| Ativo | TF | Lado | Sinais | Pior DD | P95 DD | Med DD | Med MFE | SL sug | TP sug |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| EURCAD | H4 | BUY | 126 | 263.0 | 243.0 | 116.0 | 20.5 | 270.0 | 30.0 |
| AUDJPY | H1 | BUY | 18 | 149.0 | 149.0 | 143.5 | -17.0 | 165.0 | 5.0 |
| GBPUSD | H1 | BUY | 46 | 126.0 | 125.0 | 104.5 | 2.0 | 140.0 | 15.0 |
| NZDUSD | H1 | BUY | 35 | 108.0 | 89.8 | 64.0 | 0.0 | 100.0 | 5.0 |
| EURUSD | H1 | BUY | 41 | 107.0 | 103.0 | 90.0 | -4.0 | 115.0 | 5.0 |
| EURNZD | H1 | BUY | 16 | 96.0 | 96.0 | 84.5 | -25.0 | 110.0 | 5.0 |
| CHFJPY | M15 | BUY | 29 | 90.0 | 87.0 | 46.0 | 4.0 | 100.0 | 5.0 |
| NZDCHF | H4 | BUY | 3 | 68.0 | 68.0 | 68.0 | 31.0 | 75.0 | 30.0 |
| NZDSGD | H1 | BUY | 3 | 67.0 | 67.0 | 67.0 | 8.0 | 75.0 | 5.0 |
| NZDSGD | H4 | BUY | 3 | 67.0 | 67.0 | 67.0 | 121.0 | 75.0 | 60.0 |
| CHFJPY | H1 | BUY | 3 | 65.0 | 65.0 | 65.0 | 86.0 | 75.0 | 60.0 |
| CADCHF | M15 | BUY | 9 | 64.0 | 64.0 | 51.0 | -30.0 | 75.0 | 5.0 |
| EURGBP | H4 | SELL | 26 | 52.0 | 51.25 | 43.5 | 35.0 | 60.0 | 35.0 |
| NZDCHF | H1 | BUY | 3 | 48.0 | 48.0 | 48.0 | -5.0 | 55.0 | 5.0 |
| USDCHF | H1 | SELL | 3 | 36.0 | 36.0 | 36.0 | 24.0 | 40.0 | 20.0 |
| GBPCHF | H1 | SELL | 3 | 25.0 | 25.0 | 25.0 | 34.0 | 30.0 | 20.0 |
