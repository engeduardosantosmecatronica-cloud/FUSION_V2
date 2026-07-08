# Ciclo Operacional do Fusion V2

Este documento descreve o fluxo completo do Fusion V2, desde a inicializacao ate o fechamento de uma ordem.

## 1. Componentes principais

O Fusion trabalha em arquitetura hibrida:

- Python/Fusion: cerebro quantitativo, modelos, filtros, matriz operacional, execucao e gestao.
- MT5/FusionMt5Bridge EA: ponte de dados, controle operacional rapido e publicacao do modo MANUAL/AUTOMATIC.
- MT5/FusionSignalPanel indicador: legenda, sinal FINAL, alertas, confirmacao manual, seta, zonas de entrada, SL e TP.
- Arquivos CSV/JSON em Common Files: comunicacao entre Python e MT5.

## 2. Inicializacao do Fusion

Quando `run_fusion.py` inicia o sistema, o Fusion executa a inicializacao principal:

1. Carrega `config/fusion_config.yaml`.
2. Inicializa logger, event bus, OMS, trailing manager, registry de engines e executor de ordens.
3. Inicializa a conexao com o MT5 via biblioteca `MetaTrader5`.
4. Carrega modelos por ativo/timeframe.
5. Carrega modelos aprovados/ensembles, quando habilitados.
6. Sincroniza simbolos da corretora com os ativos logicos do Fusion.
7. Atualiza o snapshot inicial do OMS com posicoes e historico recente.
8. Executa a rotina da matriz operacional, quando habilitada.

## 3. Matriz operacional diaria

Antes de operar, o Fusion pode atualizar a matriz operacional:

1. Verifica se `operational_target_matrix.update_on_startup` esta ativo.
2. Verifica se a matriz do dia ja existe.
3. Se necessario, baixa historico recente do MT5.
4. Testa movimentos por ativo e direcao.
5. Calcula estatisticas como:
   - movimento limpo a favor;
   - drawdown antes de recuperar;
   - movimento depois da recuperacao;
   - MFE/MAE liquido;
   - spread;
   - alvo e stop candidatos;
   - sequencias de perdas.
6. Salva `reports/operational_target_matrix/operational_target_matrix_latest.json`.

Essa matriz nao substitui o modelo. Ela atua como filtro de qualidade e referencia operacional para alvo/stop/drawdown.

## 4. Inicializacao do MT5

No MT5 normalmente rodam dois elementos:

1. `FusionMt5Bridge.mq5` como EA.
2. `FusionSignalPanel.mq5` como indicador.

A EA `FusionMt5Bridge`:

1. Conecta ao servidor TCP local do Fusion.
2. Envia ticks/candles conforme solicitado.
3. Descobre ativos monitorados pelos CSVs `fusion_signal_panel_*.csv`.
4. Publica controle operacional em `fusion_execution_control.csv`.

O indicador `FusionSignalPanel`:

1. Le `fusion_signal_panel_<ATIVO>.csv`.
2. Mostra sinais por timeframe e linha `FINAL`.
3. Mostra seta de entrada do `FINAL`.
4. Le `fusion_trade_zones_<ATIVO>.csv`.
5. Desenha zonas de entrada, SL e TP.
6. Dispara alertas.
7. Em modo manual, exibe a confirmacao de ordem.

## 5. Controle operacional pela EA

O controle rapido fica na EA do MT5:

- `InpAllowFusionOrders`
- `InpFusionExecutionMode`

A EA grava `fusion_execution_control.csv`.

O Fusion le esse arquivo em tempo real:

- se `InpAllowFusionOrders = false`, nenhuma nova ordem e enviada;
- se `InpAllowFusionOrders = true` e modo `MANUAL`, o Fusion pede confirmacao no MT5;
- se `InpAllowFusionOrders = true` e modo `AUTOMATIC`, o Fusion envia a ordem apos todos os filtros.

O YAML fica apenas como fallback se a EA nao estiver publicando controle valido.

## 6. Loop principal de sinais

O loop `_run_signals()` roda por minuto.

Em cada ciclo:

1. Recarrega a configuracao.
2. Recria exporters do painel, zonas e camadas de decisao.
3. Atualiza o OMS com posicoes e historico recente.
4. Zera estados acionaveis do ciclo.
5. Percorre cada ativo e cada timeframe.

Para cada ativo/timeframe:

1. Verifica se ha modelo runtime ou modelo aprovado.
2. Calcula features a partir do historico do MT5.
3. Executa o modelo.
4. Gera probabilidades `p_buy` e `p_sell`.
5. Converte probabilidades em predicao:
   - `1` = BUY;
   - `2` = SELL;
   - `0` = WAIT.

## 7. Inversoes e overrides

Apos o modelo gerar o sinal bruto:

1. Aplica inversoes configuradas em `signal.inverted_signal_groups`.
2. Aplica overrides pontuais em `signal_overrides`.
3. Mantem rastreabilidade do sinal bruto em `raw_signal`, `raw_p_buy`, `raw_p_sell` e `raw_reason`.

Isso permite ver o que o modelo original disse e o que foi alterado por calibracao operacional.

## 8. Estrategias

O Fusion avalia varias estrategias registradas em `strategy_runners`.

Cada estrategia recebe:

- ativo;
- timeframe;
- predicao;
- probabilidades;
- modelo;
- features;
- horario atual;
- contexto aprovado.

A estrategia decide se tenta executar ou se fica aguardando setup.

Mesmo que varios timeframes apontem a mesma direcao, existe trava para evitar multiplas ordens por ativo no mesmo ciclo.

## 9. Camadas de filtro antes da ordem

Antes de chamar `order_send`, o Fusion passa por varias camadas.

Entre elas:

1. `trading.allow_new_orders` ou controle da EA.
2. Verificacao se o MT5 permite trade.
3. Qualidade do meta-model/ensemble.
4. Briefing macro do dia.
5. Regime de mercado.
6. Volatilidade.
7. Sessao/horario.
8. Macro flow.
9. Alinhamento de mercado.
10. Consenso multi-timeframe.
11. Exposicao de portfolio.
12. Correlacao com posicoes abertas.
13. Estrutura de mercado.
14. Feature engineering.
15. Timing de entrada.
16. Execution engine.
17. Risk engine.
18. Confirmacao por candle.
19. Alinhamento de EMAs.
20. Context engine.
21. Calibracao de confianca.
22. Consensus engine.
23. Opportunity engine.
24. Context brain.
25. AI advisor, quando ativo.
26. Floating loss guard.

Se qualquer camada em modo `block` reprovar, a ordem nao e enviada.

## 10. Sinal refinado para painel

O sinal que aparece no MT5 nao e apenas o sinal cru do modelo.

O Fusion monta um estado refinado para o painel:

1. Usa sinal apos inversoes e overrides.
2. Anota o motivo bruto.
3. Consulta a matriz operacional.
4. Marca amostra baixa, falta de plano de alvo/stop ou lado nao recomendado.
5. Mantem BUY/SELL visivel quando a matriz ainda nao tem amostra suficiente.
6. Pode transformar em WAIT quando houver evidencia operacional forte contra o sinal.

Esse estado e exportado para `fusion_signal_panel_<ATIVO>.csv`.

## 11. Sinal FINAL por ativo

O Fusion calcula um `FINAL` por ativo.

Esse `FINAL` e o consenso ponderado dos timeframes:

- M5;
- M15;
- M30;
- H1;
- H4;
- D1.

Os pesos vem de `entry_filters.timeframe_consensus.timeframe_weights`.

O calculo considera:

1. sinais BUY;
2. sinais SELL;
3. sinais WAIT;
4. probabilidade relativa entre `p_buy` e `p_sell`;
5. quantidade minima de timeframes validos;
6. score minimo de consenso.

Resultado:

- `FINAL BUY`;
- `FINAL SELL`;
- `FINAL WAIT`.

O indicador do MT5 usa o `FINAL` como prioridade para alerta e seta. Se `FINAL = WAIT`, nao deve alertar ordem.

## 12. Exportacao para MT5

Apos calcular os sinais, o Fusion exporta:

1. `fusion_signal_panel_<ATIVO>.csv`
   - sinais por timeframe;
   - probabilidades;
   - motivos;
   - linha `FINAL`.

2. `fusion_trade_zones_<ATIVO>.csv`
   - suporte;
   - resistencia;
   - zona de entrada;
   - zona de SL;
   - zona de TP.

3. `fusion_decision_layers_<ATIVO>.csv`
   - diagnostico das camadas de decisao.

4. Relatorios de forca relativa de moedas.

O MT5 le esses arquivos via `Common Files`.

## 13. Visualizacao no MT5

O `FusionSignalPanel` faz:

1. Le o CSV de sinais.
2. Mostra a legenda no grafico.
3. Mostra a linha `FINAL`.
4. Desenha uma seta para `FINAL BUY` ou `FINAL SELL`.
5. Le o CSV de zonas.
6. Desenha entrada, SL e TP.
7. Pode desenhar suporte/resistencia se habilitado.
8. Gera alerta apenas pelo `FINAL`.
9. Deduplica alertas iguais entre varias instancias do indicador.

## 14. Modo manual

Quando a EA esta em modo manual:

1. O Fusion passa por todos os filtros.
2. Antes de enviar a ordem, grava `fusion_manual_order_request.csv`.
3. O `FusionSignalPanel` detecta o pedido.
4. O MT5 mostra uma pergunta de confirmacao.
5. Se o usuario aprovar, o indicador grava `fusion_manual_order_response.csv`.
6. O Fusion le a resposta.
7. Se aprovado dentro do timeout, envia a ordem.
8. Se rejeitado ou expirar, bloqueia a ordem.

## 15. Modo automatico

Quando a EA esta em modo automatico:

1. O Fusion passa por todos os filtros.
2. Se o sinal for aprovado, chama o executor.
3. O executor calcula lote, SL, TP e magic.
4. Envia a ordem para o MT5 via `mt5.order_send`.
5. Atualiza OMS, eventos e logs.

## 16. Execucao da ordem

Na execucao:

1. O Fusion cria um `order_correlation_id`.
2. Registra evento de decisao `ALLOW`.
3. Cria uma ordem pendente no OMS.
4. Publica `ORDER_REQUEST`.
5. Chama:
   - `execute_buy_strategy`, ou
   - `execute_sell_strategy`.
6. O executor verifica limite de posicoes:
   - por ativo;
   - por direcao;
   - por magic;
   - por sistema inteiro, quando configurado.
7. Monta o request MT5.
8. Envia `mt5.order_send`.
9. Se executou, marca como `FILLED`.
10. Se falhou, marca como `FAILED` ou `REJECTED`.
11. Publica `ORDER_RESULT`.

## 17. Controle de uma ordem por ativo

Hoje ha duas protecoes principais:

1. Configuracao:
   - `trading.position_limits.enabled`;
   - `scope: system`;
   - `max_per_symbol: 1`;
   - `mode: any_direction`.

2. Trava de ciclo:
   - se um ativo ja teve ordem executada no ciclo atual, outros timeframes do mesmo ativo nao tentam abrir nova ordem.

Assim, se M15, M30 e H1 concordarem, isso deve gerar no maximo uma ordem por ativo.

## 18. OMS e eventos

O OMS mantem estado operacional:

- ordens pendentes;
- ordens preenchidas;
- ordens falhas;
- posicoes abertas;
- historico recente;
- snapshots.

O Event Bus registra eventos como:

- sinal detectado;
- ordem solicitada;
- ordem executada;
- posicao atualizada;
- trade historico.

Esses registros servem para auditoria e depuracao.

## 19. Gestao da posicao aberta

Depois que a ordem abre:

1. O MT5 controla TP e SL nativos enviados na ordem.
2. O Fusion atualiza snapshots do OMS.
3. O trailing manager roda em thread separada.
4. O trailing monitora posicoes com magics do Fusion.
5. Quando o lucro em pontos atinge a ativacao, ele ajusta o SL.
6. Para BUY, o SL sobe junto com o preco.
7. Para SELL, o SL desce junto com o preco.

O trailing usa:

- presets otimizados por ativo/timeframe, quando existem;
- fallback padrao por ativo;
- fallback geral.

## 20. Fechamento da ordem

A ordem pode fechar por:

1. TP nativo no MT5.
2. SL nativo no MT5.
3. SL movido pelo trailing.
4. Fechamento manual no MT5.
5. Rotina de fechamento por simbolo, se chamada.
6. Intervencao externa.

Quando uma posicao fecha:

1. O Fusion detecta pelo historico de deals.
2. Atualiza OMS.
3. Registra evento de trade.
4. Aplica cooldown de reentrada se configurado.
5. A posicao passa a influenciar relatorios, matriz futura e filtros de risco.

## 21. Cooldown depois do fechamento

O Fusion consulta o historico recente do MT5.

Se uma ordem acabou de fechar, pode bloquear nova entrada no mesmo ativo/timeframe por alguns segundos.

Isso evita reentrada imediata apos stop, alvo ou fechamento manual.

## 22. Resumo do fluxo completo

Fluxo simplificado:

1. Fusion inicia.
2. Carrega config, modelos, MT5, OMS e matriz.
3. EA MT5 publica controle operacional.
4. Fusion le ativos e timeframes.
5. Modelos geram BUY/SELL/WAIT.
6. Inversoes e overrides ajustam o sinal.
7. Estrategias avaliam setup.
8. Filtros institucionais aprovam ou bloqueiam.
9. Fusion calcula sinal refinado e `FINAL`.
10. Exporta CSVs para MT5.
11. Indicador mostra legenda, seta, entrada, SL e TP.
12. Se houver ordem candidata:
    - em manual, pede aprovacao no MT5;
    - em automatico, envia direto.
13. Executor envia ordem ao MT5.
14. OMS registra resultado.
15. Trailing acompanha posicao.
16. Ordem fecha por TP, SL, trailing, manual ou rotina externa.
17. Fusion registra fechamento e aplica cooldown.

## 23. Pontos importantes

- O alerta no MT5 nao significa necessariamente ordem aberta.
- O `FINAL` e o sinal operacional principal para visualizacao e alerta.
- A ordem so abre se passar por filtros e se a EA permitir.
- A EA controla rapidamente MANUAL/AUTOMATIC sem reiniciar o Fusion.
- O Python continua sendo o cerebro quantitativo.
- O MT5 continua sendo a camada de execucao, visualizacao e controle rapido.
