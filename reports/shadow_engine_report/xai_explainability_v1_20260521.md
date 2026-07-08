# XAI Explainability v1 - Pos-Roadmap

## Objetivo

Adicionar explicabilidade consolidada por decisao auditada, sem alterar a execucao do robo.

## Implementado

- Criado `fusion/decision/explain.py`.
- `DecisionEvent` passou para `decision_event_v2` com campo opcional `explanation`.
- `_audit_decision_event(...)` agora gera explicacao XAI quando `decision_engine.xai_enabled: true`.
- `config/fusion_config.yaml` recebeu:
  - `decision_engine.xai_enabled: true`;
  - `decision_engine.xai_top_factors: 8`.
- `dashboard/fusion_dashboard.py` agora le:
  - `xai_final_score`;
  - `xai_confidence_band`;
  - `xai_summary`;
  - fatores positivos dominantes;
  - fatores negativos dominantes.
- `tools/summarize_decision_audit.py` agora exporta campos XAI e inclui resumo XAI no markdown.
- Criado `tools/check_xai_explainer.py`.

## Saida XAI

Cada novo evento em `logs/decision_audit/decision_audit_*.jsonl` pode carregar:

- `final_score`;
- `confidence_band`;
- `aligned_engines`;
- `conflicting_engines`;
- `neutral_engines`;
- `warning_engines`;
- `top_positive_factors`;
- `top_negative_factors`;
- `top_warnings`;
- `engine_contributions`;
- `summary`.

## Status Operacional

- Audit-only.
- Nao bloqueia ordem.
- Nao muda lote.
- Nao altera TP/SL/trailing.
- Compatibilidade mantida com logs antigos sem `explanation`.

## Validacoes

- `.\venv\Scripts\python.exe tools\check_xai_explainer.py` passou:
  - `xai_ok score=0.735 band=alta aligned=1 conflicts=1`.
- `.\venv\Scripts\python.exe -m compileall fusion dashboard tools\check_xai_explainer.py tools\summarize_decision_audit.py tools\check_dashboard_data.py` passou.
- `.\venv\Scripts\python.exe -c "from fusion.main import FusionV2; print('import_ok')"` passou.
- `.\venv\Scripts\python.exe tools\check_dashboard_data.py` passou.
- `.\venv\Scripts\python.exe tools\summarize_decision_audit.py --date 20260521 --output-dir reports\decision_audit_xai_check` processou 15152 eventos antigos sem erro.

## Observacao

Os eventos antigos nao possuem `explanation`. O XAI aparecera nos novos eventos gerados depois do reinicio/continuidade do robo com esta versao carregada.
