# FUSION_V2

Sistema de trading algorítmico com integração MT5, motores de decisão, filtros de risco, execução automática, trailing, painéis de controle e pipeline de pesquisa/treinamento.

Este repositório foi organizado para separar claramente:

- runtime do robô;
- configurações operacionais;
- painéis e APIs auxiliares;
- dados e modelos;
- análises, relatórios e backtests;
- pesquisa/experimentos;
- arquivos legados e projetos externos.

## Aviso Operacional

Este projeto abre ordens no MetaTrader 5 quando `allow_new_orders=true` e `execution_mode=automatic`. Use conta demo para validação. Antes de rodar em conta real, revise limites, lote, SL/TP, filtros, exposição e estado do MT5.

Configuração operacional atual relevante:

- `trading.allow_new_orders`: `true`
- `trading.execution_mode`: `automatic`
- `trading.max_positions_per_symbol`: `1`
- regra de posição: 1 ordem por ativo, em qualquer direção e em qualquer estratégia
- lote fixado pelo config em `min_lot=0.01` e `max_lot=0.01`
- `trailing.enabled`: `true`
- `manual_approval.enabled`: `false`

## Execução Rápida

### 1. Abrir MT5

1. Abra o MetaTrader 5.
2. Faça login na conta demo/operacional correta.
3. Confirme que o terminal está conectado.
4. Confirme que o Algo Trading/AutoTrading está liberado quando for testar execução automática.

### 2. Rodar o robô Fusion

Na raiz do projeto:

```powershell
cd E:\Eduardo\PROJETOS_PYTHON\FUSION_V2
.\.venv\Scripts\python.exe run_fusion.py
```

Entrada principal:

- `run_fusion.py`: adiciona a raiz ao `sys.path`, importa `fusion.main.FusionV2` e chama `FusionV2().run()`.

### 3. Abrir painel Windows

```powershell
cd E:\Eduardo\PROJETOS_PYTHON\FUSION_V2
.\terminal_windows\run_terminal_windows.ps1
```

Esse script:

- localiza o `.NET`;
- usa `.venv\Scripts\python.exe` ou `venv\Scripts\python.exe`;
- inicia o bridge MT5 de candles, salvo se usado `-NoMt5Bridge`;
- roda `terminal_windows/FusionTerminalWindows.csproj`.

Parâmetros úteis:

```powershell
.\terminal_windows\run_terminal_windows.ps1 -BridgeIntervalSeconds 1 -BridgeBars 200
.\terminal_windows\run_terminal_windows.ps1 -NoMt5Bridge
```

### 4. Subir bridge de candles manualmente

Se abrir o `.exe` do painel direto, o bridge não sobe automaticamente. Para sincronizar candles MT5 -> painel:

```powershell
.\.venv\Scripts\python.exe tools\export_mt5_candles_for_terminal.py --timeframes M5,M15,M30,H1,H4,D1 --bars 200 --interval 1
```

Saída dos candles:

- `runtime/market_data/latest_candles/*.json`

### 5. Frontend/API auxiliar

Scripts relacionados:

```powershell
.\tools\open_fusion_frontend_app.ps1
.\tools\manage_mt5_live_api.ps1
.\.venv\Scripts\python.exe tools\mt5_live_api.py
.\.venv\Scripts\python.exe tools\fusion_frontend_data.py
```

Consulte também os documentos em `docs/` para guias específicos.

## Estrutura Atual da Raiz

| Item | Tipo | Função | Pode mover? |
|---|---|---|---|
| `.venv/` | ambiente | ambiente Python local | não é runtime lógico, mas necessário localmente |
| `.vscode/` | IDE | configurações do VS Code | sim, mas normalmente fica na raiz |
| `02_research/` | pesquisa | experts/experimentos separados do runtime | sim |
| `_archive/` | arquivo morto | backups e versões antigas | sim |
| `_external/` | externo | projetos externos/integracoes isoladas | sim |
| `config/` | runtime | YAML/JSON de configuração operacional | não mover sem atualizar paths |
| `dashboard/` | painel | dashboard legado/apoio | pode reorganizar depois |
| `data/` | dados | dados/parquet/cache usados por treino e alguns fluxos runtime | não mover sem atualizar config |
| `docs/` | documentação | guias, arquitetura, planos e diagnósticos | pode reorganizar internamente |
| `features/` | dados/features | features para treino/backtest/estratégias | não mover sem atualizar config |
| `frontend/` | painel web | frontend web auxiliar | pode reorganizar depois |
| `fusion/` | runtime | código principal do robô | não mover |
| `fusion-frontend/` | painel web | frontend web alternativo/novo | pode reorganizar depois |
| `fusion_refatorado/` | runtime dependência | ensembles M5, feature builder e registry usados pelo Fusion | não mover ainda |
| `logs/` | runtime | logs vivos do robô e bridges | não mover sem atualizar config |
| `models*/` | modelos | modelos treinados/candidatos | não mover sem atualizar config |
| `mql5/` | integração | arquivos/integração MQL5 | não mover sem atualizar fluxo MT5 |
| `node_modules/` | ambiente JS | dependências JS da raiz/frontend | pode limpar/reinstalar com cuidado |
| `reports/` | análise | backtests, auditorias, inventários e saídas | pode reorganizar internamente |
| `runtime/` | runtime | estado vivo, snapshots e candles | não mover sem atualizar código |
| `terminal_*` | painéis | terminais/painéis desktop/Qt/Windows | pode reorganizar depois com ajustes de paths |
| `tools/` | ferramentas | scripts de análise, treino, bridge, API e manutenção | reorganizar com wrappers |
| `README.md` | documentação | este manual | manter na raiz |
| `requirements.txt` | runtime | dependências Python | manter na raiz |
| `run_fusion.py` | runtime | entrypoint principal | manter na raiz |

Invent?rio detalhado:

- `reports/project_inventory/root_inventory.md`
- `reports/project_inventory/root_inventory.csv`
- `reports/project_inventory/detailed_file_inventory.md`
- `reports/project_inventory/detailed_file_inventory.csv`
- `reports/project_inventory/phase1_migration_log.md`

O README explica a arquitetura, execu??o, configura??o e fun??o das ?reas do sistema. A lista arquivo por arquivo fica no invent?rio detalhado em CSV/Markdown, porque o projeto tem dezenas de milhares de arquivos quando considerados dados, modelos, relat?rios e integra??es. Use o CSV para decidir limpeza por `recommended_action`, `category` e `path`.

## Configurações Principais

### `config/fusion_config.yaml`

Arquivo principal do sistema. Controla risco, símbolos, estratégias, filtros, modelos, trailing, logging e integração MT5.

Seções importantes:

- `risk`: lote, risco por trade, perda diária, limite de posições e SL padrão.
- `trading`: abertura de ordens, modo automático/manual, cooldown, guardas de perda e limite por ativo.
- `entry_filters`: motores de filtro antes da ordem.
- `strategies`: parâmetros das estratégias 1 a 6.
- `trailing`: trailing stop global e overrides por símbolo.
- `market_data`: diretórios de dados e mapeamento de símbolos.
- `model`: diretório e arquivos do modelo global.
- `logging`: nível e pasta de logs.
- `mt5_signal_panel`: export do painel de sinais para MT5/Common Files.
- `mt5_trade_zones`: zonas de trade para MT5.
- `mt5_decision_layers`: camadas de decisão exportadas para MT5.
- `symbols`: ativos monitorados pelo robô.

Pontos críticos atuais:

```yaml
risk:
  max_risk_per_trade: 0.25
  max_positions: 1
  min_lot: 0.01
  max_lot: 0.01

trading:
  allow_new_orders: true
  execution_mode: automatic
  position_limits:
    enabled: true
    scope: system
    max_per_symbol: 1
    mode: any_direction

model:
  model_dir: ./models_research

market_data:
  data_dir: ./data
  parquet_dir: ./data/parquet

logging:
  log_dir: ./logs
```

### `config/fusion_runtime_control.json`

Controle runtime lido sem reiniciar o Fusion para ajustes operacionais.

Uso típico:

- bloquear/liberar novas ordens;
- alterar thresholds de sinal;
- ligar/desligar trailing;
- ajustar TP/SL runtime;
- controlar símbolo específico em `risk_by_symbol`.

Campos importantes:

- `enabled`
- `trading.allow_new_orders`
- `trading.execution_mode`
- `trading.max_positions`
- `trading.max_positions_per_symbol`
- `signals.buy_threshold`
- `signals.sell_threshold`
- `filters.*_mode`
- `global_tp_sl`
- `symbol_tp_sl`
- `risk_by_symbol`
- `trailing.enabled`

### `config/market_briefing_today.json`

Briefing macro/manual do dia. Lido pelo `MarketBriefingEngine`.

Contém:

- `enabled`
- `date`
- `valid_until`
- `summary`
- `risk_regime`
- `market_snapshot`
- `currency_bias`
- `pair_bias`
- `asset_bias`
- `data_quality`
- `rules`

Atualização manual típica:

```powershell
.\.venv\Scripts\python.exe -m json.tool config\market_briefing_today.json
```

## Núcleo do Robô: `fusion/`

| Caminho | Função |
|---|---|
| `fusion/main.py` | orquestrador principal do FusionV2 |
| `fusion/runtime_control.py` | leitura do JSON runtime control |
| `fusion/core/` | configuração, logging e utilidades centrais |
| `fusion/data/` | conexão MT5, leitura de dados, candles e qualidade |
| `fusion/features/` | features, indicadores e engenharia de sinais |
| `fusion/models/` | carregamento/inferência de modelos |
| `fusion/decision/` | schema e decisão agregada |
| `fusion/engines/` | motores de filtro/risco/contexto/consenso |
| `fusion/execution/` | envio de ordem, trailing, lifecycle e MT5 execution |
| `fusion/strategies/` | estratégias operacionais do robô |
| `fusion/strategy_bank/` | banco de estratégias/padrões |
| `fusion/backtest/` | suporte a backtests internos |
| `fusion/advisor/` | componentes de advisor |
| `fusion/ai/` | bridge/reviewer IA |
| `fusion/approved_ensembles.py` | integração com ensembles aprovados de `fusion_refatorado` |
| `fusion/mt5_signal_panel.py` | exporta painel de sinais para MT5 |
| `fusion/mt5_trade_zones.py` | exporta zonas de trade |
| `fusion/mt5_decision_layers.py` | exporta camadas de decisão |

## Dependência Runtime Especial: `fusion_refatorado/`

Apesar do nome, esta pasta ainda é usada pelo robô atual.

Referências conhecidas:

- `fusion/approved_ensembles.py`
- `fusion/strategies/estrategia_6.py`
- `fusion/execution/trailing.py`
- `config/fusion_config.yaml` em `strategies.strategy6.registry_path`

Não mover até desacoplar esses imports e paths.

## Painéis e Interfaces

### `terminal_windows/`

Painel Windows atual em .NET/WinForms.

Arquivos principais:

- `run_terminal_windows.ps1`: inicializador recomendado.
- `FusionTerminalWindows.csproj`: projeto .NET.
- `Program.cs`: bootstrap da aplicação.
- `MainForm.cs`: tela principal e refresh de dados.
- `Chart/`, `Data/`, `Models/`, `Theme/`, `Widgets/`: componentes do painel.
- `bin/`, `obj/`: build outputs do .NET.

Comando:

```powershell
.\terminal_windows\run_terminal_windows.ps1
```

### `terminal_qt/`

Terminal Qt/bridge usado como fonte de utilidades de mercado e normalização por alguns scripts.

Importante para:

- `tools/export_mt5_candles_for_terminal.py`
- leitura de candles MT5 para snapshots do painel

### `terminal_desktop/`

Painel desktop legado/alternativo.

### `frontend/` e `fusion-frontend/`

Frontends web. Consulte `package.json`, scripts internos e ferramentas em `tools/`.

### `dashboard/`

Dashboard antigo/apoio.

## Ferramentas: `tools/`

A pasta `tools/` contém scripts de várias naturezas. Ainda não foi completamente separada para evitar quebrar comandos existentes.

### Runtime/Bridge/API

- `export_mt5_candles_for_terminal.py`: MT5 -> `runtime/market_data/latest_candles`.
- `mt5_live_api.py`: API local para dados/ordens MT5.
- `mt5_snapshot_api.py`: API/snapshot MT5.
- `fusion_frontend_data.py`: dados para frontend.
- `manage_mt5_live_api.ps1`: gerencia API MT5.
- `manage_mt5_socket.ps1`: gerencia socket MT5.
- `open_fusion_frontend_app.ps1`: abre frontend/painel web.

### Treinamento/modelos

- `train_model.py`
- `train_expr_model.py`
- `train_research_models.py`
- `train_runtime_models_from_parquet.py`
- `train_missing_runtime_models_mt5.py`
- `train_expert_models_batch.py`
- `merge_best_models.py`
- `inventory_model_features.py`
- `model_source_cleanup.py`

### Backtest/otimização/análise

- `analyze_signal_outcomes.py`
- `analyze_signal_path_outcomes.py`
- `optimize_signal_targets_stops.py`
- `analyze_blocked_signals.py`
- `analyze_block_quality_since_20260529.py`
- `analyze_event_performance.py`
- `analyze_market_structure_shadow_outcomes.py`
- `analyze_signal_inversion.py`
- `backtest_insidebar_gold.py`
- `backtest_strategy_bank.py`
- `backteste_rapido.py`
- `build_operational_target_matrix.py`
- `build_portfolio_risk_map.py`
- `build_asset_correlations.py`
- `build_shadow_engine_report.py`
- `summarize_decision_audit.py`
- `summarize_market_structure_ranking.py`
- `summarize_market_structure_shadow.py`

### Checks/smoke tests

Scripts `check_*.py`, `smoke_decision_engine.py`, `validate_order_financial_cross.py`, `test_mt5_socket_port.py`.

### Legado de análise

- `tools/analysis_legacy/extract_predictions.py`
- `tools/analysis_legacy/table_predictions.py`

## Relatórios e Análises: `reports/`

Contém saídas de auditoria, backtests, calibragens e inventários.

Subpastas importantes:

- `reports/risk_drawdown/`: análise de drawdown, SL/TP por ativo.
- `reports/project_inventory/`: inventário e log da organização do projeto.
- `reports/signal_path_optimization/`: otimização TP/SL histórica.
- `reports/signal_path_outcomes_*`: MAE/MFE e caminho de sinais.
- `reports/operational_target_matrix/`: matriz operacional usada por painel/sinal.
- `reports/correlation/`: matrizes de correlação/exposição.
- `reports/prints/legacy_chart_prints/`: prints movidos da raiz.
- `reports/legacy_tables/`: tabelas legadas movidas da raiz.

## Dados, Features e Modelos

### `data/`

Dados brutos/cache/parquet. Configurado em:

```yaml
market_data:
  data_dir: ./data
  parquet_dir: ./data/parquet
```

### `features/`

Features geradas e relatórios usados por estratégias/backtests.

Algumas estratégias ainda apontam para arquivos em `features/`, então não mover sem ajuste.

### `models*`

- `models/`: modelos genéricos/legados.
- `models_research/`: diretório configurado como `model.model_dir` do Fusion.
- `models_principal/`: modelos principais antigos/candidatos.
- `models_experts/`, `models_experts_v2/`: modelos por expert.
- `models_expr/`: modelos de expressão/experimentos.

## Pesquisa: `02_research/`

Área criada para separar o que não é runtime direto.

- `02_research/experts/`: experts experimentais que antes ficavam em `experts/`.

## Archive e External

### `_archive/`

Contém backups e legados movidos da raiz:

- `_archive/backups/`
- `_archive/fusion_pro/`
- `_archive/repositorio/`
- `_archive/revisar/`

### `_external/`

Contém projetos externos/integrados:

- `_external/Quant/`

A duplicata `_cleanup_pending...` foi preservada por segurança por conter `node_modules` pesado. Pode ser removida depois com uma limpeza dedicada.

## Logs e Estado Vivo

### `logs/`

Logs do robô, APIs, bridges e diagnósticos runtime.

### `runtime/`

Estado vivo e snapshots. Destaque:

- `runtime/market_data/latest_candles/`: snapshots JSON de candles MT5 usados pelos painéis.
- arquivos `.fcnd/.fcni/.csv`: caches/artefatos do terminal.

## Regras Operacionais Atuais

### Ordem por ativo

Regra desejada e aplicada:

- máximo de 1 ordem por ativo;
- qualquer direção conta;
- qualquer estratégia/magic conta;
- exemplo: se existe `GBPJPY SELL`, o Fusion não deve abrir outro `GBPJPY BUY` nem outro `GBPJPY SELL`.

Arquivos relacionados:

- `config/fusion_config.yaml`
- `config/fusion_runtime_control.json`
- `fusion/main.py`
- `fusion/execution/trading.py`

### SL mínimo operacional

A análise de risco considera stop menor que 15 pontos inviável.

Relatórios:

- `reports/risk_drawdown/stop_take_plan_by_asset.md`
- `reports/risk_drawdown/stop_take_plan_by_asset.csv`

### Briefing macro

Arquivo atual:

- `config/market_briefing_today.json`

Validar JSON:

```powershell
.\.venv\Scripts\python.exe -m json.tool config\market_briefing_today.json
```

## Comandos de Validação

### Validar sintaxe básica

```powershell
.\.venv\Scripts\python.exe -m py_compile run_fusion.py
.\.venv\Scripts\python.exe -m py_compile reports\project_inventory\build_project_inventory.py
```

### Ver posições abertas no MT5

```powershell
.\.venv\Scripts\python.exe -c "import MetaTrader5 as mt5, collections, json; mt5.initialize(); ps=list(mt5.positions_get() or []); print(len(ps)); print(json.dumps(dict(collections.Counter(p.symbol for p in ps)), indent=2))"
```

### Ver candles sincronizados para o painel

```powershell
Get-ChildItem runtime\market_data\latest_candles -Filter *.json | Sort-Object LastWriteTime -Descending | Select-Object -First 10 Name,LastWriteTime,Length
```

### Ver bridge de candles rodando

```powershell
Get-CimInstance Win32_Process | Where-Object { ($_.CommandLine -like '*export_mt5_candles_for_terminal.py*') -and ($_.Name -like '*python*') } | Select-Object ProcessId,Name,CommandLine
```

## Organização Executada

Log completo:

- `reports/project_inventory/phase1_migration_log.md`

Resumo:

- documentos operacionais soltos -> `docs/operacional/`;
- tabelas soltas -> `reports/legacy_tables/`;
- scripts legados de tabela/previsão -> `tools/analysis_legacy/`;
- backups/legados -> `_archive/`;
- prints -> `reports/prints/legacy_chart_prints/`;
- experts experimentais -> `02_research/experts/`.

## Próximas Etapas Seguras

1. Separar `tools/` em subpastas (`runtime`, `analysis`, `training`, `checks`) mantendo wrappers nos caminhos antigos.
2. Separar `models` em runtime vs pesquisa, depois de confirmar quais arquivos são carregados.
3. Separar `data/features` por uso: runtime, treinamento, backtest e cache.
5. Desacoplar `fusion_refatorado/` do runtime antes de movê-lo para archive/research.

## Documentos Complementares

- `docs/ORGANIZACAO_PROJETO.md`
- `docs/RUNTIME_FUSION_MAP.md`
- `docs/operacional/README.md`
- `reports/project_inventory/root_inventory.md`
- `reports/project_inventory/phase1_migration_log.md`
- `reports/risk_drawdown/stop_take_plan_by_asset.md`