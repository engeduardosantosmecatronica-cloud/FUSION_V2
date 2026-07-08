# Roadmap: Dashboard Como Plataforma De Negociação Read-Only

## Objetivo

Evoluir o dashboard externo do FUSION para uma plataforma operacional de análise, no estilo terminal de negociação/TradingView, sem botões de execução manual.

O dashboard deve mostrar:

- estado atual do mercado por ativo;
- sinais, bloqueios e alertas;
- candles com indicadores principais;
- ordens/posições abertas no gráfico;
- diagnóstico das engines;
- exposição e risco;
- replay histórico para backtest e auditoria.

## Inspirações Em `repositorio/`

### `lightweight-charts-master`

Principal inspiração visual para gráficos:

- candles limpos;
- marcadores no gráfico;
- linhas de preço;
- overlays para ordens, stops e take profits;
- boa aparência de plataforma.

Uso provável: futura tela HTML/React ou componente customizado no Streamlit.

### `finplot-master`

Útil como referência para:

- gráficos financeiros rápidos;
- overlays técnicos;
- marcações de trades;
- replay visual local.

Uso provável: referência de UX e lógica, não necessariamente dependência principal.

### `vnpy-master`

Referência arquitetural:

- watchlist;
- contratos;
- ordens;
- trades;
- posições;
- event-driven UI.

Uso provável: organização de abas e estado operacional.

### `freqtrade-develop`, `vectorbt-master`, `backtrader-master`, `Lean-master`

Referência para:

- backtest;
- replay;
- análise de performance;
- relatórios por trade;
- separação entre dados, estratégia e execução.

Uso provável: fase de replay/backtest, não primeira entrega visual.

### `example-app-crypto-dashboard-main` e `fx_analytics-main`

Referência leve para:

- layout Streamlit;
- cards;
- filtros;
- visualizações tabulares.

Uso provável: melhorias incrementais no dashboard atual.

## Princípios De Produto

- Read-only: não executar ordens pelo dashboard.
- Visual limpo: evitar tabelas largas como fonte principal.
- Informação progressiva: primeiro resumo, depois detalhe ao clicar.
- Cada ativo precisa ter uma tela própria.
- Sinais e alertas devem ser visíveis sem arrastar tela.
- Gráfico deve ser o centro da experiência.
- Logs brutos ficam escondidos em abas de auditoria.

## Fase 1 - Layout De Plataforma

Criar uma tela principal com:

- barra superior com status do robô, conta, Event Bus, AutoTrading, sessão e último evento;
- sidebar/watchlist com ativos, sinal atual, alerta e exposição;
- área central com gráfico do ativo selecionado;
- painel direito com sinais, posições, risco e motivos;
- painel inferior com timeline de eventos.

Entregável:

- reorganizar a aba `Terminal` atual;
- reduzir dependência de tabelas largas;
- manter dados brutos em expansores.

## Fase 2 - Gráfico De Candles Operacional

Melhorar o gráfico atual com:

- candles por timeframe;
- EMA 9/21/50;
- markers de BUY/SELL;
- markers de bloqueio importante;
- linhas de preço atual;
- linhas de entrada, SL e TP quando houver posição;
- faixa visual de risco/retorno.

Entregável:

- função única para montar dados OHLCV + eventos;
- gráfico com overlays de posição;
- fallback limpo quando não houver OHLCV.

## Fase 3 - Ordens E Posições No Gráfico

Usar OMS/Event Bus para mostrar:

- posições abertas por ativo;
- preço de entrada;
- lucro/prejuízo;
- SL/TP;
- trailing se disponível;
- histórico recente de trades.

Entregável:

- camada visual `PositionOverlay`;
- card de posição no painel direito;
- eventos `ORDER_REQUEST`, `ORDER_RESULT`, `TRADE_UPDATE`, `POSITION_UPDATE` conectados ao ativo.

## Fase 4 - Sinais E Alertas

Separar visualmente:

- sinal do modelo;
- bloqueio por filtro;
- alerta de risco;
- alerta de correlação;
- alerta de macro fluxo;
- alerta de execução.

Entregável:

- cards verticais de alertas;
- severidade: info, warning, danger, success;
- filtro por tipo de alerta.

## Fase 5 - Painel Do Ativo

Para cada ativo selecionado:

- consenso dos timeframes;
- engines alinhadas/conflitantes;
- regime atual;
- volatilidade;
- macro fluxo;
- correlação;
- exposição de carteira;
- últimas decisões.

Entregável:

- tela de ativo sem tabelas largas;
- métricas em cards e listas compactas.

## Fase 6 - Replay Histórico

Criar replay read-only:

- selecionar data;
- selecionar ativo;
- navegar evento a evento;
- reconstruir candles + decisões;
- mostrar por que abriu/bloqueou;
- comparar resultado posterior.

Entregável:

- primeira versão usando Event Bus JSONL;
- sem motor de backtest ainda;
- foco em auditoria visual.

## Fase 7 - Backtest Visual

Depois do replay:

- carregar trades simulados;
- plotar entradas/saídas;
- curva de capital;
- drawdown;
- métricas por ativo/timeframe/estratégia;
- comparação entre versões de filtro.

Entregável:

- relatório visual integrado ao dashboard.

## Próximo Passo

Começar pela Fase 1 e Fase 2 em Streamlit:

1. criar um modelo visual mais parecido com plataforma;
2. melhorar gráfico de candles atual;
3. mostrar posição aberta no gráfico usando OMS snapshot;
4. transformar motivos em cards compactos;
5. deixar tabelas brutas apenas como auditoria.

## Status Atual

Implementado nesta etapa:

- checkpoint do roadmap event-driven registrado em `docs/roadmap_event_driven_fusion_v2.md`;
- roadmap específico do dashboard/plataforma criado;
- gráfico de candles recebe overlays de posição aberta via OMS snapshot;
- painel direito mostra cards de posição aberta do ativo selecionado;
- watchlist mostra quantidade de posições e PnL aberto por ativo;
- métricas superiores mostram posições abertas e PnL aberto total.
- alertas visuais para `SIGNAL` e movimentação de trailing;
- alerta sonoro opcional no dashboard com cooldown configurável;
- eventos recentes passam a classificar trailing como tipo próprio quando aparecer `[TRAILING BUY/SELL] ... Novo SL`.
- primeiro `Fusion Terminal Desktop` em modo monitor criado em `terminal_desktop/fusion_terminal_desktop.py`;
- script de abertura do terminal desktop criado em `terminal_desktop/run_terminal_desktop.ps1`;
- terminal desktop lê Event Bus e OMS sem controlar o robô.
- integração visual inspirada no `Fusion_ProfitDesk` aplicada ao Terminal Desktop:
  - barra superior de menus/ferramentas;
  - ribbon horizontal de ativos;
  - watchlist lateral com sinal, alertas, posições e PnL;
  - gráfico central de candles por ativo/timeframe usando OHLC CSV local;
  - linhas de posição aberta no gráfico usando OMS;
  - painel direito do ativo com probabilidades por timeframe, posições e resumo;
  - abas inferiores para sinais/decisões, engines e auditoria;
  - alertas visuais e sonoros para eventos relevantes.
- gráfico do Terminal Desktop agora inclui:
  - EMA 9/21/50;
  - marcadores de `SIGNAL`, `DECISION`/bloqueio e `ORDER_RESULT`;
  - suporte visual para linhas de SL, TP e trailing quando esses campos existirem no OMS/Event Bus;
  - aba Engines lendo o formato real do `ENGINE_RESULT` emitido pelo Event Bus.

Próximo foco:

- validar visualmente o Terminal Desktop durante sessão real;
- transformar alertas/motivos em cards com severidade;
- mostrar SL/TP/trailing no gráfico quando esses campos existirem no OMS/Event Bus;
- preparar primeira tela de replay visual baseada no Event Bus.
