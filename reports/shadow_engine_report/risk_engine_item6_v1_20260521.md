# Item 6 - Risk Engine v1

Objetivo:

- Criar motor institucional de risco.
- Avaliar risco operacional antes da ordem.
- Sugerir reducao de tamanho/risco sem alterar o lote real nesta fase.
- Manter tudo em `shadow`.

## Implementado

Arquivo principal:

- `fusion/engines/risk.py`

Engine:

- `RiskEngine`

Config:

- `RiskConfig`

## Sinais Avaliados

O engine calcula:

- `risk_score`
- `position_multiplier_suggested`
- drawdown percentual
- perda flutuante percentual
- quantidade de posicoes abertas
- quantidade de posicoes negativas
- conflito vindo de `context_engine`, `consensus_engine` e `opportunity_engine`
- risco de `portfolio_exposure`
- risco de `portfolio_correlation`
- `PANIC_VOLATILITY`

## Estados Possiveis

- `normal_risk`
- `reduced_risk`
- `high_risk`
- `critical_risk`

## Integracao No Runtime

Arquivo:

- `fusion/main.py`

Adicionado:

- `_risk_engine_account_snapshot(...)`
- `_risk_engine_positions_snapshot(...)`
- `_risk_engine_check(...)`

O engine roda:

- depois de `execution_engine`;
- antes de candle/EMA;
- tambem em `_run_shadow_diagnostics(...)`.

## Config

Arquivo:

- `config/fusion_config.yaml`

Nova secao:

- `entry_filters.risk_engine`

Parametros:

- `max_drawdown_pct`
- `warning_drawdown_pct`
- `max_floating_loss_pct`
- `warning_floating_loss_pct`
- `max_open_positions`
- `max_losing_positions`
- `high_conflict_threshold`
- `moderate_conflict_threshold`
- `min_multiplier`
- `log_each_check`
- `reason_code`

## Integracao Com Outros Engines

O `risk_engine` foi adicionado aos pesos de:

- `context_engine`
- `consensus_engine`
- `opportunity_engine`

O `tools/build_shadow_engine_report.py` tambem passou a contabilizar `risk_engine`.

## Validacao

Comandos executados:

- `.\venv\Scripts\python.exe -m compileall fusion tools\check_risk_engine.py tools\build_shadow_engine_report.py`
- `.\venv\Scripts\python.exe tools\check_risk_engine.py`
- `.\venv\Scripts\python.exe -c "from fusion.main import FusionV2; print('import_ok')"`

Resultado do teste sintetico:

- `state`: `critical_risk`
- `direction`: `NEUTRAL`
- `risk_score`: `0.17`
- `position_multiplier_suggested`: `0.5`
- negativos:
  - `muitas_posicoes_negativas`
  - `conflito_alto`
- alertas:
  - `drawdown_alerta`
  - `perda_flutuante_alerta`
  - `portfolio:exposicao_excessiva`

## Decisao

Status: manter `shadow`.

Motivo:

- Ainda nao altera lote real.
- Precisa validar forward test antes de reduzir tamanho automaticamente.
- O primeiro uso recomendado e reduzir posicao, nao bloquear ordem.

## Proximo Passo

Reiniciar o robo e revisar nos proximos eventos:

- distribuicao de `risk_score`;
- frequencia de `reduced_risk`, `high_risk`, `critical_risk`;
- quantas entradas `ALLOW` teriam multiplicador menor que 1;
- se `critical_risk` coincide com periodos de perda acumulada.

