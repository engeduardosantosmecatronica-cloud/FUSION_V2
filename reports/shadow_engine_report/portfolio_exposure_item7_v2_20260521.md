# Item 7 - Portfolio Exposure Engine v2

Objetivo:

- Evoluir controle de exposicao de portfolio.
- Detectar concentracao sintetica por moeda, exposicao bruta, cluster correlacionado e exposicao perdedora.
- Manter tudo em `shadow`.
- Nao bloquear nem alterar lote real nesta fase.

## Implementado

Arquivo principal:

- `fusion/engines/portfolio.py`

Novos controles:

- `max_cluster_exposure`
- `warning_cluster_exposure`
- `correlation_threshold`
- `max_gross_exposure`
- `warning_gross_exposure`
- `max_losing_currency_exposure`

## Novas Leituras

O engine agora calcula:

- exposicao sintetica por moeda;
- exposicao projetada por moeda;
- exposicao perdedora por moeda;
- maior exposicao atual;
- maior exposicao projetada;
- maior exposicao perdedora por moeda;
- exposicao bruta total;
- exposicao bruta projetada;
- unidades em cluster correlacionado com o ativo candidato;
- lista de posicoes correlacionadas;
- concentracao por simbolo;
- posicoes negativas.

## Novos Estados

- `gross_overexposure`
- `gross_warning`
- `cluster_overexposure`
- `cluster_warning`
- `losing_currency_overexposure`

Estados anteriores mantidos:

- `ok`
- `symbol_concentration`
- `currency_warning`
- `currency_overexposure`

## Integracao No Runtime

Arquivo:

- `fusion/main.py`

O `_portfolio_exposure_check(...)` agora:

- carrega matriz de correlacao;
- passa `correlation_matrix` para o engine;
- usa parametros novos vindos de `config/fusion_config.yaml`.

## Config

Arquivo:

- `config/fusion_config.yaml`

Novas chaves em `entry_filters.portfolio_exposure`:

- `max_cluster_exposure`
- `warning_cluster_exposure`
- `correlation_threshold`
- `max_gross_exposure`
- `warning_gross_exposure`
- `max_losing_currency_exposure`
- `matrix_path`

## Relatorios

Arquivo atualizado:

- `tools/build_shadow_engine_report.py`

Agora reconhece estados novos:

- `gross_overexposure`
- `cluster_overexposure`
- `losing_currency_overexposure`
- `gross_warning`
- `cluster_warning`

## Validacao

Comandos executados:

- `.\venv\Scripts\python.exe -m compileall fusion tools\check_portfolio_exposure.py tools\build_shadow_engine_report.py`
- `.\venv\Scripts\python.exe tools\check_portfolio_exposure.py --symbol EURNZD --side BUY`
- `.\venv\Scripts\python.exe -c "from fusion.main import FusionV2; print('import_ok')"`

Resultado do teste sintetico:

- `state`: `cluster_overexposure`
- `direction`: `SELL`
- `score`: `0.4`
- negativo:
  - `cluster_correlacionado:3.00`
- alertas:
  - exposicao AUD/EUR alta;
  - posicoes negativas.

## Decisao

Status: manter `shadow`.

Motivo:

- O engine ficou mais sensivel e precisa de forward test.
- O primeiro uso recomendado ainda e reduzir risco/tamanho, nao bloquear.

## Proximo Passo

Reiniciar o robo e revisar nos proximos eventos:

- frequencia de `cluster_overexposure`;
- frequencia de `gross_overexposure`;
- frequencia de `losing_currency_overexposure`;
- quais moedas concentram mais risco;
- se esses alertas coincidem com sequencias de prejuizo.

