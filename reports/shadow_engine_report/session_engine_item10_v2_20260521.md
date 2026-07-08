# Item 10 - Session Engine v2

## Objetivo

Evoluir o `SessionEngine` de uma classificacao simples de horario para uma camada contextual de sessao, capaz de medir qualidade operacional por ativo/timeframe sem bloquear ordens nesta fase.

## Implementado

- Expandido `fusion/engines/session.py`.
- O engine agora recebe:
  - ativo;
  - timeframe;
  - lado do sinal;
  - horario UTC.
- Novas leituras:
  - sessao ativa: Asia, London, New York, overlap London/NY, rollover, sexta-feira;
  - risco de abertura London;
  - risco de abertura New York;
  - transicao entre sessoes;
  - adequacao do ativo a sessao;
  - ativo ruidoso para scalping;
  - timeframe de scalping.
- Estados novos/expandidos:
  - `friday_close_risk`;
  - `weak_session_fit`;
  - `rollover_low_liquidity`;
  - `london_new_york_overlap`;
  - `london`;
  - `new_york`;
  - `asia`;
  - `weekend`.

## Configuracao

Atualizado `config/fusion_config.yaml` em `entry_filters.session_context` com:

- janelas de abertura de risco;
- moedas preferenciais por sessao;
- ativos ruidosos;
- timeframes de scalping;
- scores por estado de sessao.

## Status

- Permanece em `shadow`.
- Nao altera ordem, lote, TP, SL ou trailing.
- Alimenta `context_engine`, `consensus_engine` e `opportunity_engine` com um score de sessao mais realista.

## Proximo Uso

Depois de observar eventos suficientes:

- medir win rate por sessao;
- identificar ativos ruins por sessao;
- calibrar score por ativo/timeframe;
- promover apenas estados extremos, como `rollover_low_liquidity` e `friday_close_risk`, para `block` se os dados confirmarem.
