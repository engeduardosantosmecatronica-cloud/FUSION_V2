# Relatorio Inside Bar - Gold

## Configuracao

- Ativo historico/modelo: XAUUSD
- Ativo corretora: GOLD
- Timeframes: M5, M15, M30
- Entrada BUY: rompimento da maxima da inside bar
- Entrada SELL: rompimento da minima da inside bar
- Sem SL e sem TP fixo
- Saida: trailing stop com ativacao em 1000 pontos e distancia de 500 pontos
- Janela maxima: 1000 candles

## Resumo Por Timeframe

| TF | Trades | Wins | Losses | Flats | Win rate | Media resultado | Media a favor | Media contra | Candles ate saida |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M15 | 16863 | 14145 | 2718 | 0 | 83,88% | -153,81 | 5.276,14 | 5.085,73 | 290,40 |
| M30 | 9006 | 7997 | 1009 | 0 | 88,80% | -116,48 | 7.704,37 | 7.293,17 | 213,51 |
| M5 | 46418 | 36281 | 10135 | 2 | 78,16% | -121,73 | 3.635,60 | 3.456,26 | 402,72 |

## Resultado Por Direcao

| TF | Direcao | Trades | Wins | Losses | Win rate | Media resultado | Media a favor | Media contra |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M15 | BUY | 8500 | 7472 | 1028 | 87,91% | 190,74 | 6.162,39 | 4.446,31 |
| M15 | SELL | 8363 | 6673 | 1690 | 79,79% | -504,01 | 4.375,37 | 5.735,62 |
| M30 | BUY | 4603 | 4224 | 379 | 91,77% | 306,11 | 9.666,15 | 5.930,53 |
| M30 | SELL | 4403 | 3773 | 630 | 85,69% | -558,25 | 5.653,48 | 8.717,70 |
| M5 | BUY | 23393 | 19092 | 4299 | 81,61% | 116,83 | 3.990,57 | 3.170,66 |
| M5 | SELL | 23025 | 17189 | 5836 | 74,65% | -364,10 | 3.274,96 | 3.746,42 |

## Melhores Padroes

| TF | Direcao | Candle mae | Inside | Trades | Wins | Win rate | Media resultado | Media a favor | Media contra |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M15 | BUY | baixa | doji | 24 | 24 | 100,00% | 922,92 | 6.076,54 | 2.297,29 |
| M30 | BUY | alta | doji | 7 | 7 | 100,00% | 868,86 | 10.051,86 | 2.714,29 |
| M30 | SELL | alta | doji | 7 | 7 | 100,00% | 857,86 | 4.848,71 | 4.310,29 |
| M5 | BUY | doji | doji | 3 | 3 | 100,00% | 938,67 | 5.092,67 | 1.226,33 |
| M15 | BUY | doji | baixa | 2 | 2 | 100,00% | 1.206,00 | 14.137,00 | 494,00 |
| M30 | BUY | doji | baixa | 2 | 2 | 100,00% | 842,50 | 12.965,50 | 3.787,00 |
| M30 | SELL | doji | alta | 2 | 2 | 100,00% | 1.021,00 | 6.226,00 | 7.627,50 |
| M5 | SELL | doji | doji | 2 | 2 | 100,00% | 855,00 | 2.922,50 | 3.118,50 |
| M30 | BUY | alta | alta | 873 | 819 | 93,81% | 443,49 | 9.717,06 | 5.975,58 |
| M30 | BUY | baixa | alta | 2206 | 2029 | 91,98% | 319,73 | 9.952,50 | 6.118,73 |
| M30 | BUY | baixa | baixa | 389 | 355 | 91,26% | 267,20 | 9.299,46 | 5.324,13 |
| M30 | BUY | alta | baixa | 1110 | 999 | 90,00% | 193,91 | 9.254,91 | 5.738,44 |
| M15 | BUY | alta | doji | 30 | 27 | 90,00% | 310,23 | 5.189,73 | 4.318,73 |
| M15 | BUY | alta | alta | 1623 | 1442 | 88,85% | 214,65 | 6.239,96 | 4.389,36 |
| M15 | BUY | alta | baixa | 2017 | 1792 | 88,84% | 303,54 | 6.077,93 | 4.350,74 |
| M15 | BUY | baixa | baixa | 742 | 657 | 88,54% | 223,22 | 5.972,64 | 4.440,10 |
| M15 | SELL | alta | doji | 24 | 21 | 87,50% | 448,00 | 3.993,33 | 4.847,83 |
| M15 | SELL | doji | baixa | 8 | 7 | 87,50% | -354,75 | 3.206,13 | 5.600,50 |
| M15 | BUY | baixa | alta | 4050 | 3519 | 86,89% | 113,54 | 6.212,00 | 4.534,49 |
| M30 | SELL | alta | baixa | 2107 | 1827 | 86,71% | -462,46 | 5.596,79 | 8.531,85 |
| M30 | SELL | baixa | alta | 1045 | 899 | 86,03% | -515,27 | 5.782,20 | 9.054,10 |
| M5 | BUY | alta | doji | 150 | 127 | 84,67% | 251,29 | 3.908,58 | 2.887,15 |
| M30 | SELL | baixa | baixa | 886 | 750 | 84,65% | -693,90 | 5.628,76 | 8.413,29 |
| M5 | BUY | doji | baixa | 36 | 30 | 83,33% | 582,81 | 3.255,39 | 1.858,50 |
| M30 | SELL | baixa | doji | 6 | 5 | 83,33% | -310,33 | 6.963,17 | 6.930,83 |
| M5 | BUY | baixa | alta | 10923 | 8966 | 82,08% | 124,88 | 4.051,73 | 3.263,67 |
| M30 | BUY | baixa | doji | 11 | 9 | 81,82% | -764,82 | 3.721,91 | 7.586,82 |
| M5 | BUY | alta | alta | 4343 | 3544 | 81,60% | 132,73 | 3.965,31 | 3.017,37 |
| M5 | BUY | baixa | baixa | 1994 | 1624 | 81,44% | 105,86 | 4.076,05 | 3.310,11 |
| M15 | SELL | baixa | baixa | 1657 | 1349 | 81,41% | -451,27 | 4.535,92 | 6.118,85 |

## Arquivos Gerados

- Relatorio: `relatorio_insidebar_gold.md`
- Resumo CSV: `insidebar_gold_resumo.csv`
- Direcao CSV: `insidebar_gold_direcao.csv`
- Padroes CSV: `insidebar_gold_padroes.csv`
- Trades CSV: `insidebar_gold_trades.csv`