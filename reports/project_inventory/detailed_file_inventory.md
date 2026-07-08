# Inventario detalhado de arquivos

Este inventario foi gerado para apoiar limpeza segura do projeto. O CSV contem a lista completa dos arquivos considerados.

- Arquivos inventariados: 64037
- CSV completo: `reports/project_inventory/detailed_file_inventory.csv`
- Diretorios pesados/gerados ignorados no inventario: `.git`, `.venv`, `node_modules`, `bin`, `obj`, caches Python/testes.

## Resumo por acao sugerida

| Acao | Arquivos |
|---|---:|
| `candidato_remocao` | 1 |
| `candidato_remocao_apos_revisao` | 22885 |
| `manter` | 10 |
| `manter_com_cautela` | 11717 |
| `manter_se_usado` | 26369 |
| `manter_se_util` | 2474 |
| `nao_deletar_com_robo_rodando` | 308 |
| `pode_limpar_com_robo_parado` | 249 |
| `revisar` | 24 |

## Resumo por categoria

| Categoria | Arquivos |
|---|---:|
| `ambiente_frontend` | 2 |
| `ambiente_ide` | 2 |
| `analise_relatorio` | 2450 |
| `arquivo_morto_legado` | 22884 |
| `config_runtime` | 6 |
| `dados_modelos_treinamento` | 25954 |
| `documentacao` | 23 |
| `estado_runtime` | 308 |
| `ferramenta_analise_teste` | 47 |
| `ferramenta_nao_classificada` | 22 |
| `ferramenta_runtime_bridge` | 10 |
| `ferramenta_treinamento` | 13 |
| `instalador_local` | 1 |
| `inventario_projeto` | 7 |
| `logs` | 249 |
| `painel_monitoramento` | 355 |
| `projeto_externo` | 1 |
| `runtime_entrypoint` | 2 |
| `runtime_robo` | 11701 |

## Resumo por pasta da raiz

| Pasta/arquivo | Arquivos | Categorias principais | Acao dominante |
|---|---:|---|---|
| `.vscode` | 2 | ambiente_ide (2) | `manter_se_util` |
| `02_research` | 12 | dados_modelos_treinamento (12) | `manter_se_usado` |
| `README.md` | 1 | documentacao (1) | `manter` |
| `_archive` | 22884 | arquivo_morto_legado (22884) | `candidato_remocao_apos_revisao` |
| `_external` | 1 | projeto_externo (1) | `candidato_remocao_apos_revisao` |
| `config` | 6 | config_runtime (6) | `manter_com_cautela` |
| `dashboard` | 4 | painel_monitoramento (4) | `manter_se_usado` |
| `data` | 1701 | dados_modelos_treinamento (1701) | `manter_se_usado` |
| `docs` | 22 | documentacao (22) | `manter_se_util` |
| `features` | 3 | dados_modelos_treinamento (3) | `manter_se_usado` |
| `frontend` | 149 | painel_monitoramento (149) | `manter_se_usado` |
| `fusion` | 125 | runtime_robo (125) | `manter_com_cautela` |
| `fusion-frontend` | 157 | painel_monitoramento (157) | `manter_se_usado` |
| `fusion_refatorado` | 11571 | runtime_robo (11571) | `manter_com_cautela` |
| `logs` | 249 | logs (249) | `pode_limpar_com_robo_parado` |
| `models` | 433 | dados_modelos_treinamento (433) | `manter_se_usado` |
| `models_experts` | 1958 | dados_modelos_treinamento (1958) | `manter_se_usado` |
| `models_experts_v2` | 14629 | dados_modelos_treinamento (14629) | `manter_se_usado` |
| `models_expr` | 415 | dados_modelos_treinamento (415) | `manter_se_usado` |
| `models_principal` | 434 | dados_modelos_treinamento (434) | `manter_se_usado` |
| `models_research` | 6369 | dados_modelos_treinamento (6369) | `manter_se_usado` |
| `mql5` | 5 | runtime_robo (5) | `manter_com_cautela` |
| `package-lock.json` | 1 | ambiente_frontend (1) | `revisar` |
| `package.json` | 1 | ambiente_frontend (1) | `revisar` |
| `reports` | 2457 | analise_relatorio (2450), inventario_projeto (7) | `manter_se_util` |
| `requirements.txt` | 1 | runtime_entrypoint (1) | `manter` |
| `run_fusion.py` | 1 | runtime_entrypoint (1) | `manter` |
| `runtime` | 308 | estado_runtime (308) | `nao_deletar_com_robo_rodando` |
| `rustup-init.exe` | 1 | instalador_local (1) | `candidato_remocao` |
| `terminal_desktop` | 2 | painel_monitoramento (2) | `manter_se_usado` |
| `terminal_qt` | 12 | painel_monitoramento (12) | `manter_se_usado` |
| `terminal_windows` | 31 | painel_monitoramento (31) | `manter_se_usado` |
| `tools` | 92 | ferramenta_analise_teste (47), ferramenta_nao_classificada (22), ferramenta_treinamento (13) | `manter_se_usado` |

## Amostras por pasta

A lista completa esta no CSV. As amostras abaixo mostram os primeiros arquivos de cada area para orientar a revisao humana.

### `.vscode`

| Arquivo | Categoria | Acao |
|---|---|---|
| `.vscode/launch.json` | `ambiente_ide` | `manter_se_util` |
| `.vscode/settings.json` | `ambiente_ide` | `manter_se_util` |

### `02_research`

| Arquivo | Categoria | Acao |
|---|---|---|
| `02_research/experts/base.py` | `dados_modelos_treinamento` | `manter_se_usado` |
| `02_research/experts/market_phase_expert.py` | `dados_modelos_treinamento` | `manter_se_usado` |
| `02_research/experts/news_expert.py` | `dados_modelos_treinamento` | `manter_se_usado` |
| `02_research/experts/risk_expert.py` | `dados_modelos_treinamento` | `manter_se_usado` |
| `02_research/experts/session_expert.py` | `dados_modelos_treinamento` | `manter_se_usado` |
| `02_research/experts/signal_zone_expert.py` | `dados_modelos_treinamento` | `manter_se_usado` |
| `02_research/experts/spread_expert.py` | `dados_modelos_treinamento` | `manter_se_usado` |
| `02_research/experts/sr_liquidity_expert.py` | `dados_modelos_treinamento` | `manter_se_usado` |
| `02_research/experts/target_room_expert.py` | `dados_modelos_treinamento` | `manter_se_usado` |
| `02_research/experts/trend_expert.py` | `dados_modelos_treinamento` | `manter_se_usado` |
| `02_research/experts/volatility_expert.py` | `dados_modelos_treinamento` | `manter_se_usado` |
| `02_research/README.md` | `dados_modelos_treinamento` | `manter_se_usado` |

### `README.md`

| Arquivo | Categoria | Acao |
|---|---|---|
| `README.md` | `documentacao` | `manter` |

### `_archive`

| Arquivo | Categoria | Acao |
|---|---|---|
| `_archive/backups/feature_rules_before_h4d1_20260520/backteste_rapido_dinamica_entradas.csv` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/feature_rules_before_h4d1_20260520/backteste_rapido_resumo.csv` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/feature_rules_before_h4d1_20260520/features_backteste_dinamica.csv` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_backup_20260611_033625/.env.local` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_backup_20260611_033625/.gitignore` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_backup_20260611_033625/components.json` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_backup_20260611_033625/dist/assets/index-CDyiyVXh.css` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_backup_20260611_033625/dist/assets/index-DdipaVCd.js` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_backup_20260611_033625/dist/index.html` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_backup_20260611_033625/entities/Candle.json` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_backup_20260611_033625/entities/MT5Connection.json` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_backup_20260611_033625/entities/Trade.json` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_backup_20260611_033625/eslint.config.js` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_backup_20260611_033625/index.html` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_backup_20260611_033625/jsconfig.json` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_backup_20260611_033625/package-lock.json` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_backup_20260611_033625/package.json` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_backup_20260611_033625/postcss.config.js` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_backup_20260611_033625/README.md` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_backup_20260611_033625/tailwind.config.js` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_backup_20260611_033625/vite.config.js` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_code_backup_20260611_084204/.env.local` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_code_backup_20260611_084204/.gitignore` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_code_backup_20260611_084204/components.json` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_code_backup_20260611_084204/entities/Candle.json` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_code_backup_20260611_084204/entities/MT5Connection.json` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_code_backup_20260611_084204/entities/Trade.json` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_code_backup_20260611_084204/eslint.config.js` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_code_backup_20260611_084204/index.html` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_code_backup_20260611_084204/jsconfig.json` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_code_backup_20260611_084204/package-lock.json` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_code_backup_20260611_084204/package.json` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_code_backup_20260611_084204/postcss.config.js` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_code_backup_20260611_084204/README.md` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_code_backup_20260611_084204/src/api/base44Client.js` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_code_backup_20260611_084204/src/App.jsx` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_code_backup_20260611_084204/src/components/AuthLayout.jsx` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_code_backup_20260611_084204/src/components/chart/CandleChart.jsx` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_code_backup_20260611_084204/src/components/chart/CandleRenderer.jsx` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| `_archive/backups/fusion-frontend_code_backup_20260611_084204/src/components/chart/ChartBuffer.jsx` | `arquivo_morto_legado` | `candidato_remocao_apos_revisao` |
| ... | mais 22844 arquivos no CSV | ... |

### `_external`

| Arquivo | Categoria | Acao |
|---|---|---|
| `_external/README.md` | `projeto_externo` | `candidato_remocao_apos_revisao` |

### `config`

| Arquivo | Categoria | Acao |
|---|---|---|
| `config/fusion_config.yaml` | `config_runtime` | `manter_com_cautela` |
| `config/fusion_config.yaml.bak_20260524_comments` | `config_runtime` | `manter_com_cautela` |
| `config/fusion_runtime_control.json` | `config_runtime` | `manter_com_cautela` |
| `config/fusion_runtime_control.json.bak_bottom_guard_20260611` | `config_runtime` | `manter_com_cautela` |
| `config/market_briefing_template.json` | `config_runtime` | `manter_com_cautela` |
| `config/market_briefing_today.json` | `config_runtime` | `manter_com_cautela` |

### `dashboard`

| Arquivo | Categoria | Acao |
|---|---|---|
| `dashboard/event_readers.py` | `painel_monitoramento` | `manter_se_usado` |
| `dashboard/fusion_dashboard.py` | `painel_monitoramento` | `manter_se_usado` |
| `dashboard/requirements.txt` | `painel_monitoramento` | `manter_se_usado` |
| `dashboard/run_dashboard.ps1` | `painel_monitoramento` | `manter_se_usado` |

### `data`

| Arquivo | Categoria | Acao |
|---|---|---|
| `data/candles_bin/M15/AUDCAD.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/AUDCHF.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/AUDJPY.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/AUDNOK.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/AUDNZD.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/AUDSEK.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/AUDSGD.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/AUDUSD.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/AUS200.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/BTCUSD.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/CADCHF.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/CADJPY.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/CHFDKK.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/CHFJPY.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/CHFNOK.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/CHFSGD.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/DOTUSD.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/ETHUSD.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/EURAUD.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/EURCAD.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/EURCHF.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/EURGBP.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/EURHKD.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/EURHUF.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/EURJPY.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/EURMXN.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/EURNOK.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/EURNZD.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/EURPLN.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/EURSEK.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/EURUSD.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/GBPAUD.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/GBPCAD.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/GBPCHF.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/GBPJPY.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/GBPNZD.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/GBPUSD.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/GOLD.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/NZDCAD.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| `data/candles_bin/M15/NZDCHF.bin` | `dados_modelos_treinamento` | `manter_se_usado` |
| ... | mais 1661 arquivos no CSV | ... |

### `docs`

| Arquivo | Categoria | Acao |
|---|---|---|
| `docs/arquitetura_institucional_fusion_v2.md` | `documentacao` | `manter_se_util` |
| `docs/comunicacao_mt5_backend_frontend.md` | `documentacao` | `manter_se_util` |
| `docs/FUSION_CICLO_OPERACIONAL.md` | `documentacao` | `manter_se_util` |
| `docs/market_briefing_macro_json.md` | `documentacao` | `manter_se_util` |
| `docs/melhorias_a_ser_implementadas.md` | `documentacao` | `manter_se_util` |
| `docs/model_integration_m5.md` | `documentacao` | `manter_se_util` |
| `docs/operacional/DIAGNOSTICO_STARTUP.md` | `documentacao` | `manter_se_util` |
| `docs/operacional/IMPLEMENTACAO_CACHE_FEATURES.md` | `documentacao` | `manter_se_util` |
| `docs/operacional/IMPLEMENTACAO_OTIMIZACAO_COMPLETA.md` | `documentacao` | `manter_se_util` |
| `docs/operacional/OTIMIZACAO_STARTUP.md` | `documentacao` | `manter_se_util` |
| `docs/operacional/OTIMIZACAO_TERMINAL_BRIDGE.md` | `documentacao` | `manter_se_util` |
| `docs/operacional/plan.md` | `documentacao` | `manter_se_util` |
| `docs/operacional/README.md` | `documentacao` | `manter_se_util` |
| `docs/ORGANIZACAO_PROJETO.md` | `documentacao` | `manter_se_util` |
| `docs/roadmap_analise_quant_ohlcv.md` | `documentacao` | `manter_se_util` |
| `docs/roadmap_backtest_real_fusion.md` | `documentacao` | `manter_se_util` |
| `docs/roadmap_context_brain_institucional.md` | `documentacao` | `manter_se_util` |
| `docs/roadmap_dashboard_trading_platform.md` | `documentacao` | `manter_se_util` |
| `docs/roadmap_event_driven_fusion_v2.md` | `documentacao` | `manter_se_util` |
| `docs/roadmap_news_impact_engine.md` | `documentacao` | `manter_se_util` |
| `docs/RUNTIME_FUSION_MAP.md` | `documentacao` | `manter_se_util` |
| `docs/strategy_bank_models_research.md` | `documentacao` | `manter_se_util` |

### `features`

| Arquivo | Categoria | Acao |
|---|---|---|
| `features/features_backteste_ativo_timeframe.csv` | `dados_modelos_treinamento` | `manter_se_usado` |
| `features/features_backteste_dinamica.csv` | `dados_modelos_treinamento` | `manter_se_usado` |
| `features/features_backteste_modelagem.csv` | `dados_modelos_treinamento` | `manter_se_usado` |

### `frontend`

| Arquivo | Categoria | Acao |
|---|---|---|
| `frontend/.gitignore` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/components.json` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/entities/Candles.json` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/entities/MT5Connection` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/entities/Trade.json` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/eslint.config.js` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/index.html` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/jsconfig.json` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/package.json` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/postcss.config.js` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/README.md` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/src/api/base44Client.js` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/src/App.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/src/components/AuthLayout.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/src/components/chart/CandleChart.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/src/components/chart/CandleRenderer.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/src/components/chart/ChartBuffer.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/src/components/chart/IndicatorConfig.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/src/components/fusion/FusionDiffViewer.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/src/components/fusion/FusionDraftBar.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/src/components/fusion/FusionFieldRenderers.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/src/components/fusion/FusionPresetBar.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/src/components/fusion/tabs/TabBroker.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/src/components/fusion/tabs/TabContratos.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/src/components/fusion/tabs/TabCurrencyStrength.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/src/components/fusion/tabs/TabDashboardLogs.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/src/components/fusion/tabs/TabFiltros.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/src/components/fusion/tabs/TabGeral.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/src/components/fusion/tabs/TabJsonEditor.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/src/components/fusion/tabs/TabModelos.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/src/components/fusion/tabs/TabMT5Panels.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/src/components/fusion/tabs/TabOMS.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/src/components/fusion/tabs/TabOTM.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/src/components/fusion/tabs/TabPolicies.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/src/components/fusion/tabs/TabRisco.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/src/components/fusion/tabs/TabSignalOverrides.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/src/components/fusion/tabs/TabSinais.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/src/components/fusion/tabs/TabStrategies.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/src/components/fusion/tabs/TabTrading.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `frontend/src/components/fusion/tabs/TabTrailing.jsx` | `painel_monitoramento` | `manter_se_usado` |
| ... | mais 109 arquivos no CSV | ... |

### `fusion`

| Arquivo | Categoria | Acao |
|---|---|---|
| `fusion/__init__.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/advisor/__init__.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/advisor/advisor_client.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/advisor/advisor_payloads.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/ai/__init__.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/ai/bridge.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/ai/reviewer.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/approved_ensembles.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/backtest/__init__.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/backtest/adapters.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/backtest/context.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/backtest/feature_replay_runner.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/backtest/features.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/backtest/market_data.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/backtest/model_replay.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/backtest/oms.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/backtest/replay.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/core/__init__.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/core/config.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/core/contracts.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/core/engine_registry.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/core/enums.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/core/event_logger.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/core/events.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/core/logger.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/core/objects.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/data/__init__.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/data/pipeline.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/decision/__init__.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/decision/audit.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/decision/explain.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/decision/orchestrator.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/decision/policy.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/decision/schema.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/engines/__init__.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/engines/ai_advisor.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/engines/calibration.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/engines/consensus.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/engines/context.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion/engines/context_brain.py` | `runtime_robo` | `manter_com_cautela` |
| ... | mais 85 arquivos no CSV | ... |

### `fusion-frontend`

| Arquivo | Categoria | Acao |
|---|---|---|
| `fusion-frontend/.env.local` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/.gitignore` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/components.json` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/dist/assets/index-B8BRX_IU.css` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/dist/assets/index-CLRBpcmB.js` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/dist/favicon.svg` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/dist/index.html` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/entities/Candle.json` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/entities/MT5Connection.json` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/entities/Trade.json` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/eslint.config.js` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/index.html` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/jsconfig.json` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/package-lock.json` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/package.json` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/postcss.config.js` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/public/favicon.svg` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/README.md` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/src/api/fusionLocalClient.js` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/src/App.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/src/components/AppErrorBoundary.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/src/components/AuthLayout.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/src/components/chart/CandleChart.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/src/components/chart/CandleRenderer.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/src/components/chart/ChartBuffer.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/src/components/chart/IndicatorConfig.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/src/components/fusion/FusionDiffViewer.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/src/components/fusion/FusionDraftBar.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/src/components/fusion/FusionFieldRenderers.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/src/components/fusion/FusionPresetBar.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/src/components/fusion/tabs/TabBroker.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/src/components/fusion/tabs/TabContratos.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/src/components/fusion/tabs/TabCurrencyStrength.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/src/components/fusion/tabs/TabDashboardLogs.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/src/components/fusion/tabs/TabFiltros.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/src/components/fusion/tabs/TabGeral.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/src/components/fusion/tabs/TabJsonEditor.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/src/components/fusion/tabs/TabModelos.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/src/components/fusion/tabs/TabMT5Panels.jsx` | `painel_monitoramento` | `manter_se_usado` |
| `fusion-frontend/src/components/fusion/tabs/TabOMS.jsx` | `painel_monitoramento` | `manter_se_usado` |
| ... | mais 117 arquivos no CSV | ... |

### `fusion_refatorado`

| Arquivo | Categoria | Acao |
|---|---|---|
| `fusion_refatorado/config/build_models_qlib_task_config.yaml` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/config/omnis_backup_config.py` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/config/omnis_legacy/model_config_v1.yaml` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/config/omnis_legacy/qlib_config.yaml` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/config/omnis_legacy/strategy_settings.yaml` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/config/omnis_legacy/symbols.yaml` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/data/backup_migrated/build_models_shards_v4/SHARD_CRYPTO_M15.parquet` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/data/backup_migrated/build_models_shards_v4/SHARD_CRYPTO_M30.parquet` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/data/backup_migrated/build_models_shards_v4/SHARD_CRYPTO_M5.parquet` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/data/backup_migrated/build_models_shards_v4/SHARD_EXOTICS_WORLD_M15.parquet` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/data/backup_migrated/build_models_shards_v4/SHARD_EXOTICS_WORLD_M30.parquet` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/data/backup_migrated/build_models_shards_v4/SHARD_EXOTICS_WORLD_M5.parquet` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/data/backup_migrated/build_models_shards_v4/SHARD_FOREX_CROSSES_M15.parquet` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/data/backup_migrated/build_models_shards_v4/SHARD_FOREX_CROSSES_M30.parquet` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/data/backup_migrated/build_models_shards_v4/SHARD_FOREX_CROSSES_M5.parquet` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/data/backup_migrated/build_models_shards_v4/SHARD_FOREX_MAJORS_M15.parquet` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/data/backup_migrated/build_models_shards_v4/SHARD_FOREX_MAJORS_M30.parquet` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/data/backup_migrated/build_models_shards_v4/SHARD_FOREX_MAJORS_M5.parquet` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/data/backup_migrated/build_models_shards_v4/SHARD_INDEXES_M15.parquet` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/data/backup_migrated/build_models_shards_v4/SHARD_INDEXES_M30.parquet` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/data/backup_migrated/build_models_shards_v4/SHARD_INDEXES_M5.parquet` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/data/backup_migrated/build_models_shards_v4/SHARD_METALS_ELITE_M15.parquet` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/data/backup_migrated/build_models_shards_v4/SHARD_METALS_ELITE_M30.parquet` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/data/backup_migrated/build_models_shards_v4/SHARD_METALS_ELITE_M5.parquet` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/data/backup_migrated/build_models_shards_v4/SHARD_OTHERS_M15.parquet` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/data/backup_migrated/build_models_shards_v4/SHARD_OTHERS_M30.parquet` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/data/backup_migrated/build_models_shards_v4/SHARD_OTHERS_M5.parquet` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/data/backup_migrated/data_csv_full/D1/ADAUSD.csv` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/data/backup_migrated/data_csv_full/D1/AEDCNH.csv` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/data/backup_migrated/data_csv_full/D1/AEDCZK.csv` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/data/backup_migrated/data_csv_full/D1/AEDHKD.csv` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/data/backup_migrated/data_csv_full/D1/AEDHUF.csv` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/data/backup_migrated/data_csv_full/D1/AEDJPY.csv` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/data/backup_migrated/data_csv_full/D1/AEDMXN.csv` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/data/backup_migrated/data_csv_full/D1/AEDRON.csv` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/data/backup_migrated/data_csv_full/D1/AEDSAR.csv` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/data/backup_migrated/data_csv_full/D1/AEDTHB.csv` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/data/backup_migrated/data_csv_full/D1/AEDTRY.csv` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/data/backup_migrated/data_csv_full/D1/AEDZAR.csv` | `runtime_robo` | `manter_com_cautela` |
| `fusion_refatorado/data/backup_migrated/data_csv_full/D1/AUDAED.csv` | `runtime_robo` | `manter_com_cautela` |
| ... | mais 11531 arquivos no CSV | ... |

### `logs`

| Arquivo | Categoria | Acao |
|---|---|---|
| `logs/ai_reviews/ai_reviews_20260521_122836.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/ai_reviews/ai_reviews_20260521_122836.md` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/decision_audit/decision_audit_20260521.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/decision_audit/decision_audit_20260522.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/decision_audit/decision_audit_20260524.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/decision_audit/decision_audit_20260525.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/decision_audit/decision_audit_20260526.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/decision_audit/decision_audit_20260527.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/decision_audit/decision_audit_20260528.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/decision_audit/decision_audit_20260529.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/decision_audit/decision_audit_20260531.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/decision_audit/decision_audit_20260601.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/decision_audit/decision_audit_20260602.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/decision_audit/decision_audit_20260603.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/decision_audit/decision_audit_20260604.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/decision_audit/decision_audit_20260605.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/decision_audit/decision_audit_20260608.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/decision_audit/decision_audit_20260609.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/decision_audit/decision_audit_20260610.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/decision_audit/decision_audit_20260611.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/decision_audit/decision_audit_20260612.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/decision_audit/decision_audit_20260617.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/decision_audit/decision_audit_20260707.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/decision_audit/decision_audit_20260708.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/decision_audit_smoke/decision_audit_20260521.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/events/events_20260522.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/events/events_20260524.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/events/events_20260525.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/events/events_20260526.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/events/events_20260527.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/events/events_20260528.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/events/events_20260529.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/events/events_20260531.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/events/events_20260601.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/events/events_20260602.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/events/events_20260603.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/events/events_20260604.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/events/events_20260605.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/events/events_20260608.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| `logs/events/events_20260609.jsonl` | `logs` | `pode_limpar_com_robo_parado` |
| ... | mais 209 arquivos no CSV | ... |

### `models`

| Arquivo | Categoria | Acao |
|---|---|---|
| `models/AUDCAD/D1/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDCAD/D1/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDCAD/D1/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDCAD/H1/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDCAD/H1/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDCAD/H1/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDCAD/H4/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDCAD/H4/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDCAD/H4/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDCAD/M15/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDCAD/M15/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDCAD/M15/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDCAD/M30/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDCAD/M30/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDCAD/M30/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDCAD/M5/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDCAD/M5/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDCAD/M5/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDCHF/D1/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDCHF/D1/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDCHF/D1/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDCHF/H1/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDCHF/H1/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDCHF/H1/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDCHF/H4/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDCHF/H4/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDCHF/H4/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDCHF/M15/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDCHF/M15/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDCHF/M15/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDCHF/M30/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDCHF/M30/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDCHF/M30/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDCHF/M5/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDCHF/M5/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDCHF/M5/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDJPY/D1/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDJPY/D1/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDJPY/D1/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models/AUDJPY/H1/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| ... | mais 393 arquivos no CSV | ... |

### `models_experts`

| Arquivo | Categoria | Acao |
|---|---|---|
| `models_experts/AUDCAD/D1/candles/candles_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/D1/candles/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/D1/orderflow/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/D1/orderflow/orderflow_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/D1/pullback/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/D1/pullback/pullback_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/D1/quant/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/D1/quant/quant_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/D1/reversal/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/D1/reversal/reversal_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/D1/risk/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/D1/risk/risk_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/D1/sr/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/D1/sr/sr_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/D1/training_report.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/D1/trend/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/D1/trend/trend_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/D1/volatility/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/D1/volatility/volatility_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/H1/candles/candles_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/H1/candles/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/H1/orderflow/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/H1/orderflow/orderflow_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/H1/pullback/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/H1/pullback/pullback_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/H1/quant/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/H1/quant/quant_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/H1/reversal/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/H1/reversal/reversal_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/H1/risk/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/H1/risk/risk_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/H1/sr/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/H1/sr/sr_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/H1/training_report.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/H1/trend/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/H1/trend/trend_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/H1/volatility/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/H1/volatility/volatility_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/H4/candles/candles_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts/AUDCAD/H4/candles/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| ... | mais 1918 arquivos no CSV | ... |

### `models_experts_v2`

| Arquivo | Categoria | Acao |
|---|---|---|
| `models_experts_v2/AUDCAD/D1/advanced_volatility/advanced_volatility_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/advanced_volatility/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/anomaly_regime/anomaly_regime_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/anomaly_regime/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/candles/candles_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/candles/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/exhaustion/exhaustion_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/exhaustion/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/fibonacci/fibonacci_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/fibonacci/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/gap_structure/gap_structure_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/gap_structure/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/ichimoku/ichimoku_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/ichimoku/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/market_phase/market_phase_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/market_phase/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/microstructure/microstructure_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/microstructure/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/momentum_accel/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/momentum_accel/momentum_accel_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/orderflow/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/orderflow/orderflow_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/pullback/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/pullback/pullback_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/quant/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/quant/quant_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/quant_regime/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/quant_regime/quant_regime_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/reversal/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/reversal/reversal_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/risk/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/risk/risk_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/session/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/session/session_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/signal_zone/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/signal_zone/signal_zone_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/spread/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/spread/spread_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/sr/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_experts_v2/AUDCAD/D1/sr/sr_metadata.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| ... | mais 14589 arquivos no CSV | ... |

### `models_expr`

| Arquivo | Categoria | Acao |
|---|---|---|
| `models_expr/AUDCAD/D1/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDCAD/D1/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDCAD/D1/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDCAD/H1/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDCAD/H1/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDCAD/H1/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDCAD/H4/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDCAD/H4/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDCAD/H4/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDCAD/M15/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDCAD/M15/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDCAD/M15/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDCAD/M30/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDCAD/M30/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDCAD/M30/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDCAD/M5/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDCAD/M5/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDCAD/M5/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDCHF/D1/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDCHF/D1/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDCHF/D1/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDCHF/H1/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDCHF/H1/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDCHF/H1/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDCHF/H4/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDCHF/H4/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDCHF/H4/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDCHF/M15/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDCHF/M15/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDCHF/M15/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDCHF/M30/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDCHF/M30/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDCHF/M30/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDCHF/M5/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDCHF/M5/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDCHF/M5/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDJPY/D1/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDJPY/D1/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDJPY/D1/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_expr/AUDJPY/H1/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| ... | mais 375 arquivos no CSV | ... |

### `models_principal`

| Arquivo | Categoria | Acao |
|---|---|---|
| `models_principal/AUDCAD/D1/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDCAD/D1/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDCAD/D1/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDCAD/H1/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDCAD/H1/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDCAD/H1/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDCAD/H4/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDCAD/H4/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDCAD/H4/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDCAD/M15/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDCAD/M15/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDCAD/M15/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDCAD/M30/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDCAD/M30/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDCAD/M30/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDCAD/M5/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDCAD/M5/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDCAD/M5/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDCHF/D1/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDCHF/D1/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDCHF/D1/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDCHF/H1/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDCHF/H1/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDCHF/H1/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDCHF/H4/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDCHF/H4/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDCHF/H4/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDCHF/M15/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDCHF/M15/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDCHF/M15/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDCHF/M30/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDCHF/M30/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDCHF/M30/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDCHF/M5/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDCHF/M5/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDCHF/M5/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDJPY/D1/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDJPY/D1/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDJPY/D1/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_principal/AUDJPY/H1/meta.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| ... | mais 394 arquivos no CSV | ... |

### `models_research`

| Arquivo | Categoria | Acao |
|---|---|---|
| `models_research/AUDCAD/D1/catboost/isotonic/calibrator.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/D1/catboost/isotonic/meta.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/D1/catboost/isotonic/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/D1/catboost/isotonic/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/D1/catboost/logistic/calibrator.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/D1/catboost/logistic/meta.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/D1/catboost/logistic/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/D1/catboost/logistic/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/D1/catboost/raw/meta.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/D1/catboost/raw/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/D1/catboost/raw/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/D1/catboost/regime_hmm.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/D1/lightgbm/isotonic/calibrator.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/D1/lightgbm/isotonic/meta.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/D1/lightgbm/isotonic/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/D1/lightgbm/isotonic/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/D1/lightgbm/logistic/calibrator.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/D1/lightgbm/logistic/meta.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/D1/lightgbm/logistic/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/D1/lightgbm/logistic/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/D1/lightgbm/raw/meta.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/D1/lightgbm/raw/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/D1/lightgbm/raw/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/D1/lightgbm/regime_hmm.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/H1/catboost/isotonic/calibrator.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/H1/catboost/isotonic/meta.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/H1/catboost/isotonic/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/H1/catboost/isotonic/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/H1/catboost/logistic/calibrator.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/H1/catboost/logistic/meta.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/H1/catboost/logistic/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/H1/catboost/logistic/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/H1/catboost/raw/meta.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/H1/catboost/raw/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/H1/catboost/raw/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/H1/catboost/regime_hmm.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/H1/lightgbm/isotonic/calibrator.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/H1/lightgbm/isotonic/meta.json` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/H1/lightgbm/isotonic/model.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| `models_research/AUDCAD/H1/lightgbm/isotonic/scaler.pkl` | `dados_modelos_treinamento` | `manter_se_usado` |
| ... | mais 6329 arquivos no CSV | ... |

### `mql5`

| Arquivo | Categoria | Acao |
|---|---|---|
| `mql5/Experts/FusionMt5Bridge.ex5` | `runtime_robo` | `manter_com_cautela` |
| `mql5/Experts/FusionMt5Bridge.mq5` | `runtime_robo` | `manter_com_cautela` |
| `mql5/Indicators/FusionDecisionLayers.mq5` | `runtime_robo` | `manter_com_cautela` |
| `mql5/Indicators/FusionSignalPanel.mq5` | `runtime_robo` | `manter_com_cautela` |
| `mql5/Indicators/FusionTradeZones.mq5` | `runtime_robo` | `manter_com_cautela` |

### `package-lock.json`

| Arquivo | Categoria | Acao |
|---|---|---|
| `package-lock.json` | `ambiente_frontend` | `revisar` |

### `package.json`

| Arquivo | Categoria | Acao |
|---|---|---|
| `package.json` | `ambiente_frontend` | `revisar` |

### `reports`

| Arquivo | Categoria | Acao |
|---|---|---|
| `reports/asset_history_audit/asset_history_model_audit_20260525_111313.csv` | `analise_relatorio` | `manter_se_util` |
| `reports/asset_history_audit/asset_history_model_audit_20260525_111344.csv` | `analise_relatorio` | `manter_se_util` |
| `reports/asset_history_audit/asset_history_model_audit_20260525_112149.csv` | `analise_relatorio` | `manter_se_util` |
| `reports/asset_history_audit/asset_history_model_audit_20260525_112207.csv` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/backteste_rapido_dinamica_entradas.csv` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/backteste_rapido_resultados.csv` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/backteste_rapido_resumo.csv` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/backteste_resumo_por_ativo.csv` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/backteste_resumo_por_ativo.md` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/cache/AUDCAD_D1_y2_t100-200-300-400-500_l1000/by_side.csv` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/cache/AUDCAD_D1_y2_t100-200-300-400-500_l1000/by_symbol_tf.csv` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/cache/AUDCAD_D1_y2_t100-200-300-400-500_l1000/grouped.csv` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/cache/AUDCAD_D1_y2_t100-200-300-400-500_l1000/meta.json` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/cache/AUDCAD_D1_y2_t100-200-300-400-500_l1000/prev_candle.csv` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/cache/AUDCAD_H1_y2_t100-200-300-400-500_l1000/by_side.csv` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/cache/AUDCAD_H1_y2_t100-200-300-400-500_l1000/by_symbol_tf.csv` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/cache/AUDCAD_H1_y2_t100-200-300-400-500_l1000/grouped.csv` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/cache/AUDCAD_H1_y2_t100-200-300-400-500_l1000/meta.json` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/cache/AUDCAD_H1_y2_t100-200-300-400-500_l1000/prev_candle.csv` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/cache/AUDCAD_H4_y2_t100-200-300-400-500_l1000/by_side.csv` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/cache/AUDCAD_H4_y2_t100-200-300-400-500_l1000/by_symbol_tf.csv` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/cache/AUDCAD_H4_y2_t100-200-300-400-500_l1000/grouped.csv` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/cache/AUDCAD_H4_y2_t100-200-300-400-500_l1000/meta.json` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/cache/AUDCAD_H4_y2_t100-200-300-400-500_l1000/prev_candle.csv` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/cache/AUDCAD_M15_y2_t100-200-300-400-500_l1000/by_side.csv` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/cache/AUDCAD_M15_y2_t100-200-300-400-500_l1000/by_symbol_tf.csv` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/cache/AUDCAD_M15_y2_t100-200-300-400-500_l1000/grouped.csv` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/cache/AUDCAD_M15_y2_t100-200-300-400-500_l1000/meta.json` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/cache/AUDCAD_M15_y2_t100-200-300-400-500_l1000/prev_candle.csv` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/cache/AUDCAD_M30_y2_t100-200-300-400-500_l1000/by_side.csv` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/cache/AUDCAD_M30_y2_t100-200-300-400-500_l1000/by_symbol_tf.csv` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/cache/AUDCAD_M30_y2_t100-200-300-400-500_l1000/grouped.csv` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/cache/AUDCAD_M30_y2_t100-200-300-400-500_l1000/meta.json` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/cache/AUDCAD_M30_y2_t100-200-300-400-500_l1000/prev_candle.csv` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/cache/AUDCAD_M5_y2_t100-200-300-400-500_l1000/by_side.csv` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/cache/AUDCAD_M5_y2_t100-200-300-400-500_l1000/by_symbol_tf.csv` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/cache/AUDCAD_M5_y2_t100-200-300-400-500_l1000/grouped.csv` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/cache/AUDCAD_M5_y2_t100-200-300-400-500_l1000/meta.json` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/cache/AUDCAD_M5_y2_t100-200-300-400-500_l1000/prev_candle.csv` | `analise_relatorio` | `manter_se_util` |
| `reports/backtests/cache/AUDCHF_D1_y2_t100-200-300-400-500_l1000/by_side.csv` | `analise_relatorio` | `manter_se_util` |
| ... | mais 2417 arquivos no CSV | ... |

### `requirements.txt`

| Arquivo | Categoria | Acao |
|---|---|---|
| `requirements.txt` | `runtime_entrypoint` | `manter` |

### `run_fusion.py`

| Arquivo | Categoria | Acao |
|---|---|---|
| `run_fusion.py` | `runtime_entrypoint` | `manter` |

### `runtime`

| Arquivo | Categoria | Acao |
|---|---|---|
| `runtime/market_data/latest_candles/AUDCAD_D1.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDCAD_H1.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDCAD_H4.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDCAD_M15.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDCAD_M30.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDCAD_M5.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDCHF_D1.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDCHF_H1.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDCHF_H4.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDCHF_M15.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDCHF_M30.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDCHF_M5.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDJPY_D1.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDJPY_H1.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDJPY_H4.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDJPY_M15.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDJPY_M30.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDJPY_M5.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDNOK_D1.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDNOK_H1.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDNOK_H4.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDNOK_M15.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDNOK_M30.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDNOK_M5.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDNZD_D1.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDNZD_H1.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDNZD_H4.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDNZD_M15.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDNZD_M30.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDNZD_M5.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDSEK_D1.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDSEK_H1.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDSEK_H4.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDSEK_M15.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDSEK_M30.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDSEK_M5.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDSGD_D1.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDSGD_H1.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDSGD_H4.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| `runtime/market_data/latest_candles/AUDSGD_M15.json` | `estado_runtime` | `nao_deletar_com_robo_rodando` |
| ... | mais 268 arquivos no CSV | ... |

### `rustup-init.exe`

| Arquivo | Categoria | Acao |
|---|---|---|
| `rustup-init.exe` | `instalador_local` | `candidato_remocao` |

### `terminal_desktop`

| Arquivo | Categoria | Acao |
|---|---|---|
| `terminal_desktop/fusion_terminal_desktop.py` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_desktop/run_terminal_desktop.ps1` | `painel_monitoramento` | `manter_se_usado` |

### `terminal_qt`

| Arquivo | Categoria | Acao |
|---|---|---|
| `terminal_qt/candle_chart.py` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_qt/chart_axes.py` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_qt/fusion_terminal_qt.py` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_qt/institutional_layers.py` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_qt/market_data.py` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_qt/period_backtest_engine.py` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_qt/probability_events.py` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_qt/run_candle_chart.ps1` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_qt/run_terminal_qt.ps1` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_qt/runtime_utils.py` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_qt/simulation_engine.py` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_qt/terminal_state.py` | `painel_monitoramento` | `manter_se_usado` |

### `terminal_windows`

| Arquivo | Categoria | Acao |
|---|---|---|
| `terminal_windows/bin_check/FusionTerminalWindows.deps.json` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_windows/bin_check/FusionTerminalWindows.dll` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_windows/bin_check/FusionTerminalWindows.pdb` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_windows/bin_check/FusionTerminalWindows.runtimeconfig.json` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_windows/Chart/CandleChartControl.cs` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_windows/Data/BacktestTradeLoader.cs` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_windows/Data/CandleFilters.cs` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_windows/Data/CsvCandleLoader.cs` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_windows/Data/OperationalStatusLoader.cs` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_windows/Data/SignalEventLoader.cs` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_windows/Data/TerminalSnapshotLoader.cs` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_windows/FusionTerminalWindows.csproj` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_windows/MainForm.cs` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_windows/Models/BacktestTrade.cs` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_windows/Models/Candle.cs` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_windows/Models/OperationalStatus.cs` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_windows/Models/SelectedSignal.cs` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_windows/Models/SignalMarker.cs` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_windows/Models/SimulatedOrder.cs` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_windows/Models/SimulationSettings.cs` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_windows/Program.cs` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_windows/README.md` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_windows/run_terminal_windows.ps1` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_windows/Theme/TerminalTheme.cs` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_windows/Widgets/BacktestPanel.cs` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_windows/Widgets/EventTablePanel.cs` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_windows/Widgets/ModulePlaceholder.cs` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_windows/Widgets/OperationalMatrixPanel.cs` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_windows/Widgets/ProbabilityPanel.cs` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_windows/Widgets/SimulationPanel.cs` | `painel_monitoramento` | `manter_se_usado` |
| `terminal_windows/Widgets/TechnicalAnalysisPanel.cs` | `painel_monitoramento` | `manter_se_usado` |

### `tools`

| Arquivo | Categoria | Acao |
|---|---|---|
| `tools/analise_probs.py` | `ferramenta_nao_classificada` | `revisar` |
| `tools/analysis_legacy/extract_predictions.py` | `ferramenta_analise_teste` | `manter_se_usado` |
| `tools/analysis_legacy/README.md` | `ferramenta_analise_teste` | `manter_se_usado` |
| `tools/analysis_legacy/table_predictions.py` | `ferramenta_analise_teste` | `manter_se_usado` |
| `tools/analyze_block_quality_since_20260529.py` | `ferramenta_analise_teste` | `manter_se_usado` |
| `tools/analyze_blocked_signals.py` | `ferramenta_analise_teste` | `manter_se_usado` |
| `tools/analyze_event_performance.py` | `ferramenta_analise_teste` | `manter_se_usado` |
| `tools/analyze_market_structure_shadow_outcomes.py` | `ferramenta_analise_teste` | `manter_se_usado` |
| `tools/analyze_signal_inversion.py` | `ferramenta_analise_teste` | `manter_se_usado` |
| `tools/analyze_signal_outcomes.py` | `ferramenta_analise_teste` | `manter_se_usado` |
| `tools/analyze_signal_path_outcomes.py` | `ferramenta_analise_teste` | `manter_se_usado` |
| `tools/audit_and_fetch_mt5_assets.py` | `ferramenta_runtime_bridge` | `manter_com_cautela` |
| `tools/backfill_events_from_decision_audit.py` | `ferramenta_nao_classificada` | `revisar` |
| `tools/backtest_insidebar_gold.py` | `ferramenta_analise_teste` | `manter_se_usado` |
| `tools/backtest_strategy_bank.py` | `ferramenta_analise_teste` | `manter_se_usado` |
| `tools/backteste_rapido.py` | `ferramenta_analise_teste` | `manter_se_usado` |
| `tools/build_asset_correlations.py` | `ferramenta_nao_classificada` | `revisar` |
| `tools/build_confidence_calibration_profiles.py` | `ferramenta_nao_classificada` | `revisar` |
| `tools/build_event_bus_report.py` | `ferramenta_analise_teste` | `manter_se_usado` |
| `tools/build_market_structure_calibration.py` | `ferramenta_nao_classificada` | `revisar` |
| `tools/build_market_structure_labels_and_ranking.py` | `ferramenta_nao_classificada` | `revisar` |
| `tools/build_operational_day_report.py` | `ferramenta_analise_teste` | `manter_se_usado` |
| `tools/build_operational_target_matrix.py` | `ferramenta_nao_classificada` | `revisar` |
| `tools/build_portfolio_risk_map.py` | `ferramenta_nao_classificada` | `revisar` |
| `tools/build_shadow_engine_report.py` | `ferramenta_analise_teste` | `manter_se_usado` |
| `tools/check_ai_advisor_payload.py` | `ferramenta_analise_teste` | `manter_se_usado` |
| `tools/check_ai_bridge.py` | `ferramenta_analise_teste` | `manter_se_usado` |
| `tools/check_confidence_calibration.py` | `ferramenta_analise_teste` | `manter_se_usado` |
| `tools/check_consensus_engine.py` | `ferramenta_analise_teste` | `manter_se_usado` |
| `tools/check_context_engine.py` | `ferramenta_analise_teste` | `manter_se_usado` |
| `tools/check_dashboard_data.py` | `ferramenta_analise_teste` | `manter_se_usado` |
| `tools/check_entry_timing.py` | `ferramenta_analise_teste` | `manter_se_usado` |
| `tools/check_event_bus_async.py` | `ferramenta_analise_teste` | `manter_se_usado` |
| `tools/check_event_bus_integrity.py` | `ferramenta_analise_teste` | `manter_se_usado` |
| `tools/check_event_bus_runtime_health.py` | `ferramenta_analise_teste` | `manter_se_usado` |
| `tools/check_execution_engine.py` | `ferramenta_analise_teste` | `manter_se_usado` |
| `tools/check_feature_engineering.py` | `ferramenta_analise_teste` | `manter_se_usado` |
| `tools/check_gold_trailing.py` | `ferramenta_analise_teste` | `manter_se_usado` |
| `tools/check_macro_flow.py` | `ferramenta_analise_teste` | `manter_se_usado` |
| `tools/check_market_briefing.py` | `ferramenta_analise_teste` | `manter_se_usado` |
| ... | mais 52 arquivos no CSV | ... |

## Diretorios ignorados por serem ambiente/cache

- `.venv/`
- `_archive\backups\fusion-frontend_backup_20260611_033625\node_modules/`
- `_archive\backups\pre_model_integration_20260519_101004\fusion\__pycache__/`
- `_archive\backups\pre_model_integration_20260519_101004\fusion\core\__pycache__/`
- `_archive\backups\pre_model_integration_20260519_101004\fusion\data\__pycache__/`
- `_archive\backups\pre_model_integration_20260519_101004\fusion\execution\__pycache__/`
- `_archive\backups\pre_model_integration_20260519_101004\fusion\features\__pycache__/`
- `_archive\backups\pre_model_integration_20260519_101004\fusion\features\expressions\__pycache__/`
- `_archive\backups\pre_model_integration_20260519_101004\fusion\features\expressions\operators\__pycache__/`
- `_archive\backups\pre_model_integration_20260519_101004\fusion\models\__pycache__/`
- `_archive\fusion_pro\apps\fusion_terminal_institutional\node_modules/`
- `_archive\fusion_pro\crates\fusion_renderer\src\bin/`
- `_archive\fusion_pro\dist\fusion_pro\bin/`
- `_archive\repositorio\FinRL-master\FinRL-master\docker\bin/`
- `_archive\repositorio\fx_analytics-main\fx_analytics\__pycache__/`
- `_archive\repositorio\vnpy-master\.venv/`
- `_archive\repositorio\vnpy-master\__pycache__/`
- `_archive\repositorio\vnpy-master\vnpy\__pycache__/`
- `_archive\repositorio\vnpy-master\vnpy\chart\__pycache__/`
- `_archive\repositorio\vnpy-master\vnpy\event\__pycache__/`
- `_archive\repositorio\vnpy-master\vnpy\rpc\__pycache__/`
- `_archive\repositorio\vnpy-master\vnpy\trader\__pycache__/`
- `_archive\repositorio\vnpy-master\vnpy\trader\locale\__pycache__/`
- `_archive\repositorio\vnpy-master\vnpy\trader\ui\__pycache__/`
- `dashboard\__pycache__/`
- `fusion-frontend\node_modules/`
- `fusion\__pycache__/`
- `fusion\advisor\__pycache__/`
- `fusion\ai\__pycache__/`
- `fusion\backtest\__pycache__/`
- `fusion\core\__pycache__/`
- `fusion\data\__pycache__/`
- `fusion\decision\__pycache__/`
- `fusion\engines\__pycache__/`
- `fusion\execution\__pycache__/`
- `fusion\features\__pycache__/`
- `fusion\features\expressions\__pycache__/`
- `fusion\features\expressions\operators\__pycache__/`
- `fusion\models\__pycache__/`
- `fusion\strategies\__pycache__/`
- `fusion\strategy_bank\__pycache__/`
- `fusion\strategy_bank\asset_strategies\__pycache__/`
- `fusion_refatorado\fusion_best\__pycache__/`
- `fusion_refatorado\pipelines\__pycache__/`
- `node_modules/`
- `reports\project_inventory\__pycache__/`
- `reports\risk_drawdown\__pycache__/`
- `terminal_desktop\__pycache__/`
- `terminal_qt\__pycache__/`
- `terminal_windows\bin/`
- `terminal_windows\obj/`
- `tools\__pycache__/`
