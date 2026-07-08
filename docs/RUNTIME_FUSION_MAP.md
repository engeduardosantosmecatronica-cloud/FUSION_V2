# Mapa de runtime do Fusion

Este arquivo lista o minimo que precisa estar consistente para o robo rodar em tempo real.

## Entrada principal

- `run_fusion.py` importa `fusion.main.FusionV2`.
- `fusion/main.py` inicializa motores, estrategias, runtime control, MT5, logs e execucao.

## Configuracoes criticas

- `config/fusion_config.yaml`
- `config/fusion_runtime_control.json`
- `config/market_briefing_today.json`

## Diretorios runtime lidos/escritos

- `logs/`: logs e stdout/stderr de bridges.
- `runtime/`: snapshots, candles e estado auxiliar.
- `reports/operational_target_matrix/operational_target_matrix_latest.json`: usado pelo painel MT5/signal panel quando habilitado.
- `reports/correlation/correlation_matrix_H1.json`: usado por filtro de exposicao/correlacao.

## Modelos e dados configurados

No `config/fusion_config.yaml`:

- `model.model_dir: ./models_research`
- `market_data.data_dir: ./data`
- `market_data.parquet_dir: ./data/parquet`
- Algumas estrategias ainda apontam para `./features/features_backteste_dinamica.csv`.

## Paineis/bridges que participam do runtime operacional

- `terminal_windows/run_terminal_windows.ps1`: sobe painel Windows e bridge MT5 de candles.
- `tools/export_mt5_candles_for_terminal.py`: exporta candles MT5 para `runtime/market_data/latest_candles`.
- `tools/mt5_live_api.py`: API de dados/ordens MT5 para painel/frontend.
- `tools/fusion_frontend_data.py`: dados auxiliares para frontend.

## Regra de organizacao

Antes de mover fisicamente qualquer item acima, atualizar os paths em `config/fusion_config.yaml`, scripts `.ps1`, imports Python e README de execucao.

## Itens que podem ser separados primeiro com baixo risco

- Documentos soltos `.md` da raiz para `docs/operacional/`.
- Arquivos `tabela*.txt` para `reports/manual_validation/` ou `reports/legacy_tables/`.
- Backups antigos para `_archive/`.
