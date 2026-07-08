# Market Structure Feature Ranking

- Labels: 449.910
- Ranking rows: 25.488
- Ativos: 30
- Timeframes: H1, M15, M5

## Win rate geral por lado/timeframe

| timeframe | samples | buy_wr | sell_wr | buy_timeout_pct | sell_timeout_pct |
| --- | --- | --- | --- | --- | --- |
| H1 | 149970 | 0.1949 | 0.2075 | 0.0156 | 0.0174 |
| M15 | 149970 | 0.1004 | 0.0982 | 0.2321 | 0.2186 |
| M5 | 149970 | 0.0674 | 0.1008 | 0.1850 | 0.2188 |

## Top edges positivos

| feature | side | symbol | timeframe | bucket | samples | win_rate | edge_score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| hour | sell | NZDSGD | H1 | (17.0, 23.0] | 1248 | 0.7444 | 1.7425 |
| session | sell | NZDSGD | H1 | after_hours | 1248 | 0.7444 | 1.7425 |
| regime_reversal_risk | buy | XAUUSD | H1 | 1 | 375 | 0.7653 | 1.5733 |
| lower_wick_to_range | buy | XAUUSD | H1 | (0.074, 0.211] | 1144 | 0.7072 | 1.4591 |
| bars_since_breakout_down | buy | XAUUSD | H1 | (64.0, 448.0] | 2026 | 0.6811 | 1.3793 |
| upper_wick_to_range | sell | NZDSGD | H1 | (0.231, 0.407] | 1202 | 0.6897 | 1.3453 |
| range_zscore_20 | sell | NZDSGD | H1 | (-4.25, -0.639] | 1050 | 0.6924 | 1.3385 |
| ema_alignment_buy | buy | XAUUSD | H1 | 1 | 2758 | 0.6657 | 1.3128 |
| movement_efficiency | buy | XAUUSD | H1 | (0.471, 0.689] | 1026 | 0.6784 | 1.2368 |
| body_to_range | buy | XAUUSD | H1 | (0.471, 0.689] | 1026 | 0.6784 | 1.2368 |
| atr_ratio_5_50 | sell | NZDSGD | H1 | (0.752, 0.978] | 1763 | 0.6631 | 1.2190 |
| upper_wick_to_range | buy | XAUUSD | H1 | (0.407, 1.0] | 1099 | 0.6679 | 1.1757 |
| price_extension_atr | buy | XAUUSD | H1 | (-3.15e-07, 0.711] | 1338 | 0.6622 | 1.1677 |
| volatility_compression | sell | NZDSGD | H1 | 1 | 2232 | 0.6492 | 1.1504 |
| volume_ratio | sell | NZDSGD | H1 | (0.813, 1.206] | 1173 | 0.6624 | 1.1479 |
| range_to_atr | sell | NZDSGD | H1 | (0.0013999999999999998, 0.726] | 1203 | 0.6584 | 1.1233 |
| bars_since_breakout_up | buy | XAUUSD | H1 | (9.0, 26.0] | 1263 | 0.6564 | 1.1168 |
| ema21_slope_atr | buy | XAUUSD | H1 | (-1.71e-07, 0.337] | 1352 | 0.6546 | 1.1146 |
| ema_alignment_sell | buy | XAUUSD | H1 | 0 | 3691 | 0.6353 | 1.1116 |
| price_extension_atr | sell | NZDSGD | H1 | (-3.15e-07, 0.711] | 967 | 0.6587 | 1.0914 |
| regime_consolidation | sell | NZDSGD | H1 | 1 | 3240 | 0.6340 | 1.0828 |
| velocity_atr_10 | sell | NZDSGD | H1 | (0.0, 0.976] | 755 | 0.6583 | 1.0491 |
| movement_efficiency | sell | NZDSGD | H1 | (0.471, 0.689] | 1342 | 0.6453 | 1.0466 |
| body_to_range | sell | NZDSGD | H1 | (0.471, 0.689] | 1342 | 0.6453 | 1.0466 |
| ema21_slope_atr | buy | XAUUSD | H1 | (0.337, 33191153721.958] | 1745 | 0.6401 | 1.0460 |
| upper_wick_to_range | buy | XAUUSD | H1 | (0.0945, 0.231] | 1322 | 0.6452 | 1.0439 |
| bars_since_breakout_up | sell | NZDSGD | H1 | (26.0, 58.0] | 1422 | 0.6435 | 1.0416 |
| upper_wick_to_range | buy | XAUUSD | H1 | (-0.001, 0.0945] | 1219 | 0.6448 | 1.0290 |
| price_extension_atr | buy | XAUUSD | H1 | (0.711, 54366273643.438] | 1713 | 0.6363 | 1.0150 |
| kaufman_er_20 | sell | NZDSGD | H1 | (-0.001, 0.0405] | 1302 | 0.6413 | 1.0136 |

## Piores buckets

| feature | side | symbol | timeframe | bucket | samples | win_rate | edge_score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| change_of_character_down | buy | NZDCHF | M5 | 0 | 4953 | 0.0036 | -4.2231 |
| change_of_character_up | buy | NZDCHF | M5 | 0 | 4952 | 0.0036 | -4.2229 |
| breakout_down_with_volume | buy | NZDCHF | M5 | 0 | 4909 | 0.0037 | -4.2184 |
| regime_reversal_risk | buy | NZDCHF | M5 | 0 | 4908 | 0.0037 | -4.2182 |
| breakout_up_with_volume | buy | NZDCHF | M5 | 0 | 4896 | 0.0037 | -4.2170 |
| change_of_character_down | buy | EURCHF | M15 | 0 | 4962 | 0.0048 | -4.2137 |
| change_of_character_up | buy | EURCHF | M15 | 0 | 4962 | 0.0050 | -4.2120 |
| change_of_character_down | buy | NZDCAD | M5 | 0 | 4948 | 0.0051 | -4.2105 |
| absorption | buy | NZDCHF | M5 | 0 | 4812 | 0.0035 | -4.2096 |
| break_of_structure_down | buy | NZDCHF | M5 | 0 | 4808 | 0.0035 | -4.2091 |
| breakout_down_with_volume | buy | EURCHF | M15 | 0 | 4918 | 0.0049 | -4.2089 |
| change_of_character_up | buy | NZDCAD | M5 | 0 | 4949 | 0.0053 | -4.2089 |
| liquidity_grab_down | buy | NZDCHF | M5 | 0 | 4784 | 0.0033 | -4.2083 |
| regime_reversal_risk | buy | EURCHF | M15 | 0 | 4926 | 0.0051 | -4.2081 |
| liquidity_grab_down | buy | EURCHF | M15 | 0 | 4834 | 0.0043 | -4.2050 |
| breakout_up_with_volume | buy | EURCHF | M15 | 0 | 4897 | 0.0051 | -4.2049 |
| liquidity_grab_up | buy | NZDCHF | M5 | 0 | 4731 | 0.0032 | -4.2042 |
| regime_reversal_risk | buy | NZDCAD | M5 | 0 | 4906 | 0.0053 | -4.2042 |
| break_of_structure_down | buy | EURCHF | M15 | 0 | 4838 | 0.0045 | -4.2036 |
| change_of_character_up | sell | NZDUSD | M5 | 0 | 4948 | 0.0059 | -4.2036 |
| change_of_character_down | sell | NZDUSD | M5 | 0 | 4948 | 0.0059 | -4.2036 |
| breakout_up_with_volume | buy | NZDCAD | M5 | 0 | 4881 | 0.0051 | -4.2032 |
| breakout_down_with_volume | buy | NZDCAD | M5 | 0 | 4884 | 0.0053 | -4.2017 |
| break_of_structure_up | buy | EURCHF | M15 | 0 | 4863 | 0.0051 | -4.2012 |
| liquidity_grab_up | buy | EURCHF | M15 | 0 | 4838 | 0.0050 | -4.2001 |
| break_of_structure_up | buy | NZDCHF | M5 | 0 | 4728 | 0.0038 | -4.1985 |
| regime_reversal_risk | sell | NZDUSD | M5 | 0 | 4905 | 0.0061 | -4.1971 |
| breakout_up_with_volume | sell | NZDUSD | M5 | 0 | 4852 | 0.0056 | -4.1964 |
| breakout_down_with_volume | sell | NZDUSD | M5 | 0 | 4894 | 0.0061 | -4.1959 |
| regime_expansion | buy | NZDCHF | M5 | 0 | 4668 | 0.0036 | -4.1936 |

## Melhores features por frequencia no top 500

| feature | side | top500_count |
| --- | --- | --- |
| range_zscore_20 | buy | 9 |
| volume_ratio | sell | 9 |
| pressure_imbalance | sell | 9 |
| atr_ratio_5_50 | sell | 8 |
| hour | buy | 8 |
| kaufman_er_10 | buy | 8 |
| overlap_ratio_10 | sell | 8 |
| overlap_ratio_10 | buy | 8 |
| kaufman_er_10 | sell | 8 |
| day_of_week | sell | 8 |
| volume_zscore | buy | 8 |
| range_to_atr | buy | 8 |
| velocity_atr_10 | buy | 8 |
| volume_ratio | buy | 8 |
| session | buy | 8 |
| kaufman_er_20 | buy | 8 |
| delta_proxy | sell | 7 |
| ema21_slope_atr | sell | 7 |
| body_to_range | sell | 7 |
| atr_ratio_5_50 | buy | 7 |
| bars_since_volume_climax | sell | 7 |
| bars_since_volume_climax | buy | 7 |
| day_of_week | buy | 7 |
| bars_since_breakout_down | sell | 7 |
| movement_efficiency | sell | 7 |
| pressure_imbalance | buy | 7 |
| distance_to_swing_high_atr | buy | 7 |
| range_to_atr | sell | 7 |
| ema21_slope_atr | buy | 7 |
| distance_to_swing_low_atr | buy | 7 |