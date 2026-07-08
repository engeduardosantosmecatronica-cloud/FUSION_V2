"""
BACKTESTE RAPIDO
================
Usa todos os sinais BUY/SELL do modelo e testa entradas no candle do sinal
quando o preco rompe niveis do candle anterior: maxima, minima, abertura
ou fechamento.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import warnings

import joblib
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


# Configuracao padrao. Para testar mais ativos/timeframes, basta adicionar aqui
# ou usar argumentos:
# python backteste_rapido.py --symbols EURUSD GBPUSD --timeframes H1 H4 --years 2 --targets 100 200 300 400 500
SYMBOLS = [
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "GBPJPY",
    "AUDUSD",
    "USDCAD",
    "USDCHF",
    "EURGBP",
    "EURJPY",
    "NZDUSD",
    "EURCHF",
    "AUDCAD",
    "AUDCHF",
    "EURCAD",
    "GBPCHF",
    "AUDJPY",
    "CADCHF",
    "EURAUD",
    "GBPAUD",
    "NZDCAD",
    "AUDNZD",
    "CHFJPY",
    "EURNZD",
]


TIMEFRAMES = ["M5", "M15", "M30", "H1", "H4", "D1"]
BACKTEST_YEARS = 2
TARGETS_POINTS = [100, 200, 300, 400, 500]
LOOKAHEAD_CANDLES = 1000
SUMMARY_CSV = "reports/backtests/backteste_rapido_resumo.csv"
SYMBOL_SUMMARY_CSV = "reports/backtests/backteste_resumo_por_ativo.csv"
SYMBOL_SUMMARY_MD = "reports/backtests/backteste_resumo_por_ativo.md"
DYNAMICS_CSV = "reports/backtests/backteste_rapido_dinamica_entradas.csv"
DETAILED_CSV = "reports/backtests/backteste_rapido_resultados_detalhado.csv"
REPORT_MD = "reports/backtests/relatorio_backteste_rapido.md"
CACHE_DIR = "reports/backtests/cache"
REPORTS_DIR = "relatorios_por_ativo"
PRINT_TOP_COMBINATIONS = 0
SAVE_DETAILED_CSV = False
SAVE_PROGRESS_EVERY = 1

LEVELS = {
    "maxima": "high",
    "minima": "low",
    "abertura": "open",
    "fechamento": "close",
}


@dataclass(frozen=True)
class ModelSignal:
    idx: int
    side: str
    p_buy: float
    p_sell: float


def rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))


def build_model_features(df: pd.DataFrame) -> pd.DataFrame:
    """Replica as 43 features usadas pelos modelos salvos em models_expr."""
    features = pd.DataFrame(index=df.index)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    ret = np.log(close / close.shift(1))
    features["open"] = df["open"]
    features["high"] = high
    features["low"] = low
    features["close"] = close
    features["tick_volume"] = df.get("tick_volume", 0)
    features["spread"] = df.get("spread", 0)
    features["real_volume"] = df.get("real_volume", 0)

    features["ret"] = ret
    features["ret_5"] = ret.rolling(5).sum()
    features["ret_10"] = ret.rolling(10).sum()
    features["ret_20"] = ret.rolling(20).sum()

    features["rsi14"] = rsi(close, 14)
    features["rsi28"] = rsi(close, 28)
    features["rsi_diff"] = features["rsi14"] - features["rsi28"]
    features["rsi_ma5"] = features["rsi14"].rolling(5).mean()
    features["rsi_gap"] = features["rsi14"] - features["rsi14"].rolling(10).mean()

    for period in [8, 21, 50, 200]:
        ema = close.ewm(span=period, adjust=False).mean()
        features[f"ema{period}"] = ema
        features[f"dist_ema{period}"] = (close / ema) - 1

    range_pct = (high - low) / close
    features["range_pct"] = range_pct
    features["range_ma10"] = range_pct.rolling(10).mean()
    features["high_20"] = high.rolling(20).max()
    features["low_20"] = low.rolling(20).min()
    features["position_in_range"] = (
        (close - features["low_20"]) / (features["high_20"] - features["low_20"] + 1e-9)
    )

    features["vol5"] = ret.rolling(5).std()
    features["vol20"] = ret.rolling(20).std()
    features["vol_ratio"] = features["vol5"] / (features["vol20"] + 1e-9)

    ema_fast = close.ewm(span=12, adjust=False).mean()
    ema_slow = close.ewm(span=26, adjust=False).mean()
    features["macd"] = ema_fast - ema_slow
    features["macd_signal"] = features["macd"].ewm(span=9, adjust=False).mean()
    features["macd_hist"] = features["macd"] - features["macd_signal"]

    features["upper_bb"] = features["ema21"] + (ret.rolling(20).std() * 2)
    features["lower_bb"] = features["ema21"] - (ret.rolling(20).std() * 2)
    features["bb_width"] = features["upper_bb"] - features["lower_bb"]

    features["alpha_vam"] = ret.rolling(20).mean() / (range_pct.rolling(20).std() + 1e-9)
    features["alpha_effort"] = range_pct / (range_pct.rolling(50).mean() + 1e-9)
    features["alpha_mrs"] = features["dist_ema21"] / (range_pct.rolling(20).mean() + 1e-9)
    features["alpha_rsi_gap"] = features["rsi14"] - features["rsi14"].rolling(10).mean()

    trend_alignment = (features["rsi14"] > 50).astype(int)
    for period in [5, 10, 20]:
        trend_alignment += (close > close.ewm(span=period, adjust=False).mean()).astype(int)
    features["trend_alignment"] = trend_alignment

    return features


class BacktestEngine:
    def __init__(self, data_path: Path, model_dir: Path, symbol: str, timeframe: str, years: int):
        self.symbol = symbol
        self.timeframe = timeframe
        self.years = years
        self.df = pd.read_parquet(data_path).copy()
        self.df["date"] = pd.to_datetime(self.df["date"])
        self.df = self.df.sort_values("date").reset_index(drop=True)
        cutoff_date = self.df["date"].max() - pd.DateOffset(years=years)
        self.df = self.df[self.df["date"] >= cutoff_date].reset_index(drop=True)

        for col in ["spread", "real_volume"]:
            if col not in self.df.columns:
                self.df[col] = 0.0

        self.point_value = float(self.df["point_value"].dropna().iloc[0])
        self.model = joblib.load(model_dir / "model.pkl")
        self.scaler = joblib.load(model_dir / "scaler.pkl")
        self.meta = joblib.load(model_dir / "meta.pkl")
        self.feature_cols = self.meta["feature_columns"]
        self.buy_threshold = float(self.meta.get("buy_threshold", 0.55))
        self.sell_threshold = float(self.meta.get("sell_threshold", 0.55))

        self.features = build_model_features(self.df)

        print(f"Dados {symbol} {timeframe}: {len(self.df)} candles")
        print(f"Periodo: {self.df['date'].min()} ate {self.df['date'].max()}")
        print(f"Thresholds: BUY {self.buy_threshold:.4f} | SELL {self.sell_threshold:.4f}")

    def collect_model_signals(self) -> list[ModelSignal]:
        missing = [col for col in self.feature_cols if col not in self.features.columns]
        if missing:
            raise ValueError(f"Features ausentes para o modelo: {missing}")

        valid_features = self.features[self.feature_cols].replace([np.inf, -np.inf], np.nan)
        valid_features = valid_features.dropna()
        scaled = self.scaler.transform(valid_features.values)
        probs = self.model.predict_proba(scaled)

        p_buy = np.zeros(len(valid_features), dtype=float)
        p_sell = np.zeros(len(valid_features), dtype=float)
        for class_idx, cls in enumerate(self.model.classes_):
            if cls == 1:
                p_buy = probs[:, class_idx]
            elif cls == 2:
                p_sell = probs[:, class_idx]

        buy_signal = p_buy >= self.buy_threshold
        sell_signal = p_sell >= self.sell_threshold
        signal_mask = buy_signal | sell_signal

        signals: list[ModelSignal] = []
        indexes = valid_features.index.to_numpy()
        for pos in np.flatnonzero(signal_mask):
            if buy_signal[pos] and (not sell_signal[pos] or p_buy[pos] >= p_sell[pos]):
                side = "BUY"
            else:
                side = "SELL"
            signals.append(ModelSignal(int(indexes[pos]), side, float(p_buy[pos]), float(p_sell[pos])))

        return signals

    def previous_candle_type(self, idx: int) -> str:
        prev = self.df.iloc[idx - 1]
        if prev["close"] > prev["open"]:
            return "alta"
        if prev["close"] < prev["open"]:
            return "baixa"
        return "doji"

    def triggered_entries(self, signal: ModelSignal) -> Iterable[dict]:
        if signal.idx < 1:
            return []

        current = self.df.iloc[signal.idx]
        previous = self.df.iloc[signal.idx - 1]
        prev_type = self.previous_candle_type(signal.idx)
        entries = []

        for level_name, col in LEVELS.items():
            level_price = float(previous[col])
            if signal.side == "BUY":
                triggered = float(current["high"]) >= level_price
                relation = "acima"
            else:
                triggered = float(current["low"]) <= level_price
                relation = "abaixo"

            if triggered:
                entries.append(
                    {
                        "entry_idx": signal.idx,
                        "entry_date": current["date"],
                        "side": signal.side,
                        "entry_rule": level_name,
                        "relation": relation,
                        "entry_price": level_price,
                        "prev_candle": prev_type,
                        "p_buy": signal.p_buy,
                        "p_sell": signal.p_sell,
                    }
                )

        return entries

    def simulate_trade(self, entry: dict) -> dict:
        entry_idx = entry["entry_idx"]
        entry_price = entry["entry_price"]
        side = entry["side"]

        max_favorable = 0.0
        max_against_before_recovery = 0.0
        max_favorable_after_recovery = 0.0
        had_adverse = False
        recovered = False
        result = "NO_TARGET"
        exit_idx = None

        end_idx = min(entry_idx + LOOKAHEAD_CANDLES, len(self.df) - 1)
        for idx in range(entry_idx, end_idx + 1):
            row = self.df.iloc[idx]
            if side == "BUY":
                favorable = (float(row["high"]) - entry_price) / self.point_value
                adverse = (entry_price - float(row["low"])) / self.point_value
                touched_entry = float(row["high"]) >= entry_price
            else:
                favorable = (entry_price - float(row["low"])) / self.point_value
                adverse = (float(row["high"]) - entry_price) / self.point_value
                touched_entry = float(row["low"]) <= entry_price

            max_favorable = max(max_favorable, favorable)

            if not recovered:
                if adverse > 0:
                    had_adverse = True
                    max_against_before_recovery = max(max_against_before_recovery, adverse)
                if had_adverse and touched_entry:
                    recovered = True
            else:
                max_favorable_after_recovery = max(max_favorable_after_recovery, favorable)

            if favorable >= TARGETS_POINTS[0]:
                result = "WIN"
                exit_idx = idx
                break

        if exit_idx is None:
            exit_idx = end_idx

        trade = entry.copy()
        trade.update(
            {
                "target": TARGETS_POINTS[0],
                "result": result,
                "exit_idx": exit_idx,
                "exit_date": self.df.iloc[exit_idx]["date"],
                "max_favorable": max_favorable,
                "max_against_before_recovery": max_against_before_recovery,
                "max_favorable_after_recovery": max_favorable_after_recovery,
                "recovered": recovered,
            }
        )
        return trade

    def run(self) -> pd.DataFrame:
        signals = self.collect_model_signals()
        print(f"Sinais do modelo: {len(signals)}")
        print(f"  BUY: {sum(s.side == 'BUY' for s in signals)}")
        print(f"  SELL: {sum(s.side == 'SELL' for s in signals)}")

        entries = []
        for signal in signals:
            entries.extend(self.triggered_entries(signal))

        print(f"Entradas acionadas: {len(entries)}")
        result = self.simulate_trades_batch(entries)
        if not result.empty:
            result.insert(0, "symbol", self.symbol)
            result.insert(1, "timeframe", self.timeframe)
        return result

    def simulate_trades_batch(self, entries: list[dict], chunk_size: int = 2000) -> pd.DataFrame:
        if not entries:
            return pd.DataFrame()

        base = pd.DataFrame(entries)
        n = len(self.df)
        highs = self.df["high"].to_numpy(dtype=float)
        lows = self.df["low"].to_numpy(dtype=float)
        dates = self.df["date"].to_numpy()
        offsets = np.arange(LOOKAHEAD_CANDLES + 1)

        max_favorable_all = np.empty(len(base), dtype=float)
        max_against_all = np.empty(len(base), dtype=float)
        favor_after_all = np.empty(len(base), dtype=float)
        recovered_all = np.empty(len(base), dtype=bool)
        target_results = {target: np.empty(len(base), dtype=object) for target in TARGETS_POINTS}
        target_exit_indexes = {target: np.empty(len(base), dtype=int) for target in TARGETS_POINTS}

        entry_indexes = base["entry_idx"].to_numpy(dtype=int)
        entry_prices = base["entry_price"].to_numpy(dtype=float)
        is_buy = (base["side"].to_numpy() == "BUY")

        for start in range(0, len(base), chunk_size):
            end = min(start + chunk_size, len(base))
            chunk_idx = entry_indexes[start:end]
            chunk_price = entry_prices[start:end]
            chunk_buy = is_buy[start:end]

            matrix_idx = chunk_idx[:, None] + offsets[None, :]
            valid = matrix_idx < n
            clipped_idx = np.minimum(matrix_idx, n - 1)

            high_window = highs[clipped_idx]
            low_window = lows[clipped_idx]
            price_col = chunk_price[:, None]

            favorable = np.where(
                chunk_buy[:, None],
                (high_window - price_col) / self.point_value,
                (price_col - low_window) / self.point_value,
            )
            adverse = np.where(
                chunk_buy[:, None],
                (price_col - low_window) / self.point_value,
                (high_window - price_col) / self.point_value,
            )
            touched_entry = np.where(
                chunk_buy[:, None],
                high_window >= price_col,
                low_window <= price_col,
            )

            favorable = np.where(valid, favorable, -np.inf)
            adverse = np.where(valid, adverse, 0.0)
            touched_entry = valid & touched_entry

            max_favorable = np.max(favorable, axis=1)
            last_valid_pos = np.sum(valid, axis=1) - 1

            for target in TARGETS_POINTS:
                win_mask = favorable >= target
                has_win = np.any(win_mask, axis=1)
                first_win_pos = np.argmax(win_mask, axis=1)
                exit_pos = np.where(has_win, first_win_pos, last_valid_pos)
                target_results[target][start:end] = np.where(has_win, "WIN", "NO_TARGET")
                target_exit_indexes[target][start:end] = chunk_idx + exit_pos

            adverse_positive = adverse > 0
            had_adverse = np.maximum.accumulate(adverse_positive, axis=1)
            recovery_mask = had_adverse & touched_entry
            has_recovery = np.any(recovery_mask, axis=1)
            first_recovery_pos = np.argmax(recovery_mask, axis=1)

            before_recovery = offsets[None, :] <= first_recovery_pos[:, None]
            adverse_before_recovery = np.where(
                has_recovery[:, None] & before_recovery & valid,
                adverse,
                np.where((~has_recovery)[:, None] & valid, adverse, 0.0),
            )
            max_against = np.max(adverse_before_recovery, axis=1)

            after_recovery = offsets[None, :] >= first_recovery_pos[:, None]
            favor_after_recovery = np.where(
                has_recovery[:, None] & after_recovery & valid,
                favorable,
                0.0,
            )
            favor_after = np.max(favor_after_recovery, axis=1)

            max_favorable_all[start:end] = max_favorable
            max_against_all[start:end] = max_against
            favor_after_all[start:end] = favor_after
            recovered_all[start:end] = has_recovery

        base["max_favorable"] = max_favorable_all
        base["max_against_before_recovery"] = max_against_all
        base["max_favorable_after_recovery"] = favor_after_all
        base["recovered"] = recovered_all

        frames = []
        for target in TARGETS_POINTS:
            target_frame = base.copy()
            target_frame["target"] = target
            target_frame["result"] = target_results[target]
            target_frame["exit_idx"] = target_exit_indexes[target]
            target_frame["exit_date"] = dates[target_exit_indexes[target]]
            frames.append(target_frame)

        return pd.concat(frames, ignore_index=True)


def build_grouped_summary(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()

    grouped = (
        trades.groupby(["symbol", "timeframe", "target", "side", "relation", "prev_candle", "entry_rule"], dropna=False)
        .agg(
            trades=("result", "size"),
            wins=("result", lambda s: int((s == "WIN").sum())),
            win_rate=("result", lambda s: float((s == "WIN").mean() * 100)),
            favor_media=("max_favorable", "mean"),
            contra_media=("max_against_before_recovery", "mean"),
            favor_apos_voltar_media=("max_favorable_after_recovery", "mean"),
            recuperou_pct=("recovered", lambda s: float(s.mean() * 100)),
        )
        .reset_index()
        .sort_values(["win_rate", "trades"], ascending=[False, False])
    )
    return enrich_dynamics(grouped)


def enrich_dynamics(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    result = df.copy()
    result["direcao"] = result["side"].map({"BUY": "compra", "SELL": "venda"}).fillna(result["side"])
    result["entrada_posicao"] = result["relation"].map({"acima": "acima", "abaixo": "abaixo"}).fillna(result["relation"])
    result["nivel_candle_anterior"] = result["entry_rule"]
    result["candle_anterior"] = result["prev_candle"]
    result["leitura"] = (
        result["direcao"]
        + " "
        + result["entrada_posicao"]
        + " da "
        + result["nivel_candle_anterior"]
        + " do candle anterior de "
        + result["candle_anterior"]
    )
    return result


def print_summary(trades: pd.DataFrame, symbol: str, timeframe: str) -> None:
    print("\n" + "=" * 100)
    print(f"RESUMO {symbol} {timeframe} | alvos {', '.join(map(str, TARGETS_POINTS))} pontos")
    print("=" * 100)

    if trades.empty:
        print("Nenhuma entrada acionada pelos sinais do modelo.")
        return

    unique_entries = trades.drop_duplicates(["entry_idx", "side", "entry_rule", "entry_price"]).shape[0]
    print(f"Entradas acionadas: {unique_entries}")
    print(f"Simulacoes por alvo: {len(trades)}")
    print("\nCandle anterior dos sinais:")
    unique_trade_rows = trades.drop_duplicates(["entry_idx", "side", "entry_rule", "entry_price"])
    print(unique_trade_rows["prev_candle"].value_counts().to_string())

    if PRINT_TOP_COMBINATIONS > 0:
        grouped = build_grouped_summary(trades).drop(columns=["symbol", "timeframe"])
        print(f"\nTop {PRINT_TOP_COMBINATIONS} combinacoes no terminal:")
        for _, row in grouped.head(PRINT_TOP_COMBINATIONS).iterrows():
            print(
                f"{row['side']:>4} | {row['relation']:<6} | {row['entry_rule']:<10} | prev {row['prev_candle']:<5} | "
                f"alvo {int(row['target']):>3} | "
                f"trades {int(row['trades']):>5} | wins {int(row['wins']):>5} | "
                f"win {row['win_rate']:>6.2f}% | favor {row['favor_media']:>8.2f} | "
                f"contra ate voltar {row['contra_media']:>8.2f} | "
                f"favor apos voltar {row['favor_apos_voltar_media']:>8.2f} | "
                f"recuperou {row['recuperou_pct']:>6.2f}%"
            )


def format_br(value: float, decimals: int = 2) -> str:
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def markdown_table(df: pd.DataFrame, columns: list[str], headers: list[str]) -> str:
    if df.empty:
        return "_Sem dados._"

    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in df.iterrows():
        values = []
        for col in columns:
            value = row[col]
            if isinstance(value, (float, np.floating)):
                if col.endswith("_pct") or col == "win_rate":
                    values.append(f"{format_br(float(value))}%")
                else:
                    values.append(format_br(float(value)))
            elif isinstance(value, (int, np.integer)):
                values.append(f"{int(value):,}".replace(",", "."))
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def generate_report(
    trades: pd.DataFrame,
    report_path: Path,
    results_path: Path,
    symbols: list[str],
    timeframes: list[str],
    years: int,
) -> None:
    if trades.empty:
        report_path.write_text("# Relatorio Backteste Rapido\n\nNenhuma entrada foi acionada.\n", encoding="utf-8")
        return

    grouped = build_grouped_summary(trades)
    by_symbol_tf = (
        trades.groupby(["symbol", "timeframe", "target"])
        .agg(
            entradas=("result", "size"),
            wins=("result", lambda s: int((s == "WIN").sum())),
            win_rate=("result", lambda s: float((s == "WIN").mean() * 100)),
            favor_media=("max_favorable", "mean"),
            contra_media=("max_against_before_recovery", "mean"),
            favor_apos_voltar_media=("max_favorable_after_recovery", "mean"),
        )
        .reset_index()
        .sort_values(["symbol", "timeframe"])
    )
    by_side = (
        trades.groupby(["symbol", "timeframe", "target", "side"])
        .agg(
            entradas=("result", "size"),
            wins=("result", lambda s: int((s == "WIN").sum())),
            win_rate=("result", lambda s: float((s == "WIN").mean() * 100)),
            favor_media=("max_favorable", "mean"),
            contra_media=("max_against_before_recovery", "mean"),
        )
        .reset_index()
        .sort_values(["symbol", "timeframe", "side"])
    )
    prev_candle = (
        trades.groupby(["symbol", "timeframe", "target", "prev_candle"])
        .size()
        .reset_index(name="entradas")
        .sort_values(["symbol", "timeframe", "target", "entradas"], ascending=[True, True, True, False])
    )

    period_start = trades["entry_date"].min()
    period_end = trades["entry_date"].max()
    unique_entries = trades.drop_duplicates(["symbol", "timeframe", "entry_idx", "side", "entry_rule", "entry_price"]).shape[0]
    total = len(trades)
    wins = int((trades["result"] == "WIN").sum())
    win_rate = float((trades["result"] == "WIN").mean() * 100)

    lines = [
        "# Relatorio Backteste Rapido",
        "",
        "## Configuracao",
        "",
        f"- Ativos: {', '.join(symbols)}",
        f"- Timeframes: {', '.join(timeframes)}",
        f"- Periodo: ultimos {years} ano(s) do historico disponivel",
        f"- Entradas analisadas: {period_start} ate {period_end}",
        f"- Alvos: {', '.join(map(str, TARGETS_POINTS))} pontos",
        f"- Janela maxima pos-entrada: {LOOKAHEAD_CANDLES} candles",
        "- Sinais: todos os sinais BUY e SELL do modelo",
        "- Entradas: preco tocando/rompendo maxima, minima, abertura ou fechamento do candle anterior",
        "- Filtro de medias: removido",
        "",
        "## Resumo Geral",
        "",
        f"- Entradas acionadas: {unique_entries:,}".replace(",", "."),
        f"- Simulacoes por alvo: {total:,}".replace(",", "."),
        f"- Wins: {wins:,}".replace(",", "."),
        f"- Win rate geral: {format_br(win_rate)}%",
        "",
        "## Resultado Por Ativo E Timeframe",
        "",
        markdown_table(
            by_symbol_tf,
            ["symbol", "timeframe", "target", "entradas", "wins", "win_rate", "favor_media", "contra_media", "favor_apos_voltar_media"],
            ["Ativo", "Timeframe", "Alvo", "Entradas", "Wins", "Win rate", "Media a favor", "Media contra ate voltar", "Media a favor apos voltar"],
        ),
        "",
        "## Resultado Por Direcao",
        "",
        markdown_table(
            by_side,
            ["symbol", "timeframe", "target", "side", "entradas", "wins", "win_rate", "favor_media", "contra_media"],
            ["Ativo", "Timeframe", "Alvo", "Direcao", "Entradas", "Wins", "Win rate", "Media a favor", "Media contra ate voltar"],
        ),
        "",
        "## Candle Anterior",
        "",
        markdown_table(
            prev_candle,
            ["symbol", "timeframe", "target", "prev_candle", "entradas"],
            ["Ativo", "Timeframe", "Alvo", "Candle anterior", "Entradas"],
        ),
        "",
        "## Melhores Combinacoes",
        "",
        markdown_table(
            grouped.head(30),
            [
                "symbol",
                "timeframe",
                "target",
                "side",
                "entry_rule",
                "prev_candle",
                "trades",
                "wins",
                "win_rate",
                "favor_media",
                "contra_media",
                "favor_apos_voltar_media",
                "recuperou_pct",
            ],
            [
                "Ativo",
                "Timeframe",
                "Alvo",
                "Direcao",
                "Nivel anterior",
                "Candle anterior",
                "Entradas",
                "Wins",
                "Win rate",
                "Media a favor",
                "Media contra ate voltar",
                "Media a favor apos voltar",
                "Recuperou",
            ],
        ),
        "",
        "## Arquivos Gerados",
        "",
        f"- Resultado detalhado: `{results_path.name}`",
        f"- Relatorio: `{report_path.name}`",
        f"- Script: `backteste_rapido.py`",
        "",
    ]

    report_path.write_text("\n".join(lines), encoding="utf-8")


def summarize_trades(trades: pd.DataFrame) -> dict[str, pd.DataFrame | int | str]:
    if trades.empty:
        by_symbol_tf_cols = [
            "symbol",
            "timeframe",
            "target",
            "entradas",
            "wins",
            "win_rate",
            "favor_media",
            "contra_media",
            "favor_apos_voltar_media",
        ]
        by_side_cols = [
            "symbol",
            "timeframe",
            "target",
            "side",
            "entradas",
            "wins",
            "win_rate",
            "favor_media",
            "contra_media",
        ]
        prev_candle_cols = ["symbol", "timeframe", "target", "prev_candle", "entradas"]
        grouped_cols = [
            "symbol",
            "timeframe",
            "target",
            "side",
            "relation",
            "prev_candle",
            "entry_rule",
            "trades",
            "wins",
            "win_rate",
            "favor_media",
            "contra_media",
            "favor_apos_voltar_media",
            "recuperou_pct",
            "direcao",
            "entrada_posicao",
            "nivel_candle_anterior",
            "candle_anterior",
            "leitura",
        ]
        return {
            "by_symbol_tf": pd.DataFrame(columns=by_symbol_tf_cols),
            "by_side": pd.DataFrame(columns=by_side_cols),
            "prev_candle": pd.DataFrame(columns=prev_candle_cols),
            "grouped": pd.DataFrame(columns=grouped_cols),
            "unique_entries": 0,
            "simulations": 0,
            "wins": 0,
            "period_start": "",
            "period_end": "",
        }

    unique_entries = trades.drop_duplicates(["symbol", "timeframe", "entry_idx", "side", "entry_rule", "entry_price"])
    by_symbol_tf = (
        trades.groupby(["symbol", "timeframe", "target"])
        .agg(
            entradas=("result", "size"),
            wins=("result", lambda s: int((s == "WIN").sum())),
            win_rate=("result", lambda s: float((s == "WIN").mean() * 100)),
            favor_media=("max_favorable", "mean"),
            contra_media=("max_against_before_recovery", "mean"),
            favor_apos_voltar_media=("max_favorable_after_recovery", "mean"),
        )
        .reset_index()
    )
    by_side = (
        trades.groupby(["symbol", "timeframe", "target", "side"])
        .agg(
            entradas=("result", "size"),
            wins=("result", lambda s: int((s == "WIN").sum())),
            win_rate=("result", lambda s: float((s == "WIN").mean() * 100)),
            favor_media=("max_favorable", "mean"),
            contra_media=("max_against_before_recovery", "mean"),
        )
        .reset_index()
    )
    prev_candle = (
        trades.groupby(["symbol", "timeframe", "target", "prev_candle"])
        .size()
        .reset_index(name="entradas")
    )
    grouped = build_grouped_summary(trades)
    return {
        "by_symbol_tf": by_symbol_tf,
        "by_side": by_side,
        "prev_candle": prev_candle,
        "grouped": grouped,
        "unique_entries": len(unique_entries),
        "simulations": len(trades),
        "wins": int((trades["result"] == "WIN").sum()),
        "period_start": str(trades["entry_date"].min()),
        "period_end": str(trades["entry_date"].max()),
    }


def cache_key(symbol: str, timeframe: str, years: int) -> str:
    targets = "-".join(str(target) for target in TARGETS_POINTS)
    return f"{symbol}_{timeframe}_y{years}_t{targets}_l{LOOKAHEAD_CANDLES}"


def save_summary_cache(cache_root: Path, key: str, summary: dict[str, pd.DataFrame | int | str]) -> None:
    path = cache_root / key
    path.mkdir(parents=True, exist_ok=True)

    for name in ["by_symbol_tf", "by_side", "prev_candle", "grouped"]:
        value = summary[name]
        if isinstance(value, pd.DataFrame):
            value.to_csv(path / f"{name}.csv", index=False)

    meta = {
        "unique_entries": int(summary["unique_entries"]),
        "simulations": int(summary["simulations"]),
        "wins": int(summary["wins"]),
        "period_start": str(summary["period_start"]),
        "period_end": str(summary["period_end"]),
    }
    (path / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def load_summary_cache(cache_root: Path, key: str) -> dict[str, pd.DataFrame | int | str] | None:
    path = cache_root / key
    required = ["by_symbol_tf.csv", "by_side.csv", "prev_candle.csv", "grouped.csv", "meta.json"]
    if not all((path / name).exists() for name in required):
        return None

    meta = json.loads((path / "meta.json").read_text(encoding="utf-8"))
    grouped = pd.read_csv(path / "grouped.csv")
    if "leitura" not in grouped.columns:
        grouped = enrich_dynamics(grouped)

    return {
        "by_symbol_tf": pd.read_csv(path / "by_symbol_tf.csv"),
        "by_side": pd.read_csv(path / "by_side.csv"),
        "prev_candle": pd.read_csv(path / "prev_candle.csv"),
        "grouped": grouped,
        "unique_entries": int(meta["unique_entries"]),
        "simulations": int(meta["simulations"]),
        "wins": int(meta["wins"]),
        "period_start": str(meta["period_start"]),
        "period_end": str(meta["period_end"]),
    }


def weighted_mean(df: pd.DataFrame, value_col: str, weight_col: str = "entradas") -> float:
    weights = df[weight_col].astype(float)
    if weights.sum() == 0:
        return 0.0
    return float((df[value_col].astype(float) * weights).sum() / weights.sum())


def combine_weighted_summary(frames: list[pd.DataFrame], keys: list[str]) -> pd.DataFrame:
    if not frames:
        return pd.DataFrame()
    raw = pd.concat(frames, ignore_index=True)
    rows = []
    for key_values, group in raw.groupby(keys, dropna=False):
        if not isinstance(key_values, tuple):
            key_values = (key_values,)
        entradas = int(group["entradas"].sum())
        wins = int(group["wins"].sum()) if "wins" in group.columns else None
        row = dict(zip(keys, key_values))
        row["entradas"] = entradas
        if wins is not None:
            row["wins"] = wins
            row["win_rate"] = (wins / entradas * 100) if entradas else 0.0
            row["favor_media"] = weighted_mean(group, "favor_media")
            row["contra_media"] = weighted_mean(group, "contra_media")
            if "favor_apos_voltar_media" in group.columns:
                row["favor_apos_voltar_media"] = weighted_mean(group, "favor_apos_voltar_media")
        rows.append(row)
    return pd.DataFrame(rows)


def combine_grouped_summary(frames: list[pd.DataFrame]) -> pd.DataFrame:
    if not frames:
        return pd.DataFrame()
    raw = pd.concat(frames, ignore_index=True)
    keys = ["symbol", "timeframe", "target", "side", "relation", "prev_candle", "entry_rule"]
    rows = []
    for key_values, group in raw.groupby(keys, dropna=False):
        entradas = int(group["trades"].sum())
        wins = int(group["wins"].sum())
        row = dict(zip(keys, key_values))
        row["trades"] = entradas
        row["wins"] = wins
        row["win_rate"] = (wins / entradas * 100) if entradas else 0.0
        row["favor_media"] = weighted_mean(group.rename(columns={"trades": "entradas"}), "favor_media")
        row["contra_media"] = weighted_mean(group.rename(columns={"trades": "entradas"}), "contra_media")
        row["favor_apos_voltar_media"] = weighted_mean(group.rename(columns={"trades": "entradas"}), "favor_apos_voltar_media")
        row["recuperou_pct"] = weighted_mean(group.rename(columns={"trades": "entradas"}), "recuperou_pct")
        rows.append(row)
    return enrich_dynamics(pd.DataFrame(rows)).sort_values(["win_rate", "trades"], ascending=[False, False])


def build_symbol_summary(by_symbol_tf: pd.DataFrame) -> pd.DataFrame:
    if by_symbol_tf.empty:
        return pd.DataFrame()

    rows = []
    for symbol, group in by_symbol_tf.groupby("symbol", sort=True):
        entradas = int(group["entradas"].sum())
        wins = int(group["wins"].sum())
        win_rate = (wins / entradas * 100) if entradas else 0.0
        favor_media = weighted_mean(group, "favor_media")
        contra_media = weighted_mean(group, "contra_media")
        favor_apos = weighted_mean(group, "favor_apos_voltar_media")

        candidates = group[group["entradas"] >= 500].copy()
        if candidates.empty:
            candidates = group.copy()
        candidates["score"] = (
            candidates["target"] * (candidates["win_rate"] / 100.0)
            - candidates["contra_media"] * (1.0 - candidates["win_rate"] / 100.0)
        )
        best = candidates.sort_values(["score", "target", "win_rate", "entradas"], ascending=[False, False, False, False]).iloc[0]

        rows.append(
            {
                "symbol": symbol,
                "entradas": entradas,
                "wins": wins,
                "win_rate": win_rate,
                "favor_media": favor_media,
                "contra_media": contra_media,
                "favor_apos_voltar_media": favor_apos,
                "melhor_timeframe": best["timeframe"],
                "melhor_alvo": int(best["target"]),
                "melhor_alvo_win_rate": float(best["win_rate"]),
                "melhor_alvo_entradas": int(best["entradas"]),
                "score": float(best["score"]),
            }
        )

    return pd.DataFrame(rows).sort_values(["score", "win_rate", "entradas"], ascending=[False, False, False])


def save_symbol_summary_markdown(symbol_summary: pd.DataFrame, path: Path) -> None:
    lines = [
        "# Resumo Por Ativo",
        "",
        markdown_table(
            symbol_summary,
            [
                "symbol",
                "entradas",
                "wins",
                "win_rate",
                "favor_media",
                "contra_media",
                "favor_apos_voltar_media",
                "melhor_timeframe",
                "melhor_alvo",
                "melhor_alvo_win_rate",
                "melhor_alvo_entradas",
            ],
            [
                "Ativo",
                "Entradas",
                "Wins",
                "Win rate geral",
                "Media a favor",
                "Media contra",
                "Media apos voltar",
                "Melhor timeframe",
                "Melhor alvo",
                "WR melhor alvo",
                "Entradas melhor alvo",
            ],
        ),
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def generate_report_from_summaries(
    summaries: list[dict[str, pd.DataFrame | int | str]],
    report_path: Path,
    summary_path: Path,
    dynamics_path: Path,
    detailed_path: Path,
    symbols: list[str],
    timeframes: list[str],
    years: int,
) -> pd.DataFrame:
    if not summaries:
        report_path.write_text("# Relatorio Backteste Rapido\n\nNenhuma entrada foi acionada.\n", encoding="utf-8")
        return pd.DataFrame()

    by_symbol_tf = combine_weighted_summary([s["by_symbol_tf"] for s in summaries], ["symbol", "timeframe", "target"])
    by_side = combine_weighted_summary([s["by_side"] for s in summaries], ["symbol", "timeframe", "target", "side"])
    prev_candle = pd.concat([s["prev_candle"] for s in summaries], ignore_index=True)
    prev_candle = (
        prev_candle.groupby(["symbol", "timeframe", "target", "prev_candle"], dropna=False)["entradas"]
        .sum()
        .reset_index()
        .sort_values(["symbol", "timeframe", "target", "entradas"], ascending=[True, True, True, False])
    )
    grouped = combine_grouped_summary([s["grouped"] for s in summaries])
    symbol_summary = build_symbol_summary(by_symbol_tf)

    total_entries = int(sum(int(s["unique_entries"]) for s in summaries))
    total_simulations = int(sum(int(s["simulations"]) for s in summaries))
    total_wins = int(sum(int(s["wins"]) for s in summaries))
    win_rate = (total_wins / total_simulations * 100) if total_simulations else 0.0
    period_start = min(str(s["period_start"]) for s in summaries)
    period_end = max(str(s["period_end"]) for s in summaries)

    lines = [
        "# Relatorio Backteste Rapido",
        "",
        "## Configuracao",
        "",
        f"- Ativos: {', '.join(symbols)}",
        f"- Timeframes: {', '.join(timeframes)}",
        f"- Periodo: ultimos {years} ano(s) do historico disponivel",
        f"- Entradas analisadas: {period_start} ate {period_end}",
        f"- Alvos: {', '.join(map(str, TARGETS_POINTS))} pontos",
        f"- Janela maxima pos-entrada: {LOOKAHEAD_CANDLES} candles",
        "- Sinais: todos os sinais BUY e SELL do modelo",
        "- Entradas: preco tocando/rompendo maxima, minima, abertura ou fechamento do candle anterior",
        "- Filtro de medias: removido",
        "",
        "## Resumo Geral",
        "",
        f"- Entradas acionadas: {total_entries:,}".replace(",", "."),
        f"- Simulacoes por alvo: {total_simulations:,}".replace(",", "."),
        f"- Wins: {total_wins:,}".replace(",", "."),
        f"- Win rate geral: {format_br(win_rate)}%",
        "",
        "## Resumo Por Ativo",
        "",
        markdown_table(
            symbol_summary,
            [
                "symbol",
                "entradas",
                "wins",
                "win_rate",
                "favor_media",
                "contra_media",
                "favor_apos_voltar_media",
                "melhor_timeframe",
                "melhor_alvo",
                "melhor_alvo_win_rate",
                "melhor_alvo_entradas",
            ],
            [
                "Ativo",
                "Entradas",
                "Wins",
                "Win rate geral",
                "Media a favor",
                "Media contra",
                "Media apos voltar",
                "Melhor timeframe",
                "Melhor alvo",
                "WR melhor alvo",
                "Entradas melhor alvo",
            ],
        ),
        "",
        "## Resultado Por Ativo E Timeframe",
        "",
        markdown_table(
            by_symbol_tf.sort_values(["symbol", "timeframe", "target"]),
            ["symbol", "timeframe", "target", "entradas", "wins", "win_rate", "favor_media", "contra_media", "favor_apos_voltar_media"],
            ["Ativo", "Timeframe", "Alvo", "Entradas", "Wins", "Win rate", "Media a favor", "Media contra ate voltar", "Media a favor apos voltar"],
        ),
        "",
        "## Resultado Por Direcao",
        "",
        markdown_table(
            by_side.sort_values(["symbol", "timeframe", "target", "side"]),
            ["symbol", "timeframe", "target", "side", "entradas", "wins", "win_rate", "favor_media", "contra_media"],
            ["Ativo", "Timeframe", "Alvo", "Direcao", "Entradas", "Wins", "Win rate", "Media a favor", "Media contra ate voltar"],
        ),
        "",
        "## Candle Anterior",
        "",
        markdown_table(
            prev_candle,
            ["symbol", "timeframe", "target", "prev_candle", "entradas"],
            ["Ativo", "Timeframe", "Alvo", "Candle anterior", "Entradas"],
        ),
        "",
        "## Melhores Combinacoes",
        "",
        markdown_table(
            grouped.head(60),
            ["symbol", "timeframe", "target", "direcao", "entrada_posicao", "nivel_candle_anterior", "candle_anterior", "trades", "wins", "win_rate", "favor_media", "contra_media", "favor_apos_voltar_media", "recuperou_pct"],
            ["Ativo", "Timeframe", "Alvo", "Direcao", "Entrada", "Nivel anterior", "Candle anterior", "Entradas", "Wins", "Win rate", "Media a favor", "Media contra ate voltar", "Media a favor apos voltar", "Recuperou"],
        ),
        "",
        "## Dinamica Completa Das Entradas",
        "",
        "Esta tabela responde se a entrada foi compra/venda, acima/abaixo do candle anterior, se o candle anterior era de alta/baixa/doji e qual nivel foi usado.",
        "",
        markdown_table(
            grouped.sort_values(["symbol", "timeframe", "target", "side", "prev_candle", "entry_rule"]),
            ["symbol", "timeframe", "target", "direcao", "entrada_posicao", "nivel_candle_anterior", "candle_anterior", "trades", "wins", "win_rate", "favor_media", "contra_media", "favor_apos_voltar_media", "recuperou_pct", "leitura"],
            ["Ativo", "Timeframe", "Alvo", "Direcao", "Entrada", "Nivel anterior", "Candle anterior", "Entradas", "Wins", "Win rate", "Media a favor", "Media contra ate voltar", "Media a favor apos voltar", "Recuperou", "Leitura"],
        ),
        "",
        "## Arquivos Gerados",
        "",
        f"- Resumo CSV: `{summary_path.name}`",
        f"- Dinamica CSV: `{dynamics_path.name}`",
        f"- Relatorio: `{report_path.name}`",
        f"- Detalhado CSV: {'ativado' if SAVE_DETAILED_CSV else 'desativado por padrao'}"
        + (f" (`{detailed_path.name}`)" if SAVE_DETAILED_CSV else ""),
        f"- Script: `backteste_rapido.py`",
        "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")

    summary_csv = by_symbol_tf.sort_values(["symbol", "timeframe", "target"])
    summary_csv.to_csv(summary_path, index=False)
    symbol_summary.to_csv(summary_path.parent / Path(SYMBOL_SUMMARY_CSV).name, index=False)
    save_symbol_summary_markdown(symbol_summary, summary_path.parent / Path(SYMBOL_SUMMARY_MD).name)
    grouped.sort_values(["symbol", "timeframe", "target", "side", "prev_candle", "entry_rule"]).to_csv(dynamics_path, index=False)
    save_symbol_reports(
        report_path.parent / REPORTS_DIR,
        by_symbol_tf,
        by_side,
        prev_candle,
        grouped,
        summaries,
        symbols,
        timeframes,
        years,
    )
    return summary_csv


def save_symbol_reports(
    output_dir: Path,
    by_symbol_tf: pd.DataFrame,
    by_side: pd.DataFrame,
    prev_candle: pd.DataFrame,
    grouped: pd.DataFrame,
    summaries: list[dict[str, pd.DataFrame | int | str]],
    symbols: list[str],
    timeframes: list[str],
    years: int,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    summaries_by_symbol: dict[str, list[dict[str, pd.DataFrame | int | str]]] = {}
    for summary in summaries:
        symbol_df = summary.get("by_symbol_tf")
        if isinstance(symbol_df, pd.DataFrame) and not symbol_df.empty:
            symbol = str(symbol_df["symbol"].iloc[0])
            summaries_by_symbol.setdefault(symbol, []).append(summary)

    for symbol in symbols:
        symbol_summary = by_symbol_tf[by_symbol_tf["symbol"] == symbol].copy()
        if symbol_summary.empty:
            continue

        symbol_side = by_side[by_side["symbol"] == symbol].copy()
        symbol_prev = prev_candle[prev_candle["symbol"] == symbol].copy()
        symbol_grouped = grouped[grouped["symbol"] == symbol].copy()
        symbol_summaries = summaries_by_symbol.get(symbol, [])

        total_entries = int(sum(int(s["unique_entries"]) for s in symbol_summaries))
        total_simulations = int(sum(int(s["simulations"]) for s in symbol_summaries))
        total_wins = int(sum(int(s["wins"]) for s in symbol_summaries))
        win_rate = (total_wins / total_simulations * 100) if total_simulations else 0.0
        period_start = min((str(s["period_start"]) for s in symbol_summaries), default="-")
        period_end = max((str(s["period_end"]) for s in symbol_summaries), default="-")

        report_file = output_dir / f"{symbol}_relatorio.md"
        summary_file = output_dir / f"{symbol}_resumo.csv"
        dynamics_file = output_dir / f"{symbol}_dinamica.csv"

        lines = [
            f"# Relatorio Backteste - {symbol}",
            "",
            "## Configuracao",
            "",
            f"- Ativo: {symbol}",
            f"- Timeframes: {', '.join(timeframes)}",
            f"- Periodo: ultimos {years} ano(s) do historico disponivel",
            f"- Entradas analisadas: {period_start} ate {period_end}",
            f"- Alvos: {', '.join(map(str, TARGETS_POINTS))} pontos",
            f"- Janela maxima pos-entrada: {LOOKAHEAD_CANDLES} candles",
            "- Sinais: todos os sinais BUY e SELL do modelo",
            "- Entradas: preco tocando/rompendo maxima, minima, abertura ou fechamento do candle anterior",
            "- Filtro de medias: removido",
            "",
            "## Resumo Geral Do Ativo",
            "",
            f"- Entradas acionadas: {total_entries:,}".replace(",", "."),
            f"- Simulacoes por alvo: {total_simulations:,}".replace(",", "."),
            f"- Wins: {total_wins:,}".replace(",", "."),
            f"- Win rate geral: {format_br(win_rate)}%",
            "",
            "## Resultado Por Timeframe E Alvo",
            "",
            markdown_table(
                symbol_summary.sort_values(["timeframe", "target"]),
                ["timeframe", "target", "entradas", "wins", "win_rate", "favor_media", "contra_media", "favor_apos_voltar_media"],
                ["Timeframe", "Alvo", "Entradas", "Wins", "Win rate", "Media a favor", "Media contra ate voltar", "Media a favor apos voltar"],
            ),
            "",
            "## Resultado Por Direcao",
            "",
            markdown_table(
                symbol_side.sort_values(["timeframe", "target", "side"]),
                ["timeframe", "target", "side", "entradas", "wins", "win_rate", "favor_media", "contra_media"],
                ["Timeframe", "Alvo", "Direcao", "Entradas", "Wins", "Win rate", "Media a favor", "Media contra ate voltar"],
            ),
            "",
            "## Candle Anterior",
            "",
            markdown_table(
                symbol_prev.sort_values(["timeframe", "target", "entradas"], ascending=[True, True, False]),
                ["timeframe", "target", "prev_candle", "entradas"],
                ["Timeframe", "Alvo", "Candle anterior", "Entradas"],
            ),
            "",
            "## Melhores Combinacoes Do Ativo",
            "",
            markdown_table(
                symbol_grouped.head(80),
                ["timeframe", "target", "direcao", "entrada_posicao", "nivel_candle_anterior", "candle_anterior", "trades", "wins", "win_rate", "favor_media", "contra_media", "favor_apos_voltar_media", "recuperou_pct"],
                ["Timeframe", "Alvo", "Direcao", "Entrada", "Nivel anterior", "Candle anterior", "Entradas", "Wins", "Win rate", "Media a favor", "Media contra ate voltar", "Media a favor apos voltar", "Recuperou"],
            ),
            "",
            "## Dinamica Completa Das Entradas",
            "",
            markdown_table(
                symbol_grouped.sort_values(["timeframe", "target", "side", "prev_candle", "entry_rule"]),
                ["timeframe", "target", "direcao", "entrada_posicao", "nivel_candle_anterior", "candle_anterior", "trades", "wins", "win_rate", "favor_media", "contra_media", "favor_apos_voltar_media", "recuperou_pct", "leitura"],
                ["Timeframe", "Alvo", "Direcao", "Entrada", "Nivel anterior", "Candle anterior", "Entradas", "Wins", "Win rate", "Media a favor", "Media contra ate voltar", "Media a favor apos voltar", "Recuperou", "Leitura"],
            ),
            "",
            "## Arquivos Do Ativo",
            "",
            f"- Resumo: `{summary_file.name}`",
            f"- Dinamica: `{dynamics_file.name}`",
            f"- Relatorio: `{report_file.name}`",
            "",
        ]

        report_file.write_text("\n".join(lines), encoding="utf-8")
        symbol_summary.sort_values(["timeframe", "target"]).to_csv(summary_file, index=False)
        symbol_grouped.sort_values(["timeframe", "target", "side", "prev_candle", "entry_rule"]).to_csv(dynamics_file, index=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backteste rapido dos sinais do modelo.")
    parser.add_argument("--symbols", nargs="+", default=SYMBOLS, help="Ativos para testar. Ex: EURUSD GBPUSD")
    parser.add_argument("--timeframes", nargs="+", default=TIMEFRAMES, help="Timeframes para testar. Ex: H1 H4")
    parser.add_argument("--years", type=int, default=BACKTEST_YEARS, help="Periodo em anos do historico disponivel.")
    parser.add_argument(
        "--targets",
        nargs="+",
        type=int,
        default=TARGETS_POINTS,
        help="Alvos em pontos. Ex: 100 200 300 400 500",
    )
    parser.add_argument("--lookahead", type=int, default=LOOKAHEAD_CANDLES, help="Candles maximos apos a entrada.")
    parser.add_argument("--force", action="store_true", help="Recalcula mesmo se houver cache do ativo/timeframe.")
    return parser.parse_args()


def main() -> None:
    global TARGETS_POINTS, LOOKAHEAD_CANDLES

    args = parse_args()
    symbols = [symbol.upper() for symbol in args.symbols]
    timeframes = [timeframe.upper() for timeframe in args.timeframes]
    TARGETS_POINTS = args.targets
    LOOKAHEAD_CANDLES = args.lookahead

    root = Path(__file__).resolve().parents[1] if Path(__file__).resolve().parent.name == "tools" else Path(__file__).resolve().parent
    cache_root = root / CACHE_DIR
    summaries = []
    detailed_frames = []
    processed = 0

    for symbol in symbols:
        for timeframe in timeframes:
            print("\n" + "#" * 100)
            print(f"TESTANDO {symbol} {timeframe}")
            print("#" * 100)

            data_path = root / "data" / "parquet" / timeframe / f"{symbol}.parquet"
            model_dir = root / "models_expr" / symbol / timeframe
            if not model_dir.exists():
                model_dir = root / "models_principal" / symbol / timeframe

            if not data_path.exists():
                print(f"Arquivo de dados nao encontrado: {data_path}")
                continue
            if not model_dir.exists():
                print(f"Modelo nao encontrado: {model_dir}")
                continue

            key = cache_key(symbol, timeframe, args.years)
            if not args.force:
                cached = load_summary_cache(cache_root, key)
                if cached is not None:
                    summaries.append(cached)
                    processed += 1
                    print(f"Cache usado: {symbol} {timeframe}")
                    continue

            engine = BacktestEngine(data_path, model_dir, symbol, timeframe, args.years)
            trades = engine.run()
            print_summary(trades, symbol, timeframe)
            summary = summarize_trades(trades)
            save_summary_cache(cache_root, key, summary)
            summaries.append(summary)
            if SAVE_DETAILED_CSV:
                detailed_frames.append(trades)
            processed += 1

            if processed % SAVE_PROGRESS_EVERY == 0:
                generate_report_from_summaries(
                    summaries,
                    root / REPORT_MD,
                    root / SUMMARY_CSV,
                    root / DYNAMICS_CSV,
                    root / DETAILED_CSV,
                    symbols,
                    timeframes,
                    args.years,
                )
                print(f"Progresso salvo apos {processed} combinacoes. Ultimo: {symbol} {timeframe}")

    if summaries:
        summary_path = root / SUMMARY_CSV
        dynamics_path = root / DYNAMICS_CSV
        detailed_path = root / DETAILED_CSV
        report_path = root / REPORT_MD
        summary_output = generate_report_from_summaries(
            summaries,
            report_path,
            summary_path,
            dynamics_path,
            detailed_path,
            symbols,
            timeframes,
            args.years,
        )
        if SAVE_DETAILED_CSV and detailed_frames:
            pd.concat(detailed_frames, ignore_index=True).to_csv(detailed_path, index=False)
        total_entries = int(sum(int(s["unique_entries"]) for s in summaries))
        total_simulations = int(sum(int(s["simulations"]) for s in summaries))
        print("\n" + "=" * 100)
        print(f"Resumo salvo: {summary_path}")
        print(f"Dinamica salva: {dynamics_path}")
        print(f"Relatorio salvo: {report_path}")
        if SAVE_DETAILED_CSV:
            print(f"Detalhado salvo: {detailed_path}")
        print(f"Total geral de entradas: {total_entries}")
        print(f"Total geral de simulacoes por alvo: {total_simulations}")
        print(f"Linhas no resumo CSV: {len(summary_output)}")
        print("=" * 100)
    else:
        report_path = root / REPORT_MD
        generate_report_from_summaries(
            [],
            report_path,
            root / SUMMARY_CSV,
            root / DYNAMICS_CSV,
            root / DETAILED_CSV,
            symbols,
            timeframes,
            args.years,
        )
        print(f"Nenhum resultado gerado. Relatorio salvo: {report_path}")


if __name__ == "__main__":
    main()
