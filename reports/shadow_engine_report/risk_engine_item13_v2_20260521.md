# Item 13 - Risk Engine v2

## Objetivo

Evoluir o `RiskEngine` para uma camada mais institucional, capaz de medir risco de conta, margem, concentracao sintetica por moeda e qualidade contextual antes da ordem.

## Implementado

- Expandido `fusion/engines/risk.py`.
- Atualizado `fusion/main.py`.
- Atualizado `config/fusion_config.yaml`.
- Atualizado `tools/check_risk_engine.py`.

## Novas Leituras

- `margin`;
- `margin_free`;
- `margin_level`;
- `margin_usage_pct`;
- exposicao sintetica por moeda;
- exposicao projetada por moeda;
- maior risco projetado por moeda;
- posicoes no mesmo ativo;
- posicoes na mesma direcao;
- risco por volatilidade;
- risco por sessao;
- risco por qualidade de features;
- risco por oportunidade fraca.

## Novas Configuracoes

- `min_margin_level_pct`;
- `warning_margin_level_pct`;
- `max_margin_usage_pct`;
- `warning_margin_usage_pct`;
- `max_currency_risk_units`;
- `warning_currency_risk_units`;
- `max_symbol_positions`;
- `max_same_direction_positions`;
- `low_opportunity_threshold`;
- `low_feature_quality_threshold`.

## Saida Principal

- `risk_score`;
- `position_multiplier_suggested`;
- `currency_exposure`;
- `projected_currency_exposure`;
- `max_projected_currency_risk`;
- `margin_usage_pct`;
- `drawdown_pct`;
- `floating_loss_pct`.

## Status

- Permanece em `shadow`.
- Nao altera lote real.
- Nao bloqueia ordem enquanto `mode: shadow`.
- A saida `position_multiplier_suggested` fica pronta para futura reducao de lote.

## Proxima Evolucao

- Forward test do multiplicador sugerido.
- Aplicar reducao de lote somente quando houver evidencias suficientes.
- Criar limite de risco diario e perda maxima por sessao.
- Adicionar VAR/Expected Shortfall por portfolio.
