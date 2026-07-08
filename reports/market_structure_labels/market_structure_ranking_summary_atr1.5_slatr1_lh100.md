# Market Structure Feature Ranking

- Labels: 449.910
- Ranking rows: 25.488
- Ativos: 30
- Timeframes: H1, M15, M5

## Win rate geral por lado/timeframe

| timeframe | samples | buy_wr | sell_wr | buy_timeout_pct | sell_timeout_pct |
| --- | --- | --- | --- | --- | --- |
| H1 | 149970 | 0.3383 | 0.4349 | 0.0010 | 0.0009 |
| M15 | 149970 | 0.3031 | 0.3646 | 0.1584 | 0.1308 |
| M5 | 149970 | 0.2516 | 0.3964 | 0.0008 | 0.0013 |

## Top edges positivos

| feature | side | symbol | timeframe | bucket | samples | win_rate | edge_score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| regime_reversal_risk | sell | GBPCHF | H1 | 1 | 276 | 0.8152 | 1.7728 |
| regime_reversal_risk | sell | USDCAD | H1 | 1 | 440 | 0.7773 | 1.6883 |
| hour | sell | NZDCHF | H1 | (17.0, 23.0] | 1248 | 0.7356 | 1.6797 |
| session | sell | NZDCHF | H1 | after_hours | 1248 | 0.7356 | 1.6797 |
| regime_reversal_risk | sell | EURGBP | H1 | 1 | 162 | 0.8210 | 1.6350 |
| day_of_week | sell | AUDCHF | H1 | (4.0, 6.0] | 1440 | 0.7236 | 1.6263 |
| range_contraction | sell | NZDCHF | H1 | 1 | 933 | 0.7117 | 1.4478 |
| regime_reversal_risk | sell | EURCHF | H1 | 1 | 205 | 0.7707 | 1.4424 |
| hour | sell | AUDCHF | H1 | (17.0, 23.0] | 1248 | 0.6979 | 1.4112 |
| session | sell | AUDCHF | H1 | after_hours | 1248 | 0.6979 | 1.4112 |
| day_of_week | sell | AUDCAD | H1 | (4.0, 6.0] | 1427 | 0.6931 | 1.4024 |
| overlap_ratio_10 | sell | AUDCHF | H1 | (0.711, 1.0] | 1480 | 0.6899 | 1.3861 |
| delta_proxy | sell | AUDCHF | H1 | (-0.0702, -0.0] | 1775 | 0.6834 | 1.3721 |
| bars_since_breakout_up | sell | AUDCAD | H1 | (58.0, 605.0] | 873 | 0.7010 | 1.3616 |
| hour | sell | CADCHF | H1 | (17.0, 23.0] | 1248 | 0.6867 | 1.3312 |
| session | sell | CADCHF | H1 | after_hours | 1248 | 0.6867 | 1.3312 |
| bars_since_volume_climax | sell | AUDCHF | H1 | (34.0, 248.0] | 824 | 0.6966 | 1.3203 |
| delta_proxy | sell | AUDCAD | H1 | (-0.0702, -0.0] | 1570 | 0.6713 | 1.2610 |
| volume_ratio | sell | AUDCHF | H1 | (-0.001, 0.381] | 1738 | 0.6680 | 1.2535 |
| atr_ratio_5_50 | sell | NZDCHF | H1 | (-0.001, 0.752] | 1219 | 0.6743 | 1.2388 |
| range_contraction | sell | AUDCHF | H1 | 1 | 1129 | 0.6749 | 1.2298 |
| day_of_week | sell | CADCHF | H1 | (4.0, 6.0] | 1440 | 0.6667 | 1.2122 |
| kaufman_er_10 | sell | AUDCHF | H1 | (-0.001, 0.0429] | 1512 | 0.6627 | 1.1913 |
| day_of_week | sell | AUDJPY | H1 | (4.0, 6.0] | 1427 | 0.6636 | 1.1886 |
| regime_reversal_risk | sell | AUDCAD | H1 | 1 | 374 | 0.7005 | 1.1886 |
| price_extension_atr | sell | NZDCHF | H1 | (-3.15e-07, 0.711] | 1205 | 0.6672 | 1.1864 |
| bars_since_volume_climax | sell | EURCHF | H1 | (34.0, 248.0] | 801 | 0.6767 | 1.1813 |
| day_of_week | sell | EURCHF | H1 | (4.0, 6.0] | 1440 | 0.6604 | 1.1667 |
| delta_proxy | sell | AUDJPY | H1 | (-0.0702, -0.0] | 1477 | 0.6588 | 1.1588 |
| overlap_ratio_10 | sell | AUDCAD | H1 | (0.711, 1.0] | 1541 | 0.6567 | 1.1504 |

## Piores buckets

| feature | side | symbol | timeframe | bucket | samples | win_rate | edge_score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| change_of_character_up | buy | NZDSGD | M5 | 0 | 4957 | 0.0274 | -4.0209 |
| breakout_down_with_volume | buy | NZDSGD | M5 | 0 | 4923 | 0.0272 | -4.0195 |
| change_of_character_down | buy | NZDSGD | M5 | 0 | 4958 | 0.0276 | -4.0194 |
| regime_reversal_risk | buy | NZDSGD | M5 | 0 | 4909 | 0.0279 | -4.0123 |
| breakout_up_with_volume | buy | NZDSGD | M5 | 0 | 4893 | 0.0280 | -4.0100 |
| absorption | buy | NZDSGD | M5 | 0 | 4875 | 0.0279 | -4.0091 |
| break_of_structure_down | buy | NZDSGD | M5 | 0 | 4802 | 0.0273 | -4.0072 |
| liquidity_grab_down | buy | NZDSGD | M5 | 0 | 4781 | 0.0274 | -4.0042 |
| range_expansion | buy | NZDSGD | M5 | 0 | 4215 | 0.0211 | -3.9971 |
| regime_expansion | buy | NZDSGD | M5 | 0 | 4736 | 0.0281 | -3.9939 |
| break_of_structure_up | buy | NZDSGD | M5 | 0 | 4695 | 0.0285 | -3.9859 |
| liquidity_grab_up | buy | NZDSGD | M5 | 0 | 4668 | 0.0287 | -3.9818 |
| volatility_expansion | buy | NZDSGD | M5 | 0 | 4540 | 0.0293 | -3.9638 |
| range_contraction | buy | NZDSGD | M5 | 0 | 4070 | 0.0310 | -3.8985 |
| ema_alignment_sell | buy | NZDSGD | M5 | 0 | 3481 | 0.0267 | -3.8598 |
| regime_trend | buy | NZDSGD | M5 | 1 | 2857 | 0.0235 | -3.7923 |
| regime_consolidation | buy | NZDSGD | M5 | 1 | 2961 | 0.0280 | -3.7727 |
| volatility_compression | buy | NZDSGD | M5 | 0 | 3119 | 0.0330 | -3.7571 |
| volume_ratio | buy | NZDSGD | M5 | (0.813, 1.206] | 2592 | 0.0228 | -3.7514 |
| delta_proxy | buy | NZDSGD | M5 | (-0.0, 0.0828] | 2133 | 0.0127 | -3.7358 |
| ema_alignment_buy | buy | NZDSGD | M5 | 1 | 2529 | 0.0233 | -3.7352 |
| day_of_week | buy | NZDSGD | M5 | (-0.001, 1.0] | 2205 | 0.0231 | -3.6714 |
| delta_proxy | buy | NZDSGD | M5 | (-0.0702, -0.0] | 2132 | 0.0211 | -3.6709 |
| day_of_week | buy | AUDCHF | M15 | (4.0, 6.0] | 1536 | 0.0000 | -3.6688 |
| ema_alignment_buy | buy | NZDSGD | M5 | 0 | 2470 | 0.0324 | -3.6532 |
| volatility_compression | buy | NZDSGD | M5 | 1 | 1880 | 0.0191 | -3.6254 |
| day_of_week | buy | GBPCHF | M15 | (4.0, 6.0] | 1536 | 0.0078 | -3.6115 |
| day_of_week | buy | CADCHF | M15 | (4.0, 6.0] | 1536 | 0.0085 | -3.6067 |
| regime_consolidation | buy | NZDSGD | M5 | 0 | 2038 | 0.0275 | -3.6007 |
| day_of_week | buy | NZDCHF | M15 | (4.0, 6.0] | 1536 | 0.0098 | -3.5971 |

## Melhores features por frequencia no top 500

| feature | side | top500_count |
| --- | --- | --- |
| range_zscore_20 | sell | 21 |
| bars_since_breakout_down | sell | 18 |
| distance_to_swing_high_atr | sell | 17 |
| lower_wick_to_range | sell | 17 |
| regime_reversal_risk | sell | 17 |
| ema21_slope_atr | sell | 16 |
| range_to_atr | sell | 16 |
| overlap_ratio_10 | sell | 16 |
| close_position | sell | 16 |
| bars_since_volume_climax | sell | 15 |
| atr_ratio_5_50 | sell | 15 |
| volume_zscore | sell | 15 |
| hour | sell | 15 |
| session | sell | 15 |
| body_to_range | sell | 14 |
| day_of_week | sell | 14 |
| kaufman_er_10 | sell | 14 |
| price_extension_atr | sell | 14 |
| movement_efficiency | sell | 14 |
| distance_to_swing_low_atr | sell | 14 |
| delta_proxy | sell | 14 |
| volume_ratio | sell | 13 |
| kaufman_er_20 | sell | 13 |
| upper_wick_to_range | sell | 13 |
| bars_since_breakout_up | sell | 13 |
| velocity_atr_10 | sell | 11 |
| range_contraction | sell | 10 |
| volatility_compression | sell | 10 |
| regime_trend | sell | 8 |
| ema_alignment_buy | sell | 8 |