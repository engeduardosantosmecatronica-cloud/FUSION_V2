from __future__ import annotations

from pathlib import Path
import math

import numpy as np
import pandas as pd


RESUMO_CSV = "backteste_rapido_resumo.csv"
DINAMICA_CSV = "backteste_rapido_dinamica_entradas.csv"

OUT_ATIVO_TF = "features/features_backteste_ativo_timeframe.csv"
OUT_DINAMICA = "features/features_backteste_dinamica.csv"
OUT_MODELAGEM = "features_backteste_modelagem.csv"

TARGETS = [100, 200, 300, 400, 500]
MIN_ENTRADAS = 500


def round_up(value: float, step: int = 10, minimum: int = 50) -> int:
    if pd.isna(value):
        return minimum
    return max(minimum, int(math.ceil(value / step) * step))


def safe_div(a: pd.Series | float, b: pd.Series | float) -> pd.Series | float:
    return a / (b + 1e-9)


def add_common_metrics(df: pd.DataFrame, entries_col: str = "entradas") -> pd.DataFrame:
    result = df.copy()
    result["losses"] = result[entries_col] - result["wins"]
    result["loss_rate"] = 100.0 - result["win_rate"]
    result["win_rate_norm"] = result["win_rate"] / 100.0
    result["target_efficiency"] = result["target"] * result["win_rate_norm"]
    result["favor_contra_ratio"] = safe_div(result["favor_media"], result["contra_media"])
    result["recovery_favor_ratio"] = safe_div(result["favor_apos_voltar_media"], result["favor_media"])
    result["risk_penalty"] = result["contra_media"] * (1.0 - result["win_rate_norm"])
    result["score"] = result["target_efficiency"] - result["risk_penalty"]
    result["sample_weight"] = np.log1p(result[entries_col])
    result["sample_ok"] = result[entries_col] >= MIN_ENTRADAS
    result["stop_curto"] = result["contra_media"].apply(lambda n: round_up(float(n) * 1.25))
    result["stop_sugerido"] = result["contra_media"].apply(lambda n: round_up(float(n) * 1.50))
    result["stop_folgado"] = result["contra_media"].apply(lambda n: round_up(float(n) * 2.00))
    return result


def build_target_features(resumo: pd.DataFrame) -> pd.DataFrame:
    enriched = add_common_metrics(resumo)
    rows = []

    for (symbol, timeframe), group in enriched.groupby(["symbol", "timeframe"], sort=True):
        row = {"symbol": symbol, "timeframe": timeframe}
        group_by_target = group.set_index("target")

        for target in TARGETS:
            if target not in group_by_target.index:
                continue
            item = group_by_target.loc[target]
            prefix = f"tp{target}"
            row[f"{prefix}_entradas"] = int(item["entradas"])
            row[f"{prefix}_wins"] = int(item["wins"])
            row[f"{prefix}_win_rate"] = float(item["win_rate"])
            row[f"{prefix}_score"] = float(item["score"])
            row[f"{prefix}_target_efficiency"] = float(item["target_efficiency"])

        first = group.iloc[0]
        row["entradas_media_por_alvo"] = float(group["entradas"].mean())
        row["favor_media"] = float(first["favor_media"])
        row["contra_media"] = float(first["contra_media"])
        row["favor_apos_voltar_media"] = float(first["favor_apos_voltar_media"])
        row["favor_contra_ratio"] = float(first["favor_contra_ratio"])
        row["recovery_favor_ratio"] = float(first["recovery_favor_ratio"])
        row["stop_curto"] = int(first["stop_curto"])
        row["stop_sugerido"] = int(first["stop_sugerido"])
        row["stop_folgado"] = int(first["stop_folgado"])

        candidates = group[group["sample_ok"]].copy()
        if candidates.empty:
            candidates = group.copy()
        best = candidates.sort_values(["score", "target", "win_rate", "entradas"], ascending=[False, False, False, False]).iloc[0]
        row["best_target"] = int(best["target"])
        row["best_target_win_rate"] = float(best["win_rate"])
        row["best_target_score"] = float(best["score"])
        row["best_target_entries"] = int(best["entradas"])

        if 100 in group_by_target.index and 500 in group_by_target.index:
            row["win_rate_decay_100_to_500"] = float(group_by_target.loc[100, "win_rate"] - group_by_target.loc[500, "win_rate"])
            row["score_decay_100_to_500"] = float(group_by_target.loc[100, "score"] - group_by_target.loc[500, "score"])
        else:
            row["win_rate_decay_100_to_500"] = np.nan
            row["score_decay_100_to_500"] = np.nan

        rows.append(row)

    return pd.DataFrame(rows)


def build_dynamic_features(dinamica: pd.DataFrame) -> pd.DataFrame:
    rename_map = {"trades": "entradas"}
    base = dinamica.rename(columns=rename_map).copy()
    enriched = add_common_metrics(base, entries_col="entradas")

    enriched["pattern"] = (
        enriched["direcao"].astype(str)
        + "_"
        + enriched["entrada_posicao"].astype(str)
        + "_"
        + enriched["nivel_candle_anterior"].astype(str)
        + "_prev_"
        + enriched["candle_anterior"].astype(str)
    )
    enriched["pattern_is_buy"] = (enriched["direcao"] == "compra").astype(int)
    enriched["pattern_is_sell"] = (enriched["direcao"] == "venda").astype(int)
    enriched["prev_is_alta"] = (enriched["candle_anterior"] == "alta").astype(int)
    enriched["prev_is_baixa"] = (enriched["candle_anterior"] == "baixa").astype(int)
    enriched["prev_is_doji"] = (enriched["candle_anterior"] == "doji").astype(int)
    return enriched


def build_modeling_table(target_features: pd.DataFrame, dynamic_features: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (symbol, timeframe), group in dynamic_features.groupby(["symbol", "timeframe"], sort=True):
        row = {"symbol": symbol, "timeframe": timeframe}

        for target in TARGETS:
            tg = group[group["target"] == target]
            if tg.empty:
                continue
            best_pattern = tg[tg["sample_ok"]].copy()
            if best_pattern.empty:
                best_pattern = tg.copy()
            best_pattern = best_pattern.sort_values(
                ["score", "win_rate", "entradas"],
                ascending=[False, False, False],
            ).iloc[0]
            prefix = f"tp{target}_best_pattern"
            row[f"{prefix}_name"] = best_pattern["pattern"]
            row[f"{prefix}_wr"] = float(best_pattern["win_rate"])
            row[f"{prefix}_entries"] = int(best_pattern["entradas"])
            row[f"{prefix}_score"] = float(best_pattern["score"])
            row[f"{prefix}_stop"] = int(best_pattern["stop_sugerido"])

        for side in ["compra", "venda"]:
            sg = group[group["direcao"] == side]
            if not sg.empty:
                row[f"{side}_entries"] = int(sg["entradas"].sum())
                row[f"{side}_avg_wr"] = float(np.average(sg["win_rate"], weights=sg["entradas"]))
                row[f"{side}_best_score"] = float(sg["score"].max())
            else:
                row[f"{side}_entries"] = 0
                row[f"{side}_avg_wr"] = np.nan
                row[f"{side}_best_score"] = np.nan

        for prev in ["alta", "baixa", "doji"]:
            pg = group[group["candle_anterior"] == prev]
            if not pg.empty:
                row[f"prev_{prev}_entries"] = int(pg["entradas"].sum())
                row[f"prev_{prev}_avg_wr"] = float(np.average(pg["win_rate"], weights=pg["entradas"]))
                row[f"prev_{prev}_best_score"] = float(pg["score"].max())
            else:
                row[f"prev_{prev}_entries"] = 0
                row[f"prev_{prev}_avg_wr"] = np.nan
                row[f"prev_{prev}_best_score"] = np.nan

        rows.append(row)

    model = pd.DataFrame(rows)
    return target_features.merge(model, on=["symbol", "timeframe"], how="left")


def main() -> None:
    root = Path(__file__).resolve().parent
    resumo_path = root / RESUMO_CSV
    dinamica_path = root / DINAMICA_CSV

    if not resumo_path.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {resumo_path}")
    if not dinamica_path.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {dinamica_path}")

    resumo = pd.read_csv(resumo_path)
    dinamica = pd.read_csv(dinamica_path)

    target_features = build_target_features(resumo)
    dynamic_features = build_dynamic_features(dinamica)
    modeling_features = build_modeling_table(target_features, dynamic_features)

    target_features.to_csv(root / OUT_ATIVO_TF, index=False)
    dynamic_features.to_csv(root / OUT_DINAMICA, index=False)
    modeling_features.to_csv(root / OUT_MODELAGEM, index=False)

    print(f"Features por ativo/timeframe: {root / OUT_ATIVO_TF}")
    print(f"Features por dinamica: {root / OUT_DINAMICA}")
    print(f"Features para modelagem: {root / OUT_MODELAGEM}")
    print(f"Linhas modelagem: {len(modeling_features)}")


if __name__ == "__main__":
    main()
