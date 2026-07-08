import shutil
from pathlib import Path
import pandas as pd


MODELS_DIR = Path("models")
MODELS_EXPR_DIR = Path("models_expr")
OUTPUT_DIR = Path("models_principal")

df1 = pd.read_csv(MODELS_DIR / "models_index.csv").copy()
df2 = pd.read_csv(MODELS_EXPR_DIR / "models_index.csv").copy()

df1["source"] = "models"
df2["source"] = "models_expr"

full = df1.merge(df2, on=["symbol", "timeframe"], how="outer", suffixes=("_v1", "_v2"), indicator=True)

selected = []

for _, row in full.iterrows():
    sym = row["symbol"]
    tf = row["timeframe"]

    if row["_merge"] == "left_only":
        source_dir = MODELS_DIR
        source_name = "models"
        acc = row["accuracy_v1"]
        buy_th = row["buy_threshold_v1"]
        sell_th = row["sell_threshold_v1"]
    elif row["_merge"] == "right_only":
        source_dir = MODELS_EXPR_DIR
        source_name = "models_expr"
        acc = row["accuracy_v2"]
        buy_th = row["buy_threshold_v2"]
        sell_th = row["sell_threshold_v2"]
    else:
        if row["accuracy_v2"] > row["accuracy_v1"]:
            source_dir = MODELS_EXPR_DIR
            source_name = "models_expr"
            acc = row["accuracy_v2"]
            buy_th = row["buy_threshold_v2"]
            sell_th = row["sell_threshold_v2"]
        else:
            source_dir = MODELS_DIR
            source_name = "models"
            acc = row["accuracy_v1"]
            buy_th = row["buy_threshold_v1"]
            sell_th = row["sell_threshold_v1"]

    dst = OUTPUT_DIR / sym / tf
    dst.mkdir(parents=True, exist_ok=True)

    for fname in ["model.pkl", "scaler.pkl", "meta.pkl"]:
        src_file = source_dir / sym / tf / fname
        if src_file.exists():
            shutil.copy2(str(src_file), str(dst / fname))

    selected.append({
        "symbol": sym,
        "timeframe": tf,
        "accuracy": acc,
        "buy_threshold": buy_th,
        "sell_threshold": sell_th,
        "source": source_name,
    })

index_df = pd.DataFrame(selected)
index_df.to_csv(OUTPUT_DIR / "models_index.csv", index=False)

print(f"Modelos exportados para {OUTPUT_DIR}: {len(selected)}")
print(f"  - Origin: models:       {(index_df['source'] == 'models').sum()}")
print(f"  - Origin: models_expr:  {(index_df['source'] == 'models_expr').sum()}")
print(f"  - Acc media: {index_df['accuracy'].mean():.4f}")
print(f"  - Simbolos: {sorted(index_df['symbol'].unique())}")
