# Historical Decision — Observability & Dashboard Mapping

Resumo rápido das saídas e como integrar no dashboard:

- Config YAML:
  - `decision_engine.historical_enabled` (bool): habilita/inibe a execução da `HistoricalDecisionEngine` no runtime. Padrão: `false`.
  - `entry_filters.historical_decision` (obj): controla `mode` (`shadow`|`block`), `lookback_bars`, `min_domain_quality` e `log_each_check`.

- Engine names registrados no backend (usar no dashboard):
  - `historical_price_acceptance` — saída do `HistoricalPriceAcceptanceEngine` (status, reasons, current_price, domain_low/high).
  - `historical_decision_gate` — saída consolidada do `HistoricalDecisionEngine` usada para auditoria e gate; contém `direction`, `score`, `confidence`, `positive_factors`, `negative_factors` e `features` com campos:
    - `acceptance_status`: accepted|needs_validation|rejected
    - `recency`: resultado do `HistoricalRecencyEngine` (ex.: `recent_bias`)
    - `mtf`: resultado do `HistoricalMTFContextEngine` (ex.: `alignment`)
    - `zone`: {type, low, high}

- Recomendações de mapeamento no dashboard (frontend):
  - Mostrar `historical_decision_gate` na lista de `EngineOutputs` do painel de sinais com:
    - Label curto: "Hist.Decision"
    - Status colorido: `buy/sell` -> verde/vermelho; `hold` -> cinza/alarme
    - Expor `confidence` como barra/porcentagem e `positive_factors` como motivos listados (máx 3)
    - Expor `features.acceptance_status` e `features.zone.type` nos detalhes do sinal (tooltip ou collapsible)

- Operacional: sugestão de rollout
  1. Manter `entry_filters.historical_decision.mode: shadow` por 7 dias e monitorar logs/events para falsos positivos.
  2. Validar via backtests representativos (use `tools/run_historical_replay.py SYMBOL`) e comparar decisões com casos conhecidos.
  3. Quando confiante, alternar para `mode: block` para símbolos controlados (usar `runtime_control` para habilitar por símbolo antes de globalizar).

- Como rodar um replay rápido (exemplo):

```
python tools/run_historical_replay.py AUDCAD --max_frames 200
```

Observações:
- O backend já grava engine outputs via `FusionV2._record_engine_output()` com nomes `historical_price_acceptance` e `historical_decision_gate`.
- O `event_bus` também publica `DASHBOARD_UPDATE` para registro do `engine_registry`.

Se precisar, eu posso abrir um PR separado para atualizar componentes do frontend (ex.: `FusionSignalCard` / `SignalPanel`) para exibir `historical_decision_gate`. Deseja que eu faça isso agora? 
