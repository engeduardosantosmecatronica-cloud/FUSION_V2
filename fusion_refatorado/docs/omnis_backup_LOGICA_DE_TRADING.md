# Lógica de Trading e Condições para Abertura de Ordem

Este documento detalha o processo completo que o robô GENESIS utiliza para decidir e executar uma nova ordem de negociação. O processo é dividido em duas etapas principais: **1. Análise e Decisão** e **2. Filtros de Execução**.

Uma ordem só é aberta se um sinal de alta confiança for gerado na primeira etapa **E** passar por **TODOS** os filtros da segunda etapa.

---

### Etapa 1: Análise e Geração de Sinal (em `core/decision_engine.py`)

O robô primeiro decide se há uma oportunidade de `BUY` ou `SELL` com base em uma análise complexa que envolve múltiplos fatores e modelos de Inteligência Artificial.

1.  **Análise do Regime de Mercado:**
    *   Utiliza dados do timeframe **H1** para classificar a condição atual do mercado (ex: tendência de alta, tendência de baixa, volátil, etc.).
    *   **Restrição:** Se o regime for considerado "não operável" (por exemplo, um mercado lateral sem volume), nenhuma operação é considerada. O robô aguarda uma condição mais clara.

2.  **Votação de Múltiplos Modelos de IA:**
    *   Para vários timeframes (`M5`, `M15`, `H1`, etc.), diversos modelos de Machine Learning especializados dão seu "voto" (`BUY`, `SELL` ou `HOLD`):
        *   `trend_model`: Analisa a direção e força da tendência.
        *   `orderflow_model`: Analisa o fluxo de ordens (pressão compradora vs. vendedora).
        *   `candles_model`: Reconhece padrões de candlestick (ex: engolfo, martelo).
        *   `sr_model`: Identifica níveis importantes de suporte e resistência.
        *   `volatility_model`: Mede a volatilidade atual para ajustar a estratégia.
    *   **Restrição:** Um modelo dedicado (`risk_model`) pode vetar a operação em um timeframe específico se o risco detectado for muito alto.

3.  **Cálculo da Pontuação de Confiança (em `core/confidence_engine.py`):**
    *   Todos os "votos" dos modelos são combinados com outros fatores analíticos, cada um com um peso específico, para gerar uma pontuação final de confiança. Os fatores incluem:
        *   **Votos dos modelos de IA**: O resultado da votação acima.
        *   **`regime_de_mercado`**: A pontuação do regime de mercado (passo 1).
        *   **`alinhamento_mtf`**: Verifica se múltiplos timeframes (`M5`, `M15`, `H1`) estão alinhados na mesma direção, indicando uma tendência mais forte.
        *   **`alignment_strength`**: Mede a "força" desse alinhamento de médias móveis.
        *   **`pontuacao_confluencia`**: Mede a qualidade técnica do setup (proximidade de indicadores-chave como EMAs e VWAP).
    *   **Restrição:** Se a pontuação de confiança final for abaixo de um limiar pré-definido (`CONFIDENCE_THRESHOLD`), a ação é `HOLD` (não fazer nada).

Se o resultado desta complexa análise for um sinal de `BUY` ou `SELL` com alta confiança, ele passa para a próxima etapa de validação.

---

### Etapa 2: Filtros Rígidos de Execução (em `core/live_trading_loop.py`)

Antes de enviar a ordem ao mercado, o sinal deve passar por uma sequência rigorosa de 9 filtros de segurança e estratégia. Se falhar em **qualquer um** deles, a ordem é cancelada.

1.  **Filtro de Cooldown:**
    *   Impede que uma nova operação seja aberta logo após outra no mesmo símbolo (`COOLDOWN_SECONDS`), evitando reentradas impulsivas.
    *   Impede uma operação na direção oposta por um período maior (`OPPOSITE_COOLDOWN`), garantindo que a análise anterior tenha tempo de se consolidar.

2.  **Filtro de Confiança Mínima:**
    *   A confiança calculada na Etapa 1 deve ser maior que um valor mínimo configurado (`CONFIDENCE_MIN`) para garantir que apenas as melhores oportunidades sejam consideradas.

3.  **Filtro de Pullback:**
    *   Verifica ativamente se há um padrão de pullback. Este filtro é único, pois pode *transformar* um sinal de `HOLD` em `SELL` se um pullback de venda claro for detectado, permitindo entradas táticas.

4.  **Filtro de Conflito em M1:**
    *   A direção do sinal não pode estar em conflito com a tendência de curtíssimo prazo do timeframe de **1 Minuto (M1)**. Isso evita entrar contra um movimento imediato forte.

5.  **Filtro de Tendência em M15:**
    *   A operação não pode ser contra a tendência principal do timeframe de **15 Minutos (M15)**, garantindo que a operação esteja a favor da estrutura de mercado mais estabelecida.

6.  **Filtro de Fibonacci:**
    *   Valida se o preço de entrada está em uma zona de retração ou extensão de Fibonacci considerada estratégica, usando dados do **M15**.

7.  **Filtro do Gerenciador de Risco (`RiskManager`):**
    *   Este é um dos filtros mais críticos, atuando como o "guardião financeiro" do sistema. Ele bloqueia a ordem se:
        *   O risco diário (`MAX_DAILY_RISK`) foi atingido.
        *   A relação Risco:Retorno da operação for menor que o mínimo aceitável (`MIN_RR`).
        *   O "Valor Esperado" (EV) da operação for negativo (matematicamente desvantajoso).
        *   O Stop Loss for inválido ou mal calculado.
        *   O lote calculado (baseado no `RISK_PER_TRADE`) for zero ou inválido.

8.  **Filtro de Distância Mínima:**
    *   Impede a abertura de uma nova ordem se ela estiver muito próxima (em preço) de outra já aberta na mesma direção, evitando a concentração de posições em uma faixa de preço estreita.

9.  **Filtro de Limite de Posições:**
    *   Verifica se o número máximo de posições na mesma direção (`MAX_POSITIONS_SAME_DIR`) ou o total de posições (`MAX_POSITIONS_TOTAL`) já foi atingido para o símbolo.

---

### Conclusão

Se, e somente se, o sinal gerado na Etapa 1 passar por **todos os 9 filtros** da Etapa 2, a função `send_order` é finalmente chamada para executar a ordem no MetaTrader 5, com lote, stop loss e take profit calculados e validados.
