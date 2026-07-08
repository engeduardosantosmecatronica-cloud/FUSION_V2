# Operational Readiness

- Data: 20260522
- Status geral: INFO
- Eventos totais: 31942
- Eventos recentes: 3025
- Ultimo evento: 2026-05-22T12:47:44.786112

## Checks

- OK | event_bus_config | event_log_enabled=True
- OK | event_bus_async | use_async=True
- OK | oms_snapshot_config | snapshot_enabled=True
- OK | allow_new_orders | allow_new_orders=True
- OK | events_freshness | ultimo_evento=2026-05-22T12:47:44.786112 idade_min=0.3
- OK | recent_signal_decision | SIGNAL=78 DECISION=191 janela_min=30
- OK | recent_engine_results | ENGINE_RESULT=2519 janela_min=30
- OK | recent_oms_events | POSITION_UPDATE=56 ACCOUNT_UPDATE=4
- OK | decision_correlation | decision_sem_signal=0
- OK | engine_correlation | decision_sem_engine=0
- INFO | order_lifecycle | order_cycles=0 request_sem_result=0 result_sem_request=0
- INFO | order_result_presence | ORDER_RESULT_total=0 TRADE_UPDATE_total=401 POSITION_UPDATE_total=425

## Tipos Recentes

- ENGINE_RESULT: 2519
- DECISION: 191
- TRADE_UPDATE: 145
- SIGNAL: 78
- POSITION_UPDATE: 56
- DASHBOARD_UPDATE: 32
- ACCOUNT_UPDATE: 4