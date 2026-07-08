import json
from collections import defaultdict

# Dicionário para armazenar previsões
predictions = defaultdict(lambda: {})

with open('logs/decision_audit/decision_audit_20260527.jsonl', 'r') as f:
    for line in f:
        try:
            entry = json.loads(line)
            candidate = entry.get('candidate', {})
            
            symbol = candidate.get('symbol', '')
            timeframe = candidate.get('timeframe', '')
            side = candidate.get('side', '')
            
            # Determinar previsão: BUY, SELL ou WAIT (bloqueado = WAIT)
            prediction = 'BUY' if side == 'BUY' else 'SELL' if side == 'SELL' else 'WAIT'
            
            # Armazenar a última previsão para cada ativo/timeframe
            predictions[symbol][timeframe] = prediction
        except:
            pass

# Ordem dos timeframes
timeframes = ['M5', 'M15', 'M30', 'H1', 'H4', 'D1']

# Lista de ativos na ordem fornecida
assets = [
    'AUDCAD', 'AUDCHF', 'AUDJPY', 'AUDNOK', 'AUDNZD', 'AUDSEK', 'AUDSGD', 'AUDUSD', 'AUS200',
    'BTCUSD', 'CADCHF', 'CADJPY', 'CHFDKK', 'CHFJPY', 'CHFNOK', 'CHFSGD', 'DOTUSD', 'ETHUSD',
    'EURAUD', 'EURCAD', 'EURCHF', 'EURGBP', 'EURHKD', 'EURHUF', 'EURJPY', 'EURMXN', 'EURNOK',
    'EURNZD', 'EURPLN', 'EURSEK', 'EURUSD', 'GBPAUD', 'GBPCAD', 'GBPCHF', 'GBPJPY', 'GBPNZD',
    'GBPUSD', 'GOLD', 'NZDCAD', 'NZDCHF', 'NZDJPY', 'NZDSGD', 'NZDUSD', 'USDCAD', 'USDCHF', 'USDJPY'
]

# Cabeçalho da tabela
print("\n" + "="*150)
print("PREVISÕES DO FUSION_V2 - 27/05/2026")
print("="*150)
print(f"\n{'ATIVO':<12} | {'M5':<6} | {'M15':<6} | {'M30':<6} | {'H1':<6} | {'H4':<6} | {'D1':<6}")
print("-"*150)

# Dados da tabela
for asset in assets:
    if asset in predictions:
        row = f"{asset:<12} |"
        for tf in timeframes:
            pred = predictions[asset].get(tf, '-')
            row += f" {pred:<6} |"
        print(row)

print("\n" + "="*150)
print(f"Total de ativos com previsões: {len(predictions)}")
print("="*150 + "\n")
