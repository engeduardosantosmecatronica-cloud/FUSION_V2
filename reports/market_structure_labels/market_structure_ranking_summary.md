# Market Structure Feature Ranking

- Labels: 449.910
- Ranking rows: 25.488
- Ativos: 30
- Timeframes: H1, M15, M5

## Win rate geral por lado/timeframe

| timeframe | samples | buy_wr | sell_wr | buy_timeout_pct | sell_timeout_pct |
| --- | --- | --- | --- | --- | --- |
| H1 | 149970 | 0.4254 | 0.5043 | 0.0002 | 0.0002 |
| M15 | 149970 | 0.3963 | 0.4338 | 0.1438 | 0.1438 |
| M5 | 149970 | 0.3729 | 0.4751 | 0.0470 | 0.0498 |

## Top edges positivos

| feature | side | symbol | timeframe | bucket | samples | win_rate | edge_score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| hour | sell | NZDCHF | H1 | (17.0, 23.0] | 1248 | 0.8421 | 2.4395 |
| session | sell | NZDCHF | H1 | after_hours | 1248 | 0.8421 | 2.4395 |
| day_of_week | sell | AUDCHF | H1 | (4.0, 6.0] | 1440 | 0.8333 | 2.4244 |
| day_of_week | sell | NZDCHF | H1 | (4.0, 6.0] | 1440 | 0.8326 | 2.4193 |
| overlap_ratio_10 | sell | NZDCHF | H1 | (0.711, 1.0] | 1541 | 0.8092 | 2.2699 |
| volume_ratio | sell | NZDCHF | H1 | (-0.001, 0.381] | 1586 | 0.8064 | 2.2583 |
| overlap_ratio_10 | sell | AUDCHF | H1 | (0.711, 1.0] | 1480 | 0.8088 | 2.2543 |
| range_contraction | sell | NZDCHF | H1 | 1 | 933 | 0.8253 | 2.2248 |
| delta_proxy | sell | NZDCHF | H1 | (-0.0702, -0.0] | 1795 | 0.7939 | 2.2021 |
| delta_proxy | sell | AUDCHF | H1 | (-0.0702, -0.0] | 1775 | 0.7938 | 2.1983 |
| regime_reversal_risk | sell | AUDCHF | H1 | 1 | 312 | 0.8782 | 2.1732 |
| hour | sell | AUDCHF | H1 | (17.0, 23.0] | 1248 | 0.8045 | 2.1710 |
| session | sell | AUDCHF | H1 | after_hours | 1248 | 0.8045 | 2.1710 |
| bars_since_volume_climax | sell | NZDCHF | H1 | (34.0, 248.0] | 862 | 0.8155 | 2.1332 |
| atr_ratio_5_50 | sell | NZDCHF | H1 | (-0.001, 0.752] | 1219 | 0.7990 | 2.1250 |
| volume_ratio | sell | AUDCHF | H1 | (-0.001, 0.381] | 1738 | 0.7837 | 2.1164 |
| hour | sell | CADCHF | H1 | (17.0, 23.0] | 1248 | 0.7941 | 2.0968 |
| session | sell | CADCHF | H1 | after_hours | 1248 | 0.7941 | 2.0968 |
| range_contraction | sell | AUDCHF | H1 | 1 | 1129 | 0.7972 | 2.0891 |
| kaufman_er_10 | sell | AUDCHF | H1 | (-0.001, 0.0429] | 1512 | 0.7798 | 2.0484 |
| range_to_atr | sell | NZDCHF | H1 | (1.0, 1.125] | 1282 | 0.7847 | 2.0377 |
| kaufman_er_10 | sell | NZDCHF | H1 | (-0.001, 0.0429] | 1521 | 0.7771 | 2.0307 |
| atr_ratio_5_50 | sell | AUDCHF | H1 | (-0.001, 0.752] | 1383 | 0.7780 | 2.0108 |
| bars_since_volume_climax | sell | AUDCHF | H1 | (34.0, 248.0] | 824 | 0.7973 | 1.9967 |
| volatility_compression | sell | NZDCHF | H1 | 1 | 2118 | 0.7559 | 1.9599 |
| regime_consolidation | sell | NZDCHF | H1 | 1 | 3001 | 0.7438 | 1.9517 |
| day_of_week | sell | NZDCAD | H1 | (4.0, 6.0] | 1427 | 0.7673 | 1.9420 |
| day_of_week | sell | CADCHF | H1 | (4.0, 6.0] | 1440 | 0.7667 | 1.9395 |
| hour | sell | GBPCHF | M5 | (17.0, 23.0] | 1224 | 0.7721 | 1.9345 |
| session | sell | GBPCHF | M5 | after_hours | 1224 | 0.7721 | 1.9345 |

## Piores buckets

| feature | side | symbol | timeframe | bucket | samples | win_rate | edge_score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| change_of_character_down | buy | XAUUSD | M5 | 0 | 4953 | 0.0061 | -4.2024 |
| change_of_character_up | buy | XAUUSD | M5 | 0 | 4952 | 0.0063 | -4.2006 |
| breakout_down_with_volume | buy | XAUUSD | M5 | 0 | 4893 | 0.0061 | -4.1958 |
| regime_reversal_risk | buy | XAUUSD | M5 | 0 | 4878 | 0.0062 | -4.1941 |
| absorption | buy | XAUUSD | M5 | 0 | 4883 | 0.0063 | -4.1929 |
| break_of_structure_down | buy | XAUUSD | M5 | 0 | 4845 | 0.0060 | -4.1922 |
| breakout_up_with_volume | buy | XAUUSD | M5 | 0 | 4846 | 0.0064 | -4.1888 |
| liquidity_grab_down | buy | XAUUSD | M5 | 0 | 4824 | 0.0062 | -4.1880 |
| liquidity_grab_up | buy | XAUUSD | M5 | 0 | 4664 | 0.0060 | -4.1732 |
| break_of_structure_up | buy | XAUUSD | M5 | 0 | 4646 | 0.0060 | -4.1711 |
| regime_expansion | buy | XAUUSD | M5 | 0 | 4561 | 0.0057 | -4.1647 |
| volatility_expansion | buy | XAUUSD | M5 | 0 | 4418 | 0.0052 | -4.1531 |
| range_contraction | buy | XAUUSD | M5 | 0 | 4014 | 0.0057 | -4.1014 |
| range_expansion | buy | XAUUSD | M5 | 0 | 4075 | 0.0069 | -4.0993 |
| ema_alignment_sell | buy | XAUUSD | M5 | 0 | 3665 | 0.0071 | -4.0452 |
| volatility_compression | buy | XAUUSD | M5 | 0 | 3174 | 0.0050 | -3.9909 |
| regime_trend | buy | XAUUSD | M5 | 1 | 2830 | 0.0074 | -3.9152 |
| regime_consolidation | buy | XAUUSD | M5 | 1 | 2748 | 0.0062 | -3.9105 |
| pressure | buy | XAUUSD | M5 | (8.56e-07, 1.575] | 2621 | 0.0053 | -3.8938 |
| delta_proxy | buy | XAUUSD | M5 | (0.0828, 3085097.053] | 2617 | 0.0053 | -3.8930 |
| volume_ratio | buy | XAUUSD | M5 | (0.813, 1.206] | 2510 | 0.0032 | -3.8893 |
| ema_alignment_buy | buy | XAUUSD | M5 | 0 | 2447 | 0.0041 | -3.8696 |
| ema_alignment_buy | buy | XAUUSD | M5 | 1 | 2552 | 0.0082 | -3.8580 |
| delta_proxy | buy | XAUUSD | M5 | (-12905231.517, -0.0702] | 2365 | 0.0072 | -3.8286 |
| pressure | buy | XAUUSD | M5 | (-1.1409999999999998, -7.56e-07] | 2365 | 0.0072 | -3.8286 |
| regime_consolidation | buy | XAUUSD | M5 | 0 | 2251 | 0.0062 | -3.8118 |
| regime_trend | buy | XAUUSD | M5 | 0 | 2169 | 0.0046 | -3.8058 |
| day_of_week | buy | XAUUSD | M5 | (-0.001, 1.0] | 2094 | 0.0029 | -3.8017 |
| bars_since_breakout_up | buy | XAUUSD | M5 | (-0.001, 9.0] | 1925 | 0.0068 | -3.7305 |
| distance_to_swing_low_atr | buy | XAUUSD | M5 | (4.642, 463989257812.5] | 1937 | 0.0093 | -3.7144 |

## Melhores features por frequencia no top 500

| feature | side | top500_count |
| --- | --- | --- |
| hour | sell | 21 |
| session | sell | 21 |
| price_extension_atr | sell | 18 |
| ema21_slope_atr | sell | 17 |
| bars_since_volume_climax | sell | 16 |
| range_zscore_20 | sell | 16 |
| bars_since_breakout_down | sell | 15 |
| regime_reversal_risk | sell | 15 |
| day_of_week | sell | 15 |
| range_to_atr | sell | 15 |
| bars_since_breakout_up | sell | 14 |
| atr_ratio_5_50 | sell | 14 |
| distance_to_swing_high_atr | sell | 13 |
| upper_wick_to_range | sell | 12 |
| distance_to_swing_low_atr | sell | 12 |
| kaufman_er_20 | sell | 12 |
| overlap_ratio_10 | sell | 11 |
| volume_zscore | sell | 11 |
| velocity_atr_10 | sell | 11 |
| movement_efficiency | sell | 11 |
| body_to_range | sell | 11 |
| kaufman_er_10 | sell | 11 |
| close_position | sell | 11 |
| volatility_compression | sell | 10 |
| volume_ratio | sell | 10 |
| delta_proxy | sell | 10 |
| lower_wick_to_range | sell | 10 |
| range_contraction | sell | 9 |
| ema_alignment_buy | sell | 8 |
| ema_alignment_sell | sell | 8 |