# Organizacao do projeto - log de migracao

## Fase 1 - documentos e analises soltas

Executado:

- Criado `docs/operacional/`.
- Movidos documentos operacionais soltos da raiz para `docs/operacional/`.
- Criado `reports/legacy_tables/`.
- Movidas tabelas soltas da raiz para `reports/legacy_tables/`.
- Criado `tools/analysis_legacy/`.
- Movidos scripts legados `extract_predictions.py` e `table_predictions.py` para `tools/analysis_legacy/`.
- Criados `_archive/` e `_external/` como destinos preparados para separacao.

Nao movido nesta fase:

- `fusion/`, `config/`, `runtime/`, `logs/`, `mql5/`, `run_fusion.py`, `requirements.txt`.
- `data/`, `features/`, `models*`, porque ainda ha paths relativos em `fusion_config.yaml`.
- `terminal_*`, `frontend*`, `dashboard`, porque sao paineis/entradas que precisam de validacao propria.

## Fase 2 - projetos externos

Movidos para `_external/`:

- `Quant/`
- `QuantDinger-main/`
- `QuantDinger-main-mt5/`
- `QuantDinger-Vue-main/`
- `QuantDinger-Vue-main-mt5/`

Observacao: uma duplicata residual pesada de `QuantDinger-Vue-main-mt5/` foi preservada em `_external/_cleanup_pending_QuantDinger-Vue-main-mt5_duplicate/` por causa de `node_modules`. O projeto consolidado esta em `_external/QuantDinger-Vue-main-mt5/`; a duplicata pode ser removida posteriormente com uma limpeza longa fora do fluxo principal.

## Fase 2 - archive

Movidos para `_archive/`:

- `backups/`
- `fusion_pro/`
- `repositorio/`
- `revisar/`

Mantido na raiz:

- `fusion_refatorado/`, porque ainda e importado pelo runtime (`fusion.approved_ensembles`, `estrategia_6`, trailing e registry M5).

## Fase 3 - pesquisa e evidencias

Movidos:

- `prints/` -> `reports/prints/legacy_chart_prints/`.
- `experts/` -> `02_research/experts/`.

Esses itens nao apareceram como dependencia direta do runtime atual.
