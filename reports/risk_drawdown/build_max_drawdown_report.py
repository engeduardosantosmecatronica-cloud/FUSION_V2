import csv
import math
import statistics
import pathlib
import datetime

src = pathlib.Path(r"reports\signal_path_outcomes_m1_spread_targets\signal_path_outcomes_20260524_20260525_20260526_20260527_20260528_20260529_20260524_000000_to_20260529_101500_mt5offset6h_M15_H1_H4_path.csv")
outdir = pathlib.Path("reports/risk_drawdown")
outdir.mkdir(parents=True, exist_ok=True)

groups = {}

def to_float(value):
    try:
        return float(value)
    except Exception:
        return None

with src.open("r", encoding="utf-8", newline="") as fh:
    reader = csv.DictReader(fh)
    for row in reader:
        if row.get("status") != "ok":
            continue
        key = (
            row.get("symbol", "").upper(),
            row.get("signal_timeframe", "").upper(),
            row.get("side", "").upper(),
        )
        mae = to_float(row.get("w1p0_net_mae_points"))
        mfe = to_float(row.get("w1p0_net_mfe_points"))
        close = to_float(row.get("w1p0_net_close_points"))
        spread = to_float(row.get("entry_spread_points"))
        if mae is None or mfe is None:
            continue
        group = groups.setdefault(key, {"mae": [], "mfe": [], "close": [], "spread": []})
        group["mae"].append(mae)
        group["mfe"].append(mfe)
        if close is not None:
            group["close"].append(close)
        if spread is not None:
            group["spread"].append(spread)

def percentile(values, pct):
    values = sorted(v for v in values if math.isfinite(v))
    if not values:
        return 0.0
    k = (len(values) - 1) * pct / 100
    lo = math.floor(k)
    hi = math.ceil(k)
    if lo == hi:
        return values[int(k)]
    return values[lo] * (hi - k) + values[hi] * (k - lo)

def rnd(value):
    return round(float(value), 2)

rows = []
for (symbol, timeframe, side), group in groups.items():
    signals = len(group["mae"])
    if signals == 0:
        continue
    worst = max(group["mae"])
    p95 = percentile(group["mae"], 95)
    p90 = percentile(group["mae"], 90)
    med = statistics.median(group["mae"])
    mfe_med = statistics.median(group["mfe"])
    mfe_p75 = percentile(group["mfe"], 75)
    spread_med = statistics.median(group["spread"]) if group["spread"] else 0.0
    suggested_sl = max(10.0, math.ceil((p95 * 1.10) / 5) * 5)
    suggested_tp = max(5.0, math.floor(min(mfe_p75, suggested_sl * 0.8) / 5) * 5)
    rows.append({
        "symbol": symbol,
        "timeframe": timeframe,
        "side": side,
        "signals": signals,
        "max_drawdown_net_mae_points": rnd(worst),
        "p95_drawdown_net_mae_points": rnd(p95),
        "p90_drawdown_net_mae_points": rnd(p90),
        "median_drawdown_net_mae_points": rnd(med),
        "median_favorable_net_mfe_points": rnd(mfe_med),
        "p75_favorable_net_mfe_points": rnd(mfe_p75),
        "median_spread_points": rnd(spread_med),
        "suggested_sl_points": rnd(suggested_sl),
        "suggested_tp_points": rnd(suggested_tp),
        "tp_sl_ratio": rnd(suggested_tp / suggested_sl if suggested_sl else 0),
    })

rows.sort(key=lambda item: (item["symbol"], item["timeframe"], item["side"]))
if not rows:
    raise SystemExit("Nenhum grupo encontrado")

csv_path = outdir / "max_drawdown_by_asset_timeframe_side.csv"
with csv_path.open("w", encoding="utf-8", newline="") as fh:
    writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

asset_rows = []
for symbol in sorted({item["symbol"] for item in rows}):
    symbol_rows = [item for item in rows if item["symbol"] == symbol]
    worst = max(item["max_drawdown_net_mae_points"] for item in symbol_rows)
    p95 = max(item["p95_drawdown_net_mae_points"] for item in symbol_rows)
    total = sum(item["signals"] for item in symbol_rows)
    reference = max(symbol_rows, key=lambda item: (item["signals"], -item["p95_drawdown_net_mae_points"]))
    asset_rows.append({
        "symbol": symbol,
        "signals_total": total,
        "worst_drawdown_points": worst,
        "worst_p95_drawdown_points": p95,
        "reference_group": reference["timeframe"] + " " + reference["side"],
        "suggested_sl_points": reference["suggested_sl_points"],
        "suggested_tp_points": reference["suggested_tp_points"],
    })

asset_path = outdir / "max_drawdown_by_asset_summary.csv"
with asset_path.open("w", encoding="utf-8", newline="") as fh:
    writer = csv.DictWriter(fh, fieldnames=list(asset_rows[0].keys()))
    writer.writeheader()
    writer.writerows(asset_rows)

md_path = outdir / "max_drawdown_summary.md"
lines = [
    "# Maior drawdown por ativo\n",
    f"Fonte: `{src}`\n",
    f"Gerado em: {datetime.datetime.now().isoformat(timespec='seconds')}\n",
    "\nInterpretacao: drawdown aqui = maior MAE liquido (`w1p0_net_mae_points`) observado apos entrada, em pontos, ja considerando spread. Para stop operacional, prefira `p95` + margem em vez do pior absoluto, porque o pior absoluto pode ser outlier.\n",
    "\n## Resumo por ativo\n",
    "| Ativo | Sinais | Pior DD pts | P95 DD pts | Grupo ref | SL sugerido | TP sugerido |\n",
    "|---|---:|---:|---:|---|---:|---:|\n",
]
for item in asset_rows:
    lines.append("| {symbol} | {signals_total} | {worst_drawdown_points} | {worst_p95_drawdown_points} | {reference_group} | {suggested_sl_points} | {suggested_tp_points} |\n".format(**item))
lines.extend([
    "\n## Top grupos por pior drawdown\n",
    "| Ativo | TF | Lado | Sinais | Pior DD | P95 DD | Med DD | Med MFE | SL sug | TP sug |\n",
    "|---|---|---|---:|---:|---:|---:|---:|---:|---:|\n",
])
for item in sorted(rows, key=lambda row: row["max_drawdown_net_mae_points"], reverse=True)[:30]:
    lines.append("| {symbol} | {timeframe} | {side} | {signals} | {max_drawdown_net_mae_points} | {p95_drawdown_net_mae_points} | {median_drawdown_net_mae_points} | {median_favorable_net_mfe_points} | {suggested_sl_points} | {suggested_tp_points} |\n".format(**item))
md_path.write_text("".join(lines), encoding="utf-8")

print(csv_path)
print(asset_path)
print(md_path)
print("---")
for item in asset_rows:
    print("{symbol}: worst={worst_drawdown_points} p95={worst_p95_drawdown_points} ref={reference_group} SL={suggested_sl_points} TP={suggested_tp_points}".format(**item))
