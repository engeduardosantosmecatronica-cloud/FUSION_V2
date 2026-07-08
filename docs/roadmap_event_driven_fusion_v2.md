# Roadmap: Arquitetura Event-Driven Leve Para FUSION_V2

## Objetivo

Evoluir o FUSION_V2 para uma arquitetura mais modular, auditável e desacoplada, usando como inspiração os padrões do vn.py, mas sem trazer a complexidade inteira do framework.

O foco desta etapa não é alterar a lógica de entrada imediatamente. O objetivo é criar uma infraestrutura que permita:

- decisões mais rastreáveis;
- dashboard menos dependente de parsing de log;
- auditoria estruturada;
- integração futura com agente IA;
- replay histórico de decisões;
- separação clara entre sinal, decisão, risco, execução e acompanhamento.

## Princípio De Implementação

Tudo deve entrar primeiro em modo paralelo/shadow.

O robô continua funcionando como hoje, mas cada parte importante começa a emitir eventos e objetos padronizados. Depois que os eventos estiverem confiáveis, módulos como dashboard, auditoria e agente IA passam a consumir essa camada.

## Status Atual

Implementado:

- `fusion/core/enums.py`
- `fusion/core/objects.py`
- `fusion/core/events.py`
- `fusion/core/event_logger.py`
- `fusion/core/contracts.py`
- `fusion/core/engine_registry.py`
- `fusion/execution/oms.py`
- `fusion/advisor/`
- `dashboard/event_readers.py`
- `tools/replay_events.py`
- `tools/inspect_order_lifecycle.py`

Integrado ao `FusionV2`:

- publicação de `DECISION`;
- publicação de `ORDER_REQUEST`;
- publicação de `ORDER_RESULT`;
- publicação de `ACCOUNT_UPDATE`;
- publicação de `POSITION_UPDATE`;
- publicação de `DASHBOARD_UPDATE`;
- publicação de `ADVISOR_REQUEST`;
- publicação de `ADVISOR_RESPONSE`;
- publicação de `SIGNAL`;
- publicação individual de `ENGINE_RESULT`;
- registro das engines principais;
- sincronização de contratos dos ativos;
- OMS leve observando conta, posições, ordens e contratos.
- snapshot persistido do OMS em `logs/oms/oms_snapshot_YYYYMMDD.json`;
- aba `Event Bus` no dashboard externo;
- replay por `correlation_id` via `tools/replay_events.py`;
- inspeção do ciclo de ordem via `tools/inspect_order_lifecycle.py`;
- relatório do Event Bus via `tools/build_event_bus_report.py`;
- relatório operacional diário via `tools/build_operational_day_report.py`;
- relatório de performance por `correlation_id` via `tools/analyze_event_performance.py`;
- validação financeira por ticket/order_id via `tools/validate_order_financial_cross.py`;
- validação operacional unificada via `tools/check_operational_readiness.py`;
- backfill de `decision_audit` para eventos via `tools/backfill_events_from_decision_audit.py`;
- replay/reconstrução de estado OMS via `tools/replay_oms_state.py`;
- validação de integridade do Event Bus via `tools/check_event_bus_integrity.py`;
- OMS observando último tick por ativo no snapshot;
- emissão de `TRADE_UPDATE` para deals novos do MT5;
- opção de Event Bus assíncrono com `publish_async`, `start_async` e `stop_async`;
- `stop_async` drenando a fila antes de encerrar;
- smoke test assíncrono via `tools/check_event_bus_async.py`;
- dashboard com opção `Preferir Event Bus como fonte`;
- dashboard externo usando Event Bus como fonte preferencial por padrão;
- painel lateral de saúde no dashboard externo mostrando fonte ativa, async, novas ordens, OMS e último evento;
- `events_to_status_table` normalizado para o formato operacional M5/M15/M30/H1/H4/D1;
- abas `Ativo`, `Decision Audit`, `Heatmaps`, `Risco`, `Engines` e `Eventos Recentes` consumindo Event Bus quando disponível;
- conversão de eventos `DECISION` para frames equivalentes ao `decision_audit`;
- `correlation_id` compartilhado entre `DECISION`, `ORDER_REQUEST` e `ORDER_RESULT` nas ordens permitidas.
- `SIGNAL` e decisões/bloqueios gerados pela mesma rodada passam a compartilhar `correlation_id` do sinal.

Ainda pendente:

- validar cruzamento financeiro por ticket/order_id em sessão real com ordens executadas;
- validar Event Bus assíncrono dentro do robô em sessão real antes de manter ativado.

## Checkpoint Para Retomar

Pausado em: validação operacional final do roadmap event-driven enquanto o robô roda em sessão real.

Estado atual esperado:

- `event_bus.use_async: true`;
- Event Bus emitindo eventos recentes;
- `decision_sem_signal=0` após a correção de `correlation_id`;
- ausência de ordem recente aparece como `INFO` no readiness, não como falha;
- ciclo completo de ordem ainda precisa ser validado quando houver `ORDER_REQUEST` e `ORDER_RESULT`.

Comandos para retomar:

```powershell
.\venv\Scripts\python.exe tools\check_operational_readiness.py --date YYYYMMDD
.\venv\Scripts\python.exe tools\check_operational_readiness.py --date YYYYMMDD --require-order
.\venv\Scripts\python.exe tools\check_event_bus_integrity.py --date YYYYMMDD
.\venv\Scripts\python.exe tools\validate_order_financial_cross.py --date YYYYMMDD
```

## Próxima Validação Em Sessão Real

1. Rodar o robô por pelo menos 30-60 minutos com `event_bus.use_async: true`.
2. Gerar:
   - `python tools/check_operational_readiness.py --date YYYYMMDD`
   - `python tools/check_operational_readiness.py --date YYYYMMDD --require-order` quando houver ordem real no período
   - `python tools/check_event_bus_integrity.py --date YYYYMMDD`
   - `python tools/build_event_bus_report.py --date YYYYMMDD`
   - `python tools/analyze_event_performance.py --date YYYYMMDD`
   - `python tools/replay_oms_state.py --date YYYYMMDD`
3. Conferir se existem:
   - `ORDER_REQUEST` sem `ORDER_RESULT`;
   - `DECISION` sem `ENGINE_RESULT`;
   - `ORDER_RESULT` sem `ORDER_REQUEST`;
   - ausência de `TRADE_UPDATE` após execução real.
4. Se a sessão assíncrona estiver estável, manter `event_bus.use_async: true`; se houver perda de evento, voltar para `false` e investigar fila/handlers.

Observação: sem `--require-order`, ausência de ordem recente aparece como `INFO`, não como falha. Use `--require-order` para validar ciclo completo de ordem.

## Fase 1 - Objetos Padronizados

Criar `fusion/core/objects.py`.

### Objetos iniciais

- `FusionTick`
- `FusionBar`
- `FusionOrder`
- `FusionTrade`
- `FusionPosition`
- `FusionAccount`
- `FusionContract`
- `FusionDecision`
- `FusionSignal`

### Campos principais

`FusionContract`:

- `symbol`
- `broker_symbol`
- `asset_type`
- `digits`
- `point`
- `tick_size`
- `tick_value`
- `min_lot`
- `lot_step`
- `max_lot`
- `spread`
- `currency_profit`

`FusionOrder`:

- `order_id`
- `symbol`
- `broker_symbol`
- `strategy`
- `timeframe`
- `direction`
- `volume`
- `price`
- `sl`
- `tp`
- `status`
- `reason`
- `created_at`
- `updated_at`

`FusionDecision`:

- `symbol`
- `timeframe`
- `strategy`
- `direction`
- `decision`
- `final_action`
- `prob_buy`
- `prob_sell`
- `confidence`
- `reasons`
- `positive_factors`
- `negative_factors`
- `engine_states`

### Resultado esperado

O sistema passa a ter uma linguagem interna única para ordens, posições, decisões e ativos.

## Fase 2 - Modelo De Ciclo Da Ordem

Criar enums em `fusion/core/enums.py`.

### Status de ordem

- `PENDING`
- `SENT`
- `FILLED`
- `PART_FILLED`
- `REJECTED`
- `CANCELLED`
- `FAILED`

### Direções

- `BUY`
- `SELL`
- `NEUTRAL`

### Ações finais

- `ALLOW`
- `BLOCK`
- `SHADOW`
- `MODERATE`
- `REDUCE_SIZE`

### Motivo

Substituir gradualmente mensagens soltas por motivos estruturados.

Exemplo:

```text
reason_code = "macro_fluxo_contra"
reason_state = "macro_contra"
reason_direction = "BUY"
reason_score = 0.450
```

### Resultado esperado

Relatórios e dashboard deixam de depender de textos muito longos como fonte principal de verdade.

## Fase 3 - Event Bus Interno

Criar `fusion/core/events.py`.

### Eventos principais

- `SIGNAL`
- `DECISION`
- `ORDER_REQUEST`
- `ORDER_RESULT`
- `POSITION_UPDATE`
- `ACCOUNT_UPDATE`
- `RISK_ALERT`
- `DASHBOARD_UPDATE`
- `AUDIT_RECORD`
- `ADVISOR_REQUEST`
- `ADVISOR_RESPONSE`

### Estrutura do evento

```python
FusionEvent(
    type="DECISION",
    source="FusionV2",
    timestamp=...,
    correlation_id="...",
    data={...}
)
```

### Recursos mínimos

- `subscribe(event_type, handler)`
- `publish(event)`
- handlers gerais opcionais
- execução síncrona inicialmente
- fila assíncrona apenas em fase posterior

### Resultado esperado

Módulos deixam de chamar uns aos outros diretamente para tudo. O robô publica eventos e consumidores escutam.

## Fase 4 - Logs/Eventos Normalizados

Criar `fusion/core/event_logger.py`.

### Saídas

- `logs/events/events_YYYYMMDD.jsonl`
- `logs/decision_audit/decision_audit_YYYYMMDD.jsonl`
- `logs/order_lifecycle/order_lifecycle_YYYYMMDD.jsonl`

### Cada evento deve carregar

- `event_id`
- `correlation_id`
- `timestamp`
- `symbol`
- `timeframe`
- `strategy`
- `event_type`
- `action`
- `status`
- `reason_codes`
- `payload`

### Resultado esperado

Auditoria, replay, dashboard e análise externa passam a consumir JSONL estruturado e consistente.

## Fase 5 - OMS Leve Em Memória

Criar `fusion/execution/oms.py`.

### Responsabilidades

Manter estado em memória de:

- últimas ordens;
- ordens ativas;
- trades executados;
- posições abertas;
- conta;
- último tick por ativo;
- último contrato conhecido por ativo.

### Métodos iniciais

- `update_tick(tick)`
- `update_order(order)`
- `update_trade(trade)`
- `update_position(position)`
- `update_account(account)`
- `get_active_orders(symbol=None)`
- `get_positions(symbol=None)`
- `get_last_tick(symbol)`
- `get_contract(symbol)`

### Resultado esperado

O dashboard pode consultar um estado operacional limpo, sem depender só de leitura de log.

## Fase 6 - Contrato Do Ativo

Criar `fusion/core/contracts.py`.

### Fontes de dados

1. MT5 `symbol_info`.
2. Overrides no `fusion_config.yaml`.
3. Cache local em JSON.

### Config sugerida

```yaml
contracts:
  overrides:
    GOLD:
      broker_symbol: XAUUSD
      asset_type: metal
      point_value: 1.0
      min_lot: 0.01
      lot_step: 0.01
    EURUSD:
      asset_type: forex
```

### Uso no sistema

- cálculo de lote;
- risco por ponto;
- spread;
- validação de símbolo;
- dashboard;
- auditoria;
- filtros específicos por ativo.

### Resultado esperado

GOLD/XAUUSD, forex majors, crosses e ativos menos líquidos passam a ser tratados com metadados próprios.

## Fase 7 - Engines Registradas

Criar `fusion/core/engine_registry.py`.

### Engines alvo

- `RiskEngine`
- `PortfolioEngine`
- `ContextEngine`
- `AuditEngine`
- `DashboardEngine`
- `ExecutionEngine`
- `AdvisorEngine`
- `MarketRegimeEngine`
- `MarketStructureEngine`
- `OpportunityEngine`

### Interface mínima

```python
class BaseFusionEngine:
    name: str

    def start(self): ...
    def stop(self): ...
    def on_event(self, event): ...
```

### Resultado esperado

Cada motor tem responsabilidade própria e pode ser ligado, desligado, testado e auditado isoladamente.

## Fase 8 - Integração Com O Fluxo Atual

Integrar sem quebrar o comportamento atual.

### Pontos de emissão

Antes do modelo:

- publicar `SIGNAL_SCAN`

Depois do modelo:

- publicar `SIGNAL`

Antes dos filtros:

- publicar `DECISION_START`

Após cada engine/filtro:

- publicar `ENGINE_RESULT`

Antes da ordem:

- publicar `ORDER_REQUEST`

Depois da ordem:

- publicar `ORDER_RESULT`

Quando posição mudar:

- publicar `POSITION_UPDATE`

### Resultado esperado

Cada decisão pode ser reconstruída do começo ao fim.

## Fase 9 - Dashboard Consumindo Eventos

Atualizar `dashboard/fusion_dashboard.py`.

### Novas visões

- timeline de eventos por ativo;
- ciclo da ordem;
- estado atual do OMS;
- motivos estruturados;
- comparação entre decisão e execução;
- painel de contratos dos ativos;
- painel de engines registradas.

### Resultado esperado

O dashboard deixa de ser apenas um leitor de logs e passa a ser uma tela operacional.

## Fase 10 - Replay Histórico

Criar `tools/replay_events.py`.

### Objetivo

Reprocessar eventos de um dia e reconstruir:

- sinais gerados;
- decisões tomadas;
- filtros acionados;
- ordens bloqueadas;
- ordens enviadas;
- resultados de execução;
- estado de posição.

### Resultado esperado

Permite debugar um caso como:

> “Por que abriu EURNZD de novo logo após fechar?”

sem depender apenas de leitura manual do log.

## Fase 11 - Advisor/IA Em Shadow

Criar `fusion/advisor/`.

### Fluxo

1. Robô gera decisão.
2. Publica `ADVISOR_REQUEST`.
3. Advisor responde com `ADVISOR_RESPONSE`.
4. Em shadow, a resposta não bloqueia.
5. Depois de validação, pode virar moderação.

### Payload esperado

- ativo;
- timeframe;
- direção;
- probabilidades;
- motores alinhados;
- motores conflitantes;
- exposição;
- correlação;
- macro fluxo;
- risco;
- últimas métricas relevantes.

### Resultado esperado

O agente IA pode revisar decisões sem controlar diretamente o robô.

## Fase 12 - Migração Progressiva

### Ordem recomendada

1. Criar objetos e enums.
2. Criar event bus.
3. Emitir eventos em paralelo.
4. Criar event logger.
5. Criar OMS leve.
6. Popular OMS com dados reais.
7. Dashboard lê OMS/eventos.
8. Auditoria usa eventos normalizados.
9. Advisor entra em shadow.
10. Decisões passam a depender menos de logs textuais.

## Arquivos Sugeridos

```text
fusion/
  core/
    enums.py
    objects.py
    events.py
    event_logger.py
    engine_registry.py
    contracts.py
  execution/
    oms.py
  advisor/
    __init__.py
    advisor_client.py
    advisor_payloads.py
  dashboard/
    event_readers.py
tools/
  replay_events.py
  inspect_order_lifecycle.py
docs/
  roadmap_event_driven_fusion_v2.md
```

## Critérios De Aceite

### Infraestrutura

- `python -m compileall fusion dashboard tools` sem erro.
- Eventos gravados em JSONL.
- Cada decisão tem `correlation_id`.
- Cada ordem tem ciclo rastreável.

### Segurança

- Nenhuma mudança inicial na decisão de abrir ordem.
- Advisor começa em shadow.
- OMS começa apenas observando.
- Dashboard novo não deve travar o robô.

### Operacional

- Conseguir responder:
  - qual sinal nasceu;
  - quais engines avaliaram;
  - qual filtro bloqueou;
  - se houve ordem enviada;
  - se houve execução;
  - qual posição ficou aberta;
  - qual contrato/metadado foi usado.

## Prioridade Recomendada

### Primeiro bloco

1. `objects.py`
2. `enums.py`
3. `events.py`
4. `event_logger.py`

### Segundo bloco

5. `contracts.py`
6. `oms.py`
7. emissão de eventos no fluxo atual

### Terceiro bloco

8. dashboard por eventos
9. replay histórico
10. advisor IA em shadow

## Resultado Final Esperado

O FUSION deixa de ser apenas um robô que executa fluxo procedural e passa a ser uma plataforma operacional orientada a eventos:

- mais modular;
- mais auditável;
- mais fácil de testar;
- mais fácil de integrar com dashboard;
- mais preparada para IA;
- mais próxima de uma arquitetura institucional.
