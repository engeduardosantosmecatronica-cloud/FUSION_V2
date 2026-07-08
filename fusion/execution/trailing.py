"""
FUSION_V2 - Trailing Stop Manager
=================================
Inspirado em OMNIS: trailing stop, proteÃ§Ã£o de lucro
"""

import json
import threading
from pathlib import Path
from typing import Optional, Dict, List

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

from fusion.core.logger import get_logger
from fusion.core.config import get_config
from fusion.runtime_control import RuntimeControl


TRAILING_CONFIG = {
    # Valores em pontos (ex: 100 pontos = 10 pips para pares FX)
    "default": {"activation_points": 100, "distance_points": 50},      # 10/5 pips
    "GOLD": {"activation_points": 1100, "distance_points": 600},      # Gold no broker
    "XAGUSD": {"activation_points": 1000, "distance_points": 500},    # 100/50 pips
}


class TrailingManager:
    """Gerenciador de trailing stop - inspirado em OMNIS."""
    
    def __init__(self):
        self.logger = get_logger("TrailingManager")
        self.config = get_config()
        self.runtime_control = RuntimeControl()
        self.active_positions: Dict[int, dict] = {}
        self.optimized_trailing = self._load_optimized_trailing()
    
    def _load_optimized_trailing(self) -> Dict[str, dict]:
        """Carrega presets otimizados gerados pelo FUSION refatorado."""
        root = Path(__file__).resolve().parents[2]
        path = root / "fusion_refatorado" / "models" / "production_registry" / "trailing_optimized_M5.json"
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            items = payload.get("items", {})
            self.logger.info(f"[TRAILING] Presets otimizados carregados: {path}")
            return items
        except Exception as exc:
            self.logger.warning(f"[TRAILING] Falha ao carregar presets otimizados {path}: {exc}")
            return {}

    @staticmethod
    def _timeframe_from_magic(magic: Optional[int]) -> Optional[str]:
        if magic is None:
            return None
        magic_text = str(int(magic))
        suffix_map = {
            "1440": "D1",
            "240": "H4",
            "60": "H1",
            "30": "M30",
            "15": "M15",
            "05": "M5",
            "5": "M5",
        }
        for suffix, timeframe in suffix_map.items():
            if magic_text.endswith(suffix):
                return timeframe
        return None

    def _base_symbol(self, symbol: str) -> str:
        symbol_upper = symbol.upper()
        if "XAU" in symbol_upper or "GOLD" in symbol_upper:
            return "GOLD"
        optimized_symbols = {
            str(item.get("symbol", "")).upper()
            for item in self.optimized_trailing.values()
            if item.get("symbol")
        }
        for candidate in sorted(optimized_symbols, key=len, reverse=True):
            if symbol_upper.startswith(candidate):
                return candidate
        return symbol_upper

    def _get_trailing_config(self, symbol: str, magic: Optional[int] = None) -> dict:
        """Retorna configuraÃ§Ã£o de trailing para o sÃ­mbolo."""
        timeframe = self._timeframe_from_magic(magic)
        base_symbol = self._base_symbol(symbol)
        runtime_symbols = self.runtime_control.section("risk_by_symbol")
        for candidate in [symbol.upper(), base_symbol.upper()]:
            runtime_override = runtime_symbols.get(candidate, {}) if isinstance(runtime_symbols, dict) else {}
            if runtime_override:
                activation = runtime_override.get("trailing_activation_points")
                distance = runtime_override.get("trailing_distance_points")
                if activation is not None and distance is not None:
                    try:
                        return {
                            "activation_points": int(activation),
                            "distance_points": int(distance),
                        }
                    except (TypeError, ValueError):
                        self.logger.warning(f"[TRAILING] Override runtime invalido para {candidate}: {runtime_override}")
        override_cfg = self.config.get("trailing.symbol_overrides", {}) or {}
        for candidate in [symbol.upper(), base_symbol.upper()]:
            override = override_cfg.get(candidate)
            if override:
                try:
                    return {
                        "activation_points": int(override["activation_points"]),
                        "distance_points": int(override["distance_points"]),
                    }
                except (KeyError, TypeError, ValueError):
                    self.logger.warning(f"[TRAILING] Override invalido para {candidate}: {override}")
        if timeframe:
            optimized = self.optimized_trailing.get(f"{base_symbol}_{timeframe}")
            if optimized:
                return {
                    "activation_points": int(optimized["activation_points"]),
                    "distance_points": int(optimized["distance_points"]),
                }
        sym_upper = symbol.upper()
        for candidate in [sym_upper, base_symbol]:
            if candidate in TRAILING_CONFIG:
                return TRAILING_CONFIG[candidate].copy()
        if "XAU" in sym_upper or "GOLD" in sym_upper:
            return TRAILING_CONFIG["GOLD"].copy()
        return TRAILING_CONFIG["default"].copy()
    
    def update_trailing(self, symbol: str, activation_points: Optional[int] = None,
                        distance_points: Optional[int] = None, allowed_magics: Optional[List[int]] = None):
        """Atualiza trailing stop para sÃ­mbolo (valores em pontos)."""
        runtime_trailing_enabled = self.runtime_control.get("trailing.enabled")
        if runtime_trailing_enabled is False or not self.config.trailing.enabled:
            return
        positions = mt5.positions_get(symbol=symbol)
        if not positions:
            return
        if allowed_magics:
            allowed_magic_set = set(int(magic) for magic in allowed_magics)
            positions = [pos for pos in positions if int(pos.magic) in allowed_magic_set]
            if not positions:
                return
        info = mt5.symbol_info(symbol)
        if not info:
            return
        point = info.point
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            return
        for pos in positions:
            pos_activation = activation_points
            pos_distance = distance_points
            if pos_activation is None or pos_distance is None:
                config = self._get_trailing_config(symbol, getattr(pos, "magic", None))
                pos_activation = config["activation_points"]
                pos_distance = config["distance_points"]
            self._process_position(pos, tick, point, pos_activation, pos_distance, symbol)
    
    def _process_position(self, pos, tick, point: float, activation: int, distance: int, symbol: str):
        """Processa trailing para uma posiÃ§Ã£o (valores em pontos)."""
        digits = int(mt5.symbol_info(symbol).digits) if mt5.symbol_info(symbol) else 5
        if pos.type == mt5.ORDER_TYPE_BUY:
            profit_points = (tick.bid - pos.price_open) / point
        else:
            profit_points = (pos.price_open - tick.ask) / point
        if profit_points < activation:
            return
        profit_pips = profit_points / 10
        if pos.type == mt5.ORDER_TYPE_BUY:
            new_sl = tick.bid - (distance * point)
            if new_sl > pos.sl or pos.sl == 0:
                request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": pos.ticket,
                    "sl": round(float(new_sl), digits),
                    "tp": round(float(pos.tp), digits),
                }
                result = mt5.order_send(request)
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    self.logger.info(f"[TRAILING BUY] {symbol} | Ativ: {profit_pips:.0f}pips | Novo SL: {new_sl:.{digits}f}")
        
        elif pos.type == mt5.ORDER_TYPE_SELL:
            new_sl = tick.ask + (distance * point)
            if new_sl < pos.sl or pos.sl == 0:
                request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": pos.ticket,
                    "sl": round(float(new_sl), digits),
                    "tp": round(float(pos.tp), digits),
                }
                result = mt5.order_send(request)
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    self.logger.info(f"[TRAILING SELL] {symbol} | Ativ: {profit_pips:.0f}pips | Novo SL: {new_sl:.{digits}f}")
    
    def update_all(self, symbols: list, allowed_magics: Optional[List[int]] = None):
        """Atualiza trailing para todos os sÃ­mbolos."""
        for symbol in symbols:
            self.update_trailing(symbol, allowed_magics=allowed_magics)
    
    def start_background_loop(
        self,
        symbols: list,
        interval: float = 1,
        allowed_magics: Optional[List[int]] = None,
        stop_event: Optional[threading.Event] = None,
    ):
        """Inicia loop de trailing em background."""
        interval = max(float(interval), 0.1)
        stop_event = stop_event or threading.Event()
        self.logger.info(
            f"[TRAILING] Iniciando loop independente para {len(symbols)} simbolos "
            f"| intervalo={interval:.2f}s"
        )
        self.logger.info(f"[TRAILING] Iniciando loop para {len(symbols)} sÃ­mbolos")
        
        gold_symbols = [
            str(item)
            for item in symbols
            if "XAU" in str(item).upper() or "GOLD" in str(item).upper()
        ]
        if gold_symbols:
            self.logger.info(f"[TRAILING] Gold monitorado como: {', '.join(gold_symbols)}")
        else:
            self.logger.warning("[TRAILING] Gold nao esta na lista de simbolos monitorados")

        if allowed_magics:
            self.logger.info(f"[TRAILING] Magics monitorados: {', '.join(str(m) for m in allowed_magics)}")

        while not stop_event.is_set():
            try:
                self.update_all(symbols, allowed_magics=allowed_magics)
            except Exception as e:
                self.logger.error(f"[TRAILING] Erro: {e}")
            
            stop_event.wait(interval)
