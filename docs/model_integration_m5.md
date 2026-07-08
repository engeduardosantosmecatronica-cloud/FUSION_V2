# Integracao dos modelos M5 aprovados

Data: 2026-05-19

Este documento descreve a integracao dos ensembles M5 aprovados do `fusion_refatorado` ao runtime atual do FUSION_V2.

## Backup de seguranca

Antes da integracao foi criado o backup:

`_archive/backups/pre_model_integration_20260519_101004`

Arquivos principais:

- `BACKUP_README.md`
- `BACKUP_MANIFEST.csv`
- copia de `run_fusion.py`, `fusion/`, `config/`, `plan.md`
- copia dos registries e relatorios de selecao/trailing

## Arquivos alterados/criados

- Criado: `fusion/approved_ensembles.py`
- Alterado: `fusion/main.py`
- Alterado: `fusion/execution/trading.py`
- Alterado: `fusion/execution/trailing.py`
- Alterado: `fusion/data/pipeline.py`
- Alterado: `fusion/__init__.py`
- Alterado: `config/fusion_config.yaml`
- Criado: `docs/model_integration_m5.md`

## Como a integracao funciona

O runtime atual continua entrando por:

`run_fusion.py -> fusion.main.FusionV2`

Durante `initialize()`, o sistema agora:

1. Carrega os modelos antigos, se existirem em `models/`.
2. Carrega os ensembles aprovados em:
   `fusion_refatorado/models/production_registry/M5_approved_ensembles.json`
3. Carrega TP/SL por ativo/timeframe de:
   `features/features_backteste_ativo_timeframe.csv`
4. Sincroniza simbolos do broker.
5. Mantem o trailing separado em thread propria.

## Strategy5

Foi adicionada a `strategy5`, isolada das strategies antigas.

Ela opera somente os ensembles aprovados carregados do registry.

Configuracao em `config/fusion_config.yaml`:

```yaml
strategy5:
  enabled: true
  magic_base: 50
  use_feature_tp_sl: true
  default_tp_points: 500
  default_sl_points: 150
  cooldown_seconds: 300
```

Magic esperado para M5:

`5005`

Padrao atual de magic por estrategia:

```text
strategy1: M5=1005, M15=1015, M30=1030, H1=1060, H4=10240, D1=101440
strategy2: M5=2005, M15=2015, M30=2030, H1=2060, H4=20240, D1=201440
strategy3: M5=3005, M15=3015, M30=3030, H1=3060, H4=30240, D1=301440
strategy4: M5=4005, M15=4015, M30=4030, H1=4060, H4=40240, D1=401440
strategy5: M5=5005, M15=5015, M30=5030, H1=5060, H4=50240, D1=501440
strategy6: M5=6005, M15=6015, M30=6030, H1=6060, H4=60240, D1=601440
```

## Inversao de sinais por estrategia

A inversao global foi desativada:

```yaml
signal:
  invert_signals: false
```

A inversao agora fica no nivel da estrategia:

```yaml
strategy1:
  invert_signal: true
strategy2:
  invert_signal: true
strategy3:
  invert_signal: true
```

Com isso:

- `strategy1`, `strategy2` e `strategy3`: BUY vira SELL, SELL vira BUY.
- `strategy4`: nao inverte.
- `strategy5`: nao inverte; usa o sinal proprio dos ensembles aprovados.

## Filtro De EMAs

Todas as estrategias passam por um filtro global de alinhamento antes de enviar ordem:

```yaml
entry_filters:
  ema_alignment:
    enabled: true
    periods: [9, 21, 50]
    use_closed_candle: true
    log_passed_filter: true
    min_distance_points:
      by_timeframe:
        M5: {ema9_ema21: 10, ema21_ema50: 15}
        M15: {ema9_ema21: 15, ema21_ema50: 20}
        M30: {ema9_ema21: 20, ema21_ema50: 30}
        H1: {ema9_ema21: 30, ema21_ema50: 40}
        H4: {ema9_ema21: 50, ema21_ema50: 70}
        D1: {ema9_ema21: 80, ema21_ema50: 100}
    buy_rule: "EMA9 > EMA21 > EMA50"
    sell_rule: "EMA9 < EMA21 < EMA50"
```

Regras:

- BUY so abre se `EMA9 > EMA21 > EMA50`.
- SELL so abre se `EMA9 < EMA21 < EMA50`.
- Alem da ordem, a distancia minima entre as medias precisa ser atendida.
- A distancia e calculada em pontos usando o `point_value` do ativo.
- O `point_value` vem de `data.point_values` quando houver override; senao usa `mt5.symbol_info(symbol).point`; se necessario, usa `trade_tick_size`.
- O calculo usa o ultimo candle fechado, nao o candle atual em formacao.
- Quando o filtro passa, o log mostra as EMAs, distancias calculadas, minimos exigidos e `point_value`.
- Se nao alinhar, a ordem e bloqueada antes de chegar ao broker.

Overrides opcionais:

```yaml
data:
  point_values:
    GOLD: 0.01
    XAUUSD: 0.01
```

## Stop Loss Padrao

Todas as estrategias usam SL de 100 pontos no envio da ordem:

```yaml
risk:
  default_sl_points: 100
```

Nas estrategias com TP vindo das features (`S2`, `S3`, `S5`), o TP continua dinamico, mas o SL fica fixo em 100 pontos:

```yaml
use_feature_sl: false
default_sl_points: 100
```

## Dashboard Progressivo

O dashboard nao limpa mais o console a cada ciclo. Cada loop imprime um novo snapshot com timestamp.

A coluna `MOTIVOS` mostra por ativo/timeframe por que nao abriu ordem, por exemplo:

```text
M5:modelo:neutro_threshold
M15:S2:sem_feature
M30:S3:exposure_block
H1:S5:ema_nao_alinhada
```

Os motivos tambem ficam em `monitor_state[(symbol, timeframe)]["reason"]`.

Com `dashboard.show_reason_details: true`, o sistema imprime abaixo da tabela os motivos completos, sem corte.

Antes de enviar ordem, o runtime tambem verifica se o MT5 permite trading. Se o AutoTrading estiver desligado no terminal, o motivo vira:

```text
autotrading_desativado_terminal
```

Nesse caso ele nao chama `order_send`, evitando repeticao de erros `AutoTrading disabled by client`.

## Strategy6

Foi criada a `strategy6` em arquivo proprio:

`fusion/strategies/estrategia_6.py`

Ela opera sem depender dos modelos antigos do `fusion/main.py`, mas usa os experts dos ensembles aprovados como filtro primario de direcao. Depois usa as regras de `features_backteste_dinamica.csv` como confirmacao/gatilho de entrada.

Fonte:

```yaml
strategy6:
  features_path: "./features/features_backteste_dinamica.csv"
```

Ordem de decisao:

1. Calcula snapshot das features do sistema (`_calculate_features`).
2. Calcula snapshot das features OMNIS de `fusion_refatorado`.
3. Avalia os experts habilitados dos ensembles aprovados disponíveis para o ativo/timeframe.
4. Agrega os votos dos experts em `buy_score`, `sell_score` e `net_score`.
5. Se os experts confirmarem direcao, procura uma regra compatível em `features_backteste_dinamica.csv`.
6. A regra de feature precisa confirmar o mesmo lado indicado pelos experts.
7. Se passar cooldown/limites, envia ordem pela rota `S6`.
8. Salva um JSONL por loop em `logs/strategy6`.

Configuracao inicial:

```yaml
strategy6:
  enabled: false
  invert_signal: false
  magic_base: 60
  enabled_experts: ["trend", "orderflow", "sr", "reversal", "pullback", "quant", "candles", "risk", "volatility"]
  enabled_features: [...]
  enabled_omnis_features: [...]
  require_expert_confirmation: true
  expert_min_confidence: 0.55
  expert_min_score: 0.25
  min_expert_votes: 1
  require_feature_rule: true
  log_each_loop: true
  log_dir: "logs/strategy6"
  bars: 1200
  use_feature_tp_sl: false
  tp_points: 0
  sl_points: 0
```

Ela foi deixada desativada por seguranca, porque opera sem SL e sem TP.

Resumo da decisao:

```text
experts aprovados definem a direcao
features_backteste_dinamica.csv confirma o gatilho de entrada
sem confirmacao dos experts = nao entra
sem regra de feature no mesmo lado = nao entra
```

## Arquivos de estrategias

A logica operacional foi separada em:

- `fusion/strategies/estrategia_1.py`
- `fusion/strategies/estrategia_2.py`
- `fusion/strategies/estrategia_3.py`
- `fusion/strategies/estrategia_4.py`
- `fusion/strategies/estrategia_5.py`
- `fusion/strategies/estrategia_6.py`
- `fusion/strategies/base.py`

O `main.py` agora instancia `strategy_runners` e chama `strategy.evaluate(...)` no ciclo principal.

## Controle de seguranca

Mesmo com `strategy5.enabled: true`, novas ordens continuam bloqueadas enquanto:

```yaml
trading:
  allow_new_orders: false
```

Esse e o estado recomendado para validar logs, sinais, TP/SL, magic e trailing antes de paper/demo.

## Ensemble loader

O arquivo `fusion/approved_ensembles.py`:

- Le o registry `M5_approved_ensembles.json`.
- Abre cada `ensemble_walkforward_config.json`.
- Carrega somente membros com peso relevante.
- Padrao atual:
  - `min_member_weight: 0.25`
  - `min_score: 0.25`
  - `bars: 1200`
- Calcula features OMNIS em tempo real com o mesmo pipeline usado no treino:
  `fusion_refatorado.fusion_best.expert_training.build_expert_feature_frame`
- Retorna sinal no padrao do runtime:
  - `1`: BUY
  - `2`: SELL
  - `0`: neutro

## Ativos M5 aprovados

Ativos carregados pelo registry:

- `EURAUD`
- `AUDJPY`
- `CHFJPY`
- `AUDUSD`
- `USDJPY`
- `CADJPY`
- `EURCAD`
- `GBPJPY`
- `NZDJPY`

## Trailing otimizado

O trailing continua em:

`fusion/execution/trailing.py`

Ele carrega automaticamente:

`fusion_refatorado/models/production_registry/trailing_optimized_M5.json`

Ativos com trailing otimizado promovido:

- `EURAUD`
- `AUDJPY`
- `AUDUSD`
- `USDJPY`
- `EURCAD`
- `GBPJPY`
- `CADJPY`

`CHFJPY` nao foi promovido para trailing otimizado porque a grade gerou retorno total negativo.
`NZDJPY` tambem foi testado em 2026-05-19 e nao foi promovido porque a grade ficou negativa.

## Validacoes realizadas

```powershell
.\venv\Scripts\python.exe -m compileall fusion
```

Carregamento dos ensembles:

```text
Ensembles aprovados carregados: 9
```

## Expansao de ativos M5 - 2026-05-19

Ativos adicionados ao monitoramento:

- `GBPCAD`
- `AUDSGD`
- `CADJPY`
- `GBPNZD`
- `NZDCHF`
- `NZDJPY`
- `NZDSGD`

Foi executado o pipeline M5 completo para esses ativos: treino dos 9 experts, backtest, walk-forward e ensemble walk-forward.

Resultado da selecao conservadora:

- Aprovados: `CADJPY`, `NZDJPY`
- Watchlist: `NZDSGD`
- Rejeitados: `GBPCAD`, `AUDSGD`, `GBPNZD`, `NZDCHF`

Trailing dos novos aprovados:

- `CADJPY`: promovido com ativacao 150 pontos e distancia 30 pontos.
- `NZDJPY`: testado, mas nao promovido porque a grade de trailing ficou negativa.

Registry aprovado atualizado:

```text
AUDJPY, AUDUSD, CADJPY, CHFJPY, EURAUD, EURCAD, GBPJPY, NZDJPY, USDJPY
```

Validacao do pacote MetaTrader5 no venv:

```text
F:\Eduardo\PROJETOS_PYTHON\FUSION_V2\venv\Scripts\python.exe
MT5 5.0.5735
```

Instanciacao do runtime:

```text
instance ok True
```

Estado seguro da integracao:

```text
allow_new_orders False
strategy5 True
```

Observacao: usar sempre o Python do venv do projeto para validar/rodar o sistema. O Python global pode nao ter `MetaTrader5` instalado.

## Como reverter

Usar o backup:

```powershell
Copy-Item _archive\backups\pre_model_integration_20260519_101004\run_fusion.py . -Force
Copy-Item _archive\backups\pre_model_integration_20260519_101004\fusion .\fusion -Recurse -Force
Copy-Item _archive\backups\pre_model_integration_20260519_101004\config .\config -Recurse -Force
```

Depois validar:

```powershell
python -m compileall fusion
```

## Proximo passo recomendado

Executar o sistema pelo venv mantendo:

```powershell
.\venv\Scripts\python.exe run_fusion.py
```

Validar no log:

- quantidade de ensembles aprovados carregados
- sinais `APPROVED`
- strategy `S5`
- TP/SL usados
- magic `5005` para M5 na `strategy5`
- trailing aplicado aos ativos com preset

