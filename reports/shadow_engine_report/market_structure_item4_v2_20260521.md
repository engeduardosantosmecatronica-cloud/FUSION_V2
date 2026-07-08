# Item 4 - Market Structure Engine Institucional v2

Objetivo:

- Evoluir a camada `market_structure` para capturar sinais estruturais mais proximos de uma leitura institucional.
- Manter tudo em `shadow`.
- Nao alterar abertura de ordens nesta fase.

## Implementado

Arquivo principal:

- `fusion/features/market_structure.py`

Novas features estruturais:

- `higher_high`
- `lower_high`
- `higher_low`
- `lower_low`
- `swing_high_expansion_atr`
- `swing_low_expansion_atr`
- `bullish_structure_sequence`
- `bearish_structure_sequence`
- `structure_transition`
- `displacement_up`
- `displacement_down`
- `bullish_fvg`
- `bearish_fvg`
- `bullish_fvg_size_atr`
- `bearish_fvg_size_atr`
- `bullish_fvg_mitigated`
- `bearish_fvg_mitigated`
- `bullish_imbalance`
- `bearish_imbalance`
- `bullish_order_block_proxy`
- `bearish_order_block_proxy`
- `stop_hunt_up`
- `stop_hunt_down`
- `institutional_structure_score`
- `bars_since_bos_up`
- `bars_since_bos_down`
- `bars_since_choch_up`
- `bars_since_choch_down`
- `bars_since_stop_hunt_up`
- `bars_since_stop_hunt_down`

## Integracao No Runtime

Arquivo:

- `fusion/main.py`

O `_market_structure_analyze_row(...)` agora registra tambem:

- score institucional;
- stop hunt;
- FVG;
- imbalance;
- displacement;
- BOS;
- CHOCH;
- sequencia estrutural bullish/bearish.

Novos motivos possiveis no shadow:

- `stop_hunt`
- `estrutura_fraca`

## Config

Arquivo:

- `config/fusion_config.yaml`

Novas chaves:

- `entry_filters.market_structure.flag_stop_hunt`
- `entry_filters.market_structure.use_institutional_score`
- `entry_filters.market_structure.min_institutional_structure_score`
- `score_penalties.stop_hunt`
- `score_penalties.weak_institutional_structure`

## Validacao

Comandos executados:

- `.\venv\Scripts\python.exe -m py_compile fusion\features\market_structure.py fusion\main.py`
- `.\venv\Scripts\python.exe -c "from fusion.main import FusionV2; print('import_ok')"`

Teste sintetico:

- `higher_high`: 1
- `break_of_structure_up`: 1
- `institutional_structure_score`: ~0.447

## Decisao

Status: manter `shadow`.

Motivo:

- A camada foi enriquecida, mas ainda precisa de forward test.
- O score institucional ainda precisa ser calibrado por ativo/timeframe.
- Nao deve bloquear ordens ainda.

## Proximo Passo

Gerar eventos novos apos reiniciar o robo e revisar:

- frequencia de `stop_hunt`;
- frequencia de `estrutura_fraca`;
- distribuicao de `institutional_structure_score`;
- impacto desses sinais sobre trades permitidos e bloqueados.

