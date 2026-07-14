# Fusion Terminal Windows

Primeira etapa da nova plataforma desktop nativa do FUSION.

## Objetivo desta fase

- Janela Windows nativa em C#/.NET.
- Grafico de candles customizado.
- Zoom com roda do mouse.
- Pan arrastando o grafico.
- Crosshair com OHLC.
- Leitura dos CSVs do Fusion em `data/csv/{timeframe}/{ano}/{mes}/{symbol}.csv`.

## Como executar

Instale o .NET SDK 10 ou superior e rode:

```powershell
.\terminal_windows\run_terminal_windows.ps1
```

O Terminal Windows inicia a ponte Python com o MT5 em segundo plano. O launcher PowerShell nao inicia outra ponte por padrao, para evitar duplicidade:

```powershell
tools\export_mt5_candles_for_terminal.py --interval 1
```

Essa ponte atualiza `runtime/market_data/latest_candles/*.json`, e o terminal mistura:

- historico local em `data/csv/{timeframe}/...`;
- candles live vindos do MT5.

Para forcar o launcher PowerShell a iniciar a ponte separadamente durante testes:

```powershell
.\terminal_windows\run_terminal_windows.ps1 -StartMt5Bridge -BridgeSymbols "AUDUSD,EURUSD,GOLD" -BridgeTimeframes "M5,M15"
```

## Proximas etapas

1. Plotar zonas de entrada, TP, SL, suporte e resistencia no grafico.
2. Melhorar cards de leitura operacional por severidade.
3. Expandir linhas de ordens/SL/TP/trailing.
4. Expandir o Backtest visual com replay passo a passo e comparacao entre estrategias.

## Backtest visual

A aba `Backtest` carrega por padrao:

```text
reports/strategy_bank_backtests/strategy_bank_backtest_trades.csv
```

Recursos atuais:

- filtro por ativo/timeframe atual;
- filtro por estrategia;
- filtro por resultado;
- filtro por periodo;
- resumo de performance;
- curva de patrimonio;
- tabela de operacoes;
- desenho de entradas, saidas, TP e SL no grafico.

## Matriz operacional

A aba `Matriz Operacional` replica a leitura do dashboard de console do FUSION em formato visual:

- ativos nas linhas;
- timeframes nas colunas;
- `B:score` para BUY;
- `S:score` para SELL;
- `p_buy/p_sell` para leituras neutras;
- cor por direcao e estado de decisao;
- tooltip com estrategia e motivo completo;
- resumo inferior dos principais motivos de bloqueio/acao.

Fonte padrao:

```text
reports/shadow_engine_report/shadow_engine_events_*.csv
```

