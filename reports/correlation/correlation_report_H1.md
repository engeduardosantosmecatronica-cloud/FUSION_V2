# Asset Correlation Report

- Timeframe: H1
- Ativos calculados: 31
- Barras alinhadas: 3173
- Threshold: 0.70

## Regra de risco

- Correlacao positiva forte: mesma direcao empilha risco.
- Correlacao negativa forte: direcoes opostas empilham risco.
- O filtro bloqueia apenas quando a posicao correlacionada ja esta em prejuizo.

## Pares fortes

| symbol_a | symbol_b | corr | risco | favoravel |
| --- | --- | --- | --- | --- |
| AUDSGD | AUDUSD | 0.8772 | BUY+BUY acumula risco se um estiver perdendo; SELL+SELL acumula risco se um estiver perdendo | direcoes opostas tendem a hedge |
| NZDSGD | NZDUSD | 0.8599 | BUY+BUY acumula risco se um estiver perdendo; SELL+SELL acumula risco se um estiver perdendo | direcoes opostas tendem a hedge |
| AUDJPY | NZDJPY | 0.8575 | BUY+BUY acumula risco se um estiver perdendo; SELL+SELL acumula risco se um estiver perdendo | direcoes opostas tendem a hedge |
| AUDCAD | AUDUSD | 0.8418 | BUY+BUY acumula risco se um estiver perdendo; SELL+SELL acumula risco se um estiver perdendo | direcoes opostas tendem a hedge |
| AUDCHF | EURAUD | -0.8259 | BUY+SELL acumula risco se um estiver perdendo; SELL+BUY acumula risco se um estiver perdendo | mesma direcao tende a hedge |
| AUDCAD | AUDSGD | 0.8244 | BUY+BUY acumula risco se um estiver perdendo; SELL+SELL acumula risco se um estiver perdendo | direcoes opostas tendem a hedge |
| EURUSD | USDCHF | -0.8233 | BUY+SELL acumula risco se um estiver perdendo; SELL+BUY acumula risco se um estiver perdendo | mesma direcao tende a hedge |
| NZDCAD | NZDUSD | 0.8228 | BUY+BUY acumula risco se um estiver perdendo; SELL+SELL acumula risco se um estiver perdendo | direcoes opostas tendem a hedge |
| CADJPY | USDJPY | 0.8165 | BUY+BUY acumula risco se um estiver perdendo; SELL+SELL acumula risco se um estiver perdendo | direcoes opostas tendem a hedge |
| AUDUSD | NZDUSD | 0.8091 | BUY+BUY acumula risco se um estiver perdendo; SELL+SELL acumula risco se um estiver perdendo | direcoes opostas tendem a hedge |
| EURAUD | GBPAUD | 0.8069 | BUY+BUY acumula risco se um estiver perdendo; SELL+SELL acumula risco se um estiver perdendo | direcoes opostas tendem a hedge |
| CHFJPY | EURJPY | 0.8059 | BUY+BUY acumula risco se um estiver perdendo; SELL+SELL acumula risco se um estiver perdendo | direcoes opostas tendem a hedge |
| NZDCAD | NZDSGD | 0.8054 | BUY+BUY acumula risco se um estiver perdendo; SELL+SELL acumula risco se um estiver perdendo | direcoes opostas tendem a hedge |
| AUDSGD | EURAUD | -0.8031 | BUY+SELL acumula risco se um estiver perdendo; SELL+BUY acumula risco se um estiver perdendo | mesma direcao tende a hedge |
| AUDCHF | NZDCHF | 0.7952 | BUY+BUY acumula risco se um estiver perdendo; SELL+SELL acumula risco se um estiver perdendo | direcoes opostas tendem a hedge |
| EURJPY | GBPJPY | 0.7919 | BUY+BUY acumula risco se um estiver perdendo; SELL+SELL acumula risco se um estiver perdendo | direcoes opostas tendem a hedge |
| CADJPY | EURJPY | 0.7798 | BUY+BUY acumula risco se um estiver perdendo; SELL+SELL acumula risco se um estiver perdendo | direcoes opostas tendem a hedge |
| AUDCHF | AUDSGD | 0.7797 | BUY+BUY acumula risco se um estiver perdendo; SELL+SELL acumula risco se um estiver perdendo | direcoes opostas tendem a hedge |
| AUDJPY | AUDSGD | 0.7748 | BUY+BUY acumula risco se um estiver perdendo; SELL+SELL acumula risco se um estiver perdendo | direcoes opostas tendem a hedge |
| AUDJPY | CADJPY | 0.7672 | BUY+BUY acumula risco se um estiver perdendo; SELL+SELL acumula risco se um estiver perdendo | direcoes opostas tendem a hedge |
| EURNZD | GBPNZD | 0.7560 | BUY+BUY acumula risco se um estiver perdendo; SELL+SELL acumula risco se um estiver perdendo | direcoes opostas tendem a hedge |
| AUDJPY | EURAUD | -0.7469 | BUY+SELL acumula risco se um estiver perdendo; SELL+BUY acumula risco se um estiver perdendo | mesma direcao tende a hedge |
| EURNZD | NZDSGD | -0.7450 | BUY+SELL acumula risco se um estiver perdendo; SELL+BUY acumula risco se um estiver perdendo | mesma direcao tende a hedge |
| CADCHF | USDCHF | 0.7433 | BUY+BUY acumula risco se um estiver perdendo; SELL+SELL acumula risco se um estiver perdendo | direcoes opostas tendem a hedge |
| AUDCHF | AUDJPY | 0.7408 | BUY+BUY acumula risco se um estiver perdendo; SELL+SELL acumula risco se um estiver perdendo | direcoes opostas tendem a hedge |
| EURUSD | GBPUSD | 0.7397 | BUY+BUY acumula risco se um estiver perdendo; SELL+SELL acumula risco se um estiver perdendo | direcoes opostas tendem a hedge |
| AUDUSD | EURAUD | -0.7389 | BUY+SELL acumula risco se um estiver perdendo; SELL+BUY acumula risco se um estiver perdendo | mesma direcao tende a hedge |
| AUDCAD | EURAUD | -0.7374 | BUY+SELL acumula risco se um estiver perdendo; SELL+BUY acumula risco se um estiver perdendo | mesma direcao tende a hedge |
| EURNZD | NZDCHF | -0.7351 | BUY+SELL acumula risco se um estiver perdendo; SELL+BUY acumula risco se um estiver perdendo | mesma direcao tende a hedge |
| GBPCAD | GBPUSD | 0.7307 | BUY+BUY acumula risco se um estiver perdendo; SELL+SELL acumula risco se um estiver perdendo | direcoes opostas tendem a hedge |
| GBPAUD | GBPNZD | 0.7303 | BUY+BUY acumula risco se um estiver perdendo; SELL+SELL acumula risco se um estiver perdendo | direcoes opostas tendem a hedge |
| CADJPY | NZDJPY | 0.7302 | BUY+BUY acumula risco se um estiver perdendo; SELL+SELL acumula risco se um estiver perdendo | direcoes opostas tendem a hedge |
| NZDCHF | NZDSGD | 0.7235 | BUY+BUY acumula risco se um estiver perdendo; SELL+SELL acumula risco se um estiver perdendo | direcoes opostas tendem a hedge |
| EURAUD | EURNZD | 0.7183 | BUY+BUY acumula risco se um estiver perdendo; SELL+SELL acumula risco se um estiver perdendo | direcoes opostas tendem a hedge |
| CADJPY | GBPJPY | 0.7167 | BUY+BUY acumula risco se um estiver perdendo; SELL+SELL acumula risco se um estiver perdendo | direcoes opostas tendem a hedge |
| NZDJPY | NZDSGD | 0.7104 | BUY+BUY acumula risco se um estiver perdendo; SELL+SELL acumula risco se um estiver perdendo | direcoes opostas tendem a hedge |
| EURNZD | NZDUSD | -0.7102 | BUY+SELL acumula risco se um estiver perdendo; SELL+BUY acumula risco se um estiver perdendo | mesma direcao tende a hedge |
| AUDSGD | NZDSGD | 0.7097 | BUY+BUY acumula risco se um estiver perdendo; SELL+SELL acumula risco se um estiver perdendo | direcoes opostas tendem a hedge |
| AUDSGD | GBPAUD | -0.7038 | BUY+SELL acumula risco se um estiver perdendo; SELL+BUY acumula risco se um estiver perdendo | mesma direcao tende a hedge |