from __future__ import annotations

import argparse
import json
import sys
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Any
from queue import Queue

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "terminal_qt"))

from fusion_terminal_qt import TIMEFRAMES, normalize_symbol  # noqa: E402
from market_data import MarketDataService  # noqa: E402
from runtime_utils import TARGET_SYMBOLS  # noqa: E402


OUT_DIR = ROOT / "runtime" / "market_data" / "latest_candles"


def parse_csv_list(value: str | None, fallback: list[str]) -> list[str]:
    if not value:
        return fallback
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def _export_symbol_tf(service: MarketDataService, symbol: str, timeframe: str, bars: int) -> tuple[bool, str]:
    """Exporta um símbolo/timeframe. Retorna (sucesso, nome_arquivo)."""
    try:
        normalized = normalize_symbol(symbol)
        candles = service.read_ohlc_mt5(normalized, timeframe)
        if not candles:
            return False, ""
        
        payload: dict[str, Any] = {
            "schema": "fusion.terminal.latest_candles.v1",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "symbol": normalized,
            "broker_symbol": service.last_broker_symbol,
            "timeframe": timeframe,
            "source": "MT5",
            "count": len(candles[-bars:]),
            "candles": candles[-bars:],
        }
        target = OUT_DIR / f"{normalized}_{timeframe}.json"
        tmp = target.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(target)
        return True, target.name
    except Exception as e:
        print(f"  ERRO {symbol}/{timeframe}: {e}", flush=True)
        return False, ""


def export_once(symbols: list[str], timeframes: list[str], bars: int, max_workers: int = 3) -> int:
    """Exporta candles com paralelização limitada."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    service = MarketDataService()
    service.build_symbol_map()
    
    # Criar fila de tarefas: [(símbolo, timeframe), ...]
    tasks = [(s, tf) for s in symbols for tf in timeframes]
    total_tasks = len(tasks)
    
    if total_tasks == 0:
        print(f"[TERMINAL] Nenhum símbolo/timeframe para exportar", flush=True)
        return 0
    
    print(f"[TERMINAL] Exportando {total_tasks} snapshots (max {max_workers} paralelos)...", flush=True)
    start_time = time.time()
    
    # Fila thread-safe para resultados
    result_queue: Queue = Queue()
    written = 0
    errors = 0
    
    def worker():
        """Worker thread que processa tarefas da fila."""
        while True:
            try:
                item = result_queue.get_nowait()
                if item is None:  # Sentinela para parar
                    break
                symbol, timeframe = item
                success, filename = _export_symbol_tf(service, symbol, timeframe, bars)
                if success:
                    print(f"  OK {filename}", flush=True)
            except:
                pass
    
    # Executar sequencialmente com logging
    for i, (symbol, timeframe) in enumerate(tasks, 1):
        success, filename = _export_symbol_tf(service, symbol, timeframe, bars)
        if success:
            written += 1
            if i % 6 == 0:  # A cada 6 exports (1 símbolo × 6 timeframes)
                elapsed = time.time() - start_time
                print(f"  {i}/{total_tasks} snapshots ({elapsed:.1f}s)...", flush=True)
        else:
            errors += 1
    
    elapsed = time.time() - start_time
    print(f"[TERMINAL] {written}/{total_tasks} snapshots em {elapsed:.2f}s" + (f" | {errors} erros" if errors > 0 else ""), flush=True)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Exporta candles recentes do MT5 para o Fusion Terminal Windows.")
    parser.add_argument("--symbols", default="", help="Lista separada por virgula. Vazio usa symbols do config.")
    parser.add_argument("--timeframes", default="M5,M15,M30,H1,H4,D1")
    parser.add_argument("--bars", type=int, default=200, help="Número de barras a exportar (padrão: 200, era 600)")
    parser.add_argument("--interval", type=float, default=0.0, help="Segundos entre exportacoes. 0 executa uma vez.")
    args = parser.parse_args()

    fallback_symbols = [normalize_symbol(item) for item in TARGET_SYMBOLS] or ["XAUUSD", "EURUSD"]
    symbols = parse_csv_list(args.symbols, fallback_symbols)
    timeframes = [item for item in parse_csv_list(args.timeframes, list(TIMEFRAMES)) if item in TIMEFRAMES]
    
    print(f"[TERMINAL] Configuração: {len(symbols)} símbolos × {len(timeframes)} timeframes | {args.bars} barras/export", flush=True)
    
    iteration = 0
    while True:
        iteration += 1
        start_time = time.time()
        written = export_once(symbols, timeframes, max(args.bars, 50))
        elapsed = time.time() - start_time
        
        print(f"{datetime.now():%Y-%m-%d %H:%M:%S} [TERMINAL] Ciclo #{iteration}: {written} snapshots em {elapsed:.2f}s | saida={OUT_DIR}", flush=True)
        
        if args.interval <= 0:
            break
        
        # Aguardar intervalo
        remaining = max(0, args.interval - elapsed)
        if remaining > 0:
            print(f"[TERMINAL] Aguardando {remaining:.1f}s até próximo ciclo...", flush=True)
            time.sleep(remaining)


if __name__ == "__main__":
    main()


