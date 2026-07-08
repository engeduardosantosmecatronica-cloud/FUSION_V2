# Comunicacao MT5, Backend e Frontend

Este documento registra como a comunicacao entre o MT5, o backend do FUSION e o frontend esta funcionando hoje.

## Visao geral

O fluxo atual de dados para candles e ticks e este:

```text
MT5
  -> tools/mt5_live_api.py
  -> HTTP REST em http://127.0.0.1:5000
  -> fusion-frontend/src/lib/mt5Api.js
  -> trading / chart UI no frontend
```

Esse caminho substitui a dependencia do antigo bridge por socket para exibicao de candles e ticks no grafico.

## Estado atual

### Fluxo ativo

- O MT5 e lido diretamente pela API Python usando o pacote `MetaTrader5`.
- O backend expoe endpoints HTTP para o frontend consumir.
- O frontend busca candles historicos e estado ao vivo por REST.
- O grafico de candles usa esses dados para renderizar OHLC e tick atual.

### Fluxo legado

- O `FusionMt5Bridge.mq5` continua existindo no projeto.
- Ele era usado no fluxo de socket antigo.
- Para o uso atual de candles e ticks no grafico, ele nao e mais necessario.
- Se estiver anexado ao terminal, pode continuar gerando logs de conexao sem agregar valor ao fluxo atual.

## Arquivos principais

### Backend / API MT5

- [`tools/mt5_live_api.py`](../tools/mt5_live_api.py)
- [`config/fusion_config.yaml`](../config/fusion_config.yaml)
- [`fusion_refatorado/models/production_registry/M5_approved_ensembles.json`](../fusion_refatorado/models/production_registry/M5_approved_ensembles.json)
- [`fusion_refatorado/models/fusion_ensemble/*.json`](../fusion_refatorado/models/fusion_ensemble)

### Frontend

- [`fusion-frontend/src/lib/mt5Api.js`](../fusion-frontend/src/lib/mt5Api.js)
- [`fusion-frontend/src/pages/Trading.jsx`](../fusion-frontend/src/pages/Trading.jsx)
- [`fusion-frontend/.env.local`](../fusion-frontend/.env.local)

### Fluxo legado do MT5

- [`mql5/Experts/FusionMt5Bridge.mq5`](../mql5/Experts/FusionMt5Bridge.mq5)

## Como os dados chegam

### 1. MT5 -> backend

O backend `tools/mt5_live_api.py` conecta no terminal MT5 via `MetaTrader5.initialize()` e consulta:

- `copy_rates_from_pos()` para candles
- `symbol_info_tick()` para tick atual

O backend normaliza:

- simbolo
- timeframe
- OHLC
- volume
- timestamp

### 2. Backend -> API

O backend expoe estes endpoints:

- `GET /api/health`
- `POST /api/stream`
- `GET /api/candles?symbol=EURUSD&tf=H1&limit=200`
- `GET /api/live?symbol=EURUSD&tf=H1`

### 3. API -> frontend

O frontend consome os dados por `fetch` em:

- [`fusion-frontend/src/lib/mt5Api.js`](../fusion-frontend/src/lib/mt5Api.js)

Funcoes principais:

- `setMt5Stream(symbol, timeframe, limit)`
- `fetchMt5Candles(symbol, timeframe, limit)`
- `fetchMt5LiveState(symbol, timeframe)`

### 4. Frontend -> grafico

Em `Trading.jsx`, o fluxo faz:

- pedir candles ao backend
- manter buffer local
- atualizar o candle atual com o tick vivo
- renderizar o grafico em `CandleChart`

## Formato dos dados

### Candle

Exemplo de payload:

```json
{
  "symbol": "EURUSD",
  "timeframe": "H1",
  "time": "2026-06-10 15:00:00",
  "open": 1.15515,
  "high": 1.15546,
  "low": 1.15464,
  "close": 1.15491,
  "volume": 1515,
  "source": "mt5_direct"
}
```

### Live state

O endpoint de live retorna:

- `tick`
- `current_candle`
- `live_count`
- `source`

## Ordem recomendada de subida

1. Abrir o MT5
2. Subir o backend `tools/mt5_live_api.py`
3. Subir o Fusion
4. Abrir o frontend

## Validacao rapida

Se estiver tudo certo:

- `GET /api/health` responde `ok`
- `GET /api/candles` retorna candles reais do MT5
- `GET /api/live` retorna tick atual
- o grafico mostra candles sem depender do socket antigo

## Observacao importante

Se o objetivo for apenas grafico + leitura operacional de mercado, o `FusionMt5Bridge.mq5` pode ficar desativado.

Se o objetivo voltar a ser integracao por socket ou execucao via EA, o bridge legado pode ser reativado em outra etapa.
