# Item 8 - Confidence Calibration Engine v2

Objetivo:

- Evoluir calibracao de probabilidades para uma camada mais estatistica.
- Usar perfis historicos por ativo/timeframe/lado com suavizacao Bayesiana.
- Adicionar confiabilidade do perfil.
- Manter tudo em `shadow`.

## Implementado

Arquivos:

- `fusion/engines/calibration.py`
- `tools/build_confidence_calibration_profiles.py`
- `tools/check_confidence_calibration.py`

## Gerador de Perfis

Novo script:

- `tools/build_confidence_calibration_profiles.py`

Entradas usadas:

- `reports/market_structure_calibration/market_structure_calibration_candidates_atr1.5_slatr1_lh100.csv`
- `reports/market_structure_calibration/market_structure_calibration_candidates_tp100_sl100_lh100.csv`
- `reports/market_structure_calibration/market_structure_calibration_candidates_optimized_lh100.csv`

Saidas:

- `reports/confidence_calibration/confidence_calibration_profiles.json`
- `reports/confidence_calibration/confidence_calibration_profiles.md`

Resultado inicial:

- Perfis exatos: 68
- Perfis fallback: 46

## Metricas Criadas

Cada perfil contem:

- `samples`
- `wins_estimated`
- `feature_count`
- `rule_count`
- `weighted_win_rate`
- `edge_weighted_win_rate`
- `posterior_probability`
- `wilson_lower`
- `reliability_score`
- `avg_edge`
- `max_edge`
- `sources`

## Mudancas No Engine

Arquivo:

- `fusion/engines/calibration.py`

O engine agora:

- tenta usar `profiles_path` primeiro;
- usa fallback por:
  - symbol + qualquer timeframe;
  - qualquer symbol + timeframe;
  - global por lado;
- aplica suavizacao Bayesiana;
- usa `wilson_lower` e `reliability_score`;
- marca perfil como:
  - `calibrated`;
  - `fallback_profile`;
  - `weak_profile`;
  - `low_reliability`;
  - `no_profile`.

## Config

Arquivo:

- `config/fusion_config.yaml`

Novas chaves em `entry_filters.confidence_calibration`:

- `profiles_path`
- `use_profiles`
- `prior_samples`
- `min_reliability`

## Validacao

Comandos executados:

- `.\venv\Scripts\python.exe tools\build_confidence_calibration_profiles.py`
- `.\venv\Scripts\python.exe -m compileall fusion tools\build_confidence_calibration_profiles.py tools\check_confidence_calibration.py`
- `.\venv\Scripts\python.exe tools\check_confidence_calibration.py --symbol AUDCHF --timeframe H1 --side SELL --p-sell 0.55`
- `.\venv\Scripts\python.exe -c "from fusion.main import FusionV2; print('import_ok')"`

Resultado do teste:

- Ativo/timeframe/lado: `AUDCHF H1 SELL`
- Probabilidade bruta: `0.55`
- Probabilidade historica posterior: `0.7476`
- Probabilidade calibrada: `0.6488`
- Reliability score: `0.8207`
- Estado: `calibrated`
- Fonte: `exact`

## Decisao

Status: manter `shadow`.

Motivo:

- A calibracao agora e mais robusta, mas ainda depende de perfis derivados de backtest/labels.
- Precisa comparar probabilidade calibrada contra resultado forward.
- Ainda nao deve bloquear ordens nem alterar lote.

## Proximo Passo

Reiniciar o robo e revisar:

- frequencia de `calibrated`;
- frequencia de `fallback_profile`;
- frequencia de `low_reliability`;
- quantas ordens teriam probabilidade reduzida;
- se `calibrated_probability` melhora expectativa posterior.

