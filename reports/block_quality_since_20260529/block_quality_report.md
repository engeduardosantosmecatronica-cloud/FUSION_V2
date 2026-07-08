# Block Quality Since 2026-05-29

Generated at: 2026-06-03T12:39:14

## Method

- Uses DECISION events with decision=BLOCK from logs/events/events_20260529..20260603.
- Joins each blocked signal to operational_target_events price outcomes from 20260529, 20260531, 20260601 and 20260602.
- Classifies using net MFE/MAE points and a dynamic base threshold=max(30, 2x spread).
- 2026-06-03 decisions without operational_target_events remain marked sem_outcome.

## Scope

- Blocked decisions found: 83679
- Decisions with price outcome: 18401
- Missed/possible winners: 6990
- Good/probable good blocks: 9838

## By Symbol

| Symbol | Matched | Missed winners | Good blocks | Ambiguous | Missed % | Good % | Median MFE | Median MAE | Top blocker |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| AUDCAD | 1709 | 759 | 799 | 143 | 44.4 | 46.8 | 84.0 | 81.0 | allow_new_orders_false |
| GBPJPY | 1464 | 825 | 564 | 75 | 56.4 | 38.5 | 156.0 | 118.0 | preco_candle_nao_confirmado |
| CADCHF | 1442 | 316 | 902 | 89 | 21.9 | 62.6 | 18.0 | 99.0 | market_alignment |
| GBPCHF | 1417 | 521 | 853 | 31 | 36.8 | 60.2 | 78.0 | 122.0 | market_alignment |
| CHFJPY | 1368 | 666 | 645 | 57 | 48.7 | 47.1 | 225.5 | 207.0 | allow_new_orders_false |
| USDCHF | 1272 | 510 | 648 | 114 | 40.1 | 50.9 | 80.0 | 107.0 | allow_new_orders_false |
| NZDCHF | 1224 | 208 | 867 | 62 | 17.0 | 70.8 | 31.0 | 78.0 | allow_new_orders_false |
| NZDSGD | 1176 | 362 | 754 | 33 | 30.8 | 64.1 | 17.0 | 103.0 | market_alignment |
| EURCAD | 1021 | 575 | 372 | 74 | 56.3 | 36.4 | 191.0 | 108.0 | allow_new_orders_false |
| EURJPY | 1005 | 426 | 484 | 95 | 42.4 | 48.2 | 104.0 | 119.0 | allow_new_orders_false |
| NZDCAD | 981 | 285 | 628 | 68 | 29.1 | 64.0 | 63.0 | 132.0 | allow_new_orders_false |
| GBPCAD | 957 | 492 | 352 | 113 | 51.4 | 36.8 | 182.0 | 133.0 | market_alignment |
| USDJPY | 846 | 283 | 457 | 70 | 33.5 | 54.0 | 49.5 | 61.0 | allow_new_orders_false |
| EURNOK | 661 | 135 | 465 | 48 | 20.4 | 70.3 | 539.0 | 2014.0 | market_alignment |
| EURHUF | 605 | 176 | 339 | 54 | 29.1 | 56.0 | 273.0 | 820.0 | market_alignment |
| AUDUSD | 560 | 136 | 381 | 43 | 24.3 | 68.0 | 35.0 | 87.0 | timeframe_consensus |
| EURHKD | 361 | 123 | 218 | 18 | 34.1 | 60.4 | 365.0 | 1058.0 | market_alignment |
| BTCUSD | 332 | 192 | 110 | 30 | 57.8 | 33.1 | 49531.0 | 30347.0 | timeframe_consensus |
| AUDCHF | 0 | 0 | 0 | 0 |  |  |  |  | market_alignment |
| AUDJPY | 0 | 0 | 0 | 0 |  |  |  |  | timeframe_consensus |
| AUDNOK | 0 | 0 | 0 | 0 |  |  |  |  | market_alignment |
| AUDNZD | 0 | 0 | 0 | 0 |  |  |  |  | market_alignment |
| AUDSEK | 0 | 0 | 0 | 0 |  |  |  |  | market_alignment |
| AUDSGD | 0 | 0 | 0 | 0 |  |  |  |  | allow_new_orders_false |
| AUS200 | 0 | 0 | 0 | 0 |  |  |  |  | allow_new_orders_false |

## Most Missed Winner Groups

| Symbol | TF | Side | Matched | Missed winners | Good blocks | Top blocker |
|---|---|---|---:|---:|---:|---|
| CHFJPY | H1 | BUY | 600 | 306 | 261 | allow_new_orders_false |
| GBPJPY | H1 | BUY | 551 | 304 | 219 | preco_candle_nao_confirmado |
| GBPJPY | M30 | BUY | 538 | 298 | 214 | preco_candle_nao_confirmado |
| AUDCAD | H1 | BUY | 573 | 271 | 252 | allow_new_orders_false |
| GBPCAD | H4 | BUY | 510 | 258 | 181 | allow_new_orders_false |
| AUDCAD | M30 | BUY | 550 | 243 | 258 | allow_new_orders_false |
| EURCAD | H4 | BUY | 508 | 241 | 228 | risk_engine |
| EURJPY | H1 | BUY | 591 | 237 | 286 | timeframe_consensus |
| EURCAD | M30 | BUY | 294 | 210 | 66 | allow_new_orders_false |
| NZDSGD | H4 | BUY | 588 | 209 | 346 | market_alignment |
| USDJPY | H4 | BUY | 513 | 207 | 247 | allow_new_orders_false |
| GBPCAD | H1 | BUY | 393 | 204 | 150 | timeframe_consensus |
| EURJPY | M30 | BUY | 414 | 189 | 198 | preco_candle_nao_confirmado |
| CHFJPY | M30 | BUY | 378 | 186 | 177 | allow_new_orders_false |
| GBPCHF | H4 | SELL | 603 | 183 | 402 | market_alignment |
| USDCHF | M30 | SELL | 402 | 178 | 186 | allow_new_orders_false |
| USDCHF | H1 | SELL | 420 | 174 | 207 | allow_new_orders_false |
| CHFJPY | M15 | BUY | 366 | 171 | 186 | allow_new_orders_false |
| USDCHF | M15 | SELL | 447 | 158 | 252 | market_alignment |
| GBPCHF | M30 | SELL | 243 | 155 | 75 | allow_new_orders_false |
| NZDSGD | H1 | BUY | 444 | 153 | 264 | allow_new_orders_false |
| GBPCHF | H1 | SELL | 438 | 150 | 279 | market_alignment |
| CADCHF | H4 | BUY | 618 | 144 | 375 | market_alignment |
| CADCHF | H1 | BUY | 622 | 141 | 382 | market_alignment |
| GBPJPY | M15 | BUY | 207 | 135 | 60 | preco_candle_nao_confirmado |

## Best Blocks

| Symbol | TF | Side | Matched | Good blocks | Missed winners | Top blocker |
|---|---|---|---:|---:|---:|---|
| NZDCHF | H4 | BUY | 596 | 429 | 89 | allow_new_orders_false |
| GBPCHF | H4 | SELL | 603 | 402 | 183 | market_alignment |
| CADCHF | H1 | BUY | 622 | 382 | 141 | market_alignment |
| CADCHF | H4 | BUY | 618 | 375 | 144 | market_alignment |
| NZDSGD | H4 | BUY | 588 | 346 | 209 | market_alignment |
| NZDCAD | H4 | BUY | 486 | 325 | 132 | allow_new_orders_false |
| EURJPY | H1 | BUY | 591 | 286 | 237 | timeframe_consensus |
| GBPCHF | H1 | SELL | 438 | 279 | 150 | market_alignment |
| NZDCHF | H1 | BUY | 415 | 267 | 86 | allow_new_orders_false |
| NZDSGD | H1 | BUY | 444 | 264 | 153 | allow_new_orders_false |
| CHFJPY | H1 | BUY | 600 | 261 | 306 | allow_new_orders_false |
| AUDCAD | M30 | BUY | 550 | 258 | 243 | allow_new_orders_false |
| AUDCAD | H1 | BUY | 573 | 252 | 271 | allow_new_orders_false |
| USDCHF | M15 | SELL | 447 | 252 | 158 | market_alignment |
| USDJPY | H4 | BUY | 513 | 247 | 207 | allow_new_orders_false |
| EURCAD | H4 | BUY | 508 | 228 | 241 | risk_engine |
| AUDUSD | H1 | BUY | 294 | 222 | 48 | timeframe_consensus |
| GBPJPY | H1 | BUY | 551 | 219 | 304 | preco_candle_nao_confirmado |
| NZDCAD | H1 | BUY | 291 | 216 | 54 | allow_new_orders_false |
| GBPJPY | M30 | BUY | 538 | 214 | 298 | preco_candle_nao_confirmado |
| USDCHF | H1 | SELL | 420 | 207 | 174 | allow_new_orders_false |
| EURJPY | M30 | BUY | 414 | 198 | 189 | preco_candle_nao_confirmado |
| CHFJPY | M15 | BUY | 366 | 186 | 171 | allow_new_orders_false |
| USDCHF | M30 | SELL | 402 | 186 | 178 | allow_new_orders_false |
| GBPCAD | H4 | BUY | 510 | 181 | 258 | allow_new_orders_false |

## Blockers Behind Possible Winners

| Symbol | Blocker | Matched | Missed winners | Good blocks | Missed % | Good % |
|---|---|---:|---:|---:|---:|---:|
| GBPCHF | allow_new_orders_false | 576 | 461 | 84 | 80.0 | 14.6 |
| CHFJPY | allow_new_orders_false | 633 | 420 | 180 | 66.4 | 28.4 |
| USDCHF | allow_new_orders_false | 660 | 408 | 183 | 61.8 | 27.7 |
| AUDCAD | allow_new_orders_false | 758 | 295 | 360 | 38.9 | 47.5 |
| EURCAD | allow_new_orders_false | 492 | 280 | 159 | 56.9 | 32.3 |
| GBPJPY | allow_new_orders_false | 601 | 270 | 285 | 44.9 | 47.4 |
| GBPJPY | preco_candle_nao_confirmado | 447 | 251 | 180 | 56.2 | 40.3 |
| GBPJPY | portfolio_exposure | 238 | 231 | 0 | 97.1 | 0.0 |
| NZDSGD | allow_new_orders_false | 459 | 222 | 201 | 48.4 | 43.8 |
| CADCHF | market_alignment | 731 | 207 | 386 | 28.3 | 52.8 |
| EURJPY | allow_new_orders_false | 399 | 186 | 183 | 46.6 | 45.9 |
| EURHUF | allow_new_orders_false | 270 | 148 | 80 | 54.8 | 29.6 |
| AUDCAD | preco_candle_nao_confirmado | 361 | 146 | 188 | 40.4 | 52.1 |
| AUDCAD | market_alignment | 158 | 144 | 0 | 91.1 | 0.0 |
| NZDCAD | allow_new_orders_false | 435 | 129 | 244 | 29.7 | 56.1 |
| GBPCAD | allow_new_orders_false | 351 | 120 | 181 | 34.2 | 51.6 |
| EURJPY | market_alignment | 119 | 119 | 0 | 100.0 | 0.0 |
| GBPCAD | timeframe_consensus | 149 | 116 | 24 | 77.9 | 16.1 |
| GBPCAD | ema_nao_alinhada | 132 | 114 | 0 | 86.4 | 0.0 |
| NZDCHF | allow_new_orders_false | 618 | 107 | 470 | 17.3 | 76.1 |
| CHFJPY | market_alignment | 129 | 99 | 21 | 76.7 | 16.3 |
| USDJPY | preco_candle_nao_confirmado | 120 | 99 | 15 | 82.5 | 12.5 |
| BTCUSD | allow_new_orders_false | 164 | 91 | 56 | 55.5 | 34.1 |
| EURCAD | preco_candle_nao_confirmado | 259 | 91 | 153 | 35.1 | 59.1 |
| USDCHF | market_alignment | 320 | 87 | 224 | 27.2 | 70.0 |
