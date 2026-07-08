Ótima ideia! Vou criar um arquivo de documentação/roadmap para acompanhar o progresso do projeto.

## 📋 `PROJECT_STATUS.md`

```markdown
# 🧠 OMNIS - Status do Projeto

## 📊 Visão Geral

**Objetivo:** Sistema de trading algorítmico baseado em ensemble de especialistas e machine learning.

**Foco Atual:** Treinar primeiro modelo (XGBoost) para EURUSD em timeframe H1.

---

## ✅ O QUE JÁ TEMOS

### 1. Estrutura de Diretórios
```
projeto_ml_trading/
├── config/
│   └── config.py                 # Configurações centralizadas (otimizado)
├── connectors/
│   ├── mt5_connector.py          # Conexão com MT5 (existente)
│   └── data_loader.py             # Carregamento de dados (existente)
├── features/
│   └── feature_extractor.py       # Extração de features (existente)
├── experts/
│   ├── __init__.py                # (vazio)
│   ├── trend_master.py            # Esqueleto implementado
│   └── zone_mapper.py             # (pendente)
├── models/                         # Modelos treinados (vazio)
├── logs/                           # Logs do sistema (vazio)
├── resultados/                     # Resultados de backtests (vazio)
├── outputs/                        # Outputs diversos (vazio)
├── HISTORICO_FOREX/                 # Dados históricos (CSVs)
├── train_model.py                  # Script principal (esqueleto)
├── utils.py                        # Funções utilitárias (esqueleto)
└── PROJECT_STATUS.md               # Este arquivo
```

### 2. Configurações (`config.py`)
- ✅ Caminhos do projeto definidos
- ✅ Símbolos configurados (foco: EURUSD)
- ✅ Timeframes configurados (foco: H1)
- ✅ Horizontes de previsão (5, 10, 20 candles)
- ✅ Especialistas ativos: `trend_master`, `zone_mapper`
- ✅ Modelos ativos: `xgboost`
- ✅ Features base definidas
- ✅ Configurações de treinamento
- ✅ Grid de hiperparâmetros XGBoost

### 3. Especialistas Implementados
#### TrendMaster (`trend_master.py`)
- ✅ Classe base estruturada
- ✅ Método `calculate_features()`
- ✅ Método `get_signal()`
- ✅ Indicadores: MA(200), ADX
- ✅ Feature: `trend_master_signal`

#### ZoneMapper (PENDENTE)

### 4. Scripts Base
- ✅ `train_model.py` - Esqueleto com pipeline completo
- ✅ `utils.py` - Funções `prepare_target()` e `split_data()`

### 5. Integrações
- ✅ `mt5_connector.py` (existente, para referência futura)
- ✅ `data_loader.py` (existente)
- ✅ `feature_extractor.py` (existente, para fallback)

---

## 🚧 EM ANDAMENTO

### Prioridade Alta
- [ ] **Completar especialistas base** (TrendMaster e ZoneMapper)
  - [ ] Finalizar `trend_master.py` com cálculos corretos
  - [ ] Implementar `zone_mapper.py` completo
  - [ ] Testar integração com `train_model.py`

- [ ] **Adaptar `train_model.py`** para usar nova estrutura
  - [ ] Integrar com `config.py` atualizado
  - [ ] Carregar dados do CSV correto
  - [ ] Calcular features dos especialistas
  - [ ] Treinar XGBoost com parâmetros otimizados

- [ ] **Testar com dados reais**
  - [ ] Colocar arquivo CSV em `HISTORICO_FOREX/EURUSD_H1.csv`
  - [ ] Executar treinamento
  - [ ] Validar resultados

### Prioridade Média
- [ ] **Implementar PullbackHunter**
  - [ ] Fibonacci retracement
  - [ ] Médias rápidas (9/21)
  - [ ] Sinal de pullback

- [ ] **Implementar ExhaustionDetector**
  - [ ] RSI com divergências
  - [ ] Estocástico
  - [ ] MACD divergências

- [ ] **Adicionar mais timeframes**
  - [ ] H4 para validação
  - [ ] M30 para scalping (futuro)

### Prioridade Baixa
- [ ] **Implementar demais especialistas**
  - [ ] PatternTrigger
  - [ ] VolatilityGauge
  - [ ] StatsQuant
  - [ ] FlowAggressor (depende de dados de order flow)

- [ ] **Adicionar outros modelos**
  - [ ] LightGBM
  - [ ] Random Forest
  - [ ] Ensemble voting

---

## 🔧 PRÓXIMAS MUDANÇAS (CHECKLIST DETALHADO)

### 📁 Arquivo: `experts/trend_master.py` (completar)

```python
# TODO: Adicionar dependências
# import talib  # Opcional, para cálculos precisos

class TrendMaster:
    def __init__(self, ma_period=200, adx_period=14):
        # OK
        pass
    
    def calculate_features(self, df):
        # TODO: Substituir cálculo manual do ADX por talib (se disponível)
        # TODO: Adicionar normalização dos sinais
        # TODO: Adicionar tratamento de NaN
        pass
    
    def get_signal(self, df):
        # TODO: Retornar sinal entre -1 e 1
        # TODO: Incluir confiança baseada no ADX
        pass
```

### 📁 Arquivo: `experts/zone_mapper.py` (novo)

```python
"""
Zone Mapper - Especialista em Suporte e Resistência
- Pivot Points
- Volume Profile (Point of Control)
- Máximas e Mínimas recentes
"""
# TODO: Implementar classe completa
```

### 📁 Arquivo: `train_model.py` (adaptar)

```python
# TODO: Substituir imports para usar config.py
# from config import SIMBOLOS, TIMEFRAMES_TREINO, TRAIN_CONFIG

# TODO: Adicionar carregamento dinâmico dos especialistas ativos
# active_experts = [eval(expert)() for expert in ESPECIALISTAS_ATIVOS]

# TODO: Adaptar prepare_target para usar HORIZONTES do config

# TODO: Adicionar salvamento da lista de features

# TODO: Adicionar logging estruturado
```

### 📁 Arquivo: `utils.py` (completar)

```python
# TODO: Adicionar função para calcular métricas por especialista
# TODO: Adicionar função para normalizar sinais
# TODO: Adicionar função para detectar overfitting
```

---

## 📊 DADOS NECESSÁRIOS

### Arquivo CSV para primeiro teste
```
Local: HISTORICO_FOREX/EURUSD_H1.csv
Formato: timestamp,open,high,low,close,volume
Período: Mínimo 2 anos de dados H1 (~17.520 candles)
Fonte: MT5 export ou Dukascopy
```

### Colunas esperadas no CSV
```csv
time,open,high,low,close,volume
2024-01-01 00:00:00,1.10450,1.10480,1.10420,1.10460,1000
...
```

---

## 🐛 BUGS CONHECIDOS / LIMITAÇÕES

1. **Cálculo manual do ADX** - Pode ter imprecisões. Considerar usar TA-Lib.
2. **Tratamento de NaN** - Necessário garantir que todas as features são calculadas corretamente.
3. **Memória** - Dataset grande pode exigir otimizações.
4. **Look-ahead bias** - Garantir que `shift(-horizon)` não vaza informação futura.

---

## 📈 PRÓXIMOS MARCOS

### Marco 1: MVP (1 especialista, 1 ativo, 1 timeframe)
- [x] Configuração base
- [ ] TrendMaster funcional
- [ ] Pipeline de treino rodando
- [ ] Modelo salvo com métricas iniciais

### Marco 2: Ensemble básico (2+ especialistas)
- [ ] ZoneMapper implementado
- [ ] PullbackHunter implementado
- [ ] Votação entre especialistas
- [ ] Comparação de performance

### Marco 3: Múltiplos timeframes
- [ ] Treino em H1 e H4
- [ ] Modelos separados por timeframe
- [ ] Estratégia de combinação

### Marco 4: Produção
- [ ] Backtesting completo
- [ ] Conexão com MT5 em tempo real
- [ ] Gerenciamento de risco integrado
- [ ] Dashboard de monitoramento

---

## 📝 NOTAS E OBSERVAÇÕES

### Decisões de Arquitetura
- **Especialistas como features**: Cada especialista gera features que alimentam o modelo
- **Votação ponderada**: Pesos configuráveis no `config.py`
- **ML como cérebro**: XGBoost aprende a combinar os sinais dos especialistas

### Boas Práticas
- Sempre validar em dados fora da amostra
- Manter separação treino/validação/teste temporal
- Documentar cada especialista com referências teóricas
- Versionar modelos treinados

### Referências
- [ ] Adicionar links para artigos sobre cada indicador
- [ ] Documentar fórmulas matemáticas
- [ ] Criar exemplos de uso

---

## 👥 COLABORADORES

- **Arquiteto principal**: [Seu nome]
- **Revisão**: Pendente

---

*Última atualização: 02/03/2026*
```

## 📁 `CHANGELOG.md` (para registrar alterações)

```markdown
# 📦 CHANGELOG

Todas as mudanças notáveis neste projeto serão documentadas aqui.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

## [Não Publicado]

### Adicionado
- Estrutura inicial do projeto
- Configuração centralizada (`config.py`) com foco em EURUSD H1
- Especialista TrendMaster (esqueleto)
- Script de treinamento (`train_model.py`) com pipeline base
- Utilitários (`utils.py`) com funções de preparação de dados
- Documentação de status do projeto (`PROJECT_STATUS.md`)

### Modificado
- Adaptado `config.py` para arquitetura de especialistas
- Comentadas configurações não utilizadas para manter foco

### Pendente
- Implementação completa do TrendMaster
- Criação do ZoneMapper
- Teste com dados reais
```

Estes arquivos vão te ajudar a:
1. **Manter o foco** no que é importante agora
2. **Documentar decisões** para referência futura
3. **Compartilhar progresso** se trabalhar em equipe
4. **Não esquecer** tasks importantes

