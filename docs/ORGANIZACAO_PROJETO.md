# Organizacao proposta do FUSION_V2

Objetivo: deixar a separacao notoria entre o que roda em tempo real, o que serve para treinamento, o que e analise/backtest, o que sao paineis e o que e legado.

## Regra de ouro

A fase 1 nao move o nucleo do robo. O Fusion usa muitos caminhos relativos (`./config`, `./data`, `./models_research`, `./reports`, `./logs`). Mover esses diretorios sem atualizar codigo/config pode quebrar execucao, painel e exports do MT5.

## Camada 00 - Runtime do robo

Itens que devem continuar sempre faceis de identificar e protegidos:

- `run_fusion.py`: entrada principal do robo.
- `fusion/`: codigo runtime do Fusion.
- `config/`: configuracoes operacionais e controle runtime.
- `runtime/`: estado vivo, snapshots e dados temporarios de execucao.
- `logs/`: logs vivos.
- `mql5/`: integracao/arquivos MQL5.
- `requirements.txt`: dependencias Python.

Esses itens nao devem ser misturados com treino, relatorio ou backup.

## Camada 01 - Paineis e interfaces

- `terminal_windows/`: painel Windows atual.
- `terminal_qt/`: terminal/bridge Qt e utilidades de dados do painel.
- `terminal_desktop/`: painel desktop legado/alternativo.
- `dashboard/`: dashboard antigo/apoio.
- `frontend/`: frontend web.
- `fusion-frontend/`: frontend web novo/alternativo.

Regra: qualquer coisa visual ou API de painel deve ficar aqui ou ser documentada como dependencia do painel.

## Camada 02 - Dados e treinamento

- `data/`: dados brutos/parquet/cache.
- `features/`: features exportadas ou usadas em treino/backtest.
- `models/`, `models_research/`, `models_principal/`, `models_experts/`, `models_experts_v2/`, `models_expr/`: modelos e variantes.
- Scripts de treino em `tools/train_*.py`, `tools/gerar_features_*.py`, `tools/build_*calibration*.py`, etc.

Regra: dado de treino nao deve ficar no runtime vivo, exceto quando explicitamente usado pelo robo em producao.

## Camada 03 - Analises, backtests e relatorios

- `reports/`: saidas de analise, auditoria, backtest, calibracao e diagnostico.
- `prints/`: evidencias visuais.
- Scripts `tools/analyze_*.py`, `tools/backtest_*.py`, `tools/optimize_*.py`, `tools/summarize_*.py`, `tools/compare_*.py`.
- Arquivos soltos como `tabela.txt`, `tabela2.txt`, `tabela_blocos.txt`, `table_predictions.py`, `extract_predictions.py`.

Regra: relatorio e analise nao podem ser tratados como fonte runtime, a nao ser quando o config apontar explicitamente para eles, como `reports/operational_target_matrix/operational_target_matrix_latest.json`.

## Camada 04 - Ferramentas operacionais

- `tools/mt5_live_api.py`
- `tools/mt5_snapshot_api.py`
- `tools/export_mt5_candles_for_terminal.py`
- `tools/fusion_frontend_data.py`
- `tools/manage_mt5_live_api.ps1`
- `tools/open_fusion_frontend_app.ps1`

Esses scripts ficam entre runtime e painel. Devem ser classificados como `tools/runtime` numa futura migracao.

## Camada 05 - Documentacao

- `docs/`
- `README.md`
- `DIAGNOSTICO_STARTUP.md`
- `IMPLEMENTACAO_*.md`
- `OTIMIZACAO_*.md`
- `plan.md`

Sugestao de migracao fisica segura: mover documentos soltos da raiz para `docs/operacional/` e manter links no README.

## Camada 06 - Backups, legado e projetos externos

- `_archive/backups/`
- `fusion_pro/`
- `fusion_refatorado/` (mantido na raiz: ainda e dependencia runtime dos ensembles M5)
- `repositorio/`
- `revisar/`

Sugestao: mover para `_archive/` ou `_external/` depois de confirmar que nenhum script runtime importa esses caminhos.

## Estrutura alvo sugerida

```text
FUSION_V2/
  00_runtime/
    robo/              # fusion/, run_fusion.py, config/, runtime/, mql5/
    logs/              # logs vivos
  01_apps/
    terminal_windows/
    terminal_qt/
    frontend_web/
  02_research/
    data/
    features/
    models/
    training_scripts/
  03_analysis/
    reports/
    backtests/
    diagnostics/
  04_tools/
    runtime_tools/
    maintenance/
    migrations/
  05_docs/
    operacional/
    arquitetura/
  90_archive/
    backups/
    legacy_fusion/
  91_external/
    external_integrations/
```

## Plano de migracao seguro

1. Congelar runtime atual e registrar entrypoints.
2. Criar manifests de caminhos usados em runtime.
3. Mover primeiro apenas documentacao solta e arquivos de analise soltos.
4. Separar `tools/` por subpastas, mantendo wrappers na raiz de `tools/` quando algum comando externo depender do caminho antigo.
5. Separar modelos em `models/runtime` e `models/research` depois de confirmar quais arquivos o Fusion carrega.
6. So entao migrar diretórios grandes/legados para `_archive` e `_external`.

## Inventario gerado

- `reports/project_inventory/root_inventory.md`
- `reports/project_inventory/root_inventory.csv`
- `reports/project_inventory/build_project_inventory.py`


