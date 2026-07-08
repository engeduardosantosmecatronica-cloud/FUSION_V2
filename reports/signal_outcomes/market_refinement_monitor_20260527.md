# Monitoramento de Refinamento - 2026-05-27

Objetivo: acompanhar os ativos em que a previsao do Fusion diverge do fluxo atual do mercado e separar o que deve ser evitado, observado ou refinado.

Contexto atual usado como base:
- NZD forte.
- AUD forte no intraday, mas misto em alguns cruzamentos.
- EUR fraco/inconsistente.
- JPY estruturalmente fraco.
- Mercado parcialmente risk-on.
- USD sustentado/recuperando no curto prazo.
- Criptos com tendencia maior bullish, apesar de pullback curto.

## Bloquear Temporariamente / Evitar

| Ativo | Motivo | Acao no sistema |
|---|---|---|
| AUDSEK | Fusion BUY M15, mercado SELL amplo; AUD enfraquecendo contra SEK | Inverter M15 para teste |
| EURJPY | Fluxo atual SELL apesar de JPY fraco; EUR mais fraco que JPY no par | Desabilitada inversao H1 antiga; manter H4 invertido por historico |
| EURMXN | MXN muito forte; Fusion BUY H1 contra fluxo | Inverter H1 para teste |
| EURNZD | NZD dominante; mercado FORTE SELL | Inverter H4 para teste; H1 ja precisa observacao porque Fusion pos-inversao esta SELL |
| EURSEK | SEK fortalecendo; Fusion BUY H1/H4 contra curto prazo | Inverter H1/H4 para teste |
| NZDCAD | NZD forte; mercado BUY total contra Fusion H4 SELL | Inverter H4 para teste |
| NZDCHF | Reversao de fluxo para BUY total | Inverter H1/H4; desabilitar eventual inversao que gere SELL se aparecer conflito |
| NZDSGD | NZD ganhou forca; mercado BUY total | Inverter H1/H4 para teste |

## Manter Observando

| Ativo | Motivo | Acao |
|---|---|---|
| AUDUSD | BUY curto e SELL estrutural; pode ser pullback dentro de estrutura maior | Observar coerencia M30/H1 contra H4/D1 |
| EURCAD | H1/H4 BUY no Fusion, mas curto prazo SELL por CAD forte | Observar; nao inverter ainda |
| EURCHF | Mercado SELL alinhado; Fusion H1 BUY/H4 SELL | Inverter H1 para teste e observar H4 |
| EURGBP | Par em chop/neutro; sinais conflitantes | Evitar novos sinais sem alinhamento M30/H1/H4 |
| EURNOK | NOK fortalecendo no curto prazo; Fusion misto | Observar; sem inversao nova por enquanto |
| EURPLN | EUR perdeu forca; Fusion misto | Observar; sem inversao nova por enquanto |
| GBPCHF | CHF perdeu momentum; inversoes antigas foram desabilitadas | Observar se H1 BUY ganha continuidade |
| GBPJPY | JPY muito fraco; sinais baixos SELL podem ser pullback | Observar; nao inverter H1/H4 |
| NZDUSD | Mercado BUY alinhado; H1 SELL parecia ruido | Desabilitada inversao H1 antiga; manter M30 invertido por teste curto |
| USDCHF | USD recuperando; Fusion misto | Observar; nao inverter ainda |

## Mais Alinhados / Refinar Coerencia

| Ativo | Leitura | Refinamento desejado |
|---|---|---|
| BTCUSD | Estrutura bullish confirmada | Evitar SELL intraday se H4/D1 continuarem BUY |
| ETHUSD | H4 forte BUY | Priorizar BUY quando H1/H4 alinharem |
| GBPAUD | SELL alinhado | Evitar BUY intraday contra H4/D1 |
| GBPCAD | SELL alinhado | Confirmar CAD forte antes de novos sinais |
| NZDJPY | Forte BUY | Evitar SELL em timeframes baixos contra H4 |
| USDJPY | Forte BUY | Evitar SELL em M15/M30 contra H1/H4 |
| EURUSD | BUY curto / SELL estrutural | Tratar BUY curto como pullback se H4 seguir SELL |

## Mudancas Aplicadas em 2026-05-27

Nota importante: a tabela do dashboard usada nesta revisao ja continha sinais pos-inversao. Portanto, quando uma previsao final estava desalinhada, a correcao pode ser desabilitar uma inversao antiga, e nao inverter novamente.

Desabilitadas inversoes antigas que estavam gerando divergencia pos-inversao:
- AUDCHF M30/H4.
- AUDSGD H4.
- EURAUD M30/H1.
- EURJPY H1.
- GBPCHF H1.
- EURSEK H4.

Mantidas inversoes onde ainda ha justificativa historica ou estrutural:
- EURAUD H4.
- EURJPY H4.
- NZDUSD M30.
- NZDUSD H1.
- GBPCHF M15/M30.
- Outros grupos historicos do relatorio 2026-05-21 a 2026-05-26 que nao foram contraditos pela leitura atual.

Adicionadas novas inversoes para teste:
- AUDSEK M15.
- EURCHF H1.
- EURMXN H1.
- EURNZD H4.
- EURSEK H1/H4.
- NZDCAD H4.
- NZDCHF H1/H4.
- NZDSGD H1/H4.

Adicionadas apos revisar a tabela pos-inversao pre-restart:
- AUS200 M15/H1.
- BTCUSD M30.
- CADCHF H4.
- CADJPY H1.
- EURCAD H1.
- EURCHF M15.
- EURNOK M15/M30/H1.
- EURNZD M30/H1.
- GBPAUD M30.
- GBPJPY M15/M30.
- NZDCAD M30.
- NZDCHF M30.
- NZDUSD H4.
- USDJPY M30.

## Regra de Revisao

Reavaliar apos algumas horas de robo ligado:
- Comparar CSVs do painel MT5 com a leitura de mercado atual.
- Separar resultado por ativo/timeframe.
- Se um grupo invertido continuar divergente, desabilitar a inversao.
- Se um grupo nao invertido continuar divergente com mercado por pelo menos H1/H4, adicionar inversao temporaria.
