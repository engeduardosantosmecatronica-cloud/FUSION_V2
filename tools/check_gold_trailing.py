from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

from fusion.core.config import get_config
from fusion.execution.trailing import TrailingManager


def main() -> None:
    if mt5 is None:
        raise SystemExit("MetaTrader5 nao instalado no ambiente Python.")
    cfg = get_config()
    terminal_path = str(cfg.get("broker.terminal_path", "") or "")
    initialized = mt5.initialize(path=terminal_path) if terminal_path else mt5.initialize()
    if not initialized:
        raise SystemExit(f"Falha ao inicializar MT5: {mt5.last_error()}")

    try:
        mapping = cfg.get("data.symbol_mapping", {}) or {}
        broker_symbol = mapping.get("XAUUSD", "GOLD")
        info = mt5.symbol_info(broker_symbol)
        if info is None:
            print(f"Simbolo broker nao encontrado: {broker_symbol}")
            alternatives = [s.name for s in mt5.symbols_get() or [] if "XAU" in s.name.upper() or "GOLD" in s.name.upper()]
            print("Alternativas:", ", ".join(alternatives[:20]) or "-")
            return
        mt5.symbol_select(broker_symbol, True)
        tick = mt5.symbol_info_tick(broker_symbol)
        positions = list(mt5.positions_get(symbol=broker_symbol) or [])
        trailing = TrailingManager()

        print(f"Broker symbol: {broker_symbol}")
        print(f"Point: {getattr(info, 'point', 0)} Digits: {getattr(info, 'digits', 0)}")
        print(f"Tick: bid={getattr(tick, 'bid', None)} ask={getattr(tick, 'ask', None)}")
        print(f"Trailing config: {trailing._get_trailing_config(broker_symbol)}")
        print(f"Posicoes: {len(positions)}")

        for pos in positions:
            config = trailing._get_trailing_config(broker_symbol, getattr(pos, "magic", None))
            point = float(getattr(info, "point", 0.0) or 0.0)
            if not tick or not point:
                profit_points = 0.0
            elif pos.type == mt5.ORDER_TYPE_BUY:
                profit_points = (float(tick.bid) - float(pos.price_open)) / point
            else:
                profit_points = (float(pos.price_open) - float(tick.ask)) / point
            print(
                f"#{pos.ticket} magic={pos.magic} tipo={'BUY' if pos.type == mt5.ORDER_TYPE_BUY else 'SELL'} "
                f"open={pos.price_open} sl={pos.sl} tp={pos.tp} profit={pos.profit} "
                f"profit_points={profit_points:.1f} activation={config['activation_points']} "
                f"distance={config['distance_points']} ativo={profit_points >= config['activation_points']}"
            )
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
