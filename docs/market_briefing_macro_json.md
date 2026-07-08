# Market Briefing Macro JSON

O Fusion pode ler `config/market_briefing_today.json` como contexto macro do dia.
Esse arquivo deve ser gerado manualmente, de hora em hora ou diariamente, a partir da sua leitura de mercado.

Ele nao deve mandar o robo comprar ou vender diretamente. Ele informa vies e risco para o Fusion comparar com os sinais do modelo.

## Campos Principais

- `currency_bias`: vies por moeda. Exemplo: USD bullish, EUR bearish, JPY bearish.
- `pair_bias`: vies direto por par. Tem prioridade sobre `currency_bias`.
- `asset_bias`: vies de ativos especiais como GOLD, BTCUSD, ETHUSD, AUS200.
- `rules`: regras de risco para bloquear ou moderar setups especificos.

## Como O Fusion Interpreta

Para pares forex:

```text
pair_bias_score = base_bias - quote_bias
```

Exemplo:

```text
EUR bearish = -0.65
NZD bullish = +0.70
EURNZD = -0.65 - 0.70 = -1.35
Resultado: briefing favorece SELL em EURNZD.
```

Se o modelo der SELL, o briefing aparece como `macro_bias_aligned`.
Se o modelo der BUY, aparece como `macro_bias_conflict`.

## Exemplo De Uso

Copie `config/market_briefing_template.json` para `config/market_briefing_today.json` e atualize:

- `date`
- `valid_until`
- `summary`
- moedas fortes/fracas
- pares com vies claro
- ativos com risco ou compressao
- regras de noticia ou volatilidade

Mantenha `entry_filters.market_briefing.mode: "shadow"` enquanto estiver calibrando.
Depois de varios dias de validacao, pode-se testar `mode: "block"` apenas para conflitos macro fortes.
