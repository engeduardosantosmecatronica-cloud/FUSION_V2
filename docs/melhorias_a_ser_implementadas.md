# Melhorias a Ser Implementadas

## Plataforma Visual

- Consolidar a tela de candles como base da plataforma desktop.
- Melhorar interatividade do grafico: zoom, pan, escala de preco e atalhos.
- Salvar e restaurar layout dos docks.
- Salvar preferencias visuais: cores, indicadores, largura dos paineis e ativo/timeframe atual.
- Adicionar legenda configuravel para ordens, sinais, SL, TP e trailing.
- Permitir esconder/mostrar todos os overlays individualmente.

## Simulador Visual

- Permitir selecionar uma seta BUY/SELL e editar os parametros daquela ordem.
- Mostrar entrada, saida, SL, TP e trailing apenas da ordem selecionada.
- Permitir mover linhas de SL/TP manualmente no grafico.
- Recalcular resultado da ordem selecionada ao alterar SL/TP/trailing.
- Criar modo replay historico candle a candle.
- Criar modo "play/pause" para reproduzir uma sessao historica.

## Estrategias

- Criar um banco de estrategias centralizado.
- Cada estrategia deve ficar registrada com:
  - ID unico.
  - Nome amigavel.
  - Categoria.
  - Descricao operacional.
  - Timeframes recomendados.
  - Ativos recomendados.
  - Parametros padrao.
  - Parametros otimizaveis.
  - Regras de entrada.
  - Regras de saida.
  - Regras de stop loss.
  - Regras de take profit.
  - Regras de trailing.
  - Filtros obrigatorios.
  - Filtros opcionais.
  - Status: ativa, experimental, desativada, obsoleta.
  - Historico de performance por ativo/timeframe.
  - Versao da estrategia.
  - Data da ultima otimizacao.
- Implementar biblioteca de estrategias simulaveis:
  - Cruzamento de medias.
  - Inside bar.
  - Rompimento de maxima/minima.
  - Pullback em medias.
  - Breakout com confirmacao.
  - Reversao por candle.
  - Estrategias reais do FUSION_V2.
- Padronizar contrato de estrategia:
  - Nome.
  - Parametros.
  - Condicao de entrada.
  - Condicao de saida.
  - Stop loss.
  - Take profit.
  - Trailing.
  - Filtros opcionais.

## Teste Multiativos

- Criar uma tela para testar uma estrategia em todos os ativos.
- Criar um dicionario de conversao financeira por ativo para transformar pips/pontos em USD e BRL:
  - Simbolo do robo.
  - Simbolo da corretora.
  - Tipo do ativo.
  - Tamanho do contrato.
  - Lote minimo.
  - Step de lote.
  - Tick size.
  - Tick value.
  - Point value.
  - Pip size.
  - Moeda de lucro.
  - Conversao para USD.
  - Conversao para BRL.
  - Regras especificas para GOLD/XAUUSD, indices e pares JPY.
  - Resultado em pips, pontos, USD e BRL por trade simulado.
- Para cada ativo/timeframe, calcular:
  - Total de trades.
  - Trades vencedores.
  - Trades perdedores.
  - Win rate.
  - Lucro bruto.
  - Prejuizo bruto.
  - Resultado liquido.
  - Drawdown maximo.
  - Profit factor.
  - Expectativa por trade.
  - Melhor sequencia vencedora.
  - Pior sequencia perdedora.
- Gerar ranking dos ativos onde cada estrategia performa melhor.
- Permitir comparar:
  - Estrategia x ativo.
  - Estrategia x timeframe.
  - Ativo x timeframe.
  - Parametros de SL/TP/trailing.

## Otimizacao

- Rodar varredura de parametros por estrategia:
  - SL.
  - TP.
  - Trailing ativacao.
  - Trailing distancia.
  - Periodos de medias.
  - Lookback de inside bar.
- Evitar overfitting usando:
  - Split treino/teste.
  - Walk-forward validation.
  - Periodos fora da amostra.
  - Validacao por regime de mercado.

## Integracao Com o Robo

- Usar as mesmas features e filtros do FUSION_V2 nas simulacoes.
- Comparar sinais simulados com decisoes reais do robo.
- Mostrar probabilidades BUY/SELL por timeframe em tempo real.
- Mostrar motores alinhados/conflitantes por ativo.
- Mostrar motivo de bloqueio da ordem diretamente no grafico.
- Permitir replay dos eventos do Event Bus junto com os candles.

## Relatorios

- Exportar resultados para CSV/Excel.
- Gerar relatorio por estrategia.
- Gerar relatorio por ativo.
- Gerar relatorio por timeframe.
- Gerar ranking geral de oportunidades.
- Criar painel de curva de capital.
- Criar painel de drawdown.

## Prioridade Proxima

1. Criar motor de backtest visual reutilizavel.
2. Implementar estrategia Inside Bar no simulador.
3. Criar tela "Teste Multiativos".
4. Rodar estrategia selecionada em todos os ativos e timeframes.
5. Exibir ranking de ativos onde a estrategia performa melhor.
