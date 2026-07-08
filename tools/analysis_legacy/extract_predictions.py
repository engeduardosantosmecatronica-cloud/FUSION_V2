import json
from collections import defaultdict

data = defaultdict(list)
count = 0

with open('logs/decision_audit/decision_audit_20260527.jsonl', 'r') as f:
    for line in f:
        try:
            entry = json.loads(line)
            candidate = entry.get('candidate', {})
            result = entry.get('result', {})
            
            symbol = candidate.get('symbol', '')
            timeframe = candidate.get('timeframe', '')
            key = f"{symbol}/{timeframe}"
            
            data[key].append({
                'side': candidate.get('side', ''),
                'p_buy': candidate.get('p_buy', 0),
                'p_sell': candidate.get('p_sell', 0),
                'decision': result.get('decision', ''),
                'consensus': result.get('consensus_score', 0),
                'tradeability': result.get('tradeability_score', 0),
                'timestamp': candidate.get('timestamp', '')
            })
            count += 1
        except:
            pass

print(f"\n{'='*130}")
print(f"PREVISÕES ATUAIS DO FUSION_V2 - {count} ENTRADAS PROCESSADAS")
print(f"{'='*130}\n")

print(f"{'ATIVO':<12} | {'TF':<5} | {'DIR':<5} | {'P_BUY':<8} | {'P_SELL':<8} | {'DECISAO':<7} | {'CONSENSUS':<12} | {'TRADEABILITY':<12}")
print(f"{'-'*130}")

# Ordenar por ativo
for key in sorted(data.keys()):
    info = data[key][-1] if data[key] else {}
    symbol, tf = key.split('/')
    
    print(f"{symbol:<12} | {tf:<5} | {info.get('side', ''):<5} | "
          f"{info.get('p_buy', 0):<8.3f} | {info.get('p_sell', 0):<8.3f} | "
          f"{info.get('decision', ''):<7} | "
          f"{info.get('consensus', 0):<12.4f} | {info.get('tradeability', 0):<12.4f}")

print(f"\n{'='*130}")
print(f"Total de pares ativo/timeframe com previsões: {len(data)}")
print(f"{'='*130}\n")

# Resumo por decisão
decisions = {}
for key in data:
    info = data[key][-1] if data[key] else {}
    decision = info.get('decision', 'UNKNOWN')
    decisions[decision] = decisions.get(decision, 0) + 1

print("RESUMO DE DECISÕES:")
for decision, count_d in sorted(decisions.items(), key=lambda x: x[1], reverse=True):
    print(f"  {decision}: {count_d}")
