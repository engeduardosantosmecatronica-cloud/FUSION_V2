# Item 14 - Dashboard Institucional v1

## Objetivo

Melhorar o dashboard externo do FUSION_V2 para acompanhar o motor de decisao institucional sem poluir o console operacional do robo.

## Implementado

- Atualizado `dashboard/fusion_dashboard.py`.
- Criado `tools/check_dashboard_data.py`.
- O dashboard agora le:
  - log operacional `logs/fusion_*.log`;
  - audit JSONL `logs/decision_audit/decision_audit_*.jsonl`;
  - relatorios de shadow quando existirem.

## Novas Abas

- `Decision Audit`:
  - ultimos eventos auditados;
  - contagem de ALLOW/BLOCK;
  - tradeability medio;
  - conflito medio;
  - estados por engine.
- `Heatmaps`:
  - heatmap por ativo/timeframe de:
    - tradeability;
    - conflict;
    - consensus;
    - p_buy;
    - p_sell;
  - heatmap por engine/score.
- `Risco`:
  - leitura de `risk_engine`;
  - `portfolio_exposure`;
  - `portfolio_correlation`;
  - `opportunity_engine`;
  - multiplicador sugerido;
  - penalties;
  - quality floor.
- `Engines`:
  - matriz detalhada dos engines institucionais;
  - score;
  - confidence;
  - estados;
  - feature coverage;
  - session fit;
  - meta-model info;
  - calibracao.

## Status

- Dashboard continua separado do loop de trading.
- Nao altera ordem, modelo, lote, TP/SL ou trailing.
- Serve para observacao e auditoria.

## Execucao

```powershell
.\venv\Scripts\python.exe -m streamlit run dashboard\fusion_dashboard.py --server.port 8501
```

## Proxima Evolucao

- Adicionar mapa de exposicao por moeda em tempo real.
- Adicionar matriz de correlacao visual.
- Adicionar historico de performance por estado de engine.
- Criar pagina dedicada para ordens abertas/fechadas.
