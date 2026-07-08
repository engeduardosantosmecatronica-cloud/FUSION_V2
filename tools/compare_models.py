import pandas as pd

df1 = pd.read_csv("models/models_index.csv")
df2 = pd.read_csv("models_expr/models_index.csv")

df1["source"] = "models"
df2["source"] = "models_expr"

merged = df1.merge(df2, on=["symbol", "timeframe"], suffixes=("_v1", "_v2"))

merged["acc_diff"] = merged["accuracy_v2"] - merged["accuracy_v1"]
merged["buy_diff"] = merged["buy_threshold_v2"] - merged["buy_threshold_v1"]
merged["sell_diff"] = merged["sell_threshold_v2"] - merged["sell_threshold_v1"]

print("=" * 110)
print(f"{'COMPARACAO: models (hardcoded) vs models_expr (expressoes)':^110}")
print("=" * 110)
print(
    f"{'SYMBOL':<10} | {'TF':<5} | {'Acc_v1':>8} | {'Acc_v2':>8} | {'Diff':>8} | "
    f"{'BuyTh_v1':>8} | {'BuyTh_v2':>8} | {'SellTh_v1':>8} | {'SellTh_v2':>8}"
)
print("-" * 110)

for _, row in merged.sort_values("acc_diff", ascending=False).iterrows():
    flag = " ***" if abs(row["acc_diff"]) > 0.01 else ""
    print(
        f"{row['symbol']:<10} | {row['timeframe']:<5} | "
        f"{row['accuracy_v1']:>8.4f} | {row['accuracy_v2']:>8.4f} | "
        f"{row['acc_diff']:>+8.4f}{flag} | "
        f"{row['buy_threshold_v1']:>8.4f} | {row['buy_threshold_v2']:>8.4f} | "
        f"{row['sell_threshold_v1']:>8.4f} | {row['sell_threshold_v2']:>8.4f}"
    )

print("-" * 110)
print(f"\nRESUMO:")
print(f"  Modelos comparados: {len(merged)}")
print(f"  Acc media v1 (hardcoded): {merged['accuracy_v1'].mean():.4f}")
print(f"  Acc media v2 (expressoes): {merged['accuracy_v2'].mean():.4f}")
print(f"  Diferenca media: {merged['acc_diff'].mean():+.4f}")
print(f"  Modelos onde v2 > v1: {(merged['acc_diff'] > 0).sum()}")
print(f"  Modelos onde v1 > v2: {(merged['acc_diff'] < 0).sum()}")
print(f"  Modelos com acc identica: {(abs(merged['acc_diff']) < 0.0001).sum()}")
