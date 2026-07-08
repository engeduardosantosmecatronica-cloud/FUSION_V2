import csv
import math
import pathlib

MIN_OPERABLE_SL = 15.0
outdir = pathlib.Path("reports/risk_drawdown")
summary_path = outdir / "max_drawdown_by_asset_summary.csv"
optimization_path = pathlib.Path(r"reports\signal_path_optimization\tp_sl_optimization_signal_path_outcomes_20260524_20260525_20260526_20260527_20260528_20260529_20260524_000000_to_20260529_101500_mt5offset6h_M15_H1_H4_path.csv")
recommended_path = pathlib.Path(r"reports\signal_path_optimization\tp_sl_recommended_signal_path_outcomes_20260524_20260525_20260526_20260527_20260528_20260529_20260524_000000_to_20260529_101500_mt5offset6h_M15_H1_H4_path.csv")

def to_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default

def ceil5(value):
    return math.ceil(float(value) / 5.0) * 5.0

with summary_path.open("r", encoding="utf-8", newline="") as fh:
    summary = list(csv.DictReader(fh))

best_by_symbol = {}
best_by_symbol_operable = {}
with optimization_path.open("r", encoding="utf-8", newline="") as fh:
    for row in csv.DictReader(fh):
        symbol = row.get("symbol", "")
        score = to_float(row.get("score"), -10**9)
        row["_score"] = score
        if symbol not in best_by_symbol or score > best_by_symbol[symbol]["_score"]:
            best_by_symbol[symbol] = row
        if to_float(row.get("sl_net_points")) >= MIN_OPERABLE_SL:
            if symbol not in best_by_symbol_operable or score > best_by_symbol_operable[symbol]["_score"]:
                best_by_symbol_operable[symbol] = row

recommended_symbols = set()
with recommended_path.open("r", encoding="utf-8", newline="") as fh:
    for row in csv.DictReader(fh):
        if row.get("recommended", "").lower() == "true" and to_float(row.get("sl_net_points")) >= MIN_OPERABLE_SL:
            recommended_symbols.add(row["symbol"])

rows = []
for row in summary:
    symbol = row["symbol"]
    p95 = float(row["worst_p95_drawdown_points"])
    worst = float(row["worst_drawdown_points"])
    conservative_sl = max(MIN_OPERABLE_SL, ceil5(p95 * 1.10))
    disaster_sl = max(conservative_sl, ceil5(worst * 1.05))
    raw_best = best_by_symbol.get(symbol, {})
    best = best_by_symbol_operable.get(symbol, {})
    raw_sl = to_float(raw_best.get("sl_net_points", 0.0)) if raw_best else 0.0
    was_inoperable = bool(raw_best) and raw_sl < MIN_OPERABLE_SL
    is_recommended = symbol in recommended_symbols
    if is_recommended:
        note = "OK para shadow/validacao com SL operavel"
    elif was_inoperable and best:
        note = "Melhor antigo usava SL < 15 e foi descartado; alternativa operavel ainda nao passou criterios"
    elif was_inoperable:
        note = "Melhor antigo usava SL < 15 e foi descartado; sem alternativa operavel robusta"
    else:
        note = "Nao passou criterios; usar apenas como limite de risco ou exigir confirmacao extra"
    rows.append({
        "symbol": symbol,
        "signals_total": row["signals_total"],
        "worst_drawdown_points": row["worst_drawdown_points"],
        "p95_drawdown_points": row["worst_p95_drawdown_points"],
        "conservative_sl_from_p95_points": int(conservative_sl),
        "disaster_sl_from_worst_points": int(disaster_sl),
        "optimized_group_operable": (best.get("timeframe", "") + " " + best.get("side", "")).strip(),
        "optimized_tp_points_operable": best.get("tp_net_points", ""),
        "optimized_sl_points_operable": best.get("sl_net_points", ""),
        "optimized_win_rate_operable": best.get("win_rate", ""),
        "optimized_avg_points_operable": best.get("avg_points", ""),
        "optimized_max_loss_streak_operable": best.get("max_loss_streak", ""),
        "discarded_best_due_sl_lt_15": str(was_inoperable),
        "recommended_by_backtest": str(is_recommended),
        "operational_note": note,
    })

out = outdir / "stop_take_plan_by_asset.csv"
with out.open("w", encoding="utf-8", newline="") as fh:
    writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

md = outdir / "stop_take_plan_by_asset.md"
lines = [
    "# Plano de SL/TP por ativo baseado em drawdown\n",
    "\nRegra operacional: stop menor que 15 pontos e inviavel (`MIN_OPERABLE_SL = 15`). Qualquer otimizacao com `SL < 15` foi descartada da recomendacao operacional.\n",
    "\n`conservative_sl_from_p95_points` = max(15, P95 do drawdown liquido do ativo + 10%), arredondado para cima em blocos de 5 pontos.\n",
    "`disaster_sl_from_worst_points` = pior drawdown observado + 5%, arredondado para cima, nunca menor que o SL conservador. Use como limite maximo de emergencia, nao como stop normal.\n",
    "\n| Ativo | Sinais | Pior DD | P95 DD | SL conservador | SL desastre | Melhor grupo operavel | TP opt | SL opt | Descartou SL<15? | Recomendado? | Nota |\n",
    "|---|---:|---:|---:|---:|---:|---|---:|---:|---|---|---|\n",
]
for row in rows:
    lines.append("| {symbol} | {signals_total} | {worst_drawdown_points} | {p95_drawdown_points} | {conservative_sl_from_p95_points} | {disaster_sl_from_worst_points} | {optimized_group_operable} | {optimized_tp_points_operable} | {optimized_sl_points_operable} | {discarded_best_due_sl_lt_15} | {recommended_by_backtest} | {operational_note} |\n".format(**row))
md.write_text("".join(lines), encoding="utf-8")

print(out)
print(md)
for row in rows:
    print("{symbol}: SL95={conservative_sl_from_p95_points} opt={optimized_group_operable} TP={optimized_tp_points_operable} SL={optimized_sl_points_operable} discard_lt15={discarded_best_due_sl_lt_15} rec={recommended_by_backtest}".format(**row))
