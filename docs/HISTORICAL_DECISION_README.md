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

## Recent Changes (feat/historical-ui-and-tools)

- `fusion/engines/risk.py`: losing positions are now reported as `warnings` (e.g. `muitas_posicoes_negativas`) instead of `negative_factors` to avoid blocking new openings.
- `fusion/main.py`: logging of short `factors=` fields no longer includes `warnings` (prioritizes `negative_factors` → `positive_factors`), reducing false-positive block indicators in logs.
- Frontend: `FusionSignalCard` already supports `historical_decision` / `historical_decision_gate` display; details are shown in the signal card (confidence, positive factors, features).

These changes are pushed to branch `feat/historical-ui-and-tools` and attached to the open PR for review.

## Proposed Rollout

1. Keep `entry_filters.historical_decision.mode: shadow` for 7 days, monitor `historical_decision_gate` outputs and logs for false positives.
2. Run representative comparative backtests for major symbols (EURUSD, XAUUSD, AUDCAD) and compare decision distributions vs baseline.
3. If shadow results are acceptable, enable `mode: block` per-symbol (use `runtime_control` overrides) for a small controlled subset (e.g., EURUSD only) for 7 days.
4. After successful per-symbol trial, incrementally enable for additional symbols.

## How I can help next

- I can run the comparative backtests and collect summary CSVs and charts.
- I can run the backend in shadow for a short live run and collect runtime logs for inspection.
- I can open or update the PR with a clear changelog and rollout checklist.

Tell me which of the above to run next and I'll execute it.
