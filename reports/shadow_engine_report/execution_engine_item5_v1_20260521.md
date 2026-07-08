# Item 5 - Execution Engine v1

Objetivo:

- Separar direcao de execucao.
- Avaliar se o timing operacional da entrada e bom no candle/contexto atual.
- Manter tudo em `shadow`.
- Nao alterar abertura de ordens nesta fase.

## Implementado

Arquivo principal:

- `fusion/engines/execution.py`

Engine:

- `ExecutionEngine`

Config:

- `ExecutionConfig`

## Sinais Avaliados

O engine calcula:

- `entry_quality_score`
- `breakout_quality`
- `buy_breakout_quality`
- `sell_breakout_quality`
- candle rejection alinhado
- absorcao de liquidez alinhada
- fake breakout / stop hunt
- exhaustion candle
- momentum ignition
- volume de execucao
- range intrabar vs ATR
- corpo do candle

## Estados Possiveis

- `good_execution`
- `acceptable_with_warnings`
- `weak_execution`
- `avoid_execution`
- `INSUFFICIENT_DATA`

## Integracao No Runtime

Arquivo:

- `fusion/main.py`

Adicionado:

- `_execution_engine_check(...)`

O engine roda:

- depois de `entry_timing`;
- antes de candle/EMA;
- tambem em `_run_shadow_diagnostics(...)`.

## Config

Arquivo:

- `config/fusion_config.yaml`

Nova secao:

- `entry_filters.execution_engine`

Parametros:

- `enabled`
- `mode`
- `bars`
- `min_entry_quality_score`
- `min_breakout_quality_score`
- `min_volume_ratio`
- `exhaustion_streak`
- `fake_breakout_max_bars`
- `log_each_check`
- `reason_code`

## Integracao Com Outros Engines

O `execution_engine` foi adicionado aos pesos de:

- `context_engine`
- `consensus_engine`
- `opportunity_engine`

O `tools/build_shadow_engine_report.py` tambem passou a contabilizar `execution_engine`.

## Validacao

Comandos executados:

- `.\venv\Scripts\python.exe -m compileall fusion tools\check_execution_engine.py tools\build_shadow_engine_report.py`
- `.\venv\Scripts\python.exe tools\check_execution_engine.py`
- `.\venv\Scripts\python.exe -c "from fusion.main import FusionV2; print('import_ok')"`

Resultado do teste sintetico:

- `state`: `good_execution`
- `direction`: `BUY`
- `entry_quality_score`: `0.82`
- `breakout_quality`: `0.85`
- positivos:
  - `breakout_quality_ok`
  - `momentum_ignition`

## Decisao

Status: manter `shadow`.

Motivo:

- Ainda precisa de forward test.
- O score de execucao deve ser calibrado por ativo/timeframe.
- Nao deve bloquear ordens ainda.

## Proximo Passo

Reiniciar o robo e revisar nos proximos eventos:

- frequencia de `avoid_execution`;
- frequencia de `weak_execution`;
- quantas entradas `ALLOW` tinham execucao fraca;
- relacao entre `entry_quality_score` e resultado posterior.

