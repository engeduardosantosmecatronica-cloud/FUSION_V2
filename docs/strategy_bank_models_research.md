# Banco Operacional de Estrategias por Ativo

Este banco define e executa estrategias por ativo para todos os simbolos com modelos em `models_research`.
Os modelos nao sao a estrategia; eles entram como camada complementar de confirmacao quando houver previsoes
disponiveis. A estrategia continua sendo o setup operacional do grafico.

## Arquivos

- `fusion/strategy_bank/_factory.py`: monta o banco por ativo, com 5 estrategias escolhidas para cada perfil.
- `fusion/strategy_bank/executor.py`: detectores operacionais dos setups e geracao de sinais com entrada, TP e SL.
- `fusion/strategy_bank/asset_strategies/*_strategies.py`: um modulo por ativo, cada um com `STRATEGY_BANK` e `STRATEGIES`.
- `tools/backtest_strategy_bank.py`: runner de backtest historico usando `data/parquet`.

## Ativos cobertos

O banco cobre 31 ativos:

`AUDCAD`, `AUDCHF`, `AUDJPY`, `AUDNZD`, `AUDSGD`, `AUDUSD`, `CADCHF`, `CADJPY`, `CHFJPY`,
`EURAUD`, `EURCAD`, `EURCHF`, `EURGBP`, `EURJPY`, `EURNZD`, `EURUSD`, `GBPAUD`, `GBPCAD`,
`GBPCHF`, `GBPJPY`, `GBPNZD`, `GBPUSD`, `NZDCAD`, `NZDCHF`, `NZDJPY`, `NZDSGD`, `NZDUSD`,
`USDCAD`, `USDCHF`, `USDJPY`, `XAUUSD`.

Cada ativo tem 5 estrategias escolhidas a partir da personalidade esperada do ativo: tendencia, range,
inside bar, rompimento, sweep, momentum de sessao, suporte/resistencia ou comportamento especifico do ouro.

## Setups implementados

- `ema_cross_continuation`: cruzamento/continuidade de EMA8, EMA21 e EMA50.
- `trend_pullback_ema21`: pullback na EMA21 dentro de tendencia.
- `inside_bar_breakout`: rompimento da maxima/minima do candle mae.
- `range_mean_reversion`: reversao em extremos de range.
- `volatility_expansion_breakout`: rompimento apos compressao de volatilidade.
- `session_momentum_open`: momentum de abertura Londres/Nova York.
- `liquidity_sweep_reversal`: varredura de liquidez e fechamento de volta ao range.
- `daily_bias_intraday`: entrada intraday alinhada ao vies maior.
- `support_resistance_bounce`: rejeicao em suporte/resistencia.
- `gold_impulse_pullback`: impulso e pullback especifico para XAUUSD.

## Uso em Python

```python
import pandas as pd

from fusion.strategy_bank import STRATEGY_BANK, evaluate_asset_bank

bank = STRATEGY_BANK["AUDSGD"]
frames = {
    "M15": pd.read_parquet("data/parquet/M15/AUDSGD.parquet"),
    "M30": pd.read_parquet("data/parquet/M30/AUDSGD.parquet"),
    "H1": pd.read_parquet("data/parquet/H1/AUDSGD.parquet"),
}

signals = evaluate_asset_bank(bank, frames)
print(signals[0])
```

## Backtest rapido

```powershell
venv\Scripts\python.exe tools\backtest_strategy_bank.py --symbols AUDSGD EURCAD XAUUSD --years 2 --max-bars 80
```

Saidas:

- `reports/strategy_bank_backtests/strategy_bank_backtest_summary.csv`
- `reports/strategy_bank_backtests/strategy_bank_backtest_trades.csv`

## Papel dos modelos

O executor aceita uma tabela opcional de previsoes do modelo com colunas como `prediction`, `p_buy` e `p_sell`.
Quando fornecida, a estrategia so emite sinal se o modelo confirmar a direcao e passar `min_probability` e `min_edge`.
Sem essa tabela, os detectores operam puramente pelo setup tecnico para permitir backtest estrutural.
